"""
Plotting function for the Drawdown Analysis chart.
"""
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from typing import Dict, Any

def plot_drawdown_analysis(ax1, ax2, analysis_result: Dict[str, Any]):
    """
    Plots the drawdown analysis chart on the provided axes.

    Args:
        ax1: Matplotlib axis for the equity curve with drawdown periods.
        ax2: Matplotlib axis for the drawdown percentage chart.
        analysis_result (Dict[str, Any]): The portfolio analysis results.
    """
    daily_df = analysis_result['raw_data']['daily_returns_df'].copy()
    
    # Calculate drawdown
    cumulative = daily_df['cumulative_pnl_sol']
    running_max = cumulative.expanding().max()
    drawdown = (cumulative - running_max) / running_max.abs().replace(0, 1) * 100

    # Equity curve with peaks highlighted
    ax1.plot(daily_df['date'], cumulative, linewidth=2, color='#004E89', label='Cumulative PnL')
    ax1.plot(daily_df['date'], running_max, linewidth=1, color='#FF6B35', linestyle='--', alpha=0.7, label='Running Maximum')
    ax1.fill_between(daily_df['date'], cumulative, running_max, where=(cumulative < running_max), color='red', alpha=0.2, interpolate=True, label='Drawdown Periods')
    ax1.set_title('Portfolio Drawdown Analysis', fontsize=16, fontweight='bold')
    ax1.set_ylabel('Cumulative PnL (SOL)', fontsize=12)
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Drawdown percentage chart
    ax2.fill_between(daily_df['date'], drawdown, 0, where=(drawdown < 0), color='red', alpha=0.6, interpolate=True)
    ax2.plot(daily_df['date'], drawdown, linewidth=1, color='darkred')

    # Highlight maximum drawdown
    if not drawdown.empty:
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        max_dd_date = daily_df.loc[max_dd_idx, 'date']
        ax2.scatter(max_dd_date, max_dd_value, color='red', s=100, zorder=5)
        ax2.annotate(f'Max DD: {max_dd_value:.1f}%', xy=(max_dd_date, max_dd_value), xytext=(10, -20), textcoords='offset points', fontsize=10, fontweight='bold', bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))

    ax2.set_title('Drawdown Percentage', fontsize=12)
    ax2.set_ylabel('Drawdown (%)', fontsize=10)
    ax2.set_xlabel('Date', fontsize=10)
    ax2.grid(True, alpha=0.3)
    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)

    # Format dates
    for ax in [ax1, ax2]:
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax.xaxis.set_major_locator(mdates.WeekdayLocator())
        plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)