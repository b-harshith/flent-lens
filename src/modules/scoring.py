"""
Flent Lens — Opportunity Scoring & Tiering
Implements the full composite Opportunity Score from the BBA spec:
  OPP_SCORE = ARBIT*arb + DII*dii + SFS*sfs + TRANSIT*transit + SEZ*sez
Tier assignment uses eligible-only percentile thresholds.
"""
import pandas as pd
import numpy as np
import geopandas as gpd
import config
from sklearn.preprocessing import MinMaxScaler
from src.utils.logger import print_info, print_detail, log_process

def _normalize(series: pd.Series) -> pd.Series:
    """Min-max normalize a Series to [0, 1]. Handles constant series."""
    vals = series.fillna(0).values.reshape(-1, 1)
    if vals.max() == vals.min():
        return pd.Series(0.0, index=series.index)
    return pd.Series(MinMaxScaler().fit_transform(vals).ravel(), index=series.index)


def compute_opportunity_score(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing composite Opportunity Score"):
        # ══════════════════════════════════════════════════════════
        # 1. DEMAND INTENSITY INDEX (DII)
        #    DII = 0.60 * norm(price_pressure) + 0.40 * norm(sfc)
        # ══════════════════════════════════════════════════════════
        df['norm_price_pressure'] = _normalize(df['price_pressure'])
        df['norm_sfc'] = _normalize(df['sfc']) if 'sfc' in df.columns else 0.0
        df['norm_psf_diff'] = _normalize(df['psf_diff']) if 'psf_diff' in df.columns else 0.0

        df['demand_intensity_idx'] = (
            config.DII_WEIGHT_PRICE_PRESSURE * df['norm_price_pressure'] +
            config.DII_WEIGHT_SFC            * df['norm_sfc'] +
            config.DII_WEIGHT_PSF_SPREAD     * df['norm_psf_diff']
        )

        # ══════════════════════════════════════════════════════════
        # 2. SUPPLY FEASIBILITY SCORE (SFS)
        #    SFS = 0.40*sv + 0.35*sa + 0.25*pf
        # ══════════════════════════════════════════════════════════
        cnt_4bhk = df['cnt_4bhk'] if 'cnt_4bhk' in df.columns else 0
        supply_raw = df['cnt_3bhk'] + cnt_4bhk
        max_supply = supply_raw.max() if supply_raw.max() > 0 else 1
        df['supply_volume_norm'] = np.log1p(supply_raw) / np.log1p(max_supply)
        df['size_adequacy'] = df['pct_3bhk_large'] if 'pct_3bhk_large' in df.columns else 0.0
        df['capital_efficiency_norm'] = _normalize(df['capital_efficiency']) if 'capital_efficiency' in df.columns else 0.0

        df['supply_depth_idx'] = (
            config.SFS_WEIGHT_VOLUME * df['supply_volume_norm'] +
            config.SFS_WEIGHT_SIZE   * df['size_adequacy'] +
            config.SFS_WEIGHT_ROI    * df['capital_efficiency_norm']
        )

        # ══════════════════════════════════════════════════════════
        # 3. NORMALIZE CORE METRICS
        # ══════════════════════════════════════════════════════════
        df['norm_arb_margin_pct'] = _normalize(df['arb_margin_pct'])
        df['norm_transit'] = _normalize(df['transit_score']) if (config.HAS_TRANSIT and 'transit_score' in df.columns) else 0.0
        df['norm_sez'] = _normalize(df['sez_employment_score']) if (config.HAS_SEZ and 'sez_employment_score' in df.columns) else 0.0

        # ══════════════════════════════════════════════════════════
        # 4. COMPOSITE OPPORTUNITY SCORE
        #    Economic base (sums to 1.0) + overlay (SEZ) - penalty (Transit)
        # ══════════════════════════════════════════════════════════
        df['OPP_SCORE'] = (
            (df['norm_arb_margin_pct']  * config.ECON_WEIGHT_ARBITRAGE) +    # +0.45
            (df['demand_intensity_idx'] * config.ECON_WEIGHT_DII) +          # +0.30
            (df['supply_depth_idx']     * config.ECON_WEIGHT_SFS) +          # +0.25
            (df['norm_sez']             * config.OVERLAY_WEIGHT_SEZ) -       # +0.10
            (df['norm_transit']         * config.OVERLAY_WEIGHT_TRANSIT)     # -0.10 (Traffic Penalty)
        ) * 100

        score_min = df['OPP_SCORE'].min()
        score_max = df['OPP_SCORE'].max()
        print_detail(f"Raw Base Score range: {score_min:.1f} — {score_max:.1f}")
        return df


def apply_spatial_spillover(df: pd.DataFrame, wards_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    with log_process("Applying Spatial Spillover (Neighborhood Contagion)"):
        # 1. Assign baseline tiers temporarily to map aura sources
        base_df = assign_tiers(df.copy())
        tier_map = base_df.set_index('ward_id')['tier'].to_dict()
        
        # 2. Extract geometries and run spatial spatial join (intersects)
        temp_gdf = wards_gdf.copy()
        if 'ward_name' not in temp_gdf.columns:
            temp_gdf['ward_name'] = temp_gdf['ward_id'].astype(str)
        temp_gdf = temp_gdf[['ward_id', 'geometry', 'ward_name']].copy()
        temp_gdf['base_tier'] = temp_gdf['ward_id'].map(tier_map).fillna('Excluded')
        
        joined = gpd.sjoin(temp_gdf, temp_gdf, how='inner', predicate='intersects')
        joined = joined[joined['ward_id_left'] != joined['ward_id_right']]  # Drop self matches
        
        spillover_boost = {}
        aura_sources_map = {}
        isolated_count = 0
        for ward_id, group in joined.groupby('ward_id_left'):
            neighbor_tiers = group['base_tier_right'].unique()
            own_tier = tier_map.get(ward_id, 'Excluded')
            
            # Extract names for the popup UI
            sources = []
            if 'Tier 1' in neighbor_tiers:
                t1_names = group[group['base_tier_right'] == 'Tier 1']['ward_name_right'].tolist()
                sources.append("<b>" + "</b>, <b>".join(t1_names) + "</b> (Tier 1)")
            if 'Tier 2' in neighbor_tiers:
                t2_names = group[group['base_tier_right'] == 'Tier 2']['ward_name_right'].tolist()
                sources.append("<b>" + "</b>, <b>".join(t2_names) + "</b> (Tier 2)")
            
            # Isolation Penalty: Penalty if Tier 1 has zero Tier 1/2 neighbors
            is_island = (own_tier == 'Tier 1') and not ('Tier 1' in neighbor_tiers or 'Tier 2' in neighbor_tiers)
            
            if is_island and hasattr(config, 'ISOLATION_PENALTY'):
                spillover_boost[ward_id] = config.ISOLATION_PENALTY
                isolated_count += 1
                aura_sources_map[ward_id] = "No Tier 1 or Tier 2 neighbors (Island pattern)."
            elif 'Tier 1' in neighbor_tiers:
                spillover_boost[ward_id] = config.SPILLOVER_BOOST_TIER1
                aura_sources_map[ward_id] = " ".join(sources)
            elif 'Tier 2' in neighbor_tiers:
                spillover_boost[ward_id] = config.SPILLOVER_BOOST_TIER2
                aura_sources_map[ward_id] = " ".join(sources)
            elif 'Tier 3' in neighbor_tiers:
                spillover_boost[ward_id] = config.SPILLOVER_BOOST_TIER3
                aura_sources_map[ward_id] = "Adjacent to Tier 3 wards."
            else:
                spillover_boost[ward_id] = 1.0
                aura_sources_map[ward_id] = "No significant neighbors."
                
        # 3. Apply Multiplier
        df['aura_multiplier'] = df['ward_id'].map(spillover_boost).fillna(1.0)
        df['aura_sources'] = df['ward_id'].map(aura_sources_map).fillna("Unknown")
        df['OPP_SCORE'] = df['OPP_SCORE'] * df['aura_multiplier']
        
        # 4. Re-index out of 100 based on the absolute best DATA-RICH viable ward, 
        #    so the top realistic opportunity is always benchmarked at 100.
        valid_benchmark = df['margin_viable'] & ~df['data_sparse']
        if valid_benchmark.any():
            viable_max = df.loc[valid_benchmark, 'OPP_SCORE'].max()
        else:
            viable_max = df['OPP_SCORE'].max()
            
        if viable_max > 0:
            df['OPP_SCORE'] = (df['OPP_SCORE'] / viable_max) * 100

        boost_t1 = sum(v == config.SPILLOVER_BOOST_TIER1 for v in spillover_boost.values())
        boost_t2 = sum(v == config.SPILLOVER_BOOST_TIER2 for v in spillover_boost.values())
        print_detail(f"Aura applied: {boost_t1} got Tier 1 boost, {boost_t2} got Tier 2 boost. Isloation Penalty: {isolated_count} wards.")
        
        score_min = df['OPP_SCORE'].min()
        score_max = df['OPP_SCORE'].max()
        print_detail(f"Final Score range: {score_min:.1f} — {score_max:.1f} (after 100-base indexing vs best viable ward)")
        return df


def assign_tiers(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Assigning investment tiers (eligible-only percentiles)"):
        # We relax the strict eligibility criteria. A ward must be AT LEAST margin_viable.
        # If it's data_sparse but highly viable, we don't automatically exclude it.
        # However, for calculating tier thresholds, we use the non-sparse viable wards as the benchmark.
        
        benchmark = df[df['margin_viable'] & ~df['data_sparse']]['OPP_SCORE']

        if len(benchmark) > 0:
            t1 = benchmark.quantile(config.TIER1_PERCENTILE / 100)
            t2 = benchmark.quantile(config.TIER2_PERCENTILE / 100)
            t3 = benchmark.quantile(config.TIER3_PERCENTILE / 100)
        else:
            t1 = df['OPP_SCORE'].quantile(0.75)
            t2 = df['OPP_SCORE'].quantile(0.50)
            t3 = df['OPP_SCORE'].quantile(0.25)

        def tier(row):
            # Exclude if not viable at all
            if not row['margin_viable']:
                return 'Excluded'
                
            # If it's sparse but viable, cap it at Tier 3 to be conservative, 
            # unless it scores incredibly high (above T2 threshold)
            is_sparse = row['data_sparse']
            score = row['OPP_SCORE']
            
            if score >= t1: return 'Tier 3' if is_sparse else 'Tier 1'
            if score >= t2: return 'Tier 3' if is_sparse else 'Tier 2'
            if score >= t3: return 'Tier 3'
            return 'Excluded'

        df['tier'] = df.apply(tier, axis=1)

        counts = df['tier'].value_counts()
        for t in ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']:
            print_detail(f"{t}: {counts.get(t, 0)} wards")
        return df
