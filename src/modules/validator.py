"""
Flent Lens 2.0 — Spatial Econometric Validation (SAR/SEM + Moran's I)
Replaces naive OLS with spatial autoregressive models using PySAL spreg.
"""
import os, json
import numpy as np
import pandas as pd
import geopandas as gpd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import config
from src.utils.logger import print_info, print_detail, print_warning, print_success, log_process


def _build_spatial_weights(hex_df):
    """Build KNN spatial weights (k=6, natural for hexagons)."""
    from libpysal.weights import KNN
    gdf = gpd.GeoDataFrame(hex_df, geometry=gpd.points_from_xy(
        hex_df['centroid_lon'], hex_df['centroid_lat']), crs=config.CRS_GEOGRAPHIC)
    w = KNN.from_dataframe(gdf, k=config.SAR_KNN)
    w.transform = 'r'  # Row-standardize
    return w, gdf


def run_moran(hex_df):
    """Moran's I with permutation-based inference."""
    with log_process("Computing Moran's I (999 permutations)"):
        from esda.moran import Moran
        valid = hex_df[hex_df['avg_rent_1bhk'].notna() & (hex_df['confidence'] != 'data_insufficient')].copy()
        if len(valid) < 10:
            print_warning("Too few valid hexes for Moran's I")
            return None, None

        w, gdf = _build_spatial_weights(valid)
        y = valid['avg_rent_1bhk'].values
        moran = Moran(y, w, permutations=config.MORAN_PERMUTATIONS)

        print_info(f"Moran's I = [highlight]{moran.I:.4f}[/highlight] "
                   f"(p={moran.p_sim:.4f}, z={moran.z_sim:.2f})")
        sig = "✅ Significant" if moran.p_sim < 0.05 else "⚠️ Not significant"
        print_detail(f"Spatial autocorrelation: {sig} at 5% level")
        return moran, valid


def run_ols(hex_df):
    """Baseline OLS: Q1_3BHK ~ Median_1BHK (with HC3 robust SEs)."""
    with log_process("Running OLS baseline regression"):
        import statsmodels.api as sm
        valid = hex_df[
            hex_df['avg_rent_1bhk'].notna() &
            hex_df['q1_rent_3bhk_apt'].notna() &
            (hex_df['confidence'] != 'data_insufficient')
        ].copy()

        if len(valid) < 10:
            print_warning("Too few valid hexes for OLS")
            return None, None

        y = valid['q1_rent_3bhk_apt'].values
        X = sm.add_constant(valid['avg_rent_1bhk'].values)
        model = sm.OLS(y, X).fit(cov_type='HC3')

        beta = model.params[1]
        breakeven = beta / 3.0
        print_info(f"OLS β = {beta:.3f} | R² = {model.rsquared:.4f}")
        print_detail(f"Breakeven DDF = {breakeven:.3f} ({breakeven*100:.1f}%)")
        print_detail(f"Flent DDF = {config.DDF_APARTMENT:.2f} → "
                     f"{'✅ PROVEN' if config.DDF_APARTMENT >= breakeven else '⚠️ REVIEW'}")
        return model, valid


def run_sar(hex_df):
    """Spatial Autoregressive (Lag) Model using spreg."""
    with log_process("Running SAR Spatial Lag Model"):
        try:
            from spreg import GM_Lag
        except ImportError:
            print_warning("spreg not available — skipping SAR")
            return None

        valid = hex_df[
            hex_df['avg_rent_1bhk'].notna() &
            hex_df['q1_rent_3bhk_apt'].notna() &
            (hex_df['confidence'] != 'data_insufficient')
        ].copy()

        if len(valid) < 15:
            print_warning("Too few hexes for SAR model")
            return None

        w, gdf = _build_spatial_weights(valid)
        y = valid['q1_rent_3bhk_apt'].values.reshape(-1, 1)
        X = valid[['avg_rent_1bhk']].values

        try:
            sar = GM_Lag(y, X, w=w, name_y='Q1_3BHK_Rent', name_x=['Median_1BHK_Rent'])
            rho = sar.betas[-1][0]  # Spatial lag coefficient
            beta_sar = sar.betas[1][0]
            print_info(f"SAR: β={beta_sar:.3f}, ρ(spatial lag)={rho:.3f}")
            print_detail(f"SAR pseudo-R²: {sar.pr2:.4f}")
            return sar
        except Exception as e:
            print_warning(f"SAR failed: {e}")
            return None


