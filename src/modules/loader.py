import pandas as pd
import geopandas as gpd
import config
import fiona
import os
import re
import xml.etree.ElementTree as ET
from src.utils.logger import console, print_success, print_error, print_info, print_warning, print_detail, log_process

def load_listings(path: str = None) -> gpd.GeoDataFrame:
    path = path or config.LISTINGS_CSV
    with log_process("Loading Listings"):
        try:
            df = pd.read_csv(path, dtype={'listing_id': str})
        except FileNotFoundError:
            print_error(f"Listings file not found at {path}")
            return gpd.GeoDataFrame(columns=['listing_id', 'latitude', 'longitude', 'bhk_type', 'monthly_rent', 'listing_type', 'sqft', 'geometry'], crs=config.CRS_GEOGRAPHIC)

        # Handle missing listing_type column (Hyderabad CSV omits it)
        if 'listing_type' not in df.columns:
            df['listing_type'] = 'rent'

        REQUIRED = ['listing_id', 'latitude', 'longitude', 'bhk_type', 'monthly_rent', 'listing_type', 'sqft']
        missing = [c for c in REQUIRED if c not in df.columns]
        if missing:
            raise ValueError(f'Missing required columns: {missing}')

        df = df[df['listing_type'] == 'rent'].copy()
        df = df.dropna(subset=['latitude', 'longitude', 'monthly_rent', 'bhk_type'])
        
        df['monthly_rent'] = pd.to_numeric(df['monthly_rent'], errors='coerce')
        df['sqft']         = pd.to_numeric(df['sqft'],         errors='coerce')
        df['bhk_type']     = df['bhk_type'].astype(int)

        df = df[(df['monthly_rent'] >= 5_000) & (df['monthly_rent'] <= 5_00_000)]
        df = df[(df['bhk_type'] >= 1) & (df['bhk_type'] <= 6)]

        # Filter out zero/invalid coordinates BEFORE geo-fence
        zero_coords = (df['latitude'].abs() < 1) | (df['longitude'].abs() < 1)
        if zero_coords.sum() > 0:
            print_detail(f"Dropped {zero_coords.sum()} listings with zero/invalid coordinates")
            df = df[~zero_coords]

        # City-specific bounding box from config
        lat_min, lat_max = config.BOUNDING_BOX['lat']
        lon_min, lon_max = config.BOUNDING_BOX['lon']
        before = len(df)
        df = df[(df['latitude'].between(lat_min, lat_max)) & (df['longitude'].between(lon_min, lon_max))]
        dropped = before - len(df)
        if dropped > 0:
            print_detail(f"Geo-fence ({config.CITY_NAME}): dropped {dropped:,} listings outside [{lat_min}–{lat_max}] lat, [{lon_min}–{lon_max}] lon")
                
        if 'days_on_market' not in df.columns:
            df['days_on_market'] = pd.NA

        gdf = gpd.GeoDataFrame(
            df, geometry=gpd.points_from_xy(df['longitude'], df['latitude']),
            crs=config.CRS_GEOGRAPHIC
        )
        print_info(f"Loaded [highlight]{len(gdf)}[/highlight] valid listings for [highlight]{config.CITY_NAME}[/highlight].")
        return gdf

def load_kml(path: str, layer: int = 0) -> gpd.GeoDataFrame:
    fiona.drvsupport.supported_drivers['KML'] = 'rw'
    try:
        layers = fiona.listlayers(path)
        gdf = gpd.read_file(path, driver='KML', layer=layers[layer])
        gdf = gdf.to_crs(config.CRS_GEOGRAPHIC)
        gdf = gdf[~gdf.geometry.is_empty & gdf.geometry.notna()].reset_index(drop=True)
        return gdf
    except Exception as e:
        print_error(f"Could not load KML at {path}. Error: {e}")
        return gpd.GeoDataFrame(columns=['geometry'], crs=config.CRS_GEOGRAPHIC)

