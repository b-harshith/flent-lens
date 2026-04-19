"""
Flent Lens 2.0 — Pipeline Orchestrator
H3 hexagonal grid, PCA calibration, dual-track economics, OSM automation, SAR/SEM validation.

Usage:
    python main.py                     # Run for active city (default: bangalore)
    python main.py --city pune         # Run for a specific city
    python main.py --all-cities        # Run all 15 cities + cross-city analysis
    python main.py --compare-only      # Re-run cross-city comparator from cached summaries
"""
import argparse
import json
import os
import sys
import time

import pandas as pd

import config
from city_config import CITY_PROFILES, get_profile
from src.utils.logger import (
    print_banner, print_stage, print_info, print_detail, print_success,
    print_warning, print_error, display_final_dashboard, console
)


TOTAL_STAGES = 9  # Per-city pipeline stages


def run_pipeline(city_key: str) -> dict:
    """Execute the full Lens 2.0 pipeline for a single city. Returns city_summary dict."""

    # Dynamically update config for this city
    profile = get_profile(city_key)
    config.CITY = profile
    config.CITY_NAME = profile['city_name']
    config.CITY_KEY = city_key
    config.CITY_CODE = profile.get('city_code', 'UNK')
    config.BOUNDING_BOX = profile['bounding_box']
    config.CRS_PROJECTED = profile['crs_projected']
    config.PROCESSED_DIR = profile['processed_dir']
    config.OUTPUT_DIR = profile['output_dir']
    config.HAS_ADMIN_KML = profile.get('has_admin_kml', False)
    config.ADMIN_KML = profile.get('admin_kml')

    os.makedirs(config.PROCESSED_DIR, exist_ok=True)
    os.makedirs(config.OUTPUT_DIR, exist_ok=True)

    t0 = time.time()
    print_banner()
    export_paths = []

    # ══════════════════════════════════════════════════════════════
    # STAGE 1: DATA INGESTION
    # ══════════════════════════════════════════════════════════════
    print_stage(1, TOTAL_STAGES, "Data Ingestion",
                f"Loading listings for {config.CITY_NAME} from compiled CSV")
    from src.modules.loader import load_listings, load_admin_boundaries
    listings_gdf = load_listings(city_key)
    admin_gdf = load_admin_boundaries()

    # ══════════════════════════════════════════════════════════════
    # STAGE 2: H3 GRID GENERATION
    # ══════════════════════════════════════════════════════════════
    print_stage(2, TOTAL_STAGES, "H3 Grid Generation",
                f"Tessellating at Resolution {config.H3_RESOLUTION}")
    from src.modules.spatial import assign_to_h3, generate_h3_grid, compute_maup_stability
    listings_gdf = assign_to_h3(listings_gdf)
    hexes_gdf = generate_h3_grid(listings_gdf)

    # MAUP sensitivity
    stability_df = compute_maup_stability(listings_gdf)

    # ══════════════════════════════════════════════════════════════
    # STAGE 3: OSM CONTEXT & REVERSE GEOCODING
    # ══════════════════════════════════════════════════════════════
    print_stage(3, TOTAL_STAGES, "OSM Context & Geocoding",
                "Fetching transit, employment, lifestyle POIs from OpenStreetMap")
    from src.modules.osm_engine import fetch_osm_pois, compute_hex_poi_scores, reverse_geocode_hexes
    osm_data = fetch_osm_pois(city_key)

    # ══════════════════════════════════════════════════════════════
    # STAGE 4: FEATURE ENGINEERING
    # ══════════════════════════════════════════════════════════════
    print_stage(4, TOTAL_STAGES, "Feature Engineering",
                "K-Ring smoothing, Neff, bootstrap CIs, demand/supply features")
    from src.modules.aggregator import aggregate_hex_features, apply_kring_smoothing, compute_demand_features
    hex_df = aggregate_hex_features(listings_gdf, hexes_gdf)
    hex_df = apply_kring_smoothing(hex_df, listings_gdf)
    hex_df = compute_demand_features(hex_df)

    # Merge stability scores
    if len(stability_df) > 0:
        hex_df = hex_df.merge(stability_df, on='hex_id', how='left')
        hex_df['stability_score'] = hex_df['stability_score'].fillna(1.0)
    else:
        hex_df['stability_score'] = 1.0

    # ══════════════════════════════════════════════════════════════
    # STAGE 5: ECONOMIC MODELING
    # ══════════════════════════════════════════════════════════════
    print_stage(5, TOTAL_STAGES, "Economic Modeling",
                "Dual-track arbitrage (Apartment + Villa), DDF elasticity")
    from src.modules.economics import compute_dual_track_economics
    hex_df = compute_dual_track_economics(hex_df)

    # ══════════════════════════════════════════════════════════════
    # STAGE 6: PCA CALIBRATION + SCORING
    # ══════════════════════════════════════════════════════════════
    print_stage(6, TOTAL_STAGES, "PCA Calibration & Opportunity Scoring",
                "Data-driven weight calibration + composite score + H3 spillover")
    from src.modules.weight_calibrator import calibrate_all_weights
    from src.modules.scoring import compute_opportunity_score, apply_spatial_spillover, assign_tiers

    pca_weights = calibrate_all_weights(hex_df) if config.USE_PCA_WEIGHTS else {}

    # OSM overlay scores
    hex_df = compute_hex_poi_scores(hex_df, osm_data)

    # Reverse geocode hex names
    hex_df = reverse_geocode_hexes(hex_df, admin_gdf)

    hex_df = compute_opportunity_score(hex_df, pca_weights)
    hex_df = apply_spatial_spillover(hex_df)
    hex_df = assign_tiers(hex_df)

    # ══════════════════════════════════════════════════════════════
    # STAGE 7: ECONOMETRIC VALIDATION
    # ══════════════════════════════════════════════════════════════
    print_stage(7, TOTAL_STAGES, "Econometric Validation",
                "Moran's I (999 perms) + OLS baseline + SAR spatial lag")
    from src.modules.validator import (
        run_moran, run_ols, run_sar,
        save_moran_plot, save_ols_plot, save_regression_comparison
    )

    econometrics_dir = os.path.join(config.OUTPUT_DIR, 'econometrics')
    os.makedirs(econometrics_dir, exist_ok=True)

    moran, moran_valid = run_moran(hex_df)
    ols_model, ols_valid = run_ols(hex_df)
    sar_model = run_sar(hex_df)

    morans_result = None
    ols_r2 = None

    if moran:
        save_moran_plot(moran, moran_valid, econometrics_dir)
        morans_result = {'moran_i': f"{moran.I:.4f}", 'p_value': f"{moran.p_sim:.4f}",
                         'clustered': moran.p_sim < 0.05}
    if ols_model:
        save_ols_plot(ols_model, ols_valid if ols_valid is not None else hex_df, econometrics_dir)
        ols_r2 = ols_model.rsquared
    save_regression_comparison(ols_model, sar_model, econometrics_dir)

    # ══════════════════════════════════════════════════════════════
    # STAGE 8: EXPORT
    # ══════════════════════════════════════════════════════════════
    print_stage(8, TOTAL_STAGES, "Export & Delivery",
                "KML Atlas + Rich XLSX + GeoJSON + city_summary.json")
    from src.utils.exporter import (
        export_investment_atlas_kml, export_lens_report_xlsx,
        export_hex_geojson, export_city_summary
    )

    # Merge hex geometries for KML/GeoJSON
    hex_full = hexes_gdf[['hex_id', 'geometry']].merge(hex_df, on='hex_id')

    kml_path = export_investment_atlas_kml(hex_df, hex_full, listings_gdf, osm_data)
    xlsx_path = export_lens_report_xlsx(hex_df, ols_model, moran, sar_model, pca_weights)
    geojson_path = export_hex_geojson(hex_full)
    summary = export_city_summary(hex_df, moran, ols_model, sar_model)

    export_paths = [p for p in [kml_path, xlsx_path, geojson_path] if p]

    # ══════════════════════════════════════════════════════════════
    # FINAL DASHBOARD
    # ══════════════════════════════════════════════════════════════
    tier_counts = hex_df['tier'].value_counts().to_dict()
    top5 = hex_df[hex_df['tier'] == 'Tier 1'].sort_values('OPP_SCORE', ascending=False).head(5)
    if len(top5) == 0:
        top5 = hex_df.sort_values('OPP_SCORE', ascending=False).head(5)

    elapsed = time.time() - t0
    display_final_dashboard(tier_counts, top5, morans_result, ols_r2, export_paths, elapsed)

    return summary


