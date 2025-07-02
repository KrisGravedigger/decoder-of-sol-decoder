"""
Weekend Parameter Analysis Module

Analyzes the impact of weekendSizePercentage parameter on portfolio performance by:
- Simulating two scenarios: current CSV data vs alternative sizing for weekend positions
- Only weekend-opened positions (Sat/Sun UTC) are affected by the parameter
- Weekday positions remain identical in both scenarios
- Compares total PnL, ROI, and Sharpe ratio between scenarios

BUSINESS ASSUMPTION: CSV always represents actual positions (regardless of config setting).
weekend_size_reduction config indicates how to interpret the data:
- weekend_size_reduction=1: CSV has reduced weekend positions, simulate enlarged for comparison
- weekend_size_reduction=0: CSV has normal positions, simulate reduced for comparison
"""

import logging
import pandas as pd
import numpy as np
import yaml
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeekendParameterAnalyzer:
    """
    Analyzes impact of weekendSizePercentage parameter on portfolio performance.
    
    Simulates alternative weekend position sizing to determine optimal configuration
    by comparing current positions with hypothetical alternative sizing.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize weekend parameter analyzer with YAML configuration.
        
        Args:
            config_path (str): Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.weekend_config = self.config.get('weekend_analysis', {})
        
        # Load configuration parameters
        self.weekend_size_reduction = self.weekend_config.get('weekend_size_reduction', 1)
        self.size_reduction_percentage = self.weekend_config.get('size_reduction_percentage', 80)
        
        # Calculate size multiplier (e.g., 80% reduction = 20% remains = 5x difference)
        if self.size_reduction_percentage > 0:
            self.weekend_size_factor = (100 - self.size_reduction_percentage) / 100  # 0.2 for 80% reduction
            self.size_multiplier = 100 / (100 - self.size_reduction_percentage)  # 5x for 80% reduction
        else:
            self.weekend_size_factor = 1.0
            self.size_multiplier = 1.0
        
        logger.info(f"Weekend Parameter Analyzer initialized")
        logger.info(f"weekend_size_reduction: {self.weekend_size_reduction}")
        logger.info(f"size_reduction_percentage: {self.size_reduction_percentage}%")
        if self.size_reduction_percentage > 0:
            logger.info(f"Weekend size factor: {self.weekend_size_factor:.2f}, multiplier: {self.size_multiplier:.1f}x")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration with error handling."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {
                'weekend_analysis': {
                    'weekend_size_reduction': 1,
                    'size_reduction_percentage': 80
                }
            }
            
    def analyze_weekend_parameter_impact(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform complete weekend parameter impact analysis.
        
        Args:
            positions_df (pd.DataFrame): Portfolio positions data
            
        Returns:
            Dict[str, Any]: Complete weekend parameter analysis results
        """
        logger.info("Starting weekend parameter impact analysis...")
        
        try:
            # Step 1: Classify positions by weekend exposure
            positions_classified = self._classify_weekend_positions(positions_df)
            
            # Step 2: Simulate alternative scenario
            simulation_results = self._simulate_alternative_scenario(positions_classified)
            
            # Step 3: Calculate performance comparison
            performance_comparison = self._calculate_performance_comparison(simulation_results)
            
            # Step 4: Generate recommendations
            recommendations = self._generate_recommendations(performance_comparison)
            
            # Compile complete analysis
            analysis_result = {
                'analysis_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'weekend_size_reduction': self.weekend_size_reduction,
                    'size_reduction_percentage': self.size_reduction_percentage,
                    'weekend_size_factor': self.weekend_size_factor,
                    'size_multiplier': self.size_multiplier,
                    'total_positions': len(positions_df),
                    'weekend_opened_positions': len(positions_classified[positions_classified['weekend_opened']]),
                    'weekday_opened_positions': len(positions_classified[~positions_classified['weekend_opened']])
                },
                'position_classification': self._get_classification_summary(positions_classified),
                'simulation_results': simulation_results,
                'performance_comparison': performance_comparison,
                'recommendations': recommendations,
                'raw_data': {
                    'positions_classified': positions_classified
                }
            }
            
            logger.info("Weekend parameter analysis completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Weekend parameter analysis failed: {e}")
            return {'error': str(e)}
            
    def _classify_weekend_positions(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify positions based on weekend opening timing.
        
        Args:
            positions_df (pd.DataFrame): Positions data
            
        Returns:
            pd.DataFrame: Positions with weekend classification
        """
        positions_classified = positions_df.copy()
        
        # Ensure timestamps are datetime objects
        positions_classified['open_timestamp'] = pd.to_datetime(positions_classified['open_timestamp'])
        positions_classified['close_timestamp'] = pd.to_datetime(positions_classified['close_timestamp'])
        
        # AIDEV-NOTE-CLAUDE: Weekend classification based on open_timestamp only (not duration)
        # weekday(): Monday=0, Sunday=6; Weekend: Saturday=5, Sunday=6
        positions_classified['open_weekday'] = positions_classified['open_timestamp'].dt.weekday
        positions_classified['weekend_opened'] = positions_classified['open_weekday'] >= 5
        
        # Additional classification for analysis
        positions_classified['open_day_name'] = positions_classified['open_timestamp'].dt.day_name()
        
        logger.info(f"Classified {len(positions_classified)} positions by weekend timing")
        logger.info(f"Weekend opened: {positions_classified['weekend_opened'].sum()}")
        logger.info(f"Weekday opened: {(~positions_classified['weekend_opened']).sum()}")
        
        return positions_classified
        
    def _simulate_alternative_scenario(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Simulate alternative scenario based on weekend_size_reduction setting.
        
        Args:
            positions_df (pd.DataFrame): Classified positions data
            
        Returns:
            Dict[str, Any]: Simulation results for current vs alternative scenarios
        """
        # AIDEV-NOTE-CLAUDE: Core business logic - CSV always represents actual positions
        # weekend_size_reduction config tells us how to interpret and simulate alternative
        
        simulation_data = positions_df.copy()
        
        # Current data from CSV (actual positions)
        simulation_data['current_pnl_sol'] = simulation_data['pnl_sol']
        simulation_data['current_investment_sol'] = simulation_data['investment_sol']
        
        # Simulate alternative scenario
        if self.weekend_size_reduction == 1:
            # CSV has reduced weekend positions → simulate enlarged (normal) positions
            scenario_name_current = f"ENABLED ({self.size_reduction_percentage}% weekend reduction)"
            scenario_name_alternative = "DISABLED (normal weekend sizes)"
            
            simulation_data['alternative_pnl_sol'] = np.where(
                simulation_data['weekend_opened'],
                simulation_data['pnl_sol'] * self.size_multiplier,  # Enlarge weekend positions
                simulation_data['pnl_sol']  # Weekday positions unchanged
            )
            simulation_data['alternative_investment_sol'] = np.where(
                simulation_data['weekend_opened'],
                simulation_data['investment_sol'] * self.size_multiplier,  # Enlarge weekend positions
                simulation_data['investment_sol']  # Weekday positions unchanged
            )
        else:
            # CSV has normal weekend positions → simulate reduced positions
            scenario_name_current = "DISABLED (normal weekend sizes)"
            scenario_name_alternative = f"ENABLED ({self.size_reduction_percentage}% weekend reduction)"
            
            simulation_data['alternative_pnl_sol'] = np.where(
                simulation_data['weekend_opened'],
                simulation_data['pnl_sol'] * self.weekend_size_factor,  # Reduce weekend positions
                simulation_data['pnl_sol']  # Weekday positions unchanged
            )
            simulation_data['alternative_investment_sol'] = np.where(
                simulation_data['weekend_opened'],
                simulation_data['investment_sol'] * self.weekend_size_factor,  # Reduce weekend positions
                simulation_data['investment_sol']  # Weekday positions unchanged
            )
        
        # Calculate ROI for both scenarios
        simulation_data['current_roi'] = simulation_data['current_pnl_sol'] / simulation_data['current_investment_sol']
        simulation_data['alternative_roi'] = simulation_data['alternative_pnl_sol'] / simulation_data['alternative_investment_sol']
        
        # Separate weekend and weekday analysis
        weekend_positions = simulation_data[simulation_data['weekend_opened']]
        weekday_positions = simulation_data[~simulation_data['weekend_opened']]
        
        return {
            'simulation_data': simulation_data,
            'scenario_names': {
                'current': scenario_name_current,
                'alternative': scenario_name_alternative
            },
            'current_scenario': {
                'total_pnl': simulation_data['current_pnl_sol'].sum(),
                'total_investment': simulation_data['current_investment_sol'].sum(),
                'weekend_positions': {
                    'count': len(weekend_positions),
                    'pnl': weekend_positions['current_pnl_sol'].sum(),
                    'investment': weekend_positions['current_investment_sol'].sum()
                },
                'weekday_positions': {
                    'count': len(weekday_positions),
                    'pnl': weekday_positions['current_pnl_sol'].sum(),
                    'investment': weekday_positions['current_investment_sol'].sum()
                }
            },
            'alternative_scenario': {
                'total_pnl': simulation_data['alternative_pnl_sol'].sum(),
                'total_investment': simulation_data['alternative_investment_sol'].sum(),
                'weekend_positions': {
                    'count': len(weekend_positions),
                    'pnl': weekend_positions['alternative_pnl_sol'].sum(),
                    'investment': weekend_positions['alternative_investment_sol'].sum()
                },
                'weekday_positions': {
                    'count': len(weekday_positions),
                    'pnl': weekday_positions['alternative_pnl_sol'].sum(),
                    'investment': weekday_positions['alternative_investment_sol'].sum()
                }
            }
        }
        
    def _calculate_performance_comparison(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate performance comparison between scenarios.
        
        Args:
            simulation_results (Dict[str, Any]): Simulation results
            
        Returns:
            Dict[str, Any]: Performance comparison metrics
        """
        simulation_data = simulation_results['simulation_data']
        scenario_names = simulation_results['scenario_names']
        
        # Calculate metrics for both scenarios
        current_metrics = self._calculate_portfolio_metrics(
            simulation_data['current_pnl_sol'],
            simulation_data['current_investment_sol']
        )
        
        alternative_metrics = self._calculate_portfolio_metrics(
            simulation_data['alternative_pnl_sol'],
            simulation_data['alternative_investment_sol']
        )
        
        # Calculate impact (alternative - current)
        total_pnl_impact = alternative_metrics['total_pnl'] - current_metrics['total_pnl']
        roi_impact = alternative_metrics['average_roi'] - current_metrics['average_roi']
        sharpe_impact = alternative_metrics['sharpe_ratio'] - current_metrics['sharpe_ratio']
        
        # Calculate percentage improvement
        pnl_improvement_percent = (
            (total_pnl_impact / abs(current_metrics['total_pnl']) * 100) 
            if current_metrics['total_pnl'] != 0 else 0
        )
        
        # Determine recommendation based on impact
        if self.weekend_size_reduction == 1:
            # Current = enabled, alternative = disabled
            recommendation = 'DISABLE' if total_pnl_impact > 0 else 'KEEP_ENABLED'
        else:
            # Current = disabled, alternative = enabled
            recommendation = 'ENABLE' if total_pnl_impact > 0 else 'KEEP_DISABLED'
        
        return {
            'current_scenario': {
                'name': scenario_names['current'],
                'description': 'Current CSV data (actual positions)',
                'metrics': current_metrics
            },
            'alternative_scenario': {
                'name': scenario_names['alternative'],
                'description': 'Simulated alternative weekend sizing',
                'metrics': alternative_metrics
            },
            'impact_analysis': {
                'total_pnl_difference_sol': total_pnl_impact,
                'roi_difference': roi_impact,
                'sharpe_difference': sharpe_impact,
                'pnl_improvement_percent': pnl_improvement_percent,
                'recommendation': recommendation
            }
        }
        
    def _calculate_portfolio_metrics(self, pnl_series: pd.Series, investment_series: pd.Series) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics (excluding win_rate for weekend analysis).
        
        Args:
            pnl_series (pd.Series): PnL values
            investment_series (pd.Series): Investment values
            
        Returns:
            Dict[str, float]: Portfolio metrics
        """
        roi_series = pnl_series / investment_series
        
        return {
            'total_pnl': pnl_series.sum(),
            'total_investment': investment_series.sum(),
            'average_roi': roi_series.mean(),
            'average_profit': pnl_series[pnl_series > 0].mean() if (pnl_series > 0).any() else 0,
            'average_loss': pnl_series[pnl_series < 0].mean() if (pnl_series < 0).any() else 0,
            'profit_factor': (
                pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum()) 
                if (pnl_series < 0).any() and pnl_series[pnl_series < 0].sum() != 0 else float('inf')
            ),
            'sharpe_ratio': roi_series.mean() / roi_series.std() if roi_series.std() > 0 else 0
        }
        
    def _get_classification_summary(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary of position classification.
        
        Args:
            positions_df (pd.DataFrame): Classified positions
            
        Returns:
            Dict[str, Any]: Classification summary
        """
        weekend_count = positions_df['weekend_opened'].sum()
        weekday_count = len(positions_df) - weekend_count
        
        # Day distribution
        day_distribution = positions_df['open_day_name'].value_counts().to_dict()
        
        # Weekend vs weekday PnL (using current data)
        weekend_pnl = positions_df[positions_df['weekend_opened']]['pnl_sol'].sum()
        weekday_pnl = positions_df[~positions_df['weekend_opened']]['pnl_sol'].sum()
        
        return {
            'total_positions': len(positions_df),
            'weekend_opened': {
                'count': weekend_count,
                'percentage': weekend_count / len(positions_df) * 100,
                'total_pnl': weekend_pnl,
                'avg_pnl': positions_df[positions_df['weekend_opened']]['pnl_sol'].mean() if weekend_count > 0 else 0
            },
            'weekday_opened': {
                'count': weekday_count,
                'percentage': weekday_count / len(positions_df) * 100,
                'total_pnl': weekday_pnl,
                'avg_pnl': positions_df[~positions_df['weekend_opened']]['pnl_sol'].mean() if weekday_count > 0 else 0
            },
            'day_distribution': day_distribution
        }
        
    def _generate_recommendations(self, performance_comparison: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate actionable recommendations based on analysis.
        
        Args:
            performance_comparison (Dict[str, Any]): Performance comparison results
            
        Returns:
            Dict[str, Any]: Recommendations and insights
        """
        impact = performance_comparison['impact_analysis']
        
        recommendations = {
            'primary_recommendation': impact['recommendation'],
            'confidence_level': (
                'HIGH' if abs(impact['pnl_improvement_percent']) > 10 
                else 'MEDIUM' if abs(impact['pnl_improvement_percent']) > 5 
                else 'LOW'
            ),
            'expected_impact': {
                'pnl_change_sol': impact['total_pnl_difference_sol'],
                'pnl_change_percent': impact['pnl_improvement_percent'],
                'roi_change': impact['roi_difference'],
                'sharpe_change': impact['sharpe_difference']
            }
        }
        
        # Generate detailed explanation
        current_name = performance_comparison['current_scenario']['name']
        alternative_name = performance_comparison['alternative_scenario']['name']
        
        if impact['total_pnl_difference_sol'] > 0:
            recommendations['explanation'] = (
                f"Switching from '{current_name}' to '{alternative_name}' would improve "
                f"portfolio performance by {impact['total_pnl_difference_sol']:+.3f} SOL "
                f"({impact['pnl_improvement_percent']:+.1f}%). "
                f"Recommendation: {impact['recommendation']}"
            )
        else:
            recommendations['explanation'] = (
                f"Current configuration '{current_name}' performs better than '{alternative_name}'. "
                f"Switching would reduce portfolio PnL by {abs(impact['total_pnl_difference_sol']):.3f} SOL "
                f"({abs(impact['pnl_improvement_percent']):.1f}%). "
                f"Recommendation: {impact['recommendation']}"
            )
            
        # Risk considerations
        recommendations['risk_considerations'] = [
            "Analysis based on historical data - future market conditions may differ",
            f"Only weekend-opened positions affected by parameter ({performance_comparison['current_scenario']['metrics']['total_investment']:.1f} SOL analyzed)",
            "Weekend definition: Saturday-Sunday UTC timezone based on open_timestamp",
            f"CSV data represents actual positions (weekend_size_reduction config: {self.weekend_size_reduction})",
            f"Position size factor: {self.weekend_size_factor:.2f} (from {self.size_reduction_percentage}% reduction)"
        ]
        
        return recommendations
        
    def generate_weekend_analysis_summary(self, analysis_result: Dict[str, Any]) -> str:
        """
        Generate human-readable summary of weekend parameter analysis.
        
        Args:
            analysis_result (Dict[str, Any]): Analysis results
            
        Returns:
            str: Summary text
        """
        if 'error' in analysis_result:
            return f"Weekend Parameter Analysis Error: {analysis_result['error']}"
            
        meta = analysis_result['analysis_metadata']
        classification = analysis_result['position_classification']
        comparison = analysis_result['performance_comparison']
        recommendations = analysis_result['recommendations']
        
        summary = []
        summary.append("WEEKEND PARAMETER ANALYSIS SUMMARY")
        summary.append("=" * 50)
        
        # Configuration
        summary.append(f"Analysis Configuration:")
        summary.append(f"  Current Setting: {'ENABLED' if meta['weekend_size_reduction'] else 'DISABLED'}")
        summary.append(f"  Size Reduction: {meta['size_reduction_percentage']}% (factor: {meta['weekend_size_factor']:.2f})")
        
        # Position classification
        summary.append(f"\nPosition Classification:")
        summary.append(f"  Total Positions: {meta['total_positions']}")
        summary.append(f"  Weekend Opened: {classification['weekend_opened']['count']} ({classification['weekend_opened']['percentage']:.1f}%)")
        summary.append(f"  Weekday Opened: {classification['weekday_opened']['count']} ({classification['weekday_opened']['percentage']:.1f}%)")
        
        # Scenario comparison
        current = comparison['current_scenario']['metrics']
        alternative = comparison['alternative_scenario']['metrics']
        
        summary.append(f"\nCURRENT SCENARIO - {comparison['current_scenario']['name']}:")
        summary.append(f"  Total PnL: {current['total_pnl']:+.3f} SOL")
        summary.append(f"  Average ROI: {current['average_roi']*100:+.2f}%")
        summary.append(f"  Sharpe Ratio: {current['sharpe_ratio']:+.3f}")
        
        summary.append(f"\nALTERNATIVE SCENARIO - {comparison['alternative_scenario']['name']}:")
        summary.append(f"  Total PnL: {alternative['total_pnl']:+.3f} SOL")
        summary.append(f"  Average ROI: {alternative['average_roi']*100:+.2f}%")
        summary.append(f"  Sharpe Ratio: {alternative['sharpe_ratio']:+.3f}")
        
        # Impact analysis
        impact = comparison['impact_analysis']
        summary.append(f"\nIMPACT ANALYSIS (Alternative vs Current):")
        summary.append(f"  PnL Difference: {impact['total_pnl_difference_sol']:+.3f} SOL ({impact['pnl_improvement_percent']:+.1f}%)")
        summary.append(f"  ROI Difference: {impact['roi_difference']*100:+.2f}%")
        summary.append(f"  Sharpe Difference: {impact['sharpe_difference']:+.3f}")
        
        # Recommendation
        summary.append(f"\nRECOMMENDATION: {recommendations['primary_recommendation']}")
        summary.append(f"Confidence: {recommendations['confidence_level']}")
        summary.append(f"Explanation: {recommendations['explanation']}")
        
        return "\n".join(summary)


if __name__ == "__main__":
    # Test weekend parameter analyzer
    import pandas as pd
    
    # Create sample positions data for testing
    test_positions = pd.DataFrame({
        'open_timestamp': pd.date_range('2024-01-01', periods=20, freq='D'),
        'close_timestamp': pd.date_range('2024-01-02', periods=20, freq='D'),
        'pnl_sol': np.random.normal(0.1, 0.3, 20),
        'investment_sol': np.random.uniform(1, 3, 20)
    })
    
    analyzer = WeekendParameterAnalyzer()
    result = analyzer.analyze_weekend_parameter_impact(test_positions)
    
    if 'error' not in result:
        summary = analyzer.generate_weekend_analysis_summary(result)
        print(summary)
    else:
        print(f"Analysis failed: {result['error']}")