def save_moran_plot(moran, valid_df, output_dir=None):
    """Save Moran scatterplot."""
    if moran is None: return None
    from esda.moran import Moran
    output_dir = output_dir or config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(1, 1, figsize=(8, 8))
    w, _ = _build_spatial_weights(valid_df)
    y = valid_df['avg_rent_1bhk'].values
    y_std = (y - y.mean()) / y.std()
    wy_std = w.sparse.dot(y_std)

    colors = []
    for yi, wyi in zip(y_std, wy_std):
        if yi > 0 and wyi > 0: colors.append('#22c55e')    # HH
        elif yi < 0 and wyi < 0: colors.append('#3b82f6')  # LL
        elif yi < 0 and wyi > 0: colors.append('#f59e0b')  # LH — arbitrage
        else: colors.append('#ef4444')                       # HL

    ax.scatter(y_std, wy_std, c=colors, alpha=0.6, s=40, edgecolors='white', linewidths=0.5)
    ax.axhline(0, color='#334155', lw=0.8, ls='--')
    ax.axvline(0, color='#334155', lw=0.8, ls='--')

    # Best fit line
    z = np.polyfit(y_std, wy_std, 1)
    p = np.poly1d(z)
    xr = np.linspace(y_std.min(), y_std.max(), 100)
    ax.plot(xr, p(xr), color='#0f172a', lw=2)

    q_labels = {'HH': (0.7, 0.7), 'LL': (-0.7, -0.7), 'LH': (-0.7, 0.7), 'HL': (0.7, -0.7)}
    for label, (x, y_pos) in q_labels.items():
        ax.text(x * ax.get_xlim()[1], y_pos * ax.get_ylim()[1], label,
                fontsize=14, fontweight='bold', alpha=0.3, ha='center', va='center')

    ax.set_xlabel('Standardized 1BHK Rent (Hex)', fontsize=12)
    ax.set_ylabel('Spatial Lag (Neighbor Avg)', fontsize=12)
    ax.set_title(f"Moran's I = {moran.I:.4f} (p = {moran.p_sim:.4f}) — {config.CITY_NAME}",
                 fontsize=14, fontweight='bold')
    plt.tight_layout()
    path = os.path.join(output_dir, 'moran_scatterplot.png')
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print_success(f"Moran plot → {os.path.basename(path)}")
    return path


def save_ols_plot(model, valid_df, output_dir=None):
    """Save OLS regression plot."""
    if model is None: return None
    output_dir = output_dir or config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)

    fig, ax = plt.subplots(figsize=(10, 7))
    x = valid_df['avg_rent_1bhk'].values
    y = valid_df['q1_rent_3bhk_apt'].values
    tiers = valid_df.get('tier', pd.Series('Unknown', index=valid_df.index))

    tier_colors = {'Tier 1': '#22c55e', 'Tier 2': '#f59e0b', 'Tier 3': '#ef4444', 'Excluded': '#94a3b8'}
    for tier_name, color in tier_colors.items():
        mask = tiers == tier_name
        if mask.any():
            ax.scatter(x[mask], y[mask], c=color, label=tier_name, alpha=0.6, s=50, edgecolors='white')

    # Regression line
    xr = np.linspace(x.min(), x.max(), 100)
    ax.plot(xr, model.predict(np.column_stack([np.ones(100), xr])),
            color='#0f172a', lw=2.5, label=f'OLS (β={model.params[1]:.3f}, R²={model.rsquared:.3f})')

    # Breakeven line
    breakeven = model.params[1] / 3.0
    ax.axhline(y=0, color='#64748b', ls='--', lw=0.5)

    ax.set_xlabel('Median 1BHK Rent (₹)', fontsize=12)
    ax.set_ylabel('Q1 3BHK Acquisition Cost (₹)', fontsize=12)
    ax.set_title(f'Arbitrage Structural Validation — {config.CITY_NAME}', fontsize=14, fontweight='bold')
    ax.legend(framealpha=0.9)
    plt.tight_layout()
    path = os.path.join(output_dir, 'ols_arbitrage_validation.png')
    fig.savefig(path, dpi=200, bbox_inches='tight')
    plt.close(fig)
    print_success(f"OLS plot → {os.path.basename(path)}")
    return path


def save_regression_comparison(ols_model, sar_model, output_dir=None):
    """Save side-by-side regression comparison to Excel."""
    output_dir = output_dir or config.OUTPUT_DIR
    os.makedirs(output_dir, exist_ok=True)
    rows = []
    if ols_model:
        rows.append({
            'Model': 'OLS (HC3)', 'Intercept': ols_model.params[0],
            'Beta_1BHK': ols_model.params[1], 'SE_Beta': ols_model.bse[1],
            'p_value': ols_model.pvalues[1], 'R_squared': ols_model.rsquared,
            'N_obs': int(ols_model.nobs), 'AIC': ols_model.aic
        })
    if sar_model:
        rows.append({
            'Model': 'SAR (Spatial Lag)', 'Intercept': sar_model.betas[0][0],
            'Beta_1BHK': sar_model.betas[1][0], 'SE_Beta': sar_model.std_err[1],
            'p_value': sar_model.z_stat[1][1], 'R_squared': sar_model.pr2,
            'N_obs': sar_model.n, 'AIC': 'N/A',
            'Rho_spatial': sar_model.betas[-1][0]
        })
    if rows:
        pd.DataFrame(rows).to_excel(
            os.path.join(output_dir, 'regression_comparison.xlsx'), index=False)
