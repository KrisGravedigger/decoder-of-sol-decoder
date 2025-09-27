"""
Example usage of UnifiedBaselineManager
"""

import pandas as pd
import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from simulations.unified_baseline_manager import UnifiedBaselineManager


def example_usage():
    """Demonstrate UnifiedBaselineManager usage."""
    
    print("=" * 60)
    print("UnifiedBaselineManager Example Usage")
    print("=" * 60)
    
    # Initialize manager
    config = {
        'baseline_confidence': {
            'min_positions_full_confidence': 20,
            'variance_penalty_factor': 0.1
        },
        'baseline_validation': {
            'consistency_tolerance_sol': 0.01
        }
    }
    
    manager = UnifiedBaselineManager(config)
    
    # Load sample data (if available)
    range_test_file = "reporting/output/range_test_aggregated.csv"
    if os.path.exists(range_test_file):
        print(f"\nLoading real data from {range_test_file}")
        range_data = pd.read_csv(range_test_file)
        
        # Get unique strategies
        strategies = range_data['strategy_instance_id'].unique()[:3]  # First 3 for demo
        
        print(f"Found {len(range_data['strategy_instance_id'].unique())} strategies, analyzing first 3...")
        
        # Calculate baselines for each strategy
        print("\n" + "=" * 60)
        print("BASELINE CALCULATIONS")
        print("=" * 60)
        
        for strategy_id in strategies:
            baseline = manager.calculate_strategy_baseline(
                strategy_id,
                range_data[range_data['strategy_instance_id'] == strategy_id],
                metric='total_pnl'
            )
            
            print(f"\nStrategy: {strategy_id}")
            print(f"  Baseline SOL: {baseline.baseline_sol:.4f}")
            print(f"  Baseline %: {baseline.baseline_pct:.2f}%")
            print(f"  Optimal TP: {baseline.optimal_tp}")
            print(f"  Optimal SL: {baseline.optimal_sl}")
            print(f"  Positions: {baseline.position_count}")
            print(f"  Confidence: {baseline.confidence_score:.2f}")
            
    else:
        print("\nNo real data available, using synthetic example...")
        
        # Create synthetic data
        import numpy as np
        
        strategies = ['BidAsk_MEDIUM_5SOL', 'Spot_WIDE_10SOL']
        data_rows = []
        
        for strategy in strategies:
            for tp in [4, 6, 8]:
                for sl in [5, 10, 15]:
                    # Simulate some positions
                    n_positions = np.random.randint(5, 15)
                    total_pnl = np.random.uniform(-2, 5) * n_positions
                    
                    data_rows.append({
                        'strategy_instance_id': strategy,
                        'tp_level': tp,
                        'sl_level': sl,
                        'total_pnl': total_pnl,
                        'avg_pnl': total_pnl / n_positions,
                        'avg_pnl_pct': np.random.uniform(-10, 20),
                        'position_count': n_positions,
                        'win_rate': np.random.uniform(30, 80)
                    })
                    
        range_data = pd.DataFrame(data_rows)
        
        print("\nCalculating baselines for synthetic strategies...")
        
        for strategy in strategies:
            baseline = manager.calculate_strategy_baseline(
                strategy,
                range_data[range_data['strategy_instance_id'] == strategy],
                metric='total_pnl'
            )
            
            print(f"\nStrategy: {strategy}")
            print(f"  Baseline SOL: {baseline.baseline_sol:.4f}")
            print(f"  Optimal TP/SL: {baseline.optimal_tp}/{baseline.optimal_sl}")
            print(f"  Confidence: {baseline.confidence_score:.2f}")
            
    # Test validation
    print("\n" + "=" * 60)
    print("CONSISTENCY VALIDATION")
    print("=" * 60)
    
    validation_report = manager.validate_consistency(range_data, None)
    
    print(f"\nValidation Report:")
    print(f"  Is Consistent: {validation_report.is_consistent}")
    print(f"  Total Strategies: {validation_report.total_strategies}")
    print(f"  Consistent: {validation_report.consistent_strategies}")
    
    if validation_report.inconsistencies:
        print(f"  Inconsistencies Found: {len(validation_report.inconsistencies)}")
        for inc in validation_report.inconsistencies[:3]:  # Show first 3
            print(f"    - {inc['strategy_id']}: diff = {inc['difference']:.4f} SOL")
            
    # Show cache status
    print("\n" + "=" * 60)
    print("CACHE STATUS")
    print("=" * 60)
    
    cached_baselines = manager.get_all_baselines()
    print(f"\nCached baselines: {len(cached_baselines)}")
    
    for key, baseline in list(cached_baselines.items())[:3]:
        print(f"  {key}: {baseline.baseline_sol:.4f} SOL")
        
    print("\n" + "=" * 60)
    print("Example completed successfully!")
    print("=" * 60)
    

if __name__ == "__main__":
    example_usage()