def run_all_cities():
    """Run pipeline for every city in CITY_PROFILES."""
    summaries = []
    for city_key in CITY_PROFILES:
        console.print(f"\n{'='*60}")
        console.print(f"  Starting pipeline for: [bold]{city_key.upper()}[/]")
        console.print(f"{'='*60}\n")
        try:
            summary = run_pipeline(city_key)
            summaries.append(summary)
        except Exception as e:
            print_error(f"Pipeline failed for {city_key}: {e}")
            import traceback
            traceback.print_exc()

    # Cross-city comparator
    if len(summaries) > 1:
        console.print(f"\n{'='*60}")
        console.print("  Cross-City Comparison")
        console.print(f"{'='*60}\n")
        from src.utils.exporter import export_cross_city
        export_cross_city(summaries)


def main():
    parser = argparse.ArgumentParser(description="Flent Lens 2.0 — Multi-City Co-Living Analysis")
    parser.add_argument('--city', type=str, default=None,
                        help=f"City key (one of: {list(CITY_PROFILES.keys())})")
    parser.add_argument('--all-cities', action='store_true',
                        help="Run all 15 cities sequentially")
    parser.add_argument('--compare-only', action='store_true',
                        help="Re-run cross-city comparator from cached summaries")
    args = parser.parse_args()

    if args.compare_only:
        from src.utils.exporter import load_cached_summaries, export_cross_city
        summaries = load_cached_summaries()
        export_cross_city(summaries)
    elif args.city:
        # Single city mode
        if args.city not in CITY_PROFILES:
            print_error(f"Unknown city '{args.city}'. Available: {list(CITY_PROFILES.keys())}")
            sys.exit(1)
        run_pipeline(args.city)
    else:
        # Default: run ALL cities
        run_all_cities()


if __name__ == '__main__':
    main()
