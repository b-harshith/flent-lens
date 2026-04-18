"""
Flent Lens — Source Code Manual Generator
==========================================
Converts the repository into a premium, print-ready PDF using the
exact Flent design token system from dashboard/index.html.

Requires: pip install markdown-it-py pygments playwright jinja2
          python3 -m playwright install (or use --channel=chrome)
"""
import os
import re
import asyncio
from markdown_it import MarkdownIt
from pygments.lexers import get_lexer_for_filename, TextLexer
from pygments.token import Token
from pygments.styles import get_style_by_name
from pygments import lex
from playwright.async_api import async_playwright

# ──────────────────────────────────────────────────────────────────────────────
# CONFIG
# ──────────────────────────────────────────────────────────────────────────────
PROJECT_DIR  = ".."
OUTPUT_HTML  = "../output/manual_temp_compile.html"
OUTPUT_PDF   = "../output/Flent_Lens_Source_Manual.pdf"
MAX_LINE_LEN = 88  # Chars before line is clipped with ↩ indicator

EXCLUDE_DIRS  = {'.git', 'venv', 'node_modules', '__pycache__', '.idea', '.vscode',
                 'output', 'Claude-skills-main', 'raw', 'processed', 'docs', 'dashboard'}
EXCLUDE_EXTS  = {'.pdf', '.docx', '.xlsx', '.png', '.jpg', '.jpeg', '.kml', '.geojson',
                 '.pyc', '.so', '.pyd', '.zip', '.tar', '.gz', '.DS_Store', '.csv'}
EXCLUDE_FILES = {'__init__.py', 'ARCHITECTURE.md', 'repo_to_pdf.py',
                 'requirements.txt', '.gitignore'}

PYGMENTS_STYLE = get_style_by_name('tango')

# Chapter dividers that appear before each logical group
CHAPTER_DIVIDERS = {
    'src/pipeline': {
        'num': '01', 'title': 'Data Pipeline',
        'desc': 'Pre-processing stages that clean Magicbricks rental listings, geocode SEZ locations via the Nominatim API, and generate 25-acre circle KML geometries for each Special Economic Zone in Bengaluru.'
    },
    'src/modules': {
        'num': '02', 'title': 'Analytical Engine',
        'desc': 'The core spatial-economic computation layer. Eight modules handle data ingestion, point-in-polygon ward joins, arbitrage margin modelling, demand & supply scoring, transit overlays, SEZ gravity models, composite opportunity indexing, and econometric validation.'
    },
    'src/utils': {
        'num': '03', 'title': 'Utilities & Export',
        'desc': 'Cross-cutting infrastructure. The terminal UI engine powers the narrative Rich logging interface. The export engine serialises final outputs to CSV, XLSX with conditional formatting, KML choropleths, and GeoJSON.'
    },
}

TEAM = [
    ("Harshith Bejjanki",  "SM24UBBA047"),
    ("Suneeth Boorgula",   "SM24UBBA016"),
    ("Sudhiksha",          "SM24UBBA033"),
    ("Peddi Sudeeksha",    "SM24UBBA027"),
    ("Vedanth Nagaarur",   "SM24UBBA019"),
]

# Per-module descriptive copy rendered before each file's code
MODULE_DESCRIPTIONS = {
    'README.md':                  ('Project Overview', 'This document explains the research context, business logic, and full methodology of the Flent Lens pipeline. Read this first to understand what the code is trying to solve before reviewing any individual module.'),
    'config.py':                  ('Global Configuration', 'All tunable parameters for the pipeline live here. Thresholds, file paths, weight allocations for scoring, and economic constants are centralised so they can be changed without editing any analytical logic. Review these values to understand the model\'s assumptions.'),
    'main.py':                    ('Pipeline Orchestrator', 'The entry point for the entire analysis. main.py calls each stage in the correct sequence and routes data between modules. Reading this file gives a bird\'s-eye view of the analytical workflow from raw data ingestion through to export.'),
    'cleaner.py':                 ('Magicbricks Data Cleaner', 'Ingests the raw Magicbricks CSV and enforces schema integrity. Extracts BHK counts from free-text titles, caps anomalous rents, and expels non-flat property types (villas, plots) that would distort median calculations. Outputs a clean, analysis-ready listings file.'),
    'geocoder.py':                ('SEZ Geocoder', 'Converts each SEZ name in the developer list into precise latitude/longitude coordinates using the free Nominatim API (OpenStreetMap). Adds rate-limiting delays to comply with the API\'s usage policy. Output feeds the KML mapper module.'),
    'mapper.py':                  ('SEZ Circle Mapper', 'Takes the geocoded SEZ coordinates and generates 25-acre (approx. 315m radius) circular polygons in KML format. These circles represent each SEZ\'s employment gravity field used in the spatial overlay scoring.'),
    'loader.py':                  ('Data Loader & Validator', 'The data ingestion gateway. Loads the four core datasets (listings CSV, BBMP wards KML, BMTC bus routes KML, SEZ KML), enforces coordinate reference system alignment to EPSG:4326, and exports processed intermediates for downstream modules.'),
    'spatial.py':                 ('Spatial Engine', 'Executes the core geographic computations: point-in-polygon joins to assign each listing to its BBMP ward, and route intersection analysis to measure bus connectivity per ward. Handles CRS projection, geometry repair, and nearest-neighbour fallback for listings that land outside ward boundaries.'),
    'aggregator.py':              ('Feature Aggregator', 'Collapses individual listing rows into per-ward summary statistics. Computes median rents by BHK type, percentage of large 3BHK+ listings, small-flat concentration (SFC), and price pressure indices — all with outlier removal via 3-sigma clipping.'),
    'economics.py':               ('Economic Modelling', 'The core valuation engine. Calculates arbitrage margin per ward (per-room revenue minus 3BHK/4BHK acquisition cost), the Demand Intensity Index (DII), Supply Feasibility Score (SFS), and the Effective Market Density index. These four metrics form the foundation of opportunity scoring.'),
    'transit.py':                 ('Transit Overlay', 'Quantifies bus connectivity per ward using BMTC route data. Scores each ward on route density and total route length relative to ward area. Acts as a negative modifier in the opportunity score — high transit cost means easier tenant sourcing but should not alone drive acquisition decisions.'),
    'sez.py':                     ('SEZ Gravity Model', 'Applies a distance-decay gravity function to measure employment proximity per ward. Wards near large, active SEZs score higher, reflecting higher latent demand for affordable co-living close to technology employment corridors.'),
    'scoring.py':                 ('Opportunity Scorer', 'Combines all economic, spatial, and overlay signals into a single composite Opportunity Score (0–120 scale). Applies neighborhood contagion boosts (Aura Effect) to wards adjacent to strong performers, and an isolation penalty to statistically anomalous wards disconnected from any investment cluster. Assigns Tier 1 / 2 / 3 / Excluded labels.'),
    'validator.py':               ('Econometric Validation', 'Runs two statistical tests to verify the model\'s assumptions. Moran\'s I confirms that rental prices cluster geographically (spatial autocorrelation). An OLS hedonic regression with HC3 robust errors measures the structural cost relationship between 1BHK and 3BHK rents, empirically validating the 0.80 demand discount factor.'),
    'exporter.py':                ('Export Engine', 'Serialises the final scored ward dataset to multiple output formats: a ranked CSV, a conditionally-formatted XLSX workbook, tier-coloured KML choropleths for Google Earth, individual listing pin maps, and a GeoJSON file for QGIS integration.'),
    'logger.py':                  ('Terminal UI Engine', 'Provides the narrative-driven Rich logging interface that runs in the terminal during pipeline execution. Defines the themed console, ASCII banner, stage headers, metric display, progress bar context manager, and the final dashboard summary. This module has no analytical logic — it exists purely to make the pipeline human-readable.'),
}

