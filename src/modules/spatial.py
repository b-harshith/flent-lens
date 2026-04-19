"""
Flent Lens 2.0 — Spatial Operations (H3 Hexagonal Grid)
Replaces all ward/pincode boundary logic with mathematical H3 tessellation.
"""
import h3
import numpy as np
import pandas as pd
import geopandas as gpd
from shapely.geometry import Polygon
import config
from src.utils.logger import print_info, print_detail, print_warning, log_process


def assign_to_h3(listings_gdf: gpd.GeoDataFrame, resolution: int = None) -> gpd.GeoDataFrame:
    """Assign every listing to an H3 hexagonal cell based on its lat/lon."""
    res = resolution or config.H3_RESOLUTION
    with log_process(f"Assigning listings to H3 hexagons (resolution {res})"):
        listings_gdf = listings_gdf.copy()
        listings_gdf['hex_id'] = listings_gdf.apply(
            lambda r: h3.latlng_to_cell(r['latitude'], r['longitude'], res), axis=1
        )
        n_hexes = listings_gdf['hex_id'].nunique()
        print_detail(f"Mapped {len(listings_gdf):,} listings → {n_hexes:,} unique hexagons")
        return listings_gdf


def generate_h3_grid(listings_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Build a GeoDataFrame of hexagonal polygon geometries
    for every active hex (containing ≥1 listing).
    This replaces wards_gdf entirely.
    """
    with log_process("Generating H3 hexagonal grid polygons"):
        active_hexes = listings_gdf['hex_id'].unique()

        records = []
        for hex_id in active_hexes:
            # h3.cell_to_boundary returns list of (lat, lon) tuples
            boundary = h3.cell_to_boundary(hex_id)
            # Convert (lat, lon) → (lon, lat) for Shapely
            polygon = Polygon([(lon, lat) for lat, lon in boundary])
            # Centroid
            center = h3.cell_to_latlng(hex_id)
            records.append({
                'hex_id': hex_id,
                'centroid_lat': center[0],
                'centroid_lon': center[1],
                'geometry': polygon,
            })

        hexes_gdf = gpd.GeoDataFrame(records, crs=config.CRS_GEOGRAPHIC)

        # Compute area in sq km using projected CRS
        hexes_proj = hexes_gdf.to_crs(config.CRS_PROJECTED)
        hexes_gdf['area_sqkm'] = hexes_proj.geometry.area / 1e6

        print_info(f"Generated [highlight]{len(hexes_gdf)}[/highlight] hex polygons "
                   f"(avg area: {hexes_gdf['area_sqkm'].mean():.2f} km²)")
        return hexes_gdf


def get_hex_neighbors(hex_id: str, k: int = 1) -> list:
    """Return the list of hex IDs within k rings of the given hex (excluding self)."""
    disk = set(h3.grid_disk(hex_id, k))
    disk.discard(hex_id)
    return list(disk)


def compute_maup_stability(listings_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    """
    Run MAUP sensitivity test across multiple H3 resolutions.
    For each hex at the default resolution, compute the median 1BHK rent
    at adjacent resolutions and measure stability.

    Returns a DataFrame with hex_id and stability_score.
    """
    with log_process("MAUP Sensitivity Testing"):
        resolutions = config.H3_SENSITIVITY_RES
        default_res = config.H3_RESOLUTION

        # Only compute for hexes that have 1BHK listings
        bhk1 = listings_gdf[listings_gdf['bhk_type'] == 1].copy()
        if len(bhk1) == 0:
            print_warning("No 1BHK listings — skipping MAUP sensitivity.")
            return pd.DataFrame(columns=['hex_id', 'stability_score'])

        # Compute median rent at each resolution
        rent_by_res = {}
        for res in resolutions:
            bhk1_res = bhk1.copy()
            bhk1_res['hex_temp'] = bhk1_res.apply(
                lambda r: h3.latlng_to_cell(r['latitude'], r['longitude'], res), axis=1
            )
            medians = bhk1_res.groupby('hex_temp')['monthly_rent'].median()
            rent_by_res[res] = medians

        # For each hex at default resolution, find its parent/child at other resolutions
        # and compare the median rent
        default_hexes = bhk1.groupby('hex_id')['monthly_rent'].median()
        stability_records = []

        for hex_id, default_rent in default_hexes.items():
            rents_across = [default_rent]
            center = h3.cell_to_latlng(hex_id)

            for res in resolutions:
                if res == default_res:
                    continue
                mapped_hex = h3.latlng_to_cell(center[0], center[1], res)
                if mapped_hex in rent_by_res[res].index:
                    rents_across.append(rent_by_res[res][mapped_hex])

            if len(rents_across) >= 2:
                arr = np.array(rents_across)
                median_val = np.median(arr)
                mad = np.median(np.abs(arr - median_val))
                stability = 1 - (mad / median_val) if median_val > 0 else 0
            else:
                stability = 1.0  # Only one resolution had data

            stability_records.append({
                'hex_id': hex_id,
                'stability_score': round(max(0, min(1, stability)), 3)
            })

        stability_df = pd.DataFrame(stability_records)
        avg_stability = stability_df['stability_score'].mean()
        low_stability = (stability_df['stability_score'] < config.STABILITY_THRESHOLD).sum()
        print_detail(f"Avg stability: {avg_stability:.3f} | "
                     f"{low_stability} hexes below {config.STABILITY_THRESHOLD} threshold")
        return stability_df
