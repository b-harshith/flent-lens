"""
Flent Lens 2.0 — PCA Weight Calibration
Replaces arbitrary expert weights with data-driven weights derived from
Principal Component Analysis variance-explained proportions.
"""
import json
import os
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
import config
from src.utils.logger import print_info, print_detail, log_process


def calibrate_weights(feature_matrix: np.ndarray, feature_names: list,
                      floor: float = None) -> dict:
    """
    Given a matrix of N hexes × K normalized features,
    return data-driven weights proportional to each feature's
    contribution to the first principal component.

    floor: minimum weight (default from config.PCA_WEIGHT_FLOOR)
    """
    floor = floor or config.PCA_WEIGHT_FLOOR

    # Remove rows with NaN
    mask = ~np.isnan(feature_matrix).any(axis=1)
    clean = feature_matrix[mask]

    if len(clean) < 5 or clean.shape[1] < 2:
        # Not enough data — return equal weights
        n = len(feature_names)
        return dict(zip(feature_names, [1.0 / n] * n))

    pca = PCA(n_components=1)
    pca.fit(clean)

    # Squared loadings = variance contribution per feature
    loadings = pca.components_[0]
    contributions = loadings ** 2
    weights = contributions / contributions.sum()

    # Apply floor constraint
    weights = np.maximum(weights, floor)
    weights = weights / weights.sum()  # re-normalize

    return dict(zip(feature_names, weights.round(4)))


def calibrate_all_weights(hex_df: pd.DataFrame) -> dict:
    """
    Calibrate all composite index weights using PCA on the hex-level dataset.
    Returns a dict of dicts: {index_name: {feature: weight}}.
    Also saves to disk for transparency.
    """
    with log_process("PCA Weight Calibration"):
        results = {}

        # ── DII Weights ──
        dii_cols = ['norm_price_pressure', 'norm_sfc', 'norm_psf_diff']
        available_dii = [c for c in dii_cols if c in hex_df.columns]
        if len(available_dii) >= 2:
            matrix = hex_df[available_dii].values
            results['DII'] = calibrate_weights(matrix, available_dii)
            _log_weights('DII', results['DII'])
        else:
            results['DII'] = None

        # ── SFS Weights ──
        sfs_cols = ['supply_volume_norm', 'size_adequacy', 'capital_efficiency_norm']
        available_sfs = [c for c in sfs_cols if c in hex_df.columns]
        if len(available_sfs) >= 2:
            matrix = hex_df[available_sfs].values
            results['SFS'] = calibrate_weights(matrix, available_sfs)
            _log_weights('SFS', results['SFS'])
        else:
            results['SFS'] = None

        # ── ECON_SCORE Weights ──
        econ_cols = ['norm_arb_margin_pct', 'demand_intensity_idx', 'supply_depth_idx']
        available_econ = [c for c in econ_cols if c in hex_df.columns]
        if len(available_econ) >= 2:
            matrix = hex_df[available_econ].values
            results['ECON'] = calibrate_weights(matrix, available_econ)
            _log_weights('ECON_SCORE', results['ECON'])
        else:
            results['ECON'] = None

        # ── Save to disk ──
        cache_path = os.path.join(config.PROCESSED_DIR, 'pca_weights.json')
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        print_detail(f"Saved PCA weights to {os.path.basename(cache_path)}")

        return results


def get_weights(pca_results: dict, index_name: str, expert_defaults: dict) -> dict:
    """
    Return PCA weights if available and USE_PCA_WEIGHTS is True,
    otherwise fall back to expert defaults.
    """
    if config.USE_PCA_WEIGHTS and pca_results.get(index_name):
        return pca_results[index_name]
    return expert_defaults


def _log_weights(name, weights):
    parts = [f"{k.replace('norm_', '').replace('_norm', '')}={v:.2f}" for k, v in weights.items()]
    print_detail(f"  {name} PCA weights: {' | '.join(parts)}")
