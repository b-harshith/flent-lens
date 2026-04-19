"""
Flent Lens 2.0 — Hex-Level Feature Engineering & K-Ring Smoothing
Aggregates listing-level data to H3 hex-level features,
applies count-weighted distance-decayed spatial smoothing,
and computes bootstrap confidence intervals.
"""
import h3
import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import config
from src.utils.logger import print_info, print_detail, print_warning, log_process


def _weighted_median(values, weights):
    """Compute the weighted median of a 1D array."""
    if len(values) == 0:
        return np.nan
    sorted_idx = np.argsort(values)
    vals = np.array(values)[sorted_idx]
    wts = np.array(weights)[sorted_idx]
    cumw = np.cumsum(wts)
    cutoff = cumw[-1] * 0.5
    idx = np.searchsorted(cumw, cutoff)
    return vals[min(idx, len(vals) - 1)]


def _bootstrap_ci(values, weights, n_iter=500, ci_pct=90):
    """Compute bootstrap confidence interval for weighted median."""
    if len(values) < 3:
        med = _weighted_median(values, weights)
        return med, med
    lower_pct = (100 - ci_pct) / 2
    upper_pct = 100 - lower_pct
    medians = []
    probs = np.array(weights) / np.sum(weights)
    for _ in range(n_iter):
        idx = np.random.choice(len(values), size=len(values), replace=True, p=probs)
        boot_med = np.median(np.array(values)[idx])
        medians.append(boot_med)
    return np.percentile(medians, lower_pct), np.percentile(medians, upper_pct)


