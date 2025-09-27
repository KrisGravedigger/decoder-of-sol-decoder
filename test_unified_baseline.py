"""
Unit tests for UnifiedBaselineManager
"""

import unittest
import pandas as pd
import numpy as np
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulations.unified_baseline_manager import (
    UnifiedBaselineManager, BaselineResult, ComparisonResult, ValidationReport
)


class TestUnifiedBaselineManager(unittest.TestCase):
    """Test cases for UnifiedBaselineManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.manager = UnifiedBaselineManager()
        
        # Create sample data
        self.sample_range_data = pd.DataFrame({
            'strategy_instance_id': ['strategy_1'] * 9 + ['strategy_2'] * 9,
            'position_id': list(range(18)),
            'tp_level': [2, 2, 2, 4, 4, 4, 6, 6, 6] * 2,
            'sl_level': [5, 10, 15, 5, 10, 15, 5, 10, 15] * 2,
            'simulated_pnl': [1.0, 1.2, 0.8, 1.5, 1.8, 1.3, 1.1, 1.4, 1.6] + 
                           [0.5, 0.6, 0.4, 0.8, 0.9, 0.7, 0.6, 0.7, 0.8],
            'simulated_pnl_pct': [10, 12, 8, 15, 18, 13, 11, 14, 16] +
                                [5, 6, 4, 8, 9, 7, 6, 7, 8],
            'position_count': [1] * 18
        })
        
    def tearDown(self):
        """Clean up after tests."""
        self.manager.clear_cache()
        
    def test_calculate_strategy_baseline(self):
        """Test baseline calculation for a strategy."""
        result = self.manager.calculate_strategy_baseline(
            'strategy_1', 
            self.sample_range_data,
            metric='total_pnl'
        )
        
        # Check result structure
        self.assertIsInstance(result, BaselineResult)
        self.assertEqual(result.strategy_id, 'strategy_1')
        
        # Verify baseline is the max total_pnl
        expected_max = self.sample_range_data[
            self.sample_range_data['strategy_instance_id'] == 'strategy_1'
        ]['simulated_pnl'].max()
        
        # The baseline should be based on aggregated data
        self.assertGreater(result.baseline_sol, 0)
        self.assertEqual(result.optimal_tp, 4)  # TP=4, SL=10 has best performance
        self.assertEqual(result.optimal_sl, 10)
        
    def test_confidence_calculation(self):
        """Test confidence score calculation."""
        # Test with different position counts
        confidence_high = self.manager._calculate_confidence(25, 0.5)
        confidence_medium = self.manager._calculate_confidence(10, 1.0)
        confidence_low = self.manager._calculate_confidence(2, 2.0)
        
        # Verify confidence ordering
        self.assertGreater(confidence_high, confidence_medium)
        self.assertGreater(confidence_medium, confidence_low)
        
        # Verify bounds
        self.assertLessEqual(confidence_high, 1.0)
        self.assertGreaterEqual(confidence_low, 0.1)
        
    def test_cache_persistence(self):
        """Test that baselines are cached and persisted."""
        # Calculate baseline
        result1 = self.manager.calculate_strategy_baseline(
            'strategy_1',
            self.sample_range_data
        )
        
        # Should be cached
        cache_key = 'strategy_1_total_pnl'
        self.assertIn(cache_key, self.manager._baseline_cache)
        
        # Create new manager instance
        manager2 = UnifiedBaselineManager()
        
        # Should load from cache file
        self.assertIn(cache_key, manager2._baseline_cache)
        
    def test_validation_consistency(self):
        """Test consistency validation between modules."""
        # Create TLS results with matching baseline
        tls_data = self.sample_range_data.copy()
        tls_data['strategy_best_non_tls_pnl'] = 1.8  # Matches range test max
        
        report = self.manager.validate_consistency(
            self.sample_range_data,
            tls_data
        )
        
        self.assertIsInstance(report, ValidationReport)
        self.assertEqual(report.total_strategies, 2)
        
    def test_recommendation_generation(self):
        """Test TLS recommendation logic."""
        # Create baseline
        baseline = BaselineResult(
            strategy_id='test',
            baseline_sol=10.0,
            baseline_pct=20.0,
            optimal_tp=6,
            optimal_sl=10,
            position_count=15,
            confidence_score=0.8
        )
        
        # Test YES recommendation
        comparison_yes = ComparisonResult(
            strategy_id='test',
            baseline_result=baseline,
            tls_best_sol=11.0,
            tls_best_pct=22.0,
            tls_best_params={'tp': 8, 'sl': 12, 'activation': 4, 'trail': 2},
            improvement_sol=1.0,
            improvement_pct=10.0,
            recommendation="",
            rationale=""
        )
        
        rec, rationale = self.manager.generate_tls_recommendation(comparison_yes)
        self.assertEqual(rec, "YES")
        self.assertIn("improves performance", rationale)
        
        # Test NO recommendation
        comparison_no = ComparisonResult(
            strategy_id='test',
            baseline_result=baseline,
            tls_best_sol=9.5,
            tls_best_pct=19.0,
            tls_best_params={'tp': 8, 'sl': 12, 'activation': 4, 'trail': 2},
            improvement_sol=-0.5,
            improvement_pct=-5.0,
            recommendation="",
            rationale=""
        )
        
        rec, rationale = self.manager.generate_tls_recommendation(comparison_no)
        self.assertEqual(rec, "NO")
        self.assertIn("degrades performance", rationale)
        
    def test_empty_strategy_handling(self):
        """Test handling of strategies with no data."""
        empty_df = pd.DataFrame()
        result = self.manager.calculate_strategy_baseline(
            'empty_strategy',
            empty_df
        )
        
        self.assertEqual(result.baseline_sol, 0.0)
        self.assertEqual(result.confidence_score, 0.0)
        self.assertEqual(result.metadata.get('error'), 'No data available')
        

if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)