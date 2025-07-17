"""
Plotting functions for the Strategy Performance Heatmap.
Includes primary implementation from strategy_instances.csv and a
fallback using positions data directly.
"""
import logging
import os
import re
import pandas as pd
import numpy as np
import seaborn as sns
from typing import Dict, Any

logger = logging.getLogger(__name__)

def _extract_step_size(strategy_str):
    if pd.isna(strategy_str): return 'UNKNOWN'
    match = re.search(r'\b(MEDIUM|WIDE|NARROW|SIXTYNINE)\b', str(strategy_str), re.IGNORECASE)
    if match: return match.group(1).upper()
    return 'MEDIUM'

def _extract_strategy_name(strategy_str):
    if pd.isna(strategy_str): return 'Unknown'
    strategy_clean = str(strategy_str)
    for step_size in ['MEDIUM', 'WIDE', 'NARROW', 'SIXTYNINE']:
        strategy_clean = strategy_clean.replace(step_size, '').strip()
    strategy_clean = ' '.join(strategy_clean.split()).rstrip('() -')
    return strategy_clean if strategy_clean else 'Unknown'

def plot_heatmap_from_instances(fig, axes, analysis_result: Dict[str, Any], config: Dict):
    """Primary heatmap plotter, using strategy_instances.csv data."""
    strategy_instances_df = pd.read_csv("strategy_instances.csv")
    positions_df = analysis_result['raw_data']['positions_df']

    filters = config.get('visualization', {}).get('filters', {})
    min_occurrences = filters.get('min_strategy_occurrences', 3)
    top_strategies = filters.get('top_strategies_only', 10)

    strategy_instances_df = strategy_instances_df[strategy_instances_df['position_count'] >= min_occurrences]
    
    if strategy_instances_df.empty:
        raise ValueError(f'No strategies with ≥{min_occurrences} positions')

    strategy_instances_df['step_size'] = strategy_instances_df['strategy'].apply(_extract_step_size)
    strategy_instances_df['strategy_clean'] = strategy_instances_df['strategy'].apply(_extract_strategy_name)

    sort_metric = 'performance_score' if 'performance_score' in strategy_instances_df.columns else 'avg_pnl_percent'
    strategy_instances_df = strategy_instances_df.sort_values(sort_metric, ascending=False).head(top_strategies)

    # Calculate Sharpe ratio for each strategy instance
    for idx, inst in strategy_instances_df.iterrows():
        instance_positions = positions_df[positions_df['strategy_instance_id'] == inst['strategy_instance_id']]
        if len(instance_positions) > 1:
            daily_pnl = instance_positions.groupby(instance_positions['close_timestamp'].dt.date)['pnl_sol'].sum()
            if len(daily_pnl) > 1 and daily_pnl.std() > 0:
                sharpe = (daily_pnl.mean() / daily_pnl.std()) * np.sqrt(365) # Simplified Sharpe
                strategy_instances_df.loc[idx, 'sharpe_ratio'] = sharpe
            else:
                strategy_instances_df.loc[idx, 'sharpe_ratio'] = 0.0
        else:
            strategy_instances_df.loc[idx, 'sharpe_ratio'] = 0.0
    
    # AIDEV-NOTE-GEMINI: CORRECTED KEYERROR. Changed 'initial_investment' to 'investment_sol'
    # to align with the project's standardized column names.
    strategy_instances_df['strategy_name'] = (
        strategy_instances_df['strategy_clean'] + ' ' + strategy_instances_df['step_size'] + ' ' +
        strategy_instances_df['investment_sol'].astype(str) + 'SOL (' +
        strategy_instances_df['position_count'].astype(str) + ')'
    )

    total_instances = len(pd.read_csv("strategy_instances.csv"))
    filter_info = f"Showing {len(strategy_instances_df)} of {total_instances} strategies (min {min_occurrences} positions)"
    fig.suptitle('Strategy Performance Heatmap (Top Strategies)', fontsize=16, fontweight='bold')
    fig.text(0.5, 0.95, filter_info, ha='center', va='center', fontsize=12, style='italic', color='gray')

    metrics = ['avg_pnl_percent', 'win_rate', 'sharpe_ratio']
    metric_labels = ['Avg PnL %', 'Win Rate', 'Sharpe Ratio']
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        if metric not in strategy_instances_df.columns: continue
        heatmap_data = strategy_instances_df.set_index('strategy_name')[[metric]]

        # AIDEV-TODO-CLAUDE: Revisit Win Rate display. Brute-force normalization applied as formatting attempts failed.
        # The value is divided by 100 to be displayed as a decimal (e.g., 0.85).
        if metric == 'win_rate':
            heatmap_data[metric] = heatmap_data[metric] / 100.0

        sns.heatmap(heatmap_data, annot=True, fmt='.2f', cmap='RdYlGn', center=0 if 'pnl' in metric else None, ax=axes[i], cbar_kws={'shrink': 0.8})
        axes[i].set_title(label, fontsize=12, fontweight='bold')
        axes[i].set_xlabel('')
        axes[i].set_ylabel('Strategy Instance' if i == 0 else '')
        axes[i].tick_params(axis='y', rotation=0)

