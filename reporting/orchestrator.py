"""
Portfolio Analysis Orchestrator Module

Coordinates the complete portfolio analysis workflow by integrating various
analysis components and generating comprehensive reports.
"""

import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any
import pandas as pd

# Add reporting module to path if not already there
# AIDEV-NOTE-CLAUDE: This ensures modules can be found when run from project root
script_dir = os.path.dirname(os.path.abspath(__file__))
if script_dir not in sys.path:
    sys.path.append(script_dir)

from portfolio_analytics import PortfolioAnalytics
from chart_generator import ChartGenerator
from market_correlation_analyzer import MarketCorrelationAnalyzer
from weekend_parameter_analyzer import WeekendParameterAnalyzer
from html_report_generator import HTMLReportGenerator
from data_loader import load_and_prepare_positions
from metrics_calculator import (
    calculate_daily_returns,
    calculate_sol_metrics,
    calculate_usdc_metrics,
    calculate_currency_comparison
)

logger = logging.getLogger(__name__)

class PortfolioAnalysisOrchestrator:
    """
    Main orchestrator for complete portfolio analysis workflow.
    
    Coordinates data loading, analysis, reporting, and visualization
    to provide comprehensive portfolio performance insights.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize portfolio analysis orchestrator.
        
        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = config_path
        self.analytics = None
        self.chart_generator = None
        self._initialize_components()
        logger.info("Portfolio Analysis Orchestrator initialized")
        
    def _initialize_components(self):
        """Initialize analysis components."""
        try:
            self.analytics = PortfolioAnalytics(self.config_path)
            self.chart_generator = ChartGenerator(self.config_path)
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise

    def run_comprehensive_analysis(self, positions_file: str) -> Dict[str, Any]:
        """
        Run comprehensive analysis including portfolio, correlation, weekend analysis and HTML report.
        
        AIDEV-NOTE-CLAUDE: Optimized to load CSV only once - major performance improvement
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Complete comprehensive analysis results
        """
        logger.info("=" * 60)
        logger.info("STARTING COMPREHENSIVE ANALYSIS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            logger.info("Step 0: Loading and preparing positions data...")
            positions_df = load_and_prepare_positions(positions_file, self.analytics.min_threshold)
            if positions_df.empty:
                return {'error': f'No positions data after loading and preparing from {positions_file}'}

            logger.info("Step 1: Running portfolio analysis...")
            portfolio_result = self._analyze_dataframe(positions_df)
            if 'error' in portfolio_result:
                return portfolio_result

            logger.info("Step 1a: Generating portfolio reports and charts...")
            saved_files = self.analytics.generate_and_save_reports(portfolio_result)
            chart_files = self.chart_generator.generate_all_charts(portfolio_result)

            logger.info("Step 2: Running market correlation analysis...")
            correlation_analyzer = MarketCorrelationAnalyzer(self.config_path)
            correlation_result = correlation_analyzer.analyze_market_correlation(positions_df)
            
            logger.info("Step 3: Running weekend parameter analysis...")
            weekend_analyzer = WeekendParameterAnalyzer() # AIDEV-NOTE: Assuming default weekend_size_percentage
            weekend_result = weekend_analyzer.analyze_weekend_parameter_impact(positions_df)

            logger.info("Step 4: Generating comprehensive HTML report...")
            html_generator = HTMLReportGenerator()
            html_file = html_generator.generate_comprehensive_report(
                portfolio_analysis=portfolio_result,
                correlation_analysis=correlation_result,
                weekend_analysis=weekend_result
            )

            execution_time = (datetime.now() - start_time).total_seconds()
            comprehensive_result = {
                'status': 'SUCCESS',
                'execution_time_seconds': execution_time,
                'portfolio_analysis': portfolio_result,
                'correlation_analysis': correlation_result,
                'weekend_analysis': weekend_result,
                'files_generated': {
                    'html_report': html_file,
                    'portfolio_reports': saved_files,
                    'portfolio_charts': chart_files,
                }
            }
            self._log_comprehensive_summary(comprehensive_result)
            return comprehensive_result

        except Exception as e:
            logger.error(f"Comprehensive analysis failed: {e}", exc_info=True)
            return {'status': 'ERROR', 'error': str(e)}

    def _analyze_dataframe(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform analysis on a DataFrame directly (internal helper).
        """
        if positions_df.empty:
            return {'error': 'No positions data available for analysis'}

        positions_df = self.analytics.cost_analyzer.allocate_costs_to_positions(positions_df)
        
        min_date = positions_df['open_timestamp'].min().strftime("%Y-%m-%d")
        max_date = positions_df['close_timestamp'].max().strftime("%Y-%m-%d")
        period_days = (positions_df['close_timestamp'].max() - positions_df['open_timestamp'].min()).days
        
        sol_rates = self.analytics.cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        daily_df = calculate_daily_returns(positions_df)
        
        risk_free_rates = self.analytics.config['portfolio_analysis']['risk_free_rates']
        sol_metrics = calculate_sol_metrics(positions_df, daily_df, risk_free_rates['sol_staking'])
        usdc_metrics = calculate_usdc_metrics(positions_df, sol_rates, risk_free_rates['usdc_staking'])
        currency_comparison = calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics, positions_df)
        cost_summary = self.analytics.cost_analyzer.generate_cost_summary(positions_df, period_days)
        
        return {
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

    def run_quick_analysis(self, positions_file: str) -> Dict[str, Any]:
        """Run quick analysis without chart generation for faster results."""
        logger.info("Running quick portfolio analysis (no charts)...")
        try:
            return self.analytics.analyze_and_report(positions_file)
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}", exc_info=True)
            return {'error': str(e)}

    def analyze_specific_period(self, start_date: str, end_date: str, positions_file: str) -> Dict[str, Any]:
        """Analyze portfolio for specific date range."""
        logger.info(f"Analyzing portfolio for period: {start_date} to {end_date}")
        try:
            positions_df = load_and_prepare_positions(positions_file, self.analytics.min_threshold)
            
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            filtered_positions = positions_df[
                (positions_df['close_timestamp'] >= start_dt) & 
                (positions_df['close_timestamp'] <= end_dt)
            ].copy()
            
            logger.info(f"Filtered to {len(filtered_positions)} positions in specified period")
            if filtered_positions.empty:
                return {'error': f'No positions found for period {start_date} to {end_date}'}
            
            analysis_result = self._analyze_dataframe(filtered_positions)
            if 'error' in analysis_result:
                return analysis_result
                
            saved_files = self.analytics.generate_and_save_reports(analysis_result)
            chart_files = self.chart_generator.generate_all_charts(analysis_result)
            
            analysis_result.pop('raw_data', None) # Don't return raw data
            analysis_result['files_generated'] = {'reports': saved_files, 'charts': chart_files}
            return analysis_result

        except Exception as e:
            logger.error(f"Period analysis failed: {e}", exc_info=True)
            return {'error': str(e)}

    def _log_comprehensive_summary(self, result: Dict[str, Any]):
        """Log comprehensive analysis summary."""
        logger.info("COMPREHENSIVE ANALYSIS SUMMARY:")
        
        portfolio = result.get('portfolio_analysis', {})
        if portfolio.get('sol_denomination'):
            sol = portfolio['sol_denomination']
            logger.info(f"  Portfolio PnL: {sol.get('total_pnl_sol', 0):+.3f} SOL, Sharpe: {sol.get('sharpe_ratio', 0):.2f}")
        
        correlation = result.get('correlation_analysis', {})
        if 'error' not in correlation.get('error', 'error'):
            corr_metrics = correlation.get('correlation_metrics', {})
            logger.info(f"  SOL Correlation: {corr_metrics.get('pearson_correlation', 0):.3f} (significant: {corr_metrics.get('is_significant', False)})")
            
        weekend = result.get('weekend_analysis', {})
        if 'error' not in weekend.get('error', 'error'):
            recs = weekend.get('recommendations', {})
            impact = weekend.get('performance_comparison', {}).get('impact_analysis', {})
            logger.info(f"  Weekend Param: {recs.get('primary_recommendation', 'N/A')} ({impact.get('total_pnl_difference_sol', 0):+.3f} SOL impact)")
            
        logger.info(f"  HTML Report: {result.get('files_generated', {}).get('html_report', 'N/A')}")
        logger.info(f"  Execution Time: {result.get('execution_time_seconds', 0):.1f} seconds")