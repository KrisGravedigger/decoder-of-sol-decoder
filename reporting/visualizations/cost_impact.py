"""
Plotting function for the Infrastructure Cost Impact chart.
"""
import numpy as np
from typing import Dict, Any

def plot_cost_impact(fig, axes, analysis_result: Dict[str, Any]):
    """
    Plots the infrastructure cost impact analysis on the provided axes.

    Args:
        fig: Matplotlib figure object.
        axes: A 2x2 grid of Matplotlib axes.
        analysis_result (Dict[str, Any]): The portfolio analysis results.
    """
    sol_metrics = analysis_result['sol_denomination']
    usdc_metrics = analysis_result['usdc_denomination']
    cost_summary = analysis_result['infrastructure_cost_impact']
    ax1, ax2, ax3, ax4 = axes.flatten()
    fig.suptitle('Infrastructure Cost Impact Analysis', fontsize=16, fontweight='bold')

    # 1. Gross vs Net PnL Comparison
    categories = ['SOL Denomination', 'USDC Denomination']
    gross_pnl = [sol_metrics.get('total_pnl_sol', 0) + cost_summary.get('total_cost_sol', 0), usdc_metrics.get('total_pnl_usdc', 0) + cost_summary.get('total_cost_usd', 0)]
    net_pnl = [sol_metrics.get('net_pnl_after_costs', 0), usdc_metrics.get('net_pnl_after_costs', 0)]
    x = np.arange(len(categories))
    width = 0.35
    bars1 = ax1.bar(x - width/2, gross_pnl, width, label='Gross PnL', color='#004E89', alpha=0.8)
    bars2 = ax1.bar(x + width/2, net_pnl, width, label='Net PnL', color='#FF6B35', alpha=0.8)
    ax1.set_title('Gross vs Net PnL Comparison', fontsize=12, fontweight='bold')
    ax1.set_ylabel('PnL Amount', fontsize=10)
    ax1.set_xticks(x)
    ax1.set_xticklabels(categories)
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    for bar in bars1 + bars2:
        height = bar.get_height()
        ax1.annotate(f'{height:.2f}', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    # 2. Cost Impact Percentage
    cost_impact_sol = cost_summary.get('cost_impact_percent', 0)
    cost_impact_usdc = 0
    gross_usdc = gross_pnl[1]
    if gross_usdc != 0:
        cost_impact_usdc = (cost_summary.get('total_cost_usd', 0) / abs(gross_usdc)) * 100
    impact_percentages = [cost_impact_sol, cost_impact_usdc]
    bars3 = ax2.bar(categories, impact_percentages, color=['#7209B7', '#A663CC'], alpha=0.8)
    ax2.set_title('Cost Impact (% of Gross PnL)', fontsize=12, fontweight='bold')
    ax2.set_ylabel('Cost Impact (%)', fontsize=10)
    ax2.grid(True, alpha=0.3)
    for bar in bars3:
        height = bar.get_height()
        ax2.annotate(f'{height:.1f}%', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=10, fontweight='bold')

    # 3. Daily Cost Allocation
    period_days = cost_summary.get('period_days', 1)
    daily_costs = [cost_summary.get('total_cost_sol', 0) / period_days, cost_summary.get('total_cost_usd', 0) / period_days]
    bars4 = ax3.bar(categories, daily_costs, color=['#FF6B35', '#004E89'], alpha=0.6)
    ax3.set_title('Daily Infrastructure Cost', fontsize=12, fontweight='bold')
    ax3.set_ylabel('Daily Cost', fontsize=10)
    ax3.grid(True, alpha=0.3)
    for bar in bars4:
        height = bar.get_height()
        ax3.annotate(f'{height:.3f}', xy=(bar.get_x() + bar.get_width() / 2, height), xytext=(0, 3), textcoords="offset points", ha='center', va='bottom', fontsize=9)

    # 4. Break-even Analysis
    break_even_days = cost_summary.get('break_even_days', 0)
    analysis_days = cost_summary.get('period_days', 0)
    if gross_pnl[0] > 0 and 0 < break_even_days < analysis_days:
        sizes = [break_even_days, analysis_days - break_even_days]
        labels = [f'Break-even\n({break_even_days:.0f} days)', f'Profitable\n({analysis_days - break_even_days:.0f} days)']
        colors = ['#FF6B35', '#004E89']
        ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
        ax4.set_title(f'Break-even Analysis (Total: {analysis_days} days)', fontsize=12, fontweight='bold')
    else:
        ax4.text(0.5, 0.5, f'Break-even: {break_even_days:.0f} days\nAnalysis: {analysis_days} days', ha='center', va='center', transform=ax4.transAxes, fontsize=12)
        ax4.set_title('Break-even Analysis', fontsize=12, fontweight='bold')