"""
Portfolio Analytics Engine for LP Strategy Analysis

Implements dual currency analysis (SOL/USDC) with risk-adjusted metrics
and infrastructure cost impact assessment.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Tuple, Any
import yaml

from infrastructure_cost_analyzer import InfrastructureCostAnalyzer
from data_loader import load_and_prepare_positions
from metrics_calculator import (
    calculate_daily_returns,
    calculate_sol_metrics,
    calculate_usdc_metrics,
    calculate_currency_comparison
)
from text_reporter import generate_text_reports

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioAnalytics:
    """
    Main portfolio analytics engine for LP strategy performance analysis.

    Orchestrates data loading, cost analysis, and metrics calculation to
    provide a comprehensive performance overview.
    """

    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize portfolio analytics engine.

        Args:
            config_path (str): Path to YAML configuration file.
        """
        self.config = self._load_config(config_path)
        self.cost_analyzer = InfrastructureCostAnalyzer(config_path)
        self.min_threshold = self.config['portfolio_analysis']['min_position_threshold']
        self.output_dir = "reporting/output"
        self._ensure_output_directory()
        logger.info("Portfolio Analytics initialized")

    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration with error handling."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise

    def _ensure_output_directory(self):
        """Create output directory structure if it doesn't exist."""
        charts_dir = os.path.join(self.output_dir, "charts")
        for directory in [self.output_dir, charts_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logger.info(f"Created directory: {directory}")

    def _generate_timestamp(self) -> str:
        """Generate timestamp for output files."""
        return datetime.now().strftime(self.config['visualization']['timestamp_format'])

    def analyze_portfolio(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Perform complete portfolio analysis with dual currency metrics.

        Args:
            positions_file (str): Path to positions CSV file.

        Returns:
            Dict[str, Any]: Complete portfolio analysis results.
        """
        logger.info("Starting portfolio analysis...")
        
        # Load and prepare data using the external data loader
        positions_df = load_and_prepare_positions(positions_file, self.min_threshold)
        if positions_df.empty:
            logger.warning("No positions data available for analysis")
            return {'error': 'No positions data available'}

        # Allocate costs and get date range
        positions_df = self.cost_analyzer.allocate_costs_to_positions(positions_df)
        min_date = positions_df['open_timestamp'].min().strftime("%Y-%m-%d")
        max_date = positions_df['close_timestamp'].max().strftime("%Y-%m-%d")
        period_days = (positions_df['close_timestamp'].max() - positions_df['open_timestamp'].min()).days
        
        sol_rates = self.cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        daily_df = calculate_daily_returns(positions_df)

        # Calculate metrics using external calculator
        sol_metrics = calculate_sol_metrics(positions_df, daily_df, self.config['portfolio_analysis']['risk_free_rates']['sol_staking'])
        usdc_metrics = calculate_usdc_metrics(positions_df, sol_rates, self.config['portfolio_analysis']['risk_free_rates']['usdc_staking'])
        currency_comparison = calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics, positions_df)
        cost_summary = self.cost_analyzer.generate_cost_summary(positions_df, period_days)

        # Compile complete analysis
        analysis_result = {
            'analysis_metadata': {
                'generated_timestamp': datetime.now().isoformat(),
                'analysis_period_days': period_days, 'start_date': min_date,
                'end_date': max_date, 'positions_analyzed': len(positions_df)
            },
            'sol_denomination': sol_metrics,
            'usdc_denomination': usdc_metrics,
            'currency_comparison': currency_comparison,
            'infrastructure_cost_impact': cost_summary,
            'raw_data': {'positions_df': positions_df, 'daily_returns_df': daily_df, 'sol_rates': sol_rates}
        }
        
        logger.info("Portfolio analysis completed successfully")
        return analysis_result

    def generate_and_save_reports(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate and save analysis reports to timestamped files.

        Args:
            analysis_result (Dict[str, Any]): Complete analysis results.

        Returns:
            Dict[str, str]: Dictionary of saved file paths.
        """
        timestamp = self._generate_timestamp()
        portfolio_summary, infrastructure_impact = generate_text_reports(analysis_result)

        portfolio_file = os.path.join(self.output_dir, f"portfolio_summary_{timestamp}.txt")
        infrastructure_file = os.path.join(self.output_dir, f"infrastructure_impact_{timestamp}.txt")
        
        try:
            with open(portfolio_file, 'w') as f: f.write(portfolio_summary)
            logger.info(f"Saved portfolio summary: {portfolio_file}")
            
            with open(infrastructure_file, 'w') as f: f.write(infrastructure_impact)
            logger.info(f"Saved infrastructure impact: {infrastructure_file}")
            
            return {'portfolio_summary': portfolio_file, 'infrastructure_impact': infrastructure_file, 'timestamp': timestamp}
        except Exception as e:
            logger.error(f"Failed to save reports: {e}")
            raise

    def analyze_and_report(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Complete analysis workflow: analyze portfolio and generate reports.
        """
        analysis_result = self.analyze_portfolio(positions_file)
        if 'error' in analysis_result:
            return analysis_result
            
        saved_files = self.generate_and_save_reports(analysis_result)
        
        complete_result = {**analysis_result, 'saved_files': saved_files}
        if 'raw_data' in complete_result:
            del complete_result['raw_data']
            
        logger.info("Portfolio analysis and reporting completed")
        return complete_result


if __name__ == "__main__":
    try:
        analytics = PortfolioAnalytics()
        result = analytics.analyze_and_report()
        
        print("Analysis completed successfully!")
        print(f"Files saved: {result.get('saved_files', {})}")
        
        if 'sol_denomination' in result:
            sol = result['sol_denomination']
            print("\nKey Results:")
            print(f"Total PnL: {sol.get('total_pnl_sol', 0):+.2f} SOL")
            print(f"Sharpe Ratio: {sol.get('sharpe_ratio', 0):.2f}")
            print(f"Win Rate: {sol.get('win_rate', 0)*100:.1f}%")
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Error: {e}")