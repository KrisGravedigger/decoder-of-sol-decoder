import logging
import os
from datetime import datetime
from typing import Dict, Any, Optional
import yaml
import pandas as pd

from .infrastructure_cost_analyzer import InfrastructureCostAnalyzer
from .data_loader import load_and_prepare_positions
from .metrics_calculator import (
    calculate_daily_returns, calculate_sol_metrics, calculate_usdc_metrics, calculate_currency_comparison
)
from .text_reporter import generate_portfolio_and_cost_reports

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class PortfolioAnalytics:
    def __init__(self, config_path: str, api_key: Optional[str] = None):
        self.config = self._load_config(config_path)
        # AIDEV-NOTE-CLAUDE: API key is now passed to the cost analyzer.
        self.cost_analyzer = InfrastructureCostAnalyzer(config_path, api_key=api_key)
        self.min_threshold = self.config.get('portfolio_analysis', {}).get('min_position_threshold', 0.01)
        self.output_dir = "reporting/output"
        os.makedirs(os.path.join(self.output_dir, "charts"), exist_ok=True)
        logger.info("Portfolio Analytics initialized")

    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file {config_path} not found. Using empty config.")
            return {}

    def analyze_dataframe(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        if positions_df.empty:
            return {'error': 'No positions data available'}

        try:
            positions_df = self.cost_analyzer.allocate_costs_to_positions(positions_df)
        except ValueError as e:
            # Handle case where cost analyzer fails due to missing API key
            return {'error': str(e)}

        min_date, max_date = positions_df['open_timestamp'].min(), positions_df['close_timestamp'].max()
        period_days = (max_date - min_date).days
        
        sol_rates = self.cost_analyzer.get_sol_usdc_rates(min_date.strftime("%Y-%m-%d"), max_date.strftime("%Y-%m-%d"))
        if not sol_rates:
            logger.warning("No SOL/USDC rates found. USDC metrics will be incomplete.")

        daily_df = calculate_daily_returns(positions_df)

        risk_free_rates = self.config.get('portfolio_analysis', {}).get('risk_free_rates', {'sol_staking': 0.05, 'usdc_staking': 0.03})
        sol_metrics = calculate_sol_metrics(positions_df, daily_df, risk_free_rates['sol_staking'])
        usdc_metrics = calculate_usdc_metrics(positions_df, sol_rates, risk_free_rates['usdc_staking'])
        currency_comparison = calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics, positions_df)
        cost_summary = self.cost_analyzer.generate_cost_summary(positions_df, period_days)

        return {
            'analysis_metadata': {
                'generated_timestamp': datetime.now().isoformat(), 'analysis_period_days': period_days,
                'start_date': min_date.strftime("%Y-%m-%d"), 'end_date': max_date.strftime("%Y-%m-%d"),
                'positions_analyzed': len(positions_df)
            },
            'sol_denomination': sol_metrics, 'usdc_denomination': usdc_metrics,
            'currency_comparison': currency_comparison, 'infrastructure_cost_impact': cost_summary,
            'raw_data': {'positions_df': positions_df, 'daily_returns_df': daily_df, 'sol_rates': sol_rates}
        }

    def generate_and_save_reports(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        timestamp_format = self.config.get('visualization', {}).get('timestamp_format', '%Y%m%d_%H%M%S')
        timestamp = datetime.now().strftime(timestamp_format)
        portfolio_summary, infrastructure_impact = generate_portfolio_and_cost_reports(analysis_result)
        saved_files = {}
        try:
            portfolio_file = os.path.join(self.output_dir, f"portfolio_summary_{timestamp}.txt")
            with open(portfolio_file, 'w') as f: f.write(portfolio_summary)
            saved_files['portfolio_summary'] = portfolio_file
            
            infra_file = os.path.join(self.output_dir, f"infrastructure_impact_{timestamp}.txt")
            with open(infra_file, 'w') as f: f.write(infrastructure_impact)
            saved_files['infrastructure_impact'] = infra_file
        except Exception as e:
            logger.error(f"Failed to save reports: {e}")
        return saved_files