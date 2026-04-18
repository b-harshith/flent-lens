import streamlit as st
import pandas as pd
import json
import plotly.express as px
import os
import subprocess
import time
import sys
import re

# Configure Streamlit page
st.set_page_config(
    page_title="Flent Lens Dashboard",
    page_icon="🏙️",
    layout="wide"
)

# Insert the local modules to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import city_config

st.title("🏙️ Flent Lens Analytics Dashboard")

# ----------------- SIDEBAR -----------------
st.sidebar.header("Pipeline Configuration")

# City selection
city_options = list(city_config.CITY_PROFILES.keys())
current_active_city = city_config.ACTIVE_CITY
default_index = city_options.index(current_active_city) if current_active_city in city_options else 0

selected_city = st.sidebar.selectbox("Select City", city_options, index=default_index)

st.sidebar.markdown("---")
st.sidebar.subheader("Execution Engine")
st.sidebar.caption("Trigger the analytical pipeline. Logs will stream here.")

if st.sidebar.button("🚀 Run Pipeline for Selected City"):
    with st.spinner(f"Running pipeline for {selected_city}..."):
        # We need to change the active city in city_config.py so main runs it correctly
        config_path = os.path.join(BASE_DIR, "city_config.py")
        with open(config_path, "r") as f:
            content = f.read()
        
        # Modify the ACTIVE_CITY constant
        new_content = re.sub(
            r'^ACTIVE_CITY\s*=\s*["\'].*?["\']', 
            f'ACTIVE_CITY = "{selected_city}"', 
            content, 
            flags=re.MULTILINE
        )
        
        with open(config_path, "w") as f:
            f.write(new_content)
        
        # Execute Pipeline
        process = subprocess.Popen(
            [sys.executable, "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=BASE_DIR
        )
        
        log_container = st.sidebar.empty()
        logs = []
        for line in process.stdout:
            logs.append(line.strip())
            # Keep only the last 25 lines to prevent scrolling out of bounds
            if len(logs) > 25:
                logs.pop(0)
            log_container.code("\n".join(logs), language="shell")
            
        process.wait()
        if process.returncode == 0:
            st.sidebar.success("Pipeline completed successfully!")
            st.rerun()  # Reload to show new data
        else:
            st.sidebar.error("Pipeline failed! Check the logs.")

st.sidebar.markdown("---")
st.sidebar.info("Explore the economic metrics derived from the real estate and spatial data overlays.")

# ---------------- MAIN CONTENT ----------------
# Parse paths directly from dictionary so we don't have to reload modules
profile = city_config.CITY_PROFILES[selected_city]
OUTPUT_DIR = os.path.join(BASE_DIR, profile['output_dir'])
GEOJSON_PATH = os.path.join(OUTPUT_DIR, "ward_analysis.geojson")
REPORT_PATH = os.path.join(OUTPUT_DIR, "flent_lens_report.xlsx")
MORAN_PATH = os.path.join(OUTPUT_DIR, "moran_scatterplot_avg_rent_1bhk.png")
OLS_PATH = os.path.join(OUTPUT_DIR, "ols_arbitrage_validation.png")

if not os.path.exists(GEOJSON_PATH):
    st.warning(f"No analytical output found for '{selected_city}'. Please run the pipeline from the sidebar first.")
    st.stop()

# Load Geospatial Data
@st.cache_data
def load_geo_data(path):
    with open(path, 'r') as f:
        geojson = json.load(f)
    
    features = geojson.get('features', [])
    records = []
    for i, f in enumerate(features):
        props = f.get('properties', {})
        if 'id' not in f:
            f['id'] = str(props.get('ward_id', i))
        props['_feature_id'] = f['id']
        records.append(props)
        
    df = pd.DataFrame(records)
    return geojson, df

try:
    raw_geojson, df_geojson = load_geo_data(GEOJSON_PATH)
except Exception as e:
    st.error(f"Failed to load GeoJSON: {e}")
    st.stop()

# 1. KPIs
st.header("Executive Summary")
try:
    total_zones = len(df_geojson)
    viable_zones = int(df_geojson['margin_viable'].sum()) if 'margin_viable' in df_geojson.columns else 0
    best_margin = df_geojson['arb_margin_best'].max() if 'arb_margin_best' in df_geojson.columns else 0
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Zones Evaluated", f"{total_zones:,}")
    col2.metric("Commercially Viable Zones", f"{viable_zones:,}")
    col3.metric("Peak Arb Margin", f"₹{best_margin:,.0f}/mo")
except Exception as e:
    st.error(f"Error calculating KPIs: {e}")

st.markdown("---")

# 2. Map
st.header("🗺️ Geospatial Opportunity Atlas")
try:
    if 'OPP_SCORE' in df_geojson.columns:
        # Determine the best label column for hover tooltips
        hover_name_col = df_geojson.index
        for col in ['ward_name', 'ward_name_x', 'zone_name', 'pincode']:
            if col in df_geojson.columns:
                hover_name_col = col
                break
                
        # Set up hover data safely checking if columns exist
        hover_data = {"OPP_SCORE": ":.1f"}
        if 'avg_rent_1bhk' in df_geojson.columns:
            hover_data['avg_rent_1bhk'] = ":,.0f"
        if 'tier' in df_geojson.columns:
            hover_data['tier'] = True
            
        # Calculate center from bounding box
        bbox = profile['bounding_box']
        center_lat = sum(bbox['lat']) / 2.0
        center_lon = sum(bbox['lon']) / 2.0
        
        fig = px.choropleth_mapbox(
            df_geojson,
            geojson=raw_geojson,
            locations='_feature_id',
            color='OPP_SCORE',
            color_continuous_scale="magma",
            mapbox_style="carto-positron",
            zoom=9 if selected_city == 'bangalore' else 10, 
            center={"lat": center_lat, "lon": center_lon},
            opacity=0.6,
            hover_name=hover_name_col,
            hover_data=hover_data,
            title=f"Opportunity Score Map — {selected_city.capitalize()}"
        )
        fig.update_layout(margin={"r":0,"t":40,"l":0,"b":0})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("OPP_SCORE not found in the spatial dataset.")
except Exception as e:
    st.error(f"Could not render interactive map: {e}")

st.markdown("---")

# 3. Data Explorer
st.header("📊 Feature Subsystem & Economics")
try:
    if os.path.exists(REPORT_PATH):
        # We can try to load "Ward Economics" sheet, fallback to 0 if it doesn't exist
        xl = pd.ExcelFile(REPORT_PATH)
        target_sheet = "Ward Economics" if "Ward Economics" in xl.sheet_names else 0
        df_report = pd.read_excel(REPORT_PATH, sheet_name=target_sheet)
        
        st.dataframe(df_report, use_container_width=True)
        
        # Display Top 10 Arbitrage Zones
        st.subheader("Top Zones by Arbitrage Margin")
        if 'arb_margin_best' in df_report.columns:
            top_arb = df_report.sort_values(by="arb_margin_best", ascending=False).head(10)
            
            display_cols = []
            for preferred in ['ward_name', 'ward_name_x', 'pincode', 'tier', 'avg_rent_1bhk', 'q1_avg_rent', 'arb_margin_best', 'OPP_SCORE']:
                if preferred in top_arb.columns:
                    display_cols.append(preferred)
                    
            st.table(top_arb[display_cols])
    else:
        st.info(f"Excel report not found at: {REPORT_PATH}")
except Exception as e:
    st.error(f"Could not load data tables: {e}")

st.markdown("---")

# 4. Validations
st.header("📈 Econometric Validations")
col_img1, col_img2 = st.columns(2)
if os.path.exists(MORAN_PATH):
    col_img1.image(MORAN_PATH, caption="Moran's I Spatial Autocorrelation", use_container_width=True)
else:
    col_img1.info("Moran's I scatterplot not available. Ensure validation stage succeeded.")

if os.path.exists(OLS_PATH):
    col_img2.image(OLS_PATH, caption="Arbitrage OLS Regression", use_container_width=True)
else:
    col_img2.info("OLS Regression chart not available. Ensure validation stage succeeded.")
