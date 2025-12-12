from nicegui import ui, app, run
from finance_engine import FinanceEngine
import config

# --- 1. INITIALIZE ENGINE ---
engine = FinanceEngine()

# --- 2. UI DASHBOARD ---
@ui.page('/')
def dashboard():
    # --- STYLING (Preserved Original) ---
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
    
    # --- HELPER: LOGIC TO REFRESH UI ---
    def refresh_ui():
        # 1. Get Data from Engine
        income, expense, net, savings_rate = engine.get_kpis()
        
        # 2. Update Top Cards
        # We assume specific element IDs or clear/fill containers. 
        # Since we use clear() on containers below, we just rebuild them.
        
        con_top_cards.clear()
        with con_top_cards:
            render_kpi_card("Total Net", net, "savings", "blue-500", "Total savings", f"{'+' if net>0 else ''}{net:,.0f} ₪")
            render_kpi_card("Total Income", income, "trending_up", "emerald-500", "Earnings", f"{income:,.0f} ₪")
            render_kpi_card("Total Expenses", expense, "trending_down", "rose-500", "Spending", f"{expense:,.0f} ₪")
            
            # Savings Rate Logic
            color = "emerald-500" if savings_rate >= 20 else "orange-500"
            if savings_rate < 0: color = "rose-500"
            render_kpi_card("Savings Rate", savings_rate, "pie_chart", color, "Target: 20%", f"{savings_rate:.1f}%")

        # 3. Update Breakdowns
        con_breakdowns.clear()
        with con_breakdowns:
            # Income Breakdown
            income_data = engine.get_category_breakdown('income')
            render_breakdown_card("Income Breakdown", income_data, is_income=True)
            
            # Expense Breakdown
            expense_data = engine.get_category_breakdown('expense')
            render_breakdown_card("Expense Breakdown", expense_data, is_income=False)

        # 4. Update Charts
        refresh_charts()

    def refresh_charts():
        # Monthly Trend Chart
        labels, inc_data, exp_data = engine.get_monthly_trend()
        chart_trend.options['xAxis']['data'] = labels
        chart_trend.options['series'][0]['data'] = inc_data
        chart_trend.options['series'][1]['data'] = exp_data
        chart_trend.update()

        # Category Pie Chart (for Transactions Tab)
        exp_breakdown = engine.get_category_breakdown('expense')
        if exp_breakdown:
            chart_cat.options['series'][0]['data'] = [
                {'value': x['amount'], 'name': x['category']} for x in exp_breakdown
            ]
            chart_cat.update()

    # --- HELPER: UI COMPONENTS ---
    def render_kpi_card(title, value, icon, color, sub_text, display_value):
        with ui.card().classes('p-5 rounded-xl border border-slate-700 bg-slate-800 shadow-sm hover:shadow-md transition-shadow'):
            with ui.row().classes('justify-between items-start w-full'):
                with ui.column().classes('gap-1'):
                    ui.label(title).classes('text-slate-400 text-sm font-medium uppercase tracking-wider')
                    ui.label(display_value).classes(f'text-2xl font-bold text-white')
                with ui.element('div').classes(f'p-3 rounded-lg bg-{color}/10 text-{color}'):
                    ui.icon(icon, size='sm')
            ui.label(sub_text).classes(f'text-xs font-medium mt-3 text-{color}')

    def render_breakdown_card(title, items, is_income):
        with ui.card().classes('p-6 rounded-xl border border-slate-700 bg-slate-800 shadow-sm h-full'):
            with ui.row().classes('items-center justify-between w-full mb-6'):
                with ui.row().classes('items-center gap-3'):
                    with ui.element('div').classes(f'w-1 h-6 rounded-full {"bg-emerald-500" if is_income else "bg-rose-500"}'): pass
                    ui.label(title).classes('text-lg font-bold text-slate-100')
                ui.button(icon='more_horiz').props('flat round dense color=grey-6')
            
            with ui.scroll_area().classes('h-64 pr-4'):
                if not items:
                    ui.label("No data available").classes('text-slate-500 italic')
                for item in items:
                    with ui.row().classes('w-full justify-between items-center mb-4 group cursor-pointer hover:bg-slate-700/30 p-2 rounded-lg transition-colors'):
                        with ui.row().classes('items-center gap-3'):
                            with ui.element('div').classes('p-2 rounded-lg bg-slate-700 text-slate-300 group-hover:text-white group-hover:bg-blue-500/20 transition-all'):
                                ui.icon(item.get('icon', 'circle'), size='xs') # Use icon from engine
                            with ui.column().classes('gap-0.5'):
                                ui.label(item['category']).classes('font-medium text-slate-200 text-sm')
                                ui.label(f"{item['pct']}%").classes('text-xs text-slate-500')
                        ui.label(f"{item['amount']:,.0f} ₪").classes('font-bold text-slate-200 text-sm')

    # --- LAYOUT CONSTRUCTION ---
    with ui.column().classes('w-full max-w-7xl mx-auto px-4 md:px-6 lg:px-8 py-6'):
        
        # --- HEADER (Preserved) ---
        with ui.card().classes('w-full mb-6 p-6 md:p-8 rounded-xl border border-slate-700 bg-slate-800 shadow-lg'):
            with ui.row().classes('w-full justify-between items-center'):
                with ui.column().classes('gap-1'):
                    ui.label('Your Financial Dashboard').classes('text-3xl font-bold text-slate-100')
                    ui.label('Track your income, expenses, and savings').classes('text-base text-slate-400')
                
                with ui.row().classes('items-center gap-6'):
                    # Year Nav
                    def change_year(val):
                        engine.filter_data(val, sel_month.value)
                        # Update months dropdown based on selected year
                        sel_month.options = engine.available_months
                        if sel_month.value not in engine.available_months:
                            sel_month.value = "All Months"
                        refresh_ui()

                    def nav_year(direction):
                        years = engine.available_years
                        if not years: return
                        try:
                            idx = years.index(sel_year.value)
                            new_idx = (idx - direction) % len(years) 
                            sel_year.value = years[new_idx] # Triggers change_year automatically
                        except: pass

                    with ui.row().classes('items-center bg-slate-700 rounded-lg p-1 border border-slate-600 gap-1'):
                        ui.button(icon='chevron_left', on_click=lambda: nav_year(-1)).props('flat dense color=grey-4')
                        sel_year = ui.select(engine.available_years, value=engine.current_year, on_change=lambda e: change_year(e.value)).props('standout="bg-grey-9 text-white" dense options-dense borderless').classes('text-lg font-bold text-white w-28 text-center')
                        ui.button(icon='chevron_right', on_click=lambda: nav_year(1)).props('flat dense color=grey-4')

                    # Month Nav
                    def change_month(val):
                        engine.filter_data(sel_year.value, val)
                        refresh_ui()

                    def nav_month(direction):
                        months = engine.available_months
                        if not months: return
                        try:
                            idx = months.index(sel_month.value)
                            new_idx = (idx + direction) % len(months)
                            sel_month.value = months[new_idx] # Triggers change_month
                        except: pass

                    with ui.row().classes('items-center bg-slate-700 rounded-lg p-1 border border-slate-600 gap-1'):
                        ui.button(icon='chevron_left', on_click=lambda: nav_month(-1)).props('flat dense color=grey-4')
                        sel_month = ui.select(engine.available_months, value=engine.current_month, on_change=lambda e: change_month(e.value)).props('standout="bg-grey-9 text-white" dense options-dense borderless').classes('text-sm text-slate-400 w-28 text-center')
                        ui.button(icon='chevron_right', on_click=lambda: nav_month(1)).props('flat dense color=grey-4')

                    # Refresh Button
                    async def reload_data():
                        ui.notify("Refreshing data...")
                        msg = await app.loop.run_in_executor(None, engine.load_data)
                        ui.notify(msg)
                        sel_year.options = engine.available_years
                        sel_year.value = engine.current_year
                        refresh_ui()
                        
                    ui.button(icon='refresh', on_click=reload_data).classes('bg-slate-700 text-slate-300 border border-slate-600 hover:bg-slate-600 shadow-sm w-10 h-10 p-0 ml-2')

                    # User Avatar (Preserved)
                    with ui.row().classes('items-center gap-3 border-l border-slate-600 pl-6'):
                         with ui.avatar().classes('bg-gradient-to-r from-purple-600 to-indigo-600 text-white font-bold'): ui.label('EM')
                         with ui.column().classes('gap-0'):
                             ui.label('Eran Mani').classes('font-semibold text-slate-200 text-sm')
                             ui.label('Premium Plan').classes('text-xs text-emerald-400')

        # --- TABS ---
        with ui.tabs().classes('bg-transparent mb-6') as tabs:
            tab_overview = ui.tab('Overview')
            tab_transactions = ui.tab('Transactions')

        # --- PANELS ---
        with ui.tab_panels(tabs, value=tab_overview).classes('w-full bg-transparent'):
            
            # 1. OVERVIEW TAB
            with ui.tab_panel(tab_overview).classes('p-0 gap-6'):
                # KPI Grid
                con_top_cards = ui.grid().classes('grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 w-full')
                
                # Breakdown Grid
                con_breakdowns = ui.grid().classes('grid-cols-1 lg:grid-cols-2 gap-6 w-full')

                # Monthly Trend Chart Area
                with ui.card().classes('w-full p-6 rounded-xl border border-slate-700 bg-slate-800 shadow-sm mt-6'):
                    ui.label("Income vs Expense Trend").classes('text-lg font-bold text-slate-100 mb-4')
                    chart_trend = ui.echart({
                        'tooltip': {'trigger': 'axis'},
                        'legend': {'textStyle': {'color': '#94a3b8'}, 'bottom': 0},
                        'grid': {'left': '3%', 'right': '4%', 'bottom': '10%', 'containLabel': True},
                        'xAxis': {'type': 'category', 'data': [], 'axisLine': {'lineStyle': {'color': '#475569'}}},
                        'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'color': '#334155'}}},
                        'series': [
                            {'name': 'Income', 'type': 'bar', 'data': [], 'itemStyle': {'color': '#10b981'}, 'barMaxWidth': 20},
                            {'name': 'Expense', 'type': 'bar', 'data': [], 'itemStyle': {'color': '#ef4444'}, 'barMaxWidth': 20}
                        ]
                    }).classes('h-72 w-full')

            # 2. TRANSACTIONS TAB
            with ui.tab_panel(tab_transactions).classes('p-0 mt-6'):
                with ui.grid().classes('grid-cols-1 lg:grid-cols-3 gap-6 w-full'):
                    # Pie Chart Card
                    with ui.card().classes('lg:col-span-1 p-6 rounded-xl shadow-sm border border-slate-700 bg-slate-800 h-[500px] flex flex-col'):
                        ui.label('Expense Analysis').classes('font-bold text-xl text-slate-100 mb-4')
                        chart_cat = ui.echart({
                            'tooltip': {'trigger': 'item'},
                            'legend': {'top': '5%', 'left': 'center', 'textStyle': {'color': '#94a3b8'}},
                            'series': [{
                                'name': 'Category',
                                'type': 'pie',
                                'radius': ['40%', '70%'],
                                'avoidLabelOverlap': False,
                                'itemStyle': {'borderRadius': 10, 'borderColor': '#1e293b', 'borderWidth': 2},
                                'label': {'show': False, 'position': 'center'},
                                'emphasis': {'label': {'show': True, 'fontSize': 20, 'fontWeight': 'bold', 'color': 'white'}},
                                'data': []
                            }]
                        }).classes('h-full w-full')

    # --- STARTUP ---
    # 1. Load Data
    if engine.master_df.empty:
        engine.load_data()
    
    # 2. Init Dropdowns
    sel_year.options = engine.available_years
    sel_year.value = engine.current_year
    sel_month.options = engine.available_months
    sel_month.value = engine.current_month
    
    # 3. Draw UI
    refresh_ui()

# --- RUN ---
ui.run(title="Finance Dashboard", dark=True)