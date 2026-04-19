"""
Flent Lens 2.0 — Master Configuration
All analytical parameters, thresholds, weights, and paths.
This file is the single source of truth for every tunable in the pipeline.
"""
import os
from city_config import get_profile, COMPILED_LISTINGS_CSV

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════
# ACTIVE CITY PROFILE — all paths and flags derive from this
# ═══════════════════════════════════════════════════════════════════
CITY = get_profile()

CITY_NAME       = CITY['city_name']
CITY_KEY        = CITY['city_key']
CITY_CODE       = CITY.get('city_code', 'UNK')
BOUNDING_BOX    = CITY['bounding_box']
HAS_ADMIN_KML   = CITY.get('has_admin_kml', False)
ADMIN_KML       = CITY.get('admin_kml')

# Directories
PROCESSED_DIR   = CITY['processed_dir']
OUTPUT_DIR      = CITY['output_dir']

# ═══════════════════════════════════════════════════════════════════
# COORDINATE REFERENCE SYSTEMS
# ═══════════════════════════════════════════════════════════════════
CRS_GEOGRAPHIC  = 'EPSG:4326'                  # WGS84
CRS_PROJECTED   = CITY['crs_projected']         # UTM — for distance calculations

# ═══════════════════════════════════════════════════════════════════
# H3 HEXAGONAL GRID CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
H3_RESOLUTION        = 7              # ~5.1 sq km per hexagon
H3_SENSITIVITY_RES   = [6, 7, 8]     # MAUP stability testing resolutions
STABILITY_THRESHOLD  = 0.80           # Min stability score for Tier 1 eligibility

# ═══════════════════════════════════════════════════════════════════
# K-RING SPATIAL SMOOTHING
# ═══════════════════════════════════════════════════════════════════
KRING_RADIUS         = 1              # Number of hex rings to include in smoothing
KRING_DECAY_BETA     = 0.4            # Distance decay: w = count / (1 + β * dist_km)
NEFF_FULL_CONFIDENCE = 8              # Neff >= this → full confidence
NEFF_LOW_CONFIDENCE  = 5              # Neff >= this → low_confidence (can be Tier 2/3)
BOOTSTRAP_ITERATIONS = 500            # For weighted bootstrap confidence intervals
BOOTSTRAP_CI_PCT     = 90             # Confidence interval percentage

# ═══════════════════════════════════════════════════════════════════
# LISTING FILTERS
# ═══════════════════════════════════════════════════════════════════
MIN_RENT             = 5_000          # ₹ — floor for valid rent
MAX_RENT             = 5_00_000       # ₹ — ceiling for valid rent
MAX_VALID_1BHK_RENT  = 50_000         # ₹ — cap on 1BHK (outlier removal)
MIN_SQFT_APARTMENT   = 1_100          # Min sqft for 3BHK apartment conversion
MIN_SQFT_VILLA       = 1_800          # Min sqft for villa/house conversion
OUTLIER_STD_THRESHOLD = 3.0           # Std devs for rent outlier removal

# ═══════════════════════════════════════════════════════════════════
# PROPERTY TYPOLOGY CLASSIFICATION
# ═══════════════════════════════════════════════════════════════════
VILLA_MIN_SQFT       = 1_800          # Physical floor area threshold
VILLA_MAX_FLOORS     = 3              # Villas are low-rise

# ═══════════════════════════════════════════════════════════════════
# ECONOMIC MODEL — DEMAND DISCOUNT FACTOR (DDF)
# ═══════════════════════════════════════════════════════════════════
DDF_APARTMENT        = 0.80           # Base DDF for apartments
DDF_VILLA            = 0.75           # Base DDF for villas (harder stabilization)
DDF_ELASTIC_BAND     = 0.10           # ± elastic adjustment based on demand pressure
DDF_SENSITIVITY_RANGE = [0.70, 0.75, 0.80, 0.85]  # For sensitivity table in reports

# ═══════════════════════════════════════════════════════════════════
# DYNAMIC ROOM YIELD MODEL
# ═══════════════════════════════════════════════════════════════════
DYNAMIC_YIELD = True
# Apartment yield thresholds
YIELD_APT_STANDARD   = 3              # < 1400 sqft → 3 rooms
YIELD_APT_LARGE_SQFT = 1_400          # >= 1400 sqft → 3.5 rooms
YIELD_APT_XL_SQFT    = 2_000          # >= 2000 sqft → 4 rooms
# Villa yield thresholds
YIELD_VILLA_BASE     = 4              # < 2500 sqft → 4 rooms
YIELD_VILLA_LARGE_SQFT = 2_500        # >= 2500 sqft → 5 rooms
YIELD_VILLA_XL_SQFT  = 3_000          # >= 3000 sqft → 6 rooms

