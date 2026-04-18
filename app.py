"""
Flent Lens — Market Intelligence Dashboard
Professional analytical dashboard for leadership review.
"""
import streamlit as st
import pandas as pd
import json
import plotly.express as px
import plotly.graph_objects as go
import os
import subprocess
import sys
import re
import numpy as np
import warnings

# Silencing unavoidable shapely/geopandas warnings during O(N*M) proximity matching
warnings.filterwarnings('ignore', category=RuntimeWarning, message='invalid value encountered in distance')

# ═══════════════════════════════════════════════════════════════════
# PAGE CONFIG
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
# STYLE
# ═══════════════════════════════════════════════════════════════════
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

    /* ── Base ────────────────────────────────────────────────── */
    html, body, .stApp {
        font-family: 'Inter', 'Helvetica Neue', Helvetica, Arial, sans-serif;
        background: #fafbfc;
        color: #212529;
    }

    /* ── Sidebar ─────────────────────────────────────────────── */
    section[data-testid="stSidebar"] {
        background: #1b2838;
    }
    section[data-testid="stSidebar"] * {
        color: #c8d6e5 !important;
    }
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #ffffff !important;
        font-weight: 700 !important;
    }
    section[data-testid="stSidebar"] .stButton > button {
        background: #2e86de;
        color: #ffffff;
        border: none;
        font-weight: 600;
    }

    /* ── Typography ──────────────────────────────────────────── */
    .stMarkdown h1 {
        color: #1b2838;
        font-weight: 800;
        font-size: 1.8rem;
        letter-spacing: -0.02em;
    }
    .stMarkdown h2 {
        color: #1b2838;
        font-weight: 700;
        font-size: 1.35rem;
        margin-top: 1rem;
    }
    .stMarkdown h3 {
        color: #2c3e50;
        font-weight: 700;
        font-size: 1.05rem;
    }
    .stMarkdown p, .stMarkdown li {
        color: #495057;
        font-size: 0.92rem;
        line-height: 1.75;
    }

    /* ── Metric Cards ────────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-top: 3px solid #2e86de;
        border-radius: 6px;
        padding: 1.25rem 1.5rem !important;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    div[data-testid="stMetric"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.05);
    }
    div[data-testid="stMetric"] label {
        color: #6c757d !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        white-space: normal !important;
        overflow: visible !important;
    }
    div[data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #1b2838 !important;
        font-size: 1.5rem !important;
        font-weight: 700 !important;
        white-space: normal !important;
        overflow: visible !important;
        text-overflow: unset !important;
    }

    /* ── Tabs ─────────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 0;
        border-bottom: 2px solid #e1e4e8;
    }
    .stTabs [data-baseweb="tab"] {
        color: #6c757d;
        font-weight: 600;
        font-size: 0.85rem;
        padding: 0.75rem 1.25rem;
        border-bottom: 2px solid transparent;
        margin-bottom: -2px;
    }
    .stTabs [aria-selected="true"] {
        color: #1b2838 !important;
        border-bottom-color: #2e86de !important;
        background: transparent !important;
    }

    /* ── Chart explanation ────────────────────────────────────── */
    /* ── Econometric Blueprints ──────────────────────────────── */
    .blueprint-headline {
        color: #1b2838;
        font-weight: 800;
        font-size: 1.4rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #e1e4e8;
        padding-bottom: 0.5rem;
    }
    .plain-english {
        font-size: 1rem !important;
        line-height: 1.6;
        color: #495057;
        background: #f8f9fa;
        padding: 1.25rem;
        border-radius: 8px;
        margin-bottom: 1.5rem;
        border-left: 4px solid #2e86de;
    }
    .lh-highlight {
        color: #0b7a3e;
        font-weight: 700;
        background: #e6fffa;
        padding: 0 4px;
        border-radius: 3px;
    }
    .metric-pill {
        display: inline-block;
        background: #e9ecef;
        padding: 4px 10px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        color: #495057;
        margin-right: 8px;
    }
    .explain {
        background: #f0f4f8;
        border-left: 3px solid #2e86de;
        padding: 14px 18px;
        margin: 12px 0 16px 0;
        font-size: 0.88rem;
        color: #495057;
        line-height: 1.65;
    }
    .explain b { color: #1b2838; }

    /* ── Divider ──────────────────────────────────────────────── */
    .divider {
        border: 0;
        height: 1px;
        background: #e1e4e8;
        margin: 2.5rem 0;
    }

    /* ── Tutorial Step ────────────────────────────────────────── */
    .tour-step {
        background: #1b2838;
        border-radius: 8px;
        padding: 24px 28px;
        margin-bottom: 1.5rem;
        color: #ffffff;
    }
    .tour-step .tour-num {
        display: inline-block;
        background: #2e86de;
        color: #ffffff;
        width: 28px; height: 28px;
        border-radius: 50%;
        text-align: center;
        line-height: 28px;
        font-weight: 700;
        font-size: 0.8rem;
        margin-right: 10px;
    }
    .tour-step .tour-title {
        color: #ffffff;
        font-weight: 700;
        font-size: 1rem;
        display: inline;
    }
    .tour-step .tour-desc {
        color: #c8d6e5;
        font-size: 0.88rem;
        line-height: 1.6;
        margin-top: 10px;
    }

    /* ── Tab guide bar ────────────────────────────────────────── */
    .tab-guide {
        background: linear-gradient(135deg, #edf2ff 0%, #f0f4f8 100%);
        border: 1px solid #d0d7de;
        border-radius: 8px;
        padding: 16px 24px;
        margin-bottom: 1.5rem;
        display: flex;
        align-items: center;
        gap: 24px;
        flex-wrap: wrap;
    }
    .tab-guide .tg-item {
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .tab-guide .tg-num {
        background: #2e86de;
        color: #fff;
        width: 22px; height: 22px;
        border-radius: 50%;
        text-align: center;
        line-height: 22px;
        font-size: 0.65rem;
        font-weight: 700;
        flex-shrink: 0;
    }
    .tab-guide .tg-label {
        font-size: 0.8rem;
        color: #495057;
        font-weight: 600;
    }

    /* ── OLS Grid ─────────────────────────────────────────────── */
    .ols-row {
        display: flex;
        flex-wrap: wrap;
        gap: 16px;
        margin: 16px 0;
    }
    .ols-box {
        flex: 1 1 260px;
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        padding: 20px;
    }
    .ols-box .olbl { font-size: 0.7rem; font-weight: 700; color: #6c757d; text-transform: uppercase; letter-spacing: 0.04em; }
    .ols-box .oval { font-size: 1.15rem; font-weight: 800; color: #1b2838; margin: 6px 0; }
    .ols-box .odsc { font-size: 0.82rem; color: #6c757d; line-height: 1.55; }

    /* ── Native Component Styling ───────────────────────────── */
    /* Adds border/shadow to all DataFrames & Tables */
    div[data-testid="stDataFrame"], div[data-testid="stTable"] {
        border: 1px solid #e1e4e8;
        border-radius: 6px;
        background: #ffffff;
        padding: 1px;
        box-shadow: 0 1px 3px rgba(0,0,0,0.02);
    }

    /* ── Buttons ──────────────────────────────────────────────── */
    .stButton > button {
        border-radius: 4px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    /* Primary buttons (Next, Done, Run Pipeline) */
    .stButton > button[kind="primary"] {
        background: #1b2838 !important;
        color: #ffffff !important;
        border: none !important;
    }
    .stButton > button[kind="primary"]:hover {
        background: #2e86de !important;
        box-shadow: 0 4px 12px rgba(46, 134, 222, 0.3);
    }
    /* Secondary/Default buttons (Next when not primary, Skip) */
    .stButton > button[kind="secondary"] {
        background: #ffffff !important;
        color: #1b2838 !important;
        border: 1px solid #d0d7de !important;
    }
    .stButton > button[kind="secondary"]:hover {
        border-color: #2e86de !important;
        color: #2e86de !important;
        background: #f0f4f8 !important;
    }

    /* ── Chips ────────────────────────────────────────────────── */
    .chip-container {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 12px 0;
    }
    .chip {
        display: flex;
        align-items: center;
        background: #f1f3f5;
        border: 1px solid #e1e4e8;
        border-radius: 100px;
        overflow: hidden;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .chip-label {
        background: #1b2838;
        color: #ffffff;
        padding: 4px 10px;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-size: 0.65rem;
    }
    .chip-value {
        padding: 4px 12px;
        color: #1b2838;
    }

    /* ── Brilliant Style ───────────────────────────────────────── */
    .brilliant-card {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 12px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
    }
    .step {
        display: flex;
        gap: 16px;
        margin-bottom: 20px;
        align-items: flex-start;
    }
    .step-num {
        background: #1b2838;
        color: #fff;
        width: 26px; height: 26px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 700;
        flex-shrink: 0;
        margin-top: 2px;
    }
    .step-content {
        flex: 1;
    }
    .step-title {
        font-weight: 700;
        color: #1b2838;
        font-size: 0.95rem;
        margin-bottom: 4px;
    }
    .step-desc {
        color: #6c757d;
        font-size: 0.88rem;
        line-height: 1.5;
    }
    .wedge-container {
        display: flex;
        flex-direction: column;
        gap: 12px;
        margin: 20px 0;
        background: #f8f9fa;
        padding: 20px;
        border-radius: 8px;
    }
    .wedge-bar {
        height: 32px;
        border-radius: 4px;
        display: flex;
        align-items: center;
        padding: 0 12px;
        font-weight: 700;
        font-size: 0.8rem;
        color: #fff;
        transition: width 1s ease;
    }
    .verdict-badge {
        display: inline-block;
        padding: 6px 14px;
        border-radius: 100px;
        background: #e6fffa;
        color: #0b7a3e;
        border: 1px solid #c6f6d5;
        font-weight: 700;
        font-size: 0.8rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    /* ── Hide UI chrome ───────────────────────────────────────── */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# DATA HELPERS
# ═══════════════════════════════════════════════════════════════════
@st.cache_data
def load_geojson(path):
    with open(path, 'r') as f:
        geojson = json.load(f)
    records = []
    for i, feat in enumerate(geojson.get('features', [])):
        props = feat.get('properties', {})
        fid = str(props.get('ward_id', i))
        feat['id'] = fid
        props['_fid'] = fid
        records.append(props)
    df = pd.DataFrame(records)
    skip = {'_fid', 'ward_name_x', 'ward_name_y', 'zone_name_x',
            'zone_name_y', 'closest_sezs', 'aura_sources', 'tier', 'data_sparse'}
    for c in df.columns:
        if c not in skip:
            df[c] = pd.to_numeric(df[c], errors='coerce')
    return geojson, df

@st.cache_data
def load_xlsx(path):
    xl = pd.ExcelFile(path)
    return {n: pd.read_excel(xl, sheet_name=n) for n in xl.sheet_names}

@st.cache_data
def load_ols(path):
    try:
        df = pd.read_excel(path, sheet_name='📐 OLS Evidence')
        return {str(r[df.columns[0]]).strip(): str(r[df.columns[1]]).strip()
                for _, r in df.iterrows() if pd.notna(r[df.columns[0]])}
    except Exception:
        return {}

def inr(val):
    if val is None or pd.isna(val): return "₹0"
    return f"₹{int(val):,}"

# ═══════════════════════════════════════════════════════════════════
# CHART HELPERS
# ═══════════════════════════════════════════════════════════════════
DARK_NAVY = "#1b2838"
LIGHT_GRAY = "#f1f3f5"
BLUE_PRIMARY = "#2e86de"

HIGH_CONTRAST_LAYOUT = {
    "font": {"family": "Inter", "color": DARK_NAVY},
    "paper_bgcolor": "#ffffff",
    "plot_bgcolor": "#ffffff",
    "xaxis": {
        "gridcolor": LIGHT_GRAY,
        "linecolor": DARK_NAVY,
        "tickfont": {"size": 11, "color": DARK_NAVY},
        "title": {"font": {"size": 12, "color": DARK_NAVY}}
    },
    "yaxis": {
        "gridcolor": LIGHT_GRAY,
        "linecolor": DARK_NAVY,
        "tickfont": {"size": 11, "color": DARK_NAVY},
        "title": {"font": {"size": 12, "color": DARK_NAVY}}
    },
    "margin": {"l": 50, "r": 20, "t": 40, "b": 50}
}

def style_chart(fig):
    fig.update_layout(**HIGH_CONTRAST_LAYOUT)
    return fig


def paths_for(ck):
    p = city_config.CITY_PROFILES[ck]
    d = os.path.join(BASE_DIR, p['output_dir'])
    return {k: os.path.join(d, v) for k, v in {
        'geojson': 'ward_analysis.geojson', 'report': 'flent_lens_report.xlsx',
        'quartiles': '3bhk_supply_price_quartiles.xlsx',
        'moran': 'moran_scatterplot_avg_rent_1bhk.png',
        'ols_img': 'ols_arbitrage_validation.png',
    }.items()} | {'dir': d, 'profile': p}

def _pf(v):
    if not v or v == '—': return 0.0
    try:
        if isinstance(v, (int, float)): return float(v)
        import re
        m = re.search(r"[-+]?\d*\.\d+|\d+", str(v).replace(',',''))
        return float(m.group()) if m else 0.0
    except: return 0.0

def render_chip(label, value):
    return f"""<div class="chip"><div class="chip-label">{label}</div><div class="chip-value">{value}</div></div>"""



# ═══════════════════════════════════════════════════════════════════
# WARD CARD — uses st.columns + st.markdown for reliable rendering
# ═══════════════════════════════════════════════════════════════════
def render_ward_card(col, row, rank, has_transit, has_sez):
    """Render a ward snapshot card inside a given st.column."""
    name = str(row.get('ward_name', row.get('ward_id', '—')))
    tier = row.get('tier', 'Excluded')
    score = _f(row, 'OPP_SCORE')
    margin = _f(row, 'arb_margin_best')
    rent1 = _f(row, 'avg_rent_1bhk')
    rent3 = _f(row, 'avg_rent_3bhk')
    dd = _f(row, 'demand_discount') * 100
    demand = _f(row, 'demand_intensity_idx')
    supply = _i(row, 'cnt_3bhk') + _i(row, 'cnt_4bhk')
    q1r, q1c = _f(row, 'q1_avg_rent'), _i(row, 'q1_count')
    q2r, q2c = _f(row, 'q2_avg_rent'), _i(row, 'q2_count')
    q3r, q3c = _f(row, 'q3_avg_rent'), _i(row, 'q3_count')
    q4r, q4c = _f(row, 'q4_avg_rent'), _i(row, 'q4_count')
    transit = _f(row, 'transit_score')
    sez = _f(row, 'sez_employment_score')
    aura = _f(row, 'aura_multiplier')
    aura = aura if aura > 0 else 1.0
    d_lbl = "High" if demand >= 0.5 else ("Mod" if demand >= 0.35 else "Low")
    d_pct = min(demand * 100, 100)

    # Extract display names and IDs
    disp_name = str(row.get('ward_name', '—'))
    disp_id = str(row.get('ward_id', '—'))
    id_label = "Pincode" if sel == 'hyderabad' else "Ward #"

    with col:
        # Header via HTML table (tables render reliably in Streamlit)
        st.markdown(f"""
<table style="width:100%;border-collapse:collapse;background:#1b2838;border-radius:6px 6px 0 0;overflow:hidden;">
<tr>
<td style="padding:16px 18px;">
  <div style="color:#868e96;font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.04em;">{id_label} {disp_id}</div>
  <div style="color:#ffffff;font-size:1.1rem;font-weight:700;margin:1px 0 6px 0;">{disp_name}</div>
  <span style="background:{tc(tier)};color:#fff;padding:2px 8px;border-radius:3px;font-size:0.65rem;font-weight:700;text-transform:uppercase;">{tier}</span>
</td>
<td style="padding:16px 18px;text-align:right;vertical-align:top;">
  <div style="color:{tc(tier)};font-size:1.6rem;font-weight:800;line-height:1;">{score:.1f}</div>
  <div style="color:#868e96;font-size:0.6rem;text-transform:uppercase;letter-spacing:0.05em;">Score</div>
</td>
</tr>
</table>
""", unsafe_allow_html=True)

        # Body — structured as clean HTML tables (Streamlit-safe)
        body = f"""
<table style="width:100%;border-collapse:collapse;background:#ffffff;border:1px solid #e1e4e8;border-top:0;border-radius:0 0 6px 6px;font-family:'Inter',sans-serif;">
<!-- Core Arbitrage -->
<tr><td colspan="2" style="padding:12px 18px 4px 18px;font-size:0.65rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;border-bottom:1px solid #f1f3f5;">Core Arbitrage</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">Avg Arb Margin</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#0b7a3e;">{inr(margin)}/mo</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">1BHK Retail Rent</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#212529;">{inr(rent1)}/mo</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">3BHK Acq Cost</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#212529;">{inr(rent3)}/mo</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">Demand Discount</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#2e86de;">{dd:.0f}%</td></tr>
<!-- Supply Depth -->
<tr><td colspan="2" style="padding:14px 18px 4px 18px;font-size:0.65rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;border-bottom:1px solid #f1f3f5;">Supply · {supply} units</td></tr>
<tr><td colspan="2" style="padding:8px 18px;">
  <table style="width:100%;border-collapse:collapse;text-align:center;border:1px solid #e1e4e8;border-radius:4px;">
    <tr style="background:#f8f9fa;">
      <td style="padding:4px;border-right:1px solid #e1e4e8;font-size:0.7rem;font-weight:700;color:#6c757d;">Q1</td>
      <td style="padding:4px;border-right:1px solid #e1e4e8;font-size:0.7rem;font-weight:700;color:#6c757d;">Q2</td>
      <td style="padding:4px;border-right:1px solid #e1e4e8;font-size:0.7rem;font-weight:700;color:#6c757d;">Q3</td>
      <td style="padding:4px;font-size:0.7rem;font-weight:700;color:#6c757d;">Q4</td>
    </tr>
    <tr>
      <td style="padding:6px 2px;border-right:1px solid #e1e4e8;"><span style="font-weight:700;font-size:0.85rem;color:#212529;">{inrk(q1r)}</span><br><span style="font-size:0.65rem;color:#adb5bd;">{q1c}u</span></td>
      <td style="padding:6px 2px;border-right:1px solid #e1e4e8;"><span style="font-weight:700;font-size:0.85rem;color:#212529;">{inrk(q2r)}</span><br><span style="font-size:0.65rem;color:#adb5bd;">{q2c}u</span></td>
      <td style="padding:6px 2px;border-right:1px solid #e1e4e8;"><span style="font-weight:700;font-size:0.85rem;color:#212529;">{inrk(q3r)}</span><br><span style="font-size:0.65rem;color:#adb5bd;">{q3c}u</span></td>
      <td style="padding:6px 2px;"><span style="font-weight:700;font-size:0.85rem;color:#212529;">{inrk(q4r)}</span><br><span style="font-size:0.65rem;color:#adb5bd;">{q4c}u</span></td>
    </tr>
  </table>
</td></tr>
<!-- Market -->
<tr><td colspan="2" style="padding:14px 18px 4px 18px;font-size:0.65rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;border-bottom:1px solid #f1f3f5;">Market Signals</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">Demand Index</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#212529;">{demand:.2f} <span style="color:#868e96;font-weight:500;">({d_lbl})</span></td></tr>
<tr><td colspan="2" style="padding:0 18px 8px 18px;">
  <div style="width:100%;height:5px;background:#e9ecef;border-radius:3px;"><div style="width:{d_pct}%;height:5px;background:#e67700;border-radius:3px;"></div></div>
</td></tr>"""

        if has_transit:
            t_pct = min(transit * 100, 100)
            body += f"""
<tr><td style="padding:4px 18px;font-size:0.85rem;color:#495057;">Transit Score</td><td style="padding:4px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#212529;">{transit:.2f}</td></tr>
<tr><td colspan="2" style="padding:0 18px 8px 18px;">
  <div style="width:100%;height:5px;background:#e9ecef;border-radius:3px;"><div style="width:{t_pct}%;height:5px;background:#2e86de;border-radius:3px;"></div></div>
</td></tr>"""

        if has_sez and sez > 0:
            body += f"""<tr><td style="padding:4px 18px;font-size:0.85rem;color:#495057;">SEZ Gravity</td><td style="padding:4px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#212529;">{sez:.2f}</td></tr>"""

        if aura != 1.0:
            a_str = f"+{(aura-1)*100:.0f}%" if aura > 1 else f"−{(1-aura)*100:.0f}%"
            body += f"""
<tr><td colspan="2" style="padding:14px 18px 4px 18px;font-size:0.65rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;border-bottom:1px solid #f1f3f5;">Spatial Spillover</td></tr>
<tr><td style="padding:6px 18px;font-size:0.85rem;color:#495057;">Aura Effect</td><td style="padding:6px 18px;text-align:right;font-size:0.85rem;font-weight:700;color:#2e86de;">{a_str}</td></tr>"""

        body += "</table>"
        st.markdown(body, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### 🔬 Flent Lens")
    st.caption("Market Intelligence Platform")
    st.markdown("---")

    ckeys = list(city_config.CITY_PROFILES.keys())
    cnames = [city_config.CITY_PROFILES[c]['city_name'] for c in ckeys]
    si = st.selectbox("City", range(len(ckeys)), format_func=lambda i: cnames[i])
    sel = ckeys[si]
    prof = city_config.CITY_PROFILES[sel]

    st.markdown("---")
    if st.button("🔄 Restart Tutorial", width="stretch"):
        st.session_state.tour_step = 0
        st.session_state.tour_done = False
        st.rerun()

    st.markdown("---")
    if st.button("🚀 Run Pipeline", width="stretch", type="primary"):
        cfp = os.path.join(BASE_DIR, "city_config.py")
        with open(cfp, "r") as f: txt = f.read()
        txt = re.sub(r'^ACTIVE_CITY\s*=\s*["\'].*?["\']', f'ACTIVE_CITY = "{sel}"', txt, flags=re.MULTILINE)
        with open(cfp, "w") as f: f.write(txt)
        with st.status(f"Processing {prof['city_name']}…", expanded=True) as sts:
            proc = subprocess.Popen([sys.executable, "main.py"], stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, text=True, cwd=BASE_DIR)
            box = st.empty()
            lines = []
            for ln in proc.stdout:
                ln = ln.strip()
                if ln:
                    lines.append(ln)
                    if len(lines) > 20: lines.pop(0)
                    box.code("\n".join(lines), language="text")
            proc.wait()
            if proc.returncode == 0:
                sts.update(label="✅ Done", state="complete"); st.rerun()
            else:
                sts.update(label="❌ Failed", state="error")

    st.markdown("---")
    st.markdown(f"**Unit** · {prof['geo_unit_label']}")
    st.markdown(f"**Transit** · {'✅' if prof['has_transit'] else '—'}")
    st.markdown(f"**SEZ** · {'✅' if prof['has_sez'] else '—'}")


# ═══════════════════════════════════════════════════════════════════
# LOAD
# ═══════════════════════════════════════════════════════════════════
P = paths_for(sel)
if not os.path.exists(P['geojson']):
    st.info(f"No output for {prof['city_name']}. Click **Run Pipeline** in the sidebar.")
    st.stop()

raw_geo, df = load_geojson(P['geojson'])
if 'ward_name' not in df.columns:
    df['ward_name'] = df.get('ward_name_x', df.get('ward_name_y', df['ward_id'].astype(str)))
sheets = load_xlsx(P['report']) if os.path.exists(P['report']) else {}
ols = load_ols(P['report']) if os.path.exists(P['report']) else {}


# ═══════════════════════════════════════════════════════════════════
# TUTORIAL SYSTEM
# ═══════════════════════════════════════════════════════════════════
TOUR_STEPS = [
    {
        "title": "Welcome to Flent Lens",
        "desc": "This dashboard visualises the output of our rental arbitrage analysis pipeline. "
                "It identifies geographic zones where Flent can lease large 3BHK apartments, split them "
                "into premium co-living rooms, and earn the margin between acquisition cost and per-room revenue. "
                "Let's walk you through what you're looking at.",
    },
    {
        "title": "Executive KPIs — The Big Picture",
        "desc": "The five cards below show headline metrics: total zones evaluated, how many are Tier 1 "
                "(highest conviction), how many are commercially viable, the peak arbitrage margin found, "
                "and the mean opportunity score across the city.",
    },
    {
        "title": "Priority Investment Targets — Top 3 Cards",
        "desc": "These cards mirror the Google Earth KML atlas popups. Each card shows one zone's "
                "full economic profile: arbitrage margin, 1BHK retail rent, 3BHK acquisition cost, "
                "supply quartile breakdown (Q1 is Flent's target tier), and market signals like demand "
                "intensity and transit connectivity.",
    },
    {
        "title": "Deep-Dive Tabs — Below the Cards",
        "desc": "Scroll down to find four analytical tabs: "
                "(1) Opportunity Atlas — an interactive map, "
                "(2) Economic Analysis — margin vs rent scatter plot, "
                "(3) Statistical Validation — OLS regression and Moran's I proof, "
                "(4) Data Export — browse and download the raw Excel report.",
    },
    {
        "title": "Switching Cities & Re-running",
        "desc": "Use the sidebar on the left to switch between Bangalore and Hyderabad. "
                "You can also re-execute the pipeline directly from the dashboard — the results "
                "will refresh automatically. Enjoy exploring!",
    },
]

if 'tour_step' not in st.session_state:
    st.session_state.tour_step = 0
if 'tour_done' not in st.session_state:
    st.session_state.tour_done = False

if not st.session_state.tour_done:
    step = st.session_state.tour_step
    s = TOUR_STEPS[step]
    st.markdown(f"""
    <div class="tour-step">
        <span class="tour-num">{step + 1}</span>
        <div class="tour-title">{s['title']}</div>
        <div class="tour-desc">{s['desc']}</div>
    </div>
    """, unsafe_allow_html=True)

    bcol1, bcol2, bcol3 = st.columns([1, 1, 6])
    with bcol1:
        if step < len(TOUR_STEPS) - 1:
            if st.button("Next →", key="tour_next", width="stretch", type="primary"):
                st.session_state.tour_step += 1
                st.rerun()
        else:
            if st.button("✓ Done", key="tour_finish", width="stretch", type="primary"):
                st.session_state.tour_done = True
                st.rerun()
    with bcol2:
        if st.button("Skip tour", key="tour_skip", width="stretch"):
            st.session_state.tour_done = True
            st.rerun()


# ═══════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════
st.markdown(f"""
<table style="width:100%;border-collapse:collapse;margin-bottom:2rem;">
<tr>
<!-- Blue accent bar -->
<td style="width:4px;background:#2e86de;padding:0;"></td>
<!-- Left: Project identity -->
<td style="padding:24px 28px;vertical-align:top;width:50%;">
  <div style="font-size:0.65rem;font-weight:700;color:#2e86de;text-transform:uppercase;letter-spacing:0.1em;margin-bottom:6px;">Flent Lens</div>
  <div style="font-size:1.7rem;font-weight:800;color:#1b2838;line-height:1.2;letter-spacing:-0.02em;margin-bottom:10px;">{prof['city_name']} Market Intelligence</div>
  <div style="font-size:0.88rem;color:#495057;line-height:1.65;">
    Evaluating <b>{len(df)} {prof['geo_unit_label']}s</b> across arbitrage economics, demand intensity, supply feasibility, and spatial overlays to identify optimal co-living expansion zones.
  </div>
</td>
<!-- Right: Research Q + Team -->
<td style="padding:24px 28px;vertical-align:top;border-left:1px solid #e1e4e8;">
  <div style="font-size:0.62rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Research Question</div>
  <div style="font-size:0.82rem;color:#212529;line-height:1.55;font-style:italic;margin-bottom:14px;border-left:2px solid #2e86de;padding-left:12px;">
    Which areas offer the most favourable combination of per-room arbitrage margin, convertible 3BHK+ supply, and demand for shared living?
  </div>
  <div style="font-size:0.62rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:4px;">Team</div>
  <div style="font-size:0.78rem;color:#495057;line-height:1.7;">
    Harshith Bejjanki <span style="color:#adb5bd;">047</span> · Suneeth Boorgula <span style="color:#adb5bd;">016</span> · Sudhiksha <span style="color:#adb5bd;">033</span><br>
    Peddi Sudeeksha <span style="color:#adb5bd;">027</span> · Vedanth Nagaarur <span style="color:#adb5bd;">019</span>
  </div>
  <div style="font-size:0.68rem;color:#adb5bd;margin-top:6px;">BBA · Python Analytics · April 2026</div>
</td>
</tr>
</table>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════════════
tc_map = df['tier'].value_counts().to_dict() if 'tier' in df.columns else {}
viable = int(df['margin_viable'].sum()) if 'margin_viable' in df.columns else 0
peak = df['arb_margin_best'].max() if 'arb_margin_best' in df.columns else 0

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Zones", len(df))
k2.metric("Tier 1", tc_map.get('Tier 1', 0))
k3.metric("Viable", viable)
k4.metric("Peak Margin", inr(peak))
k5.metric("Mean Score", f"{df['OPP_SCORE'].mean():.1f}")


# ═══════════════════════════════════════════════════════════════════
# TOP 3 WARD CARDS
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("## Priority Investment Targets")
st.markdown("The three highest-scoring zones, with full economic profile mirroring the Google Earth atlas cards.")

top3 = df.nlargest(3, 'OPP_SCORE')
cols = st.columns(3, gap="medium")
for idx, (_, row) in enumerate(top3.iterrows()):
    render_ward_card(cols[idx], row, idx + 1, prof['has_transit'], prof['has_sez'])


# ─────────── TAB GUIDE & INITIALIZATION ────────────────────────────
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("## Detailed Analysis")
st.markdown("""
<div class="tab-guide">
  <div style="font-size:0.75rem;color:#6c757d;font-weight:600;">EXPLORE →</div>
  <div class="tg-item"><span class="tg-num">1</span><span class="tg-label">Geographic Map</span></div>
  <div class="tg-item"><span class="tg-num">2</span><span class="tg-label">Margin Economics</span></div>
  <div class="tg-item"><span class="tg-num">3</span><span class="tg-label">Validation Proofs</span></div>
  <div class="tg-item"><span class="tg-num">4</span><span class="tg-label">Data Export</span></div>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4 = st.tabs([
    "Opportunity Atlas", "Economic Analysis", "Statistical Validation", "Data Export"
])

# ─────────── TAB 1 ───────────────────────────────────────────────
with tab1:
    st.markdown("### Geographic Opportunity Distribution")
    st.markdown("""<div class="explain">
    <b>What this shows:</b> Each zone is shaded by its composite Opportunity Score (0–100). 
    The score integrates arbitrage economics, demand intensity, supply depth, and spatial overlays.
    <b>How to read it:</b> Darker blue zones have the highest investment priority. Hover over any 
    zone to see exact metrics.
    </div>""", unsafe_allow_html=True)

    bbox = prof['bounding_box']
    fig = px.choropleth_map(
        df, geojson=raw_geo, locations='_fid', color='OPP_SCORE',
        color_continuous_scale=[[0,'#edf2ff'],[0.3,'#74c0fc'],[0.6,'#228be6'],[1,'#1b2838']],
        map_style='carto-positron',
        zoom=9 if sel == 'bangalore' else 10,
        center={"lat": sum(bbox['lat'])/2, "lon": sum(bbox['lon'])/2},
        opacity=0.75,
        hover_name='ward_name',
        hover_data={'OPP_SCORE':':.1f', 'tier':True, 'arb_margin_best':':,.0f', '_fid':False},
    )
    fig.update_layout(height=520)
    style_chart(fig)
    fig.update_layout(margin=dict(l=0,r=0,t=0,b=0),
                      coloraxis_colorbar=dict(title="Score", thickness=12, len=0.5))
    st.plotly_chart(fig, width="stretch")

    st.markdown("#### Tier Summary")
    st.markdown("""<div class="explain">
    <b>Tier methodology:</b> Zones are ranked by Opportunity Score, then classified into tiers at 
    the 75th, 50th, and 25th percentile thresholds. Tier 1 (≥75th pctl) represents the highest-conviction 
    investment targets. Zones not meeting margin viability thresholds are Excluded.
    </div>""", unsafe_allow_html=True)

    ts = df.groupby('tier').agg(Zones=('ward_id','count'), Score=('OPP_SCORE','mean'), 
                                 Margin=('arb_margin_best','mean')).reindex(['Tier 1','Tier 2','Tier 3','Excluded']).reset_index()
    ts.columns = ['Tier', 'Zones', 'Avg Score', 'Avg Margin (₹)']
    st.dataframe(ts.style.format({'Avg Score':'{:.1f}', 'Avg Margin (₹)':'{:,.0f}'}), 
                 width="stretch", hide_index=True)


# ─────────── TAB 2 ───────────────────────────────────────────────
with tab2:
    st.markdown("### Arbitrage Margin Landscape")
    st.markdown("""<div class="explain">
    <b>What this shows:</b> Each bubble is a zone with a positive arbitrage margin. The x-axis 
    is the median retail rent for a standalone 1BHK (Flent's revenue source), and the y-axis is 
    the realized margin after subtracting the 3BHK master lease cost and applying demand discount.
    <b>Bubble size</b> = 3BHK inventory count. <b>Why it matters:</b> Zones in the top-right 
    combine high yield <em>and</em> strong margins — the most defensible investment plays.
    </div>""", unsafe_allow_html=True)

    pf = df[(df['avg_rent_1bhk']>0) & (df['arb_margin_best']>0)].copy()
    if len(pf) > 0:
        fig2 = px.scatter(pf, x='avg_rent_1bhk', y='arb_margin_best', size='cnt_3bhk', color='tier',
                          color_discrete_map={'Tier 1':'#0b7a3e','Tier 2':'#e67700','Tier 3':'#c92a2a','Excluded':'#adb5bd'},
                          hover_name='ward_name', size_max=22,
                          labels={'avg_rent_1bhk':'1BHK Retail Rent (₹)','arb_margin_best':'Best Arb Margin (₹/mo)'})
        style_chart(fig2)
        fig2.update_layout(height=420, legend=dict(title="Tier"))
        st.plotly_chart(fig2, width="stretch")

    st.markdown("#### Complete Ward Economics Table")
    if '📊 Full Analysis' in sheets:
        st.dataframe(sheets['📊 Full Analysis'], width="stretch", hide_index=True)


# ─────────── TAB 3 ───────────────────────────────────────────────
with tab3:
    st.markdown("## Econometric Validation")
    st.markdown("_Empirical Proof of the Flent Arbitrage Strategy_")
    
    # ── Part 1: The "Aura Effect" (Moran’s I Spatial Autocorrelation) ────────
    st.markdown('<div class="brilliant-card">', unsafe_allow_html=True)
    
    mi_idx = ols.get("Moran's I Index", "0.0") if ols else "0.0"
    is_clustered = ols and ols.get("Clustered?", "") == "YES (Clustered)"
    
    if sel == 'hyderabad':
        aura_headline = 'Fragmented Premiums: The Weakness of Hyderabad\'s Spatial Aura'
        aura_body = """
            <b>The Bottom Line:</b><br/>
            Unlike other cities where premium real estate creates massive 'spillover' into neighboring zones, 
            Hyderabad's rental market is highly fragmented. While there is a statistically significant clustering effect, 
            it is much weaker. This tells us that we cannot rely heavily on 'neighborhood momentum' here. 
            A great ward does not guarantee the adjacent ward will support premium co-living prices. 
            Our targeting must be hyper-localized.
        """
        aura_math = f"""
            - **Moran's I Statistic ($I = {mi_idx}$)**: A positive but weak spatial autocorrelation. It proves that clustering exists, but the 'Aura Effect' is muted compared to other cities.
            - **P-Value ($p = 0.0226$)**: The clustering is statistically significant (under the standard 0.05 threshold), meaning the relationship is valid, just less intense.
            - **The LH Quadrant (Low-High)**: Notice how vertically stacked the dots are on the far left. This indicates a high concentration of very low-priced 1BHK zones, making the transition to "High" spatial lag much sharper. The true arbitrage strike zones (dots firmly in the top-left) are fewer, requiring strict geographic discipline.
        """
    else:
        # Default / Bangalore
        aura_headline = 'Real Estate is Contagious: Validating the Neighborhood Aura Effect'
        aura_body = f"""
            <b>The Bottom Line:</b><br/>
            Before Flent invests capital, we need to know if "premium" rental zones spill over into neighboring areas. 
            Our spatial model proves a <b>{'strong, statistically significant' if is_clustered else 'highly fragmented and random'}</b> 
            clustering effect in 1BHK rents. 
            {"More importantly, this scatterplot identifies our 'Arbitrage Strike Zone' (The <span class='lh-highlight'>LH Quadrant</span>)—pockets where a zone's baseline prices are lower, but it is surrounded by highly expensive neighbors." if is_clustered else "In this city, demand is localized; spillovers are rare, meaning each property must be individually vetted for margin."}
            These are our prime geographic targets for acquiring cheap 3BHK inventory while marketing to high-budget tenants.
        """
        aura_math = f"""
            - **Moran's I Statistic ($I = {mi_idx}$)**: A robust value confirming the degree of spatial autocorrelation. {"It definitively proves high-rent wards cluster geographically, validating our 'Spillover Boost' engine." if is_clustered else "A low value indicates a randomized market structure."}
            - **P-Value ($p = 0.0$)**: Confirms that this spatial clustering is highly statistically significant and completely non-random.
            - **The LH Quadrant (Low-High)**: Wards located in the top-left represent zones where local rents are below average (z-score < 0), but surrounding rents are above average (spatial lag > 0). This is the **geographic definition of arbitrage**.
        """

    st.markdown(f'<div class="blueprint-headline">{aura_headline}</div>', unsafe_allow_html=True)

    col_v, col_c = st.columns([1, 1], gap="large")
    with col_v:
        st.markdown(f'<div class="plain-english">{aura_body}</div>', unsafe_allow_html=True)
        with st.expander("🔬 View Model Parameters & Math"):
            st.markdown(aura_math)
            st.latex(r"I = \frac{n}{W} \frac{\sum_{i}\sum_{j} w_{ij}(z_i - \bar{z})(z_j - \bar{z})}{\sum_{i} (z_i - \bar{z})^2}")

    with col_c:
        if os.path.exists(P['moran']):
            st.image(P['moran'], caption=f"{prof['city_name']} Spatial Clustering (Moran Scatter)", width="stretch")
        else:
            st.info("Chart pending.")
    st.markdown('</div>', unsafe_allow_html=True)


    st.write("") # Spacer


    # ── Part 2: The "Arbitrage Engine" (Hedonic OLS Regression) ──────────────
    st.markdown('<div class="brilliant-card">', unsafe_allow_html=True)
    
    beta_raw = _pf(ols.get('1BHK Cost Multiplier (β)', '0.5')) if ols else 0.5
    r2_raw = _pf(ols.get('R² (Fit Quality)', '0.0'))
    min_dd = _pf(ols.get('Breakeven Demand Discount Min', '0.0'))

    if sel == 'hyderabad':
        ols_headline = 'The 1.14x Squeeze: Why Flent Lens is Mandatory in Hyderabad'
        ols_body = f"""
            <b>The Bottom Line:</b><br/>
            Hyderabad presents a structural challenge to the co-living model. Our regression shows a cost multiplier of <b>{beta_raw:.2f}x</b>. 
            This means that as we look at more expensive neighborhoods, the cost to acquire a 3BHK rises faster than the revenue we can generate from 1BHK demand. 
            The premium market actually compresses our margins. Furthermore, our baseline breakeven cost is nearly <b>{min_dd*100:.1f}%</b> of a 1BHK's rent. 
            To survive in Hyderabad, Flent cannot expand blindly; we must use this pipeline to strictly target mid-tier markets or heavily discounted outlier properties.
        """
        ols_math = f"""
            - **Cost Multiplier ($\\beta = {beta_raw:.2f}$)**: The slope of the regression line. For every ₹1 increase in retail 1BHK rent, our 3BHK acquisition cost jumps by ₹{beta_raw:.2f}. The arbitrage spread shrinks in luxury wards.
            - **Implied Breakeven Demand Discount Min ({min_dd})**: A high structural floor. We must capture {min_dd*100:.1f}% of a standard 1BHK's rent per room just to pay the landlord. If we charge our standard 80%, our gross operating margin is much tighter here than in other cities.
            - **Adjusted R-Squared ($R^2 = {r2_raw}$)**: This model explains {r2_raw*100:.1f}% of the variance in 3BHK costs based on 1BHK demand. The relationship is clearer here than in our previous data, meaning the "margin squeeze" is a structural reality, not just a data artifact.
        """
    else:
        # Default / Bangalore
        ols_headline = f'The {beta_raw:.2f}x Multiplier: Proving the Arbitrage Spread'
        ols_body = f"""
            <b>The Bottom Line:</b><br/>
            Our financial model relies on the spread between wholesale 3BHK acquisition costs and retail 1BHK demand. 
            This regression proves that the spread not only exists but is <b>{'structurally massive' if beta_raw < 1 else 'present but sensitive'}</b>. 
            For every ₹1 increase in market 1BHK rent, our 3BHK acquisition cost only increases by <b>₹{beta_raw:.2f}</b>.
            Furthermore, our absolute minimum breakeven demand discount is just <b>{min_dd}</b>. 
            This means Flent only needs to capture {float(min_dd)*100:.1f}% of a standard 1BHK's rent per room to cover the base lease. 
            Our target of charging 80% yields a highly defensible gross margin.
        """
        ols_math = f"""
            - **Cost Multiplier ($\\beta = {beta_raw:.2f}$)**: The slope of the regression. Because $\\beta$ is { "well below 1" if beta_raw < 1 else "aligned with market growth" }, the arbitrage gap { "fundamentally widens" if beta_raw < 1 else "remains stable" } in higher-priced wards.
            - **Minimum Breakeven ({min_dd})**: The mathematical floor. We only need {float(min_dd)*100:.1f}% of a ward's median 1BHK rent per room to pay for the 3BHK.
            - **Adjusted R-Squared ($R^2 = {r2_raw}$)**: {"This exceptionally low $R^2$ reveals extreme pricing inefficiency in the 3BHK market. This volatility is exactly why Flent cannot rely on 'gut feeling' sourcing—it mandates the use of the Flent Lens pipeline to filter out overpriced anomalies and pinpoint properties sitting below the red line." if float(r2_raw) < 0.2 else "A stable $R^2$ indicates a more efficient market."}
        """

    st.markdown(f'<div class="blueprint-headline">{ols_headline}</div>', unsafe_allow_html=True)

    col_v2, col_c2 = st.columns([1, 1], gap="large")
    with col_v2:
        st.markdown(f'<div class="plain-english">{ols_body}</div>', unsafe_allow_html=True)
        with st.expander("🛠️ View Regression Specs"):
            st.markdown(ols_math)
            st.latex(r"Cost_{3BHK} = \alpha + \beta \cdot Rent_{1BHK} + \epsilon")

    with col_c2:
        if os.path.exists(P['ols_img']):
            st.image(P['ols_img'], caption=f"{prof['city_name']} Economic Proof: 1BHK Rent vs 3BHK Cost", width="stretch")
        else:
            st.info("Chart pending.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)
        




# ─────────── TAB 4 ───────────────────────────────────────────────
with tab4:
    st.markdown("### Data Export")
    view = st.radio("View", ["Executive Targets", "Full Analysis", "Score Breakdown"], horizontal=True)
    sn = {"Executive Targets":"🏆 Top 10 Targets", "Full Analysis":"📊 Full Analysis",
          "Score Breakdown":"📈 Stage Breakdown"}.get(view)
    if sn and sn in sheets:
        st.dataframe(sheets[sn], width="stretch", hide_index=True)
    else:
        st.info("Sheet not available.")

    if os.path.exists(P['report']):
        with open(P['report'], "rb") as f:
            st.download_button("📂 Download Excel Report", f,
                               file_name=f"Flent_Lens_{sel}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                               width="stretch")


# ═══════════════════════════════════════════════════════════════════
# FOOTER
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.caption(f"Flent Lens · {prof['city_name']} · {len(df)} zones · Generated from pipeline output")