# ──────────────────────────────────────────────────────────────────────────────
# HTML MASTER TEMPLATE
# ──────────────────────────────────────────────────────────────────────────────
HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Flent Lens — Source Code Manual</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Playfair+Display:ital,wght@1,400;1,600&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
/* ────────────────────────────────────────────────────────────
   FLENT DESIGN TOKENS (exact mirror of dashboard/index.html)
──────────────────────────────────────────────────────────── */
:root {
  --cream:        #F5F0EB;
  --cream-deep:   #EDE7DF;
  --ivory:        #FAFAF7;
  --charcoal:     #1A1A1A;
  --carbon:       #2D2D2D;
  --stone:        #8B7355;
  --stone-light:  #B5A08A;
  --flent-black:  #111111;
  --sage:         #5C7A52;
  --sage-light:   #8BAE82;
  --sage-bg:      #EBF2E9;
  --rust:         #C4622D;
  --rust-bg:      #FAF0EA;
  --amber:        #D4924A;
  --border:       #E2DDD6;
  --border-light: #EDE9E3;
  --tag-bg:       #EDE8E1;
  --tag-text:     #6B5B47;
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-story:   'Playfair Display', Georgia, serif;
  --font-mono:    'JetBrains Mono', 'Courier New', monospace;
  --font-ui:      system-ui, -apple-system, 'Helvetica Neue', Helvetica, Arial, sans-serif;
}

/* ────────────────────────────────────────────────────────────
   BASE
──────────────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

html { background: var(--cream); }

body {
  font-family: var(--font-ui);
  background: var(--cream);
  color: var(--carbon);
  font-size: 11pt;
  line-height: 1.65;
  -webkit-print-color-adjust: exact;
  print-color-adjust: exact;
}

/* Safe inner wrapper — generous padding ensures nothing clips at print edges */
.page-wrapper {
  padding: 6mm 4mm 8mm 4mm;
}

/* ────────────────────────────────────────────────────────────
   PAGE GEOMETRY  (Playwright will also enforce margins)
──────────────────────────────────────────────────────────── */
@page {
  size: A4;
  /* Playwright handles margins; leave 0 here so we control layout */
  margin: 0;
}

/* ────────────────────────────────────────────────────────────
   COVER PAGE
──────────────────────────────────────────────────────────── */
.cover {
  min-height: 250mm;
  display: flex;
  flex-direction: column;
  page-break-after: always;
  background: var(--cream);
}

/* Zone A — black top strip */
.cover-header {
  background: var(--flent-black);
  padding: 18px 32px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.cover-header-logo {
  font-family: var(--font-display);
  font-size: 22px;
  color: #fff;
  letter-spacing: -0.01em;
  display: flex;
  align-items: center;
  gap: 10px;
}
.cover-header-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  background: var(--rust);
  flex-shrink: 0;
}
.cover-header-sub {
  font-family: var(--font-ui);
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: rgba(255,255,255,0.5);
}

/* Zone B — identity block */
.cover-body {
  flex: 1;
  padding: 52px 40px 36px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
}

.cover-eyebrow {
  font-family: var(--font-ui);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--stone-light);
  margin-bottom: 14px;
}

.cover-title-block { margin-bottom: 28px; }
.cover-project-name {
  font-family: var(--font-display);
  font-size: 52px;
  color: var(--charcoal);
  line-height: 1.05;
  letter-spacing: -0.02em;
}
.cover-project-name span { color: var(--rust); }

.cover-rule {
  width: 56px;
  height: 3px;
  background: var(--rust);
  margin: 18px 0;
  border-radius: 2px;
}

.cover-project-sub {
  font-family: var(--font-ui);
  font-size: 13px;
  font-weight: 400;
  color: var(--stone);
  line-height: 1.55;
  max-width: 380px;
}

/* Research question pull-quote */
.cover-question {
  font-family: var(--font-story);
  font-style: italic;
  font-size: 13px;
  color: var(--carbon);
  line-height: 1.65;
  border-left: 3px solid var(--rust);
  padding: 10px 18px;
  background: var(--rust-bg);
  border-radius: 0 6px 6px 0;
  max-width: 480px;
  margin: 24px 0 0;
}
.cover-question-label {
  font-family: var(--font-ui);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.15em;
  text-transform: uppercase;
  color: var(--rust);
  margin-bottom: 6px;
}

