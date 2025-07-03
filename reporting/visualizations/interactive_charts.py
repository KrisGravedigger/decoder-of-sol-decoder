"""
Interactive Chart Generation for HTML Reports

Provides functions to create Plotly-based interactive charts for the
comprehensive HTML report.
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
import os
import re

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)

def create_equity_curve_chart(portfolio_analysis: Dict[str, Any]) -> str:
    """Create interactive equity curve chart."""
    try:
        daily_df = portfolio_analysis['raw_data']['daily_returns_df']
        sol_rates = portfolio_analysis['raw_data']['sol_rates']
        fallback_price = 150.0
        
        if daily_df.empty:
            return "<p>No daily data available for equity curve</p>"
            
        daily_df = daily_df.copy()
        daily_df['cumulative_pnl_usdc'] = 0.0
        for idx, row in daily_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            # AIDEV-NOTE-CLAUDE: Fix for TypeError. Handle None values from sol_rates.
            rate = sol_rates.get(date_str)
            price_to_use = rate if rate is not None else fallback_price
            daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * price_to_use
                
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Portfolio Equity Curve', 'SOL Price'),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": True}], [{}]]
        )
        
        fig.add_trace(go.Scatter(x=daily_df['date'], y=daily_df['cumulative_pnl_sol'], name='SOL PnL', line=dict(color='#FF6B35', width=3), hovertemplate='Date: %{x}<br>SOL PnL: %{y:.3f}<extra></extra>'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily_df['date'], y=daily_df['cumulative_pnl_usdc'], name='USDC PnL', line=dict(color='#004E89', width=2, dash='dash'), yaxis='y2', hovertemplate='Date: %{x}<br>USDC PnL: $%{y:.2f}<extra></extra>'), row=1, col=1)
        
        valid_sol_rates = {k: v for k, v in sol_rates.items() if v is not None}
        if valid_sol_rates:
            sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in valid_sol_rates.keys()]
            sol_prices = list(valid_sol_rates.values())
            fig.add_trace(go.Scatter(x=sol_dates, y=sol_prices, name='SOL/USDC Price', line=dict(color='#7209B7', width=2), hovertemplate='Date: %{x}<br>SOL Price: $%{y:.2f}<extra></extra>'), row=2, col=1)
            
        fig.update_layout(title=dict(text="Portfolio Performance - Dual Currency Analysis", font=dict(size=20, color='#2E3440')), height=700, showlegend=True, template='plotly_white', hovermode='x unified')
        fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
        fig.update_yaxes(title_text="Cumulative PnL (USDC)", secondary_y=True, row=1, col=1)
        fig.update_yaxes(title_text="SOL Price (USDC)", row=2, col=1)
        fig.update_xaxes(title_text="Date", row=2, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create equity curve chart: {e}", exc_info=True)
        return f"<p>Error creating equity curve chart: {str(e)}</p>"

def create_metrics_summary_chart(portfolio_analysis: Dict[str, Any]) -> str:
    """Create metrics summary visualization as a table for clarity."""
    try:
        sol_metrics = portfolio_analysis['sol_denomination']
        usdc_metrics = portfolio_analysis['usdc_denomination']
        
        # AIDEV-NOTE-CLAUDE: Fix for KeyError by accessing keys that are guaranteed to exist.
        header = ['Metric', 'SOL Denomination', 'USDC Denomination']
        cells = [
            ['Total PnL', f"{sol_metrics.get('total_pnl_sol', 0):.3f} SOL", f"${usdc_metrics.get('total_pnl_usdc', 0):.2f}"],
            ['Net PnL (after costs)', f"{sol_metrics.get('net_pnl_after_costs', 0):.3f} SOL", f"${usdc_metrics.get('net_pnl_after_costs', 0):.2f}"],
            ['Win Rate', f"{sol_metrics.get('win_rate', 0):.1%}", f"{usdc_metrics.get('win_rate', 0):.1%}"],
            ['Sharpe Ratio', f"{sol_metrics.get('sharpe_ratio', 0):.2f}", f"{usdc_metrics.get('sharpe_ratio', 0):.2f}"],
            ['Max Drawdown', f"{sol_metrics.get('max_drawdown_percent', 0):.2%}", f"{usdc_metrics.get('max_drawdown_percent', 0):.2%}"],
            ['Cost Impact', f"{sol_metrics.get('cost_impact_percent', 0):.1f}%", f"{usdc_metrics.get('cost_impact_percent', 0):.1f}%"],
        ]

        cells_transposed = list(map(list, zip(*cells)))
        
        fig = go.Figure(data=[go.Table(
            header=dict(values=header,
                        fill_color='#2c3e50',
                        align='left',
                        font=dict(color='white', size=14)),
            cells=dict(values=cells_transposed,
                       fill_color='#ecf0f1',
                       align='left',
                       font=dict(size=12, color='#2c3e50'),
                       height=30)
        )])
        
        fig.update_layout(title="Key Performance Indicators", height=300, margin=dict(l=10, r=10, t=50, b=10))
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create metrics summary chart: {e}", exc_info=True)
        return f"<p>Error creating metrics chart: {str(e)}</p>"


def create_correlation_chart(correlation_analysis: Dict[str, Any]) -> str:
    """Create market correlation visualization."""
    try:
        corr_metrics = correlation_analysis.get('correlation_metrics', {})
        if not correlation_analysis or correlation_analysis.get('error') or corr_metrics.get('error'):
            return "" 

        raw_data = correlation_analysis.get('raw_data', {})
        portfolio_daily = raw_data.get('portfolio_daily_returns')
        sol_daily = raw_data.get('sol_daily_data')

        if portfolio_daily is None or sol_daily is None or portfolio_daily.empty or sol_daily.empty:
            return "<div class='skipped'>Insufficient raw data for correlation chart.</div>"
            
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        if len(common_dates) < 2:
            return "<div class='skipped'>Insufficient common dates for correlation chart.</div>"
            
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sol_aligned, y=portfolio_aligned, mode='markers', name='Daily Returns', marker=dict(size=8, color=portfolio_aligned, colorscale='RdYlGn', showscale=True, colorbar=dict(title="Portfolio Return")), hovertemplate='SOL Return: %{x:.2%}<br>Portfolio Return: %{y:.3f} SOL<extra></extra>'))
        
        if len(sol_aligned.dropna()) > 1:
            z = np.polyfit(sol_aligned, portfolio_aligned, 1)
            p = np.poly1d(z)
            fig.add_trace(go.Scatter(x=sol_aligned, y=p(sol_aligned), mode='lines', name='Trend Line', line=dict(color='red', width=2, dash='dash')))
        
        fig.update_layout(title=f"Portfolio vs SOL Correlation (r={corr_metrics.get('pearson_correlation', 0):.3f}, p={corr_metrics.get('pearson_p_value', 1):.3f})", xaxis_title="SOL Daily Return", yaxis_title="Portfolio Daily Return (SOL)", template='plotly_white', height=500)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create correlation chart: {e}", exc_info=True)
        return f"<p>Error creating correlation chart: {str(e)}</p>"

def create_trend_performance_chart(correlation_analysis: Dict[str, Any]) -> str:
    """Create trend-based performance chart."""
    try:
        trend_analysis = correlation_analysis.get('trend_analysis', {})
        if (not correlation_analysis or correlation_analysis.get('error') or 
            trend_analysis.get('error') or 'uptrend' not in trend_analysis):
            return ""

        trends = ['Uptrend', 'Downtrend']
        returns = [trend_analysis.get('uptrend', {}).get('mean_return', 0), trend_analysis.get('downtrend', {}).get('mean_return', 0)]
        win_rates = [trend_analysis.get('uptrend', {}).get('win_rate', 0) * 100, trend_analysis.get('downtrend', {}).get('win_rate', 0) * 100]
        days = [trend_analysis.get('uptrend', {}).get('days', 0), trend_analysis.get('downtrend', {}).get('days', 0)]
        
        fig = make_subplots(rows=1, cols=3, subplot_titles=('Average Daily Return', 'Win Rate (%)', 'Days Count'), specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]])
        fig.add_trace(go.Bar(x=trends, y=returns, name='Avg Return', marker_color=['#4CAF50', '#F44336']), row=1, col=1)
        fig.add_trace(go.Bar(x=trends, y=win_rates, name='Win Rate', marker_color=['#2196F3', '#FF9800']), row=1, col=2)
        fig.add_trace(go.Bar(x=trends, y=days, name='Days', marker_color=['#9C27B0', '#607D8B']), row=1, col=3)
        fig.update_layout(title="Performance by SOL Market Trend", template='plotly_white', showlegend=False, height=400)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create trend performance chart: {e}", exc_info=True)
        return f"<p>Error creating trend performance chart: {str(e)}</p>"

def create_weekend_comparison_chart(weekend_analysis: Dict[str, Any]) -> str:
    """Create weekend parameter comparison chart."""
    try:
        if weekend_analysis.get('analysis_skipped'):
            return f"<p>Weekend analysis was skipped: {weekend_analysis.get('reason', 'unknown reason')}</p>"
        if 'error' in weekend_analysis or not weekend_analysis.get('is_valid'):
            return f"<p>Weekend analysis error: {weekend_analysis.get('error', 'invalid data')}</p>"
            
        comparison = weekend_analysis.get('performance_comparison', {})
        
        current = comparison.get('current_scenario', {}).get('metrics', {})
        alternative = comparison.get('alternative_scenario', {}).get('metrics', {})
        
        metrics = ['Total PnL', 'Average ROI (%)', 'Sharpe Ratio']
        current_values = [
            current.get('total_pnl', 0), 
            current.get('average_roi', 0) * 100, 
            current.get('sharpe_ratio', 0)
        ]
        alternative_values = [
            alternative.get('total_pnl', 0), 
            alternative.get('average_roi', 0) * 100, 
            alternative.get('sharpe_ratio', 0)
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

        actual_pnl = portfolio_analysis['sol_denomination']['gross_pnl_sol']

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

def create_strategy_heatmap_chart(strategy_instances_path: str = "strategy_instances.csv") -> str:
    """Create an interactive strategy performance heatmap from strategy_instances.csv."""
    try:
        if not os.path.exists(strategy_instances_path):
            return "<div class='skipped'>strategy_instances.csv not found. Run log extraction and instance detection.</div>"
            
        df = pd.read_csv(strategy_instances_path)
        min_occurrences = 3
        top_strategies = 15
        
        df = df[df['position_count'] >= min_occurrences]
        if df.empty:
            return f"<div class='skipped'>No strategies with at least {min_occurrences} positions found.</div>"

        def _extract_step_size(s):
            m = re.search(r'\b(MEDIUM|WIDE|NARROW|SIXTYNINE)\b', str(s), re.IGNORECASE)
            return m.group(1).upper() if m else 'MEDIUM'
        
        def _extract_strategy_name(s):
            s_clean = str(s)
            # AIDEV-NOTE-CLAUDE: Fix for TypeError. Using re.sub for case-insensitive replace.
            for step in ['MEDIUM', 'WIDE', 'NARROW', 'SIXTYNINE']:
                s_clean = re.sub(step, '', s_clean, flags=re.IGNORECASE).strip()
            return ' '.join(s_clean.split()).rstrip('() -') or 'Unknown'

        df['step_size'] = df['strategy'].apply(_extract_step_size)
        df['strategy_clean'] = df['strategy'].apply(_extract_strategy_name)
        
        sort_metric = 'performance_score' if 'performance_score' in df.columns else 'avg_pnl_percent'
        df = df.sort_values(sort_metric, ascending=False).head(top_strategies)
        
        df['strategy_label'] = df['strategy_clean'] + ' ' + df['initial_investment'].round(3).astype(str) + ' SOL'
        
        pivot_df = df.pivot(index='strategy_label', columns='step_size', values='avg_pnl_percent')
        
        if pivot_df.empty:
            return "<div class='skipped'>Could not create pivot table for heatmap. Check data.</div>"

        fig = go.Figure(data=go.Heatmap(
            z=pivot_df.values,
            x=pivot_df.columns,
            y=pivot_df.index,
            colorscale='RdYlGn',
            zmid=0,
            hovertemplate='Strategy: %{y}<br>Step Size: %{x}<br>Avg PnL: %{z:.2f}%<extra></extra>'
        ))
        
        fig.update_layout(
            title=f'Strategy Performance Heatmap (Avg PnL %)',
            xaxis_title='Step Size',
            yaxis_title='Strategy Instance',
            template='plotly_white',
            height=max(400, len(pivot_df.index) * 30 + 150),
            yaxis=dict(autorange="reversed")
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)

    except Exception as e:
        logger.error(f"Failed to create strategy heatmap chart: {e}", exc_info=True)
        return f"<p>Error creating strategy heatmap chart: {str(e)}</p>"