import geopandas as gpd
import pandas as pd
import numpy as np
import config
from src.utils.logger import print_info, log_process

def compute_sez_score(wards_gdf: gpd.GeoDataFrame, sez_gdf: gpd.GeoDataFrame) -> pd.DataFrame:
    with log_process("Overlays: SEZ Employment Impact"):
        # Convert to projected for distance calculations
        wards_proj = wards_gdf.to_crs(config.CRS_PROJECTED)
        sez_proj = sez_gdf.to_crs(config.CRS_PROJECTED)
        
        # Compute Distance Matrix (Wards x SEZs)
        # We use ward centroids for simplified distance proxy
        ward_centroids = wards_proj.geometry.centroid
        
        sez_scores = []
        closest_sezs = []
        for _, ward_point in ward_centroids.items():
            # Distances from this ward to all SEZs
            dists = sez_proj.geometry.distance(ward_point).clip(lower=config.SEZ_MIN_DISTANCE_M)
            
            # Gravity Model: Sum(1 / distance^alpha)
            # Wards closer to more SEZs get higher scores
            score = np.sum(1 / (dists ** config.SEZ_DISTANCE_DECAY_ALPHA))
            sez_scores.append(score)
            
            # Fetch names and distances for top 3 closest SEZs
            closest_idx = np.argsort(dists.values)[:3]
            hub_strings = []
            for idx in closest_idx:
                hub_name = sez_gdf.iloc[idx].get('developer', f"SEZ Hub {idx}")
                # Tidy up corporate suffixes for clean UI display
                hub_name = str(hub_name).split(' (')[0].split(',')[0].replace(' Limited', '').replace(' Pvt', '').replace(' Ltd.', '').strip()
                dist_km = dists.iloc[idx] / 1000.0
                hub_strings.append(f"<div style='color:#4e342e; font-size: 12px; margin-bottom: 2px;'>• {hub_name} <span style='color:#8d6e63;'>({dist_km:.1f} km)</span></div>")
            closest_sezs.append("".join(hub_strings))
            
        # Scale to 0-100 index for readability (otherwise values are ~0.0000x)
        max_score = np.max(sez_scores) if len(sez_scores) > 0 else 0
        if max_score > 0:
            sez_scores = [ (s / max_score) * 100 for s in sez_scores ]
            
        rez_df = pd.DataFrame({
            'ward_id': wards_gdf['ward_id'],
            'sez_employment_score': sez_scores,
            'closest_sezs': closest_sezs
        })

        return rez_df