def _parse_kml_attributes(path: str) -> pd.DataFrame:
    """
    Parse attributes from KML ExtendedData/SchemaData/SimpleData,
    which fiona silently drops. Returns a DataFrame indexed by row order.
    Works for both ward KMLs and pincode KMLs.
    """
    ns_map = [
        'http://www.opengis.net/kml/2.2',
        'http://earth.google.com/kml/2.2',
        'http://earth.google.com/kml/2.1',
        '',
    ]
    tree = ET.parse(path)
    root = tree.getroot()

    records = []
    for ns in ns_map:
        prefix = f'{{{ns}}}' if ns else ''
        placemarks = root.findall(f'.//{prefix}Placemark')
        if not placemarks:
            continue
        for pm in placemarks:
            rec = {}
            # Grab the <name> element as well (pincode KMLs use it)
            name_el = pm.find(f'{prefix}name')
            if name_el is not None and name_el.text:
                rec['_kml_name'] = name_el.text.strip()
            # Try both namespaced and bare SimpleData
            for parent in [pm.find(f'.//{prefix}SchemaData'),
                           pm.find('.//SchemaData'),
                           pm.find(f'.//{prefix}ExtendedData'),
                           pm.find('.//ExtendedData')]:
                if parent is None:
                    continue
                for sd in parent.iter():
                    tag = sd.tag.split('}')[-1]
                    if tag in ('SimpleData', 'Data'):
                        name = sd.get('name', '')
                        val = (sd.text or '').strip()
                        if name and name not in rec:
                            rec[name] = val
            records.append(rec)
        if records:
            break

    return pd.DataFrame(records)


