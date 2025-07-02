"""
HTML Report Generator Module

Creates comprehensive interactive HTML reports combining:
- Portfolio analytics results
- Market correlation analysis
- Weekend parameter impact analysis
- Interactive charts and visualizations
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import plotly.offline as pyo
import numpy as np
from jinja2 import Template

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates comprehensive HTML reports with interactive charts.
    
    Combines portfolio analytics, market correlation, and weekend analysis
    into professional HTML reports using Plotly for interactivity.
    """
    
    def __init__(self, output_dir: str = "reporting/output"):
        """
        Initialize HTML report generator.
        
        Args:
            output_dir (str): Directory for output files
        """
        self.output_dir = output_dir
        self.templates_dir = os.path.join("reporting", "templates")
        self.timestamp_format = "%Y%m%d_%H%M"
        
        # Ensure directories exist
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.templates_dir, exist_ok=True)
        
        logger.info("HTML Report Generator initialized")
        
    def generate_comprehensive_report(self, 
                                    portfolio_analysis: Dict[str, Any],
                                    correlation_analysis: Optional[Dict[str, Any]] = None,
                                    weekend_analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate comprehensive HTML report combining all analyses.
        
        Args:
            portfolio_analysis (Dict[str, Any]): Portfolio analytics results
            correlation_analysis (Optional[Dict[str, Any]]): Market correlation results
            weekend_analysis (Optional[Dict[str, Any]]): Weekend parameter results
            
        Returns:
            str: Path to generated HTML report
        """
        logger.info("Generating comprehensive HTML report...")
        
        try:
            # Generate timestamp for filename
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            # Create interactive charts
            charts = self._generate_interactive_charts(
                portfolio_analysis, correlation_analysis, weekend_analysis
            )
            
            # Prepare data for template
            template_data = self._prepare_template_data(
                portfolio_analysis, correlation_analysis, weekend_analysis, charts
            )
            
            # Generate HTML content
            html_content = self._render_html_template(template_data)
            
            # Save report
            filename = f"comprehensive_report_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Comprehensive HTML report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}")
            raise
            
    def _generate_interactive_charts(self, 
                                   portfolio_analysis: Dict[str, Any],
                                   correlation_analysis: Optional[Dict[str, Any]],
                                   weekend_analysis: Optional[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate interactive Plotly charts for the report.
        
        Args:
            portfolio_analysis (Dict[str, Any]): Portfolio analytics
            correlation_analysis (Optional[Dict[str, Any]]): Correlation analysis
            weekend_analysis (Optional[Dict[str, Any]]): Weekend analysis
            
        Returns:
            Dict[str, str]: Dictionary of chart names to HTML strings
        """
        charts = {}
        
        # Portfolio equity curve
        charts['equity_curve'] = self._create_equity_curve_chart(portfolio_analysis)
        
        # Portfolio metrics summary
        charts['metrics_summary'] = self._create_metrics_summary_chart(portfolio_analysis)
        
        # Market correlation charts (if available)
        if correlation_analysis and 'error' not in correlation_analysis:
            charts['correlation_analysis'] = self._create_correlation_chart(correlation_analysis)
            charts['trend_performance'] = self._create_trend_performance_chart(correlation_analysis)
            
        # Weekend analysis charts (if available)
        if weekend_analysis and 'error' not in weekend_analysis:
            charts['weekend_comparison'] = self._create_weekend_comparison_chart(weekend_analysis)
            charts['weekend_distribution'] = self._create_weekend_distribution_chart(weekend_analysis)
            
        return charts
        
    def _create_equity_curve_chart(self, portfolio_analysis: Dict[str, Any]) -> str:
        """Create interactive equity curve chart."""
        try:
            daily_df = portfolio_analysis['raw_data']['daily_returns_df']
            sol_rates = portfolio_analysis['raw_data']['sol_rates']
            
            if daily_df.empty:
                return "<p>No daily data available for equity curve</p>"
                
            # Prepare data
            daily_df = daily_df.copy()
            
            # Convert SOL PnL to USDC for dual axis
            daily_df['cumulative_pnl_usdc'] = 0.0
            for idx, row in daily_df.iterrows():
                date_str = row['date'].strftime("%Y-%m-%d")
                if date_str in sol_rates:
                    daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_rates[date_str]
                    
            # Create subplot with secondary y-axis
            fig = make_subplots(
                rows=2, cols=1,
                subplot_titles=('Portfolio Equity Curve', 'SOL Price'),
                vertical_spacing=0.08,
                specs=[[{"secondary_y": True}], [{}]]
            )
            
            # Main equity curve
            fig.add_trace(
                go.Scatter(
                    x=daily_df['date'],
                    y=daily_df['cumulative_pnl_sol'],
                    name='SOL PnL',
                    line=dict(color='#FF6B35', width=3),
                    hovertemplate='Date: %{x}<br>SOL PnL: %{y:.3f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # USDC PnL on secondary axis
            fig.add_trace(
                go.Scatter(
                    x=daily_df['date'],
                    y=daily_df['cumulative_pnl_usdc'],
                    name='USDC PnL',
                    line=dict(color='#004E89', width=2, dash='dash'),
                    yaxis='y2',
                    hovertemplate='Date: %{x}<br>USDC PnL: $%{y:.2f}<extra></extra>'
                ),
                row=1, col=1
            )
            
            # SOL price in bottom subplot
            if sol_rates:
                sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in sol_rates.keys()]
                sol_prices = list(sol_rates.values())
                
                fig.add_trace(
                    go.Scatter(
                        x=sol_dates,
                        y=sol_prices,
                        name='SOL/USDC Price',
                        line=dict(color='#7209B7', width=2),
                        hovertemplate='Date: %{x}<br>SOL Price: $%{y:.2f}<extra></extra>'
                    ),
                    row=2, col=1
                )
                
            # Update layout
            fig.update_layout(
                title=dict(
                    text="Portfolio Performance - Dual Currency Analysis",
                    font=dict(size=20, color='#2E3440')
                ),
                height=700,
                showlegend=True,
                template='plotly_white',
                hovermode='x unified'
            )
            
            # Update axes
            fig.update_yaxes(title_text="Cumulative PnL (SOL)", row=1, col=1)
            fig.update_yaxes(title_text="Cumulative PnL (USDC)", secondary_y=True, row=1, col=1)
            fig.update_yaxes(title_text="SOL Price (USDC)", row=2, col=1)
            fig.update_xaxes(title_text="Date", row=2, col=1)
            
            return pyo.plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create equity curve chart: {e}")
            return f"<p>Error creating equity curve chart: {str(e)}</p>"
            
    def _create_metrics_summary_chart(self, portfolio_analysis: Dict[str, Any]) -> str:
        """Create metrics summary visualization."""
        try:
            sol_metrics = portfolio_analysis['sol_denomination']
            usdc_metrics = portfolio_analysis['usdc_denomination']
            
            # Create metrics comparison chart
            metrics = ['Total PnL', 'Win Rate (%)', 'Sharpe Ratio', 'Max Drawdown (%)']
            sol_values = [
                sol_metrics['total_pnl_sol'],
                sol_metrics['win_rate'] * 100,
                sol_metrics['sharpe_ratio'],
                abs(sol_metrics['max_drawdown_percent'])
            ]
            usdc_values = [
                usdc_metrics['total_pnl_usdc'],
                usdc_metrics['win_rate'] * 100,
                usdc_metrics['sharpe_ratio'],
                abs(usdc_metrics['max_drawdown_percent'])
            ]
            
            fig = go.Figure()
            
            # Add bars for SOL metrics
            fig.add_trace(go.Bar(
                name='SOL Denomination',
                x=metrics,
                y=sol_values,
                marker_color='#FF6B35',
                hovertemplate='%{x}<br>SOL: %{y:.3f}<extra></extra>'
            ))
            
            # Add bars for USDC metrics (normalized for comparison)
            # Normalize USDC PnL to SOL equivalent for better visualization
            usdc_values_normalized = usdc_values.copy()
            if len(portfolio_analysis['raw_data']['sol_rates']) > 0:
                avg_sol_price = sum(portfolio_analysis['raw_data']['sol_rates'].values()) / len(portfolio_analysis['raw_data']['sol_rates'])
                usdc_values_normalized[0] = usdc_values[0] / avg_sol_price  # Convert USDC PnL to SOL equivalent
                
            fig.add_trace(go.Bar(
                name='USDC Denomination',
                x=metrics,
                y=usdc_values_normalized,
                marker_color='#004E89',
                hovertemplate='%{x}<br>USDC: %{y:.3f}<extra></extra>'
            ))
            
            fig.update_layout(
                title="Portfolio Metrics Comparison",
                xaxis_title="Metrics",
                yaxis_title="Value",
                barmode='group',
                template='plotly_white',
                height=400
            )
            
            return pyo.plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create metrics summary chart: {e}")
            return f"<p>Error creating metrics chart: {str(e)}</p>"
            
    def _create_correlation_chart(self, correlation_analysis: Dict[str, Any]) -> str:
        """Create market correlation visualization."""
        try:
            raw_data = correlation_analysis['raw_data']
            portfolio_daily = raw_data['portfolio_daily_returns']
            sol_daily = raw_data['sol_daily_data']
            
            # Align data
            common_dates = portfolio_daily.index.intersection(sol_daily.index)
            portfolio_aligned = portfolio_daily.loc[common_dates]
            sol_aligned = sol_daily.loc[common_dates, 'daily_return']
            
            # Create scatter plot
            fig = go.Figure()
            
            fig.add_trace(go.Scatter(
                x=sol_aligned,
                y=portfolio_aligned,
                mode='markers',
                name='Daily Returns',
                marker=dict(
                    size=8,
                    color=portfolio_aligned,
                    colorscale='RdYlGn',
                    showscale=True,
                    colorbar=dict(title="Portfolio Return")
                ),
                hovertemplate='SOL Return: %{x:.2%}<br>Portfolio Return: %{y:.3f} SOL<extra></extra>'
            ))
            
            # Add trend line
            z = np.polyfit(sol_aligned, portfolio_aligned, 1)
            p = np.poly1d(z)
            
            fig.add_trace(go.Scatter(
                x=sol_aligned,
                y=p(sol_aligned),
                mode='lines',
                name='Trend Line',
                line=dict(color='red', width=2, dash='dash')
            ))
            
            # Add correlation info
            corr_metrics = correlation_analysis['correlation_metrics']
            
            fig.update_layout(
                title=f"Portfolio vs SOL Correlation (r={corr_metrics['pearson_correlation']:.3f}, p={corr_metrics['pearson_p_value']:.3f})",
                xaxis_title="SOL Daily Return",
                yaxis_title="Portfolio Daily Return (SOL)",
                template='plotly_white',
                height=500
            )
            
            return pyo.plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create correlation chart: {e}")
            return f"<p>Error creating correlation chart: {str(e)}</p>"
            
    def _create_trend_performance_chart(self, correlation_analysis: Dict[str, Any]) -> str:
        """Create trend-based performance chart."""
        try:
            trend_analysis = correlation_analysis['trend_analysis']
            
            # Prepare data
            trends = ['Uptrend', 'Downtrend']
            returns = [
                trend_analysis['uptrend']['mean_return'],
                trend_analysis['downtrend']['mean_return']
            ]
            win_rates = [
                trend_analysis['uptrend']['win_rate'] * 100,
                trend_analysis['downtrend']['win_rate'] * 100
            ]
            days = [
                trend_analysis['uptrend']['days'],
                trend_analysis['downtrend']['days']
            ]
            
            # Create subplot
            fig = make_subplots(
                rows=1, cols=3,
                subplot_titles=('Average Daily Return', 'Win Rate (%)', 'Days Count'),
                specs=[[{"type": "bar"}, {"type": "bar"}, {"type": "bar"}]]
            )
            
            # Average returns
            fig.add_trace(
                go.Bar(x=trends, y=returns, name='Avg Return', marker_color=['#4CAF50', '#F44336']),
                row=1, col=1
            )
            
            # Win rates
            fig.add_trace(
                go.Bar(x=trends, y=win_rates, name='Win Rate', marker_color=['#2196F3', '#FF9800']),
                row=1, col=2
            )
            
            # Days count
            fig.add_trace(
                go.Bar(x=trends, y=days, name='Days', marker_color=['#9C27B0', '#607D8B']),
                row=1, col=3
            )
            
            fig.update_layout(
                title="Performance by SOL Market Trend",
                template='plotly_white',
                showlegend=False,
                height=400
            )
            
            return pyo.plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create trend performance chart: {e}")
            return f"<p>Error creating trend performance chart: {str(e)}</p>"
            
    def _create_weekend_comparison_chart(self, weekend_analysis: Dict[str, Any]) -> str:
        """Create weekend parameter comparison chart."""
        try:
            comparison = weekend_analysis['performance_comparison']
            
            original = comparison['original_scenario']['metrics']
            simulated = comparison['simulated_scenario']['metrics']
            
            metrics = ['Total PnL', 'Average ROI (%)', 'Win Rate (%)', 'Sharpe Ratio']
            original_values = [
                original['total_pnl'],
                original['average_roi'] * 100,
                original['win_rate'] * 100,
                original['sharpe_ratio']
            ]
            simulated_values = [
                simulated['total_pnl'],
                simulated['average_roi'] * 100,
                simulated['win_rate'] * 100,
                simulated['sharpe_ratio']
            ]
            
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name='Current (No Weekend Parameter)',
                x=metrics,
                y=original_values,
                marker_color='#FF6B35'
            ))
            
            fig.add_trace(go.Bar(
                name='With Weekend Parameter',
                x=metrics,
                y=simulated_values,
                marker_color='#004E89'
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
            logger.error(f"Failed to create weekend comparison chart: {e}")
            return f"<p>Error creating weekend comparison chart: {str(e)}</p>"
            
    def _create_weekend_distribution_chart(self, weekend_analysis: Dict[str, Any]) -> str:
        """Create weekend position distribution chart."""
        try:
            classification = weekend_analysis['position_classification']
            
            # Create pie chart for weekend vs weekday
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
            logger.error(f"Failed to create weekend distribution chart: {e}")
            return f"<p>Error creating weekend distribution chart: {str(e)}</p>"
            
    def _prepare_template_data(self, 
                             portfolio_analysis: Dict[str, Any],
                             correlation_analysis: Optional[Dict[str, Any]],
                             weekend_analysis: Optional[Dict[str, Any]],
                             charts: Dict[str, str]) -> Dict[str, Any]:
        """Prepare data for HTML template."""
        
        template_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'portfolio_analysis': portfolio_analysis,
            'correlation_analysis': correlation_analysis,
            'weekend_analysis': weekend_analysis,
            'charts': charts,
            'plotly_js': pyo.get_plotlyjs()  # Include Plotly.js for interactivity
        }
        
        return template_data
        
    def _render_html_template(self, template_data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        
        # HTML template as string (inline for simplicity)
        html_template = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Portfolio Analytics Report</title>
    <script>{{ plotly_js|safe }}</script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f8f9fa;
            color: #2c3e50;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 20px;
        }
        .section {
            margin: 30px 0;
            padding: 20px;
            border-left: 4px solid #3498db;
            background-color: #f8f9fa;
        }
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric-card {
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            text-align: center;
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #2c3e50;
        }
        .metric-label {
            color: #7f8c8d;
            margin-top: 5px;
        }
        .chart-container {
            margin: 20px 0;
            padding: 15px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }
        .recommendation {
            background: #e8f5e8;
            border: 1px solid #4caf50;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
        .warning {
            background: #fff3cd;
            border: 1px solid #ffc107;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
        .error {
            background: #f8d7da;
            border: 1px solid #dc3545;
            padding: 15px;
            border-radius: 5px;
            margin: 15px 0;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚀 Portfolio Analytics Report</h1>
            <p>Generated on {{ timestamp }}</p>
        </div>

        <!-- Executive Summary -->
        <div class="section">
            <h2>📊 Executive Summary</h2>
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">{{ "%.3f"|format(portfolio_analysis.sol_denomination.total_pnl_sol) }}</div>
                    <div class="metric-label">Total PnL (SOL)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f"|format(portfolio_analysis.usdc_denomination.total_pnl_usdc) }}</div>
                    <div class="metric-label">Total PnL (USDC)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(portfolio_analysis.sol_denomination.win_rate * 100) }}%</div>
                    <div class="metric-label">Win Rate</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.2f"|format(portfolio_analysis.sol_denomination.sharpe_ratio) }}</div>
                    <div class="metric-label">Sharpe Ratio</div>
                </div>
            </div>
        </div>

        <!-- Portfolio Performance -->
        <div class="section">
            <h2>📈 Portfolio Performance</h2>
            <div class="chart-container">
                {{ charts.equity_curve|safe }}
            </div>
            <div class="chart-container">
                {{ charts.metrics_summary|safe }}
            </div>
        </div>

        <!-- Market Correlation Analysis -->
        {% if correlation_analysis and 'error' not in correlation_analysis %}
        <div class="section">
            <h2>🔗 Market Correlation Analysis</h2>
            <div class="recommendation">
                <strong>SOL Correlation:</strong> {{ "%.3f"|format(correlation_analysis.correlation_metrics.pearson_correlation) }}
                (p-value: {{ "%.3f"|format(correlation_analysis.correlation_metrics.pearson_p_value) }})
                {% if correlation_analysis.correlation_metrics.is_significant %}
                - <strong>Statistically Significant</strong>
                {% else %}
                - Not statistically significant
                {% endif %}
            </div>
            
            <div class="chart-container">
                {{ charts.correlation_analysis|safe }}
            </div>
            
            {% if 'trend_performance' in charts %}
            <div class="chart-container">
                {{ charts.trend_performance|safe }}
            </div>
            {% endif %}
            
            <h3>Trend Analysis Results:</h3>
            <ul>
                <li><strong>Uptrend Performance:</strong> 
                    {{ "%.4f"|format(correlation_analysis.trend_analysis.uptrend.mean_return) }} SOL/day 
                    ({{ correlation_analysis.trend_analysis.uptrend.days }} days,
                    {{ "%.1f"|format(correlation_analysis.trend_analysis.uptrend.win_rate * 100) }}% win rate)
                </li>
                <li><strong>Downtrend Performance:</strong> 
                    {{ "%.4f"|format(correlation_analysis.trend_analysis.downtrend.mean_return) }} SOL/day 
                    ({{ correlation_analysis.trend_analysis.downtrend.days }} days,
                    {{ "%.1f"|format(correlation_analysis.trend_analysis.downtrend.win_rate * 100) }}% win rate)
                </li>
            </ul>
        </div>
        {% elif correlation_analysis and 'error' in correlation_analysis %}
        <div class="section">
            <h2>🔗 Market Correlation Analysis</h2>
            <div class="error">
                <strong>Error:</strong> {{ correlation_analysis.error }}
            </div>
        </div>
        {% endif %}

        <!-- Weekend Parameter Analysis -->
        {% if weekend_analysis and 'error' not in weekend_analysis %}
        <div class="section">
            <h2>📅 Weekend Parameter Analysis</h2>
            
            {% set recommendation = weekend_analysis.recommendations.primary_recommendation %}
            {% if recommendation == 'ENABLE' %}
            <div class="recommendation">
                <strong>Recommendation: ENABLE Weekend Parameter</strong><br>
                Expected Impact: {{ "%.3f"|format(weekend_analysis.performance_comparison.impact_analysis.total_pnl_difference_sol) }} SOL
                ({{ "%.1f"|format(weekend_analysis.performance_comparison.impact_analysis.pnl_improvement_percent) }}% improvement)
            </div>
            {% else %}
            <div class="warning">
                <strong>Recommendation: DISABLE Weekend Parameter</strong><br>
                Current performance would decrease by {{ "%.3f"|format(weekend_analysis.performance_comparison.impact_analysis.total_pnl_difference_sol|abs) }} SOL
                ({{ "%.1f"|format(weekend_analysis.performance_comparison.impact_analysis.pnl_improvement_percent|abs) }}% reduction)
            </div>
            {% endif %}
            
            <p><strong>Confidence Level:</strong> {{ weekend_analysis.recommendations.confidence_level }}</p>
            <p>{{ weekend_analysis.recommendations.explanation }}</p>
            
            <div class="chart-container">
                {{ charts.weekend_comparison|safe }}
            </div>
            
            {% if 'weekend_distribution' in charts %}
            <div class="chart-container">
                {{ charts.weekend_distribution|safe }}
            </div>
            {% endif %}
            
            <h3>Position Classification:</h3>
            <ul>
                <li><strong>Weekend Opened:</strong> 
                    {{ weekend_analysis.position_classification.weekend_opened.count }} positions 
                    ({{ "%.1f"|format(weekend_analysis.position_classification.weekend_opened.percentage) }}%)
                </li>
                <li><strong>Weekday Opened:</strong> 
                    {{ weekend_analysis.position_classification.weekday_opened.count }} positions 
                    ({{ "%.1f"|format(weekend_analysis.position_classification.weekday_opened.percentage) }}%)
                </li>
            </ul>
        </div>
        {% elif weekend_analysis and 'error' in weekend_analysis %}
        <div class="section">
            <h2>📅 Weekend Parameter Analysis</h2>
            <div class="error">
                <strong>Error:</strong> {{ weekend_analysis.error }}
            </div>
        </div>
        {% endif %}

        <!-- Infrastructure Cost Impact -->
        <div class="section">
            <h2>💰 Infrastructure Cost Impact</h2>
            {% set cost_impact = portfolio_analysis.infrastructure_cost_impact %}
            <div class="metrics-grid">
                <div class="metric-card">
                    <div class="metric-value">${{ "%.2f"|format(cost_impact.total_cost_usd) }}</div>
                    <div class="metric-label">Total Cost (USD)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.3f"|format(cost_impact.total_cost_sol) }}</div>
                    <div class="metric-label">Total Cost (SOL)</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.1f"|format(cost_impact.cost_impact_percent) }}%</div>
                    <div class="metric-label">Cost Impact</div>
                </div>
                <div class="metric-card">
                    <div class="metric-value">{{ "%.0f"|format(cost_impact.break_even_days) }}</div>
                    <div class="metric-label">Break-even Days</div>
                </div>
            </div>
            
            <p><strong>Daily Cost:</strong> ${{ "%.2f"|format(cost_impact.daily_cost_usd) }} 
               ({{ "%.4f"|format(cost_impact.daily_cost_sol) }} SOL)</p>
        </div>

        <!-- Recommendations -->
        <div class="section">
            <h2>🎯 Key Recommendations</h2>
            <ul>
                {% if correlation_analysis and 'error' not in correlation_analysis %}
                <li><strong>Market Correlation:</strong>
                    {% if correlation_analysis.correlation_metrics.pearson_correlation > 0.3 and correlation_analysis.correlation_metrics.is_significant %}
                    Strong positive correlation with SOL - strategy performs better during SOL uptrends
                    {% elif correlation_analysis.correlation_metrics.pearson_correlation < -0.3 and correlation_analysis.correlation_metrics.is_significant %}
                    Strong negative correlation with SOL - strategy performs better during SOL downtrends
                    {% elif correlation_analysis.correlation_metrics.is_significant %}
                    Weak but significant correlation - monitor SOL market trends
                    {% else %}
                    No significant correlation with SOL market trends detected
                    {% endif %}
                </li>
                {% endif %}
                
                {% if weekend_analysis and 'error' not in weekend_analysis %}
                <li><strong>Weekend Parameter:</strong> 
                    {{ weekend_analysis.recommendations.primary_recommendation }} the weekendSizePercentage parameter
                    for an expected impact of {{ "%.3f"|format(weekend_analysis.performance_comparison.impact_analysis.total_pnl_difference_sol) }} SOL
                </li>
                {% endif %}
                
                <li><strong>Infrastructure Costs:</strong> 
                    Current costs represent {{ "%.1f"|format(portfolio_analysis.infrastructure_cost_impact.cost_impact_percent) }}% 
                    of gross performance - consider optimization if above 15%
                </li>
                
                <li><strong>Risk Management:</strong> 
                    Current Sharpe ratio of {{ "%.2f"|format(portfolio_analysis.sol_denomination.sharpe_ratio) }}
                    {% if portfolio_analysis.sol_denomination.sharpe_ratio > 1.0 %}
                    indicates good risk-adjusted returns
                    {% elif portfolio_analysis.sol_denomination.sharpe_ratio > 0.5 %}
                    indicates acceptable risk-adjusted returns
                    {% else %}
                    suggests room for improvement in risk management
                    {% endif %}
                </li>
            </ul>
        </div>

        <!-- Technical Details -->
        <div class="section">
            <h2>🔧 Technical Details</h2>
            <p><strong>Analysis Period:</strong> {{ portfolio_analysis.analysis_metadata.start_date }} to {{ portfolio_analysis.analysis_metadata.end_date }} 
               ({{ portfolio_analysis.analysis_metadata.analysis_period_days }} days)</p>
            <p><strong>Positions Analyzed:</strong> {{ portfolio_analysis.analysis_metadata.positions_analyzed }}</p>
            {% if correlation_analysis and 'error' not in correlation_analysis %}
            <p><strong>Market Data:</strong> {{ correlation_analysis.correlation_metrics.common_days }} days of SOL price data</p>
            <p><strong>EMA Period:</strong> {{ correlation_analysis.analysis_metadata.ema_period }} days</p>
            {% endif %}
            {% if weekend_analysis and 'error' not in weekend_analysis %}
            <p><strong>Weekend Definition:</strong> Saturday-Sunday UTC</p>
            <p><strong>Size Multiplier:</strong> {{ "%.1f"|format(weekend_analysis.analysis_metadata.size_multiplier) }}x simulation</p>
            {% endif %}
        </div>

        <!-- Footer -->
        <div class="section" style="text-align: center; margin-top: 50px; border: none; background: none;">
            <p style="color: #7f8c8d; font-size: 0.9em;">
                Report generated by Portfolio Analytics System v1.0<br>
                Data sources: Position logs, Moralis API (SOL/USDC rates)<br>
                <em>This analysis is for informational purposes only and should not be considered financial advice.</em>
            </p>
        </div>
    </div>
</body>
</html>
        """
        
        # Render template
        template = Template(html_template)
        return template.render(**template_data)


if __name__ == "__main__":
    # Test HTML report generator
    print("HTML Report Generator module ready for integration")
