"""
Flent Lens — City Configuration Profiles
Each city defines its data paths, coordinate system, geographic boundaries,
and which optional data layers (transit, SEZ) are available.

To add a new city:
  1. Add a dict entry to CITY_PROFILES below
  2. Set ACTIVE_CITY to the new key
  3. Run  python main.py
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# ═══════════════════════════════════════════════════════════════════
# CITY PROFILES
# ═══════════════════════════════════════════════════════════════════
CITY_PROFILES = {

    # ──────────────────────────────────────────────────────────────
    # BANGALORE  (original dataset — wards + transit + SEZ)
    # ──────────────────────────────────────────────────────────────
    "bangalore": {
        "city_name":       "Bangalore",
        "geo_unit_name":   "ward",            # internal key used in column names
        "geo_unit_label":  "BBMP Ward",       # human-readable label for UI/popups
        "crs_projected":   "EPSG:32643",      # UTM Zone 43N
        "bounding_box": {
            "lat": (12.7, 13.2),
            "lon": (77.4, 77.8),
        },

        # ── Input files (relative to BASE_DIR) ──
        "raw_listings_csv":  "data/raw/bangalore/magicbricks_final_listings.csv",
        "geo_kml":           "data/raw/bangalore/gba-369-wards-december-2025.kml",

        # ── Optional layers ──
        "has_transit":  True,
        "transit_kml":  "data/raw/bangalore/bmtc_bus_routes.kml",
        "has_sez":      True,
        "raw_sez_csv":  "data/raw/bangalore/SEZ List /SEZ list - Sheet1.csv",

        # ── Processing ──
        "processed_dir":  "data/processed/bangalore",
        "output_dir":     "output/bangalore",
        "nearest_max_distance_m": 2450,
    },

    # ──────────────────────────────────────────────────────────────
    # HYDERABAD  (pincode map + listings only — no transit/SEZ)
    # ──────────────────────────────────────────────────────────────
    "hyderabad": {
        "city_name":       "Hyderabad",
        "geo_unit_name":   "pincode",
        "geo_unit_label":  "Pincode Zone",
        "crs_projected":   "EPSG:32644",      # UTM Zone 44N
        "bounding_box": {
            "lat": (17.0, 17.65),
            "lon": (78.2, 78.7),
        },

        # ── Input files ──
        "raw_listings_csv":  "data/raw/hyderabad/magicbricks_final_listings_hyderabad.csv",
        "geo_kml":           "data/raw/hyderabad/Hyderabad Pincode Map.kml",

        # ── Optional layers ──
        "has_transit":  False,
        "transit_kml":  None,
        "has_sez":      False,
        "raw_sez_csv":  None,

        # ── Processing ──
        "processed_dir":  "data/processed/hyderabad",
        "output_dir":     "output/hyderabad",
        "nearest_max_distance_m": 3000,
    },
}

# ═══════════════════════════════════════════════════════════════════
# ACTIVE CITY  — change this single line to switch the pipeline
# ═══════════════════════════════════════════════════════════════════
ACTIVE_CITY = "bangalore"


def get_profile():
    """Return the resolved profile dict for the active city."""
    if ACTIVE_CITY not in CITY_PROFILES:
        raise ValueError(
            f"Unknown city '{ACTIVE_CITY}'. "
            f"Available: {list(CITY_PROFILES.keys())}"
        )
    profile = CITY_PROFILES[ACTIVE_CITY].copy()

    # Resolve relative paths to absolute
    def _abs(key):
        val = profile.get(key)
        if val and not os.path.isabs(val):
            profile[key] = os.path.join(BASE_DIR, val)

    _abs('raw_listings_csv')
    _abs('geo_kml')
    _abs('transit_kml')
    _abs('raw_sez_csv')
    _abs('processed_dir')
    _abs('output_dir')

    return profile