# Margin viability
MARGIN_VIABLE_FLOOR  = 5_000          # ₹ — minimum monthly margin to be "viable"
MARGIN_VIABLE_PCT    = 0.05           # 5% minimum margin ratio
MIN_LISTINGS_PER_BHK = 3              # Min listings per BHK type for reliability

# ═══════════════════════════════════════════════════════════════════
# PCA WEIGHT CALIBRATION
# ═══════════════════════════════════════════════════════════════════
USE_PCA_WEIGHTS      = True           # True = data-driven, False = expert defaults
PCA_WEIGHT_FLOOR     = 0.10           # No weight below 10%

# ═══════════════════════════════════════════════════════════════════
# EXPERT DEFAULT SCORING WEIGHTS (used when USE_PCA_WEIGHTS = False)
# ═══════════════════════════════════════════════════════════════════
# Demand Intensity Index (DII) sub-weights
DII_WEIGHT_PRICE_PRESSURE = 0.40
DII_WEIGHT_SFC            = 0.30
DII_WEIGHT_PSF_SPREAD     = 0.30

# Supply Feasibility Score (SFS) sub-weights
SFS_WEIGHT_VOLUME    = 0.35
SFS_WEIGHT_SIZE      = 0.30
SFS_WEIGHT_ROI       = 0.35

# Composite ECON_SCORE weights
ECON_WEIGHT_ARBITRAGE = 0.45
ECON_WEIGHT_DII       = 0.30
ECON_WEIGHT_SFS       = 0.25

# OSM Overlay weights (scaled by osm_confidence at runtime)
OVERLAY_WEIGHT_TRANSIT    = 0.10
OVERLAY_WEIGHT_EMPLOYMENT = 0.15
OVERLAY_WEIGHT_LIFESTYLE  = 0.05

# ═══════════════════════════════════════════════════════════════════
# OSM CONFIGURATION
# ═══════════════════════════════════════════════════════════════════
OSM_CACHE_DAYS       = 90             # Days before cache is considered stale
OSM_CONFIDENCE_FLOOR = 0.40           # Below this, overlay weights are down-scaled

# Transit directional weighting
TRANSIT_BUS_WEIGHT   = -0.10          # Bus stops = negative (noise/congestion)
TRANSIT_METRO_WEIGHT = +0.15          # Metro/Rail = positive (premium demand)

# ═══════════════════════════════════════════════════════════════════
# TIER ASSIGNMENT
# ═══════════════════════════════════════════════════════════════════
TIER1_PERCENTILE = 75
TIER2_PERCENTILE = 50
TIER3_PERCENTILE = 25

# ═══════════════════════════════════════════════════════════════════
# SPATIAL SPILLOVER (Neighborhood Contagion via H3 K-Ring)
# ═══════════════════════════════════════════════════════════════════
SPILLOVER_BOOST_TIER1  = 1.10   # +10%
SPILLOVER_BOOST_TIER2  = 1.05   # +5%
SPILLOVER_BOOST_TIER3  = 1.025  # +2.5%
ISOLATION_PENALTY      = 0.85   # -15% for Tier 1 hexes with ZERO Tier 1/2 neighbors

# ═══════════════════════════════════════════════════════════════════
# SPATIAL ECONOMETRICS
# ═══════════════════════════════════════════════════════════════════
MORAN_PERMUTATIONS   = 999            # Number of permutations for robust p-values
SAR_KNN              = 6              # K-nearest neighbors for spatial weights
SAR_DISTANCE_CUTOFF  = 5_000          # meters — inverse-distance W cutoff

# ═══════════════════════════════════════════════════════════════════
# CITY ATTRACTIVENESS INDEX (CAI) — Cross-City Scoring
# ═══════════════════════════════════════════════════════════════════
CAI_WEIGHT_DEMAND    = 0.25
CAI_WEIGHT_MARGIN    = 0.25
CAI_WEIGHT_SUPPLY    = 0.15
CAI_WEIGHT_SPATIAL   = 0.10
CAI_WEIGHT_MACRO     = 0.15
CAI_WEIGHT_RISK      = 0.10

# ═══════════════════════════════════════════════════════════════════
# LEGACY COMPATIBILITY — kept so old module imports don't break
# ═══════════════════════════════════════════════════════════════════
GEO_UNIT_NAME   = "hex"
GEO_UNIT_LABEL  = "Hex Zone"
DEMAND_DISCOUNT_FACTOR = DDF_APARTMENT
HAS_TRANSIT     = False    # Legacy — now handled by OSM engine
HAS_SEZ         = False    # Legacy — now handled by OSM engine