/* Zone C — team footer */
.cover-footer {
  border-top: 1px solid var(--border);
  padding: 24px 40px;
  background: var(--ivory);
}
.cover-footer-label {
  font-family: var(--font-ui);
  font-size: 8.5px;
  font-weight: 700;
  letter-spacing: 0.16em;
  text-transform: uppercase;
  color: var(--stone-light);
  margin-bottom: 12px;
}
.cover-team-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 4px 32px;
}
.cover-team-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 4px 0;
  border-bottom: 1px dotted var(--border);
  gap: 16px;
}
.cover-team-name {
  font-family: var(--font-ui);
  font-size: 11px;
  font-weight: 600;
  color: var(--charcoal);
}
.cover-team-id {
  font-family: var(--font-mono);
  font-size: 9.5px;
  color: var(--stone);
  background: var(--tag-bg);
  padding: 2px 7px;
  border-radius: 5px;
  white-space: nowrap;
}
.cover-meta-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 12px;
}
.cover-meta-text {
  font-family: var(--font-ui);
  font-size: 9px;
  color: var(--stone-light);
}

/* ────────────────────────────────────────────────────────────
   RUNNING HEADER (all pages after cover)
──────────────────────────────────────────────────────────── */
.running-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 6px 0 12px;
  border-bottom: 2px solid var(--border);
  margin-bottom: 28px;
}
.running-header-left {
  font-family: var(--font-display);
  font-size: 13px;
  color: var(--stone);
}
.running-header-right {
  font-family: var(--font-mono);
  font-size: 9px;
  color: var(--stone-light);
  letter-spacing: 0.06em;
}

/* ────────────────────────────────────────────────────────────
   MODULE DESCRIPTION BLURB
──────────────────────────────────────────────────────────── */
.module-blurb {
  background: var(--ivory);
  border: 1px solid var(--border);
  border-left: 3px solid var(--amber);
  border-radius: 0 8px 8px 0;
  padding: 18px 24px;
  margin-bottom: 28px;
}
.module-blurb-role {
  font-family: var(--font-ui);
  font-size: 7.5px;
  font-weight: 700;
  letter-spacing: 0.2em;
  text-transform: uppercase;
  color: var(--amber);
  margin-bottom: 8px;
}
.module-blurb-text {
  font-family: var(--font-ui);
  font-size: 11.5px;
  color: var(--stone);
  line-height: 1.85;
}

/* Note sidebar removed — space is provided purely by the
   wide right PDF margin enforced at the Playwright level. */

/* ────────────────────────────────────────────────────────────
   TABLE OF CONTENTS
──────────────────────────────────────────────────────────── */
.toc-page {
  page-break-after: always;
  padding: 0;
}
.toc-title {
  font-family: var(--font-display);
  font-size: 28px;
  color: var(--charcoal);
  margin-bottom: 6px;
}
.toc-subtitle {
  font-family: var(--font-ui);
  font-size: 11px;
  color: var(--stone);
  margin-bottom: 24px;
}
.toc-group { margin-bottom: 28px; }
.toc-group-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px solid var(--border);
}
.toc-group-stripe {
  width: 4px;
  height: 20px;
  border-radius: 3px;
  flex-shrink: 0;
}
.toc-group-label {
  font-family: var(--font-ui);
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--stone);
}
.toc-item {
  display: flex;
  align-items: baseline;
  gap: 0;
  padding: 7px 0 7px 16px;
}
.toc-item-name {
  font-family: var(--font-mono);
  font-size: 10.5px;
  color: var(--charcoal);
  font-weight: 500;
  white-space: nowrap;
}
.toc-item-dots {
  flex: 1;
  border-bottom: 1px dotted var(--border);
  margin: 0 10px;
  margin-bottom: 3px;
}
.toc-item-desc {
  font-family: var(--font-ui);
  font-size: 9px;
  color: var(--stone-light);
  white-space: nowrap;
}

/* ────────────────────────────────────────────────────────────
   CHAPTER DIVIDER PAGE
──────────────────────────────────────────────────────────── */
.chapter-divider {
  page-break-before: always;
  page-break-after: always;
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-height: 220mm;
  padding: 12mm 10mm 14mm;
}
.chapter-num {
  font-family: var(--font-display);
  font-size: 120px;
  color: var(--border);
  line-height: 1;
  margin-bottom: 0;
}
.chapter-rule {
  width: 56px;
  height: 3px;
  background: var(--rust);
  border-radius: 2px;
  margin: 14px 0 22px;
}
.chapter-title {
  font-family: var(--font-display);
  font-size: 42px;
  color: var(--charcoal);
  letter-spacing: -0.01em;
  margin-bottom: 20px;
}
.chapter-desc {
  font-family: var(--font-ui);
  font-size: 12.5px;
  color: var(--stone);
  line-height: 1.85;
  max-width: 460px;
}

/* ────────────────────────────────────────────────────────────
   MODULE / FILE PAGES
──────────────────────────────────────────────────────────── */
.module-page {
  page-break-before: always;
}

.module-file-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--flent-black);
  border-radius: 8px;
  padding: 14px 22px;
  margin-bottom: 24px;
}
.module-file-path {
  font-family: var(--font-mono);
  font-size: 11.5px;
  color: rgba(255,255,255,0.88);
  letter-spacing: 0.04em;
}
.module-file-badge {
  display: flex;
  align-items: center;
  gap: 12px;
}
.module-file-lang {
  font-family: var(--font-mono);
  font-size: 9px;
  font-weight: 700;
  color: #9DC88A;
  background: rgba(255,255,255,0.1);
  padding: 4px 12px;
  border-radius: 10px;
  letter-spacing: 0.06em;
}
.module-file-lines {
  font-family: var(--font-mono);
  font-size: 9px;
  color: rgba(255,255,255,0.45);
}

/* ────────────────────────────────────────────────────────────
   CODE BLOCK
──────────────────────────────────────────────────────────── */
.code-block {
  background: var(--ivory);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
  margin-bottom: 16px;
  padding: 8px 0;
  box-shadow: 0 1px 4px rgba(0,0,0,0.03);
}

.code-line {
  display: flex;
  align-items: baseline;
  min-height: 1.85em;
  line-height: 1.85;
}
.code-line:nth-child(even) { background: rgba(139,115,85,0.015); }

