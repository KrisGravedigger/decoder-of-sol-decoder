"""
Unified Baseline Management System for TP/SL/TLS Analysis

Provides single source of truth for all baseline calculations,
ensuring consistency across range testing, TLS comparison, and reporting.
"""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json
import os

logger = logging.getLogger(__name__)


@dataclass
class BaselineResult:
    """Unified baseline result structure."""
    strategy_id: str
    baseline_sol: float          # Absolute SOL value (sum of best positions)
    baseline_pct: float          # Weighted average percentage return
    optimal_tp: float            # Best performing TP level
    optimal_sl: float            # Best performing SL level  
    position_count: int          # Number of positions in strategy
    confidence_score: float      # 0-1, based on sample size and variance
    metadata: Dict[str, Any] = field(default_factory=dict)  # Additional context
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            'strategy_id': self.strategy_id,
            'baseline_sol': self.baseline_sol,
            'baseline_pct': self.baseline_pct,
            'optimal_tp': self.optimal_tp,
            'optimal_sl': self.optimal_sl,
            'position_count': self.position_count,
            'confidence_score': self.confidence_score,
            'metadata': self.metadata
        }
    
    
@dataclass
class ComparisonResult:
    """Unified comparison structure for TLS vs baseline."""
    strategy_id: str
    baseline_result: BaselineResult
    tls_best_sol: float          # Best TLS performance in SOL
    tls_best_pct: float          # Best TLS performance in %
    tls_best_params: Dict[str, float]  # TP/SL/Act/Trail values
    improvement_sol: float       # Absolute difference
    improvement_pct: float       # Percentage improvement over baseline
    recommendation: str          # "YES", "NO", "MARGINAL"
    rationale: str              # Explanation for recommendation
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'strategy_id': self.strategy_id,
            'baseline_sol': self.baseline_result.baseline_sol,
            'baseline_pct': self.baseline_result.baseline_pct,
            'tls_best_sol': self.tls_best_sol,
            'tls_best_pct': self.tls_best_pct,
            'tls_best_params': self.tls_best_params,
            'improvement_sol': self.improvement_sol,
            'improvement_pct': self.improvement_pct,
            'recommendation': self.recommendation,
            'rationale': self.rationale,
            'confidence': self.baseline_result.confidence_score
        }


