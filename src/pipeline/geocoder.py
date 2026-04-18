import csv
import re
import time
import os
import config
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut
from src.utils.logger import console, print_success, print_error, print_info, log_process, progress_bar

def geocode_sez(input_path=config.RAW_SEZ_CSV, output_path=config.SEZ_CSV):
    with log_process("SEZ Geocoding"):
        if not os.path.exists(input_path):
            print_error(f"Raw SEZ list not found at {input_path}")
            return

        sez_list = []
        with open(input_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                sez_list.append({
                    'developer': row.get('Name of the Developer', '').strip(),
                    'location': row.get('Location', '').strip(),
                    'type': row.get('Type of SEZ', '').strip()
                })

        geolocator = Nominatim(user_agent="bba_flent_spatial_analysis_v2")
        results = []
        
        print_info(f"Geocoding [highlight]{len(sez_list)}[/highlight] SEZ locations...")
        
        with progress_bar() as progress:
            task = progress.add_task("[cyan]Connecting to Maps API...", total=len(sez_list))
            
            for sez in sez_list:
                dev = sez['developer']
                loc = sez['location']
                
                clean_dev = dev.replace('Pvt. Ltd.', '').replace('Private Limited', '').replace('Limited', '').replace('LLP', '').replace('Ltd.', '')
                clean_dev = re.sub(r'\(.*?\)', '', clean_dev).strip()
                
                clean_loc_parts = loc.split(',')
                clean_loc_primary = clean_loc_parts[0].strip()
                clean_loc_secondary = clean_loc_parts[1].strip() if len(clean_loc_parts) > 1 else clean_loc_primary
                
                queries = [
                    f"{clean_dev}, {clean_loc_primary}, Bangalore",
                    f"{clean_loc_primary}, Bangalore",
                    f"{clean_dev}, {clean_loc_secondary}, Bangalore",
                    f"{clean_loc_secondary}, Bangalore"
                ]
                
                location = None
                for query in queries:
                    try:
                        time.sleep(0.5) # Reduced delay for efficiency during bulk runs
                        location = geolocator.geocode(query, timeout=10)
                        if location: break
                    except GeocoderTimedOut:
                        continue
                        
                if location:
                    sez['latitude'] = location.latitude
                    sez['longitude'] = location.longitude
                    sez['matched_address'] = location.address
                else:
                    sez['latitude'] = ''
                    sez['longitude'] = ''
                    sez['matched_address'] = 'Not Found'
                    
                results.append(sez)
                progress.update(task, advance=1, description=f"[cyan]Resolved: {clean_dev[:20]}...")

        # Export
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        fieldnames = ['developer', 'location', 'type', 'latitude', 'longitude', 'matched_address']
        with open(output_path, mode='w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(results)
            
        print_success(f"Geocoding complete! Results saved to [highlight]{os.path.basename(output_path)}[/highlight]")

if __name__ == "__main__":
    geocode_sez()
