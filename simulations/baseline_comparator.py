"""
Baseline Comparison System for TLS Analysis

Provides functionality to identify best non-TLS performance per strategy
and calculate TLS benefit metrics for comparison analysis.
"""

import logging
import pandas as pd
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class StrategyBaselineComparator:
    """
    AIDEV-BASELINE-CLAUDE: Per-strategy baseline identification and comparison.
    
    Identifies the best performing TP/SL combination for each strategy 
    and calculates TLS benefit metrics.
    """
    
    def __init__(self):
        """Initialize baseline comparator."""
        pass
    
    def identify_best_non_tls_performance(self, strategy_positions: List[Dict], 
                                        existing_tp_sl_results: Optional[pd.DataFrame] = None) -> Dict[str, float]:
        """
        For each strategy, find the best non-TLS performance.
        
        Args:
            strategy_positions: List of position dictionaries
            existing_tp_sl_results: Optional DataFrame with existing TP/SL simulation results
            
        Returns:
            Dictionary mapping strategy_instance_id -> best_non_tls_pnl
        """
        strategy_baselines = {}
        
        if existing_tp_sl_results is not None and not existing_tp_sl_results.empty:
            # Use existing TP/SL results as baseline
            logger.info(f"Using existing TP/SL results as baseline ({len(existing_tp_sl_results)} results)")
            
            for strategy_id in existing_tp_sl_results['strategy_instance_id'].unique():
                strategy_results = existing_tp_sl_results[existing_tp_sl_results['strategy_instance_id'] == strategy_id]
              
                if not strategy_results.empty:
                    best_pnl = strategy_results['simulated_pnl'].max()
                    strategy_baselines[strategy_id] = best_pnl
                    
                    # Log details for top performing combination
                    best_idx = strategy_results['simulated_pnl'].idxmax()
                    best_combo = strategy_results.loc[best_idx]
                    logger.debug(
                        f"Baseline for {strategy_id}: {best_pnl:.4f} SOL "
                        f"(TP: {best_combo['tp_level']}, SL: {best_combo['sl_level']})"
                    )
                else:
                    logger.warning(f"No TP/SL results found for strategy {strategy_id}")
                    strategy_baselines[strategy_id] = 0.0
        else:
            # Calculate baseline from actual position performance if no TP/SL results
            logger.info("No existing TP/SL results provided, using actual position performance as baseline")
            
            positions_df = pd.DataFrame(strategy_positions)
            
            for strategy_id in positions_df['strategy_instance_id'].unique():
                strategy_positions_data = positions_df[positions_df['strategy_instance_id'] == strategy_id]
                
                if not strategy_positions_data.empty:
                    # Use best actual performance as baseline
                    best_actual_pnl = strategy_positions_data['pnl_sol'].max()
                    strategy_baselines[strategy_id] = best_actual_pnl
                    logger.debug(f"Actual performance baseline for {strategy_id}: {best_actual_pnl:.4f} SOL")
                else:
                    strategy_baselines[strategy_id] = 0.0
        
        logger.info(f"Calculated baselines for {len(strategy_baselines)} strategies")
        return strategy_baselines
    
    def calculate_tls_benefit(self, tls_pnl: float, baseline_pnl: float) -> float:
        """
        Calculate TLS benefit as percentage improvement over baseline.
        
        Args:
            tls_pnl: TLS simulation PnL result
            baseline_pnl: Best non-TLS PnL for comparison
            
        Returns:
            Percentage improvement (positive = TLS better, negative = TLS worse)
        """
        if baseline_pnl == 0:
            return 0.0  # Avoid division by zero
        
        return ((tls_pnl - baseline_pnl) / abs(baseline_pnl)) * 100
    
    def calculate_strategy_effectiveness(self, tls_results_df: pd.DataFrame, 
                                       strategy_baselines: Dict[str, float]) -> pd.DataFrame:
        """
        Calculate TLS effectiveness metrics per strategy.
        
        Args:
            tls_results_df: DataFrame with TLS simulation results
            strategy_baselines: Dictionary of baseline performance per strategy
            
        Returns:
            DataFrame with strategy-level TLS effectiveness metrics
        """
        if tls_results_df.empty:
            return pd.DataFrame()
        
        strategy_effectiveness = []
        
        for strategy_id in tls_results_df['strategy_instance_id'].unique():
            strategy_results = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
            baseline_pnl = strategy_baselines.get(strategy_id, 0.0)
            
            if strategy_results.empty:
                continue
            
            # Calculate TLS benefit for all combinations
            strategy_results = strategy_results.copy()
            strategy_results['tls_benefit_pct'] = strategy_results['simulated_pnl'].apply(
                lambda x: self.calculate_tls_benefit(x, baseline_pnl)
            )
            
            # Find best TLS performance
            best_tls_idx = strategy_results['simulated_pnl'].idxmax()
            best_tls_result = strategy_results.loc[best_tls_idx]
            
            # Calculate effectiveness metrics
            improvement_count = len(strategy_results[strategy_results['tls_benefit_pct'] > 0])
            total_combinations = len(strategy_results)
            improvement_rate = (improvement_count / total_combinations * 100) if total_combinations > 0 else 0
            
            avg_improvement = strategy_results[strategy_results['tls_benefit_pct'] > 0]['tls_benefit_pct'].mean()
            if pd.isna(avg_improvement):
                avg_improvement = 0.0
            
            # Risk reduction: average loss reduction when TLS prevents deeper losses
            negative_results = strategy_results[strategy_results['tls_benefit_pct'] < 0]
            avg_risk_increase = negative_results['tls_benefit_pct'].mean() if not negative_results.empty else 0.0
            
            strategy_effectiveness.append({
                'strategy_instance_id': strategy_id,
                'baseline_pnl': baseline_pnl,
                'best_tls_pnl': best_tls_result['simulated_pnl'],
                'best_tls_tp': best_tls_result['tp_level'],
                'best_tls_sl': best_tls_result['sl_level'],
                'best_tls_activation': best_tls_result['tls_activation'],
                'best_tls_trail': best_tls_result['tls_trail'],
                'best_tls_benefit_pct': best_tls_result['tls_benefit_pct'],
                'improvement_rate_pct': improvement_rate,
                'avg_improvement_when_positive': avg_improvement,
                'avg_risk_increase_when_negative': avg_risk_increase,
                'total_combinations_tested': total_combinations,
                'combinations_improved': improvement_count,
                'tls_recommended': best_tls_result['tls_benefit_pct'] > 0
            })
        
        return pd.DataFrame(strategy_effectiveness)
    
    def generate_comparison_summary(self, effectiveness_df: pd.DataFrame) -> Dict[str, Any]:
        """
        Generate summary statistics for TLS vs baseline comparison.
        
        Args:
            effectiveness_df: DataFrame with strategy effectiveness metrics
            
        Returns:
            Dictionary with summary statistics
        """
        if effectiveness_df.empty:
            return {
                'total_strategies': 0,
                'strategies_improved': 0,
                'improvement_rate': 0.0,
                'avg_benefit_when_positive': 0.0,
                'median_benefit_all_strategies': 0.0
            }
        
        total_strategies = len(effectiveness_df)
        strategies_improved = len(effectiveness_df[effectiveness_df['tls_recommended']])
        overall_improvement_rate = (strategies_improved / total_strategies * 100) if total_strategies > 0 else 0
        
        positive_benefits = effectiveness_df[effectiveness_df['best_tls_benefit_pct'] > 0]['best_tls_benefit_pct']
        avg_benefit_when_positive = positive_benefits.mean() if not positive_benefits.empty else 0.0
        
        median_benefit_all = effectiveness_df['best_tls_benefit_pct'].median()
        
        return {
            'total_strategies': total_strategies,
            'strategies_improved': strategies_improved,
            'improvement_rate': overall_improvement_rate,
            'avg_benefit_when_positive': avg_benefit_when_positive,
            'median_benefit_all_strategies': median_benefit_all,
            'best_performing_strategy': effectiveness_df.loc[effectiveness_df['best_tls_benefit_pct'].idxmax()]['strategy_instance_id'] if not effectiveness_df.empty else None,
            'max_benefit_achieved': effectiveness_df['best_tls_benefit_pct'].max() if not effectiveness_df.empty else 0.0
        }