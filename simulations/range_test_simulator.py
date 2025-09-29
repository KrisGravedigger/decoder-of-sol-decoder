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
import json  # AIDEV-DEBUG

from reporting.post_close_analyzer import PostCloseAnalyzer
from reporting.data_loader import load_and_prepare_positions
from core.models import Position  # ZMIANA: Import oficjalnego modelu

logger = logging.getLogger(__name__)

# AIDEV-INTEGRATE-CLAUDE: Import UnifiedBaselineManager for Phase 2 integration
from simulations.unified_baseline_manager import UnifiedBaselineManager


class TpSlRangeSimulator:
    """
    Simulates various TP/SL combinations to find optimal parameters.
    """
    
    def __init__(self, config: Dict[str, Any], post_close_analyzer: PostCloseAnalyzer):
        """
        Initialize range test simulator.
        
        Args:
            config: Main configuration dictionary
            post_close_analyzer: A pre-configured instance of PostCloseAnalyzer
        """
        self.config = config
        self.range_config = config.get('range_testing', {})
        self.tp_levels = self.range_config.get('tp_levels', [2, 4, 6, 8, 10])
        self.sl_levels = self.range_config.get('sl_levels', [3, 5, 7, 10, 15])
        self.post_close_analyzer = post_close_analyzer
        
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
        # AIDEV-TODO-CLAUDE: Diagnostic logging for strategy instance counts
        strategy_counts = positions_df['strategy_instance_id'].value_counts()
        logger.info(f"Input strategy counts for TP/SL analysis:")
        for strategy_id, count in strategy_counts.head(10).items():
            logger.info(f"  {strategy_id}: {count} positions")


        # Process each position
        with tqdm(total=len(positions_df), desc="Processing positions") as pbar:
            for idx, row in positions_df.iterrows():
                position = self._row_to_position(row)
                
                # Get post-close timeline once (expensive operation)
                timeline = self._get_position_timeline(position)
                
                if not timeline:
                    logger.error(f"DIAGNOSTIC: Position {position.position_id} EXCLUDED from strategy {row['strategy_instance_id']}")
                    logger.error(f"  - This reduces strategy position count in TP/SL analysis")
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
        
        # AIDEV-INTEGRATE-CLAUDE: Export to unified baseline system if enabled
        self.export_to_baseline_manager(aggregated_df)
        
        return {
            'detailed_results': detailed_df,
            'aggregated_results': aggregated_df
        }
        
    def _get_position_timeline(self, position: Position) -> List[Dict]:
        """
        Get a COMPLETE historical timeline for a position, combining the actual
        in-position period with the post-close simulation period.
        """
        try:
            # --- 1. Fetch data for the actual "in-position" period (from cache) ---
            timeframe_in_pos = self.post_close_analyzer.cache_manager._determine_timeframe_from_duration(
                position.open_timestamp, position.close_timestamp
            )
            in_position_data = self.post_close_analyzer.cache_manager.get_price_data(
                pool_address=position.pool_address,
                start_dt=position.open_timestamp,
                end_dt=position.close_timestamp,
                timeframe=timeframe_in_pos,
                use_cache_only=True
            )

            # --- 2. Fetch data for the "post-close" simulation period ---
            end_dt, _ = self.post_close_analyzer._calculate_post_close_period(position)
            timeframe_post_close = self.post_close_analyzer.cache_manager._determine_timeframe_from_duration(
                position.close_timestamp, end_dt
            )
            post_close_data = self.post_close_analyzer.cache_manager.get_price_data(
                pool_address=position.pool_address,
                start_dt=position.close_timestamp,
                end_dt=end_dt,
                timeframe=timeframe_post_close,
                use_cache_only=True
            )

            combined_price_data = in_position_data + post_close_data
            if not combined_price_data:
                logger.error(f"DIAGNOSTIC: Position {position.position_id} excluded from TP/SL analysis - No price data available")
                logger.error(f"  - Strategy: {position.actual_strategy}")
                logger.error(f"  - Pool: {position.pool_address}")
                logger.error(f"  - Open: {position.open_timestamp}, Close: {position.close_timestamp}")
                return []
            
            unique_points = {p['timestamp']: p for p in combined_price_data}
            sorted_price_data = sorted(unique_points.values(), key=lambda x: x['timestamp'])

            # --- 3. Simulate fees for the ENTIRE combined period ---
            position_volume_data = in_position_data
            
            allocated_fees = self.post_close_analyzer.fee_simulator.calculate_fee_allocation(
                position, position_volume_data, sorted_price_data
            )
            
            # --- 4. Initialize LP valuator and generate the final timeline ---
            strategy_parts = position.actual_strategy.split()
            strategy_type = "Bid-Ask" if "Bid-Ask" in position.actual_strategy else "Spot"
            step_size = "MEDIUM"
            for part in strategy_parts:
                if part.upper() in ["WIDE", "MEDIUM", "NARROW", "SIXTYNINE"]:
                    step_size = part.upper()
                    break
                    
            from reporting.lp_position_valuator import LPPositionValuator
            lp_valuator = LPPositionValuator(strategy_type, step_size)
            
            timeline = lp_valuator.simulate_position_timeline(position, sorted_price_data, allocated_fees)
            
            return timeline
            
        except Exception as e:
            logger.error(f"Failed to get complete timeline for position {position.position_id}: {e}", exc_info=True)
            return []

    def _find_exit_in_timeline(self, position: Position, timeline: List[Dict], tp_level: float, sl_level: float) -> Dict[str, Any]:
        """
        Finds the simulated exit point using realistic intra-candle (high/low) logic.
        - TP triggers if candle's high reaches the level, closing at exactly tp_level.
        - SL triggers if candle's low reaches the level, closing at exactly -sl_level.
        - OOR is checked based on the candle's close price.
        """
        if not timeline:
            return {'simulated_pnl': 0.0, 'simulated_pnl_pct': 0.0, 'exit_reason': 'NO_DATA', 'days_to_exit': 0.0}

        oor_timeout_minutes = position.oor_timeout_minutes if pd.notna(position.oor_timeout_minutes) else 30.0
        min_price = getattr(position, 'min_bin_price', None)
        max_price = getattr(position, 'max_bin_price', None)

        oor_start_timestamp = None
        exit_point = None
        exit_reason = 'END'
        final_pnl_pct = 0.0
                
        for i, point in enumerate(timeline):
            pnl_pct_high = point.get('pnl_pct_high', point['pnl_pct'])
            pnl_pct_low = point.get('pnl_pct_low', point['pnl_pct'])
            pnl_pct_close = point['pnl_pct']
            
            current_price = point['price'] # This is the close price
            current_timestamp = point['timestamp']
            
            # --- REALISTIC TP/SL TRIGGER LOGIC (INTRA-CANDLE) ---
            # Standard backtesting practice: check high for TP first, then low for SL.
            if pnl_pct_high >= tp_level:
                exit_reason = 'TP'
                final_pnl_pct = tp_level # Exit at the exact TP level
                exit_point = point
                break

            if pnl_pct_low <= -sl_level:
                exit_reason = 'SL'
                final_pnl_pct = -sl_level # Exit at the exact SL level
                exit_point = point
                break

            # --- OOR LOGIC (based on close price) ---
            is_out_of_range = (min_price is not None and current_price < min_price) or \
                              (max_price is not None and current_price > max_price)

            if is_out_of_range:
                if oor_start_timestamp is None:
                    oor_start_timestamp = current_timestamp
                
                time_in_oor = (current_timestamp - oor_start_timestamp).total_seconds() / 60
                if time_in_oor >= oor_timeout_minutes:
                    exit_reason = 'OOR'
                    final_pnl_pct = pnl_pct_close
                    exit_point = point
                    break
            else:
                oor_start_timestamp = None
        
        # If no exit condition was met, position runs to the end of the timeline
        if exit_point is None:
            exit_reason = 'END'
            exit_point = timeline[-1]
            final_pnl_pct = exit_point['pnl_pct']

        # Calculate final PnL in SOL based on the determined PnL percentage
        simulated_pnl = position.initial_investment * (final_pnl_pct / 100.0)
        days_to_exit = (exit_point['timestamp'] - position.open_timestamp).total_seconds() / 86400

        return {
            'simulated_pnl': simulated_pnl,
            'simulated_pnl_pct': final_pnl_pct,
            'exit_reason': exit_reason,
            'days_to_exit': days_to_exit,
        }

    def _simulate_single_combination(self, position: Position, timeline: List[Dict], 
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
        
        # AIDEV-INTEGRATE-CLAUDE: Added 'max' aggregation for baseline tracking
        aggregated = grouped.agg({
            'simulated_pnl': ['sum', 'mean', 'count', 'max'],  # Added 'max' for best position
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
            'simulated_pnl_max': 'best_position_pnl',  # AIDEV-INTEGRATE-CLAUDE: Track best position
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

    def export_to_baseline_manager(self, aggregated_df: pd.DataFrame) -> None:
        """
        Export aggregated results to UnifiedBaselineManager.
        
        AIDEV-INTEGRATE-CLAUDE: Phase 2 integration point
        Sends range test results to unified baseline system
        
        Args:
            aggregated_df: Aggregated results DataFrame
        """
        try:
            # Check if unified baseline is enabled
            if not self.config.get('unified_baseline', {}).get('enabled', False):
                logger.debug("UnifiedBaselineManager not enabled, skipping export")
                return
                
            manager = UnifiedBaselineManager(self.config)
            
            # Register results for each strategy
            for strategy_id in aggregated_df['strategy_instance_id'].unique():
                strategy_data = aggregated_df[aggregated_df['strategy_instance_id'] == strategy_id]
                
                # Calculate and cache baseline
                baseline = manager.calculate_strategy_baseline(
                    strategy_id,
                    strategy_data,
                    metric='total_pnl'  # Use total_pnl as primary metric
                )
                
                logger.debug(f"Exported baseline for {strategy_id}: {baseline.baseline_sol:.4f} SOL")
                
            logger.info(f"Exported {len(aggregated_df['strategy_instance_id'].unique())} strategies to UnifiedBaselineManager")
            
        except Exception as e:
            logger.warning(f"Could not export to UnifiedBaselineManager: {e}")

    def _row_to_position(self, row: pd.Series) -> Position:
        """
        Convert DataFrame row to a Position object for simulation.
        
        Args:
            row: DataFrame row containing position data.
            
        Returns:
            A populated Position object.
        """
        # CHANGE: Removed SimplePosition class and now using the official Position model.
        # We correctly initialize the object using its constructor.
        # CRITICAL FIX: The Position constructor expects a string in MM/DD-HH:MM:SS format.
        # We convert the Timestamp back to this format ONLY for initialization purposes.
        position = Position(
            open_timestamp=row['open_timestamp'].strftime('%m/%d-%H:%M:%S'),
            bot_version=row.get('bot_version', 'unknown'),
            open_line_index=int(row.get('open_line_index', -1)), # Ensure it's an integer
            wallet_id=row.get('wallet_id', 'unknown_wallet'),
            source_file=row.get('source_file', 'unknown_file')
        )
        
        # CHANGE: Mapping attributes from the DataFrame row to the Position object.
        position.position_id = row['position_id']
        position.pool_address = row['pool_address']
        
        # AIDEV-TPSL-CLAUDE: CRITICAL FIX - Ensure timestamps are datetime objects for simulation.
        # The Position model may store them as strings, but the simulation engine requires datetime.
        position.open_timestamp = pd.to_datetime(row['open_timestamp'])
        position.close_timestamp = pd.to_datetime(row['close_timestamp'])
        
        position.initial_investment = row['investment_sol']
        position.final_pnl = row['pnl_sol']
        position.close_reason = row['close_reason']
        position.actual_strategy = row['strategy_raw']
        
        # Populate TP/SL and other relevant fields for simulation
        position.take_profit = row.get('takeProfit')
        position.stop_loss = row.get('stopLoss')
        position.total_fees_collected = row.get('total_fees_collected', 0.0)
        position.min_bin_price = row.get('min_bin_price')
        position.max_bin_price = row.get('max_bin_price')
        
        # AIDEV-NOTE-GEMINI: Read dynamic OOR parameters from the DataFrame row
        position.oor_timeout_minutes = row.get('oor_timeout_minutes')
        position.oor_threshold_pct = row.get('oor_threshold_pct')
        
        return position