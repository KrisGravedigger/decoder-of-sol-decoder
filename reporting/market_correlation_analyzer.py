"""
Market Correlation Analysis Module

Analyzes portfolio performance correlation with SOL market trends using:
- EMA 50 slope for trend detection
- Pearson correlation analysis
- Trend-based performance segmentation
- Statistical significance testing
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
from scipy import stats
import sys
import os

# Add reporting module to path for imports
# Corrected path logic
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)
    
from reporting.infrastructure_cost_analyzer import InfrastructureCostAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketCorrelationAnalyzer:
    """
    Analyzes correlation between portfolio performance and SOL market trends.
    
    Uses EMA 50 slope for trend detection and Pearson correlation for
    measuring relationship strength between portfolio returns and SOL price movements.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml", api_key: Optional[str] = None):
        """
        Initialize market correlation analyzer.
        
        Args:
            config_path (str): Path to configuration file
            api_key (Optional[str]): Moralis API key
        """
        self.config_path = config_path
        # AIDEV-NOTE-CLAUDE: Pass API key down to the cost analyzer.
        self.cost_analyzer = InfrastructureCostAnalyzer(config_path, api_key=api_key)
        
        # Analysis parameters
        self.ema_period = 50
        self.slope_period = 3  # Days for slope calculation
        self.trend_threshold = 0.001  # 0.1% threshold for uptrend
        
        logger.info("Market Correlation Analyzer initialized")
        
    def analyze_market_correlation(self, positions_df: pd.DataFrame, sol_rates: Dict[str, Optional[float]]) -> Dict[str, Any]:
        """
        Perform complete market correlation analysis using pre-fetched SOL rates.
        
        Args:
            positions_df (pd.DataFrame): Portfolio positions data.
            sol_rates (Dict[str, Optional[float]]): Pre-fetched SOL/USDC price data.
            
        Returns:
            Dict[str, Any]: Complete correlation analysis results.
        """
        logger.info("Starting market correlation analysis with pre-fetched data...")
        
        try:
            if positions_df.empty or 'close_timestamp' not in positions_df.columns:
                 return {'error': 'Positions data is empty or missing required columns.'}
            
            portfolio_start_dt = positions_df['open_timestamp'].min()
            portfolio_end_dt = positions_df['close_timestamp'].max()

            # AIDEV-NOTE-GEMINI: ARCHITECTURAL FIX - We no longer fetch data here.
            # We receive the complete, buffered sol_rates dictionary as an argument.
            if not sol_rates:
                return {'error': "No SOL price data provided to correlation analyzer."}
                
            # Step 1: Process SOL price data to get daily indicators
            sol_daily = self._process_sol_price_data(sol_rates)
            if sol_daily.empty:
                return {'error': "SOL daily data is empty after processing. Cannot perform analysis."}

            # Step 2: Prepare portfolio daily returns
            portfolio_daily = self._calculate_portfolio_daily_returns(positions_df)
            if portfolio_daily.empty:
                return {'error': 'No daily portfolio data available for correlation analysis'}
                
            # Step 3: Align data and calculate correlations
            correlation_results = self._calculate_correlations(portfolio_daily, sol_daily)
            
            # Step 4: Trend-based analysis
            trend_analysis = self._analyze_trend_performance(portfolio_daily, sol_daily)
            
            # Step 5: Statistical significance testing
            significance_tests = self._calculate_statistical_significance(portfolio_daily, sol_daily)
            
            # Compile complete analysis
            analysis_result = {
                'analysis_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'analysis_period': f"{portfolio_start_dt.strftime('%Y-%m-%d')} to {portfolio_end_dt.strftime('%Y-%m-%d')}",
                    'portfolio_days': len(portfolio_daily),
                    'sol_price_days': len(sol_daily),
                    'ema_period': self.ema_period,
                    'slope_period': self.slope_period,
                    'trend_threshold': self.trend_threshold
                },
                'correlation_metrics': correlation_results,
                'trend_analysis': trend_analysis,
                'statistical_significance': significance_tests,
                'raw_data': {
                    'portfolio_daily_returns': portfolio_daily,
                    'sol_daily_data': sol_daily,
                    # We no longer own the full sol_rates, so we reference it
                    'sol_rates_source': 'Provided by orchestrator'
                }
            }
            
            logger.info("Market correlation analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Market correlation analysis failed: {e}", exc_info=True)
            return {'error': str(e)}
        
    def _process_sol_price_data(self, sol_rates: Dict[str, Optional[float]]) -> pd.DataFrame:
        """
        Process SOL price data and calculate technical indicators.
        
        Args:
            sol_rates (Dict[str, Optional[float]]): SOL/USDC rates by date
            
        Returns:
            pd.DataFrame: Processed SOL data with indicators
        """
        if not sol_rates:
            logger.warning("SOL price data is empty. Cannot process.")
            return pd.DataFrame()
            
        valid_rates = {k: v for k, v in sol_rates.items() if v is not None}
        if not valid_rates:
            logger.warning("No valid SOL price data found after filtering. Cannot process.")
            return pd.DataFrame()

        sol_df = pd.DataFrame(list(valid_rates.items()), columns=['date', 'close'])
        sol_df['date'] = pd.to_datetime(sol_df['date'])
        sol_df = sol_df.set_index('date').sort_index()
        
        sol_df['daily_return'] = sol_df['close'].pct_change()
        
        # AIDEV-NOTE-GEMINI: min_periods ensures EMA is calculated even if we have slightly less than 50 days of buffer.
        sol_df['ema_50'] = sol_df['close'].ewm(span=self.ema_period, min_periods=min(self.ema_period, len(sol_df))).mean()
        
        sol_df['ema_slope'] = sol_df['ema_50'].pct_change(periods=self.slope_period)
        
        sol_df['trend'] = np.where(sol_df['ema_slope'] > self.trend_threshold, 'uptrend', 'downtrend')
        
        sol_df = sol_df.dropna(subset=['daily_return', 'ema_slope'])
        
        if not sol_df.empty:
            logger.info(f"Processed SOL price data for {len(sol_df)} days")
        else:
            logger.warning("SOL price data became empty after processing and NaN removal.")

        return sol_df
        
    def _calculate_correlations(self, portfolio_daily: pd.Series, sol_daily: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate correlation metrics between portfolio and SOL returns.
        
        Args:
            portfolio_daily (pd.Series): Portfolio daily returns
            sol_daily (pd.DataFrame): SOL daily data
            
        Returns:
            Dict[str, Any]: Correlation analysis results
        """
        if sol_daily.empty:
            return {'error': 'SOL daily data is empty.'}

        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        
        if len(common_dates) < 2:
            logger.warning(f"Only {len(common_dates)} common dates. Cannot calculate correlation.")
            return {'error': 'Less than 2 common data points for correlation.'}

        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        pearson_corr, pearson_p = stats.pearsonr(portfolio_aligned, sol_aligned)
        
        return {
            'pearson_correlation': pearson_corr,
            'pearson_p_value': pearson_p,
            'is_significant': pearson_p < 0.05,
            'common_days': len(common_dates),
            'portfolio_volatility': portfolio_aligned.std(),
            'sol_volatility': sol_aligned.std(),
            'portfolio_mean_return': portfolio_aligned.mean(),
            'sol_mean_return': sol_aligned.mean()
        }
        
    def _analyze_trend_performance(self, portfolio_daily: pd.Series, sol_daily: pd.DataFrame) -> Dict[str, Any]:
        """
        Analyze portfolio performance during different SOL trend periods.
        
        Args:
            portfolio_daily (pd.Series): Portfolio daily returns
            sol_daily (pd.DataFrame): SOL daily data with trend classification
            
        Returns:
            Dict[str, Any]: Trend-based performance analysis
        """
        if sol_daily.empty: return {'error': 'SOL daily data is empty for trend analysis.'}
        
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates]
        
        uptrend_mask = sol_aligned['trend'] == 'uptrend'
        downtrend_mask = sol_aligned['trend'] == 'downtrend'
        uptrend_returns = portfolio_aligned[uptrend_mask]
        downtrend_returns = portfolio_aligned[downtrend_mask]
        
        trend_analysis = {
            'uptrend': {
                'days': len(uptrend_returns),
                'mean_return': uptrend_returns.mean() if len(uptrend_returns) > 0 else 0,
                'total_return': uptrend_returns.sum() if len(uptrend_returns) > 0 else 0,
                'win_rate': (uptrend_returns > 0).mean() if len(uptrend_returns) > 0 else 0
            },
            'downtrend': {
                'days': len(downtrend_returns),
                'mean_return': downtrend_returns.mean() if len(downtrend_returns) > 0 else 0,
                'total_return': downtrend_returns.sum() if len(downtrend_returns) > 0 else 0,
                'win_rate': (downtrend_returns > 0).mean() if len(downtrend_returns) > 0 else 0
            }
        }
        
        if len(uptrend_returns) > 1 and len(downtrend_returns) > 1:
            t_stat, t_p_value = stats.ttest_ind(uptrend_returns, downtrend_returns, equal_var=False)
            trend_analysis['performance_difference'] = {
                'uptrend_vs_downtrend_mean_diff': trend_analysis['uptrend']['mean_return'] - trend_analysis['downtrend']['mean_return'],
                't_statistic': t_stat,
                't_p_value': t_p_value,
                'difference_is_significant': t_p_value < 0.05
            }
        
        trend_analysis['trend_distribution'] = {
            'uptrend_percentage': (sol_aligned['trend'] == 'uptrend').mean() * 100,
            'downtrend_percentage': (sol_aligned['trend'] == 'downtrend').mean() * 100
        }
        
        return trend_analysis
        
    def _calculate_statistical_significance(self, portfolio_daily: pd.Series, sol_daily: pd.DataFrame) -> Dict[str, Any]:
        """
        Calculate statistical significance tests for correlation analysis.
        
        Args:
            portfolio_daily (pd.Series): Portfolio daily returns
            sol_daily (pd.DataFrame): SOL daily data
            
        Returns:
            Dict[str, Any]: Statistical significance test results
        """
        if sol_daily.empty: return {'error': 'SOL daily data is empty.'}

        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        if len(common_dates) < 3: return {'error': 'Insufficient data for statistical testing (< 3 points)'}
            
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        pearson_corr, pearson_p = stats.pearsonr(portfolio_aligned, sol_aligned)
        
        n = len(common_dates)
        if n <= 3: return {'error': f'Sample size ({n}) too small for confidence interval.'}
        
        z = np.arctanh(pearson_corr)
        se = 1 / np.sqrt(n - 3)
        z_crit = stats.norm.ppf(0.975)  # 95% confidence
        z_low, z_high = z - z_crit * se, z + z_crit * se
        corr_ci_low, corr_ci_high = np.tanh(z_low), np.tanh(z_high)
        
        return {
            'sample_size': n,
            'correlation_confidence_interval_95': [corr_ci_low, corr_ci_high],
            'correlation_is_significant_95': pearson_p < 0.05
        }
        
    def generate_correlation_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of correlation analysis.
        
        Args:
            analysis_result (Dict[str, Any]): Analysis results
            
        Returns:
            str: Summary text
        """
        if 'error' in analysis_result: return f"Correlation Analysis Error: {analysis_result['error']}"
        corr = analysis_result.get('correlation_metrics', {})
        trend = analysis_result.get('trend_analysis', {})
        if not corr or not trend or 'pearson_correlation' not in corr: return "Correlation Analysis Summary: Incomplete data."

        summary = ["MARKET CORRELATION ANALYSIS SUMMARY", "=" * 50]
        summary.append(f"Overall SOL Correlation: {corr.get('pearson_correlation', 0):.3f}")
        summary.append(f"Statistical Significance: {'Yes' if corr.get('is_significant') else 'No'} (p={corr.get('pearson_p_value', 1):.3f})")
        
        uptrend = trend.get('uptrend', {})
        downtrend = trend.get('downtrend', {})
        
        summary.append("\nTREND-BASED PERFORMANCE:")
        summary.append(f"Uptrend Days: {uptrend.get('days',0)} ({trend.get('trend_distribution', {}).get('uptrend_percentage',0):.1f}%) | Avg Return: {uptrend.get('mean_return',0):+.4f} SOL/day")
        summary.append(f"Downtrend Days: {downtrend.get('days',0)} ({trend.get('trend_distribution', {}).get('downtrend_percentage',0):.1f}%) | Avg Return: {downtrend.get('mean_return',0):+.4f} SOL/day")

        if 'performance_difference' in trend:
            diff = trend['performance_difference']
            summary.append(f"Performance Difference Significant: {'Yes' if diff.get('difference_is_significant') else 'No'}")
            
        return "\n".join(summary)