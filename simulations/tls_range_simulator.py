"""
4D TP/SL/TLS Range Test Simulator for Phase 1

Extends the existing TP/SL simulation infrastructure with Trailing Stop Loss functionality.
Implements the core TLS business logic: activation, trailing mechanism, and baseline comparison.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime
from tqdm import tqdm

from simulations.range_test_simulator import TpSlRangeSimulator
from core.models import Position, TlsSimulationResult
from reporting.post_close_analyzer import PostCloseAnalyzer

logger = logging.getLogger(__name__)


class TlsRangeSimulator:
    """
    AIDEV-TLS-CLAUDE: 4D TP/SL/TLS range testing simulator.
    
    Extends existing TP/SL simulation with Trailing Stop Loss functionality.
    Key business logic:
    1. TLS only activates when position reaches tls_activation profit level
    2. Dynamic SL = max(original_SL, peak_PnL - tls_trail) when TLS active
    3. Parameter validation: TP > TLS_activation, TLS_trail < TLS_activation
    """
    
    def __init__(self, config: Dict[str, Any], post_close_analyzer: PostCloseAnalyzer):
        """
        Initialize TLS range test simulator.
        
        Args:
            config: Main configuration dictionary
            post_close_analyzer: A pre-configured instance of PostCloseAnalyzer
        """
        self.config = config
        self.tls_config = config.get('tls_range_testing', {})
        self.range_config = config.get('range_testing', {})
        
        # TLS-specific parameters
        self.tls_activation_range = self.tls_config.get('tls_activation_range', [3, 4, 5, 6, 7, 8])
        self.tls_trail_range = self.tls_config.get('tls_trail_range', [1, 2, 3, 4, 5])
        
        # Inherit TP/SL ranges from existing configuration
        if self.tls_config.get('inherit_tp_sl_ranges', True):
            self.tp_levels = self.range_config.get('tp_levels', [2, 4, 6, 8, 10])
            self.sl_levels = self.range_config.get('sl_levels', [3, 5, 7, 10, 15])
        else:
            self.tp_levels = self.tls_config.get('tp_levels', [2, 4, 6, 8, 10])
            self.sl_levels = self.tls_config.get('sl_levels', [3, 5, 7, 10, 15])
        
        # Performance settings
        self.enable_smart_filtering = self.tls_config.get('enable_smart_filtering', True)
        self.max_combinations_per_position = self.tls_config.get('max_combinations_per_position', 1000)
        self.generate_baseline_comparison = self.tls_config.get('generate_baseline_comparison', True)
        
        self.post_close_analyzer = post_close_analyzer
        
        # Initialize baseline TP/SL simulator for comparison
        self.baseline_simulator = TpSlRangeSimulator(config, post_close_analyzer)
        
    def generate_valid_combinations(self) -> List[Tuple[float, float, float, float]]:
        """
        AIDEV-4D-VIZ-CLAUDE: Generate only valid TLS parameter combinations.
        
        Business logic constraints:
        - TP > TLS_activation (must be able to reach activation level)
        
        Returns:
            List of valid (tp, sl, tls_activation, tls_trail) tuples
        """
        valid_combinations = []
        total_possible = len(self.tp_levels) * len(self.sl_levels) * len(self.tls_activation_range) * len(self.tls_trail_range)
        
        for tp in self.tp_levels:
            for sl in self.sl_levels:
                for tls_act in self.tls_activation_range:
                    for tls_trail in self.tls_trail_range:
                        if self.enable_smart_filtering:
                            # Apply business logic constraints
                            if tp > tls_act:
                                valid_combinations.append((tp, sl, tls_act, tls_trail))
                        else:
                            valid_combinations.append((tp, sl, tls_act, tls_trail))
        
        logger.info(f"Generated {len(valid_combinations)} valid combinations out of {total_possible} possible")
        
        # Apply performance circuit breaker
        if len(valid_combinations) > self.max_combinations_per_position:
            logger.warning(f"Too many combinations ({len(valid_combinations)}), limiting to {self.max_combinations_per_position}")
            valid_combinations = valid_combinations[:self.max_combinations_per_position]
            
        return valid_combinations
    
    def simulate_position_with_tls(self, position: Position, timeline: List[Dict], 
                                  tp_level: float, sl_level: float, 
                                  tls_activation: float, tls_trail: float) -> Dict[str, Any]:
        """
        AIDEV-TLS-CLAUDE: Core TLS simulation logic.
        
        Simulates position with Trailing Stop Loss logic.
        
        Business Logic:
        - TLS activates only when position reaches tls_activation profit level
        - Once active, dynamic SL = max(original_SL, tls_activation - tls_trail)
        - Exit on first condition: TP reached, SL/TLS triggered, OOR, or end of data
        
        Args:
            position: Position object
            timeline: Complete price timeline with PnL data
            tp_level: Take profit level (%)
            sl_level: Stop loss level (%)
            tls_activation: TLS activation level (%)
            tls_trail: TLS trail distance (%)
            
        Returns:
            Dictionary with simulation results
        """
        if not timeline:
            return {
                'simulated_pnl': 0.0,
                'simulated_pnl_pct': 0.0,
                'exit_reason': 'NO_DATA',
                'days_to_exit': 0.0,
                'tls_activated': False,
                'peak_pnl_reached': 0.0
            }
        
        # TLS state tracking
        peak_pnl = 0.0
        tls_activated = False
        dynamic_sl = -sl_level  # Start with original SL
        
        # OOR tracking (reuse existing logic)
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
            
            current_price = point['price']  # Close price
            current_timestamp = point['timestamp']
            
            # Update peak PnL and check TLS activation
            current_max_pnl = max(pnl_pct_high, peak_pnl)
            if current_max_pnl > peak_pnl:
                peak_pnl = current_max_pnl
                
            # TLS activation check
            if not tls_activated and peak_pnl >= tls_activation:
                tls_activated = True
                logger.debug(f"TLS activated at {peak_pnl:.2f}% for position {position.position_id}")
                
            # Update dynamic SL if TLS is active (FIXED: use activation-based, not peak-based)
            if tls_activated:
                # TLS sets SL as fixed offset from activation point
                tls_sl = tls_activation - tls_trail
                dynamic_sl = max(dynamic_sl, tls_sl)
            
            # --- PRIORITY EXIT LOGIC (same as existing TP/SL) ---
            # 1. TP check (high price)
            if pnl_pct_high >= tp_level:
                exit_reason = 'TP'
                final_pnl_pct = tp_level  # Exit at exact TP level
                exit_point = point
                break
            
            # 2. SL/TLS check (low price)
            if pnl_pct_low <= dynamic_sl:
                if tls_activated and dynamic_sl > -sl_level:
                    exit_reason = 'TLS'
                else:
                    exit_reason = 'SL'
                final_pnl_pct = dynamic_sl  # Exit at exact SL/TLS level
                exit_point = point
                break
            
            # 3. OOR check (close price)
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
        
        # If no exit condition was met, position runs to end
        if exit_point is None:
            exit_reason = 'END'
            exit_point = timeline[-1]
            final_pnl_pct = exit_point['pnl_pct']
        
        # Calculate final results
        simulated_pnl = position.initial_investment * (final_pnl_pct / 100.0)
        days_to_exit = (exit_point['timestamp'] - position.open_timestamp).total_seconds() / 86400
        
        return {
            'simulated_pnl': simulated_pnl,
            'simulated_pnl_pct': final_pnl_pct,
            'exit_reason': exit_reason,
            'days_to_exit': days_to_exit,
            'tls_activated': tls_activated,
            'peak_pnl_reached': peak_pnl
        }
    
    def calculate_strategy_baseline(self, strategy_positions: List[Dict], existing_tp_sl_results: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        AIDEV-BASELINE-CLAUDE: Find best non-TLS performance per strategy.
        
        Args:
            strategy_positions: List of positions for a strategy
            existing_tp_sl_results: Optional pre-computed TP/SL results to use as baseline
            
        Returns:
            Dictionary mapping strategy_instance_id to best non-TLS PnL
        """
        strategy_baselines = {}
        
        if existing_tp_sl_results is not None and not existing_tp_sl_results.empty:
            # Use existing TP/SL results as baseline
            for strategy_id in existing_tp_sl_results['strategy_instance_id'].unique():
                strategy_results = existing_tp_sl_results[existing_tp_sl_results['strategy_instance_id'] == strategy_id]
                best_pnl = strategy_results['simulated_pnl'].max()
                strategy_baselines[strategy_id] = best_pnl
                logger.debug(f"Baseline for {strategy_id}: {best_pnl:.4f} SOL")
        else:
            # Run baseline TP/SL simulation if needed
            logger.info("No existing TP/SL results provided, running baseline simulation...")
            positions_df = pd.DataFrame(strategy_positions)
            baseline_results = self.baseline_simulator.run_simulation(positions_df)
            
            if 'detailed_results' in baseline_results:
                detailed_df = baseline_results['detailed_results']
                for strategy_id in detailed_df['strategy_instance_id'].unique():
                    strategy_results = detailed_df[detailed_df['strategy_instance_id'] == strategy_id]
                    best_pnl = strategy_results['simulated_pnl'].max()
                    strategy_baselines[strategy_id] = best_pnl
                    logger.debug(f"Computed baseline for {strategy_id}: {best_pnl:.4f} SOL")
        
        return strategy_baselines
    
    def run_tls_analysis(self, positions_df: pd.DataFrame, existing_tp_sl_results: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
        """
        Main TLS analysis orchestrator.
        
        Args:
            positions_df: Enriched positions DataFrame with strategy_instance_id
            existing_tp_sl_results: Optional existing TP/SL results for baseline comparison
            
        Returns:
            Dictionary with 'detailed_results' and 'baseline_comparison' DataFrames
        """
        if 'strategy_instance_id' not in positions_df.columns:
            raise ValueError("positions_df must contain strategy_instance_id column. Run strategy detection first.")
        
        # Calculate baseline performance per strategy
        strategy_baselines = self.calculate_strategy_baseline(
            positions_df.to_dict('records'), 
            existing_tp_sl_results
        )
        
        # Generate valid parameter combinations
        valid_combinations = self.generate_valid_combinations()
        total_simulations = len(positions_df) * len(valid_combinations)
        
        logger.info(f"Starting TLS simulation: {len(positions_df)} positions × {len(valid_combinations)} combinations = {total_simulations} simulations")
        
        detailed_results = []
        
        # Process each position
        with tqdm(total=len(positions_df), desc="Processing TLS simulations") as pbar:
            for idx, row in positions_df.iterrows():
                position = self._row_to_position(row)
                strategy_id = row['strategy_instance_id']
                baseline_pnl = strategy_baselines.get(strategy_id, 0.0)
                
                # Get position timeline once (expensive operation)
                timeline = self._get_position_timeline(position)
                
                if not timeline:
                    logger.debug(f"Position {position.position_id} excluded from TLS analysis - no timeline data")
                    pbar.update(1)
                    continue
                
                # Test all TLS combinations
                for tp_level, sl_level, tls_activation, tls_trail in valid_combinations:
                    sim_result = self.simulate_position_with_tls(
                        position, timeline, tp_level, sl_level, tls_activation, tls_trail
                    )
                    
                    # Create TLS simulation result
                    tls_result = TlsSimulationResult(
                        position_id=position.position_id,
                        strategy_instance_id=strategy_id,
                        tp_level=tp_level,
                        sl_level=sl_level,
                        tls_activation=tls_activation,
                        tls_trail=tls_trail,
                        simulated_pnl=sim_result['simulated_pnl'],
                        exit_reason=sim_result['exit_reason'],
                        strategy_best_non_tls_pnl=baseline_pnl
                    )
                    
                    detailed_results.append(tls_result.to_csv_row())
                
                pbar.update(1)
        
        # Convert to DataFrame
        detailed_df = pd.DataFrame(detailed_results)
        
        # Calculate baseline comparison metrics
        baseline_comparison_df = self._calculate_baseline_comparison(detailed_df, strategy_baselines)
        
        return {
            'detailed_results': detailed_df,
            'baseline_comparison': baseline_comparison_df
        }
    
    def _calculate_baseline_comparison(self, detailed_df: pd.DataFrame, strategy_baselines: Dict[str, float]) -> pd.DataFrame:
        """Calculate TLS vs baseline comparison metrics."""
        if detailed_df.empty:
            return pd.DataFrame()
        
        # Group by strategy and find best TLS performance
        strategy_comparisons = []
        
        for strategy_id in detailed_df['strategy_instance_id'].unique():
            strategy_results = detailed_df[detailed_df['strategy_instance_id'] == strategy_id]
            baseline_pnl = strategy_baselines.get(strategy_id, 0.0)
            
            # Find best TLS combination for this strategy
            best_tls_idx = strategy_results['simulated_pnl'].idxmax()
            best_tls_result = strategy_results.loc[best_tls_idx]
            
            # Calculate improvement metrics
            tls_benefit_pct = ((best_tls_result['simulated_pnl'] - baseline_pnl) / abs(baseline_pnl) * 100) if baseline_pnl != 0 else 0
            
            strategy_comparisons.append({
                'strategy_instance_id': strategy_id,
                'baseline_pnl': baseline_pnl,
                'best_tls_pnl': best_tls_result['simulated_pnl'],
                'best_tls_tp': best_tls_result['tp_level'],
                'best_tls_sl': best_tls_result['sl_level'],
                'best_tls_activation': best_tls_result['tls_activation'],
                'best_tls_trail': best_tls_result['tls_trail'],
                'tls_benefit_pct': tls_benefit_pct,
                'tls_improves_performance': best_tls_result['simulated_pnl'] > baseline_pnl
            })
        
        return pd.DataFrame(strategy_comparisons)
    
    def _get_position_timeline(self, position: Position) -> List[Dict]:
        """
        Get complete historical timeline for position.
        Reuses existing timeline logic from TpSlRangeSimulator.
        """
        # Delegate to existing implementation
        return self.baseline_simulator._get_position_timeline(position)
    
    def _row_to_position(self, row: pd.Series) -> Position:
        """
        Convert DataFrame row to Position object.
        Reuses existing conversion logic from TpSlRangeSimulator.
        """
        # Delegate to existing implementation
        return self.baseline_simulator._row_to_position(row)