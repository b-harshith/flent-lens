"""
Flent Lens 2.0 — Dual-Track Economic Modeling
Computes arbitrage margins for both Apartment and Villa sourcing tracks.
Each hex gets evaluated on both tracks, and the best-performing one is selected.
"""
import numpy as np
import pandas as pd
import config
from src.utils.logger import print_info, print_detail, print_warning, log_process


def _compute_room_yield_apartment(sqft):
    """Dynamic room yield from apartment sqft."""
    if sqft >= config.YIELD_APT_XL_SQFT:
        return 4
    elif sqft >= config.YIELD_APT_LARGE_SQFT:
        return 3.5
    else:
        return config.YIELD_APT_STANDARD


def _compute_room_yield_villa(sqft):
    """Dynamic room yield from villa sqft."""
    if sqft >= config.YIELD_VILLA_XL_SQFT:
        return 6
    elif sqft >= config.YIELD_VILLA_LARGE_SQFT:
        return 5
    else:
        return config.YIELD_VILLA_BASE


def _elastic_ddf(base_ddf, price_pressure):
    """
    Apply elastic band to DDF based on local price pressure.
    High demand wards → DDF approaches 0.90 (can charge more)
    Low demand wards → DDF drops toward 0.70 (must discount more)
    """
    band = config.DDF_ELASTIC_BAND
    adjustment = (price_pressure - 1.0) * band  # pressure=1.0 is city median
    adjusted = base_ddf + adjustment
    return np.clip(adjusted, base_ddf - band, base_ddf + band)