.code-gutter {
  width: 54px;
  min-width: 54px;
  text-align: right;
  padding: 0 14px 0 10px;
  font-family: var(--font-mono);
  font-size: 8pt;
  color: var(--stone-light);
  user-select: none;
  border-right: 1px solid var(--border-light);
  background: var(--cream);
  flex-shrink: 0;
  position: relative;
  z-index: 1;
}

.code-content {
  padding: 0 18px;
  font-family: var(--font-mono);
  font-size: 9pt;
  white-space: pre;
  flex: 1;
  overflow: hidden;
  tab-size: 4;
  letter-spacing: 0.015em;
}

/* Indent guide bars — subtle vertical lines per indent level */
.indent-1 .code-content { border-left: 2px solid #EAE5DC; padding-left: 16px; }
.indent-2 .code-content { border-left: 2px solid #E5DFD6; padding-left: 16px; }
.indent-3 .code-content { border-left: 2px solid #E0D9CF; padding-left: 16px; }

/* ────────────────────────────────────────────────────────────
   COMMENT CALLOUT (Flent story-card style)
──────────────────────────────────────────────────────────── */
.comment-callout {
  background: var(--sage-bg);
  border: 1px solid #C6DDBE;
  border-left: 3px solid var(--sage);
  border-radius: 0 8px 8px 0;
  padding: 14px 20px;
  margin: 14px 0 14px 54px;
}
.comment-callout-label {
  font-family: var(--font-ui);
  font-size: 7px;
  font-weight: 700;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  color: var(--sage);
  margin-bottom: 6px;
}
.comment-callout-text {
  font-family: var(--font-story);
  font-style: italic;
  font-size: 10.5pt;
  color: #2E4A36;
  line-height: 1.75;
}

/* ────────────────────────────────────────────────────────────
   MARKDOWN BODY  (README + any .md files)
──────────────────────────────────────────────────────────── */
.md-body {
  max-width: 100%;
  /* Generous vertical rhythm so the README feels like a proper document */
}
.md-body > * + * { margin-top: 0; }

/* h1 — only one per file, the project title */
.md-body h1 {
  font-family: var(--font-display);
  font-size: 28pt;
  color: var(--charcoal);
  letter-spacing: -0.02em;
  line-height: 1.1;
  border-bottom: 3px solid var(--rust);
  padding-bottom: 10px;
  margin: 0 0 20px;
}

/* h2 — section headings */
.md-body h2 {
  font-family: var(--font-display);
  font-size: 18pt;
  color: var(--charcoal);
  letter-spacing: -0.01em;
  border-bottom: 1px solid var(--border);
  padding-bottom: 6px;
  margin: 32px 0 14px;
}

/* h3 — sub-section labels */
.md-body h3 {
  font-family: var(--font-ui);
  font-size: 10.5pt;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.09em;
  color: var(--stone);
  margin: 24px 0 10px;
}

/* h4 — rarely used, treated as a bold label */
.md-body h4 {
  font-family: var(--font-ui);
  font-size: 10pt;
  font-weight: 700;
  color: var(--charcoal);
  margin: 18px 0 8px;
}

.md-body p {
  font-family: var(--font-ui);
  font-size: 11pt;
  color: var(--carbon);
  line-height: 1.78;
  margin-bottom: 14px;
}

.md-body ul, .md-body ol {
  padding-left: 24px;
  margin-bottom: 14px;
  font-family: var(--font-ui);
  font-size: 11pt;
  color: var(--carbon);
  line-height: 1.7;
}
.md-body li {
  margin-bottom: 5px;
}
.md-body li > p { margin-bottom: 4px; }

/* Nested lists — slight size reduction */
.md-body ul ul, .md-body ol ol, .md-body ul ol, .md-body ol ul {
  font-size: 10.5pt;
  margin-top: 4px;
  margin-bottom: 6px;
}

.md-body blockquote {
  border-left: 3px solid var(--rust);
  background: var(--rust-bg);
  border-radius: 0 8px 8px 0;
  padding: 14px 20px;
  margin: 18px 0;
  font-family: var(--font-story);
  font-style: italic;
  font-size: 12pt;
  color: var(--carbon);
  line-height: 1.7;
}
.md-body blockquote p { margin-bottom: 0; font-size: inherit; }

/* Inline code */
.md-body code {
  font-family: var(--font-mono);
  font-size: 9pt;
  background: var(--cream-deep);
  padding: 2px 6px;
  border-radius: 4px;
  color: var(--rust);
  white-space: nowrap;
}

/* Fenced code block */
.md-body pre {
  background: var(--ivory);
  border: 1px solid var(--border-light);
  border-left: 3px solid var(--sage);
  border-radius: 0 8px 8px 0;
  padding: 16px 20px;
  margin: 16px 0;
  font-family: var(--font-mono);
  font-size: 9pt;
  white-space: pre-wrap;
  word-break: break-word;
  overflow: hidden;
  color: var(--carbon);
  line-height: 1.65;
}
.md-body pre code {
  background: none;
  color: inherit;
  padding: 0;
  font-size: inherit;
  white-space: inherit;
}

/* Tables — Flent leaderboard aesthetic */
.md-body table {
  width: 100%;
  border-collapse: collapse;
  margin: 20px 0;
  font-family: var(--font-ui);
  font-size: 10pt;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid var(--border);
}
.md-body th {
  background: var(--flent-black);
  color: rgba(255,255,255,0.9);
  font-weight: 600;
  font-size: 8.5pt;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  padding: 10px 14px;
  text-align: left;
}
.md-body td {
  padding: 9px 14px;
  border-bottom: 1px solid var(--border-light);
  color: var(--carbon);
  vertical-align: top;
  line-height: 1.55;
}
.md-body tr:nth-child(even) td { background: var(--cream); }
.md-body tr:last-child td { border-bottom: none; }

/* Horizontal rule */
.md-body hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 28px 0;
}

/* Strong / em */
.md-body strong { color: var(--charcoal); font-weight: 700; }
.md-body em     { font-style: italic; color: var(--stone); }

/* Mermaid diagram container */
.mermaid-wrap {
  background: var(--ivory);
  border: 1px solid var(--border);
  border-radius: 10px;
  padding: 24px 20px;
  margin: 20px 0;
  display: flex;
  justify-content: center;
  overflow: hidden;
}

/* ────────────────────────────────────────────────────────────
   END OF STYLES
──────────────────────────────────────────────────────────── */
/* The right PDF margin (68mm) provides the physical note-taking
   space. No CSS overlay needed — it is guaranteed by Playwright. */

</style>
</head>
<body>

{CONTENT}

<script type="module">
  import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';
  mermaid.initialize({
    startOnLoad: true,
    theme: 'base',
    themeVariables: {
      primaryColor: '#EBF2E9',
      primaryTextColor: '#1A1A1A',
      primaryBorderColor: '#5C7A52',
      lineColor: '#8B7355',
      fontFamily: 'system-ui, -apple-system, Helvetica, Arial, sans-serif',
      fontSize: '12px',
    }
  });
</script>
</body>
</html>
"""

# ──────────────────────────────────────────────────────────────────────────────
# HELPERS
# ──────────────────────────────────────────────────────────────────────────────
def h(text):
    """HTML-escape a plain string."""
    return (str(text)
            .replace('&', '&amp;')
            .replace('<', '&lt;')
            .replace('>', '&gt;')
            .replace('"', '&quot;'))

def get_token_style(token):
    """Walk up the Pygments token tree to find a style."""
    while token not in PYGMENTS_STYLE.styles and token.parent:
        token = token.parent
    st = PYGMENTS_STYLE.style_for_token(token)
    css = []
    if st['color']:
        css.append(f"color:#{st['color']}")
    if st['bold']:
        css.append("font-weight:bold")
    if st['italic']:
        css.append("font-style:italic")
    return ";".join(css)

def indent_level(text):
    """Return leading indent level (0-3+) for indentation class."""
    spaces = len(text) - len(text.lstrip())
    return min(spaces // 4, 3)

def clip_line(text):
    """Clip a line longer than MAX_LINE_LEN and add a continuation marker."""
    if len(text) <= MAX_LINE_LEN:
        return text
    return text[:MAX_LINE_LEN] + "  ↩"

def sort_weight(path):
    p = path.lower()
    if p == 'readme.md':         return 0
    if p == 'config.py':         return 10
    if p == 'main.py':           return 20
    if p.startswith('src/pipeline'): return 30
    if p.startswith('src/module'):   return 40
    if p.startswith('src/util'):     return 50
    return 100

def collect_files():
    files = []
    for root, dirs, filenames in os.walk(PROJECT_DIR):
        dirs[:] = [d for d in dirs
                   if not d.startswith('.') and d not in EXCLUDE_DIRS]
        for fn in filenames:
            if fn in EXCLUDE_FILES:                              continue
            if fn.startswith('.'):                               continue
            if any(fn.endswith(e) for e in EXCLUDE_EXTS):       continue
            full = os.path.join(root, fn)
            rel  = os.path.relpath(full, PROJECT_DIR)
            files.append((full, rel))
    files.sort(key=lambda x: (sort_weight(x[1]), x[1]))
    return files

# ──────────────────────────────────────────────────────────────────────────────
# SECTION BUILDERS
# ──────────────────────────────────────────────────────────────────────────────
def build_cover():
    team_rows = ""
    for name, sid in TEAM:
        team_rows += f"""
        <div class="cover-team-row">
          <span class="cover-team-name">{h(name)}</span>
          <span class="cover-team-id">{h(sid)}</span>
        </div>"""

    # ── PAGE 1: Main cover ──────────────────────────────────────────────────
    page1 = f"""
<div class="cover">
  <div class="cover-header">
    <div class="cover-header-logo">
      <span>Flent</span>
      <div class="cover-header-dot"></div>
      <span>Lens</span>
    </div>
    <span class="cover-header-sub">Source Code Manual &nbsp;&#x2022;&nbsp; BBA Python Project &nbsp;&#x2022;&nbsp; 2026</span>
  </div>

  <div class="cover-body">
    <div>
      <div class="cover-eyebrow">Spatial&#x2011;Economic Analysis &nbsp;&#x2022;&nbsp; BBMP Ward Intelligence &nbsp;&#x2022;&nbsp; Bengaluru</div>

      <div class="cover-title-block">
        <div class="cover-project-name">Flent<br><span>Lens</span></div>
        <div class="cover-rule"></div>
        <div class="cover-project-sub">
          Ward Opportunity Analysis &amp; Rental Arbitrage Pipeline.<br>
          A spatial&#x2011;economic engine built to identify the highest&#x2011;return
          co&#x2011;living acquisition targets across 369 BBMP wards in Bengaluru.
        </div>
      </div>

      <div class="cover-question">
        <div class="cover-question-label">Central Research Question</div>
        Which areas in Bengaluru offer the most favourable combination of
        maximum per&#x2011;room arbitrage margin, highest availability of convertible
        3BHK+ properties, and strongest demand for shared living in premium
        furnished rooms?
      </div>
    </div>
  </div>

  <div class="cover-footer">
    <div class="cover-footer-label">Project Team &nbsp;&#x2014;&nbsp; Mahindra University School Of Management, BBA Programme</div>
    <div class="cover-team-grid">{team_rows}</div>
    <div class="cover-meta-row">
      <span class="cover-meta-text"> Hyderabad, Telangana, India &nbsp;&#x2022;&nbsp; April 2026</span>
      <span class="cover-meta-text">Flent Lens v2.0 &nbsp;&#x2022;&nbsp; Python 3.11</span>
    </div>
  </div>
</div>
"""

    # ── PAGE 2: What is a Price Arbitrage Model? ────────────────────────────
    page2 = """
<div class="cover" style="justify-content:flex-start;">
  <div class="cover-header">
    <div class="cover-header-logo">
      <span>Flent</span><div class="cover-header-dot"></div><span>Lens</span>
    </div>
    <span class="cover-header-sub">Conceptual Framework &nbsp;&#x2022;&nbsp; Page 2 of 3</span>
  </div>

  <div class="cover-body" style="padding-top:36px;">
    <div>
      <div class="cover-eyebrow">Understanding the Model</div>
      <div class="cover-title-block">
        <div class="cover-project-name" style="font-size:38px;">What is a<br><span>Price Arbitrage</span><br>Model?</div>
        <div class="cover-rule"></div>
      </div>

      <p style="font-family:var(--font-ui);font-size:12px;color:var(--carbon);line-height:1.8;max-width:500px;margin-bottom:18px;">
        Price arbitrage, in its simplest form, is the practice of <strong>buying low and selling high across two different market tiers</strong> that are structurally disconnected in pricing. In physical real estate, this occurs when a large apartment\'s bulk lease price is significantly below the sum of its individual room-level rents.
      </p>
      <p style="font-family:var(--font-ui);font-size:12px;color:var(--carbon);line-height:1.8;max-width:500px;margin-bottom:24px;">
        Flent operates this model by acting as an institutional lessee. A 3BHK+ flat is leased at its <strong>ward-level 25th-percentile rent</strong> &#x2014; capturing distressed, dated, or bulk inventory. The property is then furnished, branded, and sub-let as individual premium co-living rooms at rates benchmarked against the ward\'s <strong>median 1BHK rent</strong>. The spread between these two price layers is the <em>arbitrage margin</em> &#x2014; Flent\'s primary revenue mechanism.
      </p>

      <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;max-width:560px;margin-bottom:24px;">
        <div style="background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:14px 16px;">
          <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--rust);margin-bottom:6px;">Step 1</div>
          <div style="font-family:var(--font-ui);font-size:11px;font-weight:600;color:var(--charcoal);margin-bottom:4px;">Acquire</div>
          <div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);line-height:1.6;">Lease a 3BHK/4BHK at Q25 ward rent. Lower price bracket = higher arbitrage ceiling.</div>
        </div>
        <div style="background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:14px 16px;">
          <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--stone);margin-bottom:6px;">Step 2</div>
          <div style="font-family:var(--font-ui);font-size:11px;font-weight:600;color:var(--charcoal);margin-bottom:4px;">Convert</div>
          <div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);line-height:1.6;">Divide and furnish as 3&#x2013;5 premium co-living rooms. Add amenities that command a rental premium.</div>
        </div>
        <div style="background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:14px 16px;">
          <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--sage);margin-bottom:6px;">Step 3</div>
          <div style="font-family:var(--font-ui);font-size:11px;font-weight:600;color:var(--charcoal);margin-bottom:4px;">Earn</div>
          <div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);line-height:1.6;">Collect per-room rents at ~80% of median 1BHK price. The margin is the spread.</div>
        </div>
      </div>

      <div style="background:var(--rust-bg);border-left:3px solid var(--rust);border-radius:0 6px 6px 0;padding:14px 20px;max-width:520px;">
        <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.16em;text-transform:uppercase;color:var(--rust);margin-bottom:6px;">The Formula</div>
        <div style="font-family:var(--font-mono);font-size:11px;color:var(--carbon);line-height:1.8;">
          per_room_revenue = median_rent_1bhk &times; 0.80<br>
          arb_margin_3bhk &nbsp;= (per_room_revenue &times; 3) &minus; Q25_rent_3bhk<br>
          arb_margin_4bhk &nbsp;= (per_room_revenue &times; 4) &minus; Q25_rent_4bhk<br>
          <strong>arb_margin_best &nbsp;= max(3bhk, 4bhk)</strong>
        </div>
      </div>
    </div>
  </div>