def load_geo_zones(path: str = None) -> gpd.GeoDataFrame:
    """
    Load geographic zones — works for both BBMP ward KMLs and pincode KMLs.
    
    The function auto-detects the schema from the KML attributes and produces
    a normalized GeoDataFrame with columns: ['ward_id', 'ward_name', 'geometry']
    (and optionally 'zone_name').
    
    We keep 'ward_id' and 'ward_name' as column names regardless of whether the 
    actual geo-unit is a ward, pincode, or something else. This avoids cascading 
    renames across the entire analytics pipeline.
    """
    path = path or config.GEO_KML
    geo_label = config.GEO_UNIT_LABEL

    with log_process(f"Loading {geo_label}s (parsing SchemaData attributes)"):
        # Get geometries via geopandas
        gdf = load_kml(path)

        # Parse rich attributes from raw XML (fiona drops ExtendedData/SchemaData)
        attrs = _parse_kml_attributes(path)

        if len(attrs) == len(gdf) and not attrs.empty:
            # Attach parsed attributes to geometry rows by position
            gdf = gdf.reset_index(drop=True)
            attrs = attrs.reset_index(drop=True)

            # ── DETECTION: Is this a pincode KML or a ward KML? ──
            is_pincode_kml = 'PINCODE' in attrs.columns

            if is_pincode_kml:
                # ── PINCODE KML SCHEMA ──
                # Schema: PINCODE, PT_ID, STATE_UT
                gdf['ward_id']   = attrs['PINCODE'].astype(str).str.strip()
                gdf['ward_name'] = attrs['PINCODE'].astype(str).str.strip()
                if 'STATE_UT' in attrs.columns:
                    gdf['zone_name'] = attrs['STATE_UT'].astype(str).str.strip()
                print_detail(f"Detected pincode KML schema — {gdf['ward_id'].nunique()} unique pincodes")

            else:
                # ── WARD KML SCHEMA (original Bangalore logic) ──
                # USE GLOBALLY UNIQUE ID
                if 'id' in attrs.columns:
                    def _extract_global_id(raw_id):
                        """Extract numeric suffix from 'ward_369_final.N' → N"""
                        m = re.search(r'\.(\d+)$', str(raw_id))
                        return int(m.group(1)) if m else None

                    gdf['ward_id'] = attrs['id'].apply(_extract_global_id).astype(str)
                    print_detail(f"Extracted {gdf['ward_id'].nunique()} globally unique ward IDs from 'id' field")
                elif 'ward_id' in attrs.columns:
                    # Fallback: construct composite key from zone + ward_id
                    if 'zone_name' in attrs.columns:
                        gdf['ward_id'] = (attrs['zone_name'].str.strip() + '_' + attrs['ward_id'].str.strip())
                    else:
                        gdf['ward_id'] = attrs['ward_id'].astype(str).str.strip()
                else:
                    gdf['ward_id'] = [f'W_{i:03d}' for i in range(len(gdf))]

                # Ward name: prefer Ward_Name (has format "N - Name"), extract just the name part
                if 'Ward_Name' in attrs.columns:
                    def _clean_ward_name(raw):
                        """Strip leading 'N - ' prefix from 'Ward_Name' like '25 - Vinayaka Layout'"""
                        raw = str(raw).strip()
                        m = re.match(r'^\d+\s*-\s*(.+)$', raw)
                        return m.group(1).strip() if m else raw
                    gdf['ward_name'] = attrs['Ward_Name'].apply(_clean_ward_name)
                elif 'ward_name' in attrs.columns:
                    gdf['ward_name'] = attrs['ward_name'].astype(str).str.strip()
                elif 'Name' in attrs.columns:
                    gdf['ward_name'] = attrs['Name'].astype(str).str.strip()
                elif '_kml_name' in attrs.columns:
                    gdf['ward_name'] = attrs['_kml_name'].astype(str).str.strip()
                else:
                    gdf['ward_name'] = gdf['ward_id']

                # Carry useful fields for downstream analysis
                keep_extras = ['Corporation', 'ac', 'Assembly', 'zone_name',
                               'ward_id']  # original per-zone ward_id
                for col in keep_extras:
                    target = col.lower()
                    if target == 'ward_id':
                        target = 'zone_ward_num'  # keep original per-zone number
                    if col in attrs.columns:
                        gdf[target] = attrs[col]

            print_detail(f"Parsed {len(attrs.columns)} attributes from SchemaData XML")
        else:
            print_warning("SchemaData parse mismatch — using synthetic IDs.")
            if 'Name' in gdf.columns and gdf['Name'].str.len().max() > 0:
                gdf = gdf.rename(columns={'Name': 'ward_name'})
                gdf['ward_id'] = gdf['ward_name']
            else:
                gdf['ward_name'] = [f'{config.GEO_UNIT_LABEL} {i+1}' for i in range(len(gdf))]
                gdf['ward_id'] = [f'{i+1}' for i in range(len(gdf))]

        keep_cols = ['ward_id', 'ward_name', 'zone_name', 'geometry']
        gdf = gdf[[c for c in keep_cols if c in gdf.columns]].copy()
        # Convert ward_id to string so sjoin joins cleanly
        gdf['ward_id'] = gdf['ward_id'].astype(str)

        # Handle duplicates
        dupes = gdf.duplicated(subset='ward_id').sum()
        if dupes > 0:
            print_warning(f"{dupes} duplicate IDs found — merging geometries")
            gdf = gdf.dissolve(by='ward_id', aggfunc='first').reset_index()

        print_info(f"Loaded [highlight]{len(gdf)}[/highlight] {geo_label}s. "
                   f"Sample: {gdf['ward_id'].iloc[0]} — {gdf.get('ward_name', pd.Series(['?'])).iloc[0]}")
        return gdf


# Legacy alias so existing imports don't break
load_wards = load_geo_zones


