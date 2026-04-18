# Flent Lens — Architecture Reference v3.0

*April 2026 — reflects post-dashboard modernization*

---

## 1. System Overview

Flent Lens has two runtime modes:

```
┌──────────────────────────────────────────────────────────────┐
│  MODE A: CLI Pipeline                                        │
│  python main.py                                              │
│  → Reads config.py directly → Runs 9 stages → Writes output │
└──────────────────────────────────────────────────────────────┘

┌──────────────────────────────────────────────────────────────┐
│  MODE B: Dashboard                                           │
│  venv/bin/python3.14 dashboard/app.py                        │
│  → Serves http://localhost:5050                              │
│  → Holds session config in memory (config.py untouched)      │
│  → Spawns pipeline subprocess with overridden values         │
│  → Streams output to browser via SSE                         │
└──────────────────────────────────────────────────────────────┘
```

---

## 2. Full Directory Structure

```
BBA_Python_final/
│
├── main.py                     ← Pipeline entry point (Stages 0–8)
├── config.py                   ← ALL configuration — paths, weights, thresholds
├── requirements.txt            ← Python dependencies
├── README.md                   ← Project overview and usage guide
├── ARCHITECTURE.md             ← This document
├── BBA Python Project.docx     ← Original course methodology brief
│
├── dashboard/                  ← Leadership Dashboard
│   ├── app.py                  ← Flask server (session config + SSE + GeoJSON API)
│   ├── index.html              ← Full-stack SPA (HTML + CSS + Vanilla JS)
│   └── run_with_overrides.py   ← Pipeline subprocess shim (patches config in-memory)
│
├── docs/                       ← Product documentation
│   └── CONSUMER_FINDER_SPEC.md ← Smart Apartment Finder feature spec (future)
│
├── data/
│   ├── raw/                    ← Unmodified source data (do not edit)
│   │   ├── magicbricks_final_listings.csv
│   │   ├── gba-369-wards-december-2025.kml
│   │   ├── bmtc_bus_routes.kml
│   │   └── SEZ List/SEZ list - Sheet1.csv
│   └── processed/              ← Auto-generated (recreated on each run)
│       ├── listings.csv
│       ├── sez_latlong.csv
│       ├── sez_enriched_wards.kml
│       ├── wards_processed.csv
│       └── transit_processed.csv
│
├── src/
│   ├── pipeline/
│   │   ├── cleaner.py
│   │   ├── geocoder.py
│   │   └── mapper.py
│   ├── modules/
│   │   ├── loader.py
│   │   ├── spatial.py
│   │   ├── aggregator.py
│   │   ├── economics.py
│   │   ├── transit.py
│   │   ├── sez.py
│   │   ├── scoring.py
│   │   └── validator.py
│   └── utils/
│       ├── logger.py
│       └── exporter.py
│
├── output/                     ← Analytical deliverables (git-ignored)
│   ├── flent_investment_atlas.kml
│   ├── flent_lens_report.xlsx
│   ├── ward_analysis.geojson
│   ├── moran_scatterplot_*.png
│   └── ols_arbitrage_validation.png
│
├── venv/                       ← Python virtual environment (git-ignored)
│   ├── lib/python3.12/         ← Analysis pipeline dependencies
│   └── lib/python3.14/         ← Flask + dashboard dependencies
│
└── Claude-skills-main/         ← Claude AI skill definitions (reference)
```

> **Note on venv:** Two Python versions coexist. `python3.12` hosts geospatial libs (geopandas, fiona, libpysal). `python3.14` hosts Flask. Use `venv/bin/python3.14` to start the dashboard; `venv/bin/python main.py` for the analysis pipeline.

---

## 3. Data Flow

