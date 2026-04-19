import os
import json
import pandas as pd
import re

base_dir = "/Users/malleswararao/Desktop/Harshith files/BBA_Python_final/output"
cities = [d for d in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, d)) and d not in ['cross_city', '__pycache__']]

results = []

for city in cities:
    city_path = os.path.join(base_dir, city)
    summary_path = os.path.join(city_path, "city_summary.json")
    report_path = os.path.join(city_path, "flent_lens_report.xlsx")
    
    data = {
        "city": city.capitalize(),
        "moran_i": None,
        "ols_beta": None,
        "ols_r2": None,
        "breakeven_ddf": None,
        "total_listings": 0,
        "viable_hexes": 0,
        "median_margin": 0,
        "clustered": "Unknown"
    }
    
    # Read JSON summary
    if os.path.exists(summary_path):
        with open(summary_path, 'r') as f:
            summary = json.load(f)
            data["total_listings"] = summary.get("total_listings", 0)
            data["viable_hexes"] = summary.get("viable_hexes", 0)
            data["median_margin"] = summary.get("median_arb_margin", 0)
            data["moran_i"] = summary.get("moran_i")
            data["ols_beta"] = summary.get("ols_slope")
            data["ols_r2"] = summary.get("ols_r2")
    
    # Read Excel for Breakeven DDF and more accurate stats if available
    if os.path.exists(report_path):
        try:
            ols_df = pd.read_excel(report_path, sheet_name='📐 OLS Evidence')
            # Extract Breakeven DDF
            # Find the row where first column contains "Breakeven Demand Discount Min"
            for i, row in ols_df.iterrows():
                label = str(row.iloc[0])
                if "Breakeven Demand Discount Min" in label:
                    val = str(row.iloc[1])
                    # Extract numeric value
                    import re
                    m = re.search(r"(\d+\.\d+)", val)
                    if m:
                        data["breakeven_ddf"] = float(m.group(1))
                if "Clustered?" in label:
                    data["clustered"] = str(row.iloc[1])
                if "1BHK Cost Multiplier (β)" in label:
                    val = str(row.iloc[1])
                    m = re.search(r"(\d+\.\d+)", val.replace('x',''))
                    if m:
                        data["ols_beta"] = float(m.group(1))
                if "R² (Fit Quality)" in label:
                    val = str(row.iloc[1])
                    m = re.search(r"(\d+\.\d+)", val)
                    if m:
                        data["ols_r2"] = float(m.group(1))
                if "Moran's I Index" in label:
                    val = str(row.iloc[1])
                    m = re.search(r"(-?\d+\.\d+)", val)
                    if m:
                        data["moran_i"] = float(m.group(1))
        except Exception as e:
            print(f"Error reading Excel for {city}: {e}")
            
    results.append(data)

print(json.dumps(results, indent=2))
