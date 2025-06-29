# reporting/visualizations/equity_curve.py
"""
Plotting function for the Equity Curve chart.
"""
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any

def plot_equity_curve(ax1, ax2, analysis_result: Dict[str, Any]):
    """
    Plots the equity curve and SOL price chart on the provided axes.

    Args:
        ax1: Matplotlib axis for the main equity curve.
        ax2: Matplotlib axis for the SOL price subplot.
        analysis_result (Dict[str, Any]): The portfolio analysis results.
    """
    daily_df = analysis_result['raw_data']['daily_returns_df']
    sol_rates = analysis_result['raw_data']['sol_rates']

    # Prepare data
    daily_df = daily_df.copy()
    cost_summary = analysis_result['infrastructure_cost_impact']
    daily_cost_usd = cost_summary.get('daily_cost_usd', 11.67)
    
    daily_df['cumulative_pnl_usdc'] = 0.0
    cumulative_cost = 0.0
    for idx, row in daily_df.iterrows():
        date_str = row['date'].strftime("%Y-%m-%d")
        if date_str in sol_rates:
            sol_price = sol_rates[date_str]
            daily_df.loc[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_price
            daily_cost_sol = daily_cost_usd / sol_price
            cumulative_cost += daily_cost_sol
            daily_df.loc[idx, 'cumulative_cost_sol'] = cumulative_cost
    
    daily_df['net_pnl_sol'] = daily_df['cumulative_pnl_sol'] - daily_df.get('cumulative_cost_sol', 0)

    # Main equity curve
    ax1.plot(daily_df['date'], daily_df['cumulative_pnl_sol'], label='Gross SOL PnL', linewidth=2, color='#FF6B35')
    ax1.plot(daily_df['date'], daily_df['net_pnl_sol'], label='Net SOL PnL (after costs)', linewidth=2, color='#D2001C', linestyle='-.')

    # Secondary axis for USDC
    ax1_twin = ax1.twinx()
    ax1_twin.plot(daily_df['date'], daily_df['cumulative_pnl_usdc'], label='USDC PnL', linewidth=2, color='#004E89', linestyle='--')

    # Fill area showing cost impact
    ax1.fill_between(daily_df['date'], daily_df['cumulative_pnl_sol'], daily_df['net_pnl_sol'], alpha=0.3, color='red', label='Infrastructure Cost Impact')

    # Formatting
    ax1.set_title('Portfolio Equity Curve - Dual Currency Analysis', fontsize=16, fontweight='bold', pad=20)
    ax1.set_xlabel('Date', fontsize=12)
    ax1.set_ylabel('Cumulative PnL (SOL)', fontsize=12, color='#FF6B35')
    ax1_twin.set_ylabel('Cumulative PnL (USDC)', fontsize=12, color='#004E89')
    ax1.grid(True, alpha=0.3)
    ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
    ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
    plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
    ax1.legend(loc='upper left')
    ax1_twin.legend(loc='upper right')
    ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)

    # SOL price chart subplot
    if sol_rates:
        sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in sol_rates.keys()]
        sol_prices = list(sol_rates.values())
        ax2.plot(sol_dates, sol_prices, color='#7209B7', linewidth=2)
        ax2.set_ylabel('SOL/USDC Price', fontsize=10, color='#7209B7')
        ax2.set_xlabel('Date', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))