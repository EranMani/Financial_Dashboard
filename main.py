from nicegui import ui, app, run
import pandas as pd
import glob
import os
import calendar
import numpy as np
import re
from datetime import datetime
import config

# --- CONFIGURATION ---
DATA_FOLDER = r"demo_data" # Updated to point to the demo folder

# --- 1. FINANCIAL BRAIN ---
class FinancialBrain:
    def __init__(self):
        # 1. Master Data Storage
        self.bank_df = pd.DataFrame()       
        self.cc_df = pd.DataFrame()         
        self.master_df = pd.DataFrame()
        
        # 2. Active Views
        self.active_bank_df = pd.DataFrame() 
        self.active_cc_df = pd.DataFrame()   
        self.analytics_df = pd.DataFrame()

        # 3. Metrics
        self.income_breakdown = []
        self.expense_breakdown = []
        self.cc_breakdown = []
        self.transactions = []
        
        self.total_net = 0
        self.total_income = 0
        self.total_expense = 0
        
        # KPI Comparisons
        self.prev_total_net = 0
        self.prev_total_income = 0
        self.prev_savings_rate = 0
        
        self.available_years = ["All Years"]
        self.available_months = ["All Months"]
        self.available_categories = ["All Categories"]
        
        # Internal State
        self.current_year_filter = "All Years"
        self.load_status = "Waiting..."

    def get_category_from_keywords(self, desc):
        """
        Scans the description against keywords defined in config.CATEGORY_RULES.
        Returns the first matching category or 'Other'.
        """

        desc = str(desc).upper()

        for category, keywords in config.CATEGORY_RULES.items():
            for keyword in keywords:
                if keyword in desc:
                    return category
                
        return "Other"

    def parse_info_from_filename(self, filename):
        try:
            base = os.path.basename(filename).lower()
            year_match = re.search(r'20[2-3]\d', base)
            if not year_match: return None, None, None
            year_str = year_match.group(0)
            month_str = None
            month_num = None
            for m_name in calendar.month_name[1:]:
                if m_name.lower() in base:
                    month_str = m_name
                    month_num = list(calendar.month_name).index(m_name)
                    break
            if not month_str: return None, None, None
            return year_str, month_str, month_num
        except: return None, None, None

    def read_file_smart(self, file_path):
        is_excel = file_path.lower().endswith(('.xlsx', '.xls'))
        try:
            if is_excel:
                temp_df = pd.read_excel(file_path, header=None, nrows=20)
            else:
                for enc in ['utf-8', 'cp1255', 'windows-1255', 'iso-8859-8', 'utf-8-sig']:
                    try:
                        temp_df = pd.read_csv(file_path, header=None, nrows=20, encoding=enc)
                        break
                    except: continue
            if 'temp_df' not in locals(): return None

            header_idx = -1
            for i, row in temp_df.iterrows():
                row_str = row.astype(str).str.cat(sep=' ')
                if 'תאריך' in row_str or 'Date' in row_str or 'שם בית העסק' in row_str or 'שם בית עסק' in row_str or 'פרטים' in row_str:
                    header_idx = i
                    break
            if header_idx == -1: return None

            if is_excel:
                df = pd.read_excel(file_path, header=header_idx)
            else:
                for enc in ['utf-8', 'cp1255', 'windows-1255', 'iso-8859-8', 'utf-8-sig']:
                    try:
                        df = pd.read_csv(file_path, header=header_idx, encoding=enc)
                        break
                    except: continue
            
            df.columns = df.columns.astype(str).str.strip().str.replace("\n", " ").str.replace("\r", "")
            return df
        except: return None

    def normalize_data(self, df, source_type, file_year=None, file_month=None, file_month_num=None):
        normalized = pd.DataFrame()
        normalized['Source_Type'] = source_type 
        
        if source_type == 'bank':
            date_col = next((c for c in df.columns if 'תאריך' in c), None)
            credit_col = next((c for c in df.columns if 'זכות' in c), None)
            debit_col = next((c for c in df.columns if 'חובה' in c), None)
            # Demo bank file uses 'פרטים' as main description
            details_col = next((c for c in df.columns if 'פרטים' in c), None)

            if not date_col or (not credit_col and not debit_col): return pd.DataFrame()

            normalized['Date_Raw'] = df[date_col]
            normalized['Raw_Desc'] = df[details_col].fillna('') if details_col else ""
            
            credit = pd.to_numeric(df[credit_col], errors='coerce').fillna(0) if credit_col else 0
            debit = pd.to_numeric(df[debit_col], errors='coerce').fillna(0) if debit_col else 0
            normalized['Net'] = credit - debit
            normalized['Category'] = normalized['Raw_Desc'].apply(self.get_category_from_keywords)

        elif source_type == 'credit_card':
            date_col = next((c for c in df.columns if 'תאריך' in c), None)
            if not date_col: return pd.DataFrame()
            
            normalized['Date_Raw'] = df[date_col]
            name_col = next((c for c in df.columns if 'שם בית' in c or 'שם עסק' in c), None)
            
            s_name = df[name_col].fillna('') if name_col else pd.Series('', index=df.index)
            normalized['Raw_Desc'] = s_name.astype(str)
            
            amount_col = next((c for c in df.columns if 'סכום' in c and 'חיוב' in c), None) # Match 'סכום חיוב'
            if amount_col:
                amount = pd.to_numeric(df[amount_col], errors='coerce').fillna(0)
                normalized['Net'] = amount * -1
            else:
                normalized['Net'] = 0

            # Demo CC files have explicit 'קטגוריה' column
            cat_col = next((c for c in df.columns if 'קטגוריה' in c or 'ענף' in c), None)
            normalized['Category'] = normalized['Raw_Desc'].apply(self.get_category_from_keywords)

        normalized['Date_Obj'] = pd.to_datetime(normalized['Date_Raw'], dayfirst=True, errors='coerce')
        normalized.dropna(subset=['Date_Obj'], inplace=True)
        
        if file_year and file_month:
            normalized['Year_Str'] = str(file_year)
            normalized['Month_Str'] = str(file_month)
            normalized['Month_Num'] = int(file_month_num)
        else:
            normalized['Year_Str'] = normalized['Date_Obj'].dt.year.astype(int).astype(str)
            normalized['Month_Str'] = normalized['Date_Obj'].dt.month_name()
            normalized['Month_Num'] = normalized['Date_Obj'].dt.month

        normalized['Date'] = normalized['Date_Obj'].dt.strftime('%Y-%m-%d')
        return normalized

    def load_folder(self, folder_path: str):
        try:
            bank_list = []
            cc_list = []
            if not os.path.exists(folder_path): return "Folder not found"
            files = glob.glob(os.path.join(folder_path, "**", "*.csv"), recursive=True) + \
                    glob.glob(os.path.join(folder_path, "**", "*.xlsx"), recursive=True)
            if not files: return "No files found"

            for file_path in files:
                filename = os.path.basename(file_path).lower()
                
                # Check format based on demo logic
                # Demo CC: "1_january_2024_maxit.csv"
                # Demo Bank: "1_january_2024.csv"
                if "_maxit" in filename: source_type = "credit_card"
                else: source_type = "bank"

                f_year, f_month, f_month_num = self.parse_info_from_filename(filename)
                df = self.read_file_smart(file_path)
                if df is None or df.empty: continue

                clean_df = self.normalize_data(df, source_type, f_year, f_month, f_month_num)
                if not clean_df.empty:
                    if source_type == "bank": bank_list.append(clean_df)
                    else: cc_list.append(clean_df)

            self.bank_df = pd.concat(bank_list, ignore_index=True) if bank_list else pd.DataFrame(columns=['Year_Str', 'Month_Str', 'Month_Num', 'Net', 'Category', 'Source_Type', 'Date_Obj'])
            if not self.bank_df.empty: self.bank_df.sort_values(by='Date_Obj', ascending=False, inplace=True)

            self.cc_df = pd.concat(cc_list, ignore_index=True) if cc_list else pd.DataFrame(columns=['Year_Str', 'Month_Str', 'Month_Num', 'Net', 'Category', 'Source_Type', 'Date_Obj'])
            if not self.cc_df.empty: self.cc_df.sort_values(by='Date_Obj', ascending=False, inplace=True)

            self.master_df = pd.concat([self.bank_df, self.cc_df], ignore_index=True)
            
            if not self.master_df.empty:
                unique_years = sorted(self.master_df['Year_Str'].unique().tolist(), reverse=True)
                self.available_years = ["All Years"] + unique_years
            
            self.apply_filter("All Years", "All Months")
            return f"Loaded {len(bank_list)} Bank, {len(cc_list)} CC files."

        except Exception as e: return f"Error: {str(e)}"

    def get_months_for_year(self, year):
        combined = pd.concat([self.bank_df, self.cc_df])
        if combined.empty: return ["All Months"]
        if year == "All Years":
            months = combined.sort_values('Month_Num')['Month_Str'].unique().tolist()
        else:
            months = combined[combined['Year_Str'] == year].sort_values('Month_Num')['Month_Str'].unique().tolist()
        return ["All Months"] + months

    def apply_filter(self, selected_year, selected_month, date_range=None):
        self.current_year_filter = selected_year
        b_df = self.bank_df.copy()
        c_df = self.cc_df.copy()
        a_df = self.bank_df.copy()

        if date_range:
            try:
                if isinstance(date_range, str):
                    start = pd.to_datetime(date_range)
                    end = pd.to_datetime(date_range)
                else:
                    s_val = date_range.get('from')
                    e_val = date_range.get('to')
                    if not e_val: e_val = s_val 
                    start = pd.to_datetime(s_val)
                    end = pd.to_datetime(e_val)

                if not b_df.empty: b_df = b_df[(b_df['Date_Obj'] >= start) & (b_df['Date_Obj'] <= end)]
                if not c_df.empty: c_df = c_df[(c_df['Date_Obj'] >= start) & (c_df['Date_Obj'] <= end)]
                if not a_df.empty: a_df = a_df[(a_df['Date_Obj'] >= start) & (a_df['Date_Obj'] <= end)]
            except: pass

        elif selected_year != "All Years":
            if not b_df.empty: b_df = b_df[b_df['Year_Str'] == selected_year]
            if not c_df.empty: c_df = c_df[c_df['Year_Str'] == selected_year]
            if not a_df.empty: a_df = a_df[a_df['Year_Str'] == selected_year]
            
            if selected_month != "All Months":
                if not b_df.empty: b_df = b_df[b_df['Month_Str'] == selected_month]
                if not c_df.empty: c_df = c_df[c_df['Month_Str'] == selected_month]
                
        self.active_bank_df = b_df
        self.active_cc_df = c_df
        self.analytics_df = a_df

        # --- METRICS ---
        if not self.active_bank_df.empty:
            pos = self.active_bank_df[self.active_bank_df['Net'] > 0]
            neg = self.active_bank_df[self.active_bank_df['Net'] < 0]
            self.total_income = pos['Net'].sum()
            self.total_expense = neg['Net'].sum()
            self.total_net = self.total_income + self.total_expense
            
            # Previous Period Logic (Simplified for Demo)
            self.prev_total_net = 0
            self.prev_total_income = 0
            self.prev_savings_rate = 0
            
            self.income_breakdown = []
            for cat, group in pos.groupby('Category'):
                self.income_breakdown.append({'category': cat, 'amount': group['Net'].sum(), 'pct': round(group['Net'].sum() / self.total_income * 100, 1) if self.total_income else 0})
            self.income_breakdown.sort(key=lambda x: x['amount'], reverse=True)

            self.expense_breakdown = []
            abs_exp = abs(self.total_expense)
            for cat, group in neg.groupby('Category'):
                self.expense_breakdown.append({'category': cat, 'amount': abs(group['Net'].sum()), 'pct': round(abs(group['Net'].sum()) / abs_exp * 100, 1) if abs_exp else 0})
            self.expense_breakdown.sort(key=lambda x: x['amount'], reverse=True)
        else:
            self.total_income = 0; self.total_expense = 0; self.total_net = 0
            self.income_breakdown = []; self.expense_breakdown = []

        self.cc_breakdown = []
        if not self.active_cc_df.empty:
            neg_cc = self.active_cc_df[self.active_cc_df['Net'] < 0]
            total_cc = abs(neg_cc['Net'].sum())
            for cat, group in neg_cc.groupby('Category'):
                self.cc_breakdown.append({'category': cat, 'amount': abs(group['Net'].sum()), 'pct': round(abs(group['Net'].sum()) / total_cc * 100, 1) if total_cc else 0})
            self.cc_breakdown.sort(key=lambda x: x['amount'], reverse=True)
            self.available_categories = ["All Categories"] + sorted(self.active_cc_df['Category'].unique().tolist())
        else:
            self.available_categories = ["All Categories"]

        self.transactions = []
        if not self.active_cc_df.empty:
            for _, row in self.active_cc_df.iterrows():
                self.transactions.append({'date': row['Date'], 'desc': row['Raw_Desc'], 'category': row['Category'], 'amount': row['Net'], 'type': 'income' if row['Net'] > 0 else 'expense', 'source': 'Credit Card'})

    def get_yoy_series(self, category_name):
        combined = pd.concat([self.bank_df, self.cc_df])
        if combined.empty: return []
        cat_df = combined[combined['Category'] == category_name].copy()
        if cat_df.empty: return []
        cat_df['Abs_Amount'] = cat_df['Net'].abs()
        grouped = cat_df.groupby(['Year_Str', 'Month_Num'])['Abs_Amount'].sum().reset_index()
        series_list = []
        all_years = sorted(grouped['Year_Str'].unique())
        for year in all_years:
            year_data = grouped[grouped['Year_Str'] == year]
            monthly_values = [0.0] * 12
            for _, row in year_data.iterrows():
                m_idx = int(row['Month_Num']) - 1
                monthly_values[m_idx] = float(round(row['Abs_Amount'], 2))
            series_list.append({'name': year, 'type': 'bar', 'emphasis': {'focus': 'series'}, 'data': monthly_values})
        return series_list
    
    def get_top_grocery_items(self):
        if self.cc_df.empty: return [], []
        groceries = self.cc_df[self.cc_df['Category'] == 'Groceries'].copy()
        if groceries.empty: return [], []
        top_items = groceries.groupby('Raw_Desc')['Net'].sum().abs().sort_values(ascending=False).head(10)
        labels = [name[:20] + '...' if len(name) > 20 else name for name in top_items.index.tolist()]
        values = [float(round(x, 2)) for x in top_items.values.tolist()]
        return labels, values
    
    def generate_smart_insights(self):
        insights = []
        curr_rate = (self.total_net / self.total_income * 100) if self.total_income else 0
        if curr_rate < 0: insights.append(("Critical", "Negative Cash Flow", f"You spent **{abs(self.total_net):,.0f} ₪** more than you earned."))
        elif curr_rate < 10: insights.append(("Warning", "Low Savings", f"Savings rate is **{curr_rate:.1f}%**. Target 20%."))
        else: insights.append(("Success", "Healthy Savings", f"Great job! You saved **{curr_rate:.1f}%** of income."))
        if self.expense_breakdown:
            top_exp = self.expense_breakdown[0]
            if top_exp['pct'] > 40: insights.append(("Warning", f"High {top_exp['category']}", f"Consumed **{top_exp['pct']:.1f}%** of expenses."))
        return insights

    def get_analytics_data(self):
        df = self.analytics_df.copy()
        if df.empty: return None
        df['Sort_Key'] = df['Year_Str'].astype(int) * 100 + df['Month_Num']
        monthly = df.groupby(['Year_Str', 'Month_Str', 'Sort_Key']).agg({'Net': 'sum'}).reset_index().sort_values('Sort_Key')
        monthly_data, months_labels = [], []
        for _, row in monthly.iterrows():
            m_year, m_name = row['Year_Str'], row['Month_Str']
            sub_df = df[(df['Year_Str'] == m_year) & (df['Month_Str'] == m_name)]
            inc = float(sub_df[sub_df['Net'] > 0]['Net'].sum())
            exp = float(abs(sub_df[sub_df['Net'] < 0]['Net'].sum()))
            net = inc - exp
            months_labels.append(f"{m_name[:3]} {m_year}")
            monthly_data.append({'income': round(inc, 2), 'expense': round(exp, 2), 'net': round(net, 2)})
        
        cc_data = self.cc_df.copy()
        if self.current_year_filter != "All Years": cc_data = cc_data[cc_data['Year_Str'] == self.current_year_filter]
        if cc_data.empty: cat_labels, cat_values, cat_objs = [], [], []
        else:
             cc_exp = cc_data[cc_data['Net'] < 0]
             cat_df = cc_exp.groupby('Category')['Net'].sum().abs().sort_values(ascending=False)
             cat_labels = [str(x) for x in cat_df.index.tolist()]
             cat_values = [float(round(x, 2)) for x in cat_df.values.tolist()]
             cat_objs = [{'value': v, 'name': k} for k, v in zip(cat_labels, cat_values)]
        return {'months': months_labels, 'data': monthly_data, 'categories': {'labels': cat_labels, 'values': cat_values, 'objects': cat_objs}}