</div>
"""

    # ── PAGE 3: Methodology & Scoring Framework ─────────────────────────────
    page3 = """
<div class="cover" style="justify-content:flex-start;">
  <div class="cover-header">
    <div class="cover-header-logo">
      <span>Flent</span><div class="cover-header-dot"></div><span>Lens</span>
    </div>
    <span class="cover-header-sub">Scoring Methodology &nbsp;&#x2022;&nbsp; Page 3 of 3</span>
  </div>

  <div class="cover-body" style="padding-top:36px;">
    <div>
      <div class="cover-eyebrow">How Opportunity Scores are Computed</div>
      <div class="cover-title-block">
        <div class="cover-project-name" style="font-size:36px;">The<br><span>Scoring</span><br>Framework</div>
        <div class="cover-rule"></div>
      </div>

      <p style="font-family:var(--font-ui);font-size:11.5px;color:var(--carbon);line-height:1.8;max-width:520px;margin-bottom:20px;">
        The pipeline assigns every BBMP ward a composite <strong>Opportunity Score (0&#x2013;120)</strong> derived from three economic pillars and two spatial overlays. Tiers are assigned using percentile thresholds calculated only on <em>eligible</em> wards where margin viability is confirmed.
      </p>

      <div style="display:grid;grid-template-columns:1fr;gap:8px;max-width:520px;margin-bottom:22px;">
        <div style="display:flex;align-items:center;gap:14px;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:12px 16px;">
          <div style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:var(--rust);min-width:40px;text-align:center;">45%</div>
          <div><div style="font-family:var(--font-ui);font-size:11px;font-weight:700;color:var(--charcoal);">Arbitrage Margin</div><div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);">Spread between per-room revenue and 3/4BHK acquisition cost. The primary viability signal.</div></div>
        </div>
        <div style="display:flex;align-items:center;gap:14px;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:12px 16px;">
          <div style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:var(--stone);min-width:40px;text-align:center;">30%</div>
          <div><div style="font-family:var(--font-ui);font-size:11px;font-weight:700;color:var(--charcoal);">Demand Intensity Index (DII)</div><div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);">Price pressure + small-flat concentration + rent-per-sqft spread. Measures tenant demand.</div></div>
        </div>
        <div style="display:flex;align-items:center;gap:14px;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:12px 16px;">
          <div style="font-family:var(--font-mono);font-size:20px;font-weight:700;color:var(--amber);min-width:40px;text-align:center;">25%</div>
          <div><div style="font-family:var(--font-ui);font-size:11px;font-weight:700;color:var(--charcoal);">Supply Feasibility Score (SFS)</div><div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);">Volume, size adequacy, and ROI of 3BHK+ stock available for conversion.</div></div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:520px;margin-bottom:22px;">
        <div style="background:var(--sage-bg);border:1px solid #C6DDBE;border-radius:8px;padding:12px 14px;">
          <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:var(--sage);margin-bottom:5px;">+10% Boost</div>
          <div style="font-family:var(--font-ui);font-size:10.5px;font-weight:600;color:var(--charcoal);margin-bottom:3px;">Aura Effect</div>
          <div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);">Wards adjacent to Tier 1 hubs inherit a spillover valuation premium, rewarding cluster density.</div>
        </div>
        <div style="background:var(--rust-bg);border:1px solid #F0C4AC;border-radius:8px;padding:12px 14px;">
          <div style="font-family:var(--font-ui);font-size:8px;font-weight:700;letter-spacing:0.14em;text-transform:uppercase;color:var(--rust);margin-bottom:5px;">&#x2212;15% Penalty</div>
          <div style="font-family:var(--font-ui);font-size:10.5px;font-weight:600;color:var(--charcoal);margin-bottom:3px;">Island Penalty</div>
          <div style="font-family:var(--font-ui);font-size:10px;color:var(--stone);">Isolated Tier 1 wards surrounded entirely by low-performing zones are penalised for scalability risk.</div>
        </div>
      </div>

      <div style="display:grid;grid-template-columns:repeat(4,1fr);gap:10px;max-width:520px;">
        <div style="text-align:center;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:10px 8px;">
          <div style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:#3A6B32;">&ge;75th</div>
          <div style="font-family:var(--font-ui);font-size:9px;font-weight:700;color:#3A6B32;margin-top:4px;">TIER 1</div>
          <div style="font-family:var(--font-ui);font-size:9px;color:var(--stone);margin-top:2px;">Priority</div>
        </div>
        <div style="text-align:center;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:10px 8px;">
          <div style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:#8B5E1A;">&ge;50th</div>
          <div style="font-family:var(--font-ui);font-size:9px;font-weight:700;color:#8B5E1A;margin-top:4px;">TIER 2</div>
          <div style="font-family:var(--font-ui);font-size:9px;color:var(--stone);margin-top:2px;">Pipeline</div>
        </div>
        <div style="text-align:center;background:var(--ivory);border:1px solid var(--border);border-radius:8px;padding:10px 8px;">
          <div style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:#2A5F8A;">&ge;25th</div>
          <div style="font-family:var(--font-ui);font-size:9px;font-weight:700;color:#2A5F8A;margin-top:4px;">TIER 3</div>
          <div style="font-family:var(--font-ui);font-size:9px;color:var(--stone);margin-top:2px;">Watch</div>
        </div>
        <div style="text-align:center;background:var(--tag-bg);border:1px solid var(--border);border-radius:8px;padding:10px 8px;">
          <div style="font-family:var(--font-mono);font-size:12px;font-weight:700;color:var(--stone-light);">&#x3c;25th</div>
          <div style="font-family:var(--font-ui);font-size:9px;font-weight:700;color:var(--stone-light);margin-top:4px;">EXCL.</div>
          <div style="font-family:var(--font-ui);font-size:9px;color:var(--stone);margin-top:2px;">Excluded</div>
        </div>
      </div>
    </div>
  </div>
