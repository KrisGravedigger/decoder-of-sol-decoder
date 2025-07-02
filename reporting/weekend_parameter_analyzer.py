"""
Weekend Parameter Analysis Module

Simulates the impact of weekendSizePercentage parameter on portfolio performance by:
- Identifying positions opened during weekends (Sat/Sun UTC)
- Simulating 5x larger positions (where parameter reduced size to 20%)
- Simulating 5x smaller positions (where parameter should have applied but didn't)
- Comparing performance metrics with and without the parameter
"""

import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class WeekendParameterAnalyzer:
    """
    Analyzes impact of weekendSizePercentage parameter on portfolio performance.
    
    Simulates position size adjustments to determine optimal parameter configuration
    by comparing actual results with hypothetical weekend size adjustments.
    """
    
    def __init__(self, weekend_size_percentage: float = 20.0):
        """
        Initialize weekend parameter analyzer.
        
        Args:
            weekend_size_percentage (float): Weekend size reduction percentage (default: 20%)
        """
        self.weekend_size_percentage = weekend_size_percentage
        self.size_multiplier = 100.0 / weekend_size_percentage  # 5x for 20%
        
        logger.info(f"Weekend Parameter Analyzer initialized (weekend size: {weekend_size_percentage}%)")
        
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
            
            # Step 2: Simulate parameter impact
            simulation_results = self._simulate_parameter_impact(positions_classified)
            
            # Step 3: Calculate performance metrics
            performance_comparison = self._calculate_performance_comparison(simulation_results)
            
            # Step 4: Generate recommendations
            recommendations = self._generate_recommendations(performance_comparison)
            
            # Compile complete analysis
            analysis_result = {
                'analysis_metadata': {
                    'generated_timestamp': datetime.now().isoformat(),
                    'weekend_size_percentage': self.weekend_size_percentage,
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
        
        # Convert to UTC if not already (assuming input is UTC)
        # weekday(): Monday=0, Sunday=6; Weekend: Saturday=5, Sunday=6
        positions_classified['open_weekday'] = positions_classified['open_timestamp'].dt.weekday
        positions_classified['weekend_opened'] = positions_classified['open_weekday'] >= 5
        
        # Additional classification for analysis
        positions_classified['open_day_name'] = positions_classified['open_timestamp'].dt.day_name()
        positions_classified['close_weekday'] = positions_classified['close_timestamp'].dt.weekday
        positions_classified['weekend_closed'] = positions_classified['close_weekday'] >= 5
        
        logger.info(f"Classified {len(positions_classified)} positions by weekend timing")
        return positions_classified
        
    def _simulate_parameter_impact(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Simulate the impact of weekendSizePercentage parameter on positions.
        
        Args:
            positions_df (pd.DataFrame): Classified positions data
            
        Returns:
            Dict[str, Any]: Simulation results
        """
        # AIDEV-NOTE-CLAUDE: Core business logic - simulate size adjustments based on weekend opening
        simulation_data = positions_df.copy()
        
        # Simulate position adjustments
        simulation_data['original_pnl_sol'] = simulation_data['pnl_sol']
        simulation_data['original_investment_sol'] = simulation_data['investment_sol']
        
        # Calculate simulated values based on weekend parameter logic
        simulation_data['simulated_pnl_sol'] = np.where(
            simulation_data['weekend_opened'],
            # Weekend positions: simulate 5x larger (parameter reduced to 20%)
            simulation_data['pnl_sol'] * self.size_multiplier,
            # Weekday positions: simulate 5x smaller (parameter would reduce)
            simulation_data['pnl_sol'] / self.size_multiplier
        )
        
        simulation_data['simulated_investment_sol'] = np.where(
            simulation_data['weekend_opened'],
            # Weekend positions: simulate 5x larger investment
            simulation_data['investment_sol'] * self.size_multiplier,
            # Weekday positions: simulate 5x smaller investment
            simulation_data['investment_sol'] / self.size_multiplier
        )
        
        # Calculate ROI for both scenarios
        simulation_data['original_roi'] = simulation_data['original_pnl_sol'] / simulation_data['original_investment_sol']
        simulation_data['simulated_roi'] = simulation_data['simulated_pnl_sol'] / simulation_data['simulated_investment_sol']
        
        # Aggregate results
        weekend_positions = simulation_data[simulation_data['weekend_opened']]
        weekday_positions = simulation_data[~simulation_data['weekend_opened']]
        
        return {
            'simulation_data': simulation_data,
            'weekend_analysis': {
                'count': len(weekend_positions),
                'original_total_pnl': weekend_positions['original_pnl_sol'].sum(),
                'simulated_total_pnl': weekend_positions['simulated_pnl_sol'].sum(),
                'original_total_investment': weekend_positions['original_investment_sol'].sum(),
                'simulated_total_investment': weekend_positions['simulated_investment_sol'].sum(),
                'original_avg_roi': weekend_positions['original_roi'].mean(),
                'simulated_avg_roi': weekend_positions['simulated_roi'].mean()
            },
            'weekday_analysis': {
                'count': len(weekday_positions),
                'original_total_pnl': weekday_positions['original_pnl_sol'].sum(),
                'simulated_total_pnl': weekday_positions['simulated_pnl_sol'].sum(),
                'original_total_investment': weekday_positions['original_investment_sol'].sum(),
                'simulated_total_investment': weekday_positions['simulated_investment_sol'].sum(),
                'original_avg_roi': weekday_positions['original_roi'].mean(),
                'simulated_avg_roi': weekday_positions['simulated_roi'].mean()
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
        
        # Overall portfolio metrics
        original_metrics = self._calculate_portfolio_metrics(
            simulation_data['original_pnl_sol'],
            simulation_data['original_investment_sol']
        )
        
        simulated_metrics = self._calculate_portfolio_metrics(
            simulation_data['simulated_pnl_sol'],
            simulation_data['simulated_investment_sol']
        )
        
        # Calculate impact
        total_pnl_impact = simulated_metrics['total_pnl'] - original_metrics['total_pnl']
        roi_impact = simulated_metrics['average_roi'] - original_metrics['average_roi']
        
        # Calculate percentage improvement
        pnl_improvement_percent = (total_pnl_impact / abs(original_metrics['total_pnl']) * 100 
                                  if original_metrics['total_pnl'] != 0 else 0)
        
        return {
            'original_scenario': {
                'name': 'Current (Without Weekend Parameter)',
                'metrics': original_metrics
            },
            'simulated_scenario': {
                'name': f'With Weekend Parameter ({self.weekend_size_percentage}%)',
                'metrics': simulated_metrics
            },
            'impact_analysis': {
                'total_pnl_difference_sol': total_pnl_impact,
                'roi_difference': roi_impact,
                'pnl_improvement_percent': pnl_improvement_percent,
                'recommendation': 'ENABLE' if total_pnl_impact > 0 else 'DISABLE'
            }
        }
        
    def _calculate_portfolio_metrics(self, pnl_series: pd.Series, investment_series: pd.Series) -> Dict[str, float]:
        """
        Calculate portfolio performance metrics.
        
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
            'win_rate': (pnl_series > 0).mean(),
            'average_profit': pnl_series[pnl_series > 0].mean() if (pnl_series > 0).any() else 0,
            'average_loss': pnl_series[pnl_series < 0].mean() if (pnl_series < 0).any() else 0,
            'profit_factor': (pnl_series[pnl_series > 0].sum() / abs(pnl_series[pnl_series < 0].sum()) 
                            if (pnl_series < 0).any() and pnl_series[pnl_series < 0].sum() != 0 else float('inf')),
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
        
        # Weekend vs weekday PnL
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
            'confidence_level': 'HIGH' if abs(impact['pnl_improvement_percent']) > 10 else 'MEDIUM' if abs(impact['pnl_improvement_percent']) > 5 else 'LOW',
            'expected_impact': {
                'pnl_change_sol': impact['total_pnl_difference_sol'],
                'pnl_change_percent': impact['pnl_improvement_percent'],
                'roi_change': impact['roi_difference']
            }
        }
        
        # Generate detailed explanation
        if impact['total_pnl_difference_sol'] > 0:
            recommendations['explanation'] = (
                f"Enabling weekendSizePercentage={self.weekend_size_percentage}% would improve "
                f"portfolio performance by {impact['total_pnl_difference_sol']:+.2f} SOL "
                f"({impact['pnl_improvement_percent']:+.1f}%). This suggests weekend positions "
                f"underperform and should be reduced in size."
            )
        else:
            recommendations['explanation'] = (
                f"Enabling weekendSizePercentage={self.weekend_size_percentage}% would reduce "
                f"portfolio performance by {abs(impact['total_pnl_difference_sol']):.2f} SOL "
                f"({abs(impact['pnl_improvement_percent']):.1f}%). This suggests weekend positions "
                f"actually perform well and should not be reduced."
            )
            
        # Risk considerations
        recommendations['risk_considerations'] = [
            "Analysis based on historical data - future market conditions may differ",
            f"Sample size: {performance_comparison['original_scenario']['metrics']['total_investment']:.1f} SOL total investment",
            "Weekend definition: Saturday-Sunday UTC timezone",
            f"Simulation assumes {self.size_multiplier:.1f}x size adjustments"
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
        
        # Position classification
        summary.append(f"Total Positions Analyzed: {meta['total_positions']}")
        summary.append(f"Weekend Opened: {classification['weekend_opened']['count']} ({classification['weekend_opened']['percentage']:.1f}%)")
        summary.append(f"Weekday Opened: {classification['weekday_opened']['count']} ({classification['weekday_opened']['percentage']:.1f}%)")
        
        # Current vs simulated performance
        original = comparison['original_scenario']['metrics']
        simulated = comparison['simulated_scenario']['metrics']
        
        summary.append(f"\nCURRENT PERFORMANCE (No Weekend Parameter):")
        summary.append(f"Total PnL: {original['total_pnl']:+.3f} SOL")
        summary.append(f"Average ROI: {original['average_roi']*100:+.2f}%")
        summary.append(f"Win Rate: {original['win_rate']*100:.1f}%")
        
        summary.append(f"\nSIMULATED PERFORMANCE (With Weekend Parameter {meta['weekend_size_percentage']}%):")
        summary.append(f"Total PnL: {simulated['total_pnl']:+.3f} SOL")
        summary.append(f"Average ROI: {simulated['average_roi']*100:+.2f}%")
        summary.append(f"Win Rate: {simulated['win_rate']*100:.1f}%")
        
        # Impact analysis
        impact = comparison['impact_analysis']
        summary.append(f"\nIMPACT ANALYSIS:")
        summary.append(f"PnL Difference: {impact['total_pnl_difference_sol']:+.3f} SOL ({impact['pnl_improvement_percent']:+.1f}%)")
        summary.append(f"ROI Difference: {impact['roi_difference']*100:+.2f}%")
        
        # Recommendation
        summary.append(f"\nRECOMMENDATION: {recommendations['primary_recommendation']} Weekend Parameter")
        summary.append(f"Confidence: {recommendations['confidence_level']}")
        summary.append(f"Explanation: {recommendations['explanation']}")
        
        return "\n".join(summary)


if __name__ == "__main__":
    # Test weekend parameter analyzer
    import pandas as pd
    
    # Create sample positions data for testing
    test_positions = pd.DataFrame({
        'open_timestamp': pd.date_range('2024-01-01', periods=50, freq='D'),
        'close_timestamp': pd.date_range('2024-01-02', periods=50, freq='D'),
        'pnl_sol': np.random.normal(0.1, 0.3, 50),
        'investment_sol': np.random.uniform(1, 3, 50)
    })
    
    analyzer = WeekendParameterAnalyzer(weekend_size_percentage=20.0)
    result = analyzer.analyze_weekend_parameter_impact(test_positions)
    
    if 'error' not in result:
        summary = analyzer.generate_weekend_analysis_summary(result)
        print(summary)
    else:
        print(f"Analysis failed: {result['error']}")
