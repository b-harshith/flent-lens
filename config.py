import os
from city_config import get_profile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════
# ACTIVE CITY PROFILE — all paths and flags derive from this
# ═══════════════════════════════════════════════════════════════════
CITY = get_profile()

CITY_NAME       = CITY['city_name']
GEO_UNIT_NAME   = CITY['geo_unit_name']       # "ward" or "pincode"
GEO_UNIT_LABEL  = CITY['geo_unit_label']       # "BBMP Ward" or "Pincode Zone"
BOUNDING_BOX    = CITY['bounding_box']         # {"lat": (min, max), "lon": (min, max)}
HAS_TRANSIT     = CITY['has_transit']
HAS_SEZ         = CITY['has_sez']

# Input Data (Raw)
RAW_LISTINGS_CSV   = CITY['raw_listings_csv']
RAW_SEZ_CSV        = CITY.get('raw_sez_csv') or os.path.join(BASE_DIR, 'data/raw/SEZ List /SEZ list - Sheet1.csv')

# Geographic Boundaries
GEO_KML            = CITY['geo_kml']           # wards KML or pincode KML
TRANSIT_KML        = CITY.get('transit_kml')    # None when transit disabled

# Processed Data (Analytical Outputs)
PROCESSED_DIR      = CITY['processed_dir']
LISTINGS_CSV       = os.path.join(PROCESSED_DIR, 'listings.csv')
SEZ_CSV            = os.path.join(PROCESSED_DIR, 'sez_latlong.csv')
SEZ_KML            = os.path.join(PROCESSED_DIR, 'sez_enriched_wards.kml')
WARDS_PROCESSED    = os.path.join(PROCESSED_DIR, 'wards_processed.csv')
TRANSIT_PROCESSED  = os.path.join(PROCESSED_DIR, 'transit_processed.csv')

# Legacy aliases (used in modules that still reference WARDS_KML / BUS_ROUTES_KML)
WARDS_KML       = GEO_KML
BUS_ROUTES_KML  = TRANSIT_KML

# Output Directory
OUTPUT_DIR      = CITY['output_dir']

# ═══════════════════════════════════════════════════════════════════
# COORDINATE REFERENCE SYSTEMS
# ═══════════════════════════════════════════════════════════════════
CRS_GEOGRAPHIC  = 'EPSG:4326'                  # WGS84 — for KML files
CRS_PROJECTED   = CITY['crs_projected']         # UTM — for distance calculations

# ═══════════════════════════════════════════════════════════════════
# ANALYTICAL PARAMETERS (city-agnostic)
# ═══════════════════════════════════════════════════════════════════
MIN_LISTINGS_PER_BHK = 3        # Minimum listings for statistical reliability
MIN_SQFT_3BHK   = 1100          # Minimum viable sqft for a 3BHK conversion
LARGE_3BHK_SQFT = 1500          # Threshold for 'large' 3BHK

# Dynamic Room Conversion Settings
DYNAMIC_YIELD = 'yes'

# Dynamic Yield Thresholds (only used if DYNAMIC_YIELD == 'yes')
YIELD_3BHK_LARGE_SQFT = 1600
YIELD_3BHK_XL_SQFT    = 2000
YIELD_4BHK_XL_SQFT    = 2300

DEMAND_DISCOUNT_FACTOR = 0.80
OUTLIER_STD_THRESHOLD  = 3.0
MAX_VALID_1BHK_RENT    = 50000

# Margin viability
MARGIN_VIABLE_PCT      = 0.05

# Nearest-ward proximity assignment for listings outside boundaries
NEAREST_WARD_MAX_DISTANCE_M = CITY['nearest_max_distance_m']

# ═══════════════════════════════════════════════════════════════════
# SCORING WEIGHTS
# ═══════════════════════════════════════════════════════════════════
DII_WEIGHT_PRICE_PRESSURE = 0.40
DII_WEIGHT_SFC            = 0.30
DII_WEIGHT_PSF_SPREAD     = 0.30

SFS_WEIGHT_VOLUME    = 0.35
SFS_WEIGHT_SIZE      = 0.30
SFS_WEIGHT_ROI       = 0.35

ECON_WEIGHT_ARBITRAGE = 0.45
ECON_WEIGHT_DII       = 0.30
ECON_WEIGHT_SFS       = 0.25

# Overlay weights: set to 0 when feature is disabled
OVERLAY_WEIGHT_TRANSIT = 0.10 if HAS_TRANSIT else 0.0
OVERLAY_WEIGHT_SEZ     = 0.20 if HAS_SEZ     else 0.0

SEZ_DISTANCE_DECAY_ALPHA = 1.5
SEZ_MIN_DISTANCE_M       = 500

TRANSIT_WEIGHT_DENSITY = 0.50
TRANSIT_WEIGHT_LENGTH  = 0.50

TIER1_PERCENTILE = 75
TIER2_PERCENTILE = 50
TIER3_PERCENTILE = 25

# Spatial Spillover (Neighborhood Contagion) Boosts
SPILLOVER_BOOST_TIER1  = 1.10   # +10%
SPILLOVER_BOOST_TIER2  = 1.05   # +5%
SPILLOVER_BOOST_TIER3  = 1.025  # +2.5%
ISOLATION_PENALTY      = 0.85   # -15% for Tier 1 wards with ZERO Tier 1/2 neighbors
