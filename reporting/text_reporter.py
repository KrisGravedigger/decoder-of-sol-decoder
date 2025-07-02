"""
Text Reporter for Portfolio Analytics

Generates formatted, human-readable text summaries of the portfolio
analysis, including performance metrics, cost impact, and simulation results.
"""

from datetime import datetime
from typing import Dict, Any, Tuple, Optional

def generate_portfolio_and_cost_reports(analysis_result: Dict[str, Any]) -> Tuple[str, str]:
    """
    Generate portfolio summary and infrastructure impact reports.
    This function replaces the old generate_text_reports.

    Args:
        analysis_result (Dict[str, Any]): Portfolio analysis results.

    Returns:
        Tuple[str, str]: (portfolio_summary, infrastructure_impact) report content.
    """
    metadata = analysis_result.get('analysis_metadata', {})
    sol = analysis_result.get('sol_denomination', {})
    usdc = analysis_result.get('usdc_denomination', {})
    currency = analysis_result.get('currency_comparison', {})
    costs = analysis_result.get('infrastructure_cost_impact', {})

    portfolio_summary = f"""=== PORTFOLIO ANALYTICS REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Period: {metadata.get('analysis_period_days', 0)} days ({metadata.get('start_date')} to {metadata.get('end_date')})

SOL DENOMINATION ANALYSIS:
- Total PnL: {sol.get('total_pnl_sol', 0):+.2f} SOL
- Sharpe Ratio: {sol.get('sharpe_ratio', 0):.2f}
- Max Drawdown: {sol.get('max_drawdown_percent', 0):.1f}%
- Win Rate: {sol.get('win_rate', 0)*100:.1f}% ({int(sol.get('win_rate', 0)*sol.get('total_positions', 0))}/{sol.get('total_positions', 0)} positions)
- Profit Factor: {sol.get('profit_factor', 0):.2f}
- Net PnL After Costs: {sol.get('net_pnl_after_costs', 0):+.2f} SOL

USDC DENOMINATION ANALYSIS:
- Total PnL: {usdc.get('total_pnl_usdc', 0):+,.2f} USDC
- Sharpe Ratio: {usdc.get('sharpe_ratio', 0):.2f}
- Max Drawdown: {usdc.get('max_drawdown_percent', 0):.1f}%
- Net PnL After Costs: {usdc.get('net_pnl_after_costs', 0):+,.2f} USDC

CURRENCY COMPARISON:
- SOL Price Change: {currency.get('sol_price_change_period', 0):+.1f}%
- LP vs HODL Outperformance: {currency.get('outperformance_vs_hodl', 0):+.1f}%
- Preferred Denomination: {currency.get('preferred_denomination', 'N/A')}
"""

    monthly_net_profit_usdc = 0
    if metadata.get('analysis_period_days', 0) > 0:
        monthly_net_profit_usdc = usdc.get('net_pnl_after_costs', 0) * 30 / metadata['analysis_period_days']

    infrastructure_roi = 0
    monthly_total_cost = costs.get('daily_cost_usd', 0) * 30
    if monthly_total_cost > 0:
        infrastructure_roi = (monthly_net_profit_usdc / monthly_total_cost) * 100

    infrastructure_impact = f"""=== INFRASTRUCTURE COST ANALYSIS ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COST STRUCTURE:
- Daily Infrastructure Cost: ${costs.get('daily_cost_usd', 0):.2f} USD
- Total Period Cost: ${costs.get('total_cost_usd', 0):,.2f} USD
- Total Period Cost: {costs.get('total_cost_sol', 0):.3f} SOL

PERFORMANCE IMPACT:
- Gross PnL (SOL): {costs.get('gross_pnl_sol', 0):+.3f} SOL
- Infrastructure Costs: -{costs.get('total_cost_sol', 0):.3f} SOL
- Net PnL (SOL): {costs.get('net_pnl_sol', 0):+.3f} SOL
- Cost Impact: {costs.get('cost_impact_percent', 0):.1f}% of gross returns

EFFICIENCY METRICS:
- Break-even Period: {costs.get('break_even_days', 0):.0f} days
- Positions Analyzed: {costs.get('positions_analyzed', 0)}
- Average Cost per Position: ${costs.get('total_cost_usd', 0) / max(costs.get('positions_analyzed', 1), 1):.2f} USD
"""

    return portfolio_summary, infrastructure_impact


