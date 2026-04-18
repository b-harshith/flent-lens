import pandas as pd
import re
import os
import config
from src.utils.logger import console, print_success, print_error, print_info, log_process

def clean_data(input_path=config.RAW_LISTINGS_CSV, output_path=config.LISTINGS_CSV):
    with log_process("Magicbricks Data Cleaning"):
        if not os.path.exists(input_path):
            print_error(f"Raw data not found at {input_path}")
            return
            
        print_info(f"Loading raw data from [highlight]{os.path.basename(input_path)}[/highlight]...")
        df = pd.read_csv(input_path)
        initial_count = len(df)
        
        # 1. Filter property type
        valid_types = ['Apartment', 'Multistorey Apartment', 'Builder Floor Apartment', 'Penthouse', 'Studio Apartment']
        df = df[df['property_type'].isin(valid_types)].copy()
        print_info(f"Property type filter: [highlight]{initial_count}[/highlight] -> [highlight]{len(df)}[/highlight]")

        # 2. Add listing_type column (may already exist for some cities)
        if 'listing_type' not in df.columns:
            df['listing_type'] = 'rent'
        else:
            df['listing_type'] = df['listing_type'].fillna('rent')

        # 3. Extract BHK count
        def extract_bhk(row):
            if pd.notna(row['bhk_type']) and str(row['bhk_type']).strip():
                match = re.search(r'(\d+)', str(row['bhk_type']))
                if match: return int(match.group(1))
            
            url = str(row['listing_url'])
            match = re.search(r'(\d+)-BHK', url, re.IGNORECASE)
            if match: return int(match.group(1))
            
            bio = str(row['apartment_bio'])
            match = re.search(r'(\d+)\s*BHK', bio, re.IGNORECASE)
            if match: return int(match.group(1))
            
            if 'Studio' in str(row['property_type']) or 'Studio' in bio:
                return 1
            return None

        print_info("Recovering missing BHK data using regex heuristics...")
        df['bhk_type'] = df.apply(extract_bhk, axis=1)

        # 4. Clean numeric fields
        df['monthly_rent'] = pd.to_numeric(df['monthly_rent'], errors='coerce')
        df['sqft'] = pd.to_numeric(df['sqft'], errors='coerce')
        df['latitude'] = pd.to_numeric(df['latitude'], errors='coerce')
        df['longitude'] = pd.to_numeric(df['longitude'], errors='coerce')

        # 5. Drop rows with missing critical data
        df = df.dropna(subset=['latitude', 'longitude', 'monthly_rent', 'bhk_type'])
        
        # Final type enforcement
        df['bhk_type'] = df['bhk_type'].astype(int)

        # 6. Apply statistical sanity caps to prevent margin blowups
        if hasattr(config, 'MAX_VALID_1BHK_RENT'):
            mask_anomaly = (df['bhk_type'] == 1) & (df['monthly_rent'] > config.MAX_VALID_1BHK_RENT)
            dropped = mask_anomaly.sum()
            if dropped > 0:
                print_info(f"Dropped {dropped} fake 1BHK listings exceeding ₹{config.MAX_VALID_1BHK_RENT}")
            df = df[~mask_anomaly]

        # 7. Deduplicate
        df = df.drop_duplicates(subset=['listing_id'])
        df = df.drop_duplicates(subset=['listing_url'])
        
        print_info(f"Final valid listings: [success]{len(df)}[/success]")

        # Save to output
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        df.to_csv(output_path, index=False)
        print_success(f"Cleaned data saved to [highlight]{os.path.basename(output_path)}[/highlight]")

if __name__ == "__main__":
    clean_data()
