"""
This engine is designed as a state machine and a data funnel.
It contains everything loaded from the disk
The user use filters (year/month) to restrict flow
It uses an active dataframe that contains only the data the user currently wants to see
The data from the active dataframe flow into specific UI widgets
"""

import pandas as pd
import config
import data_loader

class FinanceEngine:
    def __init__(self):
        # Keep two copies of the dataframe to avoid re-read files from the hard drive
        # Master Data, the big bucket
        self.master_df = pd.DataFrame()

        # Active view, what the user sees right now. The small bucket
        self.active_df = pd.DataFrame()

        # Filter state of years and months
        self.available_years = ["All Years"]
        self.available_months = ["All Months"]
        self.current_year = "All Years"
        self.current_month = "All Months"

    def load_data(self):
        """The delivery truck. calls the loader to get fresh data from the disk."""
        self.master_df = data_loader.load_data_folder(config.DATA_FOLDER)

        if not self.master_df.empty:
            # unique_years is a sorted list of all years found in the data
            unique_years = sorted(self.master_df["Year"].unique().tolist(), reverse=True)
            # Show all years and unique years in the same dropdown
            self.available_years = ["All Years"] + unique_years

        # Make sure the app starts with an active dataframe instead of seeing blank screen
        self.filter_data("All Years", "All Months")
        return f"Loaded {len(self.master_df)} transactions"
    
    def filter_data(self, year, month):
        """The important function, which updates the active_df based on selected dropdowns."""
        self.current_year = year
        self.current_month = month

        df = self.master_df.copy() # start fresh with a clone

        # We load data from the master dataframe and apply filters,
        # which is stored in the active dataframe

        if df.empty:
            self.active_df = df
            return
        
        if year != "All Years":
            df = df[df["Year"] == year] # apply year filter

            # Update available months for this specific year
            valid_months = df.sort_values("Month_Num")["Month"].unique().tolist()
            self.available_months = ["All Months"] + sorted(self.master_df["Month"].unique().tolist())
        else:
            # Show all possible months
            self.available_months = ["All Months"] + sorted(self.master_df["Month"].unique().tolist())

        if month != "All Months":
            df = df[df["Month"] == month] # apply month filter

        self.active_df = df # save the result

    def get_kpis(self):
        """Calculates the 4 big numbers for the top cards."""
        if self.active_df.empty:
            return 0, 0, 0, 0
        
        # Income = sum of all positive numbers
        total_income = self.active_df[self.active_df["Amount"] > 0]["Amount"].sum()

        # expense = sum of all negative numbers
        total_expense = self.active_df[self.active_df["Amount"] < 0]["Amount"].sum()

        net_savings = total_income - (total_expense *-1)

        savings_rate = 0
        if total_income > 0:
            savings_rate = (net_savings / total_income) * 100

        return total_income, total_expense, net_savings, savings_rate

    def get_category_breakdown(self, type_filter="expense"):
        """
        Returns a sorted list of categories for charts/tables.
        type_filter: 'expense' (negative values) or 'income' (positive values)
        """

        if self.active_df.empty:
            return []
        
        df = self.active_df.copy()

        if type_filter == "expense":
            # Filter for expenses and flip sign to positive for the chart
            # charts hate negative numbers. convert them to positive numbers
            df = df[df["Amount"] < 0]
            df["Abs_Amount"] = df["Amount"].abs()
            total_vol = df["Abs_Amount"].sum()
        else:
            df = df[df["Amount"] > 0]
            df["Abs_Amount"] = df["Amount"]
            total_vol = df["Abs_Amount"].sum()

        if total_vol == 0: return []

        # Group by category and sum
        grouped = df.groupby("Category")["Abs_Amount"].sum().reset_index()
        grouped.sort_values("Abs_Amount", ascending=False, inplace=True)

        breakdown = []
        for _, row in grouped.iterrows():
            pct = (row["Abs_Amount"] / total_vol) * 100
            breakdown.append({
                "category": row["Category"],
                "amount": row["Abs_Amount"],
                "pct": round(pct, 1),
                "icon": config.CATEGORY_ICONS.get(row["Category"], "help")
            })

        return breakdown
    
    def get_monthly_trend(self):
        if self.active_df.empty:
            return [], [], []

        df = self.master_df.copy()
        if self.current_year != "All Years":
            df = df[df['Year'] == self.current_year]

        df['Sort_Key'] = df['Year'].astype(str) + "-" + df['Month_Num'].astype(str).str.zfill(2)
        
        # 1. Income (Sum of positive)
        monthly = df.groupby(['Sort_Key', 'Month', 'Year']).agg({
            'Amount': lambda x: x[x > 0].sum() 
        }).rename(columns={'Amount': 'Income'})
        
        # 2. Expense (FIXED HERE)
        # We use .apply(lambda x: abs(x[x < 0].sum())) to get the POSITIVE sum of negatives
        monthly['Expense'] = df.groupby(['Sort_Key', 'Month', 'Year'])['Amount'].apply(lambda x: abs(x[x < 0].sum()))
        
        # 3. Net Calculation
        # Because Expense is now positive, we SUBTRACT it to find the remaining Net
        monthly['Net'] = monthly['Income'] - monthly['Expense']
        
        monthly = monthly.reset_index().sort_values('Sort_Key')

        labels = [f"{row['Month'][:3]} {row['Year']}" for _, row in monthly.iterrows()]
        income_data = monthly['Income'].tolist()
        expense_data = monthly['Expense'].tolist()
        
        return labels, income_data, expense_data