def generate_weekend_simulation_report(weekend_analysis: Optional[Dict[str, Any]]) -> Optional[str]:
    """
    Generate a detailed text report for the weekend parameter simulation.

    Args:
        weekend_analysis (Optional[Dict[str, Any]]): The results from WeekendSimulator.

    Returns:
        Optional[str]: A formatted text report, or None if analysis was skipped or failed.
    """
    if not weekend_analysis or weekend_analysis.get('analysis_skipped') or 'error' in weekend_analysis:
        return None

    meta = weekend_analysis.get('analysis_metadata', {})
    classification = weekend_analysis.get('position_classification', {})
    comparison = weekend_analysis.get('performance_comparison', {})
    recommendations = weekend_analysis.get('recommendations', {})
    
    if not all([meta, classification, comparison, recommendations]):
        return "Weekend analysis data is incomplete."
        
    current_scenario = comparison.get('current_scenario', {})
    alternative_scenario = comparison.get('alternative_scenario', {})
    impact = comparison.get('impact_analysis', {})

    summary = [
        "=== WEEKEND PARAMETER SIMULATION REPORT ===",
        f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        
        "--- CONFIGURATION ---",
        f"Weekend Parameter: {'ENABLED' if meta.get('weekend_size_reduction', 0) else 'DISABLED'}",
        f"Size Reduction: {meta.get('size_reduction_percentage', 0)}%",
        f"Size Multiplier: {meta.get('size_multiplier', 1.0):.2f}x\n",

        "--- POSITION CLASSIFICATION ---",
        f"Total Positions Analyzed: {meta.get('total_positions', 0)}",
        f"Weekend-Opened Positions: {classification.get('weekend_opened', {}).get('count', 0)} ({classification.get('weekend_opened', {}).get('percentage', 0):.1f}%)",
        f"Weekday-Opened Positions: {classification.get('weekday_opened', {}).get('count', 0)} ({classification.get('weekday_opened', {}).get('percentage', 0):.1f}%)\n",

        "--- SCENARIO COMPARISON ---",
        f"CURRENT SCENARIO: {current_scenario.get('name', 'N/A')}",
        f"  - Total PnL: {current_scenario.get('metrics', {}).get('total_pnl', 0):+.3f} SOL",
        f"  - Average ROI: {current_scenario.get('metrics', {}).get('average_roi', 0)*100:+.2f}%",
        f"  - Sharpe Ratio: {current_scenario.get('metrics', {}).get('sharpe_ratio', 0):.3f}\n",

        f"ALTERNATIVE SCENARIO: {alternative_scenario.get('name', 'N/A')}",
        f"  - Total PnL: {alternative_scenario.get('metrics', {}).get('total_pnl', 0):+.3f} SOL",
        f"  - Average ROI: {alternative_scenario.get('metrics', {}).get('average_roi', 0)*100:+.2f}%",
        f"  - Sharpe Ratio: {alternative_scenario.get('metrics', {}).get('sharpe_ratio', 0):.3f}\n",

        "--- IMPACT ANALYSIS (Alternative vs. Current) ---",
        f"PnL Difference: {impact.get('total_pnl_difference_sol', 0):+.3f} SOL ({impact.get('pnl_improvement_percent', 0):+.1f}%)",
        f"ROI Difference: {impact.get('roi_difference', 0)*100:+.2f}%",
        f"Sharpe Difference: {impact.get('sharpe_difference', 0):+.3f}\n",

        "--- RECOMMENDATION ---",
        f"Primary Recommendation: {recommendations.get('primary_recommendation', 'N/A')}",
        f"Confidence Level: {recommendations.get('confidence_level', 'N/A')}",
        f"Justification: {recommendations.get('explanation', 'N/A')}"
    ]
    
    return "\n".join(summary)