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
import multiprocessing
from itertools import chain

from core.models import TlsSimulationResult
from reporting.lp_position_valuator import simulate_position_exit_with_tls

from simulations.range_test_simulator import TpSlRangeSimulator
from core.models import Position, TlsSimulationResult
from reporting.post_close_analyzer import PostCloseAnalyzer

logger = logging.getLogger(__name__)

# AIDEV-NOTE-GEMINI: These functions must be at the module's top-level
# so they can be "pickled" and sent to subprocesses.

# Global variables for each worker process
worker_simulator = None
worker_combinations = None

def init_worker(simulator_instance, combinations):
    """
    Initializes a worker process by setting global (for that process)
    variables to avoid passing large objects on each task.
    """
    global worker_simulator, worker_combinations
    worker_simulator = simulator_instance
    worker_combinations = combinations

def process_single_position(position_row_dict: Dict) -> List[Dict]:
    """
    A worker function that processes a single position (one row from the DataFrame).
    It executes the logic that was originally inside the main for loop.
    """
    global worker_simulator, worker_combinations

    # Convert dict back to Series to use the existing _row_to_position method
    position = worker_simulator._row_to_position(pd.Series(position_row_dict))
    strategy_id = position_row_dict['strategy_instance_id']
    
    # This efficient logic remains: timeline is generated only once per position.
    timeline = worker_simulator._get_position_timeline(position)
    if not timeline:
        return []

    results_for_position = []
    # Use the global, pre-initialized list of combinations
    for tp_level, sl_level, tls_activation, tls_trail in worker_combinations:
        sim_result = simulate_position_exit_with_tls(
            timeline, tp_level, sl_level, tls_activation, tls_trail, position.initial_investment
        )
        
        tls_result_obj = TlsSimulationResult(
            position_id=position.position_id,
            strategy_instance_id=strategy_id,
            tp_level=tp_level,
            sl_level=sl_level,
            tls_activation=tls_activation,
            tls_trail=tls_trail,
            simulated_pnl=sim_result['final_pnl'],
            exit_reason=sim_result['exit_reason'],
            # AIDEV-NOTE-GEMINI: This is a placeholder. The correct value will be mapped
            # in the main process after all results are collected, as workers don't have
            # access to the complete `strategy_baselines` dict.
            strategy_best_non_tls_pnl=0.0
        )
        results_for_position.append(tls_result_obj.to_csv_row())
        
    return results_for_position

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
          
    def run_tls_analysis(self, positions_df: pd.DataFrame, existing_tp_sl_results: Optional[pd.DataFrame] = None) -> Dict[str, pd.DataFrame]:
        """
        AIDEV-NOTE-GEMINI: Main TLS analysis orchestrator, using multiprocessing
        to process positions in parallel for a significant speedup.
        """
        if 'strategy_instance_id' not in positions_df.columns:
            raise ValueError("positions_df must contain strategy_instance_id column. Run strategy detection first.")

        from simulations.baseline_comparator import StrategyBaselineComparator
        baseline_comparator = StrategyBaselineComparator()

        # 1. Baseline calculation remains in the main process as it requires access to all data.
        strategy_baselines = baseline_comparator.identify_best_non_tls_performance(
            positions_df.to_dict('records'),
            existing_tp_sl_results
        )

        # 2. Parameter combinations are also generated once in the main process.
        valid_combinations = self.generate_valid_combinations()
        positions_data = positions_df.to_dict('records')
        total_simulations = len(positions_data) * len(valid_combinations)
        logger.info(f"Starting TLS simulation: {len(positions_data)} positions × {len(valid_combinations)} combinations = {total_simulations} simulations")

        # 3. Launch the pool of worker processes.
        # Use one less core than available to keep the OS responsive.
        num_processes = max(1, multiprocessing.cpu_count() - 1)
        logger.info(f"Using {num_processes} worker processes for simulation...")

        all_results = []
        # The 'with' statement ensures the pool is properly closed.
        with multiprocessing.Pool(processes=num_processes, initializer=init_worker, initargs=(self, valid_combinations)) as pool:
            # imap_unordered is more efficient as it yields results as soon as they are ready,
            # rather than waiting for the batch to complete in order.
            # This integrates perfectly with tqdm.
            results_iterator = pool.imap_unordered(process_single_position, positions_data)
            
            with tqdm(total=len(positions_data), desc="Processing positions (in parallel)") as pbar:
                for single_position_results in results_iterator:
                    if single_position_results:
                        all_results.extend(single_position_results)
                    pbar.update(1)

        if not all_results:
            logger.warning("No TLS simulation results were generated.")
            return {
                'detailed_results': pd.DataFrame(),
                'baseline_comparison': pd.DataFrame()
            }
            
        detailed_df = pd.DataFrame(all_results)
        
        # 4. Post-process: Fill in the correct baseline_pnl after collecting all results.
        detailed_df['strategy_best_non_tls_pnl'] = detailed_df['strategy_instance_id'].map(strategy_baselines).fillna(0.0)
        
        # Recalculate tls_benefit_pct with the correct baseline.
        detailed_df['tls_benefit_pct'] = detailed_df.apply(
            lambda row: ((row['simulated_pnl'] - row['strategy_best_non_tls_pnl']) / abs(row['strategy_best_non_tls_pnl']) * 100) if row['strategy_best_non_tls_pnl'] != 0 else 0,
            axis=1
        )
        
        # 5. Delegate the effectiveness calculation to the comparator.
        effectiveness_df = baseline_comparator.calculate_strategy_effectiveness(detailed_df, strategy_baselines)

        return {
            'detailed_results': detailed_df,
            'baseline_comparison': effectiveness_df
        }
    
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