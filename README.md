# 🔍 Flent Lens

> **Navigate Bengaluru's Co-Living Arbitrage Landscape**

*A spatial-economic analysis pipeline + leadership dashboard that identifies BBMP wards with maximum per-room arbitrage margin, convertible 3BHK+ supply, and strongest co-living demand — built for Flent's investment decision-making.*

---

**Team:** Harshith Bejjanki `SM24UBBA047` · Suneeth Boorgula `SM24UBBA016` · Sudhiksha `SM24UBBA033` · Peddi Sudeeksha `SM24UBBA027` · Vedanth Nagaarur `SM24UBBA019`

---

## The Research Question

> **Which areas in Bengaluru offer the most favourable combination of factors for Flent — maximum per-room arbitrage margin, highest availability of convertible 3BHK+ properties, and strongest demand for shared living in premium furnished rooms?**

This pipeline answers that question rigorously — with real Magicbricks rental data, BBMP ward geometry, BMTC bus routes, and SEZ employment zones — producing a ranked, tiered investment target list for Flent's co-living expansion.

---

## The Business Logic

Flent's model is a **rental arbitrage operation**:

1. **Lease** a large 3BHK+ apartment at the ward's market rent
2. **Convert** it into premium furnished co-living rooms  
3. **Earn** the spread between per-room revenue and the master lease cost

Three pillars determine ward viability:

| Pillar | Signal | Threshold |
|--------|--------|-----------|
| **Arbitrage Margin** | `(avg_rent_1bhk × rooms × discount) − avg_rent_3bhk` | > ₹5,000/month |
| **Supply Depth** | Count of 3BHK+ listings ≥ 1,100 sqft | > 3 per ward |
| **Demand Intensity** | Price pressure + small-flat concentration + PSF spread | Composite 0–1 index |

---

## Quick Start

```bash
# 1. Activate virtual environment
source venv/bin/activate         # macOS / Linux
# venv\Scripts\activate          # Windows

# 2. Run the full analysis pipeline
python main.py

# 3. Launch the Leadership Dashboard (recommended)
venv/bin/python3.14 dashboard/app.py
# → Opens http://localhost:5050 in your browser automatically
```

---

## Project Structure

```
BBA_Python_final/               ← Flent Lens project root
│
├── main.py                     ← Pipeline orchestrator (run this directly)
├── config.py                   ← ALL paths, weights, and thresholds (source of truth)
├── requirements.txt            ← Python dependencies
├── README.md                   ← This document
├── ARCHITECTURE.md             ← Technical architecture reference
│
├── dashboard/                  ← Leadership Dashboard (NEW)
│   ├── app.py                  ← Flask server — session config + pipeline API
│   ├── index.html              ← Full-stack dashboard UI (single file)
│   └── run_with_overrides.py   ← Subprocess shim — runs pipeline with session config
│
├── docs/                       ← Product documentation (NEW)
│   └── CONSUMER_FINDER_SPEC.md ← Smart Apartment Finder feature spec (future build)
│
├── data/
│   ├── raw/
│   │   ├── magicbricks_final_listings.csv   ← Scraped rental data
│   │   ├── gba-369-wards-december-2025.kml  ← BBMP ward boundaries (369 wards)
│   │   ├── bmtc_bus_routes.kml              ← Bus route geometries
│   │   └── SEZ List/
│   │       └── SEZ list - Sheet1.csv        ← SEZ developer master list
│   └── processed/                           ← Auto-generated pipeline intermediates
│       ├── listings.csv                     ← Cleaned & validated listings
│       ├── sez_latlong.csv                  ← Geocoded SEZ coordinates
│       ├── sez_enriched_wards.kml           ← SEZ 25-acre circle geometries
│       ├── wards_processed.csv              ← Ward metadata with areas
│       └── transit_processed.csv            ← Transit scores per ward
│
├── src/
│   ├── pipeline/               ← Pre-processing stages (run once; skip if cached)
│   │   ├── cleaner.py          ← Magicbricks cleaning, BHK extraction, dedup
│   │   ├── geocoder.py         ← SEZ geocoding via Nominatim API
│   │   └── mapper.py           ← SEZ 25-acre circle KML generation
│   │
│   ├── modules/                ← Core analytical engine
│   │   ├── loader.py           ← Data I/O, schema validation, KML parsing
│   │   ├── spatial.py          ← Point-in-polygon joins, route intersection
│   │   ├── aggregator.py       ← Outlier removal, ward-level statistics
│   │   ├── economics.py        ← Arbitrage margin, DII, SFS, margin density
│   │   ├── transit.py          ← Transit connectivity index (BMTC)
│   │   ├── sez.py              ← SEZ gravity model (employment proximity)
│   │   ├── scoring.py          ← Composite opportunity score + tier assignment
│   │   └── validator.py        ← Moran's I spatial autocorrelation + OLS regression
│   │
│   └── utils/
│       ├── logger.py           ← Rich terminal UI (banners, stages, metrics)
│       └── exporter.py         ← KML atlas, multi-sheet XLSX, GeoJSON export
│
├── output/                     ← Generated analytical deliverables
│   ├── flent_investment_atlas.kml     ← Consolidated KML (wards + listings layers)
│   ├── flent_lens_report.xlsx         ← 4-sheet executive report with formatting
│   ├── ward_analysis.geojson          ← GeoJSON for dashboard map + QGIS
│   ├── moran_scatterplot_*.png        ← Spatial autocorrelation diagnostic
│   └── ols_arbitrage_validation.png   ← OLS regression validation plot
│
└── Claude-skills-main/         ← Claude AI skill definitions (reference only)
```