</div>
"""
    return page1 + page2 + page3

def build_toc(files):
    groups = {
        'root':         ('Configuration & Entry Point', '#C4622D', []),
        'src/pipeline': ('Pipeline — Data Extraction',  '#4A7BA8', []),
        'src/modules':  ('Engine — Analytical Modules', '#5C7A52', []),
        'src/utils':    ('Utilities & Export',          '#9B6FD4', []),
    }
    for full, rel in files:
        r = rel.lower()
        if 'src/pipeline' in r:      groups['src/pipeline'][2].append(rel)
        elif 'src/modules' in r:     groups['src/modules'][2].append(rel)
        elif 'src/utils' in r:       groups['src/utils'][2].append(rel)
        else:                        groups['root'][2].append(rel)

    html = '<div class="toc-page">\n'
    html += '<div class="running-header"><span class="running-header-left">Flent Lens</span>'
    html += '<span class="running-header-right">TABLE OF CONTENTS</span></div>\n'
    html += '<div class="toc-title">Table of Contents</div>\n'
    html += '<div class="toc-subtitle">Source code organised by pipeline execution order</div>\n'

    for key, (label, color, items) in groups.items():
        if not items: continue
        html += f'<div class="toc-group">\n'
        html += f'''<div class="toc-group-header">
          <div class="toc-group-stripe" style="background:{color}"></div>
          <span class="toc-group-label">{h(label)}</span>
        </div>\n'''
        for rel in items:
            fn = os.path.basename(rel)
            html += f'''<div class="toc-item">
              <span class="toc-item-name">{h(fn)}</span>
              <span class="toc-item-dots"></span>
              <span class="toc-item-desc">{h(rel)}</span>
            </div>\n'''
        html += '</div>\n'

    html += '</div>\n'
    return html

def build_chapter_divider(key):
    ch = CHAPTER_DIVIDERS[key]
    return f"""
