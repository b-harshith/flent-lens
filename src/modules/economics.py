"""
Flent Lens — Economic Modeling
Arbitrage margin computation (3BHK + 4BHK), demand intensity,
supply feasibility, effective margin density, and PSF differential.
"""
import pandas as pd
import numpy as np
import config
from src.utils.logger import print_info, print_detail, log_process

def compute_arbitrage_margin(df: pd.DataFrame, city_median_1bhk: float) -> pd.DataFrame:
    with log_process("Computing arbitrage margins (Elastic Conversion Pricing)"):
        # Elastic Pricing Power: Premium wards can command a higher % of 1BHK rent
        df['price_pressure'] = (df['avg_rent_1bhk'] / city_median_1bhk) if city_median_1bhk > 0 else 0
        elastic_discount = config.DEMAND_DISCOUNT_FACTOR * df['price_pressure'].clip(0.90, 1.10)
        df['demand_discount'] = elastic_discount
        per_room_revenue = df['avg_rent_1bhk'] * elastic_discount

        # ── 3BHK Conversion: Dynamic Room Yield ──
        # Large spaces (>1600sqft) yield 4 rooms via living room / servant partition
        if getattr(config, 'DYNAMIC_YIELD', '').lower() == 'yes':
            df['yield_multiplier_3bhk'] = np.where(
                df['avg_sqft_3bhk'] >= config.YIELD_3BHK_XL_SQFT, 4.0, 3.0
            )
        else:
            df['yield_multiplier_3bhk'] = 3.0
            
        df['theoretical_3bhk_revenue'] = per_room_revenue * df['yield_multiplier_3bhk']
        df['arb_margin_3bhk'] = df['theoretical_3bhk_revenue'] - df['avg_rent_3bhk']
        df['arb_margin_pct_3bhk'] = (df['arb_margin_3bhk'] / df['avg_rent_3bhk']).replace([np.inf, -np.inf], 0).fillna(0)
        # Guard: zero-out where no 3BHK data exists
        df.loc[df['avg_rent_3bhk'] <= 0, 'arb_margin_3bhk'] = 0
        df.loc[df['avg_rent_3bhk'] <= 0, 'arb_margin_pct_3bhk'] = 0

        # ── 4BHK Conversion: Dynamic Room Yield ──
        if getattr(config, 'DYNAMIC_YIELD', '').lower() == 'yes':
            df['yield_multiplier_4bhk'] = np.where(
                df['avg_sqft_4bhk'] >= config.YIELD_4BHK_XL_SQFT, 5.0, 4.0
            )
        else:
            df['yield_multiplier_4bhk'] = 4.0
            
        df['theoretical_4bhk_revenue'] = per_room_revenue * df['yield_multiplier_4bhk']
        df['arb_margin_4bhk'] = df['theoretical_4bhk_revenue'] - df['avg_rent_4bhk']
        df['arb_margin_pct_4bhk'] = (df['arb_margin_4bhk'] / df['avg_rent_4bhk']).replace([np.inf, -np.inf], 0).fillna(0)
        # Guard: zero-out where no 4BHK data exists
        df.loc[df['avg_rent_4bhk'] <= 0, 'arb_margin_4bhk'] = 0
        df.loc[df['avg_rent_4bhk'] <= 0, 'arb_margin_pct_4bhk'] = 0

        # ── Best Configuration ──
        df['arb_margin_best'] = df[['arb_margin_3bhk', 'arb_margin_4bhk']].max(axis=1)
        df['arb_margin_abs']  = df['arb_margin_best']  # Legacy alias
        df['arb_margin_pct']  = df['arb_margin_pct_3bhk']  # Primary metric (3BHK)
        # Override with 4BHK pct if 4BHK is more profitable AND exists
        mask_4bhk = (df['arb_margin_4bhk'] > df['arb_margin_3bhk']) & (df['avg_rent_4bhk'] > 0)
        df.loc[mask_4bhk, 'arb_margin_pct'] = df.loc[mask_4bhk, 'arb_margin_pct_4bhk']

        # ── Viability Check — uses config threshold (default 5%) ──
        df['margin_viable'] = (
            (df['arb_margin_pct'] > config.MARGIN_VIABLE_PCT) &
            (df['avg_sqft_3bhk'] >= config.MIN_SQFT_3BHK)
        )

        viable = df['margin_viable'].sum()
        best   = df['arb_margin_best'].max()
        print_detail(f"{viable} wards with viable margins (>{config.MARGIN_VIABLE_PCT*100:.0f}%, ≥{config.MIN_SQFT_3BHK} sqft)")
        print_detail(f"Peak arbitrage margin: ₹{best:,.0f}/month")
        return df


def compute_demand_intensity_index(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing Demand Intensity Index (price pressure + velocity)"):
        # Price Pressure: already computed in arbitrage_margin

        # Listing Velocity (raw volume proxy)
        df['listing_velocity'] = df['cnt_1bhk']

        high_pressure = (df['price_pressure'] > 1.0).sum()
        print_detail(f"{high_pressure} wards above city-median price pressure")
        return df


def compute_supply_feasibility_score(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing Supply Feasibility Score (Capital Efficiency / ROI)"):
        # Size bonus: larger 3BHKs are easier to partition
        df['size_bonus'] = (df['avg_sqft_3bhk'] / config.LARGE_3BHK_SQFT).clip(0.8, 1.2)

        # Capital Efficiency (ROI): Replaces flawed entry_score
        # High ROI = low capital deployed for high absolute margin
        df['capital_efficiency'] = (df['arb_margin_best'] / df['avg_rent_3bhk']).replace([np.inf, -np.inf], 0).fillna(0)
        return df


def compute_effective_margin_density(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing Effective Margin Density per ward"):
        # EMD per spec: total addressable margin per km² based ONLY on Q1 stock (Flent's target demographic)
        if 'q1_count' in df.columns:
            supply_count = df['q1_count'].fillna(0)
        else:
            supply_count = (df['cnt_3bhk'] + df['cnt_4bhk']) * 0.25

        if 'area_sqkm' in df.columns:
            df['margin_density'] = (
                df['arb_margin_best'] * supply_count / df['area_sqkm']
            ).replace([np.inf, -np.inf], 0).fillna(0)
        else:
            # Fallback: margin per 1000 sqft
            df['margin_density'] = (df['arb_margin_best'] / (df['avg_sqft_3bhk'] + 1)) * 1000

        # ── Price-to-Rent Ratio Differential (diagnostic) ──
        # Per-sqft cost of one "room share" in a 3BHK vs standalone 1BHK
        room_share_psf = df['avg_rent_3bhk'] / (df['avg_sqft_3bhk'] * 0.33 + 1)
        df['psf_diff'] = (df['rps_1bhk'] - room_share_psf).replace([np.inf, -np.inf], 0).fillna(0)

        top_emd = df.nlargest(1, 'margin_density')
        if len(top_emd) > 0:
            print_detail(f"Highest EMD ward: {top_emd.iloc[0]['ward_id']} (₹{top_emd.iloc[0]['margin_density']:,.0f}/km²)")
        return df
