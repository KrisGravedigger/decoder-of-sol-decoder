"""
Generates interactive charts related to core portfolio performance.

Includes:
- Key Performance Indicators (KPI) summary table.
- Professional equity curve with dual currency and cost impact.
- Professional drawdown analysis.
- Professional infrastructure cost impact breakdown.
"""
import logging
from typing import Dict, Any

import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


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
            ['Max PnL Drawdown', f"{sol_metrics.get('max_drawdown_percent', 0):.2%}", f"{usdc_metrics.get('max_drawdown_percent', 0):.2%}"],
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


def create_professional_equity_curve(portfolio_analysis: Dict[str, Any]) -> str:
    """Create professional interactive equity curve with dual currency and cost impact."""
    try:
        daily_df = portfolio_analysis['raw_data']['daily_returns_df']
        sol_rates = portfolio_analysis['raw_data']['sol_rates']
        cost_summary = portfolio_analysis['infrastructure_cost_impact']
        
        if daily_df.empty:
            return "<p>No daily data available for professional equity curve</p>"
            
        daily_df = daily_df.copy()
        daily_df['cumulative_pnl_usdc'] = 0.0
        daily_df['cumulative_cost_sol'] = 0.0
        daily_df['net_pnl_sol'] = 0.0
        
        daily_cost_usd = cost_summary['daily_cost_usd']
        daily_df['daily_cost_sol'] = 0.0

        for idx, row in daily_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            sol_price = sol_rates.get(date_str)
            if sol_price and sol_price > 0:
                daily_df.at[idx, 'daily_cost_sol'] = daily_cost_usd / sol_price
                daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_price

        daily_df['cumulative_cost_sol'] = daily_df['daily_cost_sol'].cumsum()
        daily_df['net_pnl_sol'] = daily_df['cumulative_pnl_sol'] - daily_df['cumulative_cost_sol']
        
        fig = make_subplots(
            rows=1, cols=1,
            specs=[[{"secondary_y": True}]]
        )
        
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
                       
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=1, col=1)
        
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
        
        fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
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
            
        daily_df = daily_df.copy()
        cumulative = daily_df['cumulative_pnl_sol']
        running_max = cumulative.expanding().max()
        safe_running_max = running_max.abs().replace(0, 1)
        drawdown = (cumulative - running_max) / safe_running_max * 100
        
        fig = make_subplots(
            rows=2, cols=1,
            subplot_titles=('Equity Curve with Running Maximum', 'Drawdown Percentage'),
            vertical_spacing=0.12,
            row_heights=[0.6, 0.4]
        )
        
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
        
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=1, col=1)
        fig.add_hline(y=0, line_dash="dash", line_color="black", opacity=0.3, row=2, col=1)
        
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
        
        fig.update_xaxes(title_text="Date", row=2, col=1)
        fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
        fig.update_yaxes(title_text="Drawdown (%)", row=2, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create professional drawdown analysis: {e}", exc_info=True)
        return f"<p>Error creating professional drawdown analysis: {str(e)}</p>"


def create_professional_cost_impact(portfolio_analysis: Dict[str, Any]) -> str:
    """Create professional interactive infrastructure cost impact chart."""
    try:
        sol_metrics = portfolio_analysis['sol_denomination']
        usdc_metrics = portfolio_analysis['usdc_denomination']
        cost_summary = portfolio_analysis['infrastructure_cost_impact']
        
        gross_pnl_sol = sol_metrics.get('total_pnl_sol', 0)
        net_pnl_sol = sol_metrics.get('net_pnl_after_costs', 0)
        
        gross_pnl_usdc = usdc_metrics.get('total_pnl_usdc', 0)
        net_pnl_usdc = usdc_metrics.get('net_pnl_after_costs', 0)
        
        daily_cost_usd = cost_summary.get('daily_cost_usd', 0)
        avg_sol_price = (usdc_metrics.get('total_pnl_usdc', 0) / sol_metrics.get('total_pnl_sol', 1)) if sol_metrics.get('total_pnl_sol', 0) != 0 else 150
        daily_cost_sol = (daily_cost_usd / avg_sol_price) if avg_sol_price > 0 else 0
        
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=(
                'Gross vs Net PnL (SOL)',
                'Gross vs Net PnL (USDC)',
                'Daily Infrastructure Cost (SOL)',
                'Daily Infrastructure Cost (USDC)',
                'Infrastructure Cost Impact (%)',
                'Break-even Analysis'
            ),
            specs=[[{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "bar"}],
                   [{"type": "bar"}, {"type": "pie"}]],
            vertical_spacing=0.15
        )
        
        fig.add_trace(
            go.Bar(
                x=['Gross PnL', 'Net PnL'],
                y=[gross_pnl_sol, net_pnl_sol],
                name='PnL (SOL)',
                marker_color=['#004E89', '#FF6B35'],
                hovertemplate='<b>%{x}</b><br>Amount: %{y:.3f} SOL<extra></extra>',
                showlegend=False
            ),
            row=1, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=['Gross PnL', 'Net PnL'],
                y=[gross_pnl_usdc, net_pnl_usdc],
                name='PnL (USDC)',
                marker_color=['#004E89', '#FF6B35'],
                hovertemplate='<b>%{x}</b><br>Amount: $%{y:.2f}<extra></extra>',
                showlegend=False
            ),
            row=1, col=2
        )
        
        fig.add_trace(
            go.Bar(
                x=['Daily Cost'],
                y=[daily_cost_sol],
                name='Daily Cost (SOL)',
                marker_color='#D2001C',
                hovertemplate='<b>Daily Cost</b><br>Amount: %{y:.4f} SOL<extra></extra>',
                showlegend=False
            ),
            row=2, col=1
        )
        
        fig.add_trace(
            go.Bar(
                x=['Daily Cost'],
                y=[daily_cost_usd],
                name='Daily Cost (USDC)',
                marker_color='#D2001C',
                hovertemplate='<b>Daily Cost</b><br>Amount: $%{y:.2f}<extra></extra>',
                showlegend=False
            ),
            row=2, col=2
        )

        cost_impact_sol = (abs(gross_pnl_sol - net_pnl_sol) / abs(gross_pnl_sol) * 100) if gross_pnl_sol != 0 else 0
        cost_impact_usdc = (abs(gross_pnl_usdc - net_pnl_usdc) / abs(gross_pnl_usdc) * 100) if gross_pnl_usdc != 0 else 0
        impact_percentages = [cost_impact_sol, cost_impact_usdc]
        
        fig.add_trace(
            go.Bar(
                x=['SOL', 'USDC'],
                y=impact_percentages,
                name='Cost Impact %',
                marker_color=['#7209B7', '#A663CC'],
                hovertemplate='<b>Cost Impact</b><br>Currency: %{x}<br>Impact: %{y:.1f}%<extra></extra>',
                showlegend=False
            ),
            row=3, col=1
        )
        
        break_even_days = cost_summary.get('break_even_days', 0)
        analysis_days = cost_summary.get('period_days', 30)
        
        if break_even_days > 0 and analysis_days > 0:
            if break_even_days >= analysis_days:
                sizes = [analysis_days]
                labels = [f'Break-even not reached<br>within {analysis_days} days']
                colors = ['#FF6B35']
            else:
                sizes = [break_even_days, analysis_days - break_even_days]
                labels = [f'Break-even<br>({break_even_days:.0f} days)', 
                         f'Profitable<br>({analysis_days - break_even_days:.0f} days)']
                colors = ['#FF6B35', '#004E89']
            
            fig.add_trace(
                go.Pie(
                    labels=labels,
                    values=sizes,
                    marker_colors=colors,
                    hole=0.3,
                    hovertemplate='<b>%{label}</b><br>Days: %{value}<br>Percentage: %{percent}<extra></extra>',
                    showlegend=False
                ),
                row=3, col=2
            )
        
        fig.update_layout(
            height=900,
            title=dict(
                text="Professional Infrastructure Cost Impact Analysis",
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            template='plotly_white',
            showlegend=True
        )
        
        fig.update_yaxes(title_text="PnL Amount (SOL)", row=1, col=1)
        fig.update_yaxes(title_text="PnL Amount (USDC)", row=1, col=2)
        fig.update_yaxes(title_text="Daily Cost (SOL)", row=2, col=1)
        fig.update_yaxes(title_text="Daily Cost (USDC)", row=2, col=2)
        fig.update_yaxes(title_text="Cost Impact (%)", row=3, col=1)
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create professional cost impact chart: {e}", exc_info=True)
        return f"<p>Error creating professional cost impact chart: {str(e)}</p>"