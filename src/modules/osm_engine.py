"""
Flent Lens 2.0 — OSM Engine (OpenStreetMap Data Automation)
Fetches transit, employment, and lifestyle POIs via osmnx.
Computes reverse geocoding with area-weighted modal naming.
All results cached to disk.
"""
import os, json, time
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point
import config
from src.utils.logger import print_info, print_detail, print_warning, print_success, log_process

# OSM tag definitions
OSM_TAGS = {
    'bus_stops':      {'highway': 'bus_stop'},
    'metro_stations': {'railway': 'station'},
    'offices':        {'office': True},
    'commercial':     {'landuse': 'commercial'},
    'cafes':          {'amenity': 'cafe'},
    'supermarkets':   {'shop': 'supermarket'},
    'gyms':           {'leisure': 'fitness_centre'},
}

def _haversine(coord1, coord2):
    """Haversine distance in km between (lat, lon) tuples."""
    lat1, lon1 = np.radians(coord1)
    lat2, lon2 = np.radians(coord2)
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = np.sin(dlat / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


def _cache_path(city_key):
    return os.path.join(config.PROCESSED_DIR, 'osm_cache.json')

def _cache_meta_path(city_key):
    return os.path.join(config.PROCESSED_DIR, 'osm_cache_meta.json')

def _is_cache_fresh(city_key):
    meta_path = _cache_meta_path(city_key)
    if not os.path.exists(meta_path):
        return False
    with open(meta_path) as f:
        meta = json.load(f)
    fetched = datetime.fromisoformat(meta['fetched_at'])
    return (datetime.now() - fetched) < timedelta(days=config.OSM_CACHE_DAYS)


def fetch_osm_pois(city_key=None):
    """Fetch POIs natively using Master CSV or fallback to active city's OSM fetch."""
    city_key = city_key or config.CITY_KEY
    
    # 1. High Velocity Master CSV Override
    master_csv = os.path.join('data', 'processed', 'master_osm_pois.csv')
    if os.path.exists(master_csv):
        print_detail("Instantly compiling inference from Master OSM Database")
        try:
            df = pd.read_csv(master_csv)
            city_data = df[df['city'] == city_key]
            
            out_dict = {cat: [] for cat in OSM_TAGS.keys()}
            for _, row in city_data.iterrows():
                cat = row['category']
                if cat in out_dict:
                    out_dict[cat].append({
                        'lat': float(row['lat']),
                        'lon': float(row['lon']),
                        'name': str(row.get('name', '')),
                        'type': cat
                    })
            if any(len(v) > 0 for v in out_dict.values()):
                return out_dict
        except Exception as e:
            print_warning(f"Master CSV load logic corrupted: {e}. Falling back...")
            
    cache = _cache_path(city_key)
    os.makedirs(os.path.dirname(cache), exist_ok=True)

    if _is_cache_fresh(city_key) and os.path.exists(cache):
        print_detail("Using cached OSM fallback data")
        with open(cache) as f:
            cached = json.load(f)
        return cached

    with log_process("Fetching POIs from OpenStreetMap"):
        try:
            import osmnx as ox
        except ImportError:
            print_warning("osmnx not installed — skipping OSM data")
            return {}

        bb = config.BOUNDING_BOX
        north, south = bb['lat'][1], bb['lat'][0]
        east, west = bb['lon'][1], bb['lon'][0]

        def _fetch_one(name, tags):
            try:
                gdf = ox.features_from_bbox(bbox=(west, south, east, north), tags=tags)
                points = []
                for _, row in gdf.iterrows():
                    geom = row.geometry
                    if geom is None: continue
                    c = geom.centroid
                    poi_name = str(row.get('name', '')).strip()
                    points.append({'lat': c.y, 'lon': c.x, 'type': name, 'name': poi_name})
                return name, points
            except Exception as e:
                return name, []

        # Parallel fetch — all 7 tag queries at once
        from concurrent.futures import ThreadPoolExecutor, as_completed
        results = {}
        with ThreadPoolExecutor(max_workers=7) as pool:
            futures = {pool.submit(_fetch_one, n, t): n for n, t in OSM_TAGS.items()}
            for future in as_completed(futures):
                name, points = future.result()
                results[name] = points
                print_detail(f"  {name}: {len(points)} features")

        # Save cache
        with open(cache, 'w') as f:
            json.dump(results, f)
        with open(_cache_meta_path(city_key), 'w') as f:
            json.dump({'fetched_at': datetime.now().isoformat(),
                       'bbox': [south, north, west, east]}, f)
        print_success("OSM data cached")
        return results


def compute_hex_poi_scores(hex_df, osm_data):
    """Compute transit, employment, and lifestyle scores per hex from OSM POIs + Nearest Landmarks."""
    with log_process("Computing OSM overlay scores and resolving nearest landmarks"):
        if not osm_data:
            hex_df['transit_score'] = 0
            hex_df['employment_score'] = 0
            hex_df['lifestyle_score'] = 0
            hex_df['osm_confidence'] = 0
            hex_df['nearest_transit'] = pd.Series([None] * len(hex_df), dtype=object)
            hex_df['nearest_office'] = pd.Series([None] * len(hex_df), dtype=object)
            hex_df['nearest_lifestyle'] = pd.Series([None] * len(hex_df), dtype=object)
            return hex_df

        # Group raw dictionaries to carry names 
        bus_raw = osm_data.get('bus_stops', [])
        metro_raw = osm_data.get('metro_stations', [])
        transit_raw = metro_raw if len(metro_raw) > 0 else bus_raw
        
        office_raw = osm_data.get('offices', []) + osm_data.get('commercial', [])
        life_raw = osm_data.get('cafes', []) + osm_data.get('supermarkets', []) + osm_data.get('gyms', [])

        bus_pts = np.array([[p['lat'], p['lon']] for p in bus_raw])
        metro_pts = np.array([[p['lat'], p['lon']] for p in metro_raw])
        office_pts = np.array([[p['lat'], p['lon']] for p in office_raw])
        life_pts = np.array([[p['lat'], p['lon']] for p in life_raw])

        # Feature Scoring + Landmark resolution
        raw_metro_gravity, raw_bus_gravity, raw_emp_gravity, raw_life_gravity = [], [], [], []
        nearest_transits, nearest_offices, nearest_lifestyles = [], [], []

        for _, row in hex_df.iterrows():
            clat, clon = row['centroid_lat'], row['centroid_lon']

            # Transit Gravity
            m_grav = 0.0
            for pt in metro_pts:
                dist = _haversine((clat, clon), (pt[0], pt[1]))
                if dist < 5.0: m_grav += 1.0 / (1.0 + (dist ** 1.2))
            raw_metro_gravity.append(m_grav)
            
            b_grav = 0.0
            for pt in bus_pts:
                dist = _haversine((clat, clon), (pt[0], pt[1]))
                if dist < 2.0: b_grav += 1.0 / (1.0 + (dist ** 2.0))
            raw_bus_gravity.append(b_grav)

            # Employment Gravity Score
            e_grav = 0.0
            for pt in office_pts:
                dist = _haversine((clat, clon), (pt[0], pt[1]))
                if dist < 8.0: e_grav += 1.0 / (1.0 + (dist / 1.5) ** 2.0)
            raw_emp_gravity.append(e_grav)

            # Lifestyle Gravity Score
            l_grav = 0.0
            for pt in life_pts:
                dist = _haversine((clat, clon), (pt[0], pt[1]))
                if dist < 2.5: l_grav += 1.0 / (1.0 + (dist ** 2.5))
            raw_life_gravity.append(l_grav)

            # Semantic Nearest Matcher
            def _find_closest_named(lat, lon, dict_list):
                best_dist, best_item = 999.0, None
                for pt in dict_list:
                    if not pt.get('name'): continue
                    d = np.sqrt(((pt['lat']-lat)*111.32)**2 + ((pt['lon']-lon)*111.32*np.cos(np.radians(lat)))**2)
                    if d < best_dist:
                        best_dist, best_item = d, pt
                return (best_item['name'], round(best_dist, 1)) if best_item else (None, None)

            nearest_transits.append(_find_closest_named(clat, clon, transit_raw))
            nearest_offices.append(_find_closest_named(clat, clon, office_raw))
            nearest_lifestyles.append(_find_closest_named(clat, clon, life_raw))

        # Normalize Gravity Arrays Globally (0.0 - 1.0)
        def _norm(raw_list):
            arr = np.array(raw_list)
            m = arr.max() if len(arr) > 0 and arr.max() > 0 else 1.0
            return (arr / m).tolist()

        n_metro = _norm(raw_metro_gravity)
        n_bus = _norm(raw_bus_gravity)
        employment_scores = _norm(raw_emp_gravity)
        lifestyle_scores = _norm(raw_life_gravity)

        # Composite Transit Setup
        mw, bw = abs(config.TRANSIT_METRO_WEIGHT), abs(config.TRANSIT_BUS_WEIGHT)
        transit_scores = []
        for m, b in zip(n_metro, n_bus):
            transit_scores.append((m * mw + b * bw) / (mw + bw) if (mw + bw) > 0 else 0)

        hex_df['transit_score'] = transit_scores
        hex_df['employment_score'] = employment_scores
        hex_df['lifestyle_score'] = lifestyle_scores
        hex_df['nearest_transit'] = nearest_transits
        hex_df['nearest_office'] = nearest_offices
        hex_df['nearest_lifestyle'] = nearest_lifestyles

        # OSM confidence = density relative to Bangalore benchmark (~4 POIs/km²)
        total_pois = sum(len(v) for v in osm_data.values())
        city_area = hex_df['area_sqkm'].sum()
        density = total_pois / city_area if city_area > 0 else 0
        benchmark_density = 4.0  # Bangalore baseline (rough)
        osm_conf = min(density / benchmark_density, 1.0)
        hex_df['osm_confidence'] = round(osm_conf, 3)

        print_detail(f"OSM confidence: {osm_conf:.2f} (density={density:.1f}/km²)")
        return hex_df


def reverse_geocode_hexes(hex_df, admin_gdf=None):
    """Assign stable sequential IDs to hexes: [CITY_CODE]-[001, 002, ...]"""
    # Sort by ID to ensure naming is deterministic across runs.
    hex_df = hex_df.sort_values('hex_id').reset_index(drop=True)
    
    hex_df['hex_name'] = [
        f"{config.CITY_CODE}-{i+1:03d}" for i in range(len(hex_df))
    ]
    return hex_df


    # EOF