def plot_heatmap_from_positions(fig, axes, positions_df: pd.DataFrame, config: Dict):
    """Fallback heatmap plotter, using positions_df data directly."""
    logger.info("Creating positions-based strategy heatmap as fallback")
    
    positions_df = positions_df.copy()
    strategy_parts = positions_df['strategy_raw'].apply(lambda s: (_extract_strategy_name(s), _extract_step_size(s)))
    positions_df['strategy_parsed'] = [parts[0] for parts in strategy_parts]
    positions_df['step_size_parsed'] = [parts[1] for parts in strategy_parts]

    strategy_groups = positions_df.groupby(['strategy_parsed', 'step_size_parsed']).agg(
        total_pnl=('pnl_sol', 'sum'),
        avg_pnl=('pnl_sol', 'mean'),
        position_count=('pnl_sol', 'count'),
        total_investment=('investment_sol', 'sum')
    ).round(3)
    strategy_groups['win_rate'] = positions_df.groupby(['strategy_parsed', 'step_size_parsed']).apply(lambda x: (x['pnl_sol'] > 0).mean())
    strategy_groups['roi_percent'] = (strategy_groups['total_pnl'] / strategy_groups['total_investment'].replace(0, 1) * 100)
    
    min_occurrences = config.get('visualization', {}).get('filters', {}).get('min_strategy_occurrences', 3)
    strategy_groups = strategy_groups[strategy_groups['position_count'] >= min_occurrences]

    if strategy_groups.empty:
        raise ValueError(f'No strategies with ≥{min_occurrences} positions in fallback')

    filter_info = f"Using {strategy_groups['position_count'].sum()} of {len(positions_df)} positions (min {min_occurrences} per group)"
    fig.suptitle('Strategy Performance Heatmap (Positions-Based Fallback)', fontsize=16, fontweight='bold')
    fig.text(0.5, 0.94, filter_info, ha='center', va='center', fontsize=12, style='italic', color='gray')

    metrics = ['avg_pnl', 'win_rate', 'roi_percent']
    metric_labels = ['Avg PnL (SOL)', 'Win Rate (%)', 'ROI %']
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        # AIDEV-NOTE-CLAUDE: Use conditional formatting to ensure consistency with the primary heatmap.
        formatter = '.0f' if metric == 'win_rate' else '.2f'

        pivot_data = strategy_groups.reset_index().pivot(index='strategy_parsed', columns='step_size_parsed', values=metric).fillna(0)
        sns.heatmap(pivot_data, annot=True, fmt=formatter, cmap='RdYlGn', center=0 if 'pnl' in metric else None, ax=axes[i], cbar_kws={'shrink': 0.8})
        axes[i].set_title(label, fontsize=12, fontweight='bold')
        axes[i].set_xlabel('Step Size', fontsize=10)
        axes[i].set_ylabel('Strategy' if i == 0 else '')