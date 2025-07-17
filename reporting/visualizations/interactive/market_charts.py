"""
Generates interactive charts related to market conditions and correlation.

Includes:
- Portfolio vs. SOL correlation scatter plot.
- Performance breakdown by market trend (uptrend/downtrend).
- SOL price vs. EMA trend indicator chart.
"""
import logging
from typing import Dict, Any

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


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
    """Create trend-based performance chart with unified colors."""
    try:
        trend_analysis = correlation_analysis.get('trend_analysis', {})
        if (not correlation_analysis or correlation_analysis.get('error') or 
            trend_analysis.get('error') or 'uptrend' not in trend_analysis):
            return "<div class='skipped'>Insufficient data for trend performance chart.</div>"

        trends = ['Uptrend', 'Downtrend']
        colors = ['#4CAF50', '#F44336']  # Green for uptrend, Red for downtrend

        returns = [trend_analysis.get('uptrend', {}).get('mean_return', 0), trend_analysis.get('downtrend', {}).get('mean_return', 0)]
        win_rates = [trend_analysis.get('uptrend', {}).get('win_rate', 0) * 100, trend_analysis.get('downtrend', {}).get('win_rate', 0) * 100]
        days = [trend_analysis.get('uptrend', {}).get('days', 0), trend_analysis.get('downtrend', {}).get('days', 0)]
        
        fig = make_subplots(rows=1, cols=3, subplot_titles=('Average Daily Return (SOL)', 'Win Rate (%)', 'Days Count'), specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]])
        
        fig.add_trace(go.Bar(x=trends, y=returns, name='Avg Return', marker_color=colors, hovertemplate='<b>%{x}</b><br>Avg Daily Return: %{y:.4f} SOL<extra></extra>'), row=1, col=1)
        fig.add_trace(go.Bar(x=trends, y=win_rates, name='Win Rate', marker_color=colors, hovertemplate='<b>%{x}</b><br>Win Rate: %{y:.1f}%<extra></extra>'), row=1, col=2)
        fig.add_trace(go.Bar(x=trends, y=days, name='Days', marker_color=colors, hovertemplate='<b>%{x}</b><br>Days: %{y}<extra></extra>'), row=1, col=3)
        
        fig.update_layout(title="Performance by SOL Market Trend", template='plotly_white', showlegend=False, height=400)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create trend performance chart: {e}", exc_info=True)
        return f"<p>Error creating trend performance chart: {str(e)}</p>"


def create_ema_trend_chart(correlation_analysis: Dict[str, Any]) -> str:
    """Create a chart showing SOL price vs. a conditionally colored 50-day EMA."""
    try:
        raw_data = correlation_analysis.get('raw_data', {})
        if 'sol_daily_data' not in raw_data or raw_data['sol_daily_data'].empty:
            return "<div class='skipped'>No daily SOL data available for EMA trend chart.</div>"

        df = raw_data['sol_daily_data'].copy()

        if not all(col in df.columns for col in ['close', 'ema_50', 'trend']):
            return "<div class='skipped'>Data for EMA trend chart is incomplete (missing close, ema_50, or trend).</div>"

        fig = go.Figure()

        fig.add_trace(go.Scatter(
            x=df.index,
            y=df['close'],
            mode='lines',
            name='SOL Price',
            line=dict(color='lightgrey', width=1.5),
            hovertemplate='Date: %{x}<br>SOL Price: $%{y:.2f}<extra></extra>'
        ))

        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', name='EMA 50 - Uptrend', line=dict(color='#4CAF50', width=3)))
        fig.add_trace(go.Scatter(x=[None], y=[None], mode='lines', name='EMA 50 - Downtrend', line=dict(color='#F44336', width=3)))

        df['trend_change'] = df['trend'].ne(df['trend'].shift()).cumsum()
        
        for _, segment in df.groupby('trend_change'):
            trend_type = segment['trend'].iloc[0]
            color = '#4CAF50' if trend_type == 'uptrend' else '#F44336'
            
            first_index = segment.index[0]
            prev_loc = df.index.get_loc(first_index) - 1
            if prev_loc >= 0:
                plot_segment = pd.concat([df.iloc[[prev_loc]], segment])
            else:
                plot_segment = segment
            
            fig.add_trace(go.Scatter(
                x=plot_segment.index,
                y=plot_segment['ema_50'],
                mode='lines',
                line=dict(color=color, width=3),
                hovertemplate=f'Date: %{{x}}<br>EMA 50: $%{{y:.2f}}<br>Trend: {trend_type}<extra></extra>',
                showlegend=False
            ))

        fig.update_layout(
            title="SOL Price vs. EMA 50 Trend Indicator",
            xaxis_title="Date",
            yaxis_title="Price (USDC)",
            template='plotly_white',
            height=500,
            hovermode='x unified',
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)

    except Exception as e:
        logger.error(f"Failed to create EMA trend chart: {e}", exc_info=True)
        return f"<p>Error creating EMA trend chart: {str(e)}</p>"