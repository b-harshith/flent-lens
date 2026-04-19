"""
Flent Lens 2.0 — City Configuration Profiles
Each city defines its bounding box, coordinate system, and optional flags.

Architecture change:  No KML boundary files required.
All spatial zoning is handled mathematically via H3 hexagonal grids.

To add a new city:
  1. Add a dict entry to CITY_PROFILES below
  2. Run  python main.py --city <key>
"""
import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Master listings CSV (all 15 cities in one file)
COMPILED_LISTINGS_CSV = os.path.join(BASE_DIR, "data", "raw", "compiled_listings.csv")

# ═══════════════════════════════════════════════════════════════════
# CITY PROFILES
# ═══════════════════════════════════════════════════════════════════
CITY_PROFILES = {

    # ──────────────────────────────────────────────────────────────
    # BANGALORE  (anchor city — highest data density)
    # ──────────────────────────────────────────────────────────────
    "bangalore": {
        "city_name":        "Bangalore",
        "city_code":        "BLR",
        "search_city":      "Bangalore",       # value in CSV 'search_city' column
        "crs_projected":    "EPSG:32643",      # UTM Zone 43N
        "bounding_box": {
            "lat": (12.7, 13.2),
            "lon": (77.4, 77.8),
        },
        # Legacy boundary KML (disabled for unified notation)
        "admin_kml":        "data/raw/bangalore/gba-369-wards-december-2025.kml",
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # HYDERABAD
    # ──────────────────────────────────────────────────────────────
    "hyderabad": {
        "city_name":        "Hyderabad",
        "city_code":        "HYD",
        "search_city":      "Hyderabad",
        "crs_projected":    "EPSG:32644",      # UTM Zone 44N
        "bounding_box": {
            "lat": (17.0, 17.65),
            "lon": (78.2, 78.7),
        },
        "admin_kml":        "data/raw/hyderabad/Hyderabad Pincode Map.kml",
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # PUNE
    # ──────────────────────────────────────────────────────────────
    "pune": {
        "city_name":        "Pune",
        "city_code":        "PNQ",
        "search_city":      "Pune",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (18.35, 18.70),
            "lon": (73.70, 74.05),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # MUMBAI
    # ──────────────────────────────────────────────────────────────
    "mumbai": {
        "city_name":        "Mumbai",
        "city_code":        "BOM",
        "search_city":      "Mumbai",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (18.85, 19.30),
            "lon": (72.75, 73.05),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # CHENNAI
    # ──────────────────────────────────────────────────────────────
    "chennai": {
        "city_name":        "Chennai",
        "city_code":        "MAA",
        "search_city":      "Chennai",
        "crs_projected":    "EPSG:32644",
        "bounding_box": {
            "lat": (12.85, 13.25),
            "lon": (80.10, 80.35),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # GURGAON
    # ──────────────────────────────────────────────────────────────
    "gurgaon": {
        "city_name":        "Gurgaon",
        "city_code":        "GGN",
        "search_city":      "Gurgaon",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (28.35, 28.60),
            "lon": (76.90, 77.15),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # KOLKATA
    # ──────────────────────────────────────────────────────────────
    "kolkata": {
        "city_name":        "Kolkata",
        "city_code":        "CCU",
        "search_city":      "Kolkata",
        "crs_projected":    "EPSG:32645",      # UTM Zone 45N
        "bounding_box": {
            "lat": (22.40, 22.70),
            "lon": (88.25, 88.50),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # AHMEDABAD
    # ──────────────────────────────────────────────────────────────
    "ahmedabad": {
        "city_name":        "Ahmedabad",
        "city_code":        "AMD",
        "search_city":      "Ahmedabad",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (22.90, 23.15),
            "lon": (72.45, 72.75),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # JAIPUR
    # ──────────────────────────────────────────────────────────────
    "jaipur": {
        "city_name":        "Jaipur",
        "city_code":        "JAI",
        "search_city":      "Jaipur",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (26.75, 27.05),
            "lon": (75.65, 75.95),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # NOIDA
    # ──────────────────────────────────────────────────────────────
    "noida": {
        "city_name":        "Noida",
        "city_code":        "NDA",
        "search_city":      "Noida",
        "crs_projected":    "EPSG:32644",
        "bounding_box": {
            "lat": (28.45, 28.70),
            "lon": (77.25, 77.55),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # GREATER NOIDA
    # ──────────────────────────────────────────────────────────────
    "greater_noida": {
        "city_name":        "Greater Noida",
        "city_code":        "GND",
        "search_city":      "Greater Noida",
        "crs_projected":    "EPSG:32644",
        "bounding_box": {
            "lat": (28.40, 28.60),
            "lon": (77.40, 77.60),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # CHANDIGARH
    # ──────────────────────────────────────────────────────────────
    "chandigarh": {
        "city_name":        "Chandigarh",
        "city_code":        "IXC",
        "search_city":      "Chandigarh",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (30.65, 30.80),
            "lon": (76.70, 76.85),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # GANDHINAGAR
    # ──────────────────────────────────────────────────────────────
    "gandhinagar": {
        "city_name":        "Gandhinagar",
        "city_code":        "GNR",
        "search_city":      "Gandhinagar",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (23.15, 23.35),
            "lon": (72.60, 72.75),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # SURAT
    # ──────────────────────────────────────────────────────────────
    "surat": {
        "city_name":        "Surat",
        "city_code":        "STV",
        "search_city":      "Surat",
        "crs_projected":    "EPSG:32643",
        "bounding_box": {
            "lat": (21.10, 21.30),
            "lon": (72.75, 72.95),
        },
        "has_admin_kml":    False,
    },

    # ──────────────────────────────────────────────────────────────
    # VISAKHAPATNAM
    # ──────────────────────────────────────────────────────────────
    "visakhapatnam": {
        "city_name":        "Visakhapatnam",
        "city_code":        "VTZ",
        "search_city":      "Visakhapatnam",
        "crs_projected":    "EPSG:32644",
        "bounding_box": {
            "lat": (17.60, 17.85),
            "lon": (83.15, 83.45),
        },
        "has_admin_kml":    False,
    },
}

# ═══════════════════════════════════════════════════════════════════
# ACTIVE CITY  — change this single line to switch the pipeline
# ═══════════════════════════════════════════════════════════════════
ACTIVE_CITY = "bangalore"


def get_profile(city_key=None):
    """Return the resolved profile dict for a city (defaults to ACTIVE_CITY)."""
    key = city_key or ACTIVE_CITY
    if key not in CITY_PROFILES:
        raise ValueError(
            f"Unknown city '{key}'. "
            f"Available: {list(CITY_PROFILES.keys())}"
        )
    profile = CITY_PROFILES[key].copy()
    profile['city_key'] = key

    # Resolve relative paths to absolute
    for path_key in ['admin_kml']:
        val = profile.get(path_key)
        if val and not os.path.isabs(val):
            profile[path_key] = os.path.join(BASE_DIR, val)

    # Ensure output and processed dirs exist
    profile['processed_dir'] = os.path.join(BASE_DIR, 'data', 'processed', key)
    profile['output_dir'] = os.path.join(BASE_DIR, 'output', key)

    return profile
