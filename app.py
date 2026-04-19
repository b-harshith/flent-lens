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

    /* ── Econometric Section Banner ───────────────────────────── */
    .econo-banner {
        background: linear-gradient(135deg, #0d1f2d 0%, #1b2838 60%, #0d3a5c 100%);
        border-radius: 10px;
        padding: 28px 36px;
        margin-bottom: 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 24px;
        flex-wrap: wrap;
    }
    .econo-banner-left {
        flex: 1;
        min-width: 260px;
    }
    .econo-banner-eyebrow {
        font-size: 0.6rem;
        font-weight: 700;
        color: #4db6ff;
        text-transform: uppercase;
        letter-spacing: 0.14em;
        margin-bottom: 10px;
    }
    .econo-banner-title {
        font-size: 1.55rem;
        font-weight: 900;
        color: #ffffff;
        line-height: 1.2;
        letter-spacing: -0.02em;
        margin-bottom: 10px;
    }
    .econo-banner-thesis {
        font-size: 0.85rem;
        color: #c8d6e5;
        line-height: 1.65;
        font-style: italic;
        border-left: 3px solid #2e86de;
        padding-left: 12px;
    }
    .econo-banner-right {
        display: flex;
        flex-direction: column;
        gap: 10px;
        min-width: 180px;
    }
    .econo-method-chip {
        background: rgba(46,134,222,0.15);
        border: 1px solid rgba(46,134,222,0.4);
        border-radius: 6px;
        padding: 8px 14px;
        display: flex;
        align-items: center;
        gap: 10px;
    }
    .econo-method-icon {
        font-size: 1.1rem;
    }
    .econo-method-text {
        font-size: 0.75rem;
        font-weight: 700;
        color: #ffffff;
        line-height: 1.3;
    }
    .econo-method-sub {
        font-size: 0.65rem;
        color: #7ab3d8;
        font-weight: 400;
    }
    /* ── Stat Callout Row ─────────────────────────────────────── */
    .stat-callout-row {
        display: flex;
        gap: 14px;
        flex-wrap: wrap;
        margin: 0 0 24px 0;
    }
    .stat-callout {
        flex: 1 1 160px;
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-top: 3px solid #2e86de;
        border-radius: 8px;
        padding: 16px 18px;
        text-align: center;
        box-shadow: 0 2px 8px rgba(0,0,0,0.03);
    }
    .stat-callout.green { border-top-color: #0b7a3e; }
    .stat-callout.orange { border-top-color: #e67700; }
    .stat-callout-val {
        font-size: 2rem;
        font-weight: 900;
        color: #1b2838;
        line-height: 1;
        margin: 6px 0 4px 0;
    }
    .stat-callout-val.green { color: #0b7a3e; }
    .stat-callout-val.orange { color: #e67700; }
    .stat-callout-lbl {
        font-size: 0.65rem;
        font-weight: 700;
        color: #6c757d;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    .stat-callout-desc {
        font-size: 0.72rem;
        color: #868e96;
        margin-top: 5px;
        line-height: 1.4;
    }
    /* ── Proof Section Header ─────────────────────────────────── */
    .proof-header {
        display: flex;
        align-items: center;
        gap: 14px;
        margin-bottom: 18px;
    }
    .proof-badge {
        background: linear-gradient(135deg, #1b2838, #2e86de);
        color: #fff;
        width: 36px; height: 36px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.75rem;
        font-weight: 900;
        flex-shrink: 0;
        letter-spacing: 0.02em;
    }
    .proof-header-text {
        flex: 1;
    }
    .proof-header-tag {
        font-size: 0.6rem;
        font-weight: 700;
        color: #2e86de;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 3px;
    }
    .proof-header-title {
        font-size: 1.15rem;
        font-weight: 800;
        color: #1b2838;
        line-height: 1.25;
    }
    /* ── Proof Separator ──────────────────────────────────────── */
    .proof-sep {
        display: flex;
        align-items: center;
        gap: 14px;
        margin: 32px 0;
    }
    .proof-sep-line {
        flex: 1;
        height: 1px;
        background: #e1e4e8;
    }
    .proof-sep-label {
        font-size: 0.65rem;
        font-weight: 700;
        color: #adb5bd;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        white-space: nowrap;
    }
    /* ── Pull Figure ──────────────────────────────────────────── */
    .pull-figure {
        display: inline-block;
        background: linear-gradient(135deg, #e9f3ff, #f0f7ff);
        border: 1px solid #cce4ff;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 12px 0 8px 0;
        text-align: center;
        width: 100%;
    }
    .pull-figure-val {
        font-size: 2.4rem;
        font-weight: 900;
        color: #1b2838;
        line-height: 1;
    }
    .pull-figure-val.green { color: #0b7a3e; }
    .pull-figure-val.red { color: #c92a2a; }
    .pull-figure-caption {
        font-size: 0.72rem;
        color: #6c757d;
        margin-top: 5px;
        font-weight: 600;
    }

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

    /* ── Model Assumptions Grid ──────────────────────────────── */
    .assumption-grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
        gap: 12px;
        margin: 16px 0 8px 0;
    }
    .assumption-item {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-left: 4px solid #2e86de;
        border-radius: 6px;
        padding: 14px 16px;
        display: flex;
        gap: 12px;
        align-items: flex-start;
    }
    .assumption-num {
        background: #1b2838;
        color: #fff;
        min-width: 24px; height: 24px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 0.7rem;
        font-weight: 800;
        flex-shrink: 0;
        margin-top: 1px;
    }
    .assumption-text {
        font-size: 0.82rem;
        color: #212529;
        line-height: 1.55;
    }
    .assumption-text b { color: #1b2838; }
    .assumption-kv {
        display: inline-block;
        background: #e9ecef;
        color: #1b2838;
        font-size: 0.7rem;
        font-weight: 700;
        padding: 1px 7px;
        border-radius: 3px;
        margin-left: 4px;
    }
    .assumption-section-title {
        font-size: 0.65rem;
        font-weight: 700;
        color: #2e86de;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        margin-bottom: 6px;
    }

    /* ── Ward Card v2 ────────────────────────────────────────── */
    .wcard {
        background: #ffffff;
        border: 1px solid #e1e4e8;
        border-radius: 10px;
        overflow: hidden;
        box-shadow: 0 4px 16px rgba(0,0,0,0.06);
        font-family: 'Inter', sans-serif;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .wcard:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.10);
    }
    .wcard-header {
        padding: 18px 20px 14px 20px;
        position: relative;
    }
    .wcard-rank {
        position: absolute;
        top: 16px;
        right: 18px;
        width: 44px; height: 44px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 1.1rem;
        font-weight: 800;
        color: #fff;
    }
    .wcard-eyebrow {
        font-size: 0.62rem;
        font-weight: 700;
        color: rgba(255,255,255,0.55);
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 3px;
    }
    .wcard-name {
        font-size: 1.05rem;
        font-weight: 800;
        color: #ffffff;
        line-height: 1.25;
        margin-bottom: 8px;
        padding-right: 56px;
    }
    .wcard-tier {
        display: inline-block;
        padding: 2px 10px;
        border-radius: 3px;
        font-size: 0.6rem;
        font-weight: 800;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #fff;
    }
    .wcard-score-row {
        display: flex;
        align-items: center;
        gap: 6px;
        margin-top: 10px;
    }
    .wcard-score-val {
        font-size: 2rem;
        font-weight: 900;
        line-height: 1;
    }
    .wcard-score-label {
        font-size: 0.6rem;
        font-weight: 600;
        color: rgba(255,255,255,0.5);
        text-transform: uppercase;
        letter-spacing: 0.05em;
        line-height: 1.3;
    }
    .wcard-body {
        padding: 0 20px 16px 20px;
    }
    .wcard-section {
        font-size: 0.6rem;
        font-weight: 700;
        color: #868e96;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        padding: 12px 0 6px 0;
        border-bottom: 1px solid #f1f3f5;
        margin-bottom: 6px;
    }
    .wcard-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding: 4px 0;
    }
    .wcard-label { font-size: 0.82rem; color: #495057; }
    .wcard-val { font-size: 0.88rem; font-weight: 700; color: #212529; }
    .wcard-val-green { font-size: 0.88rem; font-weight: 800; color: #0b7a3e; }
    .wcard-val-blue { font-size: 0.88rem; font-weight: 700; color: #2e86de; }
    .margin-bar-wrap {
        background: #e9ecef;
        border-radius: 4px;
        height: 7px;
        margin: 3px 0 6px 0;
        overflow: hidden;
    }
    .margin-bar-fill {
        height: 100%;
        border-radius: 4px;
    }
    .wcard-qtable {
        width: 100%;
        border-collapse: collapse;
        border: 1px solid #e1e4e8;
        border-radius: 4px;
        overflow: hidden;
        margin: 6px 0 2px 0;
    }
    .wcard-qtable th {
        background: #f8f9fa;
        font-size: 0.65rem;
        font-weight: 700;
        color: #6c757d;
        padding: 5px;
        text-align: center;
        border-right: 1px solid #e1e4e8;
    }
    .wcard-qtable td {
        padding: 6px 3px;
        text-align: center;
        border-right: 1px solid #e1e4e8;
        vertical-align: middle;
    }
    .wcard-qval { font-weight: 800; font-size: 0.85rem; color: #212529; display: block; }
    .wcard-qcnt { font-size: 0.65rem; color: #adb5bd; display: block; }
    .wcard-demand-bar {
        background: #e9ecef;
        border-radius: 3px;
        height: 5px;
        margin: 3px 0 4px 0;
        overflow: hidden;
    }
    .wcard-verdict {
        background: #f0f7ff;
        border: 1px solid #cce4ff;
        border-radius: 6px;
        padding: 10px 14px;
        margin-top: 12px;
        font-size: 0.8rem;
        color: #1b2838;
        line-height: 1.55;
    }
    .wcard-verdict b { color: #2e86de; }

    /* ── Param chips row ─────────────────────────────────────── */
    .param-chips {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 12px 0 0 0;
    }
    .param-chip {
        display: inline-flex;
        align-items: center;
        gap: 0;
        background: #f1f3f5;
        border: 1px solid #e1e4e8;
        border-radius: 100px;
        overflow: hidden;
        font-size: 0.72rem;
        font-weight: 600;
    }
    .param-chip-label {
        background: #1b2838;
        color: #fff;
        padding: 3px 9px;
        font-size: 0.63rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        font-weight: 700;
    }
    .param-chip-val {
        padding: 3px 10px;
        color: #1b2838;
    }

    /* ── Footer strip ────────────────────────────────────────── */
    .footer-strip {
        background: #1b2838;
        border-radius: 8px;
        padding: 20px 28px;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 12px;
        margin-top: 2rem;
    }
    .footer-left { color: #c8d6e5; font-size: 0.82rem; line-height: 1.6; }
    .footer-left b { color: #ffffff; }
    .footer-right { display: flex; gap: 10px; align-items: center; flex-wrap: wrap; }
    .footer-badge {
        display: inline-block;
        background: #2e86de;
        color: #ffffff;
        padding: 6px 14px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
        text-decoration: none;
        letter-spacing: 0.02em;
    }
    .footer-tag {
        font-size: 0.72rem;
        color: #5a7a9a;
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

def inrk(v):
    if v is None or pd.isna(v): return "₹0"
    v = float(v)
    if v >= 1000: return f"₹{v/1000:.1f}k"
    return f"₹{int(v)}"

def _f(row, col):
    v = row.get(col, 0)
    try: return float(v) if pd.notna(v) else 0.0
    except: return 0.0

def _i(row, col):
    v = row.get(col, 0)
    try: return int(float(v)) if pd.notna(v) else 0
    except: return 0

def tc(tier):
    return {'Tier 1':'#0b7a3e','Tier 2':'#e67700','Tier 3':'#c92a2a'}.get(tier, '#adb5bd')

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
# WARD CARD v2 — redesigned for recruiter readability
# ═══════════════════════════════════════════════════════════════════
def _margin_health(margin):
    """Return (color, label) for margin health bar."""
    if margin >= 15000: return ('#0b7a3e', 'Strong')
    if margin >= 8000:  return ('#e67700', 'Viable')
    if margin >= 5000:  return ('#f59f00', 'Marginal')
    return ('#c92a2a', 'Weak')

def _rank_gradient(rank):
    """Return CSS background for rank badge."""
    return {
        1: 'linear-gradient(135deg,#f6c90e,#e67700)',
        2: 'linear-gradient(135deg,#adb5bd,#6c757d)',
        3: 'linear-gradient(135deg,#cd7f32,#8b4513)',
    }.get(rank, '#adb5bd')

def _header_bg(tier):
    """Return header background gradient per tier."""
    return {
        'Tier 1': 'linear-gradient(135deg,#0d2137 0%,#1b2838 60%,#0d3a5c 100%)',
        'Tier 2': 'linear-gradient(135deg,#1a2e1a 0%,#1b2838 100%)',
        'Tier 3': 'linear-gradient(135deg,#2e1b0f 0%,#1b2838 100%)',
    }.get(tier, '#1b2838')

def _verdict(rank, name, margin, score, tier):
    """Generate a plain-English verdict for a ward card."""
    if tier == 'Tier 1' and margin >= 10000:
        return f"<b>Prime target.</b> {name} clears the viability threshold with a {inr(margin)}/mo spread — lease a 3BHK here, split into rooms, extract margin immediately."
    if tier == 'Tier 1':
        return f"<b>High conviction.</b> {name} ranks Tier 1 with a score of {score:.1f}. Margin is positive and supply depth is sufficient for initial roll-out."
    if tier == 'Tier 2':
        return f"<b>Secondary pipeline.</b> {name} presents viable economics. Suitable as a follow-on market once Tier 1 locations are occupied."
    return f"<b>Watchlist.</b> {name} is borderline viable. Monitor supply and margin trends before committing."

def render_ward_card(col, row, rank, has_transit, has_sez):
    """Render a redesigned ward snapshot card inside a given st.column."""
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
    disp_name = str(row.get('ward_name', '—'))
    disp_id   = str(row.get('ward_id', '—'))
    id_label  = "Pincode" if sel == 'hyderabad' else "Ward"
    m_color, m_label = _margin_health(margin)
    m_pct = min(margin / 20000 * 100, 100) if margin > 0 else 0
    hbg = _header_bg(tier)
    rank_bg = _rank_gradient(rank)
    verdict_html = _verdict(rank, disp_name, margin, score, tier)

    with col:
        st.markdown(f"""
<div class="wcard">
  <!-- ── HEADER ── -->
  <div class="wcard-header" style="background:{hbg};">
    <!-- Rank badge -->
    <div class="wcard-rank" style="background:{rank_bg};box-shadow:0 2px 8px rgba(0,0,0,0.3);">#{rank}</div>
    <!-- ID eyebrow -->
    <div class="wcard-eyebrow">{id_label} {disp_id}</div>
    <!-- Ward name -->
    <div class="wcard-name">{disp_name}</div>
    <!-- Tier pill -->
    <span class="wcard-tier" style="background:{tc(tier)};">{tier}</span>
    <!-- Score -->
    <div class="wcard-score-row">
      <div class="wcard-score-val" style="color:{tc(tier)};">{score:.1f}</div>
      <div class="wcard-score-label">Opportunity<br>Score</div>
    </div>
  </div>
  <!-- ── BODY ── -->
  <div class="wcard-body">
    <!-- Margin section -->
    <div class="wcard-section">Arbitrage Margin · {supply} units available</div>
    <div class="wcard-row">
      <span class="wcard-label">Monthly Margin</span>
      <span style="font-size:1.05rem;font-weight:900;color:{m_color};">{inr(margin)}/mo</span>
    </div>
    <!-- Margin health bar -->
    <div style="display:flex;align-items:center;gap:8px;margin-bottom:6px;">
      <div class="margin-bar-wrap" style="flex:1;">
        <div class="margin-bar-fill" style="width:{m_pct}%;background:{m_color};"></div>
      </div>
      <span style="font-size:0.65rem;font-weight:700;color:{m_color};text-transform:uppercase;">{m_label}</span>
    </div>
    <div class="wcard-row">
      <span class="wcard-label">1BHK Retail Rent</span>
      <span class="wcard-val">{inr(rent1)}/mo</span>
    </div>
    <div class="wcard-row">
      <span class="wcard-label">3BHK Lease Cost (Q1)</span>
      <span class="wcard-val">{inr(rent3)}/mo</span>
    </div>
    <div class="wcard-row">
      <span class="wcard-label">Demand Discount Applied</span>
      <span class="wcard-val-blue">{dd:.0f}%</span>
    </div>
    <!-- Q1-Q4 supply depth -->
    <div class="wcard-section">Supply Quartile Depth</div>
    <table class="wcard-qtable">
      <tr>
        <th style="background:#e9f3ff;color:#2e86de;">Q1 ★</th>
        <th>Q2</th><th>Q3</th><th style="border-right:none;">Q4</th>
      </tr>
      <tr>
        <td style="background:#f0f7ff;"><span class="wcard-qval">{inrk(q1r)}</span><span class="wcard-qcnt">{q1c} units</span></td>
        <td><span class="wcard-qval">{inrk(q2r)}</span><span class="wcard-qcnt">{q2c} units</span></td>
        <td><span class="wcard-qval">{inrk(q3r)}</span><span class="wcard-qcnt">{q3c} units</span></td>
        <td style="border-right:none;"><span class="wcard-qval">{inrk(q4r)}</span><span class="wcard-qcnt">{q4c} units</span></td>
      </tr>
    </table>
    <div style="font-size:0.65rem;color:#868e96;margin-bottom:2px;">★ Q1 = cheapest 25% — Flent's sourcing target</div>
    <!-- Market signals -->
    <div class="wcard-section">Market Signals</div>
    <div class="wcard-row">
      <span class="wcard-label">Demand Index</span>
      <span class="wcard-val">{demand:.2f} <span style="color:#868e96;font-weight:500;">({d_lbl})</span></span>
    </div>
    <div class="wcard-demand-bar"><div style="width:{d_pct}%;height:5px;background:#e67700;border-radius:3px;"></div></div>
""", unsafe_allow_html=True)

        extra = ""
        if has_transit:
            t_pct = min(transit * 100, 100)
            extra += f"""
    <div class="wcard-row"><span class="wcard-label">Transit Score</span><span class="wcard-val">{transit:.2f}</span></div>
    <div class="wcard-demand-bar"><div style="width:{t_pct}%;height:5px;background:#2e86de;border-radius:3px;"></div></div>
"""
        if has_sez and sez > 0:
            extra += f"""<div class="wcard-row"><span class="wcard-label">SEZ Gravity</span><span class="wcard-val">{sez:.2f}</span></div>"""
        if aura != 1.0:
            a_str = f"+{(aura-1)*100:.0f}%" if aura > 1 else f"−{(1-aura)*100:.0f}%"
            ac = '#0b7a3e' if aura > 1 else '#c92a2a'
            extra += f"""<div class="wcard-row"><span class="wcard-label">Neighborhood Aura</span><span style="font-size:0.88rem;font-weight:700;color:{ac};">{a_str}</span></div>"""

        st.markdown(extra + f"""
    <!-- Plain-English Verdict -->
    <div class="wcard-verdict">{verdict_html}</div>
  </div>
</div>
""", unsafe_allow_html=True)


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
<table style="width:100%;border-collapse:collapse;margin-bottom:1.5rem;background:#ffffff;border:1px solid #e1e4e8;border-radius:10px;overflow:hidden;box-shadow:0 2px 8px rgba(0,0,0,0.04);">
<tr>
<!-- Blue accent bar -->
<td style="width:5px;background:linear-gradient(180deg,#2e86de,#1b2838);padding:0;"></td>
<!-- Left: Project identity -->
<td style="padding:28px 32px;vertical-align:top;width:55%;">
  <div style="font-size:0.62rem;font-weight:700;color:#2e86de;text-transform:uppercase;letter-spacing:0.12em;margin-bottom:8px;">🔬 Flent Lens · Co-Living Market Intelligence</div>
  <div style="font-size:1.9rem;font-weight:900;color:#1b2838;line-height:1.15;letter-spacing:-0.03em;margin-bottom:12px;">{prof['city_name']} Rental<br>Arbitrage Analysis</div>
  <div style="font-size:0.85rem;color:#212529;line-height:1.6;border-left:3px solid #2e86de;padding-left:14px;margin-bottom:14px;font-style:italic;">
    Which zones combine the highest per-room arbitrage margin, convertible 3BHK+ supply, and strongest co-living demand?
  </div>
  <div class="param-chips">
    <div class="param-chip"><span class="param-chip-label">Zones</span><span class="param-chip-val">{len(df)} {prof['geo_unit_label']}s</span></div>
    <div class="param-chip"><span class="param-chip-label">Revenue DDF</span><span class="param-chip-val">0.80×</span></div>
    <div class="param-chip"><span class="param-chip-label">Min Margin</span><span class="param-chip-val">₹5,000/mo</span></div>
    <div class="param-chip"><span class="param-chip-label">Sourcing</span><span class="param-chip-val">Q1 (25th pctl)</span></div>
  </div>
</td>
<!-- Right: Team + context -->
<td style="padding:28px 32px;vertical-align:top;border-left:1px solid #e1e4e8;background:#fafbfc;">
  <div style="font-size:0.6rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:8px;">Model</div>
  <div style="font-size:0.82rem;color:#212529;line-height:1.65;margin-bottom:16px;">
    Lease 3BHK+ units at <b>wholesale Q1 rates</b>, split into premium rooms,
    price each room at <b>80% of median 1BHK rent</b>. Pipeline scores
    {len(df)} zones across economics, demand, supply, and spatial overlays.
  </div>
  <div style="font-size:0.6rem;font-weight:700;color:#868e96;text-transform:uppercase;letter-spacing:0.06em;margin-bottom:6px;">Team · BBA Python Analytics · April 2026</div>
  <div style="font-size:0.78rem;color:#495057;line-height:1.7;">
    Harshith Bejjanki <span style="color:#adb5bd;">047</span> · Suneeth Boorgula <span style="color:#adb5bd;">016</span> · Sudhiksha <span style="color:#adb5bd;">033</span><br>
    Peddi Sudeeksha <span style="color:#adb5bd;">027</span> · Vedanth Nagaarur <span style="color:#adb5bd;">019</span>
  </div>
</td>
</tr>
</table>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════
# MODEL ASSUMPTIONS (always-visible, collapsed by default)
# ═══════════════════════════════════════════════════════════════════
with st.expander("📐 Model Assumptions — 7 rules this pipeline is built on", expanded=False):
    st.markdown("""
<div class="assumption-section-title">Core Business Rules</div>
<div class="assumption-grid">
  <div class="assumption-item">
    <div class="assumption-num">1</div>
    <div class="assumption-text"><b>Rental Arbitrage Only</b> — Flent does not buy properties. It leases large 3BHK+ units and converts them into premium co-living rooms.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">2</div>
    <div class="assumption-text"><b>Wholesale Sourcing at Q1</b> — Acquisition price is anchored to the <span class="assumption-kv">25th percentile</span> of market rent, reflecting Flent's ability to negotiate distressed or bulk inventory.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">3</div>
    <div class="assumption-text"><b>Dynamic Demand Discount Factor</b> — Per-room revenue uses a <span class="assumption-kv">base DDF of 0.80</span> (rooms priced at 80% of median 1BHK rent), but this is <b>not static</b>. A ±10% ward-level elastic band adjusts the discount based on local price pressure — high-demand wards retain closer to 0.90×, low-demand wards compress to 0.70×. Rooms always undercut a solo 1BHK to remain the better value proposition.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">4</div>
    <div class="assumption-text"><b>Dynamic Yield by Size</b> — Room count depends on sqft: <span class="assumption-kv">3 rooms</span> for standard 3BHK, up to <span class="assumption-kv">5 rooms</span> for 4BHK ≥2,200 sqft.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">5</div>
    <div class="assumption-text"><b>Viability Threshold</b> — A zone qualifies only if it yields arbitrage margin <span class="assumption-kv">&gt;₹5,000/mo</span> and has a supply depth of <span class="assumption-kv">&gt;3 listings</span>.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">6</div>
    <div class="assumption-text"><b>Spatial Spillover (Aura Effect)</b> — Wards adjacent to Tier 1 clusters receive a <span class="assumption-kv">+10% score boost</span>. Isolated high-performing wards receive a <span class="assumption-kv">−15% penalty</span>.</div>
  </div>
  <div class="assumption-item">
    <div class="assumption-num">7</div>
    <div class="assumption-text"><b>Transit as a Penalty</b> — High bus density is weighted <span class="assumption-kv">−0.10</span> to account for noise, congestion, and the premium positioning of Flent properties.</div>
  </div>
</div>
<div style="font-size:0.75rem;color:#868e96;margin-top:10px;">⚠ Limitations: single data source (Magicbricks), no time-series, no capex modelling, static DDF. See README for full caveats.</div>
""", unsafe_allow_html=True)

# ═══════════════════════════════════════════════════════════════════
# KPIs
# ═══════════════════════════════════════════════════════════════════
tc_map = df['tier'].value_counts().to_dict() if 'tier' in df.columns else {}
viable = int(df['margin_viable'].sum()) if 'margin_viable' in df.columns else 0
peak = df['arb_margin_best'].max() if 'arb_margin_best' in df.columns else 0

listing_cols = [c for c in df.columns if c.startswith('cnt_')]
total_listings = int(df[listing_cols].sum().sum()) if listing_cols else 0

k1, k2, lk, k3, k4, k5 = st.columns(6)
k1.metric("Zones Evaluated", len(df))
k2.metric("Tier 1 Targets", tc_map.get('Tier 1', 0))
lk.metric("Total Listings", f"{total_listings:,}")
k3.metric("Viable Zones", viable)
k4.metric("Peak Margin", inr(peak))
k5.metric("Mean Opp Score", f"{df['OPP_SCORE'].mean():.1f}")

# ═══════════════════════════════════════════════════════════════════
# TOP 3 WARD CARDS
# ═══════════════════════════════════════════════════════════════════
st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
st.markdown("## Priority Investment Targets — Tier 1")
st.markdown("""
<div style="font-size:0.88rem;color:#495057;margin-bottom:1rem;line-height:1.6;">
  Top 3 <b>Tier 1</b> zones (≥75th percentile of viable zones), ranked by composite Opportunity Score.
  Each card mirrors the Google Earth KML atlas popup — arbitrage margin, supply quartile depth, demand index, and a plain-English verdict.
  <b>Q1 (cheapest 25% of inventory)</b> is Flent's sourcing bracket.
</div>
""", unsafe_allow_html=True)

# Pull from Tier 1 only; pad with Tier 2 if city has fewer than 3 Tier 1 zones
_tier1 = df[df['tier'] == 'Tier 1'].nlargest(3, 'OPP_SCORE')
if len(_tier1) < 3:
    _needed = 3 - len(_tier1)
    _tier2_pad = df[df['tier'] == 'Tier 2'].nlargest(_needed, 'OPP_SCORE')
    top3 = pd.concat([_tier1, _tier2_pad])
else:
    top3 = _tier1

cols = st.columns(3, gap="medium")
for idx, (_, row) in enumerate(top3.iterrows()):
    render_ward_card(cols[idx], row, idx + 1, prof['has_transit'], prof['has_sez'])


# ─────────── TAB GUIDE & INITIALIZATION ──────────────────────────────────────
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

    # ── Stat extraction (shared by banner + callout row) ──────────────────────
    mi_idx   = ols.get("Moran's I Index", "—") if ols else "—"
    mi_val   = _pf(mi_idx) if mi_idx != "—" else 0.0
    is_clustered = ols and ols.get("Clustered?", "") == "YES (Clustered)"
    beta_raw = _pf(ols.get('1BHK Cost Multiplier (β)', '0.5')) if ols else 0.5
    r2_raw   = _pf(ols.get('R² (Fit Quality)', '0.0'))
    min_dd   = _pf(ols.get('Breakeven Demand Discount Min', '0.0'))

    # ── Section banner ────────────────────────────────────────────────────────
    cluster_verdict = "Clustered" if is_clustered else "Fragmented"
    beta_verdict    = "Spread Favourable" if beta_raw < 1 else "Margin Squeezed"
    st.markdown(f"""
    <div class="econo-banner">
      <div class="econo-banner-left">
        <div class="econo-banner-eyebrow">§ Section 3 · Statistical Validation</div>
        <div class="econo-banner-title">Econometric Proof of the Flent Strategy</div>
        <div class="econo-banner-thesis">
          Two independent statistical models — spatial autocorrelation and hedonic OLS regression —
          independently validate that the rental arbitrage opportunity is real, measurable, and
          concentrated in specific geographic clusters.
        </div>
      </div>
      <div class="econo-banner-right">
        <div class="econo-method-chip">
          <span class="econo-method-icon">🗺️</span>
          <div>
            <div class="econo-method-text">Moran's I</div>
            <div class="econo-method-sub">Spatial Autocorrelation · {cluster_verdict}</div>
          </div>
        </div>
        <div class="econo-method-chip">
          <span class="econo-method-icon">📉</span>
          <div>
            <div class="econo-method-text">OLS</div>
            <div class="econo-method-sub">Cost vs Demand Regression · {beta_verdict}</div>
          </div>
        </div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── At-a-glance stat callouts ─────────────────────────────────────────────
    mi_color   = "green" if mi_val > 0.1 else "orange"
    beta_color = "green" if beta_raw < 1 else "red_cls"
    r2_color   = "orange" if r2_raw < 0.2 else "green"
    st.markdown(f"""
    <div class="stat-callout-row">
      <div class="stat-callout {mi_color}">
        <div class="stat-callout-lbl">Moran's I</div>
        <div class="stat-callout-val {mi_color}">{mi_idx}</div>
        <div class="stat-callout-desc">Spatial clustering strength<br>({'Significant' if is_clustered else 'Weak'})</div>
      </div>
      <div class="stat-callout">
        <div class="stat-callout-lbl">Cost Multiplier β</div>
        <div class="stat-callout-val {'green' if beta_raw < 1 else 'orange'}">{beta_raw:.2f}×</div>
        <div class="stat-callout-desc">3BHK cost per ₹1 rise<br>in 1BHK rent</div>
      </div>
      <div class="stat-callout {r2_color}">
        <div class="stat-callout-lbl">Adj R²</div>
        <div class="stat-callout-val {r2_color}">{r2_raw:.2f}</div>
        <div class="stat-callout-desc">OLS model fit quality<br>({'Inefficient market' if r2_raw < 0.2 else 'Stable market'})</div>
      </div>
      <div class="stat-callout {'green' if min_dd < 0.7 else 'orange'}">
        <div class="stat-callout-lbl">Breakeven DDF</div>
        <div class="stat-callout-val {'green' if min_dd < 0.7 else 'orange'}">{min_dd:.0%}</div>
        <div class="stat-callout-desc">Min room revenue needed<br>to cover master lease</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Proof 1: Spatial Autocorrelation (Moran's I) ──────────────────────────
    st.markdown('<div class="brilliant-card">', unsafe_allow_html=True)

    if sel == 'hyderabad':
        proof1_tag   = "Proof 1 · Spatial Autocorrelation"
        proof1_title = "Fragmented Premiums — The Weakness of Hyderabad's Spatial Aura"
        aura_body = """
            <b>The Bottom Line:</b><br/>
            Unlike other cities where premium real estate creates massive 'spillover' into neighboring zones,
            Hyderabad's rental market is highly fragmented. While a statistically significant clustering effect exists,
            it is much weaker. We cannot rely on 'neighborhood momentum' here — a great ward does not guarantee
            the adjacent ward will support premium co-living prices. Our targeting must be hyper-localized.
        """
        aura_math = f"""
            - **Moran's I ($I = {mi_idx}$)**: Positive but weak autocorrelation — clustering exists, but the Aura Effect is muted.
            - **P-Value ($p = 0.0226$)**: Statistically significant (< 0.05), so the relationship is valid, just less intense.
            - **The LH Quadrant**: High concentration of very low-priced 1BHK zones — the true arbitrage strike zones are fewer, requiring strict geographic discipline.
        """
        pull_val   = mi_idx
        pull_class = "orange"
        pull_cap   = "Moran's I — Weak spatial spillover"
    else:
        proof1_tag   = "Proof 1 · Spatial Autocorrelation"
        proof1_title = "Real Estate is Contagious — Validating the Neighborhood Aura Effect"
        aura_body = f"""
            <b>The Bottom Line:</b><br/>
            Before Flent invests capital, we need to know if "premium" rental zones spill over into neighboring areas.
            Our spatial model proves a <b>{'strong, statistically significant' if is_clustered else 'highly fragmented and random'}</b>
            clustering effect in 1BHK rents.
            {"This scatterplot pinpoints our <b>Arbitrage Strike Zone</b> — the <span class='lh-highlight'>LH Quadrant</span> — pockets where a zone's baseline prices are low but its neighbours are expensive." if is_clustered else "Demand is localized here; each property must be individually vetted for margin."}
            These are our prime geographic targets: cheap 3BHK inventory inside high-budget tenant catchments.
        """
        aura_math = f"""
            - **Moran's I ($I = {mi_idx}$)**: {"Definitively proves high-rent wards cluster geographically, validating the Spillover Boost engine." if is_clustered else "Low value — randomized market structure."}
            - **P-Value ($p = 0.0$)**: Spatial clustering is highly significant and non-random.
            - **LH Quadrant**: Wards with below-average local rents (z < 0) but above-average spatial lag — the **geographic definition of arbitrage**.
        """
        pull_val   = mi_idx
        pull_class = "green" if is_clustered else "orange"
        pull_cap   = "Moran's I — Spatial rent clustering"

    st.markdown(f"""
    <div class="proof-header">
      <div class="proof-badge">P1</div>
      <div class="proof-header-text">
        <div class="proof-header-tag">{proof1_tag}</div>
        <div class="proof-header-title">{proof1_title}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_v, col_c = st.columns([1, 1], gap="large")
    with col_v:
        st.markdown(
            f'<div class="pull-figure">'
            f'<div class="pull-figure-val {pull_class}">{pull_val}</div>'
            f'<div class="pull-figure-caption">{pull_cap}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div class="plain-english">{aura_body}</div>', unsafe_allow_html=True)
        with st.expander("🔬 Behind the Number — Model Parameters & Formula"):
            st.markdown(aura_math)
            st.latex(r"I = \frac{n}{W} \frac{\sum_{i}\sum_{j} w_{ij}(z_i - \bar{z})(z_j - \bar{z})}{\sum_{i} (z_i - \bar{z})^2}")
    with col_c:
        if os.path.exists(P['moran']):
            st.image(P['moran'], caption=f"{prof['city_name']} Spatial Clustering (Moran Scatter)", width="stretch")
        else:
            st.info("Chart pending — run the pipeline to generate this plot.")
    st.markdown('</div>', unsafe_allow_html=True)  # close brilliant-card

    # ── Proof separator ───────────────────────────────────────────────────────
    st.markdown("""
    <div class="proof-sep">
      <div class="proof-sep-line"></div>
      <div class="proof-sep-label">Proof 2 follows</div>
      <div class="proof-sep-line"></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Proof 2: OLS Regression ──────────────────────────────────────────────
    st.markdown('<div class="brilliant-card">', unsafe_allow_html=True)

    if sel == 'hyderabad':
        proof2_tag   = "Proof 2 · OLS Regression"
        proof2_title = f"The {beta_raw:.2f}× Squeeze — Why Flent Lens is Mandatory in Hyderabad"
        ols_body = f"""
            <b>The Bottom Line:</b><br/>
            Hyderabad presents a structural challenge. Our regression shows a cost multiplier of <b>{beta_raw:.2f}×</b> —
            as we move into pricier neighbourhoods, the 3BHK acquisition cost rises faster than 1BHK revenue potential,
            compressing our margins. The breakeven floor is <b>{min_dd:.0%}</b> of a 1BHK's rent.
            Flent cannot expand blindly here; the pipeline must strictly target mid-tier markets or heavily discounted outliers.
        """
        ols_math = f"""
            - **β = {beta_raw:.2f}**: For every ₹1 rise in 1BHK retail rent, 3BHK acquisition cost jumps ₹{beta_raw:.2f} — spread shrinks in luxury wards.
            - **Breakeven floor ({min_dd:.0%})**: We must capture {min_dd:.0%} of a 1BHK's rent per room just to pay the landlord.
            - **R² = {r2_raw:.2f}**: Model explains {r2_raw*100:.1f}% of 3BHK cost variance — the margin squeeze is structural, not a data artifact.
        """
        pull_val2   = f"{beta_raw:.2f}×"
        pull_class2 = "orange"
        pull_cap2   = "Cost multiplier β — margin squeeze confirmed"
    else:
        proof2_tag   = "Proof 2 · OLS Regression"
        proof2_title = f"The {beta_raw:.2f}× Multiplier — Proving the Arbitrage Spread is Structural"
        ols_body = f"""
            <b>The Bottom Line:</b><br/>
            Our financial model relies on the spread between wholesale 3BHK acquisition cost and retail 1BHK demand.
            This regression proves the spread is <b>{'structurally massive' if beta_raw < 1 else 'present but sensitive'}</b>.
            For every ₹1 rise in market 1BHK rent, our 3BHK cost only rises by <b>₹{beta_raw:.2f}</b>.
            Flent only needs to capture <b>{min_dd:.0%}</b> of a 1BHK's rent per room to cover the master lease —
            charging 80% yields a highly defensible gross margin.
        """
        ols_math = f"""
            - **β = {beta_raw:.2f}**: Because β {'is well below 1' if beta_raw < 1 else 'tracks market growth'}, the arbitrage gap {'fundamentally widens' if beta_raw < 1 else 'remains stable'} in higher-priced wards.
            - **Minimum Breakeven ({min_dd:.0%})**: The mathematical floor — we only need {min_dd:.0%} of median 1BHK rent per room to pay for the 3BHK.
            - **R² = {r2_raw:.2f}**: {'Exceptionally low R² reveals extreme 3BHK pricing inefficiency — exactly why Flent cannot rely on gut-feel sourcing.' if r2_raw < 0.2 else 'Stable R² indicates an efficient, predictable market.'}
        """
        pull_val2   = f"{beta_raw:.2f}×"
        pull_class2 = "green" if beta_raw < 1 else "orange"
        pull_cap2   = "Cost multiplier β — arbitrage spread validated"

    st.markdown(f"""
    <div class="proof-header">
      <div class="proof-badge">P2</div>
      <div class="proof-header-text">
        <div class="proof-header-tag">{proof2_tag}</div>
        <div class="proof-header-title">{proof2_title}</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    col_v2, col_c2 = st.columns([1, 1], gap="large")
    with col_v2:
        st.markdown(
            f'<div class="pull-figure">'
            f'<div class="pull-figure-val {pull_class2}">{pull_val2}</div>'
            f'<div class="pull-figure-caption">{pull_cap2}</div>'
            f'</div>',
            unsafe_allow_html=True
        )
        st.markdown(f'<div class="plain-english">{ols_body}</div>', unsafe_allow_html=True)
        with st.expander("🔬 Behind the Number — Regression Specs & Formula"):
            st.markdown(ols_math)
            st.latex(r"Cost_{3BHK} = \alpha + \beta \cdot Rent_{1BHK} + \epsilon")
    with col_c2:
        if os.path.exists(P['ols_img']):
            st.image(P['ols_img'], caption=f"{prof['city_name']} Economic Proof: 1BHK Rent vs 3BHK Cost", width="stretch")
        else:
            st.info("Chart pending — run the pipeline to generate this plot.")


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
st.markdown(f"""
<div class="footer-strip">
  <div class="footer-left">
    <b>Flent Lens</b> — Rental Arbitrage Intelligence Platform<br>
    {prof['city_name']} · {len(df)} zones analysed · Pipeline output · April 2026<br>
    <span style="font-size:0.75rem;color:#5a7a9a;">Built by Harshith Bejjanki &amp; team · BBA Python Analytics</span>
  </div>
  <div class="footer-right">
    <span class="footer-tag">Stack: Python · GeoPandas · Statsmodels · Streamlit · Plotly</span>
    <a class="footer-badge" href="https://github.com/b-harshith/flent-lens" target="_blank">GitHub ↗</a>
  </div>
</div>
""", unsafe_allow_html=True)
