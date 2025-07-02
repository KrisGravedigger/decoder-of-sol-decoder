"""
Interactive Chart Generation for HTML Reports

Provides functions to create Plotly-based interactive charts for the
comprehensive HTML report.
"""
import logging
from datetime import datetime
from typing import Dict, Any

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
        
        if daily_df.empty:
            return "<p>No daily data available for equity curve</p>"
            
        daily_df = daily_df.copy()
        daily_df['cumulative_pnl_usdc'] = 0.0
        for idx, row in daily_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            if date_str in sol_rates:
                daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_rates[date_str]
                
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Portfolio Equity Curve', 'SOL Price'),
            vertical_spacing=0.08,
            specs=[[{"secondary_y": True}], [{}]]
        )
        
        fig.add_trace(go.Scatter(x=daily_df['date'], y=daily_df['cumulative_pnl_sol'], name='SOL PnL', line=dict(color='#FF6B35', width=3), hovertemplate='Date: %{x}<br>SOL PnL: %{y:.3f}<extra></extra>'), row=1, col=1)
        fig.add_trace(go.Scatter(x=daily_df['date'], y=daily_df['cumulative_pnl_usdc'], name='USDC PnL', line=dict(color='#004E89', width=2, dash='dash'), yaxis='y2', hovertemplate='Date: %{x}<br>USDC PnL: $%{y:.2f}<extra></extra>'), row=1, col=1)
        
        if sol_rates:
            sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in sol_rates.keys()]
            sol_prices = list(sol_rates.values())
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
    """Create metrics summary visualization."""
    try:
        sol_metrics = portfolio_analysis['sol_denomination']
        usdc_metrics = portfolio_analysis['usdc_denomination']
        
        metrics = ['Total PnL', 'Win Rate (%)', 'Sharpe Ratio', 'Max Drawdown (%)']
        sol_values = [sol_metrics['total_pnl_sol'], sol_metrics['win_rate'] * 100, sol_metrics['sharpe_ratio'], abs(sol_metrics['max_drawdown_percent'])]
        usdc_values = [usdc_metrics['total_pnl_usdc'], usdc_metrics['win_rate'] * 100, usdc_metrics['sharpe_ratio'], abs(usdc_metrics['max_drawdown_percent'])]
        
        fig = go.Figure()
        fig.add_trace(go.Bar(name='SOL Denomination', x=metrics, y=sol_values, marker_color='#FF6B35', hovertemplate='%{x}<br>SOL: %{y:.3f}<extra></extra>'))
        
        usdc_values_normalized = usdc_values.copy()
        if len(portfolio_analysis['raw_data']['sol_rates']) > 0:
            avg_sol_price = np.mean(list(portfolio_analysis['raw_data']['sol_rates'].values()))
            usdc_values_normalized[0] /= avg_sol_price
            
        fig.add_trace(go.Bar(name='USDC Denomination', x=metrics, y=usdc_values_normalized, marker_color='#004E89', hovertemplate='%{x}<br>USDC: %{y:.3f}<extra></extra>'))
        fig.update_layout(title="Portfolio Metrics Comparison", xaxis_title="Metrics", yaxis_title="Value", barmode='group', template='plotly_white', height=400)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create metrics summary chart: {e}", exc_info=True)
        return f"<p>Error creating metrics chart: {str(e)}</p>"

def create_correlation_chart(correlation_analysis: Dict[str, Any]) -> str:
    """Create market correlation visualization."""
    try:
        raw_data = correlation_analysis['raw_data']
        portfolio_daily = raw_data['portfolio_daily_returns']
        sol_daily = raw_data['sol_daily_data']
        
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sol_aligned, y=portfolio_aligned, mode='markers', name='Daily Returns', marker=dict(size=8, color=portfolio_aligned, colorscale='RdYlGn', showscale=True, colorbar=dict(title="Portfolio Return")), hovertemplate='SOL Return: %{x:.2%}<br>Portfolio Return: %{y:.3f} SOL<extra></extra>'))
        
        z = np.polyfit(sol_aligned, portfolio_aligned, 1)
        p = np.poly1d(z)
        fig.add_trace(go.Scatter(x=sol_aligned, y=p(sol_aligned), mode='lines', name='Trend Line', line=dict(color='red', width=2, dash='dash')))
        
        corr_metrics = correlation_analysis['correlation_metrics']
        fig.update_layout(title=f"Portfolio vs SOL Correlation (r={corr_metrics['pearson_correlation']:.3f}, p={corr_metrics['pearson_p_value']:.3f})", xaxis_title="SOL Daily Return", yaxis_title="Portfolio Daily Return (SOL)", template='plotly_white', height=500)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create correlation chart: {e}", exc_info=True)
        return f"<p>Error creating correlation chart: {str(e)}</p>"