```
Raw Data (data/raw/)
        │
        ▼
Pre-Processing (src/pipeline/)
  cleaner.py   → data/processed/listings.csv
  geocoder.py  → data/processed/sez_latlong.csv
  mapper.py    → data/processed/sez_enriched_wards.kml
        │
        ▼
Data Ingestion (src/modules/loader.py)
  Loads: listings GDF, wards GDF (KML), routes GDF (KML), SEZ GDF
        │
        ▼
Spatial Engine (src/modules/spatial.py)
  Point-in-polygon ward assignment (with proximity fallback)
  Route clipping to ward boundaries
        │
        ▼
Feature Engineering (src/modules/aggregator.py)
  Outlier removal per ward-BHK group (σ-threshold)
  Ward-level medians, SFC, PSF spread, pct_3bhk_large
        │
        ▼
Economic Model (src/modules/economics.py)
  Arbitrage margin (3BHK + 4BHK, best-of)
  Dynamic yield rooms (size-tiered)
  Demand Intensity Index (DII)
  Supply Feasibility Score (SFS)
  Effective Margin Density (EMD)
        │
        ├──→ Transit Score (src/modules/transit.py)
        │    BMTC route density + length per ward
        │
        └──→ SEZ Score (src/modules/sez.py)
             Gravity model: score = 1 / (distance^α)
        │
        ▼
Opportunity Indexing (src/modules/scoring.py)
  Composite OPP_SCORE from weighted ECON + overlays
  Spatial spillover boosts (Queen contiguity neighbors)
  Island penalty for isolated Tier 1 wards
  Percentile-based tier assignment (Tier 1/2/3/Excluded)
        │
        ▼
Validation (src/modules/validator.py)
  Moran's I spatial autocorrelation
  Hedonic OLS: Q25_3BHK ~ Median_1BHK (proves 0.80 factor)
        │
        ▼
Export (src/utils/exporter.py)
  flent_investment_atlas.kml  (multi-layer Google Earth file)
  flent_lens_report.xlsx      (4-sheet executive report)
  ward_analysis.geojson       (dashboard + QGIS)
```

---

## 4. Dashboard Architecture

```
Browser (http://localhost:5050)
     │
     ├── GET /               → index.html (full SPA)
     ├── GET /api/config     → SESSION_CONFIG (in-memory, enriched with metadata)
     ├── POST /api/config    → updates SESSION_CONFIG only (never config.py)
     ├── POST /api/config/reset → restores SESSION_CONFIG from ORIGINAL_CONFIG
     ├── POST /api/run       → triggers pipeline subprocess
     ├── GET /api/stream     → SSE stream of pipeline stdout
     ├── GET /api/status     → running / idle + change count
     └── GET /api/geojson    → serves output/ward_analysis.geojson
```

### Session Config Isolation — How It Works

The dashboard maintains **two config objects in memory**:

```python
ORIGINAL_CONFIG  # Deep copy of config.py at server startup — NEVER modified
SESSION_CONFIG   # Mutable working copy — modified by UI sliders/steppers
```

When the pipeline is triggered from the dashboard:

1. `SESSION_CONFIG` is written to a temp JSON at `dashboard/.session_overrides.json`
2. A subprocess runs `run_with_overrides.py /path/to/.session_overrides.json`
3. `run_with_overrides.py` imports `config`, then patches each attribute in-memory:
   ```python
   import config
   for key, val in overrides.items():
       setattr(config, key, type(getattr(config, key))(val))
   import main
   main.run_pipeline()
   ```
4. The temp JSON is deleted after the subprocess exits
5. `config.py` on disk is **never touched at any point**

### Auto-Rerun Debounce

Every slider/stepper change:
1. POSTs immediately to `/api/config` → updates SESSION_CONFIG
2. Cancels any pending debounce timer
3. Starts a new 3-second countdown
4. After 3s of no further changes → triggers `/api/run`

This prevents the pipeline from firing on every slider tick.

### Pipeline Log Streaming (SSE)

```
Server (Flask)             Browser
  pipeline subprocess           EventSource('/api/stream')
  stdout line-by-line    →      onmessage: append to log box
  generator yields SSE          auto-scrolls, colour-coded
  frames                        closes stream on 'done' event
```

---

## 5. Module Reference

### `main.py` — Pipeline Orchestrator
- Entry point for both direct CLI and dashboard subprocess invocations
- Runs 9 stages in sequence, passes DataFrames between stages in memory
- Lazy evaluation: skips pre-processing if cached files exist

### `config.py` — Configuration
- Single source of truth for all paths (absolute, relative to `BASE_DIR`)
- All analytical thresholds, weights, and model parameters
- **Never modified by the dashboard** — see session config architecture above

### `src/pipeline/cleaner.py`
- Parses raw Magicbricks CSV
- Extracts `bhk_type` via regex on title/description
- Removes non-flat types (villas, plots, PGs)
- Enforces `MAX_VALID_1BHK_RENT` cap
- Deduplicates on `(title, locality, price)` composite key

### `src/pipeline/geocoder.py`
- Geocodes SEZ names to lat/lon via Nominatim (OpenStreetMap)
- Caches results to `data/processed/sez_latlong.csv`

### `src/pipeline/mapper.py`
- Takes geocoded SEZ points
- Generates 25-acre circle polygons (radius ≈ 179m) in KML format
- Applies category-based color coding per SEZ type

### `src/modules/loader.py`
- Loads KML files using `fiona` with `ENABLE_DRIVERS` env var
- Parses complex KML `SchemaData` for ward names and attributes
- Validates GeoDataFrame schemas before analysis

