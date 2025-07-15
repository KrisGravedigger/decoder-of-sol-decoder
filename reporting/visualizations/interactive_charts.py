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
        
        # AIDEV-NOTE-CLAUDE: Merged Win Rate cells - single value for both currencies
        win_rate_value = f"{sol_metrics.get('win_rate', 0):.1%}"
        
        header = ['Metric', 'SOL Denomination', 'USDC Denomination']
        cells = [
            ['Total PnL', f"{sol_metrics.get('total_pnl_sol', 0):.3f} SOL", f"${usdc_metrics.get('total_pnl_usdc', 0):.2f}"],
            ['Net PnL (after costs)', f"{sol_metrics.get('net_pnl_after_costs', 0):.3f} SOL", f"${usdc_metrics.get('net_pnl_after_costs', 0):.2f}"],
            ['Win Rate', win_rate_value, f"({win_rate_value})"],  # Unified value, parentheses for visual unity
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
        # AIDEV-NOTE-CLAUDE: Enhanced debug logging for portfolio structure
        # Debug complete - portfolio structure identified
        
        if not simulation_results:
            return "<div class='skipped'>No simulation results available.</div>"

        sim_pnl = {}
        for res in simulation_results:
            if not res or 'simulation_results' not in res: continue
            for name, data in res['simulation_results'].items():
                if 'pnl_sol' in data:
                    sim_pnl[name] = sim_pnl.get(name, 0) + data['pnl_sol']

        # AIDEV-NOTE-CLAUDE: gross_pnl_sol is in infrastructure_cost_impact, not sol_denomination
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
        
        # AIDEV-NOTE-GEMINI: Column Standardization Fix.
        # Adhering to the project standard 'investment_sol' to prevent KeyError.
        df['strategy_label'] = df['strategy_clean'] + ' ' + df['investment_sol'].round(3).astype(str) + ' SOL'
        
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

def create_professional_equity_curve(portfolio_analysis: Dict[str, Any]) -> str:
    """Create professional interactive equity curve with dual currency and cost impact."""
    try:
        daily_df = portfolio_analysis['raw_data']['daily_returns_df']
        sol_rates = portfolio_analysis['raw_data']['sol_rates']
        cost_summary = portfolio_analysis['infrastructure_cost_impact']
        
        if daily_df.empty:
            return "<p>No daily data available for professional equity curve</p>"
            
        # Prepare data similar to chart_generator.py
        daily_df = daily_df.copy()
        daily_df['cumulative_pnl_usdc'] = 0.0
        daily_df['cumulative_cost_sol'] = 0.0
        daily_df['net_pnl_sol'] = 0.0
        
        cumulative_cost = 0.0
        daily_cost_usd = cost_summary.get('daily_cost_usd', 11.67)
        
        for idx, row in daily_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            
            if date_str in sol_rates:
                sol_price = sol_rates[date_str]
                if sol_price is not None:
                    daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_price
                    
                    daily_cost_sol = daily_cost_usd / sol_price
                    cumulative_cost += daily_cost_sol
                    
                    daily_df.at[idx, 'cumulative_cost_sol'] = cumulative_cost
                    daily_df.at[idx, 'net_pnl_sol'] = row['cumulative_pnl_sol'] - cumulative_cost
        
        # Create subplot figure
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Portfolio Equity Curve - Dual Currency Analysis', 'SOL/USDC Price'),
            vertical_spacing=0.1,
            specs=[[{"secondary_y": True}], [{}]]
        )
        
        # Main equity curves
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['cumulative_pnl_sol'],
                mode='lines',
                name='Gross SOL PnL',
                line=dict(color='#FF6B35', width=2),
                hovertemplate='<b>Gross SOL PnL</b><br>Date: %{x}<br>PnL: %{y:.3f} SOL<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['net_pnl_sol'],
                mode='lines',
                name='Net SOL PnL (after costs)',
                line=dict(color='#D2001C', width=2, dash='dash'),
                hovertemplate='<b>Net SOL PnL</b><br>Date: %{x}<br>PnL: %{y:.3f} SOL<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['cumulative_pnl_usdc'],
                mode='lines',
                name='USDC PnL',
                line=dict(color='#004E89', width=2, dash='dot'),
                yaxis='y2',
                hovertemplate='<b>USDC PnL</b><br>Date: %{x}<br>PnL: %{y:.2f} USDC<extra></extra>'
            ),
            row=1, col=1, secondary_y=True
        )
        
        # Cost impact fill area
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['cumulative_pnl_sol'],
                fill='tonexty',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(width=0),
                name='Infrastructure Cost Impact',
                showlegend=True,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=daily_df['net_pnl_sol'],
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
        
        # SOL price chart
        valid_sol_rates = {k: v for k, v in sol_rates.items() if v is not None}
        if valid_sol_rates:
            sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in valid_sol_rates.keys()]
            sol_prices = list(valid_sol_rates.values())
            
            fig.add_trace(
                go.Scatter(
                    x=sol_dates,
                    y=sol_prices,
                    mode='lines',
                    name='SOL/USDC Price',
                    line=dict(color='#7209B7', width=2),
                    hovertemplate='<b>SOL Price</b><br>Date: %{x}<br>Price: $%{y:.2f}<extra></extra>'
                ),
                row=2, col=1
            )
        
        # Add zero line
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=1, col=1)
        
        # Update layout
        fig.update_layout(
            height=700,
            title=dict(
                text="Professional Portfolio Equity Curve - Dual Currency with Cost Impact",
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            template='plotly_white',
            hovermode='x unified'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
        fig.update_yaxes(title_text="SOL/USDC Price", row=2, col=1)
        
        # Update secondary y-axis for USDC
        fig.update_yaxes(title_text="Cumulative PnL (USDC)", secondary_y=True, row=1, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create professional equity curve: {e}", exc_info=True)
        return f"<p>Error creating professional equity curve: {str(e)}</p>"

def create_professional_drawdown_analysis(portfolio_analysis: Dict[str, Any]) -> str:
    """Create professional interactive drawdown analysis chart."""
    try:
        daily_df = portfolio_analysis['raw_data']['daily_returns_df']
        
        if daily_df.empty:
            return "<p>No daily data available for professional drawdown analysis</p>"
            
        # Calculate drawdown
        daily_df = daily_df.copy()
        cumulative = daily_df['cumulative_pnl_sol']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max.abs() * 100
        
        # Create subplot
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Equity Curve with Running Maximum', 'Drawdown Percentage'),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
        # Equity curve with running max
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=cumulative,
                mode='lines',
                name='Cumulative PnL',
                line=dict(color='#004E89', width=2),
                hovertemplate='<b>Cumulative PnL</b><br>Date: %{x}<br>PnL: %{y:.3f} SOL<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=running_max,
                mode='lines',
                name='Running Maximum',
                line=dict(color='#FF6B35', width=1, dash='dash'),
                opacity=0.7,
                hovertemplate='<b>Running Maximum</b><br>Date: %{x}<br>Max: %{y:.3f} SOL<extra></extra>'
            ),
            row=1, col=1
        )
        
        # Drawdown fill
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=cumulative,
                fill='tonexty',
                fillcolor='rgba(255, 0, 0, 0.2)',
                line=dict(width=0),
                name='Drawdown Periods',
                showlegend=True,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=running_max,
                mode='lines',
                line=dict(width=0),
                showlegend=False,
                hoverinfo='skip'
            ),
            row=1, col=1
        )
        
        # Drawdown percentage
        fig.add_trace(
            go.Scatter(
                x=daily_df['date'],
                y=drawdown,
                mode='lines',
                name='Drawdown %',
                line=dict(color='darkred', width=1),
                fill='tozeroy',
                fillcolor='rgba(139, 0, 0, 0.6)',
                hovertemplate='<b>Drawdown</b><br>Date: %{x}<br>Drawdown: %{y:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Highlight maximum drawdown
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        max_dd_date = daily_df.iloc[max_dd_idx]['date']
        
        fig.add_trace(
            go.Scatter(
                x=[max_dd_date],
                y=[max_dd_value],
                mode='markers',
                name=f'Max DD: {max_dd_value:.1f}%',
                marker=dict(color='red', size=12, symbol='circle'),
                hovertemplate=f'<b>Maximum Drawdown</b><br>Date: {max_dd_date.strftime("%Y-%m-%d")}<br>Drawdown: {max_dd_value:.1f}%<extra></extra>'
            ),
            row=2, col=1
        )
        
        # Add zero lines
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=2, col=1)
        
        # Update layout
        fig.update_layout(
            height=700,
            title=dict(
                text="Professional Portfolio Drawdown Analysis",
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            template='plotly_white',
            hovermode='x unified'
        )
        
        # Update axes
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create professional drawdown analysis: {e}", exc_info=True)
        return f"<p>Error creating professional drawdown analysis: {str(e)}</p>"

def create_professional_strategy_heatmap(portfolio_analysis: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Create professional interactive strategy performance heatmap with YAML filters."""
    try:
        positions_df = portfolio_analysis['raw_data']['positions_df']
        
        if positions_df.empty:
            return "<p>No positions data available for professional strategy heatmap</p>"
            
        # Try to load strategy instances data first
        if os.path.exists("strategy_instances.csv"):
            try:
                strategy_instances_df = pd.read_csv("strategy_instances.csv")
                return _create_strategy_instances_professional_heatmap(strategy_instances_df, config)
            except Exception as e:
                logger.warning(f"Failed to use strategy_instances.csv: {e}, using positions fallback")
                return _create_positions_professional_heatmap(positions_df, config)
        else:
            return _create_positions_professional_heatmap(positions_df, config)
            
    except Exception as e:
        logger.error(f"Failed to create professional strategy heatmap: {e}", exc_info=True)
        return f"<p>Error creating professional strategy heatmap: {str(e)}</p>"

def _create_strategy_instances_professional_heatmap(strategy_instances_df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """Create professional heatmap from strategy_instances.csv with YAML filters."""
    filters = config.get('visualization', {}).get('filters', {})
    min_occurrences = filters.get('min_strategy_occurrences', 2)
    top_strategies = filters.get('top_strategies_only', 10)
    
    # Apply filters
    strategy_instances_df = strategy_instances_df[
        strategy_instances_df['position_count'] >= min_occurrences
    ]
    
    if strategy_instances_df.empty:
        return f"<p>No strategies with ≥{min_occurrences} positions found</p>"
        
    # Sort and limit strategies
    if 'avg_pnl_percent' in strategy_instances_df.columns:
        strategy_instances_df = strategy_instances_df.sort_values(
            'avg_pnl_percent', ascending=False
        ).head(top_strategies)
    else:
        strategy_instances_df = strategy_instances_df.head(top_strategies)
        
    # Create strategy name with position count
    strategy_instances_df['strategy_display_name'] = (
        strategy_instances_df['strategy'] + ' ' + 
        strategy_instances_df['step_size'] + ' ' +
        strategy_instances_df['investment_sol'].astype(str) + 'SOL' +
        ' (' + strategy_instances_df['position_count'].astype(str) + ')'
    )
    
    # Create interactive heatmap with 3 metrics
    metrics = ['avg_pnl_percent', 'win_rate']
    if 'sharpe_ratio' in strategy_instances_df.columns:
        metrics.append('sharpe_ratio')
    
    metric_labels = ['Avg PnL %', 'Win Rate', 'Sharpe Ratio'][:len(metrics)]
    
    fig = make_subplots(
        rows=1, cols=len(metrics),
        subplot_titles=metric_labels,
        horizontal_spacing=0.15
    )
    
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        if metric not in strategy_instances_df.columns:
            continue
            
        values = strategy_instances_df[metric].values
        strategy_names = strategy_instances_df['strategy_display_name'].values
        
        # Adjust values for win_rate display
        display_values = values * 100 if metric == 'win_rate' else values
        
        # Create heatmap
        heatmap = go.Heatmap(
            z=display_values.reshape(-1, 1),
            y=strategy_names,
            x=[label],
            colorscale='RdYlGn',
            zmid=0 if metric == 'avg_pnl_percent' else display_values.mean(),
            text=[[f'{val:.1f}%' if metric == 'win_rate' else f'{val:.2f}'] for val in display_values],
            texttemplate='%{text}',
            textfont=dict(size=10),
            hovertemplate=f'<b>{label}</b><br>Strategy: %{{y}}<br>Value: %{{z:.2f}}<extra></extra>',
            showscale=(i == len(metrics)-1)  # Show colorbar only for last subplot
        )
        
        fig.add_trace(heatmap, row=1, col=i+1)
    
    fig.update_layout(
        height=max(600, len(strategy_names) * 35),
        title=dict(
            text=f'Professional Strategy Performance Heatmap (Top {len(strategy_instances_df)} Strategies)',
            font=dict(size=20, color='#2E3440'),
            x=0.5
        ),
        template='plotly_white'
    )
    
    # Update y-axes to prevent label overlap
    fig.update_yaxes(tickfont=dict(size=9))
    
    return pyo.plot(fig, output_type='div', include_plotlyjs=False)

def _create_positions_professional_heatmap(positions_df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """Professional fallback heatmap based on positions data."""
    try:
        # Group by strategy and step_size
        strategy_groups = positions_df.groupby(['strategy', 'step_size']).agg({
            'pnl_sol': ['sum', 'mean', 'count'],
            'investment_sol': 'sum'
        }).round(3)
        
        strategy_groups.columns = ['total_pnl', 'avg_pnl', 'position_count', 'total_investment']
        strategy_groups['win_rate'] = positions_df.groupby(['strategy', 'step_size']).apply(
            lambda x: (x['pnl_sol'] > 0).mean()
        )
        
        # Apply filters
        filters = config.get('visualization', {}).get('filters', {})
        min_occurrences = filters.get('min_strategy_occurrences', 2)
        
        strategy_groups = strategy_groups[strategy_groups['position_count'] >= min_occurrences]
        
        if strategy_groups.empty:
            return f"<p>No strategies with ≥{min_occurrences} positions found</p>"
            
        # Create pivot table for heatmap
        pivot_data = strategy_groups.reset_index().pivot(
            index='strategy', columns='step_size', values='avg_pnl'
        ).fillna(0)
        
        # Create interactive heatmap
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale='RdYlGn',
            zmid=0,
            text=pivot_data.values,
            texttemplate='%{text:.3f}',
            textfont=dict(size=10),
            hovertemplate='<b>Strategy Performance</b><br>Strategy: %{y}<br>Step Size: %{x}<br>Avg PnL: %{z:.3f} SOL<extra></extra>'
        ))
        
        fig.update_layout(
            height=500,
            title=dict(
                text='Professional Strategy Performance Heatmap (Positions-Based)',
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            xaxis_title='Step Size',
            yaxis_title='Strategy',
            template='plotly_white'
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create positions-based professional heatmap: {e}")
        return f"<p>Error creating fallback professional heatmap: {str(e)}</p>"

def create_professional_cost_impact(portfolio_analysis: Dict[str, Any]) -> str:
    """Create professional interactive infrastructure cost impact chart."""
    try:
        sol_metrics = portfolio_analysis['sol_denomination']
        usdc_metrics = portfolio_analysis['usdc_denomination']
        cost_summary = portfolio_analysis['infrastructure_cost_impact']
        
        # Prepare data
        categories = ['SOL Denomination', 'USDC Denomination']
        gross_pnl = [
            sol_metrics['total_pnl_sol'] + cost_summary.get('total_cost_sol', 0),
            usdc_metrics['total_pnl_usdc'] + cost_summary.get('total_cost_usd', 0)
        ]
        net_pnl = [
            sol_metrics['net_pnl_after_costs'],
            usdc_metrics['net_pnl_after_costs']
        ]
        costs = [
            cost_summary.get('total_cost_sol', 0),
            cost_summary.get('total_cost_usd', 0)
        ]
        
        # Create subplot
        fig = make_subplots(
            rows=2, cols=2,
            subplot_titles=(
                'Gross vs Net PnL Comparison',
                'Infrastructure Cost Impact (%)',
                'Daily Infrastructure Cost',
                'Break-even Analysis'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "pie"}]]
        )
        
        # 1. Gross vs Net PnL
        fig.add_trace(
            go.Bar(
                x=categories,
                y=gross_pnl,
                name='Gross PnL',
                marker_color='#004E89',
                opacity=0.8,
                hovertemplate='<b>Gross PnL</b><br>Currency: %{x}<br>Amount: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=net_pnl,
                name='Net PnL',
                marker_color='#FF6B35',
                opacity=0.8,
                hovertemplate='<b>Net PnL</b><br>Currency: %{x}<br>Amount: %{y:.2f}<extra></extra>'
            ),
            row=1, col=1
        )
        
        # 2. Cost Impact Percentage
        cost_impact_sol = (costs[0] / gross_pnl[0] * 100) if gross_pnl[0] > 0 else 0
        cost_impact_usdc = (costs[1] / gross_pnl[1] * 100) if gross_pnl[1] > 0 else 0
        impact_percentages = [cost_impact_sol, cost_impact_usdc]
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=impact_percentages,
                name='Cost Impact %',
                marker_color=['#7209B7', '#A663CC'],
                opacity=0.8,
                hovertemplate='<b>Cost Impact</b><br>Currency: %{x}<br>Impact: %{y:.1f}%<extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )
        
        # 3. Daily Cost Allocation
        period_days = cost_summary.get('period_days', 30)
        daily_costs = [
            cost_summary.get('total_cost_sol', 0) / period_days,
            cost_summary.get('total_cost_usd', 0) / period_days
        ]
        
        fig.add_trace(
            go.Bar(
                x=categories,
                y=daily_costs,
                name='Daily Cost',
                marker_color=['#FF6B35', '#004E89'],
                opacity=0.6,
                hovertemplate='<b>Daily Cost</b><br>Currency: %{x}<br>Cost: %{y:.3f}<extra></extra>',
                showlegend=False
            ),
            row=2, col=1
        )
        
        # 4. Break-even Analysis (Pie Chart)
        break_even_days = cost_summary.get('break_even_days', 0)
        analysis_days = cost_summary.get('period_days', 30)
        
        if break_even_days > 0 and break_even_days < analysis_days:
            sizes = [break_even_days, analysis_days - break_even_days]
            labels = [f'Break-even<br>({break_even_days:.0f} days)', 
                     f'Profitable<br>({analysis_days - break_even_days:.0f} days)']
            colors = ['#FF6B35', '#004E89']
            
            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=sizes,
                    marker_colors=colors,
                    hovertemplate='<b>%{label}</b><br>Days: %{value}<br>Percentage: %{percent}<extra></extra>',
                    showlegend=False
                ),
                row=2, col=2
            )
        
        # Update layout
        fig.update_layout(
            height=700,
            title=dict(
                text="Professional Infrastructure Cost Impact Analysis",
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            template='plotly_white',
            showlegend=True,
            barmode='group'  # AIDEV-NOTE-CLAUDE: Added to display bars side-by-side instead of stacking
        )
        
        # Update axes
        fig.update_yaxes(title_text="PnL Amount", row=1, col=1)
        fig.update_yaxes(title_text="Cost Impact (%)", row=1, col=2)
        fig.update_yaxes(title_text="Daily Cost", row=2, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create professional cost impact chart: {e}", exc_info=True)
        return f"<p>Error creating professional cost impact chart: {str(e)}</p>"

def create_strategy_avg_pnl_summary(config: Dict[str, Any], strategy_instances_path: str = "strategy_instances.csv") -> str:
    """Create AVG PnL summary chart replacing the current heatmap."""
    try:
        if not os.path.exists(strategy_instances_path):
            return "<div class='skipped'>strategy_instances.csv not found. Run log extraction and instance detection.</div>"
            
        strategy_instances_df = pd.read_csv(strategy_instances_path)
        
        # Apply YAML filters
        filters = config.get('visualization', {}).get('filters', {})
        min_occurrences = filters.get('min_strategy_occurrences', 2)
        top_strategies = filters.get('top_strategies_only', 10)
        
        # Filter by minimum occurrences
        strategy_instances_df = strategy_instances_df[
            strategy_instances_df['position_count'] >= min_occurrences
        ]
        
        if strategy_instances_df.empty:
            return f"<div class='skipped'>No strategies with ≥{min_occurrences} positions found.</div>"
        
        # Sort by avg_pnl_percent and take top N
        if 'avg_pnl_percent' in strategy_instances_df.columns:
            strategy_instances_df = strategy_instances_df.sort_values(
                'avg_pnl_percent', ascending=True  # Ascending for horizontal bar chart
            ).tail(top_strategies)  # Take top performers
        else:
            strategy_instances_df = strategy_instances_df.head(top_strategies)
        
        # Create strategy display name with position count
        strategy_instances_df['strategy_display_name'] = (
            strategy_instances_df['strategy'] + ' ' + 
            strategy_instances_df['step_size'] + ' ' +
            strategy_instances_df['investment_sol'].astype(str) + 'SOL' +
            ' (' + strategy_instances_df['position_count'].astype(str) + ')'
        )
        
        # Create horizontal bar chart
        colors = ['#27ae60' if x >= 0 else '#c0392b' for x in strategy_instances_df['avg_pnl_percent']]
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                y=strategy_instances_df['strategy_display_name'],
                x=strategy_instances_df['avg_pnl_percent'],
                orientation='h',
                marker_color=colors,
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Avg PnL: %{x:.2f}%<br>'
                    '<extra></extra>'
                )
            )
        )
        
        # Add zero line
        fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
        
        # Update layout
        fig.update_layout(
            height=max(500, len(strategy_instances_df) * 40),
            title=dict(
                text=f'Strategy Performance Summary - AVG PnL (Top {len(strategy_instances_df)} Strategies)',
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            xaxis_title='Average PnL (%)',
            yaxis_title='Strategy (Position Count)',
            template='plotly_white',
            showlegend=False,
            margin=dict(l=250)  # Left margin for strategy names
        )
        
        # Update y-axis to prevent label overlap
        fig.update_yaxes(tickfont=dict(size=10))
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create strategy AVG PnL summary: {e}", exc_info=True)
        return f"<p>Error creating strategy AVG PnL summary: {str(e)}</p>"