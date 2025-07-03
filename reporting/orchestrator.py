"""
Portfolio Analysis Orchestrator Module

Coordinates the complete portfolio analysis workflow by integrating various
analysis components and generating comprehensive reports.
"""

import logging
import os
import sys
import yaml
from datetime import datetime
from typing import Dict, Any, Tuple, List, Optional

# AIDEV-NOTE-CLAUDE: This ensures project root is on the path for module resolution
# Corrected path to handle nested structure
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from reporting.portfolio_analytics import PortfolioAnalytics
from reporting.chart_generator import ChartGenerator
from reporting.market_correlation_analyzer import MarketCorrelationAnalyzer
from reporting.html_report_generator import HTMLReportGenerator
from reporting.data_loader import load_and_prepare_positions
from reporting.text_reporter import generate_portfolio_and_cost_reports, generate_weekend_simulation_report
from simulations.weekend_simulator import WeekendSimulator
from reporting.strategy_instance_detector import run_instance_detection
from reporting.analysis_runner import AnalysisRunner

logger = logging.getLogger(__name__)

class PortfolioAnalysisOrchestrator:
    """Main orchestrator for complete portfolio analysis workflow."""
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml", api_key: Optional[str] = None):
        """Initialize orchestrator."""
        self.config_path = config_path
        self.config = self._load_config()
        # AIDEV-NOTE-CLAUDE: API key is now passed during initialization.
        self.api_key = api_key
        if not self.api_key:
            logger.warning("API key not provided to orchestrator. API-dependent features may fail.")
        
        # AIDEV-NOTE-CLAUDE: Pass the API key to downstream analytics modules.
        self.analytics = PortfolioAnalytics(self.config_path, api_key=self.api_key)
        self.chart_generator = ChartGenerator(self.config_path)
        self.output_dir = "reporting/output"
        logger.info("Portfolio Analysis Orchestrator initialized")
        
    def _load_config(self) -> Dict:
        """Load YAML configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {self.config_path}, using defaults")
            return {}

    def _should_skip_weekend_analysis(self) -> Tuple[bool, str]:
        """Check if weekend analysis should be skipped."""
        weekend_config = self.config.get('weekend_analysis', {})
        size_reduction_percentage = weekend_config.get('size_reduction_percentage', 80)
        
        if size_reduction_percentage == 0:
            return True, "size_reduction_percentage set to 0 in configuration"
        return False, ""

    def run_comprehensive_analysis(self, positions_file: str) -> Dict[str, Any]:
        """Run comprehensive analysis including portfolio, correlation, weekend, and HTML report."""
        if not self.api_key and not self.config.get('api_settings', {}).get('cache_only', False):
            return {'status': 'ERROR', 'error': 'API key is missing and not in cache-only mode.'}

        logger.info("=" * 60)
        logger.info("STARTING COMPREHENSIVE ANALYSIS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # AIDEV-NOTE-CLAUDE: Ensure strategy instances are up-to-date before reporting.
            logger.info("Step 0: Running strategy instance detection...")
            run_instance_detection()

            positions_df = load_and_prepare_positions(positions_file, self.analytics.min_threshold)
            if positions_df.empty:
                return {'status': 'ERROR', 'error': 'No positions data after loading'}

            logger.info("Step 1: Running portfolio analysis...")
            portfolio_result = self.analytics.analyze_dataframe(positions_df)
            if 'error' in portfolio_result: return {'status': 'ERROR', **portfolio_result}
            
            # --- Text and Chart Generation (Portfolio) ---
            logger.info("Step 1a: Generating portfolio reports and charts...")
            report_files, timestamp = self._generate_portfolio_reports(portfolio_result)
            chart_files = self.chart_generator.generate_all_charts(portfolio_result)

            # AIDEV-CLAUDE-ADDITION: New step for Spot vs. Bid-Ask analysis
            logger.info("Step 1b: Running Spot vs. Bid-Ask strategy simulations...")
            strategy_simulator = AnalysisRunner(api_key=self.api_key)
            strategy_simulation_results = strategy_simulator.analyze_all_positions(positions_df)

            logger.info("Step 2: Running market correlation analysis...")
            correlation_analyzer = MarketCorrelationAnalyzer(self.config_path, api_key=self.api_key)
            correlation_result = correlation_analyzer.analyze_market_correlation(positions_df)
            
            logger.info("Step 3: Running weekend parameter simulation...")
            skip_weekend, skip_reason = self._should_skip_weekend_analysis()
            
            if skip_weekend:
                logger.warning(f"Weekend simulation SKIPPED: {skip_reason}")
                weekend_result = {'analysis_skipped': True, 'reason': skip_reason}
            else:
                weekend_simulator = WeekendSimulator(self.config_path)
                weekend_result = weekend_simulator.run_simulation(positions_df)
                weekend_report_path = self._generate_weekend_report(weekend_result, timestamp)
                if weekend_report_path:
                    report_files['weekend_simulation'] = weekend_report_path

            logger.info("Step 4: Generating comprehensive HTML report...")
            html_generator = HTMLReportGenerator()
            html_file = html_generator.generate_comprehensive_report(
                portfolio_analysis=portfolio_result,
                # AIDEV-CLAUDE-ADDITION: Pass new results to HTML generator
                strategy_simulations=strategy_simulation_results,
                correlation_analysis=correlation_result,
                weekend_analysis=weekend_result
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            comprehensive_result = {
                'status': 'SUCCESS', 'execution_time_seconds': execution_time,
                'portfolio_analysis': portfolio_result,
                'strategy_simulations': strategy_simulation_results, # Add this
                'correlation_analysis': correlation_result,
                'weekend_analysis': weekend_result,
                'files_generated': {'html_report': html_file, 'text_reports': report_files, 'charts': chart_files}
            }
            self._log_comprehensive_summary(comprehensive_result)
            return comprehensive_result

        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
            return {'status': 'ERROR', 'error': str(e)}

    def _generate_portfolio_reports(self, analysis_result: Dict[str, Any]) -> Tuple[Dict[str, str], str]:
        """Generate and save portfolio and cost text reports."""
        timestamp = datetime.now().strftime(self.config.get('visualization', {}).get('timestamp_format', '%Y%m%d_%H%M%S'))
        portfolio_summary, infrastructure_impact = generate_portfolio_and_cost_reports(analysis_result)
        
        saved_files = {}
        try:
            portfolio_file = os.path.join(self.output_dir, f"portfolio_summary_{timestamp}.txt")
            with open(portfolio_file, 'w') as f: f.write(portfolio_summary)
            saved_files['portfolio_summary'] = portfolio_file
            
            infra_file = os.path.join(self.output_dir, f"infrastructure_impact_{timestamp}.txt")
            with open(infra_file, 'w') as f: f.write(infrastructure_impact)
            saved_files['infrastructure_impact'] = infra_file

            logger.info("Successfully saved portfolio and cost reports.")
            return saved_files, timestamp
        except Exception as e:
            logger.error(f"Failed to save main reports: {e}")
            return {}, timestamp
            
    def _generate_weekend_report(self, weekend_result: Dict[str, Any], timestamp: str) -> Optional[str]:
        """Generate and save the weekend simulation text report."""
        report_content = generate_weekend_simulation_report(weekend_result)
        if report_content:
            try:
                filepath = os.path.join(self.output_dir, f"weekend_simulation_{timestamp}.txt")
                with open(filepath, 'w') as f: f.write(report_content)
                logger.info(f"Successfully saved weekend simulation report: {filepath}")
                return filepath
            except Exception as e:
                logger.error(f"Failed to save weekend report: {e}")
        return None

    def run_quick_analysis(self, positions_file: str) -> Dict[str, Any]:
        """Run quick analysis without chart generation."""
        if not self.api_key:
            return {'status': 'ERROR', 'error': 'API key is missing, cannot run quick analysis.'}
        logger.info("Running quick portfolio analysis (no charts)...")
        try:
            positions_df = load_and_prepare_positions(positions_file, self.analytics.min_threshold)
            analysis_result = self.analytics.analyze_dataframe(positions_df)
            if 'error' in analysis_result:
                return {'status': 'ERROR', **analysis_result}
            
            saved_files, _ = self._generate_portfolio_reports(analysis_result)
            return {'status': 'SUCCESS', 'files_generated': saved_files}

        except Exception as e:
            logger.error(f"Quick analysis failed: {e}", exc_info=True)
            return {'status': 'ERROR', 'error': str(e)}
            
    def analyze_specific_period(self, start_date_str: str, end_date_str: str, positions_file: str):
        """Placeholder for period-specific analysis."""
        logger.info(f"Analyzing from {start_date_str} to {end_date_str}. This feature is not fully implemented yet.")
        # Future implementation would filter positions_df by date and run analysis.
        pass

    def _log_comprehensive_summary(self, result: Dict[str, Any]):
        """Log a summary of the comprehensive analysis."""
        logger.info("COMPREHENSIVE ANALYSIS SUMMARY:")
        sol_metrics = result.get('portfolio_analysis', {}).get('sol_denomination', {})
        logger.info(f"  Portfolio PnL: {sol_metrics.get('total_pnl_sol', 0):+.3f} SOL, Sharpe: {sol_metrics.get('sharpe_ratio', 0):.2f}")
        
        corr_metrics = result.get('correlation_analysis', {}).get('correlation_metrics', {})
        if corr_metrics:
            logger.info(f"  SOL Correlation: {corr_metrics.get('pearson_correlation', 0):.3f}")
            
        weekend_result = result.get('weekend_analysis', {})
        if weekend_result.get('analysis_skipped'):
            logger.info(f"  Weekend Simulation: SKIPPED ({weekend_result.get('reason')})")
        elif 'error' not in weekend_result:
            rec = weekend_result.get('recommendations', {})
            logger.info(f"  Weekend Param Rec: {rec.get('primary_recommendation', 'N/A')}")
            
        logger.info(f"  HTML Report: {result.get('files_generated', {}).get('html_report', 'N/A')}")
        logger.info(f"  Execution Time: {result.get('execution_time_seconds', 0):.1f} seconds")