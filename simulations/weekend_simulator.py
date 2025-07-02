"""
Weekend Simulator Module

Simulates the impact of weekendSizePercentage parameter on portfolio performance by:
- Creating two scenarios: current CSV data vs an alternative sizing for weekend positions.
- Only positions opened on weekends (Sat/Sun UTC) are affected.
- Weekday positions remain identical in both scenarios.
- Compares total PnL, ROI, and Sharpe ratio to provide a recommendation.

BUSINESS ASSUMPTION: The input CSV always represents actual, historical positions.
The `weekend_size_reduction` config setting dictates how to interpret this data and what alternative to simulate:
- `weekend_size_reduction=1`: CSV has reduced weekend positions. The simulation will ENLARGE them to normal size for comparison.
- `weekend_size_reduction=0`: CSV has normal-sized weekend positions. The simulation will REDUCE them for comparison.
"""

import logging
import pandas as pd
import numpy as np
import yaml
from datetime import datetime
from typing import Dict, List, Tuple, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('WeekendSimulator') # AIDEV-NOTE-CLAUDE: Renamed logger


class WeekendSimulator:
    """
    Simulates the impact of weekendSizePercentage parameter on portfolio performance.
    
    This class simulates an alternative weekend position sizing strategy to determine
    the optimal configuration by comparing current performance with a hypothetical one.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize the weekend simulator with YAML configuration.
        
        Args:
            config_path (str): Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.weekend_config = self.config.get('weekend_analysis', {})
        
        self.weekend_size_reduction = self.weekend_config.get('weekend_size_reduction', 1)
        self.size_reduction_percentage = self.weekend_config.get('size_reduction_percentage', 80)
        
        if self.size_reduction_percentage > 0 and self.size_reduction_percentage < 100:
            self.weekend_size_factor = (100 - self.size_reduction_percentage) / 100
            self.size_multiplier = 100 / (100 - self.size_reduction_percentage)
        else:
            self.weekend_size_factor = 1.0
            self.size_multiplier = 1.0
        
        logger.info(f"Weekend Simulator initialized")
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
            return {'weekend_analysis': {'weekend_size_reduction': 1, 'size_reduction_percentage': 80}}
            
    def run_simulation(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Perform complete weekend parameter impact simulation.
        
        Args:
            positions_df (pd.DataFrame): Portfolio positions data
            
        Returns:
            Dict[str, Any]: Complete weekend simulation results
        """
        logger.info("Starting weekend parameter impact simulation...")
        
        try:
            positions_classified = self._classify_weekend_positions(positions_df)
            simulation_results = self._simulate_alternative_scenario(positions_classified)
            performance_comparison = self._calculate_performance_comparison(simulation_results)
            recommendations = self._generate_recommendations(performance_comparison)
            
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
                'raw_data': {'positions_classified': positions_classified}
            }
            
            logger.info("Weekend parameter simulation completed successfully")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Weekend parameter simulation failed: {e}", exc_info=True)
            return {'error': str(e)}
            
    def _classify_weekend_positions(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """Classify positions based on weekend opening timing."""
        positions_classified = positions_df.copy()
        positions_classified['open_timestamp'] = pd.to_datetime(positions_classified['open_timestamp'])
        positions_classified['open_weekday'] = positions_classified['open_timestamp'].dt.weekday
        positions_classified['weekend_opened'] = positions_classified['open_weekday'] >= 5 # Saturday=5, Sunday=6
        positions_classified['open_day_name'] = positions_classified['open_timestamp'].dt.day_name()
        
        logger.info(f"Classified {len(positions_classified)} positions: {positions_classified['weekend_opened'].sum()} opened on weekends, {(~positions_classified['weekend_opened']).sum()} on weekdays.")
        return positions_classified
        
    def _simulate_alternative_scenario(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """Simulate alternative scenario based on weekend_size_reduction setting."""
        simulation_data = positions_df.copy()
        
        simulation_data['current_pnl_sol'] = simulation_data['pnl_sol']
        simulation_data['current_investment_sol'] = simulation_data['investment_sol']
        
        if self.weekend_size_reduction == 1:
            scenario_name_current = f"ENABLED ({self.size_reduction_percentage}% weekend reduction)"
            scenario_name_alternative = "DISABLED (normal weekend sizes)"
            pnl_multiplier = self.size_multiplier
            investment_multiplier = self.size_multiplier
        else:
            scenario_name_current = "DISABLED (normal weekend sizes)"
            scenario_name_alternative = f"ENABLED ({self.size_reduction_percentage}% weekend reduction)"
            pnl_multiplier = self.weekend_size_factor
            investment_multiplier = self.weekend_size_factor

        simulation_data['alternative_pnl_sol'] = np.where(
            simulation_data['weekend_opened'],
            simulation_data['pnl_sol'] * pnl_multiplier,
            simulation_data['pnl_sol']
        )
        simulation_data['alternative_investment_sol'] = np.where(
            simulation_data['weekend_opened'],
            simulation_data['investment_sol'] * investment_multiplier,
            simulation_data['investment_sol']
        )
        
        simulation_data['current_roi'] = (simulation_data['current_pnl_sol'] / simulation_data['current_investment_sol']).fillna(0)
        simulation_data['alternative_roi'] = (simulation_data['alternative_pnl_sol'] / simulation_data['alternative_investment_sol']).fillna(0)
        
        return {
            'simulation_data': simulation_data,
            'scenario_names': {
                'current': scenario_name_current,
                'alternative': scenario_name_alternative
            }
        }
        
    def _calculate_performance_comparison(self, simulation_results: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate performance comparison between scenarios."""
        simulation_data = simulation_results['simulation_data']
        scenario_names = simulation_results['scenario_names']
        
        current_metrics = self._calculate_portfolio_metrics(simulation_data['current_pnl_sol'], simulation_data['current_investment_sol'])
        alternative_metrics = self._calculate_portfolio_metrics(simulation_data['alternative_pnl_sol'], simulation_data['alternative_investment_sol'])
        
        total_pnl_impact = alternative_metrics['total_pnl'] - current_metrics['total_pnl']
        pnl_improvement_percent = (total_pnl_impact / abs(current_metrics['total_pnl']) * 100) if current_metrics['total_pnl'] != 0 else 0
        
        if self.weekend_size_reduction == 1:
            recommendation = 'DISABLE' if total_pnl_impact > 0 else 'KEEP_ENABLED'
        else:
            recommendation = 'ENABLE' if total_pnl_impact > 0 else 'KEEP_DISABLED'
        
        return {
            'current_scenario': {'name': scenario_names['current'], 'metrics': current_metrics},
            'alternative_scenario': {'name': scenario_names['alternative'], 'metrics': alternative_metrics},
            'impact_analysis': {
                'total_pnl_difference_sol': total_pnl_impact,
                'roi_difference': alternative_metrics['average_roi'] - current_metrics['average_roi'],
                'sharpe_difference': alternative_metrics['sharpe_ratio'] - current_metrics['sharpe_ratio'],
                'pnl_improvement_percent': pnl_improvement_percent,
                'recommendation': recommendation
            }
        }
        
    def _calculate_portfolio_metrics(self, pnl_series: pd.Series, investment_series: pd.Series) -> Dict[str, float]:
        """Calculate key portfolio performance metrics."""
        roi_series = (pnl_series / investment_series).replace([np.inf, -np.inf], 0).fillna(0)
        return {
            'total_pnl': pnl_series.sum(),
            'average_roi': roi_series.mean(),
            'sharpe_ratio': roi_series.mean() / roi_series.std() if roi_series.std() > 0 else 0
        }
        
    def _get_classification_summary(self, positions_df: pd.DataFrame) -> Dict[str, Any]:
        """Generate summary of position classification."""
        weekend_df = positions_df[positions_df['weekend_opened']]
        weekday_df = positions_df[~positions_df['weekend_opened']]
        return {
            'total_positions': len(positions_df),
            'weekend_opened': {
                'count': len(weekend_df),
                'percentage': len(weekend_df) / len(positions_df) * 100 if len(positions_df) > 0 else 0,
                'total_pnl': weekend_df['pnl_sol'].sum()
            },
            'weekday_opened': {
                'count': len(weekday_df),
                'percentage': len(weekday_df) / len(positions_df) * 100 if len(positions_df) > 0 else 0,
                'total_pnl': weekday_df['pnl_sol'].sum()
            },
            'day_distribution': positions_df['open_day_name'].value_counts().to_dict()
        }
        
    def _generate_recommendations(self, performance_comparison: Dict[str, Any]) -> Dict[str, Any]:
        """Generate actionable recommendations based on analysis."""
        impact = performance_comparison['impact_analysis']
        recommendation = {
            'primary_recommendation': impact['recommendation'],
            'confidence_level': 'HIGH' if abs(impact['pnl_improvement_percent']) > 10 else 'MEDIUM' if abs(impact['pnl_improvement_percent']) > 5 else 'LOW',
            'expected_impact': {
                'pnl_change_sol': impact['total_pnl_difference_sol'],
                'pnl_change_percent': impact['pnl_improvement_percent'],
            }
        }
        current_name = performance_comparison['current_scenario']['name']
        alternative_name = performance_comparison['alternative_scenario']['name']
        if impact['total_pnl_difference_sol'] > 0:
            recommendation['explanation'] = f"Switching to '{alternative_name}' would improve PnL by {impact['total_pnl_difference_sol']:+.3f} SOL ({impact['pnl_improvement_percent']:+.1f}%)."
        else:
            recommendation['explanation'] = f"The current configuration '{current_name}' performs better. Switching would decrease PnL by {abs(impact['total_pnl_difference_sol']):.3f} SOL."
        return recommendation
        
    def generate_summary_text(self, analysis_result: Dict[str, Any]) -> str:
        """Generate human-readable summary of the simulation."""
        if 'error' in analysis_result:
            return f"Weekend Simulation Error: {analysis_result['error']}"
        
        rec = analysis_result['recommendations']
        summary = [
            "WEEKEND SIMULATION SUMMARY",
            "=" * 50,
            f"RECOMMENDATION: {rec['primary_recommendation']} (Confidence: {rec['confidence_level']})",
            f"Explanation: {rec['explanation']}"
        ]
        return "\n".join(summary)


if __name__ == "__main__":
    # Test weekend simulator
    test_positions = pd.DataFrame({
        'open_timestamp': pd.to_datetime(['2024-01-05', '2024-01-06', '2024-01-07', '2024-01-08']), # Fri, Sat, Sun, Mon
        'close_timestamp': pd.to_datetime(['2024-01-06', '2024-01-07', '2024-01-08', '2024-01-09']),
        'pnl_sol': [0.5, -0.2, 0.3, 0.4],
        'investment_sol': [10, 2, 2, 10] # Reduced investment for weekend
    })
    
    # Simulate with weekend_size_reduction=1 (current state is reduced positions)
    simulator = WeekendSimulator()
    result = simulator.run_simulation(test_positions)
    
    if 'error' not in result:
        summary = simulator.generate_summary_text(result)
        print(summary)
    else:
        print(f"Analysis failed: {result['error']}")