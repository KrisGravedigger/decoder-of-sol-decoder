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


def group_4d_combinations(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float], 
                         strategy_instances_df: Optional[pd.DataFrame] = None,
                         max_combined_distance: float = 4.0) -> List[Dict[str, Any]]:
    """
    AIDEV-TLS-CLAUDE: Group similar 4D TLS parameter combinations by strategy with combined tolerance.
    
    FIXED: Group best combinations from ALL STRATEGIES, not within single strategy.
    Each group represents the best parameter combination from different strategies.
    
    Grouping Algorithm:
    - Combined distance: |tp1-tp2| + |sl1-sl2| + |tls_act1-tls_act2| + |tls_trail1-tls_trail2| ≤ 4 points
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
            
            # Get total_invested for this strategy
            total_invested = 1.0  # Default fallback
            if strategy_instances_df is not None:
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
            
            # Find best combination for this strategy
            best_row = strategy_data.loc[strategy_data['simulated_pnl'].idxmax()]
            baseline_pnl = baseline_data.get(strategy_id, 0.0)
            
            # Calculate percentage-based metrics
            pnl_pct = (best_row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0
            baseline_pnl_pct = (baseline_pnl / total_invested * 100) if total_invested > 0 else 0
            
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
                'representative_pnl': pnl_pct,
                'representative_raw_pnl': best_row['simulated_pnl'],
                'baseline_pnl': baseline_pnl_pct,
                'tls_effectiveness': tls_effectiveness,
                'win_rate': win_rate,
                'group_size': len(combo_data),
                'total_invested': total_invested
            }
        
        # Step 2: Sort by performance and create groups
        sorted_combos = sorted(strategy_best_combos.values(), key=lambda x: x['representative_raw_pnl'], reverse=True)
        
        groups = []
        used_strategies = set()
        
        for main_combo in sorted_combos:
            if main_combo['strategy_id'] in used_strategies:
                continue
                
            # Create new group with this combination as representative
            group = {
                'group_id': f"group_{len(groups) + 1}",
                'representative': main_combo,
                'similar_combinations': [],
                'group_metrics': {}
            }
            
            used_strategies.add(main_combo['strategy_id'])
            
            # Find similar combinations from other strategies within distance threshold
            similar_count = 0
            for other_combo in sorted_combos:
                if (other_combo['strategy_id'] in used_strategies or 
                    similar_count >= 10):  # Max 10 similar combinations
                    continue
                
                # Calculate combined distance
                distance = (abs(main_combo['tp_level'] - other_combo['tp_level']) +
                           abs(main_combo['sl_level'] - other_combo['sl_level']) +
                           abs(main_combo['tls_activation'] - other_combo['tls_activation']) +
                           abs(main_combo['tls_trail'] - other_combo['tls_trail']))
                
                if distance <= max_combined_distance:
                    group['similar_combinations'].append(other_combo)
                    used_strategies.add(other_combo['strategy_id'])
                    similar_count += 1
            
            # Calculate group-level metrics
            all_group_combos = [group['representative']] + group['similar_combinations']
            
            group_pnl_values = [combo['representative_pnl'] for combo in all_group_combos]
            total_positions = sum(combo['group_size'] for combo in all_group_combos)
            
            # Group metrics calculations
            group['group_metrics'] = {
                'avg_pnl': np.mean(group_pnl_values),
                'group_size': total_positions,
                'tls_effectiveness': group['representative']['tls_effectiveness'],
                'win_rate': group['representative']['win_rate'],
                'baseline_pnl': group['representative']['baseline_pnl'],
                'num_combinations': len(all_group_combos),
                'actual_similar_count': len(group['similar_combinations']),  # FIXED: Actual count, not max
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


def create_grouped_ranking_table(grouped_data: List[Dict[str, Any]]) -> str:
    """
    AIDEV-4D-VIZ-CLAUDE: Create expandable table interface for grouped parameter combinations.
    
    Table Structure:
    - Main table shows group representatives with expand (+) buttons
    - Sub-rows show similar combinations per group, sorted by PnL descending
    - Color coding: Green for positive TLS effectiveness, red for negative
    
    Args:
        grouped_data: List of grouped combinations with metrics
        
    Returns:
        HTML string of expandable table
    """
    if not grouped_data:
        return "<p>No grouped TLS data available for ranking table</p>"
    
    try:
        # Sort groups by representative PnL for final display
        sorted_groups = sorted(grouped_data, key=lambda x: x['representative']['representative_pnl'], reverse=True)
        
        table_html = """
        <div class="grouped-ranking-table-container">
            <div class="table-header">
                <h4>🏆 Top TLS Parameter Groups - Grouped by Similarity (Max 4-Point Distance)</h4>
                <p class="table-description">
                    Groups show best representative combination with expandable similar alternatives. 
                    Click (+) to expand group details.
                </p>
            </div>
            
            <table class="table table-striped table-hover" id="grouped_ranking_table">
                <thead>
                    <tr>
                        <th style="width: 40px;"></th>
                        <th>Rank</th>
                        <th>Strategy</th>
                        <th>Representative Parameters</th>
                        <th>Rep. PnL (%)</th>
                        <th>Avg Group PnL (%)</th>
                        <th>Group Size</th>
                        <th>TLS Effectiveness (%)</th>
                        <th>Win Rate (%)</th>
                        <th>Baseline PnL (%)</th>
                        <th>Similar Combos</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for rank, group in enumerate(sorted_groups, 1):
            rep = group['representative']
            metrics = group['group_metrics']
            
            # Color coding for TLS effectiveness
            effectiveness_class = 'positive' if metrics['tls_effectiveness'] > 0 else 'negative'
            
            # Color coding for PnL values
            rep_pnl_class = 'positive' if rep['representative_pnl'] >= 0 else 'negative'
            avg_pnl_class = 'positive' if metrics['avg_pnl'] >= 0 else 'negative'
            baseline_class = 'positive' if metrics['baseline_pnl'] >= 0 else 'negative'
            
            # Representative row
            table_html += f"""
                <tr class="group-main-row" data-group-id="{group['group_id']}" data-expanded="false">
                    <td>
                        <button class="btn btn-sm btn-outline-secondary expand-btn" 
                                onclick="toggleGroup('{group['group_id']}')" 
                                title="Expand group details">
                            <span class="expand-icon">+</span>
                        </button>
                    </td>
                    <td><strong>{rank}</strong></td>
                    <td><small>{rep['strategy_id']}</small></td>
                    <td>
                        <div class="parameter-display">
                            <span class="param-group">TP: {rep['tp_level']}%</span>
                            <span class="param-group">SL: {rep['sl_level']}%</span>
                            <span class="param-group">TLS Act: {rep['tls_activation']}%</span>
                            <span class="param-group">Trail: {rep['tls_trail']}%</span>
                        </div>
                    </td>
                    <td class="{rep_pnl_class}"><strong>{rep['representative_pnl']:.2f}%</strong></td>
                    <td class="{avg_pnl_class}">{metrics['avg_pnl']:.2f}%</td>
                    <td>{metrics['group_size']}</td>
                    <td class="{effectiveness_class}"><strong>{metrics['tls_effectiveness']:+.1f}%</strong></td>
                    <td>{metrics['win_rate']:.1f}%</td>
                    <td class="{baseline_class}">{metrics['baseline_pnl']:.2f}%</td>
                    <td>{metrics['actual_similar_count']}</td>
                </tr>
            """
            
            # Sub-rows for similar combinations (initially hidden)
            if group['similar_combinations']:
                sorted_similar = sorted(group['similar_combinations'], 
                                      key=lambda x: x['representative_pnl'], reverse=True)
                
                for i, similar_combo in enumerate(sorted_similar):
                    similar_pnl_class = 'positive' if similar_combo['representative_pnl'] >= 0 else 'negative'
                    similar_effectiveness_class = 'positive' if similar_combo['tls_effectiveness'] > 0 else 'negative'
                    
                    table_html += f"""
                        <tr class="group-sub-row" data-group-id="{group['group_id']}" style="display: none;">
                            <td></td>
                            <td class="sub-rank">{rank}.{i+1}</td>
                            <td><small>{similar_combo['strategy_id']}</small></td>
                            <td class="sub-params">
                                <div class="parameter-display similar-params">
                                    <span class="param-group">TP: {similar_combo['tp_level']}%</span>
                                    <span class="param-group">SL: {similar_combo['sl_level']}%</span>
                                    <span class="param-group">TLS Act: {similar_combo['tls_activation']}%</span>
                                    <span class="param-group">Trail: {similar_combo['tls_trail']}%</span>
                                </div>
                            </td>
                            <td class="{similar_pnl_class}">{similar_combo['representative_pnl']:.2f}%</td>
                            <td class="text-muted">{similar_combo['representative_pnl']:.2f}%</td>
                            <td class="text-muted">{similar_combo['group_size']}</td>
                            <td class="{similar_effectiveness_class}">{similar_combo['tls_effectiveness']:+.1f}%</td>
                            <td class="text-muted">{similar_combo['win_rate']:.1f}%</td>
                            <td class="text-muted">{similar_combo['baseline_pnl']:.2f}%</td>
                            <td class="text-muted">-</td>
                        </tr>
                    """
        
        table_html += """
                </tbody>
            </table>
        </div>
        
        <style>
        .grouped-ranking-table-container {
            margin: 20px 0;
        }
        
        .parameter-display {
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        .param-group {
            display: inline-block;
            margin-right: 8px;
            padding: 2px 6px;
            background-color: #f8f9fa;
            border-radius: 3px;
            border: 1px solid #dee2e6;
        }
        
        .similar-params .param-group {
            background-color: #e9ecef;
            font-size: 0.85em;
        }
        
        .group-main-row {
            font-weight: bold;
            border-left: 3px solid #007bff;
        }
        
        .group-sub-row {
            background-color: #f8f9fa;
            font-size: 0.9em;
            border-left: 3px solid #28a745;
        }
        
        .sub-rank {
            color: #6c757d;
            font-style: italic;
        }
        
        .expand-btn {
            border: none;
            background: none;
            font-weight: bold;
            cursor: pointer;
            transition: transform 0.3s ease;
        }
        
        .expand-btn:hover {
            background-color: #f8f9fa;
        }
        
        .expand-btn.expanded {
            transform: rotate(45deg);
        }
        
        .positive {
            color: #28a745;
            font-weight: bold;
        }
        
        .negative {
            color: #dc3545;
            font-weight: bold;
        }
        
        .table-description {
            color: #6c757d;
            margin-bottom: 15px;
            font-style: italic;
        }
        </style>
        """
        
        logger.info(f"Generated grouped ranking table with {len(sorted_groups)} groups")
        return table_html
        
    except Exception as e:
        logger.error(f"Failed to create grouped ranking table: {e}")
        return f"<p>Error generating grouped ranking table: {e}</p>"


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