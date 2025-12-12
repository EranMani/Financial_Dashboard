import pandas as pd
import os


"""
When dealing with a new file, we do the following:
1) exploration - open the file without crashing to see what we are dealing with
    Action: Read the first 20 lines.
    Key Challenge: "Ragged" data (rows with different column counts) will crash Pandas.
    The Fix: Use names=range(20) to create dummy columns so Pandas accepts any row width.
    code example: pd.read_csv(path, header=None, nrows=20, encoding='utf-8', names=range(20))

2) navigation - find where the actual data table starts by ignoring metadata (logos, addresses)
    Action: Scan the preview rows for specific keywords (e.g., "Date", "Credit", "Description").
    Convert the row to a single string: row.astype(str).str.cat(sep=' ')
    Check for matches: if len([k for k in keywords if k in row_str]) >= 2:
    Outcome: You get header_idx (e.g., Row 5).

3) Extraction - Reload the entire file, but this time strictly as a table.
    Action: Read the file again using the found header_idx.
    header=header_idx: Skips the junk rows at the top automatically.
    sep=',': Forces Pandas to respect commas (crucial if regional settings are interfering).
    encoding='utf-8-sig': Handles standard web/app exports (or use cp1255 for old Hebrew Windows files).

4) Cleaning & Normalization - Convert "Text" into "Math" and "Time".
    Dates:
        Use pd.to_datetime(df['Date'], dayfirst=True, errors='coerce').
        dayfirst=True: Essential for non-US dates (DD/MM/YYYY).
        errors='coerce': Turns garbage (like "Total" rows) into NaT so they don't crash the script.
        Cleanup: df.dropna(subset=['Date']) removes the invalid rows.
    Numbers:
        Problem: Strings like "1,200" or "" (empty).
        Fix: Write a helper function to strip commas: float(val.replace(',', '')).
        Safety: Use .fillna(0) to turn empty cells into 0.0 so math doesn't fail.
    Derived Metrics:
        Create the final number you actually care about: df['Net'] = df['Credit'] - df['Debit'].

5) Enrichment (Categorization) - Turn raw text descriptions into analytical groups.
    Action: Define a rule-based function (e.g., if 'Netflix' in desc: return 'Entertainment').
    Execution: Apply it to the whole column: df['Category'] = df['Description'].apply(assign_category).
    Final Output: A DataFrame ready for charts (groupby('Category')).


List of functions used:
pd.read_csv() - The gateway. Reads text files into dataframes - pd.read_csv(file, header=0, sep=',')
.astype(str) - Force data to look like text. - Used in Header Hunt to safely search mixed rows.
.str.cat(sep=' ') - Glue a row of cells into one long string. - Makes searching for keywords easy.
.iloc[i] - Select a row by its index number. - df.iloc[5] gets the 6th row.
pd.to_datetime() - Convert text dates to real time objects. - pd.to_datetime(col, dayfirst=True)
.dropna() - Delete rows that have missing values. - df.dropna(subset=['Date']) cleans the footer.
.apply(func) - Run a custom Python function on every cell. - Used for cleaning currency strings and categorizing.
.fillna(0) - Replace empty/NaN values with a safe default. - Prevents math errors on empty credit/debit cells.
.groupby() - Group data to calculate totals. - df.groupby('Category')['Net'].sum()
"""

#FILE_PATH = os.path.join("demo_data", "1_january_2024.csv")
FILE_PATH = r"D:\AI\Financial_Dashboard\pandas_practice\demo_data\messy_bank.csv"

print(f"Loading raw preview from {FILE_PATH} ")
print(os.path.exists(FILE_PATH))


# header=none => treat the first row as data, not labels
# nrows=20 => peek at the top first 20 rows, keeping it fast

def read_file():
    try:
        # Force pandas to accept that different rows might have different widths (names=range(10))
        raw_preview = pd.read_csv(FILE_PATH, header=None, nrows=20, encoding="utf-8", sep=",", names=range(10))
        print(raw_preview)

    except UnicodeDecodeError:
        print("UTF-8 failed, trying cp1255..")
        raw_preview = pd.read_csv(FILE_PATH, header=None, nrows=20, encoding="cp1255", sep=",", names=range(10))

    return raw_preview