def aggregate_hex_features(listings_gdf: pd.DataFrame, hexes_gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Compute raw hex-level statistics from listing data.
    This is the pre-smoothing stage — direct counts and medians per hex.
    """
    with log_process("Computing raw hex-level features"):
        lg = listings_gdf.copy()

        # ──────────────────────────────────────────────────────────
        # 1. Counts by BHK and asset type
        # ──────────────────────────────────────────────────────────
        bhk_counts = lg.groupby(['hex_id', 'bhk_type']).size().unstack(fill_value=0)
        for b in [1, 2, 3, 4]:
            if b not in bhk_counts.columns:
                bhk_counts[b] = 0
        bhk_counts.columns = [f'cnt_{int(c)}bhk' for c in bhk_counts.columns]

        asset_counts = lg.groupby(['hex_id', 'asset_type']).size().unstack(fill_value=0)
        for at in ['apartment', 'villa']:
            if at not in asset_counts.columns:
                asset_counts[at] = 0
        asset_counts.columns = [f'n_{c}s' for c in asset_counts.columns]

        total_counts = lg.groupby('hex_id').size().rename('total_listings')

        # ──────────────────────────────────────────────────────────
        # 2. Median rents by BHK
        # ──────────────────────────────────────────────────────────
        median_rents = lg.groupby(['hex_id', 'bhk_type'])['monthly_rent'].median().unstack()
        for b in [1, 2, 3, 4]:
            if b not in median_rents.columns:
                median_rents[b] = np.nan
        median_rents.columns = [f'median_rent_{int(c)}bhk' for c in median_rents.columns]

        # Q1 (25th percentile) of 3BHK and villa rents — this is the acquisition cost
        q1_3bhk = (lg[(lg['bhk_type'] >= 3) & (lg['asset_type'] == 'apartment')]
                   .groupby('hex_id')['monthly_rent']
                   .quantile(0.25).rename('q1_rent_3bhk_apt'))

        q1_villa = (lg[lg['asset_type'] == 'villa']
                    .groupby('hex_id')['monthly_rent']
                    .quantile(0.25).rename('q1_rent_villa'))

        # Exact count of acquire-able volume (At or below Q1 cost)
        apt_eligible = lg[(lg['bhk_type'] >= 3) & (lg['asset_type'] == 'apartment')]
        n_acq_apt = (apt_eligible.groupby('hex_id')
                     .apply(lambda g: (g['monthly_rent'] <= g['monthly_rent'].quantile(0.25)).sum())
                     .rename('n_acq_apt')) if len(apt_eligible) > 0 else pd.Series(dtype=int, name='n_acq_apt')
                     
        vil_eligible = lg[lg['asset_type'] == 'villa']
        n_acq_villa = (vil_eligible.groupby('hex_id')
                       .apply(lambda g: (g['monthly_rent'] <= g['monthly_rent'].quantile(0.25)).sum())
                       .rename('n_acq_villa')) if len(vil_eligible) > 0 else pd.Series(dtype=int, name='n_acq_villa')

        # ──────────────────────────────────────────────────────────
        # 3. Sqft stats
        # ──────────────────────────────────────────────────────────
        sqft_stats = lg[lg['sqft'] > 0].groupby('hex_id')['sqft'].agg(
            median_sqft='median', mean_sqft='mean'
        )

        # Percentage of 3BHK+ apartments over size threshold
        apt_3bhk = lg[(lg['bhk_type'] >= 3) & (lg['asset_type'] == 'apartment')]
        if len(apt_3bhk) > 0:
            pct_large = apt_3bhk.groupby('hex_id').apply(
                lambda g: (g['sqft'] >= config.MIN_SQFT_APARTMENT).mean()
            ).rename('pct_3bhk_large')
        else:
            pct_large = pd.Series(dtype=float, name='pct_3bhk_large')

        pct_xl = apt_3bhk.groupby('hex_id').apply(
            lambda g: (g['sqft'] >= config.YIELD_APT_XL_SQFT).mean()
        ).rename('pct_3bhk_xl') if len(apt_3bhk) > 0 else pd.Series(dtype=float, name='pct_3bhk_xl')

        # ──────────────────────────────────────────────────────────
        # 4. Price per sqft spread
        # ──────────────────────────────────────────────────────────
        psf = lg[lg['price_per_sqft'].notna() & (lg['price_per_sqft'] > 0)]
        psf_1bhk = psf[psf['bhk_type'] == 1].groupby('hex_id')['price_per_sqft'].median().rename('rps_1bhk')
        psf_3bhk = psf[psf['bhk_type'] >= 3].groupby('hex_id')['price_per_sqft'].median().rename('rps_3bhk')

        # ──────────────────────────────────────────────────────────
        # 5. Merge all into hex_df
        # ──────────────────────────────────────────────────────────
        hex_df = hexes_gdf[['hex_id', 'centroid_lat', 'centroid_lon', 'area_sqkm']].copy()
        hex_df = hex_df.set_index('hex_id')

        for series in [total_counts, bhk_counts, asset_counts, median_rents,
                       q1_3bhk, q1_villa, n_acq_apt, n_acq_villa, sqft_stats, pct_large, pct_xl,
                       psf_1bhk, psf_3bhk]:
            hex_df = hex_df.join(series, how='left')

        hex_df = hex_df.fillna({'total_listings': 0, 'cnt_1bhk': 0, 'cnt_2bhk': 0,
                                'cnt_3bhk': 0, 'cnt_4bhk': 0, 'n_apartments': 0, 'n_villas': 0,
                                'n_acq_apt': 0, 'n_acq_villa': 0})
        hex_df = hex_df.reset_index()
        hex_df['sample_size'] = hex_df['total_listings'].astype(int)

        print_detail(f"Computed raw features for {len(hex_df)} hexes")
        print_detail(f"Hexes with ≥1 listing: {(hex_df['sample_size'] > 0).sum()}")
        return hex_df


def apply_kring_smoothing(hex_df: pd.DataFrame, listings_gdf: pd.DataFrame) -> pd.DataFrame:
    """
    Apply count-weighted, distance-decayed K-Ring smoothing for 1BHK median rent.
    Computes Neff and bootstrap confidence intervals.

    Weight function:  w_i = count_i / (1 + β × dist_i)
    Neff = (Σw)² / Σ(w²)
    """
    with log_process("Applying K-Ring weighted spatial smoothing"):
        beta = config.KRING_DECAY_BETA
        k = config.KRING_RADIUS
        bhk1 = listings_gdf[listings_gdf['bhk_type'] == 1].copy()

        # Pre-compute centroid lookup
        centroid_lookup = hex_df.set_index('hex_id')[['centroid_lat', 'centroid_lon']].to_dict('index')

        smoothed_records = []

        for _, row in hex_df.iterrows():
            hex_id = row['hex_id']
            own_count = int(row.get('cnt_1bhk', 0))

            # Own hex listings
            own_rents = bhk1[bhk1['hex_id'] == hex_id]['monthly_rent'].values
            own_center = (row['centroid_lat'], row['centroid_lon'])

            # Collect weighted rents from neighbors
            all_rents = list(own_rents)
            all_weights = [1.0] * len(own_rents)  # Own hex weight = 1.0 per listing

            neighbors = set(h3.grid_disk(hex_id, k))
            neighbors.discard(hex_id)

            for nb in neighbors:
                nb_rents = bhk1[bhk1['hex_id'] == nb]['monthly_rent'].values
                if len(nb_rents) == 0:
                    continue

                # Distance between centroids (in km, approximate)
                if nb in centroid_lookup:
                    nb_center = (centroid_lookup[nb]['centroid_lat'],
                                centroid_lookup[nb]['centroid_lon'])
                    dist_km = _haversine(own_center, nb_center)
                else:
                    dist_km = 2.5  # default for unknown neighbors

                # Weight per neighbor listing
                w = 1.0 / (1.0 + beta * dist_km)
                all_rents.extend(nb_rents)
                all_weights.extend([w] * len(nb_rents))

            # Compute smoothed metrics
            if len(all_rents) > 0:
                rents_arr = np.array(all_rents)
                weights_arr = np.array(all_weights)

                smoothed_median = _weighted_median(rents_arr, weights_arr)

                # Neff
                w_sum = weights_arr.sum()
                w_sq_sum = (weights_arr ** 2).sum()
                neff = (w_sum ** 2) / w_sq_sum if w_sq_sum > 0 else 0

                # Bootstrap CI
                ci_low, ci_high = _bootstrap_ci(
                    rents_arr, weights_arr,
                    n_iter=config.BOOTSTRAP_ITERATIONS,
                    ci_pct=config.BOOTSTRAP_CI_PCT
                )

                pct_neighbor = 1 - (len(own_rents) / len(all_rents)) if len(all_rents) > 0 else 0
            else:
                smoothed_median = np.nan
                neff = 0
                ci_low = ci_high = np.nan
                pct_neighbor = 0

            smoothed_records.append({
                'hex_id': hex_id,
                'smoothed_median_1bhk': smoothed_median,
                'Neff': round(neff, 2),
                'rent_1bhk_CI_low': ci_low,
                'rent_1bhk_CI_high': ci_high,
                'pct_neighbor_sourced': round(pct_neighbor, 3),
            })

        smooth_df = pd.DataFrame(smoothed_records)
        hex_df = hex_df.merge(smooth_df, on='hex_id', how='left')

        # Confidence classification
        hex_df['confidence'] = 'data_insufficient'
        hex_df.loc[hex_df['Neff'] >= config.NEFF_LOW_CONFIDENCE, 'confidence'] = 'low_confidence'
        hex_df.loc[hex_df['Neff'] >= config.NEFF_FULL_CONFIDENCE, 'confidence'] = 'full'

        # Use smoothed median as the primary 1BHK rent (overrides raw)
        hex_df['avg_rent_1bhk'] = hex_df['smoothed_median_1bhk']

        # Stats
        conf_counts = hex_df['confidence'].value_counts()
        print_detail(f"Confidence: Full={conf_counts.get('full', 0)} | "
                     f"Low={conf_counts.get('low_confidence', 0)} | "
                     f"Insufficient={conf_counts.get('data_insufficient', 0)}")
        print_detail(f"Median Neff: {hex_df['Neff'].median():.1f}")

        return hex_df


def compute_demand_features(hex_df: pd.DataFrame) -> pd.DataFrame:
    """Compute DII sub-components at hex level."""
    with log_process("Computing demand intensity features"):
        city_median_1bhk = hex_df['avg_rent_1bhk'].median()
        if city_median_1bhk == 0 or pd.isna(city_median_1bhk):
            city_median_1bhk = 1  # prevent division by zero

        hex_df['city_median_1bhk'] = city_median_1bhk
        hex_df['price_pressure'] = hex_df['avg_rent_1bhk'] / city_median_1bhk

        # Small Flat Concentration
        hex_df['sfc'] = np.where(
            hex_df['total_listings'] > 0,
            (hex_df['cnt_1bhk'] + hex_df['cnt_2bhk']) / hex_df['total_listings'],
            0
        )

        # PSF spread
        hex_df['psf_diff'] = (hex_df['rps_1bhk'].fillna(0) - hex_df['rps_3bhk'].fillna(0)).abs()

        print_detail(f"City median 1BHK rent: ₹{city_median_1bhk:,.0f}")
        return hex_df


def _haversine(coord1, coord2):
    """Haversine distance in km between (lat, lon) tuples."""
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))