### `src/modules/spatial.py`
- `compute_ward_areas()` — projects to UTM 43N, computes area in km²
- `assign_listings_to_wards()` — point-in-polygon with `NEAREST_WARD_MAX_DISTANCE_M` proximity fallback
- `clip_routes_to_wards()` — clips BMTC routes to ward boundaries

### `src/modules/aggregator.py`
- `remove_outliers_by_group()` — removes listings > N×σ from ward-BHK median
- `aggregate_ward_features()` — medians, counts, SFC, PSF spread per ward
- `compute_derived_columns()` — pct_3bhk_large, supply ratios

### `src/modules/economics.py`
- `compute_arbitrage_margin()` — dynamic yield model (3/3.5/4/5 rooms by sqft)
- `compute_demand_intensity_index()` — DII composite
- `compute_supply_feasibility_score()` — SFS composite
- `compute_effective_margin_density()` — EMD per km²

### `src/modules/transit.py`
- Computes per-ward BMTC route density (routes/km²) and total route length
- Normalizes and weights into `transit_score ∈ [0, 1]`

### `src/modules/sez.py`
- Computes distance from each ward centroid to each SEZ zone
- Applies gravity decay: `score = Σ (1 / max(dist, SEZ_MIN_DISTANCE_M)^α)`
- Normalizes to `sez_employment_score ∈ [0, 1]`

### `src/modules/scoring.py`
- `compute_opportunity_score()` — weighted composite from ECON + overlays
- `apply_spatial_spillover()` — Queen contiguity matrix, aura boosts, island penalty
- `assign_tiers()` — percentile thresholds on eligible wards only

### `src/modules/validator.py`
- `run_morans_i()` — spatial autocorrelation with Queen weights, saves scatterplot
- `run_arbitrage_ols()` — structural regression, HC3 errors, saves diagnostic plot

### `src/utils/exporter.py`
- `export_investment_atlas_kml()` — multi-layer KML with ward polygons + listing pins
- `export_lens_report_xlsx()` — 4-sheet XLSX with conditional formatting
- `export_geojson()` — full ward dataset as GeoJSON for dashboard

### `src/utils/logger.py`
- Powered by `rich` — spinners, colored panels, metrics display
- `print_stage()`, `print_metric()`, `print_narrative()` etc.
- `display_final_dashboard()` — terminal summary table at pipeline completion

---

## 6. Key Design Decisions

### Why in-memory session config (not file-based)?
Writing directly to `config.py` would permanently alter the analytical model between sessions. A leadership user wishing to explore "what if I change the margin threshold?" should never accidentally overwrite the validated baseline configuration. The session model guarantees safety — the server restart is the atomic reset.

### Why Flask (not a heavier framework)?
The dashboard is a local tool, not a production web app. Flask's zero-config startup, single-file server, and built-in SSE support via `Response(generator, mimetype='text/event-stream')` are exactly sufficient. No build step, no npm, no bundle — the entire frontend is one HTML file served from disk.

### Why SSE (not WebSockets) for log streaming?
SSE is unidirectional (server → browser), which is exactly the requirement: the server streams pipeline stdout, the browser just renders it. SSE is simpler than WebSockets for this use case, natively supported in all modern browsers, and integrates cleanly with Flask's generator-based response model.

### Why Leaflet + CartoDB (not Google Maps)?
No API key required. CartoDB Positron's clean, light basemap is visually consistent with Flent's cream aesthetic. Leaflet handles GeoJSON natively and is well-suited for ward-polygon choropleth rendering.

---

## 7. Environment Notes

```bash
# Start dashboard (uses Python 3.14 venv with Flask)
venv/bin/python3.14 dashboard/app.py

# Run pipeline directly (uses Python 3.12 venv with geospatial libs)
venv/bin/python main.py

# Install Flask (if missing)
venv/bin/pip install flask

# Check which Python has which packages
venv/bin/python3.12 -c "import geopandas; print('geopandas OK')"
venv/bin/python3.14 -c "from flask import Flask; print('flask OK')"
```

The venv contains two Python interpreters because the project was initialized with Python 3.12 (for geospatial library compatibility) and later upgraded to 3.14 for Flask. Both coexist safely.

---

## 8. What Was Removed (Cleanup, April 2026)

| File | Reason |
|------|--------|
| `test_excel_fmt.py` | One-off test script, no longer needed |
| `test_fmt.xlsx` | Test output artifact |
| `flent-lens-video/` | Remotion animation project moved out |
| All `__pycache__/` dirs | Cleaned; recreate on next run |

---

*Flent Lens Architecture — last updated April 2026*
