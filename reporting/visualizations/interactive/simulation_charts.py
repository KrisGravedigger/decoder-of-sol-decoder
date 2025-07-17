"""
Generates interactive charts related to "what-if" simulations.

Includes:
- Weekend parameter impact comparison.
- Weekend position opening distribution.
- Spot vs. Bid-Ask strategy PnL comparison.
"""
import logging
from typing import Dict, Any, List, Optional

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo

logger = logging.getLogger(__name__)


def create_weekend_comparison_chart(weekend_analysis: Dict[str, Any]) -> str:
    """Create weekend parameter comparison chart."""
    try:
        if (not weekend_analysis or 
            weekend_analysis.get('analysis_skipped') or 
            'performance_comparison' not in weekend_analysis):
            reason = weekend_analysis.get('reason', 'no valid data found') if weekend_analysis else 'no data'
            return f"<p>Weekend analysis was skipped: {reason}</p>"
            
        comparison = weekend_analysis['performance_comparison']
        
        current = comparison.get('current_scenario', {}).get('metrics', {})
        alternative = comparison.get('alternative_scenario', {}).get('metrics', {})
        
        metrics = ['Total PnL', 'Average ROI (%)']
        current_values = [
            current.get('total_pnl', 0), 
            current.get('average_roi', 0) * 100
        ]
        alternative_values = [
            alternative.get('total_pnl', 0), 
            alternative.get('average_roi', 0) * 100
        ]
        
        current_name = comparison.get('current_scenario', {}).get('name', 'Current')
        alternative_name = comparison.get('alternative_scenario', {}).get('name', 'Alternative')
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name=current_name, x=metrics, y=current_values, marker_color='#FF6B35', hovertemplate='%{x}<br>' + current_name + ': %{y:.3f}<extra></extra>'))
        fig.add_trace(go.Bar(name=alternative_name, x=metrics, y=alternative_values, marker_color='#004E89', hovertemplate='%{x}<br>' + alternative_name + ': %{y:.3f}<extra></extra>'))
        
        fig.update_layout(title="Weekend Parameter Impact Comparison", xaxis_title="Metrics", yaxis_title="Value", barmode='group', template='plotly_white', height=500)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create weekend comparison chart: {e}", exc_info=True)
        return f"<p>Error creating weekend comparison chart: {str(e)}</p>"


def create_weekend_distribution_chart(weekend_analysis: Dict[str, Any]) -> str:
    """Create weekend position distribution chart."""
    try:
        if weekend_analysis.get('analysis_skipped'):
            return f"<p>Weekend analysis was skipped: {weekend_analysis.get('reason', 'unknown reason')}</p>"
        if 'error' in weekend_analysis or not weekend_analysis.get('is_valid'):
            return f"<p>Weekend analysis error: {weekend_analysis.get('error', 'invalid data')}</p>"
            
        classification = weekend_analysis.get('position_classification', {})
        
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=['Weekend Opened', 'Weekday Opened'], 
            values=[
                classification.get('weekend_opened', {}).get('count', 0), 
                classification.get('weekday_opened', {}).get('count', 0)
            ], 
            hole=0.3, 
            marker_colors=['#FF6B35', '#004E89'], 
            hovertemplate='%{label}<br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        ))
        fig.update_layout(title="Position Opening Distribution", template='plotly_white', height=400)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create weekend distribution chart: {e}", exc_info=True)
        return f"<p>Error creating weekend distribution chart: {str(e)}</p>"


def create_strategy_simulation_chart(simulation_results: Optional[List[Dict]], portfolio_analysis: Dict[str, Any]) -> str:
    """Create a bar chart comparing total PnL from different strategies."""
    try:
        if not simulation_results:
            return "<div class='skipped'>No simulation results available.</div>"

        sim_pnl = {}
        for res in simulation_results:
            if not res or 'simulation_results' not in res: continue
            for name, data in res['simulation_results'].items():
                if 'pnl_sol' in data:
                    sim_pnl[name] = sim_pnl.get(name, 0) + data['pnl_sol']

        cost_impact_data = portfolio_analysis.get('infrastructure_cost_impact', {})
        sol_data = portfolio_analysis.get('sol_denomination', {})
        
        if 'gross_pnl_sol' in cost_impact_data:
            actual_pnl = cost_impact_data['gross_pnl_sol']
        elif 'total_pnl_sol' in sol_data:
            actual_pnl = sol_data['total_pnl_sol']
            logger.info("Using total_pnl_sol as fallback for gross_pnl_sol")
        else:
            logger.warning("No suitable PnL metric found in portfolio analysis")
            return "<div class='skipped'>Portfolio analysis data incomplete - cannot create strategy comparison chart.</div>"

        strategy_names = list(sim_pnl.keys()) + ['Actual (from Log)']
        pnl_values = list(sim_pnl.values()) + [actual_pnl]
        
        df = pd.DataFrame({'Strategy': strategy_names, 'Total PnL (SOL)': pnl_values})
        df = df.sort_values('Total PnL (SOL)', ascending=False)
        
        fig = px.bar(df, x='Strategy', y='Total PnL (SOL)', color='Strategy',
                     color_discrete_map={'Actual (from Log)': '#7f8c8d'},
                     title='Aggregated PnL: Actual vs. Simulated Strategies',
                     labels={'Total PnL (SOL)': 'Total PnL (SOL)'})
        
        fig.update_layout(template='plotly_white', height=500, showlegend=False)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)

    except Exception as e:
        logger.error(f"Failed to create strategy simulation chart: {e}", exc_info=True)
        return f"<p>Error creating strategy simulation chart: {str(e)}</p>"