"""
Flent Lens — Feature Engineering
Outlier removal, ward-level aggregation, and derived metric computation.
Implements the full schema from the BBA Python Project spec.
"""
import pandas as pd
import numpy as np
import config
from src.utils.logger import print_info, print_detail, log_process

def remove_outliers_by_group(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Removing statistical outliers (3σ per ward-BHK group)"):
        original = len(df)

        # Drop listings that didn't map to any ward first
        unmapped = df['ward_id'].isna().sum()
        if unmapped > 0:
            df = df[df['ward_id'].notna()].copy()
            print_detail(f"Dropped {unmapped:,} listings outside BBMP boundaries")

        # Use transform() — broadcasts group-level stats back to original index,
        # preserving ALL columns (safe with GeoDataFrame in pandas 2+)
        grp = df.groupby(['ward_id', 'bhk_type'])['monthly_rent']
        group_median = grp.transform('median')
        group_std    = grp.transform('std').fillna(0)

        # Keep rows within 3σ of their group median (or in single-listing groups)
        mask = (group_std == 0) | (
            (df['monthly_rent'] - group_median).abs() <= config.OUTLIER_STD_THRESHOLD * group_std
        )
        df = df[mask].copy()

        removed = original - len(df)
        print_detail(f"{removed:,} rows removed (outliers + unmapped) from {original:,} listings")
        return df



def aggregate_ward_features(df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing ward-level statistical aggregates"):
        # ── Listing Counts by BHK Type ──
        counts = df.groupby(['ward_id', 'bhk_type']).size().unstack(fill_value=0)
        counts.columns = [f'cnt_{int(c)}bhk' for c in counts.columns]
        for bhk in [1, 2, 3, 4]:
            if f'cnt_{bhk}bhk' not in counts.columns:
                counts[f'cnt_{bhk}bhk'] = 0

        # ── Rental & Size Statistics by BHK ──
        grp = df.groupby(['ward_id', 'bhk_type'])
        
        rent_median = grp['monthly_rent'].median()
        rent_q25    = grp['monthly_rent'].quantile(0.25)
        sqft_median = grp['sqft'].median()

        stats = pd.DataFrame({
            'rent_median_raw': rent_median,
            'rent_q25': rent_q25,
            'sqft_median': sqft_median
        }).reset_index()

        # Flent Acquisition Strategy: 1BHK/2BHK use Medians (Retail). 3BHK/4BHK use 25th Percentile (Distressed/Base Acquisition)
        target_bhks = [3, 4, 3.0, 4.0, '3', '4', '3.0', '4.0']
        stats['rent_stat'] = np.where(stats['bhk_type'].isin(target_bhks), stats['rent_q25'], stats['rent_median_raw'])
        stats = stats[['ward_id', 'bhk_type', 'rent_stat', 'sqft_median']]
        stats.columns = ['ward_id', 'bhk_type', 'rent_median', 'sqft_median']

        pivoted = stats.pivot(index='ward_id', columns='bhk_type')
        pivoted.columns = [f'{col[0]}_{int(col[1])}bhk' for col in pivoted.columns]
        pivoted = pivoted.reset_index().fillna(0)

        # ── Merge Counts with Medians ──
        ward_df = pivoted.merge(counts.reset_index(), on='ward_id', how='outer').fillna(0)

        # ── Rename for Internal Consistency ──
        rename_map = {
            'rent_median_1bhk': 'avg_rent_1bhk', 'rent_median_2bhk': 'avg_rent_2bhk',
            'rent_median_3bhk': 'avg_rent_3bhk', 'rent_median_4bhk': 'avg_rent_4bhk',
            'sqft_median_1bhk': 'avg_sqft_1bhk', 'sqft_median_2bhk': 'avg_sqft_2bhk',
            'sqft_median_3bhk': 'avg_sqft_3bhk', 'sqft_median_4bhk': 'avg_sqft_4bhk',
        }
        ward_df = ward_df.rename(columns={k: v for k, v in rename_map.items() if k in ward_df.columns})
        for col in rename_map.values():
            if col not in ward_df.columns:
                ward_df[col] = 0.0
        for bhk in [1, 2, 3, 4]:
            if f'cnt_{bhk}bhk' not in ward_df.columns:
                ward_df[f'cnt_{bhk}bhk'] = 0

        # Backward-compatible aliases
        ward_df['listing_count_1bhk'] = ward_df['cnt_1bhk']
        ward_df['listing_count_3bhk'] = ward_df['cnt_3bhk']

        # ── Percentage of XL 3BHKs (≥ config.YIELD_3BHK_XL_SQFT) ──
        bhk3 = df[df['bhk_type'] == 3]
        if len(bhk3) > 0:
            pct_xl = bhk3.groupby('ward_id').apply(
                lambda g: (g['sqft'].fillna(0) >= config.YIELD_3BHK_XL_SQFT).mean()
            ).reset_index(name='pct_3bhk_xl')
            ward_df = ward_df.merge(pct_xl, on='ward_id', how='left')
            ward_df['pct_3bhk_xl'] = ward_df['pct_3bhk_xl'].fillna(0)
        else:
            ward_df['pct_3bhk_xl'] = 0.0

        bhk_types = len(df['bhk_type'].unique())
        print_detail(f"Aggregated {len(ward_df)} wards across {bhk_types} BHK types")
        return ward_df


def compute_derived_columns(ward_df: pd.DataFrame) -> pd.DataFrame:
    with log_process("Computing derived metrics (SFC, unit economics, sparsity flags)"):
        # ── Data Sparsity Flag ──
        # Flag sparse if it lacks 3BHK raw acquisition supply. 
        # (We relax the 1BHK check because tech parks often naturally lack standalone 1BHKs)
        ward_df['data_sparse'] = (ward_df['cnt_3bhk'] < config.MIN_LISTINGS_PER_BHK)

        # ── Rent Per Sqft ──
        ward_df['rps_1bhk'] = (ward_df['avg_rent_1bhk'] / ward_df['avg_sqft_1bhk']).replace([np.inf, -np.inf], 0).fillna(0)
        ward_df['rps_3bhk'] = (ward_df['avg_rent_3bhk'] / ward_df['avg_sqft_3bhk']).replace([np.inf, -np.inf], 0).fillna(0)

        # ── Small Flat Concentration (SFC) — per spec ──
        total = ward_df['cnt_1bhk'] + ward_df['cnt_2bhk'] + ward_df['cnt_3bhk'] + ward_df['cnt_4bhk']
        small = ward_df['cnt_1bhk'] + ward_df['cnt_2bhk']
        ward_df['sfc'] = (small / total).replace([np.inf, -np.inf], 0).fillna(0)

        sparse_count = ward_df['data_sparse'].sum()
        print_detail(f"{sparse_count} wards flagged data-sparse (< {config.MIN_LISTINGS_PER_BHK} listings for 3BHK supply)")
        return ward_df


def compute_3bhk_quartile_breakdown(df: pd.DataFrame) -> pd.DataFrame:
    """
    Compute average 3BHK rent within each quartile bin per ward.
    Q1 = bottom 25%, Q2 = 25–50%, Q3 = 50–75%, Q4 = top 25%.
    Input: listing-level GeoDataFrame (post-outlier removal, with ward_id).
    """
    with log_process("Computing 3BHK supply price quartile breakdown per ward"):
        bhk3 = df[df['bhk_type'] == 3].copy()
        if len(bhk3) == 0:
            print_detail("No 3BHK listings found — quartile report will be empty")
            return pd.DataFrame()

        print_detail(f"Analysing {len(bhk3):,} 3BHK listings across {bhk3['ward_id'].nunique()} wards")

        def _ward_quartiles(g):
            rents = g['monthly_rent'].dropna().sort_values()
            n = len(rents)
            if n == 0:
                return pd.Series(dtype=float)

            p25 = rents.quantile(0.25)
            p50 = rents.quantile(0.50)
            p75 = rents.quantile(0.75)

            q1 = rents[rents <= p25]
            q2 = rents[(rents > p25) & (rents <= p50)]
            q3 = rents[(rents > p50) & (rents <= p75)]
            q4 = rents[rents > p75]

            q1_avg = q1.mean() if len(q1) > 0 else np.nan
            q2_avg = q2.mean() if len(q2) > 0 else np.nan
            q3_avg = q3.mean() if len(q3) > 0 else np.nan
            q4_avg = q4.mean() if len(q4) > 0 else np.nan

            spread = (q4_avg - q1_avg) if (pd.notna(q4_avg) and pd.notna(q1_avg)) else np.nan

            return pd.Series({
                'total_3bhk_count': n,
                'p25': p25, 'p50': p50, 'p75': p75,
                'q1_count': len(q1), 'q1_avg_rent': q1_avg,
                'q2_count': len(q2), 'q2_avg_rent': q2_avg,
                'q3_count': len(q3), 'q3_avg_rent': q3_avg,
                'q4_count': len(q4), 'q4_avg_rent': q4_avg,
                'spread': spread,
            })

        result = bhk3.groupby('ward_id').apply(_ward_quartiles).reset_index()

        # Flag wards with insufficient data for meaningful quartiles
        result['insufficient_data'] = result['total_3bhk_count'] < 4

        sufficient = (result['insufficient_data'] == False).sum()
        print_detail(f"{sufficient} wards have ≥4 listings (meaningful quartiles)")
        print_detail(f"{result['insufficient_data'].sum()} wards have <4 listings (flagged)")

        return result
