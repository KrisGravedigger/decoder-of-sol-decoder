"""
Text Reporter for Portfolio Analytics

Generates formatted, human-readable text summaries of the portfolio
analysis, including performance metrics and cost impact.
"""

from datetime import datetime
from typing import Dict, Any, Tuple

def generate_text_reports(analysis_result: Dict[str, Any]) -> Tuple[str, str]:
    """
    Generate formatted text reports from analysis results.

    Args:
        analysis_result (Dict[str, Any]): Complete analysis results.

    Returns:
        Tuple[str, str]: (portfolio_summary, infrastructure_impact) report content.
    """
    metadata = analysis_result['analysis_metadata']
    sol = analysis_result['sol_denomination']
    usdc = analysis_result['usdc_denomination']
    currency = analysis_result['currency_comparison']
    costs = analysis_result['infrastructure_cost_impact']

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

INFRASTRUCTURE COST IMPACT:
- Period Cost: ${costs.get('total_cost_usd', 0):,.2f} USD ({metadata.get('analysis_period_days', 0)} days × ${costs.get('daily_cost_usd', 0):.2f})
- Cost as % of Gross PnL: {costs.get('cost_impact_percent', 0):.1f}%
- Break-even Days: {costs.get('break_even_days', 0):.0f} days

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

COST BREAKDOWN:
- VPS Hosting: $50.00/month
- RPC Endpoints: $100.00/month
- Bot Subscription: $200.00/month
- Monthly Total: ${monthly_total_cost:,.2f} USD

PERFORMANCE IMPACT:
- Gross PnL (SOL): {costs.get('gross_pnl_sol', 0):+.3f} SOL
- Infrastructure Costs: -{costs.get('total_cost_sol', 0):.3f} SOL
- Net PnL (SOL): {costs.get('net_pnl_sol', 0):+.3f} SOL
- Cost Impact: {costs.get('cost_impact_percent', 0):.1f}% of gross returns

EFFICIENCY METRICS:
- Break-even Period: {costs.get('break_even_days', 0):.0f} days
- Positions Analyzed: {costs.get('positions_analyzed', 0)}
- Average Cost per Position: ${costs.get('total_cost_usd', 0) / max(costs.get('positions_analyzed', 1), 1):.2f} USD

ROI ANALYSIS:
- Monthly Infrastructure: ${monthly_total_cost:,.2f} USD
- Monthly Net Profit: ${monthly_net_profit_usdc:,.2f} USDC (projected)
- Infrastructure ROI: {infrastructure_roi:.1f}% monthly
"""

    return portfolio_summary, infrastructure_impact