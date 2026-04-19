"""
Flent Lens 2.0 — Data Ingestion
Loads from the compiled multi-city CSV, filters by city,
validates schema, and produces a GeoDataFrame ready for H3 assignment.
"""
import os
import pandas as pd
import geopandas as gpd
import numpy as np
import config
from city_config import COMPILED_LISTINGS_CSV
from src.utils.logger import (
    print_info, print_detail, print_warning, print_success, log_process
)


def classify_asset(row):
    """
    Rule-based property typology classifier.
    Returns 'villa' or 'apartment' based on physical characteristics.
    """
    pt = str(row.get('property_type', '')).lower().strip()
    sqft = row.get('sqft', 0) or 0
    floors = row.get('total_floors', 99) or 99

    # Explicit villa/house keywords + physical validation
    if any(kw in pt for kw in ['independent house', 'villa', 'residential house',
                                 'farm house', 'bungalow']):
        if sqft >= config.VILLA_MIN_SQFT and floors <= config.VILLA_MAX_FLOORS:
            return 'villa'
        elif sqft >= config.VILLA_MIN_SQFT:
            return 'villa'

    # Builder floors are functionally apartments
    if 'independent floor' in pt or 'builder floor' in pt:
        return 'apartment'

    return 'apartment'


def extract_bhk(row):
    """
    Extract numeric BHK. Priority:
      1. bhk_type column (if populated)
      2. listing_url pattern (e.g. '3-BHK-1200-Sq-ft')
    """
    import re
    # Try column value first
    val = row.get('bhk_type')
    if pd.notna(val):
        s = str(val).strip()
        for char in s:
            if char.isdigit():
                return int(char)

    # Fallback: parse from URL
    url = row.get('listing_url', '')
    if pd.notna(url):
        m = re.search(r'(\d+)-BHK', str(url), re.IGNORECASE)
        if m:
            return int(m.group(1))

    return None


def load_listings(city_key: str = None) -> gpd.GeoDataFrame:
    """
    Load listings from the compiled CSV for a specific city.
    Returns a cleaned GeoDataFrame with validated coordinates, rent, sqft, BHK, and asset_type.
    """
    target_city = config.CITY_NAME if city_key is None else config.CITY['city_name']

    with log_process(f"Loading listings for {target_city}"):
        # 1. Read and filter by city
        if not os.path.exists(COMPILED_LISTINGS_CSV):
            raise FileNotFoundError(
                f"Compiled listings CSV not found at: {COMPILED_LISTINGS_CSV}\n"
                f"Run the scraper/parser first, or place compiled_listings.csv in data/raw/"
            )

        df = pd.read_csv(COMPILED_LISTINGS_CSV, low_memory=False)
        print_detail(f"Master CSV: {len(df):,} total rows across {df['search_city'].nunique()} cities")

        city_df = df[df['search_city'].str.lower() == target_city.lower()].copy()
        print_detail(f"Filtered to {target_city}: {len(city_df):,} rows")

        if len(city_df) == 0:
            raise ValueError(f"No listings found for city '{target_city}' in compiled CSV. "
                           f"Available cities: {df['search_city'].unique().tolist()}")

        # 2. Validate coordinates
        city_df['latitude'] = pd.to_numeric(city_df['latitude'], errors='coerce')
        city_df['longitude'] = pd.to_numeric(city_df['longitude'], errors='coerce')
        before = len(city_df)
        # Drop missing, zero, or clearly invalid coords
        city_df = city_df.dropna(subset=['latitude', 'longitude'])
        city_df = city_df[(city_df['latitude'] > 1) & (city_df['longitude'] > 1)]

        bb = config.BOUNDING_BOX
        city_df = city_df[
            (city_df['latitude'].between(bb['lat'][0], bb['lat'][1])) &
            (city_df['longitude'].between(bb['lon'][0], bb['lon'][1]))
        ]
        dropped_geo = before - len(city_df)
        if dropped_geo > 0:
            print_warning(f"Dropped {dropped_geo} listings (missing/out-of-bounds coordinates)")

        # 3. Clean and validate rent
        city_df['monthly_rent'] = pd.to_numeric(city_df['monthly_rent'], errors='coerce')
        city_df = city_df.dropna(subset=['monthly_rent'])
        city_df = city_df[
            (city_df['monthly_rent'] >= config.MIN_RENT) &
            (city_df['monthly_rent'] <= config.MAX_RENT)
        ]

        # 4. Clean sqft
        city_df['sqft'] = pd.to_numeric(city_df['sqft'], errors='coerce').fillna(0)

        # 5. Extract BHK (from column or URL fallback)
        city_df['bhk_type'] = city_df.apply(extract_bhk, axis=1)
        before_bhk = len(city_df)
        city_df = city_df.dropna(subset=['bhk_type'])
        city_df['bhk_type'] = city_df['bhk_type'].astype(int)
        print_detail(f"BHK extracted: {len(city_df)} valid ({before_bhk - len(city_df)} missing)")

        # 6. Clean total_floors for villa classification
        city_df['total_floors'] = pd.to_numeric(city_df['total_floors'], errors='coerce').fillna(99)

        # 7. Classify asset type (apartment vs villa)
        city_df['asset_type'] = city_df.apply(classify_asset, axis=1)

        # 8. Compute per-sqft rent
        city_df['price_per_sqft'] = np.where(
            city_df['sqft'] > 0,
            city_df['monthly_rent'] / city_df['sqft'],
            np.nan
        )

        # 9. Convert to GeoDataFrame
        listings_gdf = gpd.GeoDataFrame(
            city_df,
            geometry=gpd.points_from_xy(city_df['longitude'], city_df['latitude']),
            crs=config.CRS_GEOGRAPHIC
        )

        # 10. Summary stats
        bhk_dist = listings_gdf['bhk_type'].value_counts().sort_index()
        asset_dist = listings_gdf['asset_type'].value_counts()
        median_rent = listings_gdf['monthly_rent'].median()

        print_info(f"Loaded [highlight]{len(listings_gdf):,}[/highlight] valid listings")
        print_detail(f"BHK distribution: {dict(bhk_dist)}")
        print_detail(f"Asset types: {dict(asset_dist)}")
        print_detail(f"Median monthly rent: ₹{median_rent:,.0f}")

        return listings_gdf


def load_admin_boundaries() -> gpd.GeoDataFrame:
    """
    Load administrative boundary KML (wards/pincodes) if available.
    Used for reverse geocoding overlay and zoning context, NOT for primary zoning.
    Returns None if no KML is configured.
    """
    if not config.HAS_ADMIN_KML:
        return None

    kml_path = config.ADMIN_KML
    if not kml_path or not os.path.exists(kml_path):
        print_warning(f"Admin KML configured but not found at: {kml_path}")
        return None

    with log_process(f"Loading admin boundaries from {os.path.basename(kml_path)}"):
        import fiona
        fiona.drvsupport.supported_drivers['KML'] = 'rw'
        layers = fiona.listlayers(kml_path)

        if not layers:
            print_warning("No layers found in admin KML")
            return None

        gdf = gpd.read_file(kml_path, driver='KML', layer=layers[0])
        gdf = gdf.to_crs(config.CRS_GEOGRAPHIC)

        # Standardize column names
        if 'Name' in gdf.columns and 'admin_name' not in gdf.columns:
            gdf = gdf.rename(columns={'Name': 'admin_name'})

        print_detail(f"Loaded {len(gdf)} admin zones from '{layers[0]}'")
        return gdf
