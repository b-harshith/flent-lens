"""
Flent Lens — Pipeline Orchestrator
Runs all analytical stages in sequence with narrative terminal output.
This is the only file you execute directly:  python main.py

City selection is controlled by ACTIVE_CITY in city_config.py.
"""
import os
import sys
import warnings
from datetime import datetime

# Silencing unavoidable shapely/geopandas warnings during O(N*M) proximity matching
warnings.filterwarnings('ignore', category=RuntimeWarning, message='invalid value encountered in distance')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import config
from src.utils.logger import (
    print_banner, print_stage, print_success, print_info, print_warning,
    print_narrative, print_detail, print_metric, console,
    display_final_dashboard
)
from src.pipeline import cleaner, geocoder, mapper
from src.modules import loader, spatial, aggregator, economics, transit, sez, scoring, validator
from src.utils import exporter


def run_pipeline():
    pipeline_start = datetime.now()
    print_banner()

    # Determine stage count dynamically (skip transit/SEZ stage if both disabled)
    has_overlays = config.HAS_TRANSIT or config.HAS_SEZ
    TOTAL = 8 if has_overlays else 7
    stage_offset = 0  # used to adjust stage numbers when overlays are skipped

    geo_label  = config.GEO_UNIT_LABEL   # e.g. "BBMP Ward" or "Pincode Zone"
    city_name  = config.CITY_NAME         # e.g. "Bangalore" or "Hyderabad"

    # ═══════════════════════════════════════════════════════════
    # STAGE 0 — Data Pre-Processing
    # ═══════════════════════════════════════════════════════════
    print_stage(0, TOTAL, "Data Pre-Processing",
        f"Before analysis begins, we prepare raw inputs — cleaning Magicbricks "
        f"listings for {city_name}"
        + (", geocoding SEZ locations, and generating spatial geometries." if config.HAS_SEZ else "."))

    if not os.path.exists(config.LISTINGS_CSV):
        cleaner.clean_data(input_path=config.RAW_LISTINGS_CSV, output_path=config.LISTINGS_CSV)
    else:
        print_info("Cleaned listings found. Skipping data cleaning.")

    if config.HAS_SEZ:
        if not os.path.exists(config.SEZ_CSV):
            geocoder.geocode_sez(input_path=config.RAW_SEZ_CSV, output_path=config.SEZ_CSV)
        else:
            print_info("Geocoded SEZ data found. Skipping geocoding.")

        if not os.path.exists(config.SEZ_KML):
            mapper.generate_sez_kml(input_path=config.SEZ_CSV, output_path=config.SEZ_KML)
        else:
            print_info("SEZ geometries found. Skipping KML generation.")
    else:
        print_info("SEZ data not available for this city — skipping SEZ pre-processing.")

    # ═══════════════════════════════════════════════════════════
    # STAGE 1 — Data Ingestion
    # ═══════════════════════════════════════════════════════════
    datasets_desc = f"rental listings and {geo_label} boundaries"
    if config.HAS_TRANSIT:
        datasets_desc += ", transit routes"
    if config.HAS_SEZ:
        datasets_desc += ", and SEZ zones"

    print_stage(1, TOTAL, "Data Ingestion",
        f"The analysis begins. We ingest core datasets for {city_name} — {datasets_desc}.")

    listings_gdf = loader.load_listings(config.LISTINGS_CSV)
    wards_gdf    = loader.load_geo_zones(config.GEO_KML)
    routes_gdf   = loader.load_bus_routes()
    sez_gdf      = loader.load_sez()
    loader.validate_schema(listings_gdf, wards_gdf, routes_gdf, sez_gdf)

    # Save processed zones
    loader.save_processed_wards(wards_gdf)

    print_metric("Total Listings",  f"{len(listings_gdf):,}")
    print_metric(f"{geo_label}s",   f"{len(wards_gdf):,}")
    if config.HAS_TRANSIT:
        print_metric("Bus Routes",      f"{len(routes_gdf):,}")
    if config.HAS_SEZ:
        print_metric("SEZ Zones",       f"{len(sez_gdf):,}")

    # ═══════════════════════════════════════════════════════════
    # STAGE 2 — Spatial Operations
    # ═══════════════════════════════════════════════════════════
    transit_desc = " Transit routes are intersected with zones." if config.HAS_TRANSIT else ""
    print_stage(2, TOTAL, "Spatial Operations",
        f"Each listing is geo-mapped to its {geo_label} via point-in-polygon "
        f"joins with proximity fallback.{transit_desc}")

    wards_gdf    = spatial.compute_ward_areas(wards_gdf)
    listings_gdf = spatial.assign_listings_to_wards(listings_gdf, wards_gdf)
    clipped_gdf  = spatial.clip_routes_to_wards(routes_gdf, wards_gdf)

    print_metric(f"Listings in {geo_label}s", f"{listings_gdf['ward_id'].notna().sum():,}")
    if config.HAS_TRANSIT:
        print_metric("Transit Segments",  f"{len(clipped_gdf):,}")

    # ═══════════════════════════════════════════════════════════
    # STAGE 3 — Feature Engineering
    # ═══════════════════════════════════════════════════════════
    print_stage(3, TOTAL, "Feature Engineering",
        f"Outliers are pruned per {geo_label.lower()}-BHK group. Zone-level aggregates are "
        "computed: median rents, listing counts, size distributions, SFC.")

    listings_gdf = aggregator.remove_outliers_by_group(listings_gdf)
    ward_df      = aggregator.aggregate_ward_features(listings_gdf)
    ward_df      = aggregator.compute_derived_columns(ward_df)

    # Merge zone area and extra info for density calculations downstream
    ward_info = wards_gdf[['ward_id', 'area_sqkm']].copy()
    if 'zone_name' in wards_gdf.columns:
        ward_info['zone_name'] = wards_gdf['zone_name']
    ward_info = ward_info.drop_duplicates('ward_id')
    ward_df = ward_df.merge(ward_info, on='ward_id', how='left')
    ward_df = ward_df.drop_duplicates(subset='ward_id', keep='first').reset_index(drop=True)

    # Pre-compute quartile breakdown and merge early to enforce Q1 depth rules
    quartile_df = aggregator.compute_3bhk_quartile_breakdown(listings_gdf)
    ward_name_map = wards_gdf[['ward_id', 'ward_name']].drop_duplicates('ward_id')
    if quartile_df is not None and not quartile_df.empty:
        cols_to_merge = ['ward_id', 'q1_avg_rent', 'q1_count', 'q2_avg_rent', 'q2_count', 
                         'q3_avg_rent', 'q3_count', 'q4_avg_rent', 'q4_count']
        ward_df = ward_df.merge(quartile_df[cols_to_merge], on='ward_id', how='left')
        
    # Condition: count a ward only if it has 3+ listings in Q1
    if 'q1_count' in ward_df.columns:
        ward_df['data_sparse'] = ward_df['data_sparse'] | (ward_df['q1_count'].fillna(0) < 3)

    print_metric(f"{geo_label}s with Data", f"{len(ward_df):,}")
    sparse = ward_df['data_sparse'].sum() if 'data_sparse' in ward_df.columns else 0
    print_detail(f"{sparse} zones flagged data-sparse")

    # ═══════════════════════════════════════════════════════════
    # STAGE 4 — Economic Modeling
    # ═══════════════════════════════════════════════════════════
    print_stage(4, TOTAL, "Economic Modeling",
        "The core business thesis is quantified — arbitrage margins, "
        "demand intensity, supply feasibility, and margin density.")

    city_median = listings_gdf[
        listings_gdf['bhk_type'] == 1]['monthly_rent'].median()
    ward_df = economics.compute_arbitrage_margin(ward_df, city_median)
    ward_df = economics.compute_demand_intensity_index(ward_df)
    ward_df = economics.compute_supply_feasibility_score(ward_df)
    ward_df = economics.compute_effective_margin_density(ward_df)

    viable = ward_df['margin_viable'].sum() if 'margin_viable' in ward_df.columns else 0
    best   = ward_df['arb_margin_best'].max() if 'arb_margin_best' in ward_df.columns else 0
    print_metric("City Median 1BHK",   f"₹{city_median:,.0f}")
    print_metric("Viable-Margin Zones", f"{viable}")
    print_metric("Peak Arb Margin",    f"₹{best:,.0f}/month")

    # ═══════════════════════════════════════════════════════════
    # STAGE 5 — Contextual Overlays (conditional)
    # ═══════════════════════════════════════════════════════════
    current_stage = 5
    if has_overlays:
        overlay_parts = []
        if config.HAS_TRANSIT:
            overlay_parts.append("Transit connectivity")
        if config.HAS_SEZ:
            overlay_parts.append("SEZ employment proximity")
        overlay_desc = " and ".join(overlay_parts)

        print_stage(current_stage, TOTAL, "Contextual Overlays",
            f"{overlay_desc} scored using route density analysis and a gravity model.")

        if config.HAS_TRANSIT:
            transit_df  = transit.compute_transit_score(wards_gdf, routes_gdf, clipped_gdf)
            loader.save_processed_transit(transit_df)
            ward_df = ward_df.merge(
                transit_df.drop_duplicates('ward_id'),  on='ward_id', how='left')
            print_metric("Transit Coverage", f"{(transit_df['transit_score'] > 0).sum()} zones scored")

        if config.HAS_SEZ:
            sez_metrics = sez.compute_sez_score(wards_gdf, sez_gdf)
            ward_df = ward_df.merge(
                sez_metrics.drop_duplicates('ward_id'), on='ward_id', how='left')
            print_metric("SEZ Proximity",    f"{len(sez_gdf)} zones modeled")

        ward_df = ward_df.drop_duplicates(subset='ward_id', keep='first').reset_index(drop=True)
        ward_df = ward_df.fillna(0)
    else:
        # No overlays — ensure columns exist with zero values
        print_info("No contextual overlays configured for this city — using pure economic scoring.")
        ward_df['transit_score'] = 0.0
        ward_df['sez_employment_score'] = 0.0
        ward_df['closest_sezs'] = 'N/A'
        stage_offset = 1  # stages after this shift by -1

    # ═══════════════════════════════════════════════════════════
    # STAGE 6 — Opportunity Indexing  (with score checkpoints)
    # ═══════════════════════════════════════════════════════════
    scoring_stage = 6 if has_overlays else 5
    print_stage(scoring_stage, TOTAL, "Opportunity Indexing",
        "The composite Opportunity Score is computed from weighted "
        "economic, demand, supply, and overlay signals.")

    # Merge ward names early so checkpoints carry them
    ward_name_map = wards_gdf[['ward_id', 'ward_name']].drop_duplicates('ward_id')
    if 'ward_name' not in ward_df.columns:
        ward_df = ward_df.merge(ward_name_map, on='ward_id', how='left')

    ward_df = scoring.compute_opportunity_score(ward_df)

    # ── Checkpoint A: base score (economic + overlays, no spatial)
    score_checkpoint_base = ward_df[['ward_id', 'ward_name', 'OPP_SCORE']].copy()
    score_checkpoint_base = score_checkpoint_base.rename(columns={'OPP_SCORE': 'score_base'})

    ward_df = scoring.apply_spatial_spillover(ward_df, wards_gdf)

    # ── Checkpoint B: after aura/island spatial
    score_checkpoint_aura = ward_df[['ward_id', 'OPP_SCORE', 'aura_multiplier']].copy()
    score_checkpoint_aura = score_checkpoint_aura.rename(columns={'OPP_SCORE': 'score_after_aura'})

    ward_df = scoring.assign_tiers(ward_df)

    tier_counts = ward_df['tier'].value_counts().to_dict()
    for t in ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']:
        print_metric(t, f"{tier_counts.get(t, 0)} zones")

    # ═══════════════════════════════════════════════════════════
    # STAGE 7 — Econometric Validation
    # ═══════════════════════════════════════════════════════════
    validation_stage = 7 if has_overlays else 6
    print_stage(validation_stage, TOTAL, "Econometric Validation",
        "Statistical rigor is verified via Moran's I spatial autocorrelation "
        "and Arbitrage Structural Regression.")

    os.makedirs(config.OUTPUT_DIR, exist_ok=True)
    morans_result = validator.run_morans_i(
        wards_gdf.merge(ward_df, on='ward_id'), 'avg_rent_1bhk', config.OUTPUT_DIR)
    ols_model = validator.run_arbitrage_ols(ward_df, config.OUTPUT_DIR)
    ols_r2 = ols_model.rsquared if ols_model and hasattr(ols_model, 'rsquared') else None

    # ═══════════════════════════════════════════════════════════
    # STAGE 8 — Export & Delivery
    # ═══════════════════════════════════════════════════════════
    export_stage = 8 if has_overlays else 7
    print_stage(export_stage, TOTAL, "Export & Delivery",
        f"One consolidated KML atlas for Google Earth ({city_name}), "
        "and one multi-sheet Excel report for leadership.")

    # Build stage breakdown table for XLSX Sheet 3
    stage_merge_cols = ['ward_id']
    if config.HAS_TRANSIT:
        stage_merge_cols.append('transit_score')
    if config.HAS_SEZ:
        stage_merge_cols.append('sez_employment_score')

    stage_df = score_checkpoint_base.merge(
        ward_df[stage_merge_cols].drop_duplicates('ward_id'),
        on='ward_id', how='left'
    ).merge(score_checkpoint_aura, on='ward_id', how='left')

    # Ensure transit/SEZ columns exist for stage breakdown even if disabled
    if 'transit_score' not in stage_df.columns:
        stage_df['transit_score'] = 0.0
    if 'sez_employment_score' not in stage_df.columns:
        stage_df['sez_employment_score'] = 0.0

    stage_df = stage_df.merge(
        ward_df[['ward_id', 'OPP_SCORE', 'tier', 'arb_margin_best', 'margin_viable']],
        on='ward_id', how='left'
    )
    stage_df = stage_df.rename(columns={'OPP_SCORE': 'score_final'})

    paths = []
    paths.append(exporter.export_investment_atlas_kml(ward_df, wards_gdf, listings_gdf))
    paths.append(exporter.export_lens_report_xlsx(ward_df, stage_df, ols_model, morans_result))
    paths.append(exporter.export_geojson(ward_df, wards_gdf))
    paths.append(exporter.export_3bhk_quartile_xlsx(quartile_df, ward_name_map))

    paths = [p for p in paths if p]

    elapsed = (datetime.now() - pipeline_start).total_seconds()

    top5 = ward_df[ward_df['tier'] == 'Tier 1'].sort_values(
        'OPP_SCORE', ascending=False).head(5)
    if len(top5) == 0:
        top5 = ward_df.sort_values('OPP_SCORE', ascending=False).head(5)

    display_final_dashboard(tier_counts, top5, morans_result, ols_r2, paths, elapsed)

if __name__ == '__main__':
    try:
        run_pipeline()
    except KeyboardInterrupt:
        console.print("\n[error]Pipeline aborted by user.[/error]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[error]CRITICAL FAILURE:[/] {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
