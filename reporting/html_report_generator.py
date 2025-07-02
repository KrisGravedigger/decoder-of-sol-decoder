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
from datetime import datetime
from typing import Dict, Any, Optional
import plotly.offline as pyo
from jinja2 import Environment, FileSystemLoader

from visualizations import interactive_charts

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
        
        # Setup Jinja2 environment
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))

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
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            charts = self._generate_interactive_charts(
                portfolio_analysis, correlation_analysis, weekend_analysis
            )
            
            template_data = self._prepare_template_data(
                portfolio_analysis, correlation_analysis, weekend_analysis, charts
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
        
        charts['equity_curve'] = interactive_charts.create_equity_curve_chart(portfolio_analysis)
        charts['metrics_summary'] = interactive_charts.create_metrics_summary_chart(portfolio_analysis)
        
        if correlation_analysis and 'error' not in correlation_analysis:
            charts['correlation_analysis'] = interactive_charts.create_correlation_chart(correlation_analysis)
            charts['trend_performance'] = interactive_charts.create_trend_performance_chart(correlation_analysis)
            
        if weekend_analysis and 'error' not in weekend_analysis:
            charts['weekend_comparison'] = interactive_charts.create_weekend_comparison_chart(weekend_analysis)
            charts['weekend_distribution'] = interactive_charts.create_weekend_distribution_chart(weekend_analysis)
            
        return charts
            
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
            'plotly_js': pyo.get_plotlyjs()
        }
        
        return template_data
        
    def _render_html_template(self, template_data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        try:
            template = self.jinja_env.get_template('comprehensive_report.html')
            return template.render(**template_data)
        except Exception as e:
            logger.error(f"Failed to render HTML template: {e}")
            # AIDEV-NOTE-CLAUDE: Fallback to inline template is removed for clarity.
            # Production code should handle this gracefully.
            raise


if __name__ == "__main__":
    print("HTML Report Generator module ready for integration")