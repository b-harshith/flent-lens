"""
Flent Lens — Spatial Operations
Ward area computation, listing-to-ward joins (with proximity fallback),
and transit intersection.
"""
import geopandas as gpd
import pandas as pd
import numpy as np
import config
from src.utils.logger import print_info, print_detail, print_warning, log_process

def compute_ward_areas(wards_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    with log_process("Computing ward areas (UTM projection)"):
        wards_gdf = wards_gdf.to_crs(config.CRS_PROJECTED)
        wards_gdf['area_sqkm'] = wards_gdf.geometry.area / 10**6
        wards_gdf = wards_gdf.to_crs(config.CRS_GEOGRAPHIC)
        print_detail(f"Area range: {wards_gdf['area_sqkm'].min():.2f} — {wards_gdf['area_sqkm'].max():.2f} km²")
        return wards_gdf

def assign_listings_to_wards(listings_gdf: gpd.GeoDataFrame, wards_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    with log_process("Spatial join: mapping listings → wards"):
        # ── Step 1: Standard point-in-polygon spatial join ──
        joined = gpd.sjoin(listings_gdf, wards_gdf[['ward_id', 'geometry']], how='left', predicate='within')

        # geopandas 1.0+: overlapping column names get _left/_right suffixes
        if 'ward_id_right' in joined.columns:
            joined = joined.rename(columns={'ward_id_right': 'ward_id'})
        if 'ward_id_left' in joined.columns:
            joined = joined.drop(columns=['ward_id_left'])

        # Drop the sjoin helper index column
        joined = joined.drop(columns=['index_right'], errors='ignore')

        mapped   = joined['ward_id'].notna().sum()
        unmapped = joined['ward_id'].isna().sum()
        print_detail(f"Point-in-polygon: {mapped:,} mapped | {unmapped:,} outside {config.GEO_UNIT_LABEL} boundaries")

        # ── Step 2: Proximity fallback for unmapped listings ──
        if unmapped > 0:
            print_detail(f"Running proximity assignment for {unmapped:,} unmapped listings (max {config.NEAREST_WARD_MAX_DISTANCE_M}m)...")
            
            unmapped_mask = joined['ward_id'].isna()
            unmapped_gdf = joined[unmapped_mask].copy()

            # Project both to UTM for accurate distance calculation
            unmapped_proj = unmapped_gdf.to_crs(config.CRS_PROJECTED)
            wards_proj = wards_gdf[['ward_id', 'geometry']].to_crs(config.CRS_PROJECTED)

            # Ensure wards_proj has no invalid or empty geometries (redundant but safe)
            wards_proj = wards_proj[~wards_proj.geometry.is_empty & wards_proj.geometry.notna() & wards_proj.geometry.is_valid]

            # For each unmapped listing, find nearest ward boundary
            nearest_ward_ids = []
            nearest_dists = []

            for idx, listing_point in unmapped_proj.geometry.items():
                if listing_point is None or listing_point.is_empty:
                    nearest_ward_ids.append(None)
                    nearest_dists.append(np.inf)
                    continue

                # Compute distance from this point to every ward polygon boundary
                distances = wards_proj.geometry.distance(listing_point)
                
                if distances.isna().all():
                    nearest_ward_ids.append(None)
                    nearest_dists.append(np.inf)
                else:
                    min_idx = distances.idxmin()
                    min_dist = distances[min_idx]

                    if min_dist <= config.NEAREST_WARD_MAX_DISTANCE_M:
                        nearest_ward_ids.append(wards_proj.loc[min_idx, 'ward_id'])
                        nearest_dists.append(min_dist)
                    else:
                        nearest_ward_ids.append(None)
                        nearest_dists.append(min_dist)

            # Assign nearest ward IDs back
            proximity_series = pd.Series(nearest_ward_ids, index=unmapped_gdf.index)
            joined.loc[unmapped_mask, 'ward_id'] = proximity_series

            # Count results
            proximity_assigned = proximity_series.notna().sum()
            still_unmapped = proximity_series.isna().sum()
            
            if nearest_dists:
                assigned_dists = [d for d, w in zip(nearest_dists, nearest_ward_ids) if w is not None]
                if assigned_dists:
                    avg_dist = np.mean(assigned_dists)
                    max_dist = np.max(assigned_dists)
                    print_detail(f"Proximity assigned: {proximity_assigned:,} listings "
                                f"(avg dist: {avg_dist:.0f}m, max: {max_dist:.0f}m)")
            
            print_detail(f"Still unmapped (>{config.NEAREST_WARD_MAX_DISTANCE_M}m from any zone): {still_unmapped:,}")

        final_mapped = joined['ward_id'].notna().sum()
        final_unmapped = joined['ward_id'].isna().sum()
        print_detail(f"Final: {final_mapped:,} listings mapped | {final_unmapped:,} outside {config.GEO_UNIT_LABEL} boundaries")
        return joined

def clip_routes_to_wards(routes_gdf: gpd.GeoDataFrame, wards_gdf: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    with log_process("Intersecting transit routes with zone boundaries"):
        if routes_gdf is None or len(routes_gdf) == 0:
            print_detail("No transit routes to intersect — skipping.")
            return gpd.GeoDataFrame(columns=['ward_id', 'geometry'], crs=config.CRS_GEOGRAPHIC)
        # Use overlay (not clip) to retain ward_id on each segment
        clipped = gpd.overlay(routes_gdf, wards_gdf[['ward_id', 'geometry']], how='intersection')
        print_detail(f"{len(clipped):,} route segments within zone boundaries")
        return clipped