<div class="chapter-divider">
  <div class="chapter-num">{h(ch['num'])}</div>
  <div class="chapter-rule"></div>
  <div class="chapter-title">{h(ch['title'])}</div>
  <div class="chapter-desc">{h(ch['desc'])}</div>
</div>
"""

def render_markdown(full_path):
    with open(full_path, 'r', encoding='utf-8') as f:
        raw = f.read()
    md = MarkdownIt()
    html = md.render(raw)
    # Swap mermaid code blocks for Mermaid.js divs
    html = re.sub(
        r'<pre><code class="language-mermaid">(.*?)</code></pre>',
        lambda m: f'<div class="mermaid-wrap"><div class="mermaid">{m.group(1)}</div></div>',
        html, flags=re.DOTALL
    )
    return f'<div class="md-body">\n{html}\n</div>'

def render_code(full_path):
    with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
        raw = f.read()

    try:
        lexer = get_lexer_for_filename(full_path)
    except Exception:
        lexer = TextLexer()

    # Tokenise and group by line
    tokens = list(lex(raw, lexer))
    lines = []
    current = []
    for ttype, val in tokens:
        parts = val.split('\n')
        for i, part in enumerate(parts):
            if part:
                current.append((ttype, part))
            if i < len(parts) - 1:
                lines.append(current)
                current = []
    if current:
        lines.append(current)

    html = '<div class="code-block">\n'
    comment_accum = []

    def flush_comment():
        nonlocal comment_accum
        if not comment_accum:
            return ''
        text = ' '.join(comment_accum).strip()
        # Strip comment markers
        text = re.sub(r'^[#\s\/\*]+', '', text).strip()
        text = text.strip('"\'').strip()
        comment_accum = []
        if not text:
            return ''
        return f'''<div class="comment-callout">
          <div class="comment-callout-label">Annotation</div>
          <div class="comment-callout-text">{h(text)}</div>
        </div>\n'''

    line_idx = 1
    for line in lines:
        # Build full text
        full_text = ''.join(v for _, v in line)
        stripped   = full_text.strip()

        # Detect pure-comment lines
        non_ws = [(t, v) for t, v in line if v.strip()]
        is_comment = bool(non_ws) and all(
            t in Token.Comment or t in Token.String.Doc
            for t, v in non_ws
        )

        if is_comment and stripped:
            comment_accum.append(stripped)
            line_idx += 1
            continue
        else:
            html += flush_comment()

        indent = indent_level(full_text)
        indent_class = f'indent-{indent}' if indent > 0 else ''

        # Clip long lines
        clipped = clip_line(full_text)
        line_html = ''
        if clipped == full_text:
            # Syntax-colour token by token
            offset = 0
            for ttype, val in line:
                if offset >= MAX_LINE_LEN:
                    break
                chunk = val[:MAX_LINE_LEN - offset]
                offset += len(chunk)
                style = get_token_style(ttype)
                escaped = h(chunk)
                if style:
                    line_html += f'<span style="{style}">{escaped}</span>'
                else:
                    line_html += escaped
        else:
            line_html = h(clipped[:MAX_LINE_LEN]) + '<span style="color:#B5A08A"> ↩</span>'

        html += f'''<div class="code-line {indent_class}">
          <span class="code-gutter">{line_idx}</span>
          <span class="code-content">{line_html}</span>
        </div>\n'''
        line_idx += 1

    html += flush_comment()
    html += '</div>\n'
    return html, line_idx - 1

def render_file(full_path, rel_path):
    try:
        with open(full_path, 'r', encoding='utf-8', errors='replace') as f:
            pass
        size = os.path.getsize(full_path)
    except Exception:
        return ''
    if size > 250_000:
        return ''

    ext   = os.path.splitext(full_path)[1].upper().lstrip('.') or 'TXT'
    fn    = os.path.basename(rel_path)

    if full_path.endswith('.md'):
        body  = render_markdown(full_path)
        lines = body.count('\n')
        lang  = 'Markdown'
    else:
        body, lines = render_code(full_path)
        lang = ext

    # Look up module description
    desc_key = fn
    role, desc_text = MODULE_DESCRIPTIONS.get(fn, ('', ''))
    blurb = ''
    if role:
        blurb = f"""
  <div class="module-blurb">
    <div class="module-blurb-role">{h(role)}</div>
    <div class="module-blurb-text">{h(desc_text)}</div>
  </div>"""

    return f"""