---

## The Dashboard

The **Leadership Dashboard** is the primary interface for Flent's team to explore, tweak, and understand the analysis without touching code.

```bash
venv/bin/python3.14 dashboard/app.py
# Opens http://localhost:5050
```

### Key features

| Feature | Description |
|---------|-------------|
| **Session Config** | All slider/toggle changes are held **in memory only** — `config.py` is never written to |
| **Auto-Rerun** | Any parameter change triggers the pipeline automatically after a 3-second debounce |
| **Reset to Defaults** | One button restores all parameters to original `config.py` values instantly |
| **Narrative Cards** | Every parameter is shown as a story card with plain-English business explanation |
| **Ward Map** | Leaflet choropleth showing all 369 BBMP wards color-coded by tier (Tier 1/2/3/Excluded) |
| **Live Leaderboard** | Top 20 wards ranked by Opportunity Score, with tier badges |
| **Pipeline Log** | Real-time streaming of pipeline terminal output via Server-Sent Events (SSE) |

### Config categories in the dashboard

- 🔵 **Data Quality** — Outlier thresholds, min listings per ward, rent caps, proximity radius
- 🟠 **Economic Model** — Demand discount factor, viable margin %, sqft thresholds, yield unlocks
- 🟢 **Scoring Weights** — DII weights, SFS weights, ECON composite weights, overlay boosts
- 🟣 **Spatial & Geographic** — Tier percentile cutoffs, SEZ gravity decay, spillover multipliers

> **Important:** The dashboard never modifies `config.py`. Changes are session-only and are discarded when the server stops. The pipeline subprocess receives overrides via an in-memory patch at runtime.

---

## Pipeline Stages

```bash
python main.py
```

The pipeline runs **9 stages** with a narrative terminal UI:

| Stage | Name | Description |
|-------|------|-------------|
| 0 | Data Pre-Processing | Clean Magicbricks CSV, geocode SEZs, generate KML geometries |
| 1 | Data Ingestion | Load 4 datasets: listings, wards (KML), bus routes (KML), SEZ points |
| 2 | Spatial Operations | Point-in-polygon ward assignment, proximity fallback, route clipping |
| 3 | Feature Engineering | Outlier removal (σ-based), ward-level median rents, SFC, PSF spread |
| 4 | Economic Modeling | Arbitrage margin (3BHK/4BHK), DII, SFS, effective margin density |
| 5 | Contextual Overlays | Transit score (BMTC density + length), SEZ gravity score |
| 6 | Opportunity Indexing | Composite score, spatial spillover / island penalty, tier assignment |
| 7 | Econometric Validation | Moran's I spatial autocorrelation, Hedonic OLS arbitrage regression |
| 8 | Export & Delivery | Consolidated KML atlas, 4-sheet XLSX report, GeoJSON |

Stages 0–0 (pre-processing) are **skipped automatically** if cached files already exist.

---

## Output Files

| File | Description |
|------|-------------|
| `flent_investment_atlas.kml` | Open in Google Earth — ward polygons + listing pins in one file |
| `flent_lens_report.xlsx` | 4 sheets: Executive Summary, Full Ward Data, Score Breakdown, OLS Model |
| `ward_analysis.geojson` | Full ward dataset for dashboard map + QGIS / web mapping |
| `moran_scatterplot_*.png` | Spatial autocorrelation diagnostic plot |
| `ols_arbitrage_validation.png` | OLS regression validation (feature importance + residuals) |

---

## Methodology

### 1. Arbitrage Margin

The core revenue model finds the spread between what Flent pays to lease a 3BHK and what it earns splitting it into rooms.

```
per_room_revenue  = city_median_rent_1bhk × DEMAND_DISCOUNT_FACTOR (0.80)
arb_margin_3bhk   = (per_room_revenue × 3) − q25_rent_3bhk
arb_margin_4bhk   = (per_room_revenue × 4) − q25_rent_4bhk
arb_margin_best   = max(arb_margin_3bhk, arb_margin_4bhk)
```

**Acquisition cost** uses the **25th percentile** (distressed/bulk inventory Flent targets).  
**Revenue** uses the **50th percentile** (median market rate Flent charges per room).  
The **0.80 demand discount factor** reflects tenants accepting a 20% discount vs solo 1BHK renting, in exchange for premium furnishing and zero hassle.

### 2. Dynamic Yield Model

Flat size determines how many revenue rooms Flent can extract:

| Size Range | BHK | Revenue Rooms |
|---|---|---|
| < 1,400 sqft | 3BHK | 3 rooms |
| 1,400–1,600 sqft | 3BHK | 3.5 rooms |
| ≥ 1,600 sqft | 3BHK | 4 rooms |
| ≥ 2,000 sqft | 4BHK | 5 rooms |

### 3. Demand Intensity Index (DII)

```
DII = w₁ × norm(price_pressure)  +  w₂ × norm(sfc)  +  w₃ × norm(psf_spread)

price_pressure = median_rent_1bhk / city_median_1bhk
sfc            = (cnt_1bhk + cnt_2bhk) / total_listings
psf_spread     = (max_psf − min_psf) / median_psf
```

Weights configurable via dashboard: default `0.40 / 0.30 / 0.30`.

### 4. Supply Feasibility Score (SFS)

```
SFS = w₁ × norm(supply_volume)  +  w₂ × norm(size_adequacy)  +  w₃ × norm(roi_score)

supply_volume = log1p(cnt_3bhk + cnt_4bhk) / log1p(city_max)
size_adequacy = pct_3bhk_listings ≥ MIN_SQFT_3BHK
roi_score     = arb_margin_best / max(arb_margin_best_citywide)
```

Weights configurable via dashboard: default `0.35 / 0.30 / 0.35`.

### 5. Composite Opportunity Score

```
ECON_SCORE  = (arb_margin_pct × 0.45) + (DII × 0.30) + (SFS × 0.25)
OPP_SCORE   = ECON_SCORE + (transit_score × 0.10) + (sez_score × 0.20)
```

All weights are configurable in real-time via the dashboard without touching code.

### 6. Spatial Spillover (Neighborhood Contagion)

A Tier 1 ward in a cluster of strong neighboring wards is more investable than an isolated one:

- **Tier 1 neighbor:** +10% `OPP_SCORE` boost
- **Tier 2 neighbor:** +5% boost
- **Tier 3 neighbor:** +2.5% boost
- **Island penalty:** −15% for Tier 1 wards with zero Tier 1/2 neighbors (non-scalable outlier)

### 7. Tier Assignment

Tiers are assigned on **percentile bands of eligible wards only** (wards where `margin_viable = True`):

| Tier | Percentile | Meaning |
|------|------------|---------|
| Tier 1 | ≥ 75th | Priority sourcing targets |
| Tier 2 | ≥ 50th | Secondary pipeline |
| Tier 3 | ≥ 25th | Watch list |
| Excluded | < 25th or margin not viable | Not recommended |

---

## Econometric Validation

### Moran's I — Spatial Autocorrelation
Tests whether rental prices cluster geographically. Positive Moran's I (> 0.3, p < 0.05) confirms the spatial spillover rules are operating within a real, spatially dependent market.

### Arbitrage Structural OLS
```
Q25_Acquisition_Rent_3BHK ~ Median_Retail_Rent_1BHK
```
HC3 robust standard errors. The slope coefficient β proves empirically that the 0.80 demand discount factor is structurally profitable — the mathematical breakeven discount is extracted directly from market data.

---

## Key Configuration Parameters

All parameters live in `config.py` and are exposed as interactive controls in the dashboard. **The dashboard never modifies this file.**

| Parameter | Default | Dashboard Control |
|-----------|---------|-------------------|
| `DEMAND_DISCOUNT_FACTOR` | `0.80` | Slider |
| `MARGIN_VIABLE_PCT` | `0.05` | Slider |
| `OUTLIER_STD_THRESHOLD` | `3.0` | Slider |
| `MIN_LISTINGS_PER_BHK` | `3` | Stepper |
| `MAX_VALID_1BHK_RENT` | `₹50,000` | Slider |
| `MIN_SQFT_3BHK` | `1,100` | Slider |
| `LARGE_3BHK_SQFT` | `1,500` | Slider |
| `ECON_WEIGHT_ARBITRAGE` | `0.45` | Weight slider |
| `ECON_WEIGHT_DII` | `0.30` | Weight slider |
| `ECON_WEIGHT_SFS` | `0.25` | Weight slider |
| `OVERLAY_WEIGHT_TRANSIT` | `0.10` | Weight slider |
| `OVERLAY_WEIGHT_SEZ` | `0.20` | Weight slider |
| `TIER1_PERCENTILE` | `75` | Stepper |
| `SEZ_DISTANCE_DECAY_ALPHA` | `1.5` | Slider |
| `SPILLOVER_BOOST_TIER1` | `1.10` | Slider |
| `ISOLATION_PENALTY` | `0.85` | Slider |

---

## Tech Stack

### Analysis Pipeline
| Library | Role |
|---------|------|
| `pandas` | DataFrame operations |
| `geopandas` | Spatial joins & CRS projections |
| `fiona` | KML file I/O |
| `shapely` | Geometry operations |
| `scikit-learn` | Min-max normalization |
| `statsmodels` | OLS regression + HC3 errors |
| `libpysal` | Spatial weights (Queen contiguity) |
| `esda` | Moran's I statistic |
| `matplotlib` / `seaborn` | Validation plots |
| `rich` | Narrative terminal UI |
| `geopy` | SEZ geocoding via Nominatim |
| `openpyxl` | XLSX export with conditional formatting |

### Dashboard
| Component | Role |
|-----------|------|
| `flask` | Lightweight local web server |
| `Leaflet.js` | Interactive ward choropleth map |
| `CartoDB Positron` | Basemap tiles |
| Google Fonts (`Playfair Display`, `DM Sans`, `JetBrains Mono`) | Typography |
| Browser SSE (`EventSource`) | Real-time pipeline log streaming |
| Vanilla JS | All UI logic (no framework) |

---

## Future Roadmap

The `docs/CONSUMER_FINDER_SPEC.md` file contains a full product specification for a **Smart Apartment Finder** — a conversational, dialogue-driven feature Flent can embed on their website to help users find the right neighborhood through a 9-step preference interview. This is the next planned build after the Leadership Dashboard is complete.

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `ModuleNotFoundError: flask` | Flask not in active venv | Use `venv/bin/python3.14 dashboard/app.py` explicitly |
| `CRSError` on spatial join | CRS mismatch between GDFs | Both GDFs are auto-projected to EPSG:4326 before joins |
| All wards `data_sparse` | Lat/lon swapped in CSV | Check `latitude` and `longitude` column names in raw CSV |
| `KML layer not found` | Missing KML layer | Run `fiona.listlayers('file.kml')` to inspect layers |
| Moran's I `island error` | Isolated ward polygon | `Queen(silence_warnings=True)` is set by default |
| GeoJSON 404 in dashboard | Pipeline not run yet | Click "Run Pipeline" in the dashboard first |
| Dashboard shows `—` metrics | GeoJSON not loaded | Run pipeline once to generate `output/ward_analysis.geojson` |

---

*Flent Lens — BBA Python Project, April 2026*
>>>>>>> 167d849 (Initial commit: Modularized Flent Lens pipeline)