def compute_dual_track_economics(hex_df: pd.DataFrame) -> pd.DataFrame:
    """
    For each hex, compute:
      1. Apartment track: margin from 3BHK+ acquisition at Q1, selling rooms at DDF_APT
      2. Villa track: margin from villa acquisition at Q1, selling rooms at DDF_VILLA
      3. Best-of selection per hex

    Revenue baseline is always the local (smoothed) 1BHK median rent.
    """
    with log_process("Computing dual-track arbitrage economics"):
        df = hex_df.copy()

        # ──────────────────────────────────────────────────────────
        # 1. PER-ROOM REVENUE (same for both tracks)
        # ──────────────────────────────────────────────────────────
        # Elastic DDF per hex
        df['ddf_apartment'] = df['price_pressure'].apply(
            lambda pp: _elastic_ddf(config.DDF_APARTMENT, pp) if pd.notna(pp) else config.DDF_APARTMENT
        )
        df['ddf_villa'] = df['price_pressure'].apply(
            lambda pp: _elastic_ddf(config.DDF_VILLA, pp) if pd.notna(pp) else config.DDF_VILLA
        )

        # Per room revenue = smoothed_1bhk_median × DDF
        df['room_revenue_apt'] = df['avg_rent_1bhk'] * df['ddf_apartment']
        df['room_revenue_villa'] = df['avg_rent_1bhk'] * df['ddf_villa']

        # ──────────────────────────────────────────────────────────
        # 2. APARTMENT TRACK
        # ──────────────────────────────────────────────────────────
        # Acquisition cost = Q1 of 3BHK+ apartment rents
        df['acq_cost_apt'] = df['q1_rent_3bhk_apt']

        # Room yield (based on median sqft of 3BHK stock in this hex)
        df['rooms_apt'] = df['median_sqft'].apply(
            lambda s: _compute_room_yield_apartment(s) if pd.notna(s) and s > 0 else 3
        )

        # Margin = (rooms × per_room_revenue) - acquisition_cost
        df['arb_margin_apartment'] = (df['rooms_apt'] * df['room_revenue_apt']) - df['acq_cost_apt']
        df['arb_margin_apt_pct'] = np.where(
            df['acq_cost_apt'] > 0,
            df['arb_margin_apartment'] / df['acq_cost_apt'],
            0
        )

        # ──────────────────────────────────────────────────────────
        # 3. VILLA TRACK
        # ──────────────────────────────────────────────────────────
        df['acq_cost_villa'] = df['q1_rent_villa']

        df['rooms_villa'] = df['median_sqft'].apply(
            lambda s: _compute_room_yield_villa(s) if pd.notna(s) and s >= config.VILLA_MIN_SQFT else 4
        )

        df['arb_margin_villa'] = (df['rooms_villa'] * df['room_revenue_villa']) - df['acq_cost_villa']
        df['arb_margin_villa_pct'] = np.where(
            df['acq_cost_villa'] > 0,
            df['arb_margin_villa'] / df['acq_cost_villa'],
            0
        )

        # ──────────────────────────────────────────────────────────
        # 4. BEST-OF SELECTION
        # ──────────────────────────────────────────────────────────
        df['arb_margin_apartment'] = df['arb_margin_apartment'].fillna(-999999)
        df['arb_margin_villa'] = df['arb_margin_villa'].fillna(-999999)

        df['best_asset_type'] = np.where(
            df['arb_margin_apartment'] >= df['arb_margin_villa'],
            'apartment', 'villa'
        )
        df['arb_margin_best'] = df[['arb_margin_apartment', 'arb_margin_villa']].max(axis=1)
        df['arb_margin_pct'] = np.where(
            df['best_asset_type'] == 'apartment',
            df['arb_margin_apt_pct'],
            df['arb_margin_villa_pct']
        )

        # Replace sentinel values back to NaN for display
        df.loc[df['arb_margin_apartment'] == -999999, 'arb_margin_apartment'] = np.nan
        df.loc[df['arb_margin_villa'] == -999999, 'arb_margin_villa'] = np.nan
        df.loc[df['arb_margin_best'] == -999999, 'arb_margin_best'] = np.nan

        # ──────────────────────────────────────────────────────────
        # 5. VIABILITY FLAGS
        # ──────────────────────────────────────────────────────────
        df['margin_viable'] = (
            (df['arb_margin_best'] >= config.MARGIN_VIABLE_FLOOR) &
            (df['arb_margin_pct'] >= config.MARGIN_VIABLE_PCT)
        )

        df['data_sparse'] = df['confidence'] == 'data_insufficient'

        # ──────────────────────────────────────────────────────────
        # 6. DEMAND INTENSITY INDEX (DII)
        # ──────────────────────────────────────────────────────────
        from sklearn.preprocessing import MinMaxScaler

        def _norm(series):
            vals = series.fillna(0).values.reshape(-1, 1)
            if vals.max() == vals.min():
                return pd.Series(0.0, index=series.index)
            return pd.Series(MinMaxScaler().fit_transform(vals).ravel(), index=series.index)

        df['norm_price_pressure'] = _norm(df['price_pressure'])
        df['norm_sfc'] = _norm(df['sfc'])
        df['norm_psf_diff'] = _norm(df['psf_diff'])

        df['demand_intensity_idx'] = (
            config.DII_WEIGHT_PRICE_PRESSURE * df['norm_price_pressure'] +
            config.DII_WEIGHT_SFC * df['norm_sfc'] +
            config.DII_WEIGHT_PSF_SPREAD * df['norm_psf_diff']
        )

        # ──────────────────────────────────────────────────────────
        # 7. SUPPLY FEASIBILITY SCORE (SFS)
        # ──────────────────────────────────────────────────────────
        supply_raw = df['cnt_3bhk'] + df['cnt_4bhk'] + df['n_villas']
        max_supply = supply_raw.max() if supply_raw.max() > 0 else 1
        df['supply_volume_norm'] = np.log1p(supply_raw) / np.log1p(max_supply)
        df['size_adequacy'] = df['pct_3bhk_large'].fillna(0)

        # Capital efficiency: margin per unit of acquisition cost
        df['capital_efficiency'] = np.where(
            df['acq_cost_apt'] > 0,
            df['arb_margin_best'] / df['acq_cost_apt'],
            0
        )
        df['capital_efficiency_norm'] = _norm(df['capital_efficiency'])

        df['supply_depth_idx'] = (
            config.SFS_WEIGHT_VOLUME * df['supply_volume_norm'] +
            config.SFS_WEIGHT_SIZE * df['size_adequacy'] +
            config.SFS_WEIGHT_ROI * df['capital_efficiency_norm']
        )

        # ──────────────────────────────────────────────────────────
        # 8. MARGIN DENSITY (TAM proxy)
        # ──────────────────────────────────────────────────────────
        # Number of Q1 acquisition opportunities × margin, per sq km
        q1_count = np.maximum(supply_raw * 0.25, 1).astype(int)  # ~25% of supply is Q1
        df['q1_count'] = q1_count
        df['margin_density'] = np.where(
            df['area_sqkm'] > 0,
            (df['arb_margin_best'].fillna(0) * q1_count) / df['area_sqkm'],
            0
        )

        # ──────────────────────────────────────────────────────────
        # 9. SUPPLY QUARTILE BREAKDOWNS (for Excel export)
        # ──────────────────────────────────────────────────────────
        df['demand_discount'] = np.where(
            df['best_asset_type'] == 'apartment',
            df['ddf_apartment'],
            df['ddf_villa']
        )

        # Stats
        viable_count = df['margin_viable'].sum()
        apt_wins = ((df['best_asset_type'] == 'apartment') & df['margin_viable']).sum()
        villa_wins = ((df['best_asset_type'] == 'villa') & df['margin_viable']).sum()
        median_margin = df.loc[df['margin_viable'], 'arb_margin_best'].median()

        print_info(f"Viable hexes: [highlight]{viable_count}[/highlight] / {len(df)}")
        print_detail(f"Best asset: Apartment wins={apt_wins}, Villa wins={villa_wins}")
        if pd.notna(median_margin):
            print_detail(f"Median viable margin: ₹{median_margin:,.0f}/mo")

        return df
