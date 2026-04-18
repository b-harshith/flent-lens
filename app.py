"""
Flent Lens — Interactive Analytics Dashboard
A premium Streamlit UI for exploring multi-city real estate arbitrage insights.
"""
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os
import subprocess
import sys
import re
import numpy as np

# ═══════════════════════════════════════════════════════════════════
# PAGE CONFIG & THEME
# ═══════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Flent Lens — Market Intelligence",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

import city_config

# ═══════════════════════════════════════════════════════════════════
# PREMIUM CSS INJECTION
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* Global */
    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .stApp {
        background: linear-gradient(135deg, #0a0a0f 0%, #111827 50%, #0f172a 100%);
    }
    .stApp > header { background: transparent; }

    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111827 0%, #1e1b4b 100%);
        border-right: 1px solid rgba(99, 102, 241, 0.15);
    }
    section[data-testid="stSidebar"] .stMarkdown p,
    section[data-testid="stSidebar"] .stMarkdown li,
    section[data-testid="stSidebar"] label {
        color: #c7d2fe !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #e0e7ff !important;
    }

    /* Main content overrides */
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3 { color: #e0e7ff; }
    .stMarkdown p, .stMarkdown li { color: #94a3b8; }

    /* Metric Cards */
    div[data-testid="stMetric"] {
        background: linear-gradient(135deg, rgba(99, 102, 241, 0.08), rgba(139, 92, 246, 0.06));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 16px;
        padding: 20px 24px;
        backdrop-filter: blur(12px);
        transition: all 0.3s ease;
    }
    div[data-testid="stMetric"]:hover {
        border-color: rgba(99, 102, 241, 0.5);
        box-shadow: 0 8px 32px rgba(99, 102, 241, 0.15);
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] label {
        color: #818cf8 !important;
        font-weight: 600;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #f1f5f9 !important;
        font-weight: 700;
    }
    div[data-testid="stMetric"] [data-testid="stMetricDelta"] {
        color: #34d399 !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: rgba(30, 27, 75, 0.5);
        border-radius: 12px;
        padding: 4px;
        border: 1px solid rgba(99, 102, 241, 0.15);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        color: #94a3b8;
        font-weight: 500;
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #4f46e5, #7c3aed) !important;
        color: #ffffff !important;
        font-weight: 600;
    }

    /* Dataframe styling */
    .stDataFrame { border-radius: 12px; overflow: hidden; }

    /* Custom card class */
    .insight-card {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.6), rgba(17, 24, 39, 0.8));
        border: 1px solid rgba(99, 102, 241, 0.15);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 16px;
        backdrop-filter: blur(12px);
    }
    .insight-card h4 {
        color: #c7d2fe;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 12px;
        font-weight: 700;
    }
    .insight-card .value {
        color: #f1f5f9;
        font-size: 2rem;
        font-weight: 800;
        line-height: 1.1;
    }
    .insight-card .subtitle {
        color: #64748b;
        font-size: 0.8rem;
        margin-top: 6px;
    }

    /* Hero Header */
    .hero-header {
        background: linear-gradient(135deg, rgba(79, 70, 229, 0.12), rgba(124, 58, 237, 0.08));
        border: 1px solid rgba(99, 102, 241, 0.2);
        border-radius: 20px;
        padding: 32px 40px;
        margin-bottom: 32px;
        position: relative;
        overflow: hidden;
    }
    .hero-header::before {
        content: '';
        position: absolute;
        top: -50%;
        right: -20%;
        width: 400px;
        height: 400px;
        background: radial-gradient(circle, rgba(99, 102, 241, 0.08) 0%, transparent 70%);
        pointer-events: none;
    }
    .hero-header h1 {
        background: linear-gradient(135deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.2rem;
        font-weight: 900;
        letter-spacing: -0.02em;
        margin-bottom: 4px;
    }
    .hero-header .tagline {
        color: #94a3b8;
        font-size: 1rem;
        font-weight: 400;
    }

    /* Tier badges */
    .tier-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .tier-1 { background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }
    .tier-2 { background: rgba(245, 158, 11, 0.15); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.3); }
    .tier-3 { background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }
    .tier-ex { background: rgba(100, 116, 139, 0.15); color: #94a3b8; border: 1px solid rgba(100, 116, 139, 0.3); }

    /* Section separator */
    .section-sep {
        height: 1px;
        background: linear-gradient(90deg, transparent, rgba(99, 102, 241, 0.3), transparent);
        margin: 40px 0;
    }

    /* OLS explanation grid */
    .ols-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 16px;
    }
    .ols-item {
        background: rgba(30, 27, 75, 0.4);
        border: 1px solid rgba(99, 102, 241, 0.12);
        border-radius: 12px;
        padding: 16px 20px;
    }
    .ols-item .ols-label {
        color: #818cf8;
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 6px;
    }
    .ols-item .ols-val {
        color: #f1f5f9;
        font-size: 1.3rem;
        font-weight: 800;
    }
    .ols-item .ols-desc {
        color: #64748b;
        font-size: 0.78rem;
        margin-top: 8px;
        line-height: 1.5;
    }

    /* Hide default Streamlit branding */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header[data-testid="stHeader"] {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# DATA LOADING HELPERS
# ═══════════════════════════════════════════════════════════════════
@st.cache_data
def load_geojson(path):
    with open(path, 'r') as f:
        geojson = json.load(f)
    features = geojson.get('features', [])
    records = []
    for i, feat in enumerate(features):
        props = feat.get('properties', {})
        fid = str(props.get('ward_id', i))
        if 'id' not in feat:
            feat['id'] = fid
        else:
            feat['id'] = str(feat['id'])
        props['_feature_id'] = feat['id']
        records.append(props)
    df = pd.DataFrame(records)
    # Clean numeric columns
    for col in df.columns:
        if col not in ['_feature_id', 'ward_name_x', 'ward_name_y', 'zone_name_x',
                        'zone_name_y', 'closest_sezs', 'aura_sources', 'tier', 'data_sparse']:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return geojson, df


@st.cache_data
def load_excel_report(path):
    xl = pd.ExcelFile(path)
    sheets = {}
    for name in xl.sheet_names:
        sheets[name] = pd.read_excel(xl, sheet_name=name)
    return sheets


@st.cache_data
def load_ols_evidence(path):
    try:
        df = pd.read_excel(path, sheet_name='📐 OLS Evidence')
        col_a = df.columns[0]
        col_b = df.columns[1]
        data = {}
        for _, row in df.iterrows():
            key = str(row[col_a]).strip() if pd.notna(row[col_a]) else ''
            val = str(row[col_b]).strip() if pd.notna(row[col_b]) else ''
            if key:
                data[key] = val
        return data
    except Exception:
        return {}


def get_city_outputs(city_key):
    """Return all output paths for a given city."""
    profile = city_config.CITY_PROFILES[city_key]
    out_dir = os.path.join(BASE_DIR, profile['output_dir'])
    return {
        'geojson': os.path.join(out_dir, 'ward_analysis.geojson'),
        'report': os.path.join(out_dir, 'flent_lens_report.xlsx'),
        'quartiles': os.path.join(out_dir, '3bhk_supply_price_quartiles.xlsx'),
        'moran': os.path.join(out_dir, 'moran_scatterplot_avg_rent_1bhk.png'),
        'ols_plot': os.path.join(out_dir, 'ols_arbitrage_validation.png'),
        'output_dir': out_dir,
        'profile': profile,
    }


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔬 Flent Lens")
    st.caption("Real Estate Arbitrage Intelligence Platform")
    st.markdown("---")

    city_options = list(city_config.CITY_PROFILES.keys())
    city_labels = [city_config.CITY_PROFILES[c]['city_name'] for c in city_options]
    selected_idx = st.selectbox(
        "🏙️ Select City",
        range(len(city_options)),
        format_func=lambda i: city_labels[i],
        index=0,
    )
    selected_city = city_options[selected_idx]
    profile = city_config.CITY_PROFILES[selected_city]

    st.markdown("---")
    st.markdown("##### ⚙️ Pipeline Control")

    if st.button("🚀 Execute Pipeline", use_container_width=True, type="primary"):
        config_path = os.path.join(BASE_DIR, "city_config.py")
        with open(config_path, "r") as f:
            content = f.read()
        new_content = re.sub(
            r'^ACTIVE_CITY\s*=\s*["\'].*?["\']',
            f'ACTIVE_CITY = "{selected_city}"',
            content,
            flags=re.MULTILINE
        )
        with open(config_path, "w") as f:
            f.write(new_content)

        with st.status(f"Running pipeline for {profile['city_name']}...", expanded=True) as status:
            process = subprocess.Popen(
                [sys.executable, "main.py"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                cwd=BASE_DIR
            )
            log_area = st.empty()
            logs = []
            for line in process.stdout:
                cleaned = line.strip()
                if cleaned:
                    logs.append(cleaned)
                    if len(logs) > 30:
                        logs.pop(0)
                    log_area.code("\n".join(logs), language="shell")

            process.wait()
            if process.returncode == 0:
                status.update(label="✅ Pipeline completed!", state="complete")
                st.success("Done! Reloading dashboard...")
                st.rerun()
            else:
                status.update(label="❌ Pipeline failed", state="error")
                st.error("Check logs above.")

    st.markdown("---")
    st.markdown("##### 📋 City Profile")
    st.markdown(f"**Geo Unit:** {profile['geo_unit_label']}")
    st.markdown(f"**CRS:** {profile['crs_projected']}")
    st.markdown(f"**Transit Data:** {'✅' if profile['has_transit'] else '❌'}")
    st.markdown(f"**SEZ Data:** {'✅' if profile['has_sez'] else '❌'}")


# ═══════════════════════════════════════════════════════════════════
# MAIN CONTENT — Load Data
# ═══════════════════════════════════════════════════════════════════
paths = get_city_outputs(selected_city)

if not os.path.exists(paths['geojson']):
    st.markdown("""
    <div class="hero-header">
        <h1>Flent Lens</h1>
        <div class="tagline">No analytical output found for this city. Use the sidebar to run the pipeline first.</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

raw_geojson, df = load_geojson(paths['geojson'])

# Ensure clean ward_name column
if 'ward_name' not in df.columns:
    if 'ward_name_x' in df.columns:
        df['ward_name'] = df['ward_name_x']
    elif 'ward_name_y' in df.columns:
        df['ward_name'] = df['ward_name_y']
    else:
        df['ward_name'] = df['ward_id'].astype(str)

# Load supplementary data
report_sheets = load_excel_report(paths['report']) if os.path.exists(paths['report']) else {}
ols_data = load_ols_evidence(paths['report']) if os.path.exists(paths['report']) else {}

city_name = profile['city_name']
geo_label = profile['geo_unit_label']


# ═══════════════════════════════════════════════════════════════════
# HERO HEADER
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"""
<div class="hero-header">
    <h1>Flent Lens — {city_name}</h1>
    <div class="tagline">Multi-dimensional opportunity scoring across {len(df)} {geo_label}s · Arbitrage · Demand · Supply · Spatial Overlay</div>
</div>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# KPI ROW
# ═══════════════════════════════════════════════════════════════════
total_zones = len(df)
tier_counts = df['tier'].value_counts().to_dict() if 'tier' in df.columns else {}
t1 = tier_counts.get('Tier 1', 0)
t2 = tier_counts.get('Tier 2', 0)
t3 = tier_counts.get('Tier 3', 0)
excluded = tier_counts.get('Excluded', 0)
viable = int(df['margin_viable'].sum()) if 'margin_viable' in df.columns else 0
peak_margin = df['arb_margin_best'].max() if 'arb_margin_best' in df.columns else 0
avg_score = df['OPP_SCORE'].mean() if 'OPP_SCORE' in df.columns else 0
median_1bhk = df.loc[df['avg_rent_1bhk'] > 0, 'avg_rent_1bhk'].median() if 'avg_rent_1bhk' in df.columns else 0

c1, c2, c3, c4, c5, c6 = st.columns(6)
c1.metric("Total Zones", f"{total_zones}")
c2.metric("Tier 1 (Elite)", f"{t1}", delta=f"{t1/total_zones*100:.0f}% of total")
c3.metric("Viable Zones", f"{viable}", delta=f"margin > 5%")
c4.metric("Peak Arb Margin", f"₹{peak_margin:,.0f}/mo")
c5.metric("Avg Opp Score", f"{avg_score:.1f}")
c6.metric("Median 1BHK Rent", f"₹{median_1bhk:,.0f}")


# ═══════════════════════════════════════════════════════════════════
# TAB LAYOUT
# ═══════════════════════════════════════════════════════════════════
tab_map, tab_econ, tab_supply, tab_scoring, tab_validation, tab_data = st.tabs([
    "🗺️ Opportunity Atlas",
    "💰 Arbitrage Economics",
    "📦 Supply & Demand",
    "📊 Scoring Breakdown",
    "📐 Econometric Validation",
    "📋 Raw Data Explorer"
])


# ─────────────────────────────────────────────────────────────────
# TAB 1: INTERACTIVE MAP
# ─────────────────────────────────────────────────────────────────
with tab_map:
    st.markdown("### Geospatial Opportunity Atlas")
    st.caption("Interactive choropleth showing composite Opportunity Score across all zones. Hover for details.")

    map_color = st.selectbox(
        "Color by",
        ['OPP_SCORE', 'arb_margin_best', 'demand_intensity_idx', 'supply_depth_idx', 'transit_score', 'sez_employment_score'],
        index=0,
        key="map_color_metric",
    )

    bbox = profile['bounding_box']
    center_lat = sum(bbox['lat']) / 2
    center_lon = sum(bbox['lon']) / 2

    # Build hover data
    hover_cols = {'OPP_SCORE': ':.1f', 'arb_margin_best': ':,.0f', 'tier': True}
    if 'avg_rent_1bhk' in df.columns:
        hover_cols['avg_rent_1bhk'] = ':,.0f'
    if 'avg_rent_3bhk' in df.columns:
        hover_cols['avg_rent_3bhk'] = ':,.0f'

    fig_map = px.choropleth_mapbox(
        df,
        geojson=raw_geojson,
        locations='_feature_id',
        color=map_color,
        color_continuous_scale='Viridis',
        mapbox_style='carto-darkmatter',
        zoom=10 if selected_city == 'hyderabad' else 9,
        center={"lat": center_lat, "lon": center_lon},
        opacity=0.7,
        hover_name='ward_name',
        hover_data=hover_cols,
    )
    fig_map.update_layout(
        margin={"r": 0, "t": 0, "l": 0, "b": 0},
        height=620,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(family="Inter", color="#e0e7ff"),
        coloraxis_colorbar=dict(
            title=dict(text=map_color.replace('_', ' ').title(), font=dict(color='#c7d2fe')),
            tickfont=dict(color='#94a3b8'),
            bgcolor='rgba(17,24,39,0.8)',
            bordercolor='rgba(99,102,241,0.3)',
            borderwidth=1,
        )
    )
    st.plotly_chart(fig_map, use_container_width=True)

    # Tier distribution mini-bar beneath the map
    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)
    col_a, col_b = st.columns([1, 2])
    with col_a:
        st.markdown("#### Tier Distribution")
        tier_df = pd.DataFrame({
            'Tier': ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded'],
            'Count': [t1, t2, t3, excluded]
        })
        tier_colors = {'Tier 1': '#10b981', 'Tier 2': '#f59e0b', 'Tier 3': '#ef4444', 'Excluded': '#475569'}
        fig_tier = px.bar(
            tier_df, x='Tier', y='Count', color='Tier',
            color_discrete_map=tier_colors,
            text='Count',
        )
        fig_tier.update_traces(textposition='outside', textfont=dict(color='#e0e7ff', size=14, family='Inter'))
        fig_tier.update_layout(
            showlegend=False,
            height=300,
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter", color="#94a3b8"),
            xaxis=dict(gridcolor='rgba(99,102,241,0.08)'),
            yaxis=dict(gridcolor='rgba(99,102,241,0.08)', title=''),
            margin=dict(l=20, r=20, t=20, b=40),
        )
        st.plotly_chart(fig_tier, use_container_width=True)

    with col_b:
        st.markdown("#### Top 10 Opportunity Zones")
        top10 = df.nlargest(10, 'OPP_SCORE')[['ward_name', 'tier', 'OPP_SCORE', 'arb_margin_best', 'avg_rent_1bhk']].copy()
        top10.insert(0, 'Rank', range(1, len(top10) + 1))
        top10.columns = ['Rank', 'Zone', 'Tier', 'Score', 'Best Margin (₹)', '1BHK Rent (₹)']
        st.dataframe(
            top10.style.format({'Score': '{:.1f}', 'Best Margin (₹)': '₹{:,.0f}', '1BHK Rent (₹)': '₹{:,.0f}'}),
            use_container_width=True,
            hide_index=True,
            height=380,
        )


# ─────────────────────────────────────────────────────────────────
# TAB 2: ARBITRAGE ECONOMICS
# ─────────────────────────────────────────────────────────────────
with tab_econ:
    st.markdown("### 💰 Arbitrage Economics Deep Dive")
    st.caption("The core business thesis — how Flent's room-splitting model creates margin from pricing inefficiency.")

    ec1, ec2, ec3, ec4 = st.columns(4)
    avg_margin = df.loc[df['arb_margin_best'] > 0, 'arb_margin_best'].mean() if 'arb_margin_best' in df.columns else 0
    median_3bhk = df.loc[df['avg_rent_3bhk'] > 0, 'avg_rent_3bhk'].median() if 'avg_rent_3bhk' in df.columns else 0
    avg_discount = df['demand_discount'].mean() * 100 if 'demand_discount' in df.columns else 0

    ec1.metric("Avg Arbitrage Margin", f"₹{avg_margin:,.0f}/mo", delta="across viable zones")
    ec2.metric("Median 3BHK Acq Cost", f"₹{median_3bhk:,.0f}/mo")
    ec3.metric("Avg Demand Discount", f"{avg_discount:.1f}%", delta="applied to room pricing")
    ec4.metric("Margin-Viable Zones", f"{viable} / {total_zones}")

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # Margin Distribution Histogram
    col_hist, col_scatter = st.columns(2)
    with col_hist:
        st.markdown("#### Margin Distribution")
        viable_df = df[df['arb_margin_best'] > 0].copy()
        if len(viable_df) > 0:
            fig_hist = px.histogram(
                viable_df, x='arb_margin_best', nbins=30,
                labels={'arb_margin_best': 'Best Arbitrage Margin (₹/month)'},
                color_discrete_sequence=['#818cf8'],
            )
            fig_hist.update_layout(
                height=380,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter", color="#94a3b8"),
                xaxis=dict(gridcolor='rgba(99,102,241,0.08)', title_font=dict(color='#c7d2fe')),
                yaxis=dict(gridcolor='rgba(99,102,241,0.08)', title='Count', title_font=dict(color='#c7d2fe')),
                margin=dict(l=40, r=20, t=20, b=40),
            )
            st.plotly_chart(fig_hist, use_container_width=True)
        else:
            st.info("No viable margin zones found.")

    with col_scatter:
        st.markdown("#### 1BHK Rent vs Arbitrage Margin")
        plot_df = df[(df['avg_rent_1bhk'] > 0) & (df['arb_margin_best'] > 0)].copy()
        if len(plot_df) > 0:
            fig_sc = px.scatter(
                plot_df, x='avg_rent_1bhk', y='arb_margin_best',
                color='tier',
                color_discrete_map={'Tier 1': '#10b981', 'Tier 2': '#f59e0b', 'Tier 3': '#ef4444', 'Excluded': '#475569'},
                hover_name='ward_name',
                labels={'avg_rent_1bhk': '1BHK Retail Rent (₹)', 'arb_margin_best': 'Best Arb Margin (₹)'},
                size='OPP_SCORE',
                size_max=18,
            )
            fig_sc.update_layout(
                height=380,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter", color="#94a3b8"),
                xaxis=dict(gridcolor='rgba(99,102,241,0.08)', title_font=dict(color='#c7d2fe')),
                yaxis=dict(gridcolor='rgba(99,102,241,0.08)', title_font=dict(color='#c7d2fe')),
                legend=dict(font=dict(color='#c7d2fe')),
                margin=dict(l=40, r=20, t=20, b=40),
            )
            st.plotly_chart(fig_sc, use_container_width=True)
        else:
            st.info("Insufficient data for scatter plot.")

    # Margin by Tier box plot
    st.markdown("#### Margin Distribution by Investment Tier")
    tier_box_df = df[df['arb_margin_best'] > 0].copy()
    if len(tier_box_df) > 0:
        fig_box = px.box(
            tier_box_df, x='tier', y='arb_margin_best',
            color='tier',
            color_discrete_map={'Tier 1': '#10b981', 'Tier 2': '#f59e0b', 'Tier 3': '#ef4444', 'Excluded': '#475569'},
            labels={'arb_margin_best': 'Best Arb Margin (₹)', 'tier': 'Investment Tier'},
            category_orders={'tier': ['Tier 1', 'Tier 2', 'Tier 3', 'Excluded']},
        )
        fig_box.update_layout(
            showlegend=False,
            height=360,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter", color="#94a3b8"),
            xaxis=dict(gridcolor='rgba(99,102,241,0.08)'),
            yaxis=dict(gridcolor='rgba(99,102,241,0.08)'),
            margin=dict(l=40, r=20, t=20, b=40),
        )
        st.plotly_chart(fig_box, use_container_width=True)


# ─────────────────────────────────────────────────────────────────
# TAB 3: SUPPLY & DEMAND
# ─────────────────────────────────────────────────────────────────
with tab_supply:
    st.markdown("### 📦 Supply Depth & Demand Intensity")
    st.caption("Analyzes the rental inventory structure and demand pressure across zones.")

    sd1, sd2, sd3, sd4 = st.columns(4)
    total_3bhk = int(df['cnt_3bhk'].sum()) if 'cnt_3bhk' in df.columns else 0
    total_listings = int(df[['cnt_1bhk', 'cnt_2bhk', 'cnt_3bhk', 'cnt_4bhk']].sum().sum()) if 'cnt_1bhk' in df.columns else 0
    avg_demand = df['demand_intensity_idx'].mean() if 'demand_intensity_idx' in df.columns else 0
    avg_supply = df['supply_depth_idx'].mean() if 'supply_depth_idx' in df.columns else 0

    sd1.metric("Total Listings", f"{total_listings:,}")
    sd2.metric("3BHK Inventory", f"{total_3bhk:,}", delta=f"{total_3bhk/max(total_listings,1)*100:.1f}% of supply")
    sd3.metric("Avg Demand Index", f"{avg_demand:.3f}")
    sd4.metric("Avg Supply Index", f"{avg_supply:.3f}")

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # BHK mix treemap
    col_bhk, col_demand = st.columns(2)
    with col_bhk:
        st.markdown("#### BHK Type Distribution (City-wide)")
        bhk_totals = {
            '1 BHK': int(df['cnt_1bhk'].sum()) if 'cnt_1bhk' in df.columns else 0,
            '2 BHK': int(df['cnt_2bhk'].sum()) if 'cnt_2bhk' in df.columns else 0,
            '3 BHK': int(df['cnt_3bhk'].sum()) if 'cnt_3bhk' in df.columns else 0,
            '4 BHK': int(df['cnt_4bhk'].sum()) if 'cnt_4bhk' in df.columns else 0,
        }
        bhk_df = pd.DataFrame({'BHK Type': bhk_totals.keys(), 'Count': bhk_totals.values()})
        bhk_df = bhk_df[bhk_df['Count'] > 0]
        fig_bhk = px.pie(
            bhk_df, names='BHK Type', values='Count',
            color_discrete_sequence=['#818cf8', '#c084fc', '#f472b6', '#fb923c'],
            hole=0.45,
        )
        fig_bhk.update_traces(textinfo='label+percent', textfont=dict(color='#e0e7ff', size=13))
        fig_bhk.update_layout(
            height=380,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter", color="#94a3b8"),
            legend=dict(font=dict(color='#c7d2fe')),
            margin=dict(l=20, r=20, t=20, b=20),
        )
        st.plotly_chart(fig_bhk, use_container_width=True)

    with col_demand:
        st.markdown("#### Demand vs Supply Index")
        if 'demand_intensity_idx' in df.columns and 'supply_depth_idx' in df.columns:
            plot_ds = df[(df['demand_intensity_idx'] > 0) | (df['supply_depth_idx'] > 0)].copy()
            fig_ds = px.scatter(
                plot_ds, x='supply_depth_idx', y='demand_intensity_idx',
                color='tier',
                color_discrete_map={'Tier 1': '#10b981', 'Tier 2': '#f59e0b', 'Tier 3': '#ef4444', 'Excluded': '#475569'},
                hover_name='ward_name',
                labels={'supply_depth_idx': 'Supply Depth Index', 'demand_intensity_idx': 'Demand Intensity Index'},
                size='OPP_SCORE', size_max=16,
            )
            fig_ds.update_layout(
                height=380,
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family="Inter", color="#94a3b8"),
                xaxis=dict(gridcolor='rgba(99,102,241,0.08)'),
                yaxis=dict(gridcolor='rgba(99,102,241,0.08)'),
                legend=dict(font=dict(color='#c7d2fe')),
                margin=dict(l=40, r=20, t=20, b=40),
            )
            st.plotly_chart(fig_ds, use_container_width=True)

    # 3BHK Quartile Breakdown
    if os.path.exists(paths['quartiles']):
        st.markdown("#### 3BHK Supply Price Quartile Breakdown")
        st.caption("Rent distribution across Q1–Q4 for 3BHK inventory per zone. Q1 (bottom 25%) is Flent's target acquisition tier.")
        q_df = pd.read_excel(paths['quartiles'], sheet_name=0)
        st.dataframe(q_df.head(20), use_container_width=True, hide_index=True)


# ─────────────────────────────────────────────────────────────────
# TAB 4: SCORING BREAKDOWN
# ─────────────────────────────────────────────────────────────────
with tab_scoring:
    st.markdown("### 📊 Composite Scoring Breakdown")
    st.caption("See how the Opportunity Score is assembled from economic, demand, supply, and overlay signals.")

    # Stage breakdown table from the report
    stage_sheet_name = '📈 Stage Breakdown'
    if stage_sheet_name in report_sheets:
        stage_df = report_sheets[stage_sheet_name]
        st.markdown("#### Score Decomposition per Zone")
        st.dataframe(stage_df.head(30), use_container_width=True, hide_index=True)
    else:
        st.info("Stage breakdown sheet not found in the report.")

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # Score components radar for top 5
    st.markdown("#### Multi-dimensional Profile — Top 5 Zones")
    top5 = df.nlargest(5, 'OPP_SCORE')
    radar_cols = ['norm_arb_margin_pct', 'demand_intensity_idx', 'supply_depth_idx']
    radar_labels = ['Arbitrage Strength', 'Demand Intensity', 'Supply Depth']
    if profile['has_transit']:
        radar_cols.append('norm_transit')
        radar_labels.append('Transit Score')
    if profile['has_sez']:
        radar_cols.append('norm_sez')
        radar_labels.append('SEZ Proximity')

    available_radar = [c for c in radar_cols if c in df.columns]
    available_labels = [radar_labels[i] for i, c in enumerate(radar_cols) if c in df.columns]

    if len(available_radar) >= 3 and len(top5) > 0:
        fig_radar = go.Figure()
        colors_radar = ['#818cf8', '#f472b6', '#34d399', '#fbbf24', '#fb923c']
        for idx, (_, row) in enumerate(top5.iterrows()):
            vals = [float(row.get(c, 0)) for c in available_radar]
            vals.append(vals[0])  # close the polygon
            labels_r = available_labels + [available_labels[0]]
            fig_radar.add_trace(go.Scatterpolar(
                r=vals, theta=labels_r, fill='toself',
                name=str(row.get('ward_name', f'Zone {idx+1}')),
                line=dict(color=colors_radar[idx % len(colors_radar)]),
                opacity=0.65,
            ))
        fig_radar.update_layout(
            polar=dict(
                bgcolor='rgba(0,0,0,0)',
                radialaxis=dict(visible=True, range=[0, 1], gridcolor='rgba(99,102,241,0.15)', tickfont=dict(color='#64748b')),
                angularaxis=dict(gridcolor='rgba(99,102,241,0.15)', tickfont=dict(color='#c7d2fe', size=11)),
            ),
            height=480,
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family="Inter", color="#94a3b8"),
            legend=dict(font=dict(color='#c7d2fe', size=12)),
            margin=dict(l=80, r=80, t=40, b=40),
        )
        st.plotly_chart(fig_radar, use_container_width=True)
    else:
        st.info("Insufficient scoring dimensions to render radar chart.")

    # Aura / Spillover analysis
    st.markdown("#### Spatial Spillover (Aura) Effects")
    st.caption("Zones receive a boost or penalty based on the quality of their geographic neighbors.")
    aura_affected = df[df['aura_multiplier'] != 1.0].copy() if 'aura_multiplier' in df.columns else pd.DataFrame()
    if len(aura_affected) > 0:
        aura_display = aura_affected[['ward_name', 'tier', 'OPP_SCORE', 'aura_multiplier', 'aura_sources']].copy()
        aura_display.columns = ['Zone', 'Tier', 'Final Score', 'Aura Multiplier', 'Source Neighbors']
        st.dataframe(
            aura_display.sort_values('Aura Multiplier', ascending=False),
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No spatial spillover effects detected — scores are purely zone-intrinsic.")


# ─────────────────────────────────────────────────────────────────
# TAB 5: ECONOMETRIC VALIDATION
# ─────────────────────────────────────────────────────────────────
with tab_validation:
    st.markdown("### 📐 Econometric Validation & Statistical Rigor")
    st.caption("Two independent tests verify the statistical foundation of the arbitrage thesis.")

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # ── OLS REGRESSION ─────────────────────────────────────────
    st.markdown("#### 1. Arbitrage Structural OLS Regression")
    st.markdown("""
    > **Model:** `OLS(Q25 3BHK Acquisition Cost ~ Median 1BHK Retail Rent)`
    >
    > This regression tests whether the cost of acquiring a 3BHK (at Q1 pricing) is structurally
    > decoupled from the retail price of 1BHK rooms — the fundamental premise behind Flent's arbitrage.
    """)

    # Extract OLS values
    r2_val = ols_data.get('R² (Fit Quality)', 'N/A')
    beta_val = ols_data.get('1BHK Cost Multiplier (β)', 'N/A')
    intercept_val = ols_data.get('Intercept (α)', 'N/A')
    pval_val = ols_data.get('p-value (β)', 'N/A')
    nobs_val = ols_data.get('Observations (Wards)', 'N/A')
    breakeven_val = ols_data.get('Breakeven Demand Discount Min', 'N/A')
    ddf_val = ols_data.get("Flent's Operational DDF", 'N/A')
    thesis_val = ols_data.get('Arbitrage Thesis', 'N/A')

    # KPI metrics for OLS
    ols_c1, ols_c2, ols_c3, ols_c4 = st.columns(4)
    ols_c1.metric("R² (Fit Quality)", r2_val)
    ols_c2.metric("β (Cost Multiplier)", beta_val)
    ols_c3.metric("Intercept (α)", intercept_val)
    ols_c4.metric("Observations", nobs_val)

    # Thesis KPIs
    th1, th2, th3 = st.columns(3)
    th1.metric("Breakeven Discount", breakeven_val)
    th2.metric("Operational DDF", ddf_val)
    th3.metric("Arbitrage Thesis", thesis_val)

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # Plain English interpretations
    st.markdown("#### Plain-English Interpretation")

    beta_explain = ols_data.get(
        [k for k in ols_data if k.startswith('What is β')][0] if any(k.startswith('What is β') for k in ols_data) else '',
        ''
    )
    r2_explain = ols_data.get(
        [k for k in ols_data if k.startswith('What is R²')][0] if any(k.startswith('What is R²') for k in ols_data) else '',
        ''
    )
    be_explain = ols_data.get(
        [k for k in ols_data if k.startswith('Breakeven Discount')][0] if any(k.startswith('Breakeven Discount') for k in ols_data) else '',
        ''
    )
    ddf_explain = ols_data.get(
        [k for k in ols_data if k.startswith('Operational DDF')][0] if any(k.startswith('Operational DDF') for k in ols_data) else '',
        ''
    )

    interp_html = f"""
    <div class="ols-grid">
        <div class="ols-item">
            <div class="ols-label">β — Cost Multiplier</div>
            <div class="ols-val">{beta_val}</div>
            <div class="ols-desc">{beta_explain}</div>
        </div>
        <div class="ols-item">
            <div class="ols-label">R² — Fit Quality</div>
            <div class="ols-val">{r2_val}</div>
            <div class="ols-desc">{r2_explain}</div>
        </div>
        <div class="ols-item">
            <div class="ols-label">Breakeven Threshold</div>
            <div class="ols-val">{breakeven_val}</div>
            <div class="ols-desc">{be_explain}</div>
        </div>
        <div class="ols-item">
            <div class="ols-label">Operational Margin of Safety</div>
            <div class="ols-val">{ddf_val}</div>
            <div class="ols-desc">{ddf_explain}</div>
        </div>
    </div>
    """
    st.markdown(interp_html, unsafe_allow_html=True)

    st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)

    # OLS Regression plot
    col_ols_img, col_moran_img = st.columns(2)
    with col_ols_img:
        st.markdown("#### OLS Regression Plot")
        if os.path.exists(paths['ols_plot']):
            st.image(paths['ols_plot'], use_container_width=True)
        else:
            st.info("OLS regression plot not available.")

    # ── MORAN's I ──────────────────────────────────────────────
    with col_moran_img:
        st.markdown("#### 2. Moran's I — Spatial Autocorrelation")
        if os.path.exists(paths['moran']):
            st.image(paths['moran'], use_container_width=True)
        else:
            st.info("Moran's I plot not available.")

    st.markdown("""
    > **What Moran's I tests:** Whether 1BHK rents in nearby wards are more similar than expected
    > by chance (spatial clustering). A significant Moran's I confirms that rents follow geographic
    > patterns, validating the spatial spillover boost used in the scoring model.
    >
    > - **I > 0 (positive):** Nearby zones have similar rents → spatial clustering exists.
    > - **p < 0.05:** The clustering is statistically significant, not random.
    > - **Implication:** Spatial adjacency carries predictive value, justifying the "aura multiplier."
    """)


