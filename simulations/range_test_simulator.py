"""
TP/SL Range Test Simulator for Phase 4A

Simulates a grid of TP/SL combinations to find optimal parameters per strategy.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple
from datetime import datetime
from tqdm import tqdm

from reporting.post_close_analyzer import PostCloseAnalyzer
from reporting.data_loader import load_and_prepare_positions

logger = logging.getLogger(__name__)


class TpSlRangeSimulator:
    """
    Simulates various TP/SL combinations to find optimal parameters.
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize range test simulator.
        
        Args:
            config: Main configuration dictionary
        """
        self.config = config
        self.range_config = config.get('range_testing', {})
        self.tp_levels = self.range_config.get('tp_levels', [2, 4, 6, 8, 10])
        self.sl_levels = self.range_config.get('sl_levels', [3, 5, 7, 10, 15])
        self.post_close_analyzer = PostCloseAnalyzer(config_path="reporting/config/portfolio_config.yaml")
        
    def run_simulation(self, positions_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
        """
        Run range testing simulation for all positions.
        
        Args:
            positions_df: Enriched positions DataFrame with strategy_instance_id
            
        Returns:
            Dictionary with 'detailed_results' and 'aggregated_results' DataFrames
        """
        if 'strategy_instance_id' not in positions_df.columns:
            raise ValueError("positions_df must contain strategy_instance_id column. Run strategy detection first.")
            
        detailed_results = []
        total_simulations = len(positions_df) * len(self.tp_levels) * len(self.sl_levels)
        
        logger.info(f"Starting range simulation: {len(positions_df)} positions × {len(self.tp_levels)} TP × {len(self.sl_levels)} SL = {total_simulations} simulations")
        
        # Process each position
        with tqdm(total=len(positions_df), desc="Processing positions") as pbar:
            for idx, row in positions_df.iterrows():
                position = self._row_to_position(row)
                
                # Get post-close timeline once (expensive operation)
                timeline = self._get_position_timeline(position)
                
                if not timeline:
                    logger.warning(f"No timeline data for position {position.position_id}")
                    pbar.update(1)
                    continue
                    
                # Test all TP/SL combinations
                for tp_level in self.tp_levels:
                    for sl_level in self.sl_levels:
                        result = self._simulate_single_combination(
                            position, timeline, tp_level, sl_level, row['strategy_instance_id']
                        )
                        detailed_results.append(result)
                        
                pbar.update(1)
                
        # Convert to DataFrame
        detailed_df = pd.DataFrame(detailed_results)
        
        # Aggregate results by strategy instance
        aggregated_df = self._aggregate_results(detailed_df)
        
        return {
            'detailed_results': detailed_df,
            'aggregated_results': aggregated_df
        }
        
    def _get_position_timeline(self, position: Any) -> List[Dict]:
        """
        Get post-close timeline for a position using PostCloseAnalyzer.
        
        Args:
            position: Position object
            
        Returns:
            Timeline list or empty list if unavailable
        """
        try:
            # Use PostCloseAnalyzer's internal methods
            end_datetime, extension_hours = self.post_close_analyzer._calculate_post_close_period(position)
            
            # Fetch post-close data
            post_close_data = self.post_close_analyzer.cache_manager.fetch_post_close_data(
                position, extension_hours
            )
            
            if not post_close_data:
                return []
                
            # Get position volume data for fee simulation
            position_volume_data = self.post_close_analyzer.cache_manager.fetch_ochlv_data(
                position.pool_address,
                position.open_timestamp,
                position.close_timestamp,
                use_cache_only=True
            )
            
            # Simulate fees
            allocated_fees = self.post_close_analyzer.fee_simulator.calculate_fee_allocation(
                position, position_volume_data, post_close_data
            )
            
            # Initialize LP valuator
            strategy_parts = position.actual_strategy.split()
            strategy_type = "Bid-Ask" if "Bid-Ask" in position.actual_strategy else "Spot"
            step_size = "MEDIUM"
            for part in strategy_parts:
                if part.upper() in ["WIDE", "MEDIUM", "NARROW", "SIXTYNINE"]:
                    step_size = part.upper()
                    break
                    
            from reporting.lp_position_valuator import LPPositionValuator
            lp_valuator = LPPositionValuator(strategy_type, step_size)
            
            # Get timeline
            timeline = lp_valuator.simulate_position_timeline(position, post_close_data, allocated_fees)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get timeline for position {position.position_id}: {e}")
            return []

    def _find_exit_in_timeline(self, position: Any, timeline: List[Dict], tp_level: float, sl_level: float) -> Dict[str, Any]:
        """
        Finds the simulated exit point and calculates the resulting PnL.

        This helper method contains the core simulation logic for a single TP/SL combination.

        Args:
            position: The position object (for initial_investment and timestamps).
            timeline: The position's value timeline, generated by LPPositionValuator.
            tp_level (float): Take profit level in percentage.
            sl_level (float): Stop loss level in percentage (positive value).

        Returns:
            A dictionary containing all key simulation results for the combination.
        """
        exit_point = None
        exit_reason = 'END'  # Default reason: position runs to the end of the simulation period

        for point in timeline:
            pnl_pct = point.get('pnl_pct', 0.0)

            # Check for Take Profit trigger
            if pnl_pct >= tp_level:
                exit_point = point
                exit_reason = 'TP'
                break

            # Check for Stop Loss trigger (sl_level is positive, so we check for negative PnL)
            if pnl_pct <= -sl_level:
                exit_point = point
                exit_reason = 'SL'
                break

        # If no TP/SL was hit, the position closes at the end of the simulation period
        if exit_point is None and timeline:
            exit_point = timeline[-1]

        # Handle cases with no valid timeline data to prevent crashes
        if not exit_point:
            return {
                'simulated_pnl': 0.0,
                'simulated_pnl_pct': 0.0,
                'exit_reason': 'NO_DATA',
                'days_to_exit': 0.0,
            }

        # AIDEV-FIX-CLAUDE: Corrected the KeyError by using 'position_value_sol'.
        simulated_pnl = exit_point['position_value_sol'] - position.initial_investment
        days_to_exit = (exit_point['timestamp'] - position.open_timestamp).total_seconds() / 86400

        return {
            'simulated_pnl': simulated_pnl,
            'simulated_pnl_pct': exit_point['pnl_pct'],
            'exit_reason': exit_reason,
            'days_to_exit': days_to_exit,
        }

    def _simulate_single_combination(self, position: Any, timeline: List[Dict], 
                                   tp_level: float, sl_level: float, 
                                   strategy_instance_id: str) -> Dict[str, Any]:
        """
        Orchestrates the simulation for a single TP/SL combination for a given position.
        
        This method calls a helper to perform the core calculation and then formats
        the final dictionary for aggregation.

        Args:
            position: Position object
            timeline: Value timeline
            tp_level: Take profit percentage
            sl_level: Stop loss percentage (positive value)
            strategy_instance_id: Strategy instance identifier
            
        Returns:
            A complete simulation result dictionary for one combination.
        """
        # Find the exit point and calculate results using the new helper method
        sim_results = self._find_exit_in_timeline(position, timeline, tp_level, sl_level)
        
        # Combine simulation results with position and parameter identifiers
        return {
            'position_id': position.position_id,
            'strategy_instance_id': strategy_instance_id,
            'tp_level': tp_level,
            'sl_level': sl_level,
            'actual_pnl': position.final_pnl,
            'improvement': sim_results['simulated_pnl'] - (position.final_pnl or 0),
            **sim_results  # Unpack results like 'simulated_pnl', 'exit_reason', etc.
        }
        
    def _aggregate_results(self, detailed_df: pd.DataFrame) -> pd.DataFrame:
        """
        Aggregate detailed results by strategy instance and TP/SL combination.
        
        Args:
            detailed_df: Detailed simulation results
            
        Returns:
            Aggregated results DataFrame
        """
        # Group by strategy instance and TP/SL levels
        grouped = detailed_df.groupby(['strategy_instance_id', 'tp_level', 'sl_level'])
        
        aggregated = grouped.agg({
            'simulated_pnl': ['sum', 'mean', 'count'],
            'simulated_pnl_pct': 'mean',
            'improvement': 'sum',
            'exit_reason': lambda x: x.value_counts().to_dict(),
            'days_to_exit': 'mean'
        }).round(3)
        
        # Flatten column names
        aggregated.columns = ['_'.join(col).strip() for col in aggregated.columns]
        aggregated = aggregated.rename(columns={
            'simulated_pnl_sum': 'total_pnl',
            'simulated_pnl_mean': 'avg_pnl',
            'simulated_pnl_count': 'position_count',
            'simulated_pnl_pct_mean': 'avg_pnl_pct',
            'improvement_sum': 'total_improvement',
            'exit_reason_<lambda>': 'exit_reasons',
            'days_to_exit_mean': 'avg_days_to_exit'
        })
        
        # Calculate win rate
        def calculate_win_rate(exit_reasons):
            total = sum(exit_reasons.values())
            tp_count = exit_reasons.get('TP', 0)
            return (tp_count / total * 100) if total > 0 else 0
            
        aggregated['win_rate'] = aggregated['exit_reasons'].apply(calculate_win_rate)
        
        # Reset index
        aggregated = aggregated.reset_index()
        
        return aggregated
        
    def _row_to_position(self, row: pd.Series) -> Any:
        """
        Convert DataFrame row to position-like object.
        
        Args:
            row: DataFrame row
            
        Returns:
            Position-like object
        """
        class SimplePosition:
            pass
            
        position = SimplePosition()
        
        # Map columns
        position.position_id = row['position_id']
        position.pool_address = row['pool_address']
        position.open_timestamp = row['open_timestamp']
        position.close_timestamp = row['close_timestamp']
        position.initial_investment = row['investment_sol']
        position.final_pnl = row['pnl_sol']
        position.close_reason = row['close_reason']
        position.actual_strategy = row['strategy_raw']
        position.total_fees_collected = row.get('total_fees_collected', 0.0)
        
        return position