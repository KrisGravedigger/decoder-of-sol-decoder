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
sys.path.append('reporting')
from infrastructure_cost_analyzer import InfrastructureCostAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MarketCorrelationAnalyzer:
    """
    Analyzes correlation between portfolio performance and SOL market trends.
    
    Uses EMA 50 slope for trend detection and Pearson correlation for
    measuring relationship strength between portfolio returns and SOL price movements.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize market correlation analyzer.
        
        Args:
            config_path (str): Path to configuration file
        """
        self.config_path = config_path
        self.cost_analyzer = InfrastructureCostAnalyzer(config_path)
        
        # Analysis parameters
        self.ema_period = 50
        self.slope_period = 3  # Days for slope calculation
        self.trend_threshold = 0.001  # 0.1% threshold for uptrend
        
        logger.info("Market Correlation Analyzer initialized")
        
    def analyze_market_correlation(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform complete market correlation analysis.
        
        Args:
            positions_df (pd.DataFrame): Portfolio positions data
            
        Returns:
            Dict[str, Any]: Complete correlation analysis results
        """
        logger.info("Starting market correlation analysis...")
        
        try:
            # Step 1: Prepare portfolio daily returns
            portfolio_daily = self._calculate_portfolio_daily_returns(positions_df)
            
            if portfolio_daily.empty:
                return {'error': 'No daily portfolio data available for correlation analysis'}
                
            # Step 2: Get SOL price data for the same period
            start_date = portfolio_daily.index.min().strftime("%Y-%m-%d")
            end_date = portfolio_daily.index.max().strftime("%Y-%m-%d")
            
            sol_rates = self.cost_analyzer.get_sol_usdc_rates(start_date, end_date)
            
            if not sol_rates:
                return {'error': f'No SOL price data available for period {start_date} to {end_date}'}
                
            # Step 3: Process SOL price data
            sol_daily = self._process_sol_price_data(sol_rates)
            
            # Step 4: Align data and calculate correlations
            correlation_results = self._calculate_correlations(portfolio_daily, sol_daily)
            
            # Step 5: Trend-based analysis
            trend_analysis = self._analyze_trend_performance(portfolio_daily, sol_daily)
            
            # Step 6: Statistical significance testing
            significance_tests = self._calculate_statistical_significance(portfolio_daily, sol_daily)
            
            # Compile complete analysis
            analysis_result = {
                'analysis_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'analysis_period': f"{start_date} to {end_date}",
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
                    'sol_rates': sol_rates
                }
            }
            
            logger.info("Market correlation analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Market correlation analysis failed: {e}")
            return {'error': str(e)}
            
    def _calculate_portfolio_daily_returns(self, positions_df: pd.DataFrame) -> pd.Series:
        """
        Calculate daily portfolio returns from positions data.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            pd.Series: Daily returns indexed by date
        """
        # AIDEV-NOTE-CLAUDE: Convert position close dates to daily PnL aggregation
        positions_df = positions_df.copy()
        positions_df['close_date'] = positions_df['close_timestamp'].dt.date
        
        # Aggregate PnL by close date
        daily_pnl = positions_df.groupby('close_date')['pnl_sol'].sum()
        
        # Convert to pandas Series with datetime index
        daily_returns = pd.Series(daily_pnl.values, index=pd.to_datetime(daily_pnl.index))
        daily_returns = daily_returns.sort_index()
        
        logger.info(f"Calculated daily returns for {len(daily_returns)} days")
        return daily_returns
        
    def _process_sol_price_data(self, sol_rates: Dict[str, float]) -> pd.DataFrame:
        """
        Process SOL price data and calculate technical indicators.
        
        Args:
            sol_rates (Dict[str, float]): SOL/USDC rates by date
            
        Returns:
            pd.DataFrame: Processed SOL data with indicators
        """
        # Convert to DataFrame
        sol_df = pd.DataFrame([
            {'date': pd.to_datetime(date), 'close': price}
            for date, price in sol_rates.items()
        ]).set_index('date').sort_index()
        
        # Calculate daily returns
        sol_df['daily_return'] = sol_df['close'].pct_change()
        
        # Calculate EMA 50
        sol_df['ema_50'] = sol_df['close'].ewm(span=self.ema_period).mean()
        
        # Calculate EMA slope (3-day percentage change)
        sol_df['ema_slope'] = sol_df['ema_50'].pct_change(periods=self.slope_period)
        
        # Determine trend based on EMA slope
        sol_df['trend'] = np.where(
            sol_df['ema_slope'] > self.trend_threshold,
            'uptrend',
            'downtrend'
        )
        
        # Clean data (remove NaN values)
        sol_df = sol_df.dropna()
        
        logger.info(f"Processed SOL price data for {len(sol_df)} days")
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
        # Align data by common dates
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        
        if len(common_dates) < 10:
            logger.warning(f"Only {len(common_dates)} common dates - correlation may be unreliable")
            
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        # Calculate Pearson correlation
        pearson_corr, pearson_p = stats.pearsonr(portfolio_aligned, sol_aligned)
        
        # Calculate additional metrics
        portfolio_volatility = portfolio_aligned.std()
        sol_volatility = sol_aligned.std()
        
        return {
            'pearson_correlation': pearson_corr,
            'pearson_p_value': pearson_p,
            'is_significant': pearson_p < 0.05,
            'common_days': len(common_dates),
            'portfolio_volatility': portfolio_volatility,
            'sol_volatility': sol_volatility,
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
        # Align data by common dates
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates]
        
        # Separate performance by trend
        uptrend_mask = sol_aligned['trend'] == 'uptrend'
        downtrend_mask = sol_aligned['trend'] == 'downtrend'
        
        uptrend_returns = portfolio_aligned[uptrend_mask]
        downtrend_returns = portfolio_aligned[downtrend_mask]
        
        # Calculate trend-specific metrics
        trend_analysis = {
            'uptrend': {
                'days': len(uptrend_returns),
                'mean_return': uptrend_returns.mean() if len(uptrend_returns) > 0 else 0,
                'total_return': uptrend_returns.sum() if len(uptrend_returns) > 0 else 0,
                'volatility': uptrend_returns.std() if len(uptrend_returns) > 1 else 0,
                'win_rate': (uptrend_returns > 0).mean() if len(uptrend_returns) > 0 else 0
            },
            'downtrend': {
                'days': len(downtrend_returns),
                'mean_return': downtrend_returns.mean() if len(downtrend_returns) > 0 else 0,
                'total_return': downtrend_returns.sum() if len(downtrend_returns) > 0 else 0,
                'volatility': downtrend_returns.std() if len(downtrend_returns) > 1 else 0,
                'win_rate': (downtrend_returns > 0).mean() if len(downtrend_returns) > 0 else 0
            }
        }
        
        # Performance difference analysis
        if len(uptrend_returns) > 0 and len(downtrend_returns) > 0:
            # Statistical test for difference in means
            t_stat, t_p_value = stats.ttest_ind(uptrend_returns, downtrend_returns)
            
            trend_analysis['performance_difference'] = {
                'uptrend_vs_downtrend_mean_diff': trend_analysis['uptrend']['mean_return'] - trend_analysis['downtrend']['mean_return'],
                't_statistic': t_stat,
                't_p_value': t_p_value,
                'difference_is_significant': t_p_value < 0.05
            }
        else:
            trend_analysis['performance_difference'] = {
                'uptrend_vs_downtrend_mean_diff': 0,
                't_statistic': None,
                't_p_value': None,
                'difference_is_significant': False
            }
            
        # Trend distribution
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
        # Align data
        common_dates = portfolio_daily.index.intersection(sol_daily.index)
        portfolio_aligned = portfolio_daily.loc[common_dates]
        sol_aligned = sol_daily.loc[common_dates, 'daily_return']
        
        if len(common_dates) < 3:
            return {'error': 'Insufficient data for statistical testing'}
            
        # Pearson correlation with confidence interval
        pearson_corr, pearson_p = stats.pearsonr(portfolio_aligned, sol_aligned)
        
        # Calculate confidence interval for correlation (Fisher z-transform)
        n = len(common_dates)
        z = np.arctanh(pearson_corr)
        se = 1 / np.sqrt(n - 3)
        z_crit = stats.norm.ppf(0.975)  # 95% confidence
        
        z_low = z - z_crit * se
        z_high = z + z_crit * se
        
        corr_ci_low = np.tanh(z_low)
        corr_ci_high = np.tanh(z_high)
        
        return {
            'sample_size': n,
            'correlation_confidence_interval_95': [corr_ci_low, corr_ci_high],
            'correlation_is_significant_95': pearson_p < 0.05,
            'correlation_is_significant_99': pearson_p < 0.01,
            'power_analysis': {
                'minimum_detectable_correlation_95': 2 / np.sqrt(n - 1) if n > 1 else 1,
                'sample_size_adequate': n >= 30
            }
        }
        
    def generate_correlation_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of correlation analysis.
        
        Args:
            analysis_result (Dict[str, Any]): Analysis results
            
        Returns:
            str: Summary text
        """
        if 'error' in analysis_result:
            return f"Correlation Analysis Error: {analysis_result['error']}"
            
        corr = analysis_result['correlation_metrics']
        trend = analysis_result['trend_analysis']
        sig = analysis_result['statistical_significance']
        
        summary = []
        summary.append("MARKET CORRELATION ANALYSIS SUMMARY")
        summary.append("=" * 50)
        
        # Overall correlation
        summary.append(f"Overall SOL Correlation: {corr['pearson_correlation']:.3f}")
        summary.append(f"Statistical Significance: {'Yes' if corr['is_significant'] else 'No'} (p={corr['pearson_p_value']:.3f})")
        summary.append(f"Sample Size: {corr['common_days']} days")
        
        # Trend analysis
        summary.append("\nTREND-BASED PERFORMANCE:")
        summary.append(f"Uptrend Days: {trend['uptrend']['days']} ({trend['trend_distribution']['uptrend_percentage']:.1f}%)")
        summary.append(f"Uptrend Avg Return: {trend['uptrend']['mean_return']:+.4f} SOL/day")
        summary.append(f"Uptrend Win Rate: {trend['uptrend']['win_rate']*100:.1f}%")
        
        summary.append(f"Downtrend Days: {trend['downtrend']['days']} ({trend['trend_distribution']['downtrend_percentage']:.1f}%)")
        summary.append(f"Downtrend Avg Return: {trend['downtrend']['mean_return']:+.4f} SOL/day")
        summary.append(f"Downtrend Win Rate: {trend['downtrend']['win_rate']*100:.1f}%")
        
        # Performance difference
        if 'performance_difference' in trend:
            diff = trend['performance_difference']
            summary.append(f"\nPerformance Difference: {diff['uptrend_vs_downtrend_mean_diff']:+.4f} SOL/day")
            summary.append(f"Difference Significant: {'Yes' if diff['difference_is_significant'] else 'No'}")
            
        # Recommendation
        summary.append("\nRECOMMENDATION:")
        if corr['pearson_correlation'] > 0.3 and corr['is_significant']:
            summary.append("Strong positive correlation with SOL - strategy performs well in SOL uptrends")
        elif corr['pearson_correlation'] < -0.3 and corr['is_significant']:
            summary.append("Strong negative correlation with SOL - strategy performs well in SOL downtrends")
        elif corr['is_significant']:
            summary.append(f"Weak but significant correlation - monitor SOL trends")
        else:
            summary.append("No significant correlation with SOL market trends")
            
        return "\n".join(summary)


if __name__ == "__main__":
    # Test market correlation analyzer
    import pandas as pd
    
    # Create sample positions data for testing
    test_positions = pd.DataFrame({
        'close_timestamp': pd.date_range('2024-01-01', periods=30, freq='D'),
        'pnl_sol': np.random.normal(0.1, 0.5, 30),
        'investment_sol': np.random.uniform(1, 5, 30)
    })
    
    analyzer = MarketCorrelationAnalyzer()
    result = analyzer.analyze_market_correlation(test_positions)
    
    if 'error' not in result:
        summary = analyzer.generate_correlation_summary(result)
        print(summary)
    else:
        print(f"Analysis failed: {result['error']}")
