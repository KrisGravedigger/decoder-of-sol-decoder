"""
Portfolio Analytics Main Integration Module

Orchestrates complete portfolio analysis workflow including:
- Data loading and validation
- Infrastructure cost analysis
- Dual currency portfolio metrics calculation
- Chart generation and report creation
- Market correlation analysis
- Weekend parameter impact analysis
- Comprehensive HTML reporting
"""

import logging
import os
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

# Add reporting module to path
sys.path.append('reporting')

from portfolio_analytics import PortfolioAnalytics
from chart_generator import ChartGenerator
from infrastructure_cost_analyzer import InfrastructureCostAnalyzer
from market_correlation_analyzer import MarketCorrelationAnalyzer
from weekend_parameter_analyzer import WeekendParameterAnalyzer  
from html_report_generator import HTMLReportGenerator
from data_loader import _parse_custom_timestamp
from metrics_calculator import (
    calculate_daily_returns, 
    calculate_sol_metrics, 
    calculate_usdc_metrics, 
    calculate_currency_comparison
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reporting/output/portfolio_analysis.log'),
        logging.StreamHandler()
    ]
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
        
        logger.info("Portfolio Analysis Orchestrator initialized")
        
    def _initialize_components(self):
        """Initialize analysis components."""
        try:
            self.analytics = PortfolioAnalytics(self.config_path)
            self.chart_generator = ChartGenerator(self.config_path)
            logger.info("All components initialized successfully")
        except Exception as e:
            logger.error(f"Component initialization failed: {e}")
            raise
            
    def _load_and_prepare_positions(self, positions_file: str) -> pd.DataFrame:
        """
        Load and prepare positions DataFrame with proper data types.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            pd.DataFrame: Prepared positions data
            
        Raises:
            FileNotFoundError: If positions file doesn't exist
            ValueError: If data format is invalid
        """
        if not os.path.exists(positions_file):
            available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
            logger.error(f"Positions file not found: {positions_file}")
            logger.info(f"Available CSV files: {available_files}")
            raise FileNotFoundError(f'File not found: {positions_file}')
            
        # Load positions data
        positions_df = pd.read_csv(positions_file)
        
        # AIDEV-NOTE-CLAUDE: Use custom parser for SOL Decoder timestamp format (MM/DD-HH:MM:SS)
        positions_df['open_timestamp'] = positions_df['open_timestamp'].apply(_parse_custom_timestamp)
        positions_df['close_timestamp'] = positions_df['close_timestamp'].apply(_parse_custom_timestamp)
        
        # AIDEV-NOTE-CLAUDE: Map CSV column names to expected format
        column_mapping = {
            'final_pnl_sol_from_log': 'pnl_sol',
            'initial_investment_sol': 'investment_sol'
        }
        
        # Apply column mapping
        for old_name, new_name in column_mapping.items():
            if old_name in positions_df.columns:
                positions_df = positions_df.rename(columns={old_name: new_name})
                logger.info(f"Mapped column: {old_name} -> {new_name}")
        
        # Verify required columns exist
        required_columns = ['pnl_sol', 'investment_sol', 'open_timestamp', 'close_timestamp']
        missing_columns = [col for col in required_columns if col not in positions_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns: {missing_columns}")
        
        logger.info(f"Loaded {len(positions_df)} positions from {positions_file}")
        return positions_df
        
    def _analyze_dataframe(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform analysis on a DataFrame directly (internal helper).
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        if positions_df.empty:
            return {'error': 'No positions data available'}
            
        # Apply minimum threshold filter
        min_threshold = self.analytics.min_threshold
        initial_count = len(positions_df)
        positions_df = positions_df[abs(positions_df['pnl_sol']) >= min_threshold]
        
        if len(positions_df) < initial_count:
            logger.info(f"Filtered {initial_count - len(positions_df)} positions below {min_threshold} SOL threshold")
            
        if positions_df.empty:
            return {'error': 'No positions meet minimum threshold criteria'}
            
        # Allocate infrastructure costs
        positions_df = self.analytics.cost_analyzer.allocate_costs_to_positions(positions_df)
        
        # Get analysis period
        min_date = positions_df['open_timestamp'].min().strftime("%Y-%m-%d")
        max_date = positions_df['close_timestamp'].max().strftime("%Y-%m-%d")
        period_days = (positions_df['close_timestamp'].max() - positions_df['open_timestamp'].min()).days
        
        # Get SOL/USDC historical rates
        sol_rates = self.analytics.cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        
        # Calculate daily returns
        daily_df = calculate_daily_returns(positions_df)
        
        # Get risk-free rates from config
        risk_free_rates = self.analytics.config['portfolio_analysis']['risk_free_rates']
        sol_risk_free = risk_free_rates['sol_staking']
        usdc_risk_free = risk_free_rates['usdc_staking']
        
        # Calculate metrics in both denominations
        sol_metrics = calculate_sol_metrics(positions_df, daily_df, sol_risk_free)
        usdc_metrics = calculate_usdc_metrics(positions_df, sol_rates, usdc_risk_free)
        
        # Currency comparison
        currency_comparison = calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics, positions_df)
        
        # Infrastructure cost summary
        cost_summary = self.analytics.cost_analyzer.generate_cost_summary(positions_df, period_days)
        
        # Compile complete analysis
        analysis_result = {
            'analysis_metadata': {
                'generated_timestamp': datetime.now().isoformat(),
                'analysis_period_days': period_days,
                'start_date': min_date,
                'end_date': max_date,
                'positions_analyzed': len(positions_df)
            },
            'sol_denomination': sol_metrics,
            'usdc_denomination': usdc_metrics,
            'currency_comparison': currency_comparison,
            'infrastructure_cost_impact': cost_summary,
            'raw_data': {
                'positions_df': positions_df,
                'daily_returns_df': daily_df,
                'sol_rates': sol_rates
            }
        }
        
        return analysis_result
        
    def _analyze_market_correlation_from_dataframe(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform market correlation analysis on DataFrame.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            Dict[str, Any]: Market correlation analysis results
        """
        try:
            correlation_analyzer = MarketCorrelationAnalyzer(self.config_path)
            result = correlation_analyzer.analyze_market_correlation(positions_df)
            
            if 'error' not in result:
                summary = correlation_analyzer.generate_correlation_summary(result)
                logger.info("Market correlation analysis completed")
                logger.info("\n" + summary)
                
            return result
            
        except Exception as e:
            logger.error(f"Market correlation analysis failed: {e}")
            return {'error': str(e)}
            
    def _analyze_weekend_parameter_from_dataframe(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform weekend parameter analysis on DataFrame.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            Dict[str, Any]: Weekend parameter analysis results
        """
        try:
            weekend_analyzer = WeekendParameterAnalyzer(weekend_size_percentage=20.0)
            result = weekend_analyzer.analyze_weekend_parameter_impact(positions_df)
            
            if 'error' not in result:
                summary = weekend_analyzer.generate_weekend_analysis_summary(result)
                logger.info("Weekend parameter analysis completed")
                logger.info("\n" + summary)
                
            return result
            
        except Exception as e:
            logger.error(f"Weekend parameter analysis failed: {e}")
            return {'error': str(e)}
            
    def run_complete_analysis(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Execute complete portfolio analysis workflow.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Complete analysis results with file paths
        """
        logger.info("=" * 60)
        logger.info("STARTING COMPLETE PORTFOLIO ANALYSIS")
        logger.info("=" * 60)
        
        start_time = datetime.now()
        
        try:
            # Initialize components
            self._initialize_components()
            
            # Step 1: Load and validate data
            logger.info("Step 1: Loading positions data...")
            try:
                positions_df = self._load_and_prepare_positions(positions_file)
            except FileNotFoundError as e:
                available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
                return {'error': str(e), 'available_files': available_files}
                
            # Step 2: Perform portfolio analysis
            logger.info("Step 2: Performing portfolio analysis...")
            analysis_result = self._analyze_dataframe(positions_df)
            
            if 'error' in analysis_result:
                logger.error(f"Portfolio analysis failed: {analysis_result['error']}")
                return analysis_result
                
            # Step 3: Generate text reports
            logger.info("Step 3: Generating text reports...")
            saved_files = self.analytics.generate_and_save_reports(analysis_result)
            
            # Step 4: Generate charts
            logger.info("Step 4: Generating visualization charts...")
            chart_files = self.chart_generator.generate_all_charts(analysis_result)
            
            # Step 5: Compile final results
            execution_time = (datetime.now() - start_time).total_seconds()
            
            final_result = {
                'status': 'SUCCESS',
                'execution_time_seconds': execution_time,
                'analysis_metadata': analysis_result['analysis_metadata'],
                'sol_denomination': analysis_result['sol_denomination'],
                'usdc_denomination': analysis_result['usdc_denomination'],
                'currency_comparison': analysis_result['currency_comparison'],
                'infrastructure_cost_impact': analysis_result['infrastructure_cost_impact'],
                'files_generated': {
                    'reports': saved_files,
                    'charts': chart_files
                }
            }
            
            # Log summary
            self._log_analysis_summary(final_result)
            
            logger.info("=" * 60)
            logger.info("PORTFOLIO ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            
            return final_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Portfolio analysis failed after {execution_time:.1f}s: {e}")
            
            return {
                'status': 'ERROR',
                'error': str(e),
                'execution_time_seconds': execution_time
            }
            
    def _log_analysis_summary(self, result: Dict[str, Any]):
        """
        Log comprehensive analysis summary.
        
        Args:
            result (Dict[str, Any]): Analysis results
        """
        logger.info("ANALYSIS SUMMARY:")
        
        # Metadata
        metadata = result['analysis_metadata']
        logger.info(f"  Period: {metadata['start_date']} to {metadata['end_date']} ({metadata['analysis_period_days']} days)")
        logger.info(f"  Positions: {metadata['positions_analyzed']}")
        
        # SOL metrics
        sol = result['sol_denomination']
        logger.info(f"  SOL PnL: {sol['total_pnl_sol']:+.3f} SOL (Net: {sol['net_pnl_after_costs']:+.3f})")
        logger.info(f"  SOL Sharpe: {sol['sharpe_ratio']:.2f}")
        logger.info(f"  Win Rate: {sol['win_rate']*100:.1f}%")
        
        # USDC metrics
        usdc = result['usdc_denomination']
        logger.info(f"  USDC PnL: ${usdc['total_pnl_usdc']:+,.2f} (Net: ${usdc['net_pnl_after_costs']:+,.2f})")
        logger.info(f"  USDC Sharpe: {usdc['sharpe_ratio']:.2f}")
        
        # Cost impact
        costs = result['infrastructure_cost_impact']
        logger.info(f"  Infrastructure Cost: ${costs.get('total_cost_usd', 0):,.2f} ({costs.get('cost_impact_percent', 0):.1f}% of gross)")
        
        # Files generated
        files = result['files_generated']
        logger.info(f"  Reports: {len(files['reports'])} files")
        logger.info(f"  Charts: {len([f for f in files['charts'].values() if not f.startswith('ERROR')])} charts")
        
        logger.info(f"  Execution Time: {result['execution_time_seconds']:.1f} seconds")
        
    def run_market_correlation_analysis(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Run market correlation analysis only.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Market correlation analysis results
        """
        logger.info("Running market correlation analysis...")
        
        try:
            # Load positions data once
            positions_df = self._load_and_prepare_positions(positions_file)
            
            # Run analysis
            result = self._analyze_market_correlation_from_dataframe(positions_df)
            
            if 'error' not in result:
                # Save analysis to JSON
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                json_file = f"reporting/output/market_correlation_{timestamp}.json"
                with open(json_file, 'w') as f:
                    # Convert pandas objects to serializable format
                    result_copy = result.copy()
                    if 'raw_data' in result_copy:
                        del result_copy['raw_data']  # Remove non-serializable data
                    json.dump(result_copy, f, indent=2, default=str)
                    
                result['files_generated'] = {'analysis': json_file}
                
            return result
            
        except Exception as e:
            logger.error(f"Market correlation analysis failed: {e}")
            return {'error': str(e)}
            
    def run_weekend_parameter_analysis(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Run weekend parameter impact analysis only.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Weekend parameter analysis results
        """
        logger.info("Running weekend parameter analysis...")
        
        try:
            # Load positions data once
            positions_df = self._load_and_prepare_positions(positions_file)
            
            # Run analysis
            result = self._analyze_weekend_parameter_from_dataframe(positions_df)
            
            if 'error' not in result:
                # Save analysis to JSON
                timestamp = datetime.now().strftime("%Y%m%d_%H%M")
                json_file = f"reporting/output/weekend_analysis_{timestamp}.json"
                with open(json_file, 'w') as f:
                    # Convert pandas objects to serializable format
                    result_copy = result.copy()
                    if 'raw_data' in result_copy:
                        del result_copy['raw_data']  # Remove non-serializable data
                    json.dump(result_copy, f, indent=2, default=str)
                    
                result['files_generated'] = {'analysis': json_file}
                
            return result
            
        except Exception as e:
            logger.error(f"Weekend parameter analysis failed: {e}")
            return {'error': str(e)}
            
    def run_comprehensive_analysis(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
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
            # Step 0: Load positions data ONCE (major optimization)
            logger.info("Step 0: Loading positions data...")
            try:
                positions_df = self._load_and_prepare_positions(positions_file)
            except FileNotFoundError as e:
                return {'error': str(e)}
                
            # Initialize components
            self._initialize_components()
            
            # Step 1: Portfolio Analysis (using DataFrame directly)
            logger.info("Step 1: Running portfolio analysis...")
            portfolio_result = self._analyze_dataframe(positions_df)
            
            if 'error' in portfolio_result:
                logger.error(f"Portfolio analysis failed: {portfolio_result['error']}")
                return portfolio_result
                
            # Generate portfolio reports and charts
            logger.info("Step 1a: Generating portfolio reports and charts...")
            saved_files = self.analytics.save_reports(portfolio_result)
            chart_files = self.chart_generator.generate_all_charts(portfolio_result)
            
            # Compile portfolio result
            portfolio_complete = {
                'status': 'SUCCESS',
                'analysis_metadata': portfolio_result['analysis_metadata'],
                'sol_denomination': portfolio_result['sol_denomination'],
                'usdc_denomination': portfolio_result['usdc_denomination'],
                'currency_comparison': portfolio_result['currency_comparison'],
                'infrastructure_cost_impact': portfolio_result['infrastructure_cost_impact'],
                'files_generated': {
                    'reports': saved_files,
                    'charts': chart_files
                }
            }
            
            # Step 2: Market Correlation Analysis (using same DataFrame)
            logger.info("Step 2: Running market correlation analysis...")
            correlation_result = self._analyze_market_correlation_from_dataframe(positions_df)
            
            # Step 3: Weekend Parameter Analysis (using same DataFrame)
            logger.info("Step 3: Running weekend parameter analysis...")
            weekend_result = self._analyze_weekend_parameter_from_dataframe(positions_df)
            
            # Step 4: Generate HTML Report
            logger.info("Step 4: Generating comprehensive HTML report...")
            html_generator = HTMLReportGenerator()
            
            html_file = html_generator.generate_comprehensive_report(
                portfolio_analysis=portfolio_result,  # Use raw portfolio_result with raw_data
                correlation_analysis=correlation_result if 'error' not in correlation_result else None,
                weekend_analysis=weekend_result if 'error' not in weekend_result else None
            )
            
            # Step 5: Save individual analysis files
            logger.info("Step 5: Saving analysis data files...")
            timestamp = datetime.now().strftime("%Y%m%d_%H%M")
            
            # Save correlation analysis
            correlation_files = {}
            if 'error' not in correlation_result:
                corr_json_file = f"reporting/output/market_correlation_{timestamp}.json"
                with open(corr_json_file, 'w') as f:
                    result_copy = correlation_result.copy()
                    if 'raw_data' in result_copy:
                        del result_copy['raw_data']
                    json.dump(result_copy, f, indent=2, default=str)
                correlation_files['analysis'] = corr_json_file
                
            # Save weekend analysis
            weekend_files = {}
            if 'error' not in weekend_result:
                weekend_json_file = f"reporting/output/weekend_analysis_{timestamp}.json"
                with open(weekend_json_file, 'w') as f:
                    result_copy = weekend_result.copy()
                    if 'raw_data' in result_copy:
                        del result_copy['raw_data']
                    json.dump(result_copy, f, indent=2, default=str)
                weekend_files['analysis'] = weekend_json_file
            
            # Step 6: Compile comprehensive results
            execution_time = (datetime.now() - start_time).total_seconds()
            
            comprehensive_result = {
                'status': 'SUCCESS',
                'execution_time_seconds': execution_time,
                'portfolio_analysis': portfolio_complete,
                'correlation_analysis': correlation_result,
                'weekend_analysis': weekend_result,
                'files_generated': {
                    'html_report': html_file,
                    'portfolio_reports': saved_files,
                    'portfolio_charts': chart_files,
                    'correlation_analysis': correlation_files,
                    'weekend_analysis': weekend_files
                }
            }
            
            # Log comprehensive summary
            self._log_comprehensive_summary(comprehensive_result)
            
            logger.info("=" * 60)
            logger.info("COMPREHENSIVE ANALYSIS COMPLETED SUCCESSFULLY")
            logger.info("=" * 60)
            
            return comprehensive_result
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            logger.error(f"Comprehensive analysis failed after {execution_time:.1f}s: {e}")
            
            return {
                'status': 'ERROR',
                'error': str(e),
                'execution_time_seconds': execution_time
            }
            
    def _log_comprehensive_summary(self, result: Dict[str, Any]):
        """
        Log comprehensive analysis summary.
        
        Args:
            result (Dict[str, Any]): Comprehensive analysis results
        """
        logger.info("COMPREHENSIVE ANALYSIS SUMMARY:")
        
        # Portfolio metrics
        if result['portfolio_analysis'].get('status') == 'SUCCESS':
            portfolio = result['portfolio_analysis']
            sol = portfolio['sol_denomination']
            logger.info(f"  Portfolio PnL: {sol['total_pnl_sol']:+.3f} SOL, Sharpe: {sol['sharpe_ratio']:.2f}")
        
        # Correlation analysis
        if 'error' not in result['correlation_analysis']:
            corr = result['correlation_analysis']['correlation_metrics']
            logger.info(f"  SOL Correlation: {corr['pearson_correlation']:.3f} (significant: {corr['is_significant']})")
        else:
            logger.info(f"  SOL Correlation: Error - {result['correlation_analysis']['error']}")
            
        # Weekend analysis
        if 'error' not in result['weekend_analysis']:
            weekend = result['weekend_analysis']['recommendations']
            impact = result['weekend_analysis']['performance_comparison']['impact_analysis']
            logger.info(f"  Weekend Parameter: {weekend['primary_recommendation']} ({impact['total_pnl_difference_sol']:+.3f} SOL impact)")
        else:
            logger.info(f"  Weekend Parameter: Error - {result['weekend_analysis']['error']}")
            
        # Files generated
        logger.info(f"  HTML Report: {result['files_generated']['html_report']}")
        logger.info(f"  Execution Time: {result['execution_time_seconds']:.1f} seconds")
        
    def quick_analysis(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Run quick analysis without chart generation for faster results.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Analysis results without charts
        """
        logger.info("Running quick portfolio analysis (no charts)...")
        
        try:
            if not self.analytics:
                self.analytics = PortfolioAnalytics(self.config_path)
                
            # Analyze and generate reports only
            result = self.analytics.analyze_and_report(positions_file)
            
            if 'error' not in result:
                logger.info("Quick analysis completed successfully")
                # Log key metrics
                sol = result['sol_denomination']
                logger.info(f"Key Results: {sol['total_pnl_sol']:+.3f} SOL, Sharpe: {sol['sharpe_ratio']:.2f}")
                
            return result
            
        except Exception as e:
            logger.error(f"Quick analysis failed: {e}")
            return {'error': str(e)}
            
    def analyze_specific_period(self, start_date: str, end_date: str, 
                               positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Analyze portfolio for specific date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Analysis results for date range
        """
        logger.info(f"Analyzing portfolio for period: {start_date} to {end_date}")
        
        try:
            # AIDEV-NOTE-CLAUDE: Optimized to avoid temporary file creation - filter in memory
            positions_df = self._load_and_prepare_positions(positions_file)
            
            # Filter positions that closed within the specified period
            start_dt = pd.to_datetime(start_date)
            end_dt = pd.to_datetime(end_date)
            
            filtered_positions = positions_df[
                (positions_df['close_timestamp'] >= start_dt) & 
                (positions_df['close_timestamp'] <= end_dt)
            ]
            
            logger.info(f"Filtered to {len(filtered_positions)} positions in specified period")
            
            if filtered_positions.empty:
                return {'error': f'No positions found for period {start_date} to {end_date}'}
                
            # Initialize components if needed
            if not self.analytics:
                self._initialize_components()
                
            # Run analysis directly on filtered DataFrame
            analysis_result = self._analyze_dataframe(filtered_positions)
            
            if 'error' in analysis_result:
                return analysis_result
                
            # Generate reports and charts
            saved_files = self.analytics.save_reports(analysis_result)
            chart_files = self.chart_generator.generate_all_charts(analysis_result)
            
            # Compile results
            final_result = {
                'status': 'SUCCESS',
                'period_filter': f'{start_date} to {end_date}',
                'analysis_metadata': analysis_result['analysis_metadata'],
                'sol_denomination': analysis_result['sol_denomination'],
                'usdc_denomination': analysis_result['usdc_denomination'],
                'currency_comparison': analysis_result['currency_comparison'],
                'infrastructure_cost_impact': analysis_result['infrastructure_cost_impact'],
                'files_generated': {
                    'reports': saved_files,
                    'charts': chart_files
                }
            }
            
            return final_result
            
        except Exception as e:
            logger.error(f"Period analysis failed: {e}")
            return {'error': str(e)}


def main():
    """Main entry point for portfolio analysis."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Portfolio Analytics for LP Strategy Optimization')
    parser.add_argument('--file', '-f', default='positions_to_analyze.csv',
                       help='Path to positions CSV file (default: positions_to_analyze.csv)')
    parser.add_argument('--quick', '-q', action='store_true',
                       help='Run quick analysis without charts')
    parser.add_argument('--start-date', help='Start date for analysis (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for analysis (YYYY-MM-DD)')
    parser.add_argument('--config', '-c', default='reporting/config/portfolio_config.yaml',
                       help='Path to configuration file')
    parser.add_argument('--correlation', action='store_true',
                       help='Run market correlation analysis only')
    parser.add_argument('--weekend', action='store_true',
                       help='Run weekend parameter analysis only')
    parser.add_argument('--comprehensive', action='store_true',
                       help='Run comprehensive analysis with HTML report')
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = PortfolioAnalysisOrchestrator(args.config)
    
    try:
        # Determine analysis type
        if args.start_date and args.end_date:
            result = orchestrator.analyze_specific_period(args.start_date, args.end_date, args.file)
        elif args.correlation:
            result = orchestrator.run_market_correlation_analysis(args.file)
        elif args.weekend:
            result = orchestrator.run_weekend_parameter_analysis(args.file)
        elif args.comprehensive:
            result = orchestrator.run_comprehensive_analysis(args.file)
        elif args.quick:
            result = orchestrator.quick_analysis(args.file)
        else:
            result = orchestrator.run_complete_analysis(args.file)
            
        # Print results summary
        if result.get('status') == 'SUCCESS':
            print("\n" + "="*50)
            print("PORTFOLIO ANALYSIS COMPLETED")
            print("="*50)
            
            # Print key metrics
            if 'sol_denomination' in result:
                sol = result['sol_denomination']
                print(f"Total PnL: {sol['total_pnl_sol']:+.3f} SOL")
                print(f"Sharpe Ratio: {sol['sharpe_ratio']:.2f}")
                print(f"Win Rate: {sol['win_rate']*100:.1f}%")
                print(f"Max Drawdown: {sol['max_drawdown_percent']:.1f}%")
                
                if 'files_generated' in result:
                    files = result['files_generated']
                    print(f"\nFiles Generated:")
                    
                    # Handle different file structures based on analysis type
                    if 'reports' in files:
                        for report_type, file_path in files['reports'].items():
                            print(f"  {report_type}: {file_path}")
                    if 'charts' in files:
                        for chart_type, file_path in files['charts'].items():
                            if not file_path.startswith('ERROR'):
                                print(f"  {chart_type}: {file_path}")
                    
                    # Handle comprehensive analysis files
                    if 'html_report' in files:
                        print(f"  html_report: {files['html_report']}")
                    if 'portfolio_reports' in files:
                        for report_type, file_path in files['portfolio_reports'].items():
                            print(f"  portfolio_{report_type}: {file_path}")
                    if 'portfolio_charts' in files:
                        for chart_type, file_path in files['portfolio_charts'].items():
                            if not file_path.startswith('ERROR'):
                                print(f"  portfolio_{chart_type}: {file_path}")
                    if 'correlation_analysis' in files and files['correlation_analysis']:
                        for analysis_type, file_path in files['correlation_analysis'].items():
                            print(f"  correlation_{analysis_type}: {file_path}")
                    if 'weekend_analysis' in files and files['weekend_analysis']:
                        for analysis_type, file_path in files['weekend_analysis'].items():
                            print(f"  weekend_{analysis_type}: {file_path}")
                    
                    # Handle single analysis files
                    if 'analysis' in files:
                        print(f"  analysis: {files['analysis']}")
                        
            # Handle comprehensive analysis summary
            elif args.comprehensive and result.get('status') == 'SUCCESS':
                if 'portfolio_analysis' in result and 'sol_denomination' in result['portfolio_analysis']:
                    sol = result['portfolio_analysis']['sol_denomination']
                    print(f"Total PnL: {sol['total_pnl_sol']:+.3f} SOL")
                    print(f"Sharpe Ratio: {sol['sharpe_ratio']:.2f}")
                    print(f"Win Rate: {sol['win_rate']*100:.1f}%")
                    print(f"Max Drawdown: {sol['max_drawdown_percent']:.1f}%")
                    
                # Print additional analysis results
                if 'correlation_analysis' in result and 'error' not in result['correlation_analysis']:
                    corr = result['correlation_analysis']['correlation_metrics']
                    print(f"\nMarket Correlation: {corr['pearson_correlation']:.3f}")
                    print(f"Correlation Significant: {'Yes' if corr['is_significant'] else 'No'}")
                    
                if 'weekend_analysis' in result and 'error' not in result['weekend_analysis']:
                    weekend = result['weekend_analysis']['recommendations']
                    impact = result['weekend_analysis']['performance_comparison']['impact_analysis']
                    print(f"\nWeekend Parameter Recommendation: {weekend['primary_recommendation']}")
                    print(f"Expected Impact: {impact['total_pnl_difference_sol']:+.3f} SOL")
                    
                # Print files generated
                if 'files_generated' in result:
                    files = result['files_generated']
                    print(f"\nFiles Generated:")
                    if 'html_report' in files:
                        print(f"  Comprehensive HTML Report: {files['html_report']}")
                    print(f"  Total Files: {sum(len(v) if isinstance(v, dict) else 1 for v in files.values() if v)}")
                        
            print(f"\nExecution Time: {result.get('execution_time_seconds', 0):.1f} seconds")
            
        else:
            print(f"\nANALYSIS FAILED: {result.get('error', 'Unknown error')}")
            return 1
            
        return 0
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        print("\nAnalysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        print(f"\nUnexpected error: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)