"""
Portfolio Analytics Main Integration Module

Orchestrates complete portfolio analysis workflow including:
- Data loading and validation
- Infrastructure cost analysis
- Dual currency portfolio metrics calculation
- Chart generation and report creation
"""

import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional
import pandas as pd

# Add reporting module to path
sys.path.append('reporting')

from portfolio_analytics import PortfolioAnalytics
from chart_generator import ChartGenerator
from infrastructure_cost_analyzer import InfrastructureCostAnalyzer

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
        daily_df = self.analytics._calculate_daily_returns(positions_df)
        
        # Calculate metrics in both denominations
        sol_metrics = self.analytics._calculate_sol_metrics(positions_df, daily_df)
        usdc_metrics = self.analytics._calculate_usdc_metrics(positions_df, sol_rates)
        
        # Currency comparison
        currency_comparison = self.analytics._calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics)
        
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
            if not os.path.exists(positions_file):
                available_files = [f for f in os.listdir('.') if f.endswith('.csv')]
                logger.error(f"Positions file not found: {positions_file}")
                logger.info(f"Available CSV files: {available_files}")
                return {'error': f'File not found: {positions_file}', 'available_files': available_files}
                
            # Step 2: Perform portfolio analysis
            logger.info("Step 2: Performing portfolio analysis...")
            analysis_result = self.analytics.analyze_portfolio(positions_file)
            
            if 'error' in analysis_result:
                logger.error(f"Portfolio analysis failed: {analysis_result['error']}")
                return analysis_result
                
            # Step 3: Generate text reports
            logger.info("Step 3: Generating text reports...")
            saved_files = self.analytics.save_reports(analysis_result)
            
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
            positions_df = pd.read_csv(positions_file)
            positions_df['open_timestamp'] = pd.to_datetime(positions_df['open_timestamp'])
            positions_df['close_timestamp'] = pd.to_datetime(positions_df['close_timestamp'])
            
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
    
    args = parser.parse_args()
    
    # Initialize orchestrator
    orchestrator = PortfolioAnalysisOrchestrator(args.config)
    
    try:
        # Determine analysis type
        if args.start_date and args.end_date:
            result = orchestrator.analyze_specific_period(args.start_date, args.end_date, args.file)
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
                    for report_type, file_path in files.get('reports', {}).items():
                        print(f"  {report_type}: {file_path}")
                    for chart_type, file_path in files.get('charts', {}).items():
                        if not file_path.startswith('ERROR'):
                            print(f"  {chart_type}: {file_path}")
                            
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