@dataclass 
class ValidationReport:
    """Report on baseline consistency across modules."""
    is_consistent: bool
    total_strategies: int
    consistent_strategies: int
    inconsistencies: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def add_inconsistency(self, strategy_id: str, module1: str, value1: float, 
                         module2: str, value2: float, tolerance: float):
        """Record an inconsistency between modules."""
        diff = abs(value1 - value2)
        if diff > tolerance:
            self.is_consistent = False
            self.inconsistencies.append({
                'strategy_id': strategy_id,
                f'{module1}_baseline': value1,
                f'{module2}_baseline': value2,
                'difference': diff,
                'difference_pct': (diff / abs(value1) * 100) if value1 != 0 else 0
            })
            
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for reporting."""
        return {
            'is_consistent': self.is_consistent,
            'total_strategies': self.total_strategies,
            'consistent_strategies': self.consistent_strategies,
            'consistency_rate': (self.consistent_strategies / self.total_strategies * 100) 
                              if self.total_strategies > 0 else 0,
            'inconsistencies': self.inconsistencies,
            'warnings': self.warnings,
            'timestamp': self.timestamp
        }


class UnifiedBaselineManager:
    """
    Single source of truth for all baseline calculations.
    
    AIDEV-NOTE-CLAUDE: Central baseline management to ensure consistency across:
    - Range test TP/SL optimization
    - TLS comparison analysis  
    - HTML report generation
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize baseline manager with configuration.
        
        Args:
            config: Configuration dictionary (from portfolio_config.yaml)
        """
        self.config = config or {}
        self._baseline_cache = {}  # Cache for calculated baselines
        self._confidence_scores = {}  # Cache for confidence scores
        self._cache_file = "reporting/output/unified_baselines_cache.json"
        
        # Configuration parameters
        self.min_positions_full_confidence = self.config.get('baseline_confidence', {}).get(
            'min_positions_full_confidence', 20
        )
        self.variance_penalty_factor = self.config.get('baseline_confidence', {}).get(
            'variance_penalty_factor', 0.1
        )
        self.consistency_tolerance = self.config.get('baseline_validation', {}).get(
            'consistency_tolerance_sol', 0.01
        )
        
        # Load cached baselines if available
        self._load_cache()
        
        logger.info("UnifiedBaselineManager initialized")
        
    def calculate_strategy_baseline(self, 
                                   strategy_id: str,
                                   detailed_results: pd.DataFrame,
                                   metric: str = 'total_pnl') -> BaselineResult:
        """
        Calculate optimal TP/SL baseline for a strategy.
        
        AIDEV-NOTE-CLAUDE: Primary baseline calculation - finds best TP/SL combo
        Uses aggregated results for strategy-level optimization.
        
        Args:
            strategy_id: Strategy instance identifier
            detailed_results: DataFrame with simulation results (from range testing)
            metric: Optimization metric ('total_pnl', 'avg_pnl', 'win_rate')
            
        Returns:
            BaselineResult with optimal parameters and confidence score
        """
        # Check cache first
        cache_key = f"{strategy_id}_{metric}"
        if cache_key in self._baseline_cache:
            logger.debug(f"Returning cached baseline for {strategy_id}")
            return self._baseline_cache[cache_key]
            
        # Filter for this strategy
        # AIDEV-NOTE-CLAUDE: Handle empty DataFrame case - check if required columns exist
        if detailed_results.empty or 'strategy_instance_id' not in detailed_results.columns:
            logger.warning(f"No data or missing columns for strategy {strategy_id}")
            return self._create_empty_baseline(strategy_id)

        strategy_data = detailed_results[detailed_results['strategy_instance_id'] == strategy_id].copy()
        
        if strategy_data.empty:
            logger.warning(f"No data found for strategy {strategy_id}")
            return self._create_empty_baseline(strategy_id)
            
        # AIDEV-NOTE-CLAUDE: Validate required columns for aggregation - flexible column mapping
        pnl_column = None
        for possible_col in ['total_pnl', 'simulated_pnl', 'avg_pnl', 'pnl_sol']:
            if possible_col in strategy_data.columns:
                pnl_column = possible_col
                break
                
        if pnl_column is None:
            logger.error(f"No PnL column found for strategy {strategy_id}. Available columns: {list(strategy_data.columns)}")
            return self._create_empty_baseline(strategy_id)
            
        # Check if data is already aggregated (has tp_level, sl_level columns)
        if 'tp_level' in strategy_data.columns and 'sl_level' in strategy_data.columns:
            # Data is already aggregated from range test results
            # AIDEV-NOTE-CLAUDE: Working with pre-aggregated range test data
            aggregated = strategy_data.copy()
            
            # Ensure we have the expected column names
            if pnl_column != 'total_pnl' and 'total_pnl' not in aggregated.columns:
                aggregated['total_pnl'] = aggregated[pnl_column]
            if 'avg_pnl' not in aggregated.columns and pnl_column in aggregated.columns:
                aggregated['avg_pnl'] = aggregated[pnl_column]
            
            # Add missing columns with defaults if needed
            if 'std_pnl' not in aggregated.columns:
                aggregated['std_pnl'] = 0.0  # No variance data in aggregated results
                
        else:
            # Raw position data - need to aggregate by TP/SL
            # AIDEV-NOTE-CLAUDE: Aggregating raw position data at TP/SL level
            agg_dict = {pnl_column: ['sum', 'mean', 'std', 'count']}
            
            # Add optional columns if they exist
            pnl_pct_col = None
            for possible_col in ['avg_pnl_pct', 'simulated_pnl_pct', 'pnl_pct']:
                if possible_col in strategy_data.columns:
                    pnl_pct_col = possible_col
                    agg_dict[possible_col] = 'mean'
                    break
                    
            if 'position_id' in strategy_data.columns:
                agg_dict['position_id'] = 'count'
                
            aggregated = strategy_data.groupby(['tp_level', 'sl_level']).agg(agg_dict).reset_index()
            
            # Flatten column names safely
            new_columns = ['tp_level', 'sl_level', 'total_pnl', 'avg_pnl', 'std_pnl', 'sim_count']
            if pnl_pct_col:
                new_columns.append('avg_pnl_pct')
            if 'position_id' in agg_dict:
                new_columns.append('position_count')
                
            aggregated.columns = new_columns
            
        # Find optimal combination based on metric
        if metric == 'total_pnl' and 'total_pnl' in aggregated.columns:
            optimal_idx = aggregated['total_pnl'].idxmax()
        elif metric == 'avg_pnl' and 'avg_pnl' in aggregated.columns:
            optimal_idx = aggregated['avg_pnl'].idxmax()
        elif metric == 'win_rate' and 'win_rate' in aggregated.columns:
            optimal_idx = aggregated['win_rate'].idxmax()
        elif 'total_pnl' in aggregated.columns:
            # Default to total_pnl
            optimal_idx = aggregated['total_pnl'].idxmax()
        elif 'avg_pnl' in aggregated.columns:
            # Fallback to avg_pnl
            optimal_idx = aggregated['avg_pnl'].idxmax()
        else:
            logger.error(f"No suitable optimization column found for {strategy_id}")
            return self._create_empty_baseline(strategy_id)
            
        optimal_row = aggregated.loc[optimal_idx]
        
        # Calculate confidence score - safe value extraction
        position_count = int(optimal_row.get('position_count', optimal_row.get('sim_count', 1)))
        variance = float(optimal_row.get('std_pnl', 0))
        confidence = self._calculate_confidence(position_count, variance)
        
        # Safe value extraction for baseline result
        baseline_sol = float(optimal_row.get('total_pnl', optimal_row.get('avg_pnl', optimal_row.get(pnl_column, 0))))
        baseline_pct = float(optimal_row.get('avg_pnl_pct', 0))
        optimal_tp = float(optimal_row.get('tp_level', 0))
        optimal_sl = float(optimal_row.get('sl_level', 0))
        
        # Create baseline result
        result = BaselineResult(
            strategy_id=strategy_id,
            baseline_sol=baseline_sol,
            baseline_pct=baseline_pct,
            optimal_tp=optimal_tp,
            optimal_sl=optimal_sl,
            position_count=position_count,
            confidence_score=confidence,
            metadata={
                'metric_used': metric,
                'variance': variance,
                'data_points': len(strategy_data),
                'unique_combinations': len(aggregated),
                'calculation_timestamp': datetime.now().isoformat()
            }
        )
        
        # Cache the result
        self._baseline_cache[cache_key] = result
        self._save_cache()
        
        logger.info(f"Calculated baseline for {strategy_id}: {result.baseline_sol:.4f} SOL "
                   f"(TP:{result.optimal_tp}, SL:{result.optimal_sl}, confidence:{confidence:.2f})")
        
        return result
        
    def get_tls_comparison_baseline(self,
                                   strategy_id: str,
                                   tls_results: Optional[pd.DataFrame] = None) -> float:
        """
        Get baseline for TLS comparison using consistent methodology.
        
        Args:
            strategy_id: Strategy instance identifier  
            tls_results: Optional TLS simulation results
            
        Returns:
            Baseline value in SOL for comparison
        """
        # AIDEV-NOTE-CLAUDE: Always use cached baseline if available for consistency
        cache_key = f"{strategy_id}_total_pnl"
        if cache_key in self._baseline_cache:
            return self._baseline_cache[cache_key].baseline_sol
            
        # If we have TLS results with embedded baselines, use them
        if tls_results is not None and not tls_results.empty:
            strategy_tls = tls_results[tls_results['strategy_instance_id'] == strategy_id]
            if not strategy_tls.empty and 'strategy_best_non_tls_pnl' in strategy_tls.columns:
                # Use the first value (should all be the same for a strategy)
                return float(strategy_tls['strategy_best_non_tls_pnl'].iloc[0])
                
        logger.warning(f"No baseline found for {strategy_id}, returning 0")
        return 0.0
        
    def validate_consistency(self, 
                            range_results: pd.DataFrame,
                            tls_results: Optional[pd.DataFrame] = None) -> ValidationReport:
        """
        Validate that baselines are consistent across modules.
        
        Args:
            range_results: Aggregated range test results
            tls_results: TLS simulation results (optional)
            
        Returns:
            ValidationReport with consistency analysis
        """
        report = ValidationReport(
            is_consistent=True,
            total_strategies=0,
            consistent_strategies=0
        )
        
        # Get unique strategies
        strategies = set()
        if 'strategy_instance_id' in range_results.columns:
            strategies.update(range_results['strategy_instance_id'].unique())
        if tls_results is not None and 'strategy_instance_id' in tls_results.columns:
            strategies.update(tls_results['strategy_instance_id'].unique())
            
        report.total_strategies = len(strategies)
        
        for strategy_id in strategies:
            # Get baseline from range results
            range_baseline = None
            if strategy_id in range_results['strategy_instance_id'].values:
                strategy_range = range_results[range_results['strategy_instance_id'] == strategy_id]
                if 'total_pnl' in strategy_range.columns:
                    # Find the max total_pnl as baseline
                    range_baseline = strategy_range['total_pnl'].max()
                    
            # Get baseline from TLS results
            tls_baseline = None  
            if tls_results is not None and strategy_id in tls_results['strategy_instance_id'].values:
                tls_baseline = self.get_tls_comparison_baseline(strategy_id, tls_results)
                
            # Compare if both exist
            if range_baseline is not None and tls_baseline is not None:
                report.add_inconsistency(
                    strategy_id, 
                    'range_test', range_baseline,
                    'tls', tls_baseline,
                    self.consistency_tolerance
                )
                
                if abs(range_baseline - tls_baseline) <= self.consistency_tolerance:
                    report.consistent_strategies += 1
            elif range_baseline is not None or tls_baseline is not None:
                # Only one baseline exists
                report.warnings.append(f"Strategy {strategy_id}: baseline only in one module")
                
        # Log validation results
        if report.is_consistent:
            logger.info(f"Baseline validation PASSED: {report.consistent_strategies}/{report.total_strategies} consistent")
        else:
            logger.warning(f"Baseline validation FAILED: {len(report.inconsistencies)} inconsistencies found")
            
        return report
        
    def generate_tls_recommendation(self, comparison: ComparisonResult) -> Tuple[str, str]:
        """
        Generate actionable TLS recommendation based on comparison.
        
        Args:
            comparison: Comparison result with baseline and TLS performance
            
        Returns:
            Tuple of (recommendation, rationale)
        """
        confidence = comparison.baseline_result.confidence_score
        improvement = comparison.improvement_pct
        
        # AIDEV-NOTE-CLAUDE: Decision thresholds from business requirements
        if improvement > 5.0 and confidence > 0.7:
            recommendation = "YES"
            rationale = f"TLS improves performance by {improvement:.1f}% with high confidence ({confidence:.2f})"
        elif improvement > 3.0 and confidence > 0.5:
            recommendation = "MARGINAL"  
            rationale = f"TLS shows {improvement:.1f}% improvement but needs more testing (confidence: {confidence:.2f})"
        elif improvement < -2.0:
            recommendation = "NO"
            rationale = f"TLS degrades performance by {abs(improvement):.1f}% - stay with fixed TP/SL"
        elif confidence < 0.3:
            recommendation = "MARGINAL"
            rationale = f"Insufficient data for reliable recommendation (confidence: {confidence:.2f})"
        else:
            recommendation = "MARGINAL"
            rationale = f"TLS impact minimal ({improvement:+.1f}%), test in small positions first"
            
        return recommendation, rationale
        
    def _calculate_confidence(self, position_count: int, variance: float) -> float:
        """
        Calculate confidence score based on sample size and variance.
        
        AIDEV-NOTE-CLAUDE: Confidence scoring for small sample interpretation
        Full confidence at 20+ positions, scaled down for smaller samples
        
        Args:
            position_count: Number of positions in strategy
            variance: Standard deviation of returns
            
        Returns:
            Confidence score between 0.1 and 1.0
        """
        # Base confidence from sample size
        size_confidence = min(1.0, position_count / self.min_positions_full_confidence)
        
        # Variance penalty (high variance = lower confidence)
        variance_penalty = 1.0 / (1.0 + variance * self.variance_penalty_factor)
        
        # Combined score with minimum threshold
        confidence = size_confidence * variance_penalty * 0.9 + 0.1
        
        logger.debug(f"Confidence calculation: positions={position_count}, variance={variance:.4f}, "
                    f"size_conf={size_confidence:.2f}, var_penalty={variance_penalty:.2f}, "
                    f"final={confidence:.2f}")
        
        return confidence
        
    def _create_empty_baseline(self, strategy_id: str) -> BaselineResult:
        """Create empty baseline result for strategies with no data."""
        return BaselineResult(
            strategy_id=strategy_id,
            baseline_sol=0.0,
            baseline_pct=0.0,
            optimal_tp=0.0,
            optimal_sl=0.0,
            position_count=0,
            confidence_score=0.0,
            metadata={'error': 'No data available'}
        )
        
    def _load_cache(self):
        """Load cached baselines from file."""
        if os.path.exists(self._cache_file):
            try:
                with open(self._cache_file, 'r') as f:
                    cache_data = json.load(f)
                    
                # Reconstruct BaselineResult objects
                for key, value in cache_data.items():
                    if isinstance(value, dict) and 'strategy_id' in value:
                        self._baseline_cache[key] = BaselineResult(
                            strategy_id=value['strategy_id'],
                            baseline_sol=value['baseline_sol'],
                            baseline_pct=value['baseline_pct'],
                            optimal_tp=value['optimal_tp'],
                            optimal_sl=value['optimal_sl'],
                            position_count=value['position_count'],
                            confidence_score=value['confidence_score'],
                            metadata=value.get('metadata', {})
                        )
                        
                logger.info(f"Loaded {len(self._baseline_cache)} cached baselines")
            except Exception as e:
                logger.warning(f"Could not load baseline cache: {e}")
                
    def _save_cache(self):
        """Save calculated baselines to file."""
        try:
            # Convert BaselineResult objects to dicts
            cache_data = {}
            for key, value in self._baseline_cache.items():
                if isinstance(value, BaselineResult):
                    cache_data[key] = value.to_dict()
                else:
                    cache_data[key] = value
                    
            os.makedirs(os.path.dirname(self._cache_file), exist_ok=True)
            with open(self._cache_file, 'w') as f:
                json.dump(cache_data, f, indent=2)
                
            logger.debug(f"Saved {len(cache_data)} baselines to cache")
        except Exception as e:
            logger.warning(f"Could not save baseline cache: {e}")
            
    def clear_cache(self):
        """Clear all cached baselines."""
        self._baseline_cache.clear()
        self._confidence_scores.clear()
        if os.path.exists(self._cache_file):
            os.remove(self._cache_file)
        logger.info("Baseline cache cleared")
        
    def get_all_baselines(self) -> Dict[str, BaselineResult]:
        """Get all cached baselines."""
        return {k: v for k, v in self._baseline_cache.items() if isinstance(v, BaselineResult)}
        
    def generate_comparison_report(self, 
                                  range_results: pd.DataFrame,
                                  tls_results: Optional[pd.DataFrame] = None) -> pd.DataFrame:
        """
        Generate comprehensive comparison report.
        
        Args:
            range_results: Range test results
            tls_results: TLS simulation results
            
        Returns:
            DataFrame with baseline comparisons and recommendations
        """
        comparisons = []
        
        # Get all unique strategies
        strategies = range_results['strategy_instance_id'].unique() if 'strategy_instance_id' in range_results.columns else []
        
        for strategy_id in strategies:
            # Calculate baseline from range results
            baseline = self.calculate_strategy_baseline(strategy_id, range_results)
            
            # If we have TLS results, create comparison
            if tls_results is not None and strategy_id in tls_results['strategy_instance_id'].values:
                strategy_tls = tls_results[tls_results['strategy_instance_id'] == strategy_id]
                
                # Find best TLS performance
                best_tls_idx = strategy_tls['simulated_pnl'].idxmax()
                best_tls_row = strategy_tls.loc[best_tls_idx]
                
                # Create comparison
                comparison = ComparisonResult(
                    strategy_id=strategy_id,
                    baseline_result=baseline,
                    tls_best_sol=float(best_tls_row['simulated_pnl']),
                    tls_best_pct=float(best_tls_row.get('simulated_pnl_pct', 0)),
                    tls_best_params={
                        'tp': float(best_tls_row.get('tp_level', 0)),
                        'sl': float(best_tls_row.get('sl_level', 0)),
                        'activation': float(best_tls_row.get('tls_activation', 0)),
                        'trail': float(best_tls_row.get('tls_trail', 0))
                    },
                    improvement_sol=float(best_tls_row['simulated_pnl']) - baseline.baseline_sol,
                    improvement_pct=((float(best_tls_row['simulated_pnl']) - baseline.baseline_sol) / 
                                    abs(baseline.baseline_sol) * 100) if baseline.baseline_sol != 0 else 0,
                    recommendation="",
                    rationale=""
                )
                
                # Generate recommendation
                recommendation, rationale = self.generate_tls_recommendation(comparison)
                comparison.recommendation = recommendation
                comparison.rationale = rationale
                
                comparisons.append(comparison.to_dict())
            else:
                # No TLS results, just add baseline
                comparisons.append({
                    'strategy_id': strategy_id,
                    'baseline_sol': baseline.baseline_sol,
                    'baseline_pct': baseline.baseline_pct,
                    'optimal_tp': baseline.optimal_tp,
                    'optimal_sl': baseline.optimal_sl,
                    'confidence': baseline.confidence_score,
                    'recommendation': 'NO_TLS_DATA',
                    'rationale': 'No TLS simulation results available'
                })
                
        return pd.DataFrame(comparisons)