"""
Portfolio Analytics Engine for LP Strategy Analysis

Implements dual currency analysis (SOL/USDC) with risk-adjusted metrics
and infrastructure cost impact assessment.
"""

import logging
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
import yaml

from infrastructure_cost_analyzer import InfrastructureCostAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PortfolioAnalytics:
    """
    Main portfolio analytics engine for LP strategy performance analysis.
    
    Provides dual currency analysis (SOL primary, USDC secondary) with
    risk-adjusted metrics including Sharpe ratio, max drawdown, and 
    infrastructure cost impact.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize portfolio analytics engine.
        
        Args:
            config_path (str): Path to YAML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
        """
        self.config = self._load_config(config_path)
        self.cost_analyzer = InfrastructureCostAnalyzer(config_path)
        self.min_threshold = self.config['portfolio_analysis']['min_position_threshold']
        self.risk_free_rates = self.config['portfolio_analysis']['risk_free_rates']
        self.analysis_periods = self.config['portfolio_analysis']['analysis_periods']
        
        # Output directory setup
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
        
    def load_positions_data(self, file_path: str = "positions_to_analyze.csv") -> pd.DataFrame:
        """
        Load and validate positions data from CSV.
        
        Args:
            file_path (str): Path to positions CSV file
            
        Returns:
            pd.DataFrame: Validated positions data
            
        Raises:
            FileNotFoundError: If positions file doesn't exist
            ValueError: If required columns are missing
        """
        try:
            positions_df = pd.read_csv(file_path)
            logger.info(f"Loaded {len(positions_df)} positions from {file_path}")
        except FileNotFoundError:
            logger.error(f"Positions file not found: {file_path}")
            raise
            
        # Validate required columns and map from actual CSV structure
        csv_to_expected_mapping = {
            'final_pnl_sol_from_log': 'pnl_sol',
            'actual_strategy_from_log': 'strategy_raw',
            'initial_investment_sol': 'investment_sol'
        }
        
        # Check if CSV has the expected structure
        missing_csv_columns = [col for col in csv_to_expected_mapping.keys() if col not in positions_df.columns]
        if missing_csv_columns:
            raise ValueError(f"Missing CSV columns: {missing_csv_columns}")
            
        # Map columns to expected names
        positions_df = positions_df.rename(columns=csv_to_expected_mapping)
        
        # Extract strategy and step_size from strategy_raw
        # Format: "Bid-Ask (1-Sided) SIXTYNINE" -> strategy="Bid-Ask", step_size="SIXTYNINE"
        positions_df['strategy'] = positions_df['strategy_raw'].str.extract(r'(Bid-Ask|Spot)')
        positions_df['step_size'] = positions_df['strategy_raw'].str.extract(r'(SIXTYNINE|MEDIUM|NARROW|WIDE)')
        
        # Fill missing strategies (fallback)
        positions_df['strategy'] = positions_df['strategy'].fillna('Bid-Ask')
        positions_df['step_size'] = positions_df['step_size'].fillna('MEDIUM')
        
        logger.info(f"Mapped CSV columns: strategies found: {positions_df['strategy'].value_counts().to_dict()}")
        logger.info(f"Step sizes found: {positions_df['step_size'].value_counts().to_dict()}")
        
        # Validate final required columns
        required_columns = ['pnl_sol', 'strategy', 'step_size', 'investment_sol']
        missing_columns = [col for col in required_columns if col not in positions_df.columns]
        if missing_columns:
            raise ValueError(f"Missing required columns after mapping: {missing_columns}")
            
        # Convert timestamps with custom parsing for non-standard format
        # Format: "05/12-20:57:08" -> "2025-05-12 20:57:08"
        for col in ['open_timestamp', 'close_timestamp']:
            if col in positions_df.columns:
                try:
                    # Try standard pandas parsing first
                    positions_df[col] = pd.to_datetime(positions_df[col])
                except (ValueError, pd.errors.OutOfBoundsDatetime):
                    # Custom parsing for format "MM/DD-HH:MM:SS"
                    logger.info(f"Using custom timestamp parsing for {col}")
                    
                    def parse_custom_timestamp(ts_str):
                        try:
                            if pd.isna(ts_str) or ts_str == '':
                                return pd.NaT
                            
                            # Format: "05/12-20:57:08" -> "2025-05-12 20:57:08"
                            date_part, time_part = ts_str.split('-')
                            month, day = date_part.split('/')
                            
                            # Handle 24:XX:XX format (should be 00:XX:XX of next day)
                            hour, minute, second = time_part.split(':')
                            hour = int(hour)
                            
                            # Assume current year (2025) - adjust if needed
                            current_year = datetime.now().year
                            base_date = datetime(current_year, int(month), int(day))
                            
                            # Handle hour 24 as next day hour 0
                            if hour >= 24:
                                hour = hour - 24
                                base_date = base_date + timedelta(days=1)
                            
                            final_datetime = base_date.replace(hour=hour, minute=int(minute), second=int(second))
                            return pd.to_datetime(final_datetime)
                            
                        except Exception as e:
                            logger.warning(f"Failed to parse timestamp '{ts_str}': {e}")
                            return pd.NaT
                    
                    positions_df[col] = positions_df[col].apply(parse_custom_timestamp)
                    
                    # Remove any rows with NaT timestamps
                    before_count = len(positions_df)
                    positions_df = positions_df.dropna(subset=[col])
                    after_count = len(positions_df)
                    
                    if before_count > after_count:
                        logger.warning(f"Removed {before_count - after_count} rows with invalid {col}")
                        
        logger.info(f"Successfully parsed timestamps. Date range: {positions_df['open_timestamp'].min()} to {positions_df['close_timestamp'].max()}")
            
        # Apply minimum threshold filter
        initial_count = len(positions_df)
        positions_df = positions_df[abs(positions_df['pnl_sol']) >= self.min_threshold]
        filtered_count = len(positions_df)
        
        if filtered_count < initial_count:
            logger.info(f"Filtered {initial_count - filtered_count} positions below {self.min_threshold} SOL threshold")
            
        return positions_df
        
    def _calculate_daily_returns(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate daily portfolio returns from positions.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            pd.DataFrame: Daily returns with date index
        """
        if positions_df.empty:
            return pd.DataFrame()
            
        # Create daily PnL series
        daily_pnl = {}
        
        for _, position in positions_df.iterrows():
            close_date = position['close_timestamp'].date()
            pnl = position['pnl_sol']
            
            if close_date in daily_pnl:
                daily_pnl[close_date] += pnl
            else:
                daily_pnl[close_date] = pnl
                
        # Convert to DataFrame with daily returns
        daily_df = pd.DataFrame(list(daily_pnl.items()), columns=['date', 'daily_pnl_sol'])
        daily_df['date'] = pd.to_datetime(daily_df['date'])
        daily_df = daily_df.sort_values('date').reset_index(drop=True)
        
        # Calculate cumulative PnL for return calculation
        daily_df['cumulative_pnl_sol'] = daily_df['daily_pnl_sol'].cumsum()
        
        # AIDEV-NOTE-CLAUDE: Improved daily return calculation - using daily PnL / capital base instead of pct_change
        # Estimate capital base as average investment per position * number of positions
        avg_investment = positions_df['investment_sol'].mean() if not positions_df.empty else 1.0
        estimated_capital_base = avg_investment * len(positions_df) if not positions_df.empty else 1.0
        
        # Calculate daily returns as daily PnL / capital base
        daily_df['daily_return'] = daily_df['daily_pnl_sol'] / estimated_capital_base
        
        return daily_df
        
    def _calculate_sol_metrics(self, positions_df: pd.DataFrame, daily_df: pd.DataFrame) -> Dict[str, float]:
        """
        Calculate portfolio metrics in SOL denomination.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            daily_df (pd.DataFrame): Daily returns data
            
        Returns:
            Dict[str, float]: SOL-denominated metrics
        """
        if positions_df.empty or daily_df.empty:
            return self._empty_metrics()
            
        # Basic metrics
        total_pnl_sol = positions_df['pnl_sol'].sum()
        win_rate = len(positions_df[positions_df['pnl_sol'] > 0]) / len(positions_df)
        
        # Profit factor
        positive_pnl = positions_df[positions_df['pnl_sol'] > 0]['pnl_sol'].sum()
        negative_pnl = abs(positions_df[positions_df['pnl_sol'] < 0]['pnl_sol'].sum())
        profit_factor = positive_pnl / negative_pnl if negative_pnl > 0 else float('inf')
        
        # Sharpe ratio calculation - AIDEV-NOTE-CLAUDE: Fixed critical bug - was using daily_usdc_df instead of daily_df
        if len(daily_df) > 1:
            daily_returns = daily_df['daily_return']
            risk_free_daily = self.risk_free_rates['sol_staking'] / 365
            excess_returns = daily_returns - risk_free_daily
            
            if excess_returns.std() > 0:
                sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(365)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
            
        # Max drawdown calculation - AIDEV-NOTE-CLAUDE: Fixed critical bug - was using daily_usdc_df instead of daily_df  
        if len(daily_df) > 1:
            cumulative = daily_df['cumulative_pnl_sol']
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max.abs()
            max_drawdown = drawdown.min() * 100  # Convert to percentage
        else:
            max_drawdown = 0.0
            
        # Net PnL after infrastructure costs
        total_cost_sol = positions_df['infrastructure_cost_sol'].sum() if 'infrastructure_cost_sol' in positions_df.columns else 0
        net_pnl_sol = total_pnl_sol - total_cost_sol
        
        return {
            'total_pnl_sol': total_pnl_sol,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_percent': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_pnl_after_costs': net_pnl_sol,
            'total_positions': len(positions_df)
        }
        
    def _calculate_usdc_metrics(self, positions_df: pd.DataFrame, sol_rates: Dict[str, float]) -> Dict[str, float]:
        """
        Calculate portfolio metrics in USDC denomination.
        
        Args:
            positions_df (pd.DataFrame): Positions data with SOL values
            sol_rates (Dict[str, float]): Historical SOL/USDC rates
            
        Returns:
            Dict[str, float]: USDC-denominated metrics
        """
        if positions_df.empty:
            return self._empty_metrics()
            
        # Convert SOL PnL to USDC using historical rates
        positions_usdc = positions_df.copy()
        positions_usdc['pnl_usdc'] = 0.0
        positions_usdc['infrastructure_cost_usdc'] = 0.0
        
        for idx, position in positions_usdc.iterrows():
            close_date = position['close_timestamp'].strftime("%Y-%m-%d")
            
            if close_date in sol_rates:
                sol_price = sol_rates[close_date]
                positions_usdc.at[idx, 'pnl_usdc'] = position['pnl_sol'] * sol_price
                
                if 'infrastructure_cost_sol' in position:
                    positions_usdc.at[idx, 'infrastructure_cost_usdc'] = position['infrastructure_cost_sol'] * sol_price
            else:
                logger.warning(f"No SOL price available for {close_date}")
                
        # Calculate USDC daily returns
        daily_pnl_usdc = {}
        for _, position in positions_usdc.iterrows():
            close_date = position['close_timestamp'].date()
            pnl = position['pnl_usdc']
            
            if close_date in daily_pnl_usdc:
                daily_pnl_usdc[close_date] += pnl
            else:
                daily_pnl_usdc[close_date] = pnl
                
        daily_usdc_df = pd.DataFrame(list(daily_pnl_usdc.items()), columns=['date', 'daily_pnl_usdc'])
        daily_usdc_df['date'] = pd.to_datetime(daily_usdc_df['date'])
        daily_usdc_df = daily_usdc_df.sort_values('date').reset_index(drop=True)
        daily_usdc_df['cumulative_pnl_usdc'] = daily_usdc_df['daily_pnl_usdc'].cumsum()
        
        # Calculate daily returns for USDC
        avg_investment = positions_df['investment_sol'].mean() if not positions_df.empty else 1.0
        estimated_capital_base_usdc = avg_investment * len(positions_df) * 150  # Assume ~$150 SOL price for base estimation
        daily_usdc_df['daily_return'] = daily_usdc_df['daily_pnl_usdc'] / estimated_capital_base_usdc
        
        # Basic metrics
        total_pnl_usdc = positions_usdc['pnl_usdc'].sum()
        win_rate = len(positions_usdc[positions_usdc['pnl_usdc'] > 0]) / len(positions_usdc)
        
        # Profit factor
        positive_pnl = positions_usdc[positions_usdc['pnl_usdc'] > 0]['pnl_usdc'].sum()
        negative_pnl = abs(positions_usdc[positions_usdc['pnl_usdc'] < 0]['pnl_usdc'].sum())
        profit_factor = positive_pnl / negative_pnl if negative_pnl > 0 else float('inf')
        
        # Sharpe ratio calculation
        if len(daily_usdc_df) > 1:
            daily_returns = daily_usdc_df['daily_return']
            risk_free_daily = self.risk_free_rates['usdc_staking'] / 365
            excess_returns = daily_returns - risk_free_daily
            
            if excess_returns.std() > 0:
                sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(365)
            else:
                sharpe_ratio = 0.0
        else:
            sharpe_ratio = 0.0
            
        # Max drawdown calculation
        if len(daily_usdc_df) > 1:
            cumulative = daily_usdc_df['cumulative_pnl_usdc']
            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max.abs()
            max_drawdown = drawdown.min() * 100  # Convert to percentage
        else:
            max_drawdown = 0.0
            
        # Net PnL after infrastructure costs
        total_cost_usdc = positions_usdc['infrastructure_cost_usdc'].sum()
        net_pnl_usdc = total_pnl_usdc - total_cost_usdc
        
        return {
            'total_pnl_usdc': total_pnl_usdc,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown_percent': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'net_pnl_after_costs': net_pnl_usdc,
            'total_positions': len(positions_usdc)
        }
        
    def _empty_metrics(self) -> Dict[str, float]:
        """Return empty metrics structure for edge cases."""
        return {
            'total_pnl_sol': 0.0,
            'total_pnl_usdc': 0.0,
            'sharpe_ratio': 0.0,
            'max_drawdown_percent': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'net_pnl_after_costs': 0.0,
            'total_positions': 0
        }
        
    def _calculate_currency_comparison(self, sol_rates: Dict[str, float], 
                                     sol_metrics: Dict[str, float],
                                     usdc_metrics: Dict[str, float]) -> Dict[str, Any]:
        """
        Calculate currency comparison metrics.
        
        Args:
            sol_rates (Dict[str, float]): Historical SOL/USDC rates
            sol_metrics (Dict[str, float]): SOL denomination metrics
            usdc_metrics (Dict[str, float]): USDC denomination metrics
            
        Returns:
            Dict[str, Any]: Currency comparison analysis
        """
        if not sol_rates:
            return {
                'sol_price_change_period': 0.0,
                'outperformance_vs_hodl': 0.0,
                'preferred_denomination': 'SOL'
            }
            
        # Calculate SOL price change over period
        rates_list = list(sol_rates.values())
        if len(rates_list) >= 2:
            start_price = rates_list[0]
            end_price = rates_list[-1]
            sol_price_change = (end_price - start_price) / start_price * 100
        else:
            sol_price_change = 0.0
            
        # Calculate LP performance vs simple SOL holding
        # Assume initial portfolio value equivalent to total investment
        total_investment_sol = sol_metrics.get('total_positions', 1) * 0.5  # Rough estimate
        lp_return_pct = (sol_metrics['total_pnl_sol'] / total_investment_sol * 100) if total_investment_sol > 0 else 0
        outperformance = lp_return_pct - sol_price_change
        
        # Determine preferred denomination based on Sharpe ratio
        preferred = 'SOL' if sol_metrics['sharpe_ratio'] >= usdc_metrics['sharpe_ratio'] else 'USDC'
        
        return {
            'sol_price_change_period': sol_price_change,
            'outperformance_vs_hodl': outperformance,
            'preferred_denomination': preferred
        }
        
    def analyze_portfolio(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Perform complete portfolio analysis with dual currency metrics.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Complete portfolio analysis results
        """
        logger.info("Starting portfolio analysis...")
        
        # Load and prepare data
        positions_df = self.load_positions_data(positions_file)
        
        if positions_df.empty:
            logger.warning("No positions data available for analysis")
            return {'error': 'No positions data available'}
            
        # Allocate infrastructure costs
        positions_df = self.cost_analyzer.allocate_costs_to_positions(positions_df)
        
        # Get analysis period
        min_date = positions_df['open_timestamp'].min().strftime("%Y-%m-%d")
        max_date = positions_df['close_timestamp'].max().strftime("%Y-%m-%d")
        period_days = (positions_df['close_timestamp'].max() - positions_df['open_timestamp'].min()).days
        
        logger.info(f"Analysis period: {min_date} to {max_date} ({period_days} days)")
        
        # Get SOL/USDC historical rates
        sol_rates = self.cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        
        # Calculate daily returns
        daily_df = self._calculate_daily_returns(positions_df)
        
        # Calculate metrics in both denominations
        sol_metrics = self._calculate_sol_metrics(positions_df, daily_df)
        usdc_metrics = self._calculate_usdc_metrics(positions_df, sol_rates)
        
        # Currency comparison
        currency_comparison = self._calculate_currency_comparison(sol_rates, sol_metrics, usdc_metrics)
        
        # Infrastructure cost summary
        cost_summary = self.cost_analyzer.generate_cost_summary(positions_df, period_days)
        
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
        
        logger.info("Portfolio analysis completed successfully")
        return analysis_result
        
    def generate_text_reports(self, analysis_result: Dict[str, Any]) -> Tuple[str, str]:
        """
        Generate formatted text reports from analysis results.
        
        Args:
            analysis_result (Dict[str, Any]): Complete analysis results
            
        Returns:
            Tuple[str, str]: (portfolio_summary, infrastructure_impact) report content
        """
        timestamp = self._generate_timestamp()
        metadata = analysis_result['analysis_metadata']
        sol = analysis_result['sol_denomination']
        usdc = analysis_result['usdc_denomination']
        currency = analysis_result['currency_comparison']
        costs = analysis_result['infrastructure_cost_impact']
        
        # AIDEV-NOTE-CLAUDE: Text format matches specification requirements exactly
        portfolio_summary = f"""=== PORTFOLIO ANALYTICS REPORT ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Analysis Period: {metadata['analysis_period_days']} days ({metadata['start_date']} to {metadata['end_date']})

SOL DENOMINATION ANALYSIS:
- Total PnL: {sol['total_pnl_sol']:+.2f} SOL
- Sharpe Ratio: {sol['sharpe_ratio']:.2f}
- Max Drawdown: {sol['max_drawdown_percent']:.1f}%
- Win Rate: {sol['win_rate']*100:.1f}% ({int(sol['win_rate']*sol['total_positions'])}/{sol['total_positions']} positions)
- Profit Factor: {sol['profit_factor']:.2f}
- Net PnL After Costs: {sol['net_pnl_after_costs']:+.2f} SOL

USDC DENOMINATION ANALYSIS:
- Total PnL: {usdc['total_pnl_usdc']:+,.2f} USDC
- Sharpe Ratio: {usdc['sharpe_ratio']:.2f}
- Max Drawdown: {usdc['max_drawdown_percent']:.1f}%
- Net PnL After Costs: {usdc['net_pnl_after_costs']:+,.2f} USDC

INFRASTRUCTURE COST IMPACT:
- Period Cost: ${costs.get('total_cost_usd', 0):,.2f} USD ({metadata['analysis_period_days']} days × ${costs.get('daily_cost_usd', 0):.2f})
- Cost as % of Gross PnL: {costs.get('cost_impact_percent', 0):.1f}%
- Break-even Days: {costs.get('break_even_days', 0):.0f} days

CURRENCY COMPARISON:
- SOL Price Change: {currency['sol_price_change_period']:+.1f}%
- LP vs HODL Outperformance: {currency['outperformance_vs_hodl']:+.1f}%
- Preferred Denomination: {currency['preferred_denomination']}
"""

        infrastructure_impact = f"""=== INFRASTRUCTURE COST ANALYSIS ===
Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

COST STRUCTURE:
- Daily Infrastructure Cost: ${costs.get('daily_cost_usd', 0):.2f} USD
- Total Period Cost: ${costs.get('total_cost_usd', 0):,.2f} USD
- Total Period Cost: {costs.get('total_cost_sol', 0):.3f} SOL

COST BREAKDOWN:
- VPS Hosting: $50.00/month
- RPC Endpoints: $100.00/month  
- Bot Subscription: $200.00/month
- Monthly Total: $350.00 USD

PERFORMANCE IMPACT:
- Gross PnL (SOL): {costs.get('gross_pnl_sol', 0):+.3f} SOL
- Infrastructure Costs: -{costs.get('total_cost_sol', 0):.3f} SOL
- Net PnL (SOL): {costs.get('net_pnl_sol', 0):+.3f} SOL
- Cost Impact: {costs.get('cost_impact_percent', 0):.1f}% of gross returns

EFFICIENCY METRICS:
- Break-even Period: {costs.get('break_even_days', 0):.0f} days
- Positions Analyzed: {costs.get('positions_analyzed', 0)}
- Average Cost per Position: ${costs.get('total_cost_usd', 0)/max(costs.get('positions_analyzed', 1), 1):.2f} USD

ROI ANALYSIS:
- Monthly Infrastructure: $350.00 USD
- Monthly Net Profit: ${usdc['net_pnl_after_costs']*30/metadata['analysis_period_days']:,.2f} USDC (projected)
- Infrastructure ROI: {(usdc['net_pnl_after_costs']*30/metadata['analysis_period_days'])/350*100:.1f}% monthly
"""
        
        return portfolio_summary, infrastructure_impact
        
    def save_reports(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Save analysis reports to timestamped files.
        
        Args:
            analysis_result (Dict[str, Any]): Complete analysis results
            
        Returns:
            Dict[str, str]: Dictionary of saved file paths
        """
        timestamp = self._generate_timestamp()
        
        # Generate reports
        portfolio_summary, infrastructure_impact = self.generate_text_reports(analysis_result)
        
        # Save files with timestamps
        portfolio_file = os.path.join(self.output_dir, f"portfolio_summary_{timestamp}.txt")
        infrastructure_file = os.path.join(self.output_dir, f"infrastructure_impact_{timestamp}.txt")
        
        try:
            with open(portfolio_file, 'w') as f:
                f.write(portfolio_summary)
            logger.info(f"Saved portfolio summary: {portfolio_file}")
            
            with open(infrastructure_file, 'w') as f:
                f.write(infrastructure_impact)
            logger.info(f"Saved infrastructure impact: {infrastructure_file}")
            
        except Exception as e:
            logger.error(f"Failed to save reports: {e}")
            raise
            
        return {
            'portfolio_summary': portfolio_file,
            'infrastructure_impact': infrastructure_file,
            'timestamp': timestamp
        }
        
    def analyze_and_report(self, positions_file: str = "positions_to_analyze.csv") -> Dict[str, Any]:
        """
        Complete analysis workflow: analyze portfolio and generate reports.
        
        Args:
            positions_file (str): Path to positions CSV file
            
        Returns:
            Dict[str, Any]: Analysis results and saved file paths
        """
        # Perform analysis
        analysis_result = self.analyze_portfolio(positions_file)
        
        if 'error' in analysis_result:
            return analysis_result
            
        # Save reports
        saved_files = self.save_reports(analysis_result)
        
        # Combine results
        complete_result = {
            **analysis_result,
            'saved_files': saved_files
        }
        
        # Remove raw data from return (keep in analysis_result for charts)
        if 'raw_data' in complete_result:
            del complete_result['raw_data']
            
        logger.info("Portfolio analysis and reporting completed")
        return complete_result


if __name__ == "__main__":
    # Test the portfolio analytics
    try:
        analytics = PortfolioAnalytics()
        result = analytics.analyze_and_report()
        
        print("Analysis completed successfully!")
        print(f"Files saved: {result.get('saved_files', {})}")
        
        # Print key metrics
        if 'sol_denomination' in result:
            sol = result['sol_denomination']
            print(f"\nKey Results:")
            print(f"Total PnL: {sol['total_pnl_sol']:+.2f} SOL")
            print(f"Sharpe Ratio: {sol['sharpe_ratio']:.2f}")
            print(f"Win Rate: {sol['win_rate']*100:.1f}%")
            
    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        print(f"Error: {e}")