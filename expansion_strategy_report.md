# 🚀 Flent Lens — Multi-City Expansion Strategy Report

> **From "Where in Bengaluru?" to "Which City is Next, and Where Exactly Within It?"**

*A full-fledged blueprint for pivoting Flent Lens from a single-city investment tool into India's most rigorous co-living expansion intelligence platform.*

---

## 1. The Strategic Pivot

Your Bengaluru analysis answered a micro question:
> *"Which wards offer the highest co-living arbitrage margin within Bengaluru?"*

The next phase answers two harder, more consequential questions:

| Layer | Question |
|---|---|
| **Macro (Cross-City)** | *"Which Indian city should Flent target next for market entry?"* |
| **Micro (Intra-City)** | *"Once we've chosen the city, exactly where — and at what rental economics — should Flent operate?"* |

This requires the pipeline to work at **two levels simultaneously**. The report below blueprints every component needed: data models, new analytical modules, output files, and the dashboard architecture.

---

## 2. Target City Universe

### Tier A — Primary Candidates *(data-rich, co-living proven)*

| City | Co-Living Rationale | Geo Unit | CRS |
|---|---|---|---|
| **Pune** | Dense IT corridor (Hinjewadi, Kharadi); high young professional density; rent arbitrage proven | Ward / Locality | EPSG:32643 |
| **Chennai** | South India's second IT hub; emerging PG-to-co-living upgrade market | Ward / Zone | EPSG:32644 |
| **Mumbai** | Highest rent-to-income stress in India = strongest demand; unit economics hardest but upside huge | Ward | EPSG:32643 |
| **Gurgaon / NCR** | Corporate belt, high expat concentration, premium co-living already exists → positioning battle | Sector / Zone | EPSG:32643 |

### Tier B — Secondary Candidates *(emerging, lower data density)*

| City | Rationale |
|---|---|
| **Kochi** | IT SEZ growth, smaller base = first-mover advantage |
| **Coimbatore** | Textile + IT, rent-to-income stress low but supply plentiful |
| **Indore** | Central India's fastest-growing IT hub |
| **Ahmedabad** | Industrial + IT, GIFT City proximity |

---

## 3. Plan of Action — Phases

```
Phase 1: Multi-City Data Acquisition        [2 – 3 weeks]
Phase 2: City Attractiveness Index (CAI)    [1 week]
Phase 3: Intra-City Granular Analysis       [2 – 3 weeks per city]
Phase 4: Cross-City Dashboard               [1 – 2 weeks]
Phase 5: Granular Intra-City Dashboard      [1 week]
```

### Phase 1 — Multi-City Data Acquisition

For each candidate city, collect:

| Data Layer | Source | Format | Priority |
|---|---|---|---|
| Rental listings (3BHK/1BHK) | Magicbricks scrape | CSV (same schema) | 🔴 Critical |
| Administrative boundaries | DIVA-GIS / Bhuvan / Data.gov.in | KML / GeoJSON / SHP | 🔴 Critical |
| Metro/Bus transit routes | OpenStreetMap / GTFS feeds | GeoJSON / KML | 🟡 High |
| SEZ / Tech parks | SEEPZ / Invest India + geocoding | CSV → geocoded | 🟡 High |
| Population density by zone | Census 2011 / Bhuvan | CSV / GeoJSON | 🟡 High |
| Co-working space density | Google Places API / OSM | GeoJSON | 🟢 Medium |
| City-level macro indicators | CBRE / JLL / NHB India reports | Manual CSV input | 🟢 Medium |

**Schema Consistency Rule:** All city listing CSVs must conform to the same column schema already used by Bengaluru. The `cleaner.py` module handles city-specific column mapping via a `column_map` key in `city_config.py`.

---

## 4. New Data Models Required

### 4.1 — Enhanced `city_config.py` profile schema

Each city profile needs these **new keys** added:

```python
"city_tier":              "Tier A",          # Tier A / B / C for context
"macro_indicators": {
    "population_mn":      13.6,               # city population in millions
    "it_workforce_mn":    1.2,                # estimated IT/white-collar workforce
    "avg_city_rent_1bhk": 18500,             # city-wide baseline (manual input)
    "yoy_rent_growth_pct": 9.2,              # YoY rent growth % (from reports)
    "coliving_market_exists": True,           # bool: known co-living operators present?
    "flent_presence":     False,              # bool: Flent already operating here?
},
"has_metro":              True,               # distinguish metro from bus
"metro_kml":              "data/raw/city/metro_lines.kml",
"has_population_density": True,
"population_density_csv": "data/raw/city/population_density.csv",
"has_coworking":          False,
"coworking_geojson":      None,
"nearest_max_distance_m": 2500,
"listing_column_map": {                       # maps raw CSV cols → standard schema
    "locality":   "Locality",
    "rent":       "Price",
    "area_sqft":  "Area",
    "bhk_type":   "BHK"
},
```

### 4.2 — New `city_summary.json` (per city output)

A machine-readable JSON generated at the end of each city's pipeline run, used by the cross-city comparator:

```json
{
  "city": "pune",
  "run_timestamp": "2026-04-19T10:30:00",
  "geo_unit": "ward",
  "total_zones_analysed": 312,
  "viable_zones": 87,
  "tier1_zones": 22,
  "tier2_zones": 31,
  "tier3_zones": 34,
  "city_median_rent_1bhk": 17800,
  "city_median_rent_3bhk": 32500,
  "city_median_arb_margin": 12400,
  "city_max_arb_margin": 38900,
  "avg_dii_score": 0.61,
  "avg_sfs_score": 0.54,
  "moran_i": 0.38,
  "moran_p": 0.001,
  "ols_slope": 0.142,
  "ols_r2": 0.61,
  "cai_score": 74.2,              ← City Attractiveness Index (new, see §5)
  "cai_rank": 2
}
```

### 4.3 — New `cross_city_summary.csv`

A flat table aggregating one row per city for the cross-city comparison dashboard section:

| Column | Type | Source |
|---|---|---|
| `city` | str | config |
| `cai_score` | float | CAI module |
| `cai_rank` | int | CAI module |
| `viable_zone_pct` | float | pipeline |
| `median_arb_margin` | int | pipeline |
| `max_arb_margin` | int | pipeline |
| `tier1_zone_count` | int | pipeline |
| `avg_dii` | float | pipeline |
| `moran_i` | float | validator |
| `ols_slope` | float | validator |
| `it_workforce_mn` | float | config |
| `yoy_rent_growth` | float | config |
| `flent_presence` | bool | config |
| `recommendation` | str | CAI module |

---

## 5. New Analytical Modules

### 5.1 — `src/modules/cai.py` — City Attractiveness Index

**Purpose:** Score each city on a 0–100 index to produce a ranked shortlist. This is the macro-level answer to "which city is next?"

**The CAI Formula:**

```
CAI = (W_demand   × Demand_Score)
    + (W_margin   × Margin_Score)
    + (W_supply   × Supply_Score)
    + (W_spatial  × Spatial_Score)
    + (W_macro    × Macro_Score)
    + (W_risk     × Risk_Score)

Weights: 0.25 / 0.25 / 0.15 / 0.10 / 0.15 / 0.10
```

**Sub-scores (all normalized 0–1):**

| Sub-Score | Inputs | Logic |
|---|---|---|
| `Demand_Score` | avg_dii city-wide, YoY rent growth, IT workforce size | Higher demand = more tenants = more room revenue |
| `Margin_Score` | median_arb_margin, ols_slope (breakeven efficiency), viable_zone_pct | Higher and stabler margins = safer returns |
| `Supply_Score` | tier1_zone_count, total_viable_zones, avg_sfs | How many high-quality zones can Flent actually operate in? |
| `Spatial_Score` | Moran's I value (how clustered are the good zones?) | High Moran's I = zones cluster = efficient cluster ops |
| `Macro_Score` | population_mn, coliving_market_exists, avg_city_rent_1bhk | City-level tailwinds |
| `Risk_Score` *(inverted)* | flent_presence (competition), market_fragmentation, data_density | Lower = less risk |