<div class="module-page page-wrapper">
  <div class="running-header">
    <span class="running-header-left">Flent Lens &nbsp;&#xb7;&nbsp; Source Manual</span>
    <span class="running-header-right">{h(rel_path)}</span>
  </div>
  <div class="module-file-header">
    <span class="module-file-path">{h(rel_path)}</span>
    <div class="module-file-badge">
      <span class="module-file-lang">{h(lang)}</span>
      <span class="module-file-lines">{lines} lines</span>
    </div>
  </div>
  {blurb}
  {body}
</div>
"""

# ──────────────────────────────────────────────────────────────────────────────
# MAIN PIPELINE
# ──────────────────────────────────────────────────────────────────────────────
async def generate():
    os.makedirs('output', exist_ok=True)
    files = collect_files()
    print(f"[Flent Lens PDF] Found {len(files)} source files\n")

    content = build_cover()
    # TOC wrapped in page-wrapper for safe padding
    toc_raw = build_toc(files)
    content += f'<div class="page-wrapper">{toc_raw}</div>'

    divider_emitted = set()
    for full, rel in files:
        for prefix, ch_key in [('src/pipeline', 'src/pipeline'),
                                ('src/modules',  'src/modules'),
                                ('src/utils',    'src/utils')]:
            if rel.lower().startswith(prefix) and ch_key not in divider_emitted:
                content += build_chapter_divider(ch_key)
                divider_emitted.add(ch_key)
                # Chapter dividers get page-wrapper too
                # (already handled inside the chapter div CSS)

        print(f"  → {rel}")
        content += render_file(full, rel)

    final_html = HTML_TEMPLATE.replace('{CONTENT}', content)
    with open(OUTPUT_HTML, 'w', encoding='utf-8') as f:
        f.write(final_html)
    print(f"\n[HTML] Written: {OUTPUT_HTML}")

    print("[Browser] Launching Chrome for PDF conversion...")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel='chrome')
        page    = await browser.new_page(viewport={'width': 1240, 'height': 1754})
        abs_path = os.path.abspath(OUTPUT_HTML)
        await page.goto(f'file://{abs_path}', wait_until='networkidle')
        # Let Google Fonts + Mermaid render
        await page.wait_for_timeout(3500)
        await page.pdf(
            path=OUTPUT_PDF,
            format='A4',
            print_background=True,
            margin={
                'top':    '28mm',
                'bottom': '26mm',
                'left':   '22mm',
                'right':  '62mm',
            }
        )
        await browser.close()

    size_kb = os.path.getsize(OUTPUT_PDF) // 1024
    print(f"[PDF] Generated: {OUTPUT_PDF}  ({size_kb} KB)")

def main():
    asyncio.run(generate())

if __name__ == '__main__':
    main()
