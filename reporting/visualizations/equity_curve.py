# reporting/visualizations/equity_curve.py
"""
Plotting function for the Equity Curve chart.
"""
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any

def plot_equity_curve(ax1, analysis_result: Dict[str, Any]):
    """
    Plots the equity curve on a single provided axis.

    Args:
        ax1: Matplotlib axis for the main equity curve.
        analysis_result (Dict[str, Any]): The portfolio analysis results.
    """
    daily_df = analysis_result['raw_data']['daily_returns_df'].copy()
    sol_rates = analysis_result['raw_data']['sol_rates']
    cost_summary = analysis_result['infrastructure_cost_impact']
    daily_cost_usd = cost_summary['daily_cost_usd']

    # Prepare data
    daily_df['daily_cost_sol'] = 0.0
    daily_df['cumulative_pnl_usdc'] = 0.0

    # Calculate daily costs first
    for idx, row in daily_df.iterrows():
        date_str = row['date'].strftime("%Y-%m-%d")
        sol_price = sol_rates.get(date_str)
        if sol_price and sol_price > 0:
            daily_df.loc[idx, 'daily_cost_sol'] = daily_cost_usd / sol_price
            daily_df.loc[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_price

    # Correctly calculate cumulative cost and net PnL
    daily_df['cumulative_cost_sol'] = daily_df['daily_cost_sol'].cumsum()
    daily_df['net_pnl_sol'] = daily_df['cumulative_pnl_sol'] - daily_df['cumulative_cost_sol']

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