def load_bus_routes(path: str = None) -> gpd.GeoDataFrame:
    with log_process("Loading Bus Routes"):
        if not config.HAS_TRANSIT:
            print_info("Transit data disabled for this city — returning empty routes.")
            return gpd.GeoDataFrame(columns=['route_id', 'route_name', 'geometry'], crs=config.CRS_GEOGRAPHIC)

        path = path or config.TRANSIT_KML
        if path is None:
            print_warning("No transit KML path configured.")
            return gpd.GeoDataFrame(columns=['route_id', 'route_name', 'geometry'], crs=config.CRS_GEOGRAPHIC)

        gdf = load_kml(path)
        rename_map = {'kgisbmtcrootid': 'route_id', 'kgisbmtcrootname': 'route_name'}
        existing_renames = {k: v for k, v in rename_map.items() if k in gdf.columns}
        if existing_renames: gdf = gdf.rename(columns=existing_renames)
        if 'route_id' not in gdf.columns: gdf['route_id'] = [f'R_{i:04d}' for i in range(len(gdf))]
        else: gdf['route_id'] = gdf['route_id'].astype(str)
        keep_cols = ['route_id', 'route_name', 'geometry']
        gdf = gdf[[c for c in keep_cols if c in gdf.columns]].copy()
        print_info(f"Loaded [highlight]{len(gdf)}[/highlight] routes.")
        return gdf

def load_sez(path: str = None) -> gpd.GeoDataFrame:
    with log_process("Loading SEZ Points"):
        if not config.HAS_SEZ:
            print_info("SEZ data disabled for this city — returning empty SEZ set.")
            return gpd.GeoDataFrame(columns=['geometry'], crs=config.CRS_GEOGRAPHIC)

        path = path or config.SEZ_CSV
        try:
            df = pd.read_csv(path)
        except FileNotFoundError:
            print_error(f"SEZ data missing at {path}")
            return gpd.GeoDataFrame(columns=['geometry'], crs=config.CRS_GEOGRAPHIC)
        df['latitude']  = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')
        df = df.dropna(subset=['latitude', 'longitude'])
        gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df['longitude'], df['latitude']), crs=config.CRS_GEOGRAPHIC)
        print_info(f"Loaded [highlight]{len(gdf)}[/highlight] SEZ points.")
        return gdf

def validate_schema(listings_gdf, wards_gdf, routes_gdf=None, sez_gdf=None) -> None:
    with log_process("Schema Validation"):
        if len(listings_gdf) == 0: print_warning("Listings dataset is empty.")
        if len(wards_gdf) == 0: print_warning(f"{config.GEO_UNIT_LABEL} dataset is empty.")
        if config.HAS_TRANSIT and routes_gdf is not None and len(routes_gdf) == 0:
            print_warning("Bus Routes dataset is empty.")
        if config.HAS_SEZ and sez_gdf is not None and len(sez_gdf) == 0:
            print_warning("SEZ dataset is empty.")
        print_success("Schema validation complete.")


def save_processed_wards(wards_gdf: gpd.GeoDataFrame) -> str:
    """Save processed zone data (without geometry) to CSV for inspection."""
    with log_process(f"Saving processed {config.GEO_UNIT_LABEL}s"):
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)
        out = wards_gdf.drop(columns=['geometry'], errors='ignore').copy()
        out.to_csv(config.WARDS_PROCESSED, index=False)
        print_success(f"Processed {config.GEO_UNIT_LABEL}s → [highlight]{os.path.basename(config.WARDS_PROCESSED)}[/] ({len(out)} zones)")
        return config.WARDS_PROCESSED


def save_processed_transit(transit_df: pd.DataFrame) -> str:
    """Save processed transit scores to CSV."""
    with log_process("Saving processed transit data"):
        os.makedirs(config.PROCESSED_DIR, exist_ok=True)
        transit_df.to_csv(config.TRANSIT_PROCESSED, index=False)
        print_success(f"Processed transit → [highlight]{os.path.basename(config.TRANSIT_PROCESSED)}[/] ({len(transit_df)} zones)")
        return config.TRANSIT_PROCESSED
