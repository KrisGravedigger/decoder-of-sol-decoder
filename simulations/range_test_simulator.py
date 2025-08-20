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
        Finds the simulated exit point and calculates the resulting PnL,
        correctly handling a dynamic OOR (Out of Range) timeout and price threshold.
        """
        if not timeline:
            return {'simulated_pnl': 0.0, 'simulated_pnl_pct': 0.0, 'exit_reason': 'NO_DATA', 'days_to_exit': 0.0}

        # Use dynamic parameters from the position object, with sensible defaults if they are missing.
        oor_timeout_minutes = position.oor_timeout_minutes if pd.notna(position.oor_timeout_minutes) else 30.0
        oor_threshold_pct = position.oor_threshold_pct if pd.notna(position.oor_threshold_pct) else 2.0
        
        # Calculate the actual max price threshold for OOR, including the percentage buffer
        max_price_threshold = None
        if position.max_bin_price is not None and pd.notna(position.max_bin_price):
            max_price_threshold = position.max_bin_price * (1 + oor_threshold_pct / 100)

        oor_start_timestamp = None
        exit_point = None
        exit_reason = 'END' # Default reason if no other condition is met

        for i, point in enumerate(timeline):
            pnl_pct = point.get('pnl_pct', 0.0)
            current_price = point.get('price', 0.0)
            current_timestamp = point.get('timestamp')

            # --- OOR LOGIC WITH DYNAMIC TIMEOUT & THRESHOLD ---
            is_out_of_range = (max_price_threshold is not None and current_price > max_price_threshold)

            if is_out_of_range:
                if oor_start_timestamp is None:
                    # First time price is out of range, start the timer
                    oor_start_timestamp = current_timestamp
                
                # Check if the timeout has elapsed since the timer started
                time_in_oor = (current_timestamp - oor_start_timestamp).total_seconds() / 60
                if time_in_oor >= oor_timeout_minutes:
                    exit_reason = 'OOR'
                    exit_point = point
                    break # Exit the loop, OOR is confirmed
            else:
                # Price is back in range, so reset the OOR timer
                oor_start_timestamp = None

            # --- TP/SL LOGIC (RUNS EVERY CANDLE, CAN OVERRIDE OOR TIMEOUT) ---
            if pnl_pct >= tp_level:
                exit_reason = 'TP'
                exit_point = point
                break

            if pnl_pct <= -sl_level:
                exit_reason = 'SL'
                exit_point = point
                break
        
        if exit_point is None: # This runs if the loop completed without a 'break'
            exit_reason = 'END'
            exit_point = timeline[-1]

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
        Orchestrates the simulation for a single TP/SL combination.
        
        AIDEV-TPSL-CLAUDE: Skip pointless simulations based on actual close reason.
        """
        # Optimization based on your discoveries:
        actual_close_reason = getattr(position, 'close_reason', 'other')
        actual_tp = getattr(position, 'take_profit', 0)
        actual_sl = getattr(position, 'stop_loss', 0)
        
        # Skip pointless simulations for OOR positions
        if actual_close_reason == 'OOR':
            # Discovery 2: No point testing higher TP - will always get same OOR
            if tp_level > actual_tp:
                # Use actual position result - OOR won't change
                return {
                    'position_id': position.position_id,
                    'strategy_instance_id': strategy_instance_id,
                    'tp_level': tp_level,
                    'sl_level': sl_level,
                    'actual_pnl': position.final_pnl,
                    'improvement': 0,  # No improvement possible
                    'simulated_pnl': position.final_pnl,
                    'simulated_pnl_pct': (position.final_pnl / position.initial_investment * 100) if position.initial_investment > 0 else 0,
                    'exit_reason': 'OOR',  # Will always be OOR
                    'days_to_exit': (position.close_timestamp - position.open_timestamp).total_seconds() / 86400,
                }
            
            # Discovery 3: No point testing deeper SL - won't trigger if shallower didn't
            if sl_level > actual_sl:
                # Use actual position result
                return {
                    'position_id': position.position_id,
                    'strategy_instance_id': strategy_instance_id,
                    'tp_level': tp_level,
                    'sl_level': sl_level,
                    'actual_pnl': position.final_pnl,
                    'improvement': 0,
                    'simulated_pnl': position.final_pnl,
                    'simulated_pnl_pct': (position.final_pnl / position.initial_investment * 100) if position.initial_investment > 0 else 0,
                    'exit_reason': 'OOR',
                    'days_to_exit': (position.close_timestamp - position.open_timestamp).total_seconds() / 86400,
                }
        
        # For TP positions: skip testing lower TP (would have triggered earlier)
        if actual_close_reason == 'TP' and tp_level < actual_tp:
            # Would have exited even earlier with same result
            return {
                'position_id': position.position_id,
                'strategy_instance_id': strategy_instance_id,
                'tp_level': tp_level,
                'sl_level': sl_level,
                'actual_pnl': position.final_pnl,
                'improvement': 0,
                'simulated_pnl': position.final_pnl,
                'simulated_pnl_pct': (position.final_pnl / position.initial_investment * 100) if position.initial_investment > 0 else 0,
                'exit_reason': 'TP',
                'days_to_exit': (position.close_timestamp - position.open_timestamp).total_seconds() / 86400,
            }
        
        # Otherwise, run normal simulation
        sim_results = self._find_exit_in_timeline(position, timeline, tp_level, sl_level)
        
        return {
            'position_id': position.position_id,
            'strategy_instance_id': strategy_instance_id,
            'tp_level': tp_level,
            'sl_level': sl_level,
            'actual_pnl': position.final_pnl,
            'improvement': sim_results['simulated_pnl'] - (position.final_pnl or 0),
            **sim_results
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
        
        # Calculate complex win rate metrics
        def calculate_rates(exit_reasons):
            total = sum(exit_reasons.values())
            if total == 0:
                return pd.Series([0, 0], index=['win_rate', 'tp_rate'])
            
            tp_count = exit_reasons.get('TP', 0)
            oor_count = exit_reasons.get('OOR', 0)
            
            win_rate = (tp_count + oor_count) / total * 100
            tp_rate = tp_count / total * 100
            
            return pd.Series([win_rate, tp_rate], index=['win_rate', 'tp_rate'])
            
        rates_df = aggregated['exit_reasons'].apply(calculate_rates)
        aggregated = pd.concat([aggregated, rates_df], axis=1)
        
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
        position.min_bin_price = row.get('min_bin_price')
        position.max_bin_price = row.get('max_bin_price')
        
        # AIDEV-NOTE-GEMINI: Read dynamic OOR parameters from the DataFrame row
        position.oor_timeout_minutes = row.get('oor_timeout_minutes')
        position.oor_threshold_pct = row.get('oor_threshold_pct')
        
        return position