def create_trend_performance_chart(correlation_analysis: Dict[str, Any]) -> str:
    """Create trend-based performance chart."""
    try:
        trend_analysis = correlation_analysis['trend_analysis']
        trends = ['Uptrend', 'Downtrend']
        returns = [trend_analysis['uptrend']['mean_return'], trend_analysis['downtrend']['mean_return']]
        win_rates = [trend_analysis['uptrend']['win_rate'] * 100, trend_analysis['downtrend']['win_rate'] * 100]
        days = [trend_analysis['uptrend']['days'], trend_analysis['downtrend']['days']]
        
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
        # AIDEV-NOTE-CLAUDE: Handle both analysis skipped and error cases
        if 'analysis_skipped' in weekend_analysis:
            return f"<p>Weekend analysis was skipped: {weekend_analysis.get('reason', 'unknown reason')}</p>"
            
        if 'error' in weekend_analysis:
            return f"<p>Weekend analysis error: {weekend_analysis['error']}</p>"
            
        comparison = weekend_analysis['performance_comparison']
        
        # AIDEV-NOTE-CLAUDE: Updated to use new structure (current_scenario/alternative_scenario)
        current = comparison['current_scenario']['metrics']
        alternative = comparison['alternative_scenario']['metrics']
        
        # AIDEV-NOTE-CLAUDE: Removed win_rate as it's not included in weekend analysis metrics
        metrics = ['Total PnL', 'Average ROI (%)', 'Sharpe Ratio']
        current_values = [
            current['total_pnl'], 
            current['average_roi'] * 100, 
            current['sharpe_ratio']
        ]
        alternative_values = [
            alternative['total_pnl'], 
            alternative['average_roi'] * 100, 
            alternative['sharpe_ratio']
        ]
        
        # Get scenario names from the analysis
        current_name = comparison['current_scenario']['name']
        alternative_name = comparison['alternative_scenario']['name']
        
        fig = go.Figure()
        fig.add_trace(go.Bar(
            name=current_name, 
            x=metrics, 
            y=current_values, 
            marker_color='#FF6B35',
            hovertemplate='%{x}<br>' + current_name + ': %{y:.3f}<extra></extra>'
        ))
        fig.add_trace(go.Bar(
            name=alternative_name, 
            x=metrics, 
            y=alternative_values, 
            marker_color='#004E89',
            hovertemplate='%{x}<br>' + alternative_name + ': %{y:.3f}<extra></extra>'
        ))
        
        fig.update_layout(
            title="Weekend Parameter Impact Comparison", 
            xaxis_title="Metrics", 
            yaxis_title="Value", 
            barmode='group', 
            template='plotly_white', 
            height=500
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create weekend comparison chart: {e}", exc_info=True)
        return f"<p>Error creating weekend comparison chart: {str(e)}</p>"

def create_weekend_distribution_chart(weekend_analysis: Dict[str, Any]) -> str:
    """Create weekend position distribution chart."""
    try:
        # AIDEV-NOTE-CLAUDE: Handle analysis skipped case
        if 'analysis_skipped' in weekend_analysis:
            return f"<p>Weekend analysis was skipped: {weekend_analysis.get('reason', 'unknown reason')}</p>"
            
        if 'error' in weekend_analysis:
            return f"<p>Weekend analysis error: {weekend_analysis['error']}</p>"
            
        classification = weekend_analysis['position_classification']
        
        fig = go.Figure()
        fig.add_trace(go.Pie(
            labels=['Weekend Opened', 'Weekday Opened'], 
            values=[
                classification['weekend_opened']['count'], 
                classification['weekday_opened']['count']
            ], 
            hole=0.3, 
            marker_colors=['#FF6B35', '#004E89'], 
            hovertemplate='%{label}<br>Count: %{value}<br>Percentage: %{percent}<extra></extra>'
        ))
        fig.update_layout(
            title="Position Opening Distribution", 
            template='plotly_white', 
            height=400
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create weekend distribution chart: {e}", exc_info=True)
        return f"<p>Error creating weekend distribution chart: {str(e)}</p>"