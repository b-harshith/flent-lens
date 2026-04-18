import geopandas as gpd
import pandas as pd
import config
from src.utils.logger import print_info, log_process

def compute_transit_score(wards_gdf: gpd.GeoDataFrame, routes_gdf: gpd.GeoDataFrame, clipped_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    with log_process("Overlays: Transit Connectivity"):
        # 1. Route Density (routes per sqkm)
        route_counts = clipped_gdf.groupby('ward_id').size().reset_index(name='route_count')
        
        # 2. Total Route Length in Ward
        clipped_gdf = clipped_gdf.to_crs(config.CRS_PROJECTED)
        clipped_gdf['length_m'] = clipped_gdf.geometry.length
        route_lengths = clipped_gdf.groupby('ward_id')['length_m'].sum().reset_index()
        
        # Join back to ward features
        transit_df = wards_gdf[['ward_id', 'area_sqkm']].merge(route_counts, on='ward_id', how='left').fillna(0)
        transit_df = transit_df.merge(route_lengths, on='ward_id', how='left').fillna(0)
        
        # Calculate Index
        transit_df['route_density'] = transit_df['route_count'] / transit_df['area_sqkm']
        transit_df['length_density'] = transit_df['length_m'] / (transit_df['area_sqkm'] * 1000)
        
        # Weighted Score
        transit_df['transit_score'] = (
            (transit_df['route_density'].rank(pct=True) * config.TRANSIT_WEIGHT_DENSITY) +
            (transit_df['length_density'].rank(pct=True) * config.TRANSIT_WEIGHT_LENGTH)
        )
        
        return transit_df[['ward_id', 'transit_score']]
