# config.py

# --- 1. SYSTEM CONFIGURATION ---
DATA_FOLDER = r"D:\AI\Financial_Dashboard\demo_data"

# --- 2. CATEGORY CLASSIFICATION RULES ---
# Dictionary format: { "Category Name": ["keyword1", "keyword2", ...] }
# This can later be defined from external files..
CATEGORY_RULES = {
    'Salary': [
        'SALARY', 'משכורת', 'BIT TRANSFER', 'REFUND' # Grouped Income items
    ],
    'Mortgage': [
        'MORTGAGE', 'משכנתא'
    ],
    'Credit Cards': [
        'CREDIT CARD', 'כרטיסי אשראי', 'מקס איט'
    ],
    'Utilities': [
        'ELECTRIC CO', 'WATER BILL', 'ARNONA', 'BEZEQ', 'הוראת קבע'
    ],
    'Groceries': [
        'SUPER YUDA', 'SHUFERSAL', 'RAMI LEVY', 'VICTORY', 'AM:PM', 
        'MEGA', 'TIV TAAM'
    ],
    'Restaurants': [
        'AROMA', 'MCDONALDS', 'DOMINOS', 'GOLDA', 'ARCAFFE', 
        'BENEDICT', 'GIRAFFE'
    ],
    'Transport': [
        'PANGO', 'PAZ FUEL', 'DELEK', 'TRAIN ISRAEL', 'LIME', 'MOOVIT'
    ],
    'Shopping': [
        'ZARA', 'H&M', 'SUPER PHARM', 'FOX', 'TERMINAL X', 'KSP', 'IVORY'
    ],
    'Entertainment': [
        'NETFLIX', 'SPOTIFY', 'CINEMA CITY', 'STEAM', 'PLAYSTATION'
    ]
}

# --- 3. UI STYLING & COLORS ---
# Centralize colors so you can switch themes easily later
COLORS = {
    'bg': '#0f172a',
    'card_bg': '#1e293b', # slate-800
    'text_main': '#f1f5f9',
    'text_sub': '#94a3b8',
    'income': '#10b981',   # emerald-500
    'expense': '#ef4444',  # red-500
    'chart_text': '#94a3b8'
}

# --- 4. ICON MAPPING ---
# Used in the breakdown cards
CATEGORY_ICONS = {
    'Salary': 'work',
    'Mortgage': 'home',
    'Credit Cards': 'credit_card',
    'Groceries': 'shopping_cart',
    'Utilities': 'bolt',
    'Transport': 'directions_car',
    'Shopping': 'shopping_bag',
    'Entertainment': 'movie',
    'Restaurants': 'restaurant',
    'Health': 'medical_services',
    'Communication': 'wifi',
    'Education': 'school',
    'Travel': 'flight',
    'Other': 'attach_money'
}