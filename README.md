# Flent Lens 2.0 — Multi-City Co-Living Arbitrage Intelligence Platform

> **Research Question:** In a rapidly formalizing Indian rental market, which geographic micro-markets contain the highest concentration of under-priced large-format residential properties (3BHK+ apartments AND villas/independent houses) whose per-room co-living revenue, after applying an empirically validated Demand Discount Factor (DDF), consistently exceeds the whole-unit master lease cost — and can this structural pricing inefficiency be proven through spatial econometric evidence?

---

## Table of Contents

1. [What This Does](#what-this-does)
2. [Architecture](#architecture)
3. [The Economic Model](#the-economic-model)
4. [Analytical Framework](#analytical-framework)
5. [Spatial Methodology](#spatial-methodology)
6. [Econometric Validation](#econometric-validation)
7. [Model Assumptions](#model-assumptions)
8. [Data Pipeline](#data-pipeline)
9. [Output Deliverables](#output-deliverables)
10. [Usage](#usage)
11. [Directory Structure](#directory-structure)
12. [Configuration](#configuration)
13. [Dependencies](#dependencies)
14. [Team](#team)

---

## What This Does

Flent Lens is a **spatial analytical platform** that identifies geographic zones where co-living rental arbitrage is structurally profitable. It does this by:

1. **Ingesting** 71,000+ rental listings across 15 Indian cities (scraped from MagicBricks)
2. **Tessellating** the city into ~5 km² hexagonal cells using Uber's H3 grid system (Resolution 7)
3. **Computing** dual-track arbitrage margins for both apartments and villas/houses
4. **Validating** the arbitrage thesis through spatial econometric models (SAR/SEM)
5. **Ranking** every hexagon by a PCA-weighted composite opportunity score
6. **Delivering** KML maps, rich Excel reports, and machine-readable JSON summaries

The platform is **boundary-less** — it requires zero administrative KML files to analyze a new city. Feed it listings with lat/lon, and it generates the entire analytical output.

---

## Architecture

```
                           ┌─────────────────────┐
                           │   compiled_listings  │
                           │   .csv (71,282 rows) │
                           └──────────┬──────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 1: Data Ingestion         │
                    │   Filter by city + validate       │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 2: H3 Grid Generation     │
                    │   Res 7 hex assignment + MAUP     │
                    │   stability test (Res 6/7/8)      │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 3: OSM Context            │
                    │   Transit · Employment · POIs     │
                    │   Reverse geocoding               │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 4: Feature Engineering    │
                    │   K-Ring smoothing · Neff · CIs   │
                    │   Demand + Supply features        │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 5: Economic Modeling      │
                    │   Apartments ←→ Villas            │
                    │   Elastic DDF · Room yield        │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 6: PCA + Scoring          │
                    │   Weight calibration · Composite  │
                    │   score · H3 spillover · Tiers    │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 7: Econometric Validation │
                    │   Moran's I · OLS · SAR/SEM      │
                    └─────────────────┬─────────────────┘
                                      │
                    ┌─────────────────┼─────────────────┐
                    │   STAGE 8: Export                 │
                    │   KML · XLSX · GeoJSON · JSON     │
                    └───────────────────────────────────┘
```

---

## The Economic Model

### The Arbitrage Thesis

The Indian rental market has a structural pricing inefficiency:

> **Large apartments (3BHK+) and villas are priced on a per-unit basis, but co-living revenue is generated per-room.** When a 3BHK flat rents at ₹40,000/month and each of its 3 rooms can be independently let at ₹18,000/month (80% of standalone 1BHK rent), the co-living operator earns ₹54,000 — a ₹14,000/month (35%) margin.

### Dual-Track Model

Lens 2.0 evaluates **two sourcing strategies** per hexagon:

| Parameter | Apartment Track | Villa/House Track |
|---|---|---|
| Source Asset | 3BHK+ flats | Villas, Independent Houses |
| Acquisition Cost | Q1 (25th percentile) rent | Q1 (25th percentile) rent |
| Min Sqft | 1,100 sqft | 1,800 sqft |
| Room Yield | 3–4 rooms (dynamic by sqft) | 4–6 rooms (larger footprint) |
| DDF Baseline | 80% of 1BHK rent | 75% (harder co-living stabilization) |

The system selects the **better-performing track** per hex automatically.

### Demand Discount Factor (DDF)

The DDF models the reality that a co-living room cannot command full 1BHK rent:

```
Per-Room Revenue = Median_1BHK_Rent × DDF
```

The DDF is **elastic** — it stretches based on local market pressure:
- High-demand hex (price_pressure > 1.0): DDF shifts toward 90%
- Low-demand hex: DDF drops toward 70%
- Band: ±10% around baseline

### Room Yield Logic

| Apartment Sqft | Rooms | Villa Sqft | Rooms |
|---|---|---|---|
| < 1,400 | 3 | < 2,500 | 4 |
| 1,400 – 1,999 | 3.5 | 2,500 – 2,999 | 5 |
| ≥ 2,000 | 4 | ≥ 3,000 | 6 |

---

## Analytical Framework

### Composite Opportunity Score

Every hexagon receives a composite score from 0–100:

```
OPP_SCORE = ECON_SCORE + OVERLAY_ADJUSTMENTS + SPATIAL_AURA
```

Where:

**ECON_SCORE** = `w₁ × norm(arb_margin) + w₂ × DII + w₃ × SFS`

- **w₁, w₂, w₃** are PCA-calibrated (or expert defaults if PCA disabled)

**DII (Demand Intensity Index)** = `w_pp × price_pressure + w_sfc × small_flat_concentration + w_psf × psf_spread`

- **Price Pressure:** How expensive is this hex relative to city median?
- **SFC:** What fraction of listings are 1BHK/2BHK (indicating room-level demand)?
- **PSF Spread:** How large is the gap between 1BHK and 3BHK per-sqft pricing?

**SFS (Supply Feasibility Score)** = `w_vol × log_volume + w_size × size_adequacy + w_roi × capital_efficiency`

**Overlay Adjustments** (from OpenStreetMap):
- **Transit:** Metro proximity (+), bus stop density (−)
- **Employment:** Office cluster proximity
- **Lifestyle:** Cafes, supermarkets, gyms density

**Spatial Aura** (H3 K-Ring):
- +10% if adjacent to Tier 1 hexes
- +5% if adjacent to Tier 2
- −15% **Island Penalty** if a Tier 1 hex has zero Tier 1/2 neighbors

### PCA Weight Calibration

All composite index weights are derived from **Principal Component Analysis**:

1. Take normalized sub-components across all hexes
2. Run PCA (1 component) → extract squared loadings
3. Normalize to weights summing to 1.0
4. Floor at 10% (no feature zeroed out)

This replaces arbitrary expert weights with mathematically justified proportions. Both PCA and expert weights are logged in outputs for transparency. Set `USE_PCA_WEIGHTS = False` in `config.py` to revert.

### Tier Assignment

| Tier | Criteria |
|---|---|
| **Tier 1** | Score ≥ 75th percentile AND `Neff ≥ 8` AND `stability ≥ 0.80` |
| **Tier 2** | Score ≥ 50th percentile (or demoted from T1 due to data issues) |
| **Tier 3** | Score ≥ 25th percentile |
| **Excluded** | Below viability floor (`margin < ₹5,000` or `margin% < 5%`) |

---

## Spatial Methodology

### H3 Hexagonal Grid (Resolution 7)

Every listing is mapped to a hex: `hex_id = h3.latlng_to_cell(lat, lon, 7)`

**Why H3 instead of administrative boundaries?**
- Uniform geometry: 6 equal neighbors (vs irregular ward polygons)
- No boundary files needed: instant expansion to any city
- ~5.1 km² per hex: granular enough for micro-market differentiation

### K-Ring Weighted Smoothing

For hexes with sparse data, we borrow strength from neighbors:

```
w_i = count_i / (1 + β × dist_km)     β = 0.4
Neff = (Σw)² / Σ(w²)                  Effective Sample Size
```

**Confidence Levels:**
- `Neff ≥ 8` → Full confidence (eligible for Tier 1)
- `5 ≤ Neff < 8` → Low confidence (capped at Tier 2)
- `Neff < 5` → Data insufficient (excluded from scoring)

All price aggregations use **weighted medians** (not means) because rent distributions are right-skewed. Uncertainty is quantified via **500-iteration bootstrap** confidence intervals at the 90% level.

### MAUP Stability Testing

The Modifiable Areal Unit Problem means our KPIs change with hex size. We test:
- Resolution 6 (~36 km²), 7 (~5 km²), 8 (~0.7 km²)
- Per-hex stability: `1 - MAD(KPI) / median(KPI)`
-  Tier 1 requires stability ≥ 0.80

---

## Econometric Validation

### Why This Matters

Every claim in the output ("Hex X has 35% arbitrage margin") needs statistical backing. Without econometric validation, the entire analysis is an assertion, not evidence.

### Moran's I — Spatial Autocorrelation

Tests whether high-rent hexes cluster near other high-rent hexes:

```
I = (N / Σw_ij) × [Σ w_ij(x_i - x̄)(x_j - x̄)] / [Σ(x_i - x̄)²]
```

- **999 permutations** for robust p-values
- Positive I (p < 0.05) → rents are spatially clustered → spatial models are necessary
- The Moran scatterplot identifies **LH quadrant hexes** (low rent surrounded by high rent) — these are the prime arbitrage targets

### OLS Baseline

```
Q1_3BHK_Rent ~ α + β × Median_1BHK_Rent
```

**Key output:** β (the cost multiplier) and the **breakeven DDF**:

```
Breakeven_DDF = β / rooms
```

If Flent's operational DDF exceeds breakeven, the arbitrage is **structurally proven in the dataset**.

### SAR (Spatial Autoregressive Lag Model)

```
Q1_3BHK = ρ × W × Q1_3BHK + α + β × Median_1BHK + ε
```

- **ρ** = spatial lag coefficient (does your neighbor's 3BHK rent predict yours?)
- Uses K=6 nearest-neighbor weights (natural for hex geometry)
- If SAR β differs significantly from OLS β, it proves that ignoring spatial dependence biases results
- Model selection between SAR and SEM guided by Lagrange Multiplier tests

---

## Model Assumptions

| # | Assumption | Rationale | Impact if Violated |
|---|---|---|---|
| 1 | **Asking rents approximate market rents** | MagicBricks listings reflect actual transaction prices within ±10% | Margins may be inflated; DDF sensitivity table provides safety check |
| 2 | **1BHK rent is the revenue benchmark** | Co-living rooms compete with studio/1BHK alternatives | Overestimates revenue in markets where sharing is culturally preferred |
| 3 | **Q1 sourcing is achievable** | Operators have procurement leverage for below-median properties | Conservative — only bottom 25% of asking rents are considered |
| 4 | **DDF of 75–80% is sustainable** | Empirical range from Flent's existing operations | Validated against OLS breakeven; DDF sensitivity tested at 70–85% |
| 5 | **Spatial proximity indicates market similarity** | Adjacent hexes share transportation, amenities, and tenant pools | MAUP stability testing mitigates across resolution scales |
| 6 | **OSM data quality is uniform** | OpenStreetMap coverage varies by city | `osm_confidence` metric scales overlay weights proportionally |
| 7 | **Transit directionality:** Bus stops indicate congestion (−), metro indicates premium connectivity (+) | Validated for Indian metros where metro proximity drives rent premiums | Reversed in cities where bus networks are premium (none identified) |
| 8 | **Snapshot analysis (no temporal dynamics)** | Single scrape date — no seasonal or trend decomposition | Margins may vary ±15% seasonally; interpreted as point-in-time signal |

---

## Data Pipeline

### Input Data

**Source:** MagicBricks rental listings, scraped April 2026

| Column | Description | Used For |
|---|---|---|
| `search_city` | City identifier | Filtering |
| `latitude`, `longitude` | Geocoordinates | H3 hex assignment |
| `bhk_type` | Room configuration (1BHK, 2BHK, etc.) | Supply segmentation, revenue modeling |
| `property_type` | Apartment, Villa, Builder Floor, etc. | Asset classification |
| `monthly_rent` | Asking rent in ₹ | Core pricing metric |
| `sqft` | Built-up or carpet area | Room yield calculation |
| `total_floors` | Building height | Villa classification (≤3 floors) |

### Cities Covered (15)

| City | Listings | UTM Zone |
|---|---|---|
| Bangalore | 13,042 | 32643 |
| Pune | 9,551 | 32643 |
| Hyderabad | 8,714 | 32644 |
| Mumbai | 7,303 | 32643 |
| Kolkata | 6,418 | 32645 |
| Gurgaon | 5,837 | 32643 |
| Chennai | 5,446 | 32644 |
| Ahmedabad | 3,830 | 32643 |
| Jaipur | 3,064 | 32643 |
| Noida | 3,037 | 32644 |
| Greater Noida | 1,610 | 32644 |
| Chandigarh | 965 | 32643 |
| Gandhinagar | 865 | 32643 |
| Visakhapatnam | 852 | 32644 |
| Surat | 748 | 32643 |

---

## Output Deliverables

### Per City

| File | Description |
|---|---|
| `{City}_Investment_Atlas.kml` | Google Earth hex map with rich popup cards (dual-track margins, confidence indicators, scoring bars, spillover aura) |
| `{City}_Master_Report.xlsx` | 7-sheet workbook: Metadata, Top 10, Supply Profile, Full Dataset, DDF Sensitivity, Weight Calibration, Data Quality |
| `{City}_hex_analysis.geojson` | Hex polygons with all metrics for Streamlit dashboard |
| `city_summary.json` | Machine-readable city KPIs for cross-city comparisons |
| `econometrics/` | Moran's I scatterplot, OLS validation plot, regression comparison XLSX |

### Cross-City

| File | Description |
|---|---|
| `India_Expansion_Master.xlsx` | All cities ranked by CAI with margin distributions and spatial statistics |

---

## Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run for a single city
python main.py --city bangalore

# Run all 15 cities
python main.py --all-cities

# Re-run cross-city analysis from cached results
python main.py --compare-only

# Available cities
python main.py --city pune
python main.py --city hyderabad
python main.py --city mumbai
# ... (all 15 city keys listed in city_config.py)
```

---

## Directory Structure

```
BBA_Python_final/
├── main.py                          # Pipeline orchestrator (CLI entry point)
├── config.py                        # All tunable parameters
├── city_config.py                   # 15-city profiles (bounding boxes, CRS)
│
├── data/
│   ├── raw/
│   │   ├── compiled_listings.csv    # Master input (71,282 listings × 40 columns)
│   │   ├── bangalore/               # Legacy KML boundaries (optional)
│   │   └── hyderabad/
│   └── processed/
│       └── {city}/                   # Per-city caches
│           ├── osm_cache.json        # Cached OSM POI data
│           ├── geocache.json         # Reverse geocoding cache
│           └── pca_weights.json      # Calibrated PCA weights
│
├── src/
│   ├── modules/
│   │   ├── loader.py                # Data ingestion + property classification
│   │   ├── spatial.py               # H3 hex assignment + MAUP stability
│   │   ├── aggregator.py            # K-Ring smoothing + Neff + bootstrap CIs
│   │   ├── economics.py             # Dual-track arbitrage (Apt + Villa)
│   │   ├── weight_calibrator.py     # PCA variance-explained weights
│   │   ├── scoring.py               # Composite OPP_SCORE + spillover + tiers
│   │   ├── osm_engine.py            # OpenStreetMap POI automation
│   │   └── validator.py             # Moran's I + OLS + SAR/SEM
│   └── utils/
│       ├── logger.py                # Rich terminal UI
│       └── exporter.py              # KML + XLSX + GeoJSON + JSON exports
│
├── output/
│   ├── {city}/                       # Per-city outputs
│   │   ├── {City}_Investment_Atlas.kml
│   │   ├── {City}_Master_Report.xlsx
│   │   ├── {City}_hex_analysis.geojson
│   │   ├── city_summary.json
│   │   └── econometrics/
│   └── cross_city/
│       └── India_Expansion_Master.xlsx
│
└── app.py                           # Streamlit dashboard
```

---

## Configuration

All parameters live in `config.py`. Key tunables:

| Parameter | Default | Description |
|---|---|---|
| `H3_RESOLUTION` | 7 | Hex size (~5.1 km²). Change affects all spatial analysis. |
| `USE_PCA_WEIGHTS` | True | Data-driven vs expert weights |
| `DDF_APARTMENT` | 0.80 | Base demand discount for apartments |
| `DDF_VILLA` | 0.75 | Base demand discount for villas |
| `KRING_DECAY_BETA` | 0.4 | Spatial smoothing decay rate |
| `NEFF_FULL_CONFIDENCE` | 8 | Min Neff for Tier 1 eligibility |
| `STABILITY_THRESHOLD` | 0.80 | Min MAUP stability for Tier 1 |
| `MORAN_PERMUTATIONS` | 999 | Permutations for robust p-values |

---

## Dependencies

```
pandas >= 2.0
geopandas >= 0.14
numpy >= 1.24
h3 >= 4.0
osmnx >= 1.6
scikit-learn >= 1.3
statsmodels >= 0.14
spreg >= 1.3
libpysal >= 4.9
esda >= 2.5
openpyxl >= 3.1
matplotlib >= 3.7
rich >= 13.0
shapely >= 2.0
```

Install: `pip install h3 osmnx spreg libpysal esda openpyxl rich`

---

## Team

| Name | ID |
|---|---|
| Harshith Bejjanki | SM24UBBA047 |
| Suneeth Boorgula | SM24UBBA016 |
| Sudhiksha | SM24UBBA033 |
| Peddi Sudeeksha | SM24UBBA027 |
| Vedanth Nagaarur | SM24UBBA019 |

**Academic Context:** BBA Python Project — Real Estate Market Analytics

---

*Flent Lens 2.0 · Multi-City Co-Living Intelligence · April 2026*
