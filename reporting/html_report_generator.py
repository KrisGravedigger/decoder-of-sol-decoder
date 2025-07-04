"""
HTML Report Generator Module

Creates comprehensive interactive HTML reports combining:
- Portfolio analytics results
- Market correlation analysis
- Weekend parameter impact analysis
- Spot vs. Bid-Ask simulations
- Interactive charts and visualizations
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional, List
import plotly.offline as pyo
from jinja2 import Environment, FileSystemLoader

from .visualizations import interactive_charts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates comprehensive HTML reports with interactive charts.
    """
    
    def __init__(self, output_dir: str = "reporting/output"):
        """
        Initialize HTML report generator.
        """
        self.output_dir = output_dir
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(base_dir, "templates")
        self.timestamp_format = "%Y%m%d_%H%M"
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        logger.info("HTML Report Generator initialized")
        
    def generate_comprehensive_report(self, 
                                    portfolio_analysis: Dict[str, Any],
                                    correlation_analysis: Optional[Dict[str, Any]] = None,
                                    weekend_analysis: Optional[Dict[str, Any]] = None,
                                    # AIDEV-NOTE-CLAUDE: Added missing argument to accept new data.
                                    strategy_simulations: Optional[List[Dict]] = None) -> str:
        """
        Generate comprehensive HTML report combining all analyses.
        """
        logger.info("Generating comprehensive HTML report...")
        
        try:
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            charts = self._generate_interactive_charts(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations
            )
            
            template_data = self._prepare_template_data(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations, charts
            )
            
            html_content = self._render_html_template(template_data)
            
            filename = f"comprehensive_report_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Comprehensive HTML report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
            raise
            
    def _generate_interactive_charts(self, 
                                   portfolio_analysis: Dict[str, Any],
                                   correlation_analysis: Optional[Dict[str, Any]],
                                   weekend_analysis: Optional[Dict[str, Any]],
                                   # AIDEV-NOTE-CLAUDE: Accept new simulation data for charting.
                                   strategy_simulations: Optional[List[Dict]]) -> Dict[str, str]:
        """
        Generate interactive Plotly charts for the report.
        """
        charts = {}
        
        charts['equity_curve'] = interactive_charts.create_equity_curve_chart(portfolio_analysis)
        charts['metrics_summary'] = interactive_charts.create_metrics_summary_chart(portfolio_analysis)
        
        if correlation_analysis and 'error' not in correlation_analysis:
            charts['correlation_analysis'] = interactive_charts.create_correlation_chart(correlation_analysis)
            charts['trend_performance'] = interactive_charts.create_trend_performance_chart(correlation_analysis)
            
        if weekend_analysis and not weekend_analysis.get('analysis_skipped'):
             if 'error' not in weekend_analysis:
                charts['weekend_comparison'] = interactive_charts.create_weekend_comparison_chart(weekend_analysis)
                charts['weekend_distribution'] = interactive_charts.create_weekend_distribution_chart(weekend_analysis)
        
        # AIDEV-NOTE-CLAUDE: Generate the new charts for strategy simulations.
        if strategy_simulations:
            charts['strategy_simulation_comparison'] = interactive_charts.create_strategy_simulation_chart(strategy_simulations, portfolio_analysis)
        charts['strategy_heatmap'] = interactive_charts.create_strategy_heatmap_chart()

        return charts
            
    def _prepare_template_data(self, 
                             portfolio_analysis: Dict[str, Any],
                             correlation_analysis: Optional[Dict[str, Any]],
                             weekend_analysis: Optional[Dict[str, Any]],
                             strategy_simulations: Optional[List[Dict]],
                             charts: Dict[str, str]) -> Dict[str, Any]:
        """Prepare data for HTML template."""
        
        formatted_weekend_data = self._format_weekend_data(weekend_analysis)
        best_sim_strategy = self._get_best_sim_strategy(strategy_simulations)

        template_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'portfolio_analysis': portfolio_analysis,
            'correlation_analysis': correlation_analysis,
            'weekend_analysis': formatted_weekend_data, # Use formatted data
            'strategy_simulations': strategy_simulations,
            'best_sim_strategy': best_sim_strategy,
            'charts': charts,
            'plotly_js': pyo.get_plotlyjs()
        }
        
        return template_data

    def _format_weekend_data(self, weekend_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        """Formats the weekend analysis dictionary for easier rendering in Jinja2."""
        if not weekend_analysis or weekend_analysis.get('analysis_skipped') or 'error' in weekend_analysis:
            return {'is_valid': False, 'raw': weekend_analysis}
        
        # Extracting nested dictionaries for easier access in the template
        comparison = weekend_analysis.get('performance_comparison', {})
        return {
            'is_valid': True,
            'raw': weekend_analysis, # Keep raw data for flexibility
            'metadata': weekend_analysis.get('analysis_metadata', {}),
            'recommendations': weekend_analysis.get('recommendations', {}),
            'classification': weekend_analysis.get('position_classification', {}),
            'current_scenario': comparison.get('current_scenario', {}),
            'alternative_scenario': comparison.get('alternative_scenario', {}),
            'impact_analysis': comparison.get('impact_analysis', {}),
        }

    def _get_best_sim_strategy(self, simulation_results: Optional[List[Dict]]) -> Optional[Dict]:
        """Find the best overall simulated strategy."""
        if not simulation_results:
            return None
            
        sim_pnl = {}
        for res in simulation_results:
            if not res or 'simulation_results' not in res: continue
            for name, data in res['simulation_results'].items():
                if 'pnl_sol' in data:
                    sim_pnl[name] = sim_pnl.get(name, 0) + data['pnl_sol']
                    
        if not sim_pnl:
            return None
            
        best_name = max(sim_pnl, key=sim_pnl.get)
        return {'name': best_name, 'pnl': sim_pnl[best_name]}
        
    def _render_html_template(self, template_data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        try:
            template = self.jinja_env.get_template('comprehensive_report.html')
            return template.render(**template_data)
        except Exception as e:
            logger.error(f"Failed to render HTML template: {e}")
            raise