**Output:** a ranked DataFrame + recommendation tag per city:
- `🟢 Priority Entry` — CAI ≥ 70
- `🟡 Evaluate Further` — CAI 50–70
- `🔴 Defer` — CAI < 50

### 5.2 — `src/modules/metro.py` — Metro Overlay (new transit layer)

In cities like Mumbai, Pune, Chennai: metro proximity is a **positive signal** (unlike bus in Bengaluru). This module builds on `transit.py` but adds:
- Directional weighting: metro = positive (+0.15), bus = negative (−0.10)
- Walking-distance buffer: ≤ 800m from metro station = premium demand boost

### 5.3 — `src/modules/coworking.py` — Co-working Density Overlay

Co-working space density within a zone is a strong proxy for mobile-professional demand (Flent's core tenant):

```
coworking_score = log1p(coworking_count_within_1km) / log1p(city_max_coworking)
```

Integrated into `OPP_SCORE` with `OVERLAY_WEIGHT_COWORKING = 0.10` (configurable).

### 5.4 — `src/modules/comparator.py` — Cross-City Comparison Engine

Reads `city_summary.json` for all completed cities and builds:
- Ranked CAI table
- City-vs-city metric comparison
- "Best city for Flent" recommendation with plain-English rationale

---

## 6. Updated Pipeline Architecture

```
Stage 0   Pre-Processing        (unchanged — cleaner.py, geocoder.py, mapper.py)
Stage 1   Data Ingestion        (unchanged — loader.py)
Stage 2   Spatial Operations    (unchanged — spatial.py)
Stage 3   Feature Engineering   (unchanged — aggregator.py)
Stage 4   Economic Modeling     (unchanged — economics.py)
Stage 5   Contextual Overlays   (UPGRADED — transit.py + NEW metro.py + NEW coworking.py)
Stage 6   Opportunity Scoring   (unchanged — scoring.py)
Stage 7   Econometric Validation(unchanged — validator.py)
Stage 8   Export & Delivery     (UPGRADED — exporter.py writes city_summary.json)
Stage 9   [NEW] CAI Scoring     (NEW — cai.py, only runs in multi-city mode)
Stage 10  [NEW] Cross-City Comp (NEW — comparator.py, runs after all cities complete)
```

`main.py` gets a new `--mode` flag:
```bash
python main.py --city bangalore     # single-city mode (existing)
python main.py --all-cities         # runs all configured cities sequentially
python main.py --cai-only           # re-runs CAI + comparator from cached summaries
```

---

## 7. Output Files — Complete Specification

### Per-City Outputs (existing, unchanged)

| File | Description |
|---|---|
| `flent_investment_atlas.kml` | KML for Google Earth |
| `flent_lens_report.xlsx` | 4-sheet Excel report |
| `ward_analysis.geojson` | GeoJSON for dashboard map |
| `3bhk_supply_price_quartiles.xlsx` | 3BHK quartile breakdown |
| `moran_scatterplot_*.png` | Spatial autocorrelation plot |
| `ols_arbitrage_validation.png` | OLS regression plot |

### Per-City Outputs (NEW)

| File | Description |
|---|---|
| `city_summary.json` | Machine-readable city KPIs → feeds cross-city dashboard |
| `top_zones_factsheet.pdf` | Auto-generated 1-pager (Top 5 zones + economics) |
| `zone_drill_down.geojson` | Zone-level GeoJSON with full feature vector for drill-down |
| `listing_heatmap.geojson` | Raw listing point layer for within-zone scatter view |

### Cross-City Outputs (NEW)

| File | Path | Description |
|---|---|---|
| `cross_city_summary.csv` | `output/` | One row per city — all CAI inputs and outputs |
| `city_rankings.xlsx` | `output/` | Formatted Excel: CAI scorecard + sub-scores + recommendation |
| `cai_radar_chart.png` | `output/` | City vs. city radar chart (6 CAI dimensions) |
| `expansion_heatmap.png` | `output/` | India map with cities colour-coded by CAI score |
| `expansion_recommendation.txt` | `output/` | Plain-English narrative: "City X is Flent's strongest next market because…" |

---

## 8. Dashboard Architecture — Section Blueprint

The Streamlit dashboard (`app.py`) needs a **two-mode structure**:

```
┌──────────────────────────────────────────────────────────────┐
│  Flent Lens                               [Cross-City Mode]  │
│                                           [Single-City Mode] │
└──────────────────────────────────────────────────────────────┘
```

---

### MODE A — Cross-City Expansion Dashboard

**Sidebar Controls:**
- Mode selector: `Cross-City Overview` / `City Deep Dive`
- City multi-select (for comparison)
- CAI weight sliders (let user adjust weights — "what matters most to you?")

---

#### Section A1 — Expansion Command Centre *(Hero Section)*
- **Purpose:** First-glance strategic answer
- **Components:**
  - **CAI Leaderboard Card** — Top 3 cities ranked, with medal badges, CAI score, and one-line recommendation
  - **India Choropleth Map** — All candidate cities plotted on an India base map, colour-coded by CAI score (green → red). Hover tooltip shows city name, CAI score, top metric.
  - **"Flent's Next City" Verdict Box** — Bold callout: `🏆 Recommended: Pune · CAI 74.2 · 87 viable zones · ₹12,400 median margin`

#### Section A2 — City Attractiveness Index Breakdown
- **Purpose:** Explain *why* cities are ranked the way they are
- **Components:**
  - **CAI Radar/Spider Chart** — Plotly radar with one trace per city, 6 axes (Demand, Margin, Supply, Spatial, Macro, Risk)
  - **Sub-score Table** — Sortable table: city × 6 CAI dimensions + total score
  - **Weight Sensitivity Panel** — Slider for each CAI weight; chart updates live → "which city wins if you weight margin more?"

#### Section A3 — Cross-City Economic Comparator
- **Purpose:** Apples-to-apples financial comparison
- **Components:**
  - **KPI Grid** — Side-by-side stat cards: Median Arb Margin, Max Arb Margin, Viable Zone %, Tier 1 Zone Count, Avg DII — for each city
  - **Margin Distribution Box Plot** — Plotly box plot: margin distributions across all cities on one chart (reveals not just median but spread and outliers)
  - **Rent Gradient Bar Chart** — City-level median 1BHK vs Q25 3BHK side by side — shows where the "spread" is widest

#### Section A4 — Spatial Validation Across Cities
- **Purpose:** Prove the spatial structure is real in each city
- **Components:**
  - **Moran's I Comparison Bar** — Bar chart: Moran's I value per city with significance stars
  - **OLS Slope Comparison** — Slope coefficient per city = "how efficiently does 1BHK rent predict 3BHK acquisition cost?" A higher slope = tighter arbitrage engine
  - **Spatial Clustering Map** — Small multiples: one mini-choropleth per city showing tier distribution

#### Section A5 — Data Coverage & Confidence
- **Purpose:** Transparency about which cities have incomplete data layers
- **Components:**
  - **Data Availability Matrix** — Table: City × Data Layer (Listings, Geo, Transit, SEZ, Metro, Coworking) with ✅/🟡/❌
  - **Confidence Score per City** — Composite of how many optional layers are present (affects how much to trust the CAI score)
  - **"Improve This City" CTA** — Actionable list of missing data layers per city that would improve the CAI precision

---

### MODE B — Single-City Granular Deep Dive

*This is the evolved version of your current Bengaluru dashboard — now generalized and deepened.*

**Sidebar Controls:**
- City selector (dropdown)
- Zone filter (tier, margin range, zone name search)
- Overlay toggles (transit, SEZ, metro, coworking)

---

#### Section B1 — City Overview Header *(Persistent Sticky)*
- City name + CAI rank badge
- 5 KPI chips: Total Zones | Viable Zones | Tier 1 Count | Median Margin | Moran's I
- Model Assumptions expander (DDF, weights — already exists, keep)

#### Section B2 — The Investment Atlas *(Upgraded Choropleth)*
- **Base Layer:** Zone polygons coloured by `OPP_SCORE` (existing)
- **NEW Overlay Toggles (sidebar checkboxes):**
  - 📍 Show listing density heatmap (raw listing points as heat layer)
  - 🚇 Metro station proximity rings (800m buffer)
  - 🏢 SEZ gravity contours
  - 💼 Co-working density layer
- **Click-to-Drill-Down:** Clicking a zone opens the Zone Drill-Down Panel (Section B4)
- **Zone Search:** Type a ward/locality name to jump to it on the map

#### Section B3 — Top Investment Zones *(Upgraded Ward Cards)*
- Top 5 instead of Top 3 (with expand/collapse for 4th and 5th)
- Each card:
  - Rank badge + tier badge
  - Arbitrage margin (3BHK and 4BHK best case)
  - DII bar, SFS bar, Margin health bar
  - **NEW: Opportunity Window tag** — e.g., `📈 High Demand · Low Supply Depth` or `🏆 Best Overall`
  - **NEW: Comparable City Context** — "This zone's margin (₹18k) ranks in the **top 12%** across all analysed cities"

#### Section B4 — Zone Drill-Down Panel *(NEW — Core Granular Section)*
- Activated by clicking a zone on the map OR selecting from a dropdown
- **Four sub-tabs:**

  **Tab 1: Zone Economics**
  - Full arbitrage math (3BHK and 4BHK scenarios) shown as a waterfall chart
  - Rent distribution histogram (1BHK and 3BHK listings in this zone)
  - Quartile table: P25 / Median / P75 for 1BHK and 3BHK rents

  **Tab 2: Listing Explorer**
  - Scatter map of individual listings within the zone (from `listing_heatmap.geojson`)
  - Filterable table: listing address, rent, sqft, PSF, BHK type
  - "Best Property to Lease" recommendation: the listing closest to Q1 rent with ≥ 1,100 sqft

  **Tab 3: Spatial Context**
  - Mini-map showing this zone + its neighbours with tier colors
  - Spillover indicator: "This zone is boosted/penalized by X neighbours"
  - Nearest SEZ / Metro station distance and name

  **Tab 4: Investment Verdict**
  - Plain-English paragraph generated from the zone's metrics
  - e.g., *"Whitefield is a Tier 1 Priority Zone. Its ₹22,400 monthly arbitrage margin sits in the top 8% citywide. Demand is strong (DII 0.78) driven by IT employment proximity (Bagmane Tech Park: 1.4km). With 14 convertible 3BHK listings meeting the size threshold, supply is adequate. Surrounding Tier 1 neighbors give a +10% spatial spillover boost. This zone is Flent's strongest acquisition target."*
  - GO / WATCH / AVOID badge

#### Section B5 — Economic Analysis *(Upgraded)*
- **Margin vs Rent Scatter Plot** — (existing, keep)
  - Add quadrant labels: "Sweet Spot", "High Margin Low Volume", "Volume Play", "Avoid"
  - Add city-median crosshair lines
- **NEW: Margin Waterfall by Tier** — stacked bar showing how margin splits across Tier 1/2/3 zones
- **Zone Economics Table** — (existing, upgraded)
  - Add columns: `arb_margin_4bhk`, `ddf_effective`, `margin_per_room`, `tier`
  - Exportable as CSV directly from dashboard

#### Section B6 — Econometric Validation *(Existing, Kept)*
- Moran's I scatterplot (existing)
- OLS regression chart (existing)
- Plain-English interpretation panels (existing from recent upgrades)
- **NEW: City Comparison Callout** — "Bengaluru's Moran's I of 0.42 is higher than Pune (0.31), meaning Bengaluru's investment zones cluster more tightly → more efficient route planning for Flent ops."

#### Section B7 — Data Export *(Upgraded)*
- Download buttons for all output files
- **NEW: Zone Shortlist Builder** — user can checkbox-select zones from the table → download a custom shortlist XLSX with only those zones
- **NEW: Pitch Deck Snapshot** — download a pre-formatted PNG of the Top 5 cards + map for presentation use

---

## 9. Key Engineering Decisions

### 9.1 — How to run multi-city without breaking single-city flow

- `ACTIVE_CITY` in `city_config.py` stays for single-city mode
- New `--all-cities` flag in `main.py` loops `CITY_PROFILES.keys()`
- `city_summary.json` is the handoff artifact — the CAI and comparator read from it, never from in-memory pipeline state
- This makes the cross-city analysis **independent of pipeline order** — run cities months apart, re-run CAI anytime

### 9.2 — Dashboard state management

```python
# In app.py — global mode control
mode = st.sidebar.radio("Dashboard Mode", ["🌏 Cross-City Overview", "🔍 City Deep Dive"])
if mode == "🌏 Cross-City Overview":
    render_cross_city_dashboard()
else:
    city = st.sidebar.selectbox("Select City", list(CITY_PROFILES.keys()))
    render_single_city_dashboard(city)
```

### 9.3 — Listing-level drill-down data

The `zone_drill_down.geojson` (new) will contain **individual listing records** tagged with their zone, not just zone aggregates. This is what powers the Listing Explorer tab. The exporter in `exporter.py` needs to write this alongside `ward_analysis.geojson`.

### 9.4 — CAI weight sensitivity (live sliders)

The CAI sub-scores are stored normalized (0–1) in `city_summary.json`. The dashboard re-computes the final CAI on the fly from these stored sub-scores + the user's slider weights. This gives the "what if" sensitivity analysis without re-running the pipeline.

---

## 10. Phased Delivery Priority

| Phase | Deliverable | Effort | Business Value |
|---|---|---|---|
| **P0** | Add Pune + Chennai to `city_config.py`, scrape data, run pipeline | Medium | Foundation |
| **P1** | `cai.py` module + `city_summary.json` output | Low-Medium | Core new value |
| **P2** | `cross_city_summary.csv` + `city_rankings.xlsx` outputs | Low | Executive-ready artifact |
| **P3** | Dashboard Section A1-A3 (Cross-City Comparator) | Medium | Highest visual impact |
| **P4** | Dashboard Section B4 (Zone Drill-Down) | Medium-High | Deepest analytical value |
| **P5** | `metro.py` + `coworking.py` overlays | Medium | Better signal quality |
| **P6** | Dashboard Section A4-A5 + B6-B7 upgrades | Low | Completeness |

---

## 11. What This Report Does NOT Cover (Intentionally Deferred)

| Item | Reason |
|---|---|
| Time-series rent trends | Requires ongoing scraping infrastructure (out of scope for BBA project) |
| Competitor co-living operator mapping | Requires a separate data collection effort |
| Capex / furnishing cost modelling | Business-specific data Flent would hold internally |
| Predictive modelling (which zone will become Tier 1?) | Requires historical data; a natural Phase 2 extension |
| Mobile app version of dashboard | Out of scope; Streamlit deployment is sufficient |

---

## 12. Quick Summary

```
┌─────────────────────────────────────────────────────────────────┐
│  FLENT LENS EXPANSION BLUEPRINT — ONE-PAGE SUMMARY              │
│                                                                  │
│  NEW CITIES:     Pune, Chennai, Mumbai, Gurgaon                 │
│  NEW MODULES:    cai.py · metro.py · coworking.py · comparator  │
│  NEW OUTPUTS:    city_summary.json · cross_city_summary.csv      │
│                  city_rankings.xlsx · cai_radar_chart.png        │
│                  expansion_recommendation.txt                     │
│                  zone_drill_down.geojson · listing_heatmap.geojson│
│                                                                  │
│  DASHBOARD:      2 Modes — Cross-City + Single-City Deep Dive   │
│  SECTIONS:       A1 Command Centre · A2 CAI Breakdown           │
│                  A3 Economic Comparator · A4 Spatial Validation  │
│                  B1 City Header · B2 Atlas (upgraded)            │
│                  B3 Top Zones · B4 Zone Drill-Down (NEW)         │
│                  B5 Economics · B6 Validation · B7 Export        │
│                                                                  │
│  KEY NEW CONCEPT: City Attractiveness Index (CAI)               │
│  → Demand (25%) + Margin (25%) + Supply (15%) + Spatial (10%)   │
│    + Macro (15%) + Risk (10%)                                    │
│  → Output: Ranked city shortlist + "Flent's Next City" verdict  │
└─────────────────────────────────────────────────────────────────┘
```

---

*Flent Lens — Multi-City Expansion Blueprint · Harshith Bejjanki · April 2026*
