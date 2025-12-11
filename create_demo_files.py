import pandas as pd
import numpy as np
import os
import calendar
import random
from datetime import datetime, timedelta

# --- CONFIGURATION ---
OUTPUT_DIR = "demo_data"
YEARS = [2024, 2025]

# --- MERCHANTS & CATEGORIES ---
# Using names that work with the dashboard's translation logic
MERCHANTS = {
    'Groceries': ['Super Yuda', 'Shufersal', 'Rami Levy', 'Victory', 'AM:PM', 'Mega', 'Tiv Taam'],
    'Restaurants': ['Aroma', 'McDonalds', 'Dominos Pizza', 'Golda', 'Arcaffe', 'Benedict', 'Giraffe', 'Wolt'],
    'Transport': ['Pango', 'Paz Fuel', 'Delek', 'Train Israel', 'Lime Scooters', 'Moovit', 'Hot Mobile'],
    'Shopping': ['Zara', 'H&M', 'Super Pharm', 'Fox', 'Terminal X', 'KSP', 'Ivory', 'Amazon', 'AliExpress'],
    'Entertainment': ['Netflix', 'Spotify', 'Cinema City', 'Steam', 'Playstation'],
    'Utilities': ['Electric Co', 'Water Bill', 'Arnona TLV', 'Bezeq'],
    'Income': ['Salary - Tech Corp', 'Salary - Freelance', 'Bit Transfer', 'Refund']
}

def ensure_dir(directory):
    if not os.path.exists(directory):
        os.makedirs(directory)

def random_date(year, month):
    # Get random day in month
    num_days = calendar.monthrange(year, month)[1]
    day = random.randint(1, num_days)
    return datetime(year, month, day).strftime("%d-%m-%Y") # Israel format

def generate_cc_file(year, month, file_path):
    # Generate 15-30 transactions
    num_tx = random.randint(15, 30)
    data = []
    
    for _ in range(num_tx):
        cat = random.choice(list(MERCHANTS.keys()))
        if cat == 'Income': continue # CC is expense only usually
        
        merchant = random.choice(MERCHANTS[cat])
        amount = round(random.uniform(50, 600), 2)
        date = random_date(year, month)
        
        # MaxIt Structure: תאריך עסקה, שם בית העסק, קטגוריה, סכום חיוב, הערות
        data.append([date, merchant, cat, amount, ""])

    df = pd.DataFrame(data, columns=['תאריך עסקה', 'שם בית העסק', 'קטגוריה', 'סכום חיוב', 'הערות'])
    # Save as CSV with utf-8-sig for Hebrew support
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def generate_bank_file(year, month, file_path):
    data = []
    
    # 1. Salary (Income)
    date = f"10-{month:02d}-{year}"
    data.append([date, "משכורת", random.choice([18000, 19500, 21000]), 0, "העברה", "משכורת ממעסיק"])
    
    # 2. Mortgage (Expense)
    date = f"15-{month:02d}-{year}"
    data.append([date, "משכנתא", 0, 4500, "הוראת קבע", "משכנתא"])
    
    # 3. Credit Card Payment (Expense)
    date = f"02-{month:02d}-{year}"
    cc_total = random.randint(3000, 6000)
    data.append([date, "כרטיסי אשראי", 0, cc_total, "הרשאה לחיוב", "מקס איט"])
    
    # 4. Utilities
    for util in ['Electric Co', 'Water Bill', 'Arnona TLV']:
        if random.random() > 0.5: # Not every month
            date = random_date(year, month)
            amount = random.randint(200, 800)
            data.append([date, util, 0, amount, "הוראת קבע", "חשבונות"])

    # Columns: תאריך, פרטים, זכות, חובה, הפעולה, פרטים נוספים
    df = pd.DataFrame(data, columns=['תאריך', 'פרטים', 'זכות', 'חובה', 'הפעולה', 'פרטים נוספים'])
    df.to_csv(file_path, index=False, encoding='utf-8-sig')

def main():
    # 1. Create main Data folder
    ensure_dir(OUTPUT_DIR)
    print(f"Generating demo data in '{OUTPUT_DIR}'...")
    
    for year in YEARS:
        # 2. Create Year Folder (e.g., demo_data/2024)
        year_folder = os.path.join(OUTPUT_DIR, str(year))
        ensure_dir(year_folder)
        
        for month in range(1, 13):
            month_name = calendar.month_name[month].lower()
            
            # 3. Generate Credit Card (_maxit style) inside the year folder
            # Naming format: 1_january_2024_maxit.csv
            cc_filename = f"{month}_{month_name}_{year}_maxit.csv"
            cc_path = os.path.join(year_folder, cc_filename)
            generate_cc_file(year, month, cc_path)
            
            # 4. Generate Bank file inside the year folder
            # Naming format: 1_january_2024.csv
            bank_filename = f"{month}_{month_name}_{year}.csv"
            bank_path = os.path.join(year_folder, bank_filename)
            generate_bank_file(year, month, bank_path)
            
    print(f"Done! Created data for years: {YEARS}")

if __name__ == "__main__":
    main()