# ─────────────────────────────────────────────────────────────────
# TAB 6: RAW DATA EXPLORER
# ─────────────────────────────────────────────────────────────────
with tab_data:
    st.markdown("### 📋 Raw Data Explorer")

    data_source = st.radio(
        "Data Source",
        ["GeoJSON Properties", "Excel — Full Analysis", "Excel — Top 10 Targets"],
        horizontal=True,
    )

    if data_source == "GeoJSON Properties":
        st.caption(f"All {len(df)} zone records from the ward_analysis.geojson output.")
        # Drop geometry-heavy columns for display
        display_df = df.drop(columns=['_feature_id', 'closest_sezs', 'aura_sources'], errors='ignore')
        st.dataframe(display_df, use_container_width=True, hide_index=True)

    elif data_source == "Excel — Full Analysis":
        sheet_name = '📊 Full Analysis'
        if sheet_name in report_sheets:
            st.caption("Complete ward-level analytics from the Excel report.")
            st.dataframe(report_sheets[sheet_name], use_container_width=True, hide_index=True)
        else:
            st.warning("Full Analysis sheet not found.")

    elif data_source == "Excel — Top 10 Targets":
        sheet_name = '🏆 Top 10 Targets'
        if sheet_name in report_sheets:
            st.caption("Executive-level top 10 investment targets.")
            st.dataframe(report_sheets[sheet_name], use_container_width=True, hide_index=True)
        else:
            st.warning("Top 10 Targets sheet not found.")

    # Download button
    if os.path.exists(paths['report']):
        with open(paths['report'], 'rb') as f:
            st.download_button(
                "⬇️ Download Full Excel Report",
                f,
                file_name=f"flent_lens_report_{selected_city}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )


# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="section-sep"></div>', unsafe_allow_html=True)
st.markdown("""
<div style="text-align: center; padding: 20px 0 40px 0;">
    <span style="color: #475569; font-size: 0.8rem;">
        Flent Lens Analytics Platform · Built with Streamlit & Plotly ·
        Data Pipeline: <code style="color: #818cf8;">python main.py</code>
    </span>
</div>
""", unsafe_allow_html=True)
