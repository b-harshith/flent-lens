"""
Flent Lens — Econometric Validation
Moran's I spatial autocorrelation and Hedonic OLS regression.
Validates methodology before results are presented.
"""
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns
import os
from src.utils.logger import print_info, print_warning, print_detail, log_process

def run_morans_i(ward_gdf, variable: str, output_dir: str = None) -> dict:
    with log_process(f"Moran's I spatial autocorrelation ({variable})"):
        try:
            from libpysal.weights import Queen
            from esda.moran import Moran

            w = Queen.from_dataframe(ward_gdf, silence_warnings=True)
            w.transform = 'r'
            values = ward_gdf[variable].fillna(ward_gdf[variable].median())
            moran = Moran(values, w)

            result = {
                'variable':  variable,
                'moran_i':   round(moran.I, 4),
                'p_value':   round(moran.p_norm, 4),
                'clustered': moran.I > 0.3 and moran.p_norm < 0.05
            }

            if output_dir:
                # Compute standardized values and spatial lag for scatter
                z   = (values - values.mean()) / values.std()
                lag = pd.Series(w.sparse.dot(z.values), index=z.index)

                fig, ax = plt.subplots(figsize=(10, 7))
                ax.scatter(z, lag, alpha=0.5, s=30, c='#2C3E50',
                           edgecolors='white', linewidth=0.5)

                # Regression line
                b, a = np.polyfit(z, lag, 1)
                x_line = np.linspace(z.min(), z.max(), 100)
                ax.plot(x_line, a + b * x_line, color='#E74C3C',
                        linewidth=2, label=f"Slope = {b:.3f}")

                # Quadrant lines
                ax.axhline(0, color='#7F8C8D', linewidth=0.8, linestyle='--')
                ax.axvline(0, color='#7F8C8D', linewidth=0.8, linestyle='--')

                # Quadrant labels
                ax.text(0.95, 0.95, 'HH', transform=ax.transAxes, fontsize=14,
                        alpha=0.3, ha='right', va='top', fontweight='bold')
                ax.text(0.05, 0.95, 'LH', transform=ax.transAxes, fontsize=14,
                        alpha=0.3, ha='left', va='top', fontweight='bold')
                ax.text(0.05, 0.05, 'LL', transform=ax.transAxes, fontsize=14,
                        alpha=0.3, ha='left', va='bottom', fontweight='bold')
                ax.text(0.95, 0.05, 'HL', transform=ax.transAxes, fontsize=14,
                        alpha=0.3, ha='right', va='bottom', fontweight='bold')

                ax.set_title(
                    f"Moran's I Scatterplot: {variable}\n"
                    f"I = {result['moran_i']}  |  p = {result['p_value']}",
                    fontsize=13, fontweight='bold', pad=15
                )
                ax.set_xlabel("Standardized Variable (z-score)", fontsize=11)
                ax.set_ylabel("Spatial Lag (z-score)", fontsize=11)
                ax.legend(loc='lower right', fontsize=10)
                ax.grid(True, alpha=0.2)

                plt.tight_layout()
                path = os.path.join(output_dir, f"moran_scatterplot_{variable}.png")
                plt.savefig(path, dpi=150, bbox_inches='tight')
                plt.close()
                print_detail(f"Moran scatter → {os.path.basename(path)}")

            tag = "[success]SPATIALLY CLUSTERED[/]" if result['clustered'] else "[warning]SPATIALLY RANDOM[/]"
            print_info(f"Moran's I = {result['moran_i']} (p={result['p_value']}) → {tag}")
            return result

        except Exception as e:
            print_warning(f"Moran's I failed: {e}")
            return {}


def run_arbitrage_ols(ward_df: pd.DataFrame, output_dir: str = None):
    with log_process("Arbitrage Structural OLS (Acquisition_3BHK ~ Retail_1BHK)"):
        try:
            import statsmodels.api as sm

            # Filter valid 1BHK and 3BHK data
            df = ward_df[(ward_df['avg_rent_1bhk'] > 0) & (ward_df['avg_rent_3bhk'] > 0)].copy()
            df['rent_1bhk'] = pd.to_numeric(df['avg_rent_1bhk'], errors='coerce')
            df['rent_3bhk'] = pd.to_numeric(df['avg_rent_3bhk'], errors='coerce')
            df = df.dropna(subset=['rent_1bhk', 'rent_3bhk'])
            df = df[(df['rent_1bhk'] > 0) & (df['rent_3bhk'] > 0)]

            if len(df) < 5:
                print_warning("Not enough data points for OLS.")
                return None

            X = df['rent_1bhk']
            X = sm.add_constant(X)
            y = df['rent_3bhk']

            model = sm.OLS(y, X).fit(cov_type='HC3')
            beta = model.params['rent_1bhk']
            
            # The implied cost per room based purely on market correlation (assuming 3 rooms derived from 3BHK)
            breakeven_discount = beta / 3.0

            if output_dir:
                # ── Plot 1: Arbitrage Structural Baseline ──
                fig, ax = plt.subplots(figsize=(9, 6))
                ax.scatter(df['rent_1bhk'], df['rent_3bhk'], alpha=0.6, s=35, c='#2C3E50', edgecolors='white', linewidth=0.5)
                
                # Regression line
                x_line = np.linspace(df['rent_1bhk'].min(), df['rent_1bhk'].max(), 100)
                y_line = model.params['const'] + beta * x_line
                ax.plot(x_line, y_line, color='#E74C3C', linewidth=2.5, 
                        label=f'Cost Multiplier (β) = {beta:.2f}x')
                
                ax.set_title(
                    f"Structural Arbitrage Validity (R² = {model.rsquared:.3f})\n"
                    f"Implied Breakeven Demand Discount Min: {breakeven_discount:.2f}",
                    fontsize=13, fontweight='bold', pad=15
                )
                
                ax.set_xlabel("Retail Revenue: 1BHK Median Rent (₹)", fontsize=11)
                ax.set_ylabel("Acquisition Cost: 3BHK 25th Percentile Rent (₹)", fontsize=11)
                
                ax.legend(loc='upper left', fontsize=11)
                ax.grid(True, alpha=0.2, linestyle='--')
                plt.tight_layout()
                plt.savefig(os.path.join(output_dir, "ols_arbitrage_validation.png"), dpi=150, bbox_inches='tight')
                plt.close()
                print_detail("Arbitrage OLS plot generated")

            print_info(f"Target Market Mult (β) = {beta:.2f}x | Arbitrage R² = [highlight]{model.rsquared:.4f}[/]")
            print_detail(f"Implied Breakeven Demand Discount Factor (3 Rooms): {breakeven_discount:.2f}")

            import config
            if hasattr(config, 'DEMAND_DISCOUNT_FACTOR'):
                if config.DEMAND_DISCOUNT_FACTOR >= breakeven_discount:
                    print_info(f"Arbitrage structurally PROVEN. Operational DDF {config.DEMAND_DISCOUNT_FACTOR} > Minimum {breakeven_discount:.2f}")
                else:
                    print_warning(f"Arbitrage FAILS structurally. Operational DDF {config.DEMAND_DISCOUNT_FACTOR} < Minimum {breakeven_discount:.2f}")

            return model

        except Exception as e:
            print_warning(f"Arbitrage OLS failed: {e}")
            return None
