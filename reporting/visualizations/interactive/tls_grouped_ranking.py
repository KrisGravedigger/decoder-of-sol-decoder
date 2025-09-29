"""
TLS 4D Grouped Ranking for Phase 4 - 4D Parameter Grouping & Expandable Tables

Creates sophisticated grouping of similar TLS parameter combinations with 
expandable ranking table interface for comprehensive optimization analysis.
"""

import plotly.graph_objects as go
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)

# AIDEV-INTEGRATE-CLAUDE: Import UnifiedBaselineManager for consistent baselines
try:
    from simulations.unified_baseline_manager import UnifiedBaselineManager
    UNIFIED_MANAGER_AVAILABLE = True
except ImportError:
    UNIFIED_MANAGER_AVAILABLE = False
    logger.debug("UnifiedBaselineManager not available, using legacy baseline calculation")


def calculate_strategy_roi_percentage(total_pnl_sol: float, total_invested_sol: float) -> float:
    """
    Standard ROI metric for strategy comparison.
    AIDEV-NOTE-CLAUDE: Unified ROI calculation - single source of truth
    """
    return (total_pnl_sol / total_invested_sol * 100) if total_invested_sol > 0 else 0.0


def group_4d_combinations(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float], 
                         strategy_instances_df: Optional[pd.DataFrame] = None,
                         max_combined_distance: float = 2.0) -> List[Dict[str, Any]]:
    """
    AIDEV-TLS-CLAUDE: Group similar 4D TLS parameter combinations by strategy with combined tolerance.
    
    FIXED: Group best combinations from ALL STRATEGIES, not within single strategy.
    Each group represents the best parameter combination from different strategies.
    
    Grouping Algorithm:
    - Combined distance: |tp1-tp2| + |sl1-sl2| + |tls_act1-tls_act2| + |tls_trail1-tls_trail2| ≤ 2 points
    - Representative selection: Highest PnL combination becomes group representative
    - Strategy diversity: Best combinations from different strategies
    - Output limits: Top 20 groups ranked by representative PnL, max 10 similar combinations per group
    
    Args:
        tls_results_df: TLS simulation results DataFrame
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl
        strategy_instances_df: Strategy instances for percentage calculations
        max_combined_distance: Maximum combined parameter distance for grouping (default: 4.0)
        
    Returns:
        List of grouped combinations with metrics and sub-combinations
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to group_4d_combinations")
        return []
    
    try:
        # Step 1: Find best combination per strategy
        strategy_best_combos = {}
        
        for strategy_id in [str(x) for x in tls_results_df['strategy_instance_id'].unique()]:
            strategy_data = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
            
            # Get investment data for this strategy
            total_invested = 1.0  # Default fallback
            position_count = 1    # Default fallback
            avg_invested = 1.0    # Default fallback
            
            if strategy_instances_df is not None:
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
                    position_count = strategy_info.iloc[0].get('analyzed_position_count', 1)
                    # AIDEV-NOTE-CLAUDE: Calculate average investment per position
                    avg_invested = total_invested / position_count if position_count > 0 else total_invested
            
            # Find best combination for this strategy
            best_row = strategy_data.loc[strategy_data['simulated_pnl'].idxmax()]
            baseline_pnl = baseline_data.get(strategy_id, 0.0)
            
            # Calculate percentage-based metrics using averages
            # AIDEV-NOTE-CLAUDE: Use average-based ROI calculation for consistency
            # For best combination, we have total PnL, so divide by position count to get average
            avg_pnl = best_row['simulated_pnl'] / position_count if position_count > 0 else best_row['simulated_pnl']
            avg_baseline_pnl = baseline_pnl / position_count if position_count > 0 else baseline_pnl
            
            pnl_pct = calculate_strategy_roi_percentage(avg_pnl, avg_invested)
            baseline_pnl_pct = calculate_strategy_roi_percentage(avg_baseline_pnl, avg_invested)
            
            # TLS effectiveness: (Representative_PnL - Strategy_Baseline_PnL) / Strategy_Baseline_PnL × 100
            tls_effectiveness = ((pnl_pct - baseline_pnl_pct) / abs(baseline_pnl_pct) * 100) if baseline_pnl_pct != 0 else 0
            
            # Calculate win rate for this strategy's best combination
            combo_data = strategy_data[
                (strategy_data['tp_level'] == best_row['tp_level']) &
                (strategy_data['sl_level'] == best_row['sl_level']) &
                (strategy_data['tls_activation'] == best_row['tls_activation']) &
                (strategy_data['tls_trail'] == best_row['tls_trail'])
            ]
            
            win_positions = 0
            for _, pos_row in combo_data.iterrows():
                pos_pnl_pct = (pos_row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0
                if pos_pnl_pct > 0:
                    win_positions += 1
            
            win_rate = (win_positions / len(combo_data) * 100) if len(combo_data) > 0 else 0
            
            strategy_best_combos[strategy_id] = {
                'strategy_id': strategy_id,
                'tp_level': best_row['tp_level'],
                'sl_level': best_row['sl_level'],
                'tls_activation': best_row['tls_activation'],
                'tls_trail': best_row['tls_trail'],
                'avg_pnl_pct': pnl_pct,  # Average PnL % per position
                'total_pnl_sol': best_row['simulated_pnl'],  # Total PnL in SOL
                'avg_pnl_sol': avg_pnl,  # Average PnL per position in SOL
                'baseline_pnl_pct': baseline_pnl_pct,
                'tls_effectiveness': tls_effectiveness,
                'win_rate': win_rate,
                'group_size': len(combo_data),
                'total_invested': total_invested,
                'position_count': position_count,
                'avg_invested': avg_invested
            }
        
        # Step 2: Sort by performance and create groups
        sorted_combos = sorted(strategy_best_combos.values(), key=lambda x: x['avg_pnl_pct'], reverse=True)
        
        groups = []
        used_strategies = set()
        
        for main_combo in sorted_combos:
            if main_combo['strategy_id'] in used_strategies:
                continue
            
            # Mark this strategy as used immediately to prevent duplicates
            used_strategies.add(main_combo['strategy_id'])
                
            # Create new group with this combination as representative
            group = {
                'group_id': f"group_{len(groups) + 1}",
                'representative': main_combo,
                'similar_combinations': [],
                'group_metrics': {}
            }
            
             # Find similar combinations within the SAME strategy from original TLS data
            similar_count = 0
            
            # Get all combinations for this strategy from the original data
            strategy_data = tls_results_df[tls_results_df['strategy_instance_id'] == main_combo['strategy_id']]
            
            # Get unique parameter combinations for this strategy, sorted by performance
            strategy_unique_combos = strategy_data.groupby(['tp_level', 'sl_level', 'tls_activation', 'tls_trail']).agg({
                'simulated_pnl': 'sum',  # Total PnL for this combination
                'strategy_instance_id': 'count'  # Number of positions
            }).reset_index()
            strategy_unique_combos.rename(columns={'strategy_instance_id': 'position_count'}, inplace=True)
            strategy_unique_combos = strategy_unique_combos.sort_values('simulated_pnl', ascending=False)
            
            # Find similar combinations within distance threshold, limited to top 10
            total_similar_available = 0
            similar_count = 0
            
            for _, combo_row in strategy_unique_combos.iterrows():
                # Skip if it's the exact same combination (representative)
                if (combo_row['tp_level'] == main_combo['tp_level'] and
                    combo_row['sl_level'] == main_combo['sl_level'] and
                    combo_row['tls_activation'] == main_combo['tls_activation'] and
                    combo_row['tls_trail'] == main_combo['tls_trail']):
                    continue
                
                # Calculate combined distance (using 2.0 threshold)
                distance = (abs(main_combo['tp_level'] - combo_row['tp_level']) +
                           abs(main_combo['sl_level'] - combo_row['sl_level']) +
                           abs(main_combo['tls_activation'] - combo_row['tls_activation']) +
                           abs(main_combo['tls_trail'] - combo_row['tls_trail']))
                
                if distance <= 2.0:
                    total_similar_available += 1
                    
                    # Only add to display list if within top 10 limit
                    if similar_count < 10:
                        # AIDEV-NOTE-CLAUDE: Use average-based calculation for similar combinations
                        avg_combo_pnl = combo_row['simulated_pnl'] / position_count if position_count > 0 else combo_row['simulated_pnl']
                        
                        similar_combo = {
                            'strategy_id': main_combo['strategy_id'],
                            'tp_level': combo_row['tp_level'],
                            'sl_level': combo_row['sl_level'],
                            'tls_activation': combo_row['tls_activation'],
                            'tls_trail': combo_row['tls_trail'],
                            'avg_pnl_pct': calculate_strategy_roi_percentage(avg_combo_pnl, avg_invested),
                            'total_pnl_sol': combo_row['simulated_pnl'],
                            'baseline_pnl_pct': baseline_pnl_pct,
                            'tls_effectiveness': 0,  # Simplified for grouping
                            'win_rate': 0,  # Simplified for grouping
                            'group_size': combo_row['position_count'],
                            'total_invested': total_invested
                        }
                        
                        group['similar_combinations'].append(similar_combo)
                        similar_count += 1
            
            # Calculate group-level metrics
            all_group_combos = [group['representative']] + group['similar_combinations']
            
            group_pnl_values = [combo['avg_pnl_pct'] for combo in all_group_combos]
            total_positions = sum(combo['group_size'] for combo in all_group_combos)
            
            # Group metrics calculations
            group['group_metrics'] = {
                'avg_pnl': np.mean(group_pnl_values),
                'group_size': total_positions,
                'tls_effectiveness': group['representative']['tls_effectiveness'],
                'win_rate': group['representative']['win_rate'],
                'baseline_pnl_pct': group['representative']['baseline_pnl_pct'],
                'num_combinations': len(all_group_combos),
                'actual_similar_count': total_similar_available,  # Show total available, not just displayed
                'parameter_spread': {
                    'tp_range': [min(c['tp_level'] for c in all_group_combos), 
                                max(c['tp_level'] for c in all_group_combos)],
                    'sl_range': [min(c['sl_level'] for c in all_group_combos), 
                                max(c['sl_level'] for c in all_group_combos)],
                    'tls_act_range': [min(c['tls_activation'] for c in all_group_combos), 
                                     max(c['tls_activation'] for c in all_group_combos)],
                    'tls_trail_range': [min(c['tls_trail'] for c in all_group_combos), 
                                       max(c['tls_trail'] for c in all_group_combos)]
                }
            }
            
            groups.append(group)
            
            # Stop at top 20 groups
            if len(groups) >= 20:
                break
        
        logger.info(f"Created {len(groups)} strategy-based parameter groups from {len(strategy_best_combos)} strategies")
        return groups
        
    except Exception as e:
        logger.error(f"Failed to group 4D combinations: {e}")
        return []


def prepare_grouped_ranking_data(grouped_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    AIDEV-4D-VIZ-CLAUDE: Prepares structured data for the expandable ranking table.
    
    This function separates data preparation from HTML rendering. It sorts the data,
    calculates display-specific values (like CSS classes), and returns a list of
    dictionaries ready for a Jinja2 template.
    
    Args:
        grouped_data: List of grouped combinations from group_4d_combinations.
        
    Returns:
        A list of dictionaries, where each dictionary represents a group
        with its representative and similar combinations, structured for rendering.
    """
    if not grouped_data:
        logger.warning("No grouped TLS data provided to prepare_grouped_ranking_data")
        return []
    
    try:
        # Sort groups by representative PnL for final display
        sorted_groups = sorted(grouped_data, key=lambda x: x['representative']['avg_pnl_pct'], reverse=True)
        
        prepared_table_data = []
        
        for rank, group in enumerate(sorted_groups, 1):
            rep = group['representative']
            metrics = group['group_metrics']
            
            # Prepare representative data with new metrics
            # AIDEV-NOTE-CLAUDE: Using average-based metrics for consistency
            representative_data = {
                'strategy_id': rep['strategy_id'],
                'tp_level': rep['tp_level'],
                'sl_level': rep['sl_level'],
                'tls_activation': rep['tls_activation'],
                'tls_trail': rep['tls_trail'],
                'avg_pnl_pct': rep.get('avg_pnl_pct', 0),  # Average PnL %
                'total_pnl_sol': rep.get('total_pnl_sol', 0),  # Total PnL in SOL
                'avg_pnl_sol': rep.get('avg_pnl_sol', 0),  # Average PnL per position in SOL
                'pnl_class': 'positive' if rep.get('avg_pnl_pct', 0) >= 0 else 'negative',
            }
            
            # Prepare group metrics data
            group_metrics_data = {
                'avg_pnl': metrics['avg_pnl'],
                'avg_pnl_class': 'positive' if metrics['avg_pnl'] >= 0 else 'negative',
                'group_size': metrics['group_size'],
                'tls_effectiveness': metrics['tls_effectiveness'],
                'effectiveness_class': 'positive' if metrics['tls_effectiveness'] > 0 else 'negative',
                'win_rate': metrics['win_rate'],
                'baseline_pnl_pct': metrics['baseline_pnl_pct'],
                'baseline_class': 'positive' if metrics['baseline_pnl_pct'] >= 0 else 'negative',
                'actual_similar_count': metrics['actual_similar_count'],
            }
            
            # Prepare similar combinations data
            similar_combos_data = []
            if group['similar_combinations']:
                sorted_similar = sorted(group['similar_combinations'], 
                                      key=lambda x: x['avg_pnl_pct'], reverse=True)
                
                for i, similar_combo in enumerate(sorted_similar):
                    similar_combos_data.append({
                        'sub_rank': f"{rank}.{i+1}",
                        'strategy_id': similar_combo['strategy_id'],
                        'tp_level': similar_combo['tp_level'],
                        'sl_level': similar_combo['sl_level'],
                        'tls_activation': similar_combo['tls_activation'],
                        'tls_trail': similar_combo['tls_trail'],
                        'avg_pnl_pct': similar_combo['avg_pnl_pct'],
                        'total_pnl_sol': similar_combo['total_pnl_sol'],
                        'pnl_class': 'positive' if similar_combo['avg_pnl_pct'] >= 0 else 'negative',
                        'group_size': similar_combo['group_size'],
                        'tls_effectiveness': similar_combo['tls_effectiveness'],
                        'effectiveness_class': 'positive' if similar_combo['tls_effectiveness'] > 0 else 'negative',
                        'win_rate': similar_combo['win_rate'],
                        'baseline_pnl_pct': similar_combo['baseline_pnl_pct'],
                    })

            prepared_table_data.append({
                'group_id': group['group_id'],
                'rank': rank,
                'representative': representative_data,
                'group_metrics': group_metrics_data,
                'similar_combinations': similar_combos_data
            })
        
        logger.info(f"Prepared structured data for {len(prepared_table_data)} ranking groups")
        return prepared_table_data
        
    except Exception as e:
        logger.error(f"Failed to prepare grouped ranking data: {e}")
        return []

def create_group_summary_statistics(grouped_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create summary statistics for grouped parameter analysis.
    
    Args:
        grouped_data: List of grouped combinations
        
    Returns:
        Dictionary with summary statistics and insights
    """
    if not grouped_data:
        return {}
    
    try:
        # Overall statistics
        total_groups = len(grouped_data)
        total_combinations = sum(g['group_metrics']['num_combinations'] for g in grouped_data)
        total_positions = sum(g['group_metrics']['group_size'] for g in grouped_data)
        
        # Effectiveness analysis
        effective_groups = len([g for g in grouped_data if g['group_metrics']['tls_effectiveness'] > 0])
        effectiveness_rate = (effective_groups / total_groups * 100) if total_groups > 0 else 0
        
        # Best performing groups
        best_group = max(grouped_data, key=lambda x: x['representative']['representative_pnl'])
        worst_group = min(grouped_data, key=lambda x: x['representative']['representative_pnl'])
        
        # Parameter distribution analysis
        all_tls_activations = [g['representative']['tls_activation'] for g in grouped_data]
        all_tls_trails = [g['representative']['tls_trail'] for g in grouped_data]
        
        summary = {
            'total_groups': total_groups,
            'total_combinations': total_combinations,
            'total_positions': total_positions,
            'effective_groups': effective_groups,
            'effectiveness_rate': effectiveness_rate,
            'best_group': {
                'rank': 1,
                'parameters': f"TP:{best_group['representative']['tp_level']}% SL:{best_group['representative']['sl_level']}% TLS:{best_group['representative']['tls_activation']}/{best_group['representative']['tls_trail']}%",
                'pnl': best_group['representative']['representative_pnl'],
                'effectiveness': best_group['group_metrics']['tls_effectiveness']
            },
            'parameter_insights': {
                'most_common_tls_activation': max(set(all_tls_activations), key=all_tls_activations.count),
                'most_common_tls_trail': max(set(all_tls_trails), key=all_tls_trails.count),
                'activation_range': f"{min(all_tls_activations)}-{max(all_tls_activations)}%",
                'trail_range': f"{min(all_tls_trails)}-{max(all_tls_trails)}%"
            }
        }
        
        return summary
        
    except Exception as e:
        logger.error(f"Failed to create group summary statistics: {e}")
        return {}