"""
Flent Lens 2.0 — Opportunity Scoring & Tiering (H3 Grid)
PCA-weighted composite score + H3 K-Ring spillover/island mechanics.
"""
import h3
import pandas as pd
import numpy as np
import config
from sklearn.preprocessing import MinMaxScaler
from src.utils.logger import print_info, print_detail, log_process

def _normalize(series):
    vals = series.fillna(0).values.reshape(-1, 1)
    if vals.max() == vals.min(): return pd.Series(0.0, index=series.index)
    return pd.Series(MinMaxScaler().fit_transform(vals).ravel(), index=series.index)

def compute_opportunity_score(df, pca_weights=None):
    with log_process("Computing composite Opportunity Score"):
        df['norm_arb_margin_pct'] = _normalize(df['arb_margin_pct'])

        # ECON_SCORE with PCA or expert weights
        if pca_weights and pca_weights.get('ECON'):
            w = pca_weights['ECON']
            w_arb = w.get('norm_arb_margin_pct', config.ECON_WEIGHT_ARBITRAGE)
            w_dii = w.get('demand_intensity_idx', config.ECON_WEIGHT_DII)
            w_sfs = w.get('supply_depth_idx', config.ECON_WEIGHT_SFS)
        else:
            w_arb, w_dii, w_sfs = config.ECON_WEIGHT_ARBITRAGE, config.ECON_WEIGHT_DII, config.ECON_WEIGHT_SFS

        # Normalize overlay scores if they exist
        for col in ['transit_score', 'employment_score', 'lifestyle_score']:
            if col in df.columns:
                df[f'norm_{col}'] = _normalize(df[col])
            else:
                df[f'norm_{col}'] = 0.0

        # OSM confidence scaling
        osm_conf = df.get('osm_confidence', pd.Series(1.0, index=df.index))
        osm_scale = osm_conf.clip(lower=config.OSM_CONFIDENCE_FLOOR)

        df['OPP_SCORE'] = (
            (df['norm_arb_margin_pct'] * w_arb) +
            (df['demand_intensity_idx'] * w_dii) +
            (df['supply_depth_idx'] * w_sfs) +
            (df['norm_transit_score'] * config.OVERLAY_WEIGHT_TRANSIT * osm_scale) +
            (df['norm_employment_score'] * config.OVERLAY_WEIGHT_EMPLOYMENT * osm_scale) +
            (df['norm_lifestyle_score'] * config.OVERLAY_WEIGHT_LIFESTYLE * osm_scale)
        ) * 100

        print_detail(f"Raw score range: {df['OPP_SCORE'].min():.1f} — {df['OPP_SCORE'].max():.1f}")
        return df

def apply_spatial_spillover(df):
    """H3 K-Ring based spillover — no geopandas sjoin needed."""
    with log_process("Applying H3-based Spatial Spillover"):
        base_df = assign_tiers(df.copy())
        tier_map = base_df.set_index('hex_id')['tier'].to_dict()
        name_map = base_df.set_index('hex_id').get('hex_name', pd.Series(dtype=str)).to_dict()

        spillover_boost = {}
        aura_sources_map = {}
        isolated = 0

        for hex_id in df['hex_id']:
            own_tier = tier_map.get(hex_id, 'Excluded')
            neighbors = set(h3.grid_disk(hex_id, 1))
            neighbors.discard(hex_id)
            neighbor_tiers = [tier_map.get(n, 'Excluded') for n in neighbors if n in tier_map]

            sources = []
            has_t1 = 'Tier 1' in neighbor_tiers
            has_t2 = 'Tier 2' in neighbor_tiers
            has_t3 = 'Tier 3' in neighbor_tiers

            if has_t1:
                t1_names = [name_map.get(n, n[:8]) for n in neighbors if tier_map.get(n) == 'Tier 1']
                sources.append(f"<b>{', '.join(t1_names[:3])}</b> (Tier 1)")
            if has_t2:
                t2_names = [name_map.get(n, n[:8]) for n in neighbors if tier_map.get(n) == 'Tier 2']
                sources.append(f"<b>{', '.join(t2_names[:3])}</b> (Tier 2)")

            is_island = own_tier == 'Tier 1' and not has_t1 and not has_t2
            if is_island:
                spillover_boost[hex_id] = config.ISOLATION_PENALTY
                aura_sources_map[hex_id] = "No Tier 1/2 neighbors (Island pattern)."
                isolated += 1
            elif has_t1:
                spillover_boost[hex_id] = config.SPILLOVER_BOOST_TIER1
                aura_sources_map[hex_id] = " ".join(sources)
            elif has_t2:
                spillover_boost[hex_id] = config.SPILLOVER_BOOST_TIER2
                aura_sources_map[hex_id] = " ".join(sources)
            elif has_t3:
                spillover_boost[hex_id] = config.SPILLOVER_BOOST_TIER3
                aura_sources_map[hex_id] = "Adjacent to Tier 3 hexes."
            else:
                spillover_boost[hex_id] = 1.0
                aura_sources_map[hex_id] = "No significant neighbors."

        df['aura_multiplier'] = df['hex_id'].map(spillover_boost).fillna(1.0)
        df['aura_sources'] = df['hex_id'].map(aura_sources_map).fillna("Unknown")
        df['OPP_SCORE'] = df['OPP_SCORE'] * df['aura_multiplier']

        # Re-index to 100 against best viable hex
        valid = df['margin_viable'] & (df['confidence'] != 'data_insufficient')
        viable_max = df.loc[valid, 'OPP_SCORE'].max() if valid.any() else df['OPP_SCORE'].max()
        if viable_max > 0:
            df['OPP_SCORE'] = (df['OPP_SCORE'] / viable_max) * 100

        boost_t1 = sum(v == config.SPILLOVER_BOOST_TIER1 for v in spillover_boost.values())
        print_detail(f"Aura: {boost_t1} T1 boosts, {isolated} island penalties")
        return df

def assign_tiers(df):
    with log_process("Assigning investment tiers"):
        benchmark = df[df['margin_viable'] & (df['confidence'] == 'full')]['OPP_SCORE']
        if len(benchmark) == 0:
            benchmark = df[df['margin_viable']]['OPP_SCORE']
        if len(benchmark) == 0:
            benchmark = df['OPP_SCORE']

        t1 = benchmark.quantile(config.TIER1_PERCENTILE / 100)
        t2 = benchmark.quantile(config.TIER2_PERCENTILE / 100)
        t3 = benchmark.quantile(config.TIER3_PERCENTILE / 100)

        def tier(row):
            if not row.get('margin_viable', False): return 'Excluded'
            sparse = row.get('confidence') == 'data_insufficient'
            unstable = row.get('stability_score', 1.0) < config.STABILITY_THRESHOLD
            s = row['OPP_SCORE']
            if s >= t1:
                if sparse or unstable: return 'Tier 2'  # Demoted — can't trust fully
                return 'Tier 1'
            if s >= t2: return 'Tier 3' if sparse else 'Tier 2'
            if s >= t3: return 'Tier 3'
            return 'Excluded'

        df['tier'] = df.apply(tier, axis=1)
        counts = df['tier'].value_counts()
        for t in ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']:
            print_detail(f"  {t}: {counts.get(t, 0)} hexes")
        return df
