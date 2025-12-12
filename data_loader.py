"""
This file is the factory assembly line. It processing the given files with their different values,
clean them, translate them and tags them.
It will return a single perfectly uniform pandas dataframe ready for analysi
"""


import pandas as pd
import glob
import os
import re
import calendar
from typing import Optional, Tuple
import config  # We use the config file we just created

# Constants for column standardization
REQUIRED_COLUMNS = ['Date', 'Year', 'Month', 'Month_Num', 'Desc', 'Category', 'Amount', 'Source_Type']

def load_data_folder(folder_path: str) -> pd.DataFrame:
    """
    Scans a folder for CSV/XLSX files, processes them, and returns
    a single merged Master DataFrame.
    """
    if not os.path.exists(folder_path):
        print(f"Error: Folder {folder_path} not found.")
        # Return empty dataframe with the given column names
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    # Use glob to find every .csv and .xlsx file in the folder
    all_files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True) + \
                glob.glob(os.path.join(folder_path, "**", "*.xlsx"), recursive=True)
    
    df_list = []
    
    for file_path in all_files:
        try:
            # 1. Parse Metadata from Filename
            filename = os.path.basename(file_path).lower()

            # Extract the date data from the file name
            year, month_name, month_num = _parse_filename_date(filename)
            
            # Determine source type based on filename conventions
            source_type = 'credit_card' if '_maxit' in filename or 'card' in filename else 'bank'

            # 2. Read the Raw File
            raw_df = _read_smart(file_path)
            if raw_df is None or raw_df.empty:
                continue

            # 3. Normalize to Standard Schema
            clean_df = _normalize_data(raw_df, source_type)
            
            if not clean_df.empty:
                # Add Metadata columns
                clean_df['Year'] = year or clean_df['Date'].dt.year.astype(str)
                clean_df['Month'] = month_name or clean_df['Date'].dt.month_name()
                clean_df['Month_Num'] = month_num or clean_df['Date'].dt.month
                clean_df['Source_Type'] = source_type
                
                df_list.append(clean_df)
                
        except Exception as e:
            print(f"Failed to load {file_path}: {e}")
            continue

    if not df_list:
        return pd.DataFrame(columns=REQUIRED_COLUMNS)

    # Combine and Sort
    master_df = pd.concat(df_list, ignore_index=True)
    master_df.sort_values(by='Date', ascending=False, inplace=True)
    
    return master_df

# --- INTERNAL HELPER FUNCTIONS ---

def _parse_filename_date(filename: str) -> Tuple[Optional[str], Optional[str], Optional[int]]:
    """Extracts Year and Month from filenames like '1_january_2024.csv'."""
    try:
        # Find Year (2020-2039)
        year_match = re.search(r'20[2-3]\d', filename)
        year = year_match.group(0) if year_match else None

        # Find Month
        month_name = None
        month_num = None

        # Iterate through a list of english month names
        for m_name in calendar.month_name[1:]:
            if m_name.lower() in filename:
                month_name = m_name
                month_num = list(calendar.month_name).index(m_name)
                break
        
        return year, month_name, month_num
    except:
        return None, None, None

def _read_smart(file_path: str) -> Optional[pd.DataFrame]:
    """
    Smartly reads CSV or Excel. Detects header row automatically.
    """
    is_excel = file_path.endswith(('.xlsx', '.xls'))
    
    try:
        # Step A: Read first 20 lines to find the Header Row
        if is_excel:
            preview = pd.read_excel(file_path, header=None, nrows=20)
        else:
            # Try different encodings for Hebrew support
            preview = None
            for enc in ['utf-8', 'cp1255', 'windows-1255', 'utf-8-sig']:
                try:
                    preview = pd.read_csv(file_path, header=None, nrows=20, encoding=enc)
                    break
                except: continue
        
        if preview is None: return None

        # Find the row index that contains common column names
        header_idx = -1
        target_keywords = ['תאריך', 'Date', 'שם בית עסק', 'Description', 'פרטים']
        
        # Search for the column names in the first 20 rows
        for i, row in preview.iterrows():
            row_str = row.astype(str).str.cat(sep=' ')
            if any(k in row_str for k in target_keywords):
                header_idx = i
                break
        
        if header_idx == -1: return None # Could not find a valid header

        # Step B: Read the full file using the found header index
        if is_excel:
            df = pd.read_excel(file_path, header=header_idx)
        else:
            for enc in ['utf-8', 'cp1255', 'windows-1255', 'utf-8-sig']:
                try:
                    df = pd.read_csv(file_path, header=header_idx, encoding=enc)
                    break
                except: continue
        
        # Clean column names (strip whitespace, newlines)
        df.columns = df.columns.astype(str).str.strip().str.replace("\n", " ")
        return df

    except Exception:
        return None

def _get_category(desc: str) -> str:
    """Classifies a transaction based on config.CATEGORY_RULES"""
    desc = str(desc).upper()
    for cat, keywords in config.CATEGORY_RULES.items():
        if any(k in desc for k in keywords):
            return cat
    return 'Other'

def _normalize_data(df: pd.DataFrame, source_type: str) -> pd.DataFrame:
    """
    Maps raw columns (Hebrew/English) to standard columns: Date, Desc, Amount, Category.
    Since a bank and credit card files can look different, it forces them to speak the same language
    """
    norm = pd.DataFrame()
    
    # Identify Columns using keyword matching
    cols = df.columns
    date_col = next((c for c in cols if 'תאריך' in c or 'Date' in c), None)
    
    if not date_col: return pd.DataFrame() # Garbage file

    norm['Date'] = pd.to_datetime(df[date_col], dayfirst=True, errors='coerce')
    norm.dropna(subset=['Date'], inplace=True)

    # --- BANK LOGIC ---
    if source_type == 'bank':
        desc_col = next((c for c in cols if 'פרטים' in c or 'Desc' in c), None)
        credit_col = next((c for c in cols if 'זכות' in c or 'Credit' in c), None)
        debit_col = next((c for c in cols if 'חובה' in c or 'Debit' in c), None)
        
        norm['Desc'] = df[desc_col].fillna('') if desc_col else "Unknown"
        
        # Calculate Net Amount
        credit = pd.to_numeric(df[credit_col], errors='coerce').fillna(0) if credit_col else 0
        debit = pd.to_numeric(df[debit_col], errors='coerce').fillna(0) if debit_col else 0
        norm['Amount'] = credit - debit

    # --- CREDIT CARD LOGIC ---
    elif source_type == 'credit_card':
        desc_col = next((c for c in cols if 'שם בית' in c or 'Name' in c or 'עסק' in c), None)
        amount_col = next((c for c in cols if 'סכום' in c and ('חיוב' in c or 'Amount' in c)), None)
        
        norm['Desc'] = df[desc_col].fillna('') if desc_col else "Unknown"
        
        if amount_col:
            # Credit cards are usually positive numbers representing debt, so we flip to negative
            raw_amount = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
            norm['Amount'] = raw_amount * -1
        else:
            norm['Amount'] = 0

    # Apply Category Classification
    norm['Category'] = norm['Desc'].apply(_get_category)

    return norm