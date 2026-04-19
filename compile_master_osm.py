import json
import os
import pandas as pd
from city_config import CITY_PROFILES

def compile_master_osm():
    print("Gathering OSM JSON caches across all cities...")
    master_records = []
    data_dir = 'data'
    
    for city_key in CITY_PROFILES.keys():
        # Using Flent Lens 2.0 conventional folder structure
        cache_path = os.path.join(data_dir, 'processed', city_key, 'osm_cache.json')
        if not os.path.exists(cache_path):
            print(f"  [Skipped] {city_key.upper()} - No cache file found.")
            continue
            
        try:
            with open(cache_path, 'r', encoding='utf-8') as f:
                city_data = json.load(f)
                
            count = 0
            for category, items in city_data.items():
                for item in items:
                    master_records.append({
                        'city': city_key,
                        'category': category,
                        'name': item.get('name', ''),
                        'lat': item.get('lat'),
                        'lon': item.get('lon')
                    })
                    count += 1
            print(f"  [Added] {city_key.upper()} - {count} records extracted.")
        except Exception as e:
            print(f"  [Error] {city_key.upper()} - Failed to read ({e})")
            
    if not master_records:
        print("No valid caches found. Please run the pipeline for at least one city first.")
        return
        
    df = pd.DataFrame(master_records)
    out_dir = os.path.join(data_dir, 'processed')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'master_osm_pois.csv')
    
    df.to_csv(out_path, index=False)
    print(f"\nSuccessfully compiled {len(df)} POIs into -> {out_path}")

if __name__ == "__main__":
    compile_master_osm()