brain = FinancialBrain()

# --- 2. UI DASHBOARD ---
@ui.page('/')
def dashboard():
    ui.add_head_html('''
        <style>
            body { background-color: #0f172a; font-family: 'Inter', sans-serif; color: #f1f5f9; }
            .nicegui-tabs .q-tab { text-transform: none; font-weight: 500; color: #94a3b8; }
            .nicegui-tabs .q-tab--active { color: #f8fafc; }
            .nicegui-tabs .q-tab__indicator { height: 3px; background: #3b82f6; }
        </style>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    ''')
    
    view_state = {'chart_mode': 'pie'}

    with ui.column().classes('w-full max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6'):
        
        # --- HEADER ---
        with ui.card().classes('w-full mb-6 p-6 md:p-8 rounded-xl border border-slate-700 bg-slate-800 shadow-lg'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-1'):
                    ui.label('Your Financial Dashboard').classes('text-3xl font-bold text-slate-100')
                    ui.label('Track your income, expenses, and savings').classes('text-base text-slate-400')
                
                with ui.row().classes('items-center gap-6'):
                    # Year Nav
                    with ui.row().classes('items-center bg-slate-700 rounded-lg p-1 border border-slate-600 gap-1'):
                        def nav_year(direction):
                            years = brain.available_years
                            if not years: return
                            try:
                                idx = years.index(sel_year.value)
                                new_idx = (idx - direction) % len(years) 
                                sel_year.value = years[new_idx]
                            except: pass
                        ui.button(icon='chevron_left', on_click=lambda: nav_year(-1)).props('flat dense color=grey-4')
                        sel_year = ui.select(brain.available_years, value='All Years', on_change=lambda e: change_year(e.value)).props('standout="bg-grey-9 text-white" dense options-dense borderless').classes('text-lg font-bold text-white w-28 text-center')
                        ui.button(icon='chevron_right', on_click=lambda: nav_year(1)).props('flat dense color=grey-4')

                    # Month Nav
                    with ui.row().classes('items-center bg-slate-700 rounded-lg p-1 border border-slate-600 gap-1'):
                        def nav_month(direction):
                            months = brain.get_months_for_year(sel_year.value)
                            if not months: return
                            try:
                                idx = months.index(sel_month.value)
                                new_idx = (idx + direction) % len(months)
                                sel_month.value = months[new_idx]
                            except: pass
                        ui.button(icon='chevron_left', on_click=lambda: nav_month(-1)).props('flat dense color=grey-4')
                        sel_month = ui.select(brain.available_months, value='All Months', on_change=lambda e: change_month(e.value)).props('standout="bg-grey-9 text-white" dense options-dense borderless').classes('text-sm text-slate-400 w-28 text-center')
                        ui.button(icon='chevron_right', on_click=lambda: nav_month(1)).props('flat dense color=grey-4')

                    # Calendar
                    with ui.dialog() as date_dialog, ui.card().classes('bg-slate-800 border border-slate-700'):
                        def on_date_range(e):
                            if e:
                                val = e if isinstance(e, dict) else {'from': e, 'to': e}
                                if 'from' in val and 'to' not in val: val['to'] = val['from']
                                brain.apply_filter("Custom", "Custom", date_range=val)
                                sel_year.value, sel_month.value = "Custom", "Range"
                                refresh_ui()
                                date_dialog.close()
                        ui.date(on_change=lambda e: on_date_range(e.value)).props('range dark')
                    ui.button(icon='calendar_month', on_click=date_dialog.open).classes('bg-slate-700 text-slate-300 border border-slate-600 hover:bg-slate-600 shadow-sm w-10 h-10 p-0 ml-2')

                    with ui.row().classes('items-center gap-3 border-l border-slate-600 pl-6'):
                         with ui.avatar().classes('bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold'): ui.label('EM')
                         with ui.column().classes('gap-0'):
                             ui.label('Eran Mani').classes('font-semibold text-slate-200 text-sm')
                             ui.label('Premium Plan').classes('text-xs text-emerald-400')

        # TABS
        with ui.tabs().classes('bg-transparent mb-6') as tabs:
            tab_overview = ui.tab('Overview')
            tab_transactions = ui.tab('Transactions')
            tab_analytics = ui.tab('Analytics')

        # PANELS
        with ui.tab_panels(tabs, value=tab_overview).classes('w-full bg-transparent'):
            
            # OVERVIEW
            with ui.tab_panel(tab_overview).classes('p-0 gap-6'):
                con_top_cards = ui.grid().classes('grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full')
                con_breakdowns = ui.grid().classes('grid-cols-1 lg:grid-cols-2 gap-6 w-full')
                con_health_summary = ui.card().classes('w-full p-0 overflow-hidden border border-t-4 border-blue-500 border-slate-700 bg-slate-800 shadow-sm rounded-xl mt-2')

            # TRANSACTIONS
            with ui.tab_panel(tab_transactions).classes('p-0 mt-6'):
                with ui.grid().classes('grid-cols-1 lg:grid-cols-3 gap-6 w-full'):
                    with ui.card().classes('lg:col-span-2 p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-[500px] flex flex-col'):
                        with ui.row().classes('w-full justify-between items-center mb-4'):
                             with ui.row().classes('items-center gap-2'):
                                 ui.icon('pie_chart').classes('text-slate-400')
                                 with ui.column().classes('gap-0'):
                                     ui.label('Expense Analytics (Credit Cards)').classes('font-bold text-xl text-slate-100')
                                     ui.label('Detailed breakdown').classes('text-sm text-slate-400')
                             def set_chart_mode(mode):
                                 view_state['chart_mode'] = mode
                                 refresh_tx_charts()
                             with ui.button_group().props('flat'):
                                 ui.button('Pie', on_click=lambda: set_chart_mode('pie')).props('flat size=sm text-color=white').classes('text-slate-300')
                                 ui.button('Bar', on_click=lambda: set_chart_mode('bar')).props('flat size=sm text-color=white').classes('text-slate-300')
                        con_tx_charts = ui.element('div').classes('w-full flex-grow relative min-h-0 overflow-hidden')

                    with ui.card().classes('p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-[500px] flex flex-col'):
                         with ui.row().classes('items-center gap-2 mb-4'):
                             ui.icon('bar_chart').classes('text-slate-400')
                             with ui.column().classes('gap-0'):
                                 ui.label('Category Details').classes('font-bold text-xl text-slate-100')
                                 ui.label('Credit Card Spending').classes('text-sm text-slate-400')
                         con_tx_cats = ui.scroll_area().classes('w-full flex-grow pr-4')

                with ui.grid().classes('grid-cols-1 lg:grid-cols-3 gap-6 w-full mt-6'):
                    with ui.card().classes('lg:col-span-2 p-0 rounded-xl shadow-sm border border-slate-700 bg-slate-800'):
                        with ui.row().classes('w-full justify-between items-center p-6 border-b border-slate-700 gap-4'):
                            with ui.column().classes('gap-0'):
                                 ui.label('Transaction History').classes('font-bold text-xl text-slate-100')
                                 ui.label('Credit Card Transactions').classes('text-sm text-slate-400')
                                 ui.element('div').props('id=tx_history_anchor')
                            with ui.row().classes('items-center gap-2'):
                                search_input = ui.input(placeholder='Search...').props('dark outlined dense').classes('w-40 bg-slate-700 text-white text-base')
                                with search_input.add_slot('prepend'): ui.icon('search').classes('text-slate-400')
                                cat_select = ui.select(brain.available_categories, value='All Categories').props('dark outlined dense options-dense').classes('w-40 bg-slate-700 text-white text-base')
                                
                                def on_filter_change(e=None):
                                    render_transactions_list(con_tx_list, search_input.value, cat_select.value)
                                    filtered_df = brain.active_cc_df.copy()
                                    if cat_select.value != 'All Categories':
                                        filtered_df = filtered_df[filtered_df['Category'] == cat_select.value]
                                    if search_input.value:
                                        term = str(search_input.value).lower()
                                        filtered_df = filtered_df[filtered_df.apply(lambda row: term in str(row['Raw_Desc']).lower() or term in str(row['Category']).lower(), axis=1)]
                                    refresh_top_expenses_widget(filtered_df)
                                search_input.on_value_change(on_filter_change)
                                cat_select.on_value_change(on_filter_change)
                                def set_category_filter(cat_name):
                                    cat_select.value = cat_name
                                    ui.run_javascript('document.getElementById("tx_history_anchor").scrollIntoView({behavior: "smooth", block: "center"});')

                        con_tx_list = ui.column().classes('w-full gap-0')

                    with ui.card().classes('p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-full'):
                        with ui.row().classes('items-center gap-2 mb-4'):
                            ui.icon('leaderboard').classes('text-slate-400')
                            with ui.column().classes('gap-0'):
                                ui.label('Top Expenses').classes('font-bold text-xl text-slate-100')
                                ui.label('Highest spenders').classes('text-sm text-slate-400')
                        con_top_expenses_widget = ui.column().classes('w-full gap-3')

            # ANALYTICS
            with ui.tab_panel(tab_analytics).classes('p-0 mt-6'):
                con_analytics = ui.column().classes('w-full gap-6')

    # --- LOGIC ---
    def update_options():
        sel_year.options = brain.available_years
        if sel_year.value not in brain.available_years: sel_year.value = "All Years"
        sel_year.update()
        update_month_options()
        cat_select.options = brain.available_categories
        cat_select.update()

    def update_month_options():
        curr_year = sel_year.value
        months = brain.get_months_for_year(curr_year)
        sel_month.options = months
        if sel_month.value not in months: sel_month.value = "All Months"
        sel_month.update()

    def change_year(val):
        update_month_options()
        brain.apply_filter(val, sel_month.value)
        refresh_ui()

    def change_month(val):
        brain.apply_filter(sel_year.value, val)
        refresh_ui()

    def refresh_top_expenses_widget(df_source):
        con_top_expenses_widget.clear()
        with con_top_expenses_widget:
            if df_source.empty:
                 ui.label('No data').classes('text-slate-400 italic text-base'); return
            expenses = df_source[df_source['Net'] < 0]
            if expenses.empty:
                 ui.label('No expenses').classes('text-slate-400 italic text-base'); return
            top = expenses.groupby('Raw_Desc')['Net'].sum().abs().sort_values(ascending=False).head(5)
            colors = ['bg-red-900/30 text-red-300 border-red-800', 'bg-orange-900/30 text-orange-300 border-orange-800', 'bg-amber-900/30 text-amber-300 border-amber-800', 'bg-yellow-900/30 text-yellow-300 border-yellow-800', 'bg-lime-900/30 text-lime-300 border-lime-800']
            for i, (name, amount) in enumerate(top.items()):
                style = colors[i % len(colors)]
                with ui.card().classes(f"w-full p-3 rounded-lg border shadow-sm {style}"):
                     with ui.row().classes('w-full justify-between items-center'):
                         with ui.row().classes('items-center gap-3'):
                             ui.label(f"#{i+1}").classes(f"font-bold text-base")
                             ui.label(name[:20]).classes('font-medium text-base text-slate-200 leading-tight')
                         ui.label(f"₪{amount:,.0f}").classes('font-bold text-base text-slate-100')

    def render_transactions_list(container, search_term, cat_filter):
        container.clear()
        with container:
            filtered = brain.transactions
            if cat_filter and cat_filter != 'All Categories': filtered = [t for t in filtered if t['category'] == cat_filter]
            if search_term:
                term = str(search_term).lower()
                filtered = [t for t in filtered if term in str(t['desc']).lower() or term in str(t['category']).lower()]
            with ui.scroll_area().classes('h-[500px] w-full'):
                if not filtered: ui.label('No matching transactions.').classes('w-full text-center text-slate-400 py-8 text-base')
                else:
                    for t in filtered:
                        is_inc = t['type'] == 'income'
                        icon = 'keyboard_arrow_up' if is_inc else 'keyboard_arrow_down'
                        icon_bg = 'bg-emerald-900/30 text-emerald-400' if is_inc else 'bg-red-900/30 text-red-400'
                        amt_color = 'text-emerald-400' if is_inc else 'text-red-400'
                        src_color = 'bg-purple-900/30 text-purple-300'
                        with ui.row().classes('w-full justify-between items-center p-4 hover:bg-slate-700 border-b border-slate-700'):
                            with ui.row().classes('items-center gap-4'):
                                with ui.element('div').classes(f'p-2 rounded-full {icon_bg}'): ui.icon(icon).classes('text-base')
                                with ui.column().classes('gap-0'):
                                    ui.label(t['desc']).classes('font-semibold text-slate-200 text-base')
                                    with ui.row().classes('items-center gap-2 text-sm text-slate-400'):
                                        ui.label(t['date']); ui.element('div').classes('w-1 h-1 rounded-full bg-slate-500')
                                        ui.label(t['source']).classes(f'px-1 rounded {src_color}'); ui.element('div').classes('w-1 h-1 rounded-full bg-slate-500')
                                        ui.label(t['category'])
                            ui.label(f"{'+' if is_inc else ''} ₪{abs(t['amount']):,.2f}").classes(f'font-bold text-base {amt_color}')

    def refresh_tx_charts():
        con_tx_charts.clear()
        data = brain.cc_breakdown 
        if not data:
             with con_tx_charts: ui.label('No data').classes('m-auto text-slate-400 text-base'); return
        cats = [x['category'] for x in data]; vals = [x['amount'] for x in data]
        pie_data = [{'value': x['amount'], 'name': x['category']} for x in data]
        text_color = '#94a3b8' 
        with con_tx_charts:
            if view_state['chart_mode'] == 'pie':
                ui.echart({'tooltip': {'trigger': 'item', 'formatter': '{b}: {c} ₪ ({d}%)'}, 'legend': {'type': 'scroll', 'bottom': 0, 'textStyle': {'color': text_color, 'fontSize': 14}}, 'series': [{'name': 'Expenses', 'type': 'pie', 'radius': ['40%', '70%'], 'avoidLabelOverlap': False, 'itemStyle': {'borderRadius': 10, 'borderColor': '#334155', 'borderWidth': 2}, 'label': {'show': False}, 'emphasis': {'label': {'show': True, 'fontSize': 16, 'fontWeight': 'bold', 'color': '#fff'}}, 'data': pie_data}]}).classes('absolute inset-0 w-full h-full')
            else:
                ui.echart({'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}}, 'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True}, 'xAxis': {'type': 'category', 'data': cats, 'axisLabel': {'interval': 0, 'rotate': 30, 'color': text_color, 'fontSize': 12}}, 'yAxis': {'type': 'value', 'axisLabel': {'color': text_color, 'fontSize': 12}}, 'series': [{'data': vals, 'type': 'bar', 'itemStyle': {'color': '#6366f1', 'borderRadius': [5, 5, 0, 0]}}]}).classes('absolute inset-0 w-full h-full')

    def render_breakdown_card(container, title, items, is_income):
        if is_income: header_icon, header_color, progress_color, border_color = 'trending_up', 'text-green-400', 'green-500', 'border-emerald-500'
        else: header_icon, header_color, progress_color, border_color = 'trending_down', 'text-red-400', 'red-500', 'border-rose-500'
        with container:
            with ui.card().classes(f'w-full p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-700 border-t-4 {border_color}'):
                with ui.row().classes('items-center gap-2 mb-1'):
                    ui.icon(header_icon).classes(f'h-5 w-5 {header_color}'); ui.label(title).classes('font-semibold text-xl text-slate-100')
                with ui.scroll_area().classes('w-full gap-6 h-64 pr-4'):
                    if not items: ui.label('No bank data').classes('text-base text-slate-400 italic')
                    else:
                        for i, item in enumerate(items):
                            with ui.column().classes('w-full gap-2'):
                                with ui.row().classes('w-full justify-between items-start'):
                                    with ui.row().classes('items-center gap-3'):
                                        icon_name = config.CATEGORY_ICONS.get(item["category"], "attach_money")
                                        with ui.element('div').classes('p-2 rounded-lg bg-slate-600'): ui.icon(icon_name).classes(f'h-5 w-5 {header_color}')
                                        with ui.column().classes('gap-0'):
                                            with ui.label(item['category']).classes('font-medium text-slate-200 text-base cursor-help'):
                                                with ui.tooltip().classes('bg-slate-900 border border-slate-700 text-white p-0 rounded shadow-xl z-50').props('track-origin'):
                                                    with ui.element('div').classes('p-2'):
                                                        ui.label(f'{item["category"]} Top 10').classes('font-bold text-slate-300 text-sm uppercase tracking-wider mb-2 border-b border-slate-700 pb-1')
                                                        target_df = brain.active_bank_df 
                                                        if is_income: cat_df = target_df[(target_df['Category'] == item['category']) & (target_df['Net'] > 0)]
                                                        else: cat_df = target_df[(target_df['Category'] == item['category']) & (target_df['Net'] < 0)]
                                                        top_tx = cat_df.reindex(cat_df['Net'].abs().sort_values(ascending=False).index).head(10)
                                                        if top_tx.empty: ui.label('No details').classes('text-xs text-slate-500 italic')
                                                        else:
                                                            with ui.grid().classes('grid-cols-2 gap-x-4 gap-y-1 items-center'):
                                                                ui.label('Name').classes('text-slate-500 font-semibold text-xs'); ui.label('Sum').classes('text-slate-500 font-semibold text-right text-xs')
                                                                for _, row in top_tx.iterrows():
                                                                    ui.label(row['Raw_Desc'][:15]).classes('text-slate-200 truncate text-xs'); ui.label(f"{row['Net']:,.0f} ₪").classes('text-blue-400 font-mono text-right text-xs')
                                            ui.label(f"{item['pct']:.1f}%").classes('text-sm text-slate-400')
                                    ui.label(f"{item['amount']:,.0f} ₪").classes('font-semibold text-slate-100 text-base')
                                ui.linear_progress(item['pct']/100, show_value=False).props(f'color={progress_color} track-color=grey-8 size=8px rounded')
                            if i < len(items) - 1: ui.separator().classes('bg-slate-600')

    def refresh_ui():
        con_top_cards.clear()
        with con_top_cards:
            def kpi_card(title, value, sub_text, icon, gradient_class):
                with ui.card().classes(f'relative overflow-hidden p-6 rounded-2xl border-t-4 shadow-lg {gradient_class} group'):
                    ui.icon(icon).classes('absolute -right-6 -bottom-6 text-9xl text-white/10 rotate-12 group-hover:rotate-6 transition-transform duration-500')
                    with ui.column().classes('relative z-10 gap-1'):
                        ui.label(title).classes('text-sm font-bold text-white/80 uppercase tracking-widest')
                        val_color = 'text-white'
                        if title == 'Total Income': val_color = 'text-emerald-400'
                        elif title == 'Total Expenses': val_color = 'text-red-400'
                        elif title == 'Total Savings': val_color = 'text-emerald-400' if brain.total_net >= 0 else 'text-red-400'
                        elif title == 'Savings Rate': 
                             try: val_color = 'text-purple-400' if float(value.replace('%',''))>=0 else 'text-red-400'
                             except: pass
                        ui.label(value).classes(f'text-4xl font-black {val_color} tracking-tight')
                        if title == "Savings Rate":
                            if brain.prev_total_income > 0:
                                diff = float(value.replace('%','')) - brain.prev_savings_rate
                                icon_trend = "trending_up" if diff > 0 else "trending_down"
                                trend_text = f"{abs(diff):.1f}% vs prev"
                                with ui.row().classes('items-center gap-1 mt-2 bg-white/10 px-2 py-1 rounded-lg w-fit backdrop-blur-sm border border-white/10'):
                                    ui.icon(icon_trend).classes("text-xs text-white"); ui.label(trend_text).classes("text-xs font-medium text-white")
                        elif title == "Total Savings":
                            if brain.prev_total_income > 0 and brain.prev_total_net != 0:
                                diff = brain.total_net - brain.prev_total_net
                                pct_change = (diff / abs(brain.prev_total_net)) * 100
                                icon_trend = "trending_up" if diff > 0 else "trending_down"
                                trend_text = f"{pct_change:+.1f}% vs prev"
                                with ui.row().classes('items-center gap-1 mt-2 bg-white/10 px-2 py-1 rounded-lg w-fit backdrop-blur-sm border border-white/10'):
                                    ui.icon(icon_trend).classes("text-xs text-white"); ui.label(trend_text).classes("text-xs font-medium text-white")
                        else:
                             with ui.row().classes('items-center gap-1 mt-2 bg-white/10 px-2 py-1 rounded-lg w-fit backdrop-blur-sm border border-white/10'):
                                 ui.label(sub_text).classes('text-xs font-medium text-white')

            sav_rate = (brain.total_net / brain.total_income * 100) if brain.total_income else 0
            kpi_card('Total Income', f"{brain.total_income:,.0f} ₪", "Bank Deposits", "trending_up", "bg-gradient-to-br from-emerald-600 to-teal-900 border-emerald-400")
            kpi_card('Total Expenses', f"{abs(brain.total_expense):,.0f} ₪", "Bank Withdrawals", "trending_down", "bg-gradient-to-br from-rose-600 to-pink-900 border-rose-400")
            kpi_card('Total Savings', f"{brain.total_net:,.0f} ₪", "", "savings", "bg-gradient-to-br from-blue-600 to-indigo-900 border-blue-400")
            kpi_card('Savings Rate', f"{sav_rate:.1f}%", "", "pie_chart", "bg-gradient-to-br from-violet-600 to-purple-900 border-violet-400")

        con_breakdowns.clear()
        with con_breakdowns:
            render_breakdown_card(con_breakdowns, "Income Breakdown", brain.income_breakdown, is_income=True)
            render_breakdown_card(con_breakdowns, "Expense Breakdown", brain.expense_breakdown, is_income=False)

        con_health_summary.clear()
        with con_health_summary:
            with ui.column().classes('p-6 gap-4 border-b border-slate-700'):
                ui.label('Financial Health Summary').classes('text-xl font-bold text-slate-100')
                insights = brain.generate_smart_insights()
                with ui.grid().classes('grid-cols-1 md:grid-cols-3 gap-3 w-full'):
                    for type_tag, title, desc in insights:
                        styles = {"Critical": "bg-red-900/20 border-red-800 text-red-200", "Warning": "bg-orange-900/20 border-orange-800 text-orange-200", "Success": "bg-green-900/20 border-green-800 text-green-200", "Info": "bg-blue-900/20 border-blue-800 text-blue-200"}
                        style = styles.get(type_tag, "bg-slate-700 border-slate-600 text-slate-200")
                        with ui.row().classes(f'w-full p-4 rounded-lg border {style} items-start gap-3'):
                            icon = 'error' if type_tag == 'Critical' else 'check_circle' if type_tag == 'Success' else 'info'
                            ui.icon(icon).classes('text-2xl')
                            with ui.column().classes('gap-1'):
                                ui.label(title).classes('font-bold text-base'); ui.markdown(desc).classes('text-base opacity-80')

        refresh_tx_charts()
        con_tx_cats.clear()
        with con_tx_cats:
            icon_map = {'Groceries': 'shopping_cart', 'Transport': 'directions_car', 'Restaurants': 'restaurant', 'Shopping': 'shopping_bag', 'Health': 'medical_services', 'Entertainment': 'movie', 'Home': 'home', 'Pets': 'pets', 'Education': 'school', 'Communication': 'wifi', 'Electronics': 'computer', 'Travel': 'flight', 'AI': 'smart_toy', 'Subscription': 'subscriptions', 'Abroad Orders': 'flight_takeoff', 'Crypto': 'currency_bitcoin', 'Online Orders': 'shopping_cart'}
            colors = ['#3b82f6', '#ef4444', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#14b8a6', '#6366f1']
            with ui.column().classes('w-full gap-3'):
                for i, item in enumerate(brain.cc_breakdown):
                    c_color = colors[i % len(colors)]
                    icon = icon_map.get(item['category'], 'category')
                    with ui.row().classes('w-full justify-between items-center p-3 bg-slate-700/50 rounded-lg hover:bg-slate-700 transition cursor-pointer').on('click', lambda e, c=item['category']: set_category_filter(c)):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes('flex items-center justify-center w-8 h-8 rounded-full').style(f'background-color: {c_color}20; color: {c_color}'):
                                ui.icon(icon).classes('text-sm')
                            with ui.column().classes('gap-0'):
                                ui.label(item['category']).classes('font-medium text-base text-slate-100')
                        with ui.column().classes('gap-0 items-end'):
                            ui.label(f"₪{item['amount']:,.0f}").classes('font-bold text-base text-slate-100')
                            ui.label(f"{item['pct']:.1f}%").classes('text-sm text-slate-400')

        cat_select.options = brain.available_categories
        if not cat_select.value: cat_select.value = 'All Categories'
        render_transactions_list(con_tx_list, search_input.value, cat_select.value)
        refresh_top_expenses_widget(brain.active_cc_df)
        refresh_analytics()

    def get_analytics_data():
        df = brain.analytics_df.copy()
        if df.empty: return None
        df['Sort_Key'] = df['Year_Str'].astype(int) * 100 + df['Month_Num']
        monthly = df.groupby(['Year_Str', 'Month_Str', 'Sort_Key']).agg({'Net': 'sum'}).reset_index().sort_values('Sort_Key')
        monthly_data, months_labels = [], []
        for _, row in monthly.iterrows():
            m_year, m_name = row['Year_Str'], row['Month_Str']
            sub_df = df[(df['Year_Str'] == m_year) & (df['Month_Str'] == m_name)]
            inc = float(sub_df[sub_df['Net'] > 0]['Net'].sum())
            exp = float(abs(sub_df[sub_df['Net'] < 0]['Net'].sum()))
            net = inc - exp
            months_labels.append(f"{m_name[:3]} {m_year}")
            monthly_data.append({'income': round(inc, 2), 'expense': round(exp, 2), 'net': round(net, 2)})
        
        cc_data = brain.cc_df.copy()
        if brain.current_year_filter != "All Years": cc_data = cc_data[cc_data['Year_Str'] == brain.current_year_filter]
        if cc_data.empty: cat_labels, cat_values, cat_objs = [], [], []
        else:
             cc_exp = cc_data[cc_data['Net'] < 0]
             cat_df = cc_exp.groupby('Category')['Net'].sum().abs().sort_values(ascending=False)
             cat_labels = [str(x) for x in cat_df.index.tolist()]
             cat_values = [float(round(x, 2)) for x in cat_df.values.tolist()]
             cat_objs = [{'value': v, 'name': k} for k, v in zip(cat_labels, cat_values)]
        return {'months': months_labels, 'data': monthly_data, 'categories': {'labels': cat_labels, 'values': cat_values, 'objects': cat_objs}}

    def refresh_analytics():
        con_analytics.clear()
        data = get_analytics_data()
        with con_analytics:
            if not data:
                ui.label('No bank data available for trends.').classes('w-full text-center mt-10 text-slate-400'); return
            with ui.tabs().classes('text-slate-400 bg-transparent border-b border-slate-700 mb-4') as sub_tabs:
                st_overview = ui.tab('Graphs'); st_cats = ui.tab('Categories'); st_insights = ui.tab('Insights')
            with ui.tab_panels(sub_tabs, value=st_overview).classes('w-full bg-transparent'):
                with ui.tab_panel(st_overview).classes('p-0 grid grid-cols-1 lg:grid-cols-2 gap-6'):
                    with ui.card().classes('p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-96'):
                        ui.label('Income vs Expenses (Bank)').classes('text-xl font-bold text-slate-100')
                        ui.echart({'tooltip': {'trigger': 'axis'}, 'legend': {'data': ['Income', 'Expenses'], 'bottom': 0, 'textStyle': {'color': '#94a3b8'}}, 'xAxis': {'type': 'category', 'data': data['months'], 'axisLabel': {'color': '#94a3b8'}}, 'yAxis': {'type': 'value', 'axisLabel': {'color': '#94a3b8'}}, 'series': [{'name': 'Income', 'type': 'bar', 'data': [x['income'] for x in data['data']], 'itemStyle': {'color': '#10b981'}}, {'name': 'Expenses', 'type': 'bar', 'data': [x['expense'] for x in data['data']], 'itemStyle': {'color': '#ef4444'}}], 'grid': {'left': '3%', 'right': '4%', 'bottom': '10%', 'containLabel': True}}).classes('w-full h-full')
                    with ui.card().classes('p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-96'):
                        ui.label('Net Savings Trend (Bank)').classes('text-xl font-bold text-slate-100')
                        ui.echart({'tooltip': {'trigger': 'axis'}, 'xAxis': {'type': 'category', 'data': data['months'], 'axisLabel': {'color': '#94a3b8'}}, 'yAxis': {'type': 'value', 'axisLabel': {'color': '#94a3b8'}}, 'series': [{'name': 'Net Savings', 'type': 'line', 'smooth': True, 'data': [x['net'] for x in data['data']], 'areaStyle': {'opacity': 0.3}, 'itemStyle': {'color': '#3b82f6'}}], 'grid': {'left': '3%', 'right': '4%', 'bottom': '3%', 'containLabel': True}}).classes('w-full h-full')
                with ui.tab_panel(st_cats).classes('p-0 gap-6'):
                    with ui.card().classes('w-full p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-96'):
                        ui.label('Top 10 Grocery Expenses (All Time)').classes('text-xl font-bold text-slate-100')
                        g_labels, g_values = brain.get_top_grocery_items()
                        if not g_labels: ui.label('No grocery data.').classes('text-slate-400 italic m-auto')
                        else: ui.echart({'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}}, 'grid': {'left': '3%', 'right': '4%', 'bottom': '15%', 'containLabel': True}, 'xAxis': {'type': 'category', 'data': g_labels, 'axisLabel': {'interval': 0, 'rotate': 30, 'fontSize': 12, 'color': '#94a3b8'}}, 'yAxis': {'type': 'value', 'axisLabel': {'color': '#94a3b8'}}, 'series': [{'name': 'Total Spent', 'type': 'bar', 'data': g_values, 'itemStyle': {'color': '#10b981', 'borderRadius': [5, 5, 0, 0]}}]}).classes('w-full h-full')
                    ui.label('Year-over-Year Comparisons (Bank + CC)').classes('text-xl font-bold text-slate-100 mt-6 mb-2')
                    with ui.column().classes('w-full gap-6'): 
                        if not brain.master_df.empty:
                             targets = sorted(brain.master_df['Category'].dropna().unique().tolist())
                             if "Other" in targets: targets.remove("Other"); targets.append("Other")
                        else: targets = []
                        with ui.grid().classes('grid-cols-1 md:grid-cols-2 gap-6 w-full'):
                            months_x = calendar.month_abbr[1:]
                            for cat in targets:
                                series = brain.get_yoy_series(cat)
                                if not series: continue 
                                with ui.card().classes('p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-80'):
                                    ui.label(f'{cat} Trends').classes('text-xl font-bold text-slate-100')
                                    ui.echart({'tooltip': {'trigger': 'axis', 'axisPointer': {'type': 'shadow'}}, 'legend': {'bottom': 0, 'textStyle': {'color': '#94a3b8'}}, 'xAxis': {'type': 'category', 'data': months_x, 'axisLabel': {'color': '#94a3b8'}}, 'yAxis': {'type': 'value', 'axisLabel': {'color': '#94a3b8'}}, 'grid': {'left': '3%', 'right': '4%', 'bottom': '10%', 'containLabel': True}, 'series': series}).classes('w-full h-full')
                with ui.tab_panel(st_insights).classes('p-0'):
                     insights = brain.generate_smart_insights()
                     with ui.grid().classes('grid-cols-1 md:grid-cols-2 gap-3 w-full'):
                        for type_tag, title, desc in insights:
                            styles = {"Critical": "bg-red-900/20 border-red-800 text-red-200", "Warning": "bg-orange-900/20 border-orange-800 text-orange-200", "Success": "bg-green-900/20 border-green-800 text-green-200", "Info": "bg-blue-900/20 border-blue-800 text-blue-200"}
                            style = styles.get(type_tag, "bg-slate-700")
                            with ui.row().classes(f'w-full p-4 rounded-lg border {style} items-start gap-3'):
                                icon = 'error' if type_tag == 'Critical' else 'check_circle' if type_tag == 'Success' else 'info'
                                ui.icon(icon).classes('text-2xl')
                                with ui.column().classes('gap-1'):
                                    ui.label(title).classes('font-bold text-base'); ui.markdown(desc).classes('text-base opacity-90')

    def startup():
        status = brain.load_folder(config.DATA_FOLDER)
        if "Error" in status:
            ui.notify(status, type='negative')
        else:
            update_options()
            refresh_ui()
            ui.notify(status, type='positive')

    startup()

ui.run(title='Finance Dashboard')