def find_row_data():
    header_idx = -1

    # The header must contain at least one of these words
    target_keywords = ["Date", "Description", "Reference", "Credit", "Debit"]

    # Loop through the preview rows
    for i, row in raw_preview.iterrows():
        # Forces every cell in the row to become a text string
        # sep - Concatenates (glues) all those cells together into one long string, separated by spaces.
        # result - the row become a single string
        row_str = row.astype(str).str.cat(sep=' ')
        print(row_str)

        # use any in case the row contains even one of the target keywords. This means its certainly the header row
        # if any(keyword in row_str for keyword in target_keywords):
        found_matches = [k for k in target_keywords if k in row_str]
        
        if len(found_matches) >= 2:
            header_idx = i
            print(f"Found header at index: {header_idx}")
            print(f"Matched Keywords: {found_matches}")
            break

    return header_idx


def load_full_data(header_idx):
    df = pd.read_csv(FILE_PATH, header=header_idx, encoding="utf-8-sig", sep=',')

    print("DF before cleaning")
    print(df.info())

    # print("\n--- First 2 Rows ---")
    # print(df.head(2))

    # Find the column containing 'Date'
    date_col = next((c for c in df.columns if "Date" in c), None)
    print(date_col)

    # Get a real datetime value 
    # dayFirst => for dd/mm/yyyy format
    # errors='coerce' turns the "Total" row's date into NaT (Not a Time)
    df["Clean_Date"] = pd.to_datetime(df[date_col], dayfirst=True, errors="coerce")
    print(df["Clean_Date"])

    # Clean rows where date didnt parse 
    df.dropna(subset=["Clean_Date"], inplace=True)
    print(df["Clean_Date"])

    def clean_currency(val):
        # Helper function to remove commas and convert to float
        if pd.isna(val) or val == '': return 0
        if isinstance(val, str):
            return float(val.replace(',', ''))
        
        return float (val)
    
    # Apply clean currency logic to credit and debt column
    # apply runs a custom function on every single cell in the column. good for mixing weird formatting like commas or currency symbols
    # use .fillna(0) first to handle empty cells
    # use fillna when:
    # math safety => df['Debit'].fillna(0) / 1000 - 0 = 1000
    # categorization => if "Netflix" in row['Description']: (crash) / df['Description'] = df['Description'].fillna("Unknown")
    # Continuity

    # when running the fillna on the apply funcition we:
    # ensures that if clean_currency returns None or NaN for any reason, 
    # it gets converted to 0.0 immediately so the Net calculation in the next step
    df["Credit_Clean"] = df["Credit"].apply(clean_currency).fillna(0)
    df["Debit_Clean"] = df["Debit"].apply(clean_currency).fillna(0)

    df["Net"] = df["Credit_Clean"]- df["Debit_Clean"]

    #print(df[["Clean_Date", "Description", "Net"]])


    print("\n--- 5. CATEGORIZATION ---")

    def assign_category(desc):
        desc = str(desc).upper() # Normalize to uppercase
        if 'SALARY' in desc or 'DEPOSIT' in desc:
            return 'Income'
        elif 'MORTGAGE' in desc:
            return 'Housing'
        elif 'BIT' in desc:
            return 'Transfers'
        elif 'CREDIT CARD' in desc:
            return 'Credit Card'
        else:
            return 'Other'
    
    # Apply the function to the description column
    df["Category"] = df["Description"].apply(assign_category)
    #print(df["Category"])

    # Keep only the columns we actually need
    final_df = df[["Clean_Date", "Category", "Description", "Net", "Credit_Clean", "Debit_Clean"]]

    # Rename columns to be pretty
    final_df.columns = ["Date", "Category", "Description", "Amount", "Income", "Expense"]

    # Group by category to see the sum of each
    print(final_df.groupby("Category")["Amount"].sum())


    



raw_preview = read_file()
print("\n--- RAW PREVIEW (first 5 rows) ---")
# print(raw_preview.head(10))

header_idx = find_row_data()


# difference between iloc and loc:
# iloc[4] (integer location) -> give me the row at position 4
# loc['2024-01-01] (label location) -> find the row by its label name
print(f"--- VERIFYING HEADER ROW (Index {header_idx}) ---")
print(raw_preview.iloc[header_idx])

# Peek at the file content
with open(FILE_PATH, "r", encoding="utf-8") as f:
    for i in range(7):
        print(repr(f.readline()))

load_full_data(header_idx)