"""
Generates interactive charts related to strategy performance analysis.

Includes:
- Professional strategy performance heatmap (multi-metric).
- Strategy average PnL summary bar chart.
"""
import logging
import os
import re
from typing import Dict, Any

import pandas as pd
import plotly.graph_objects as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

logger = logging.getLogger(__name__)


def create_professional_strategy_heatmap(portfolio_analysis: Dict[str, Any], config: Dict[str, Any]) -> str:
    """Create professional interactive strategy performance heatmap with YAML filters."""
    try:
        positions_df = portfolio_analysis['raw_data']['positions_df']
        
        if positions_df.empty:
            return "<p>No positions data available for professional strategy heatmap</p>"
            
        if os.path.exists("strategy_instances.csv"):
            try:
                strategy_instances_df = pd.read_csv("strategy_instances.csv")
                return _create_strategy_instances_professional_heatmap(strategy_instances_df, config)
            except Exception as e:
                logger.warning(f"Failed to use strategy_instances.csv: {e}, using positions fallback")
                return _create_positions_professional_heatmap(positions_df, config)
        else:
            return _create_positions_professional_heatmap(positions_df, config)
            
    except Exception as e:
        logger.error(f"Failed to create professional strategy heatmap: {e}", exc_info=True)
        return f"<p>Error creating professional strategy heatmap: {str(e)}</p>"


def _create_strategy_instances_professional_heatmap(strategy_instances_df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """Create professional heatmap from strategy_instances.csv with YAML filters."""
    filters = config.get('visualization', {}).get('filters', {})
    min_occurrences = filters.get('min_strategy_occurrences', 2)
    top_strategies = filters.get('top_strategies_only', 10)
    
    strategy_instances_df = strategy_instances_df[
        strategy_instances_df['position_count'] >= min_occurrences
    ]
    
    if strategy_instances_df.empty:
        return f"<p>No strategies with ≥{min_occurrences} positions found</p>"
        
    if 'avg_pnl_percent' in strategy_instances_df.columns:
        strategy_instances_df = strategy_instances_df.sort_values(
            'avg_pnl_percent', ascending=False
        ).head(top_strategies)
    else:
        strategy_instances_df = strategy_instances_df.head(top_strategies)
        
    strategy_instances_df['strategy_display_name'] = (
        strategy_instances_df['strategy'] + ' ' + 
        strategy_instances_df['step_size'] + ' ' +
        strategy_instances_df['investment_sol'].astype(str) + 'SOL' +
        ' (' + strategy_instances_df['position_count'].astype(str) + ')'
    )
    
    metrics = ['avg_pnl_percent', 'win_rate']
    if 'sharpe_ratio' in strategy_instances_df.columns:
        metrics.append('sharpe_ratio')
    
    metric_labels = ['Avg PnL %', 'Win Rate', 'Sharpe Ratio'][:len(metrics)]
    
    fig = make_subplots(
        rows=1, cols=len(metrics),
        subplot_titles=metric_labels,
        horizontal_spacing=0.15
    )
    
    for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
        if metric not in strategy_instances_df.columns:
            continue
            
        values = strategy_instances_df[metric].values
        strategy_names = strategy_instances_df['strategy_display_name'].values
        
        display_values = values * 100 if metric == 'win_rate' else values
        
        heatmap = go.Heatmap(
            z=display_values.reshape(-1, 1),
            y=strategy_names,
            x=[label],
            colorscale='RdYlGn',
            zmid=0 if metric == 'avg_pnl_percent' else display_values.mean(),
            text=[[f'{val:.1f}%' if metric == 'win_rate' else f'{val:.2f}'] for val in display_values],
            texttemplate='%{text}',
            textfont=dict(size=10),
            hovertemplate=f'<b>{label}</b><br>Strategy: %{{y}}<br>Value: %{{z:.2f}}<extra></extra>',
            showscale=(i == len(metrics)-1)
        )
        
        fig.add_trace(heatmap, row=1, col=i+1)
    
    fig.update_layout(
        height=max(600, len(strategy_names) * 35),
        title=dict(
            text=f'Professional Strategy Performance Heatmap (Top {len(strategy_instances_df)} Strategies)',
            font=dict(size=20, color='#2E3440'),
            x=0.5
        ),
        template='plotly_white'
    )
    
    fig.update_yaxes(tickfont=dict(size=9))
    
    return pyo.plot(fig, output_type='div', include_plotlyjs=False)


def _create_positions_professional_heatmap(positions_df: pd.DataFrame, config: Dict[str, Any]) -> str:
    """Professional fallback heatmap based on positions data."""
    try:
        strategy_groups = positions_df.groupby(['strategy', 'step_size']).agg({
            'pnl_sol': ['sum', 'mean', 'count'],
            'investment_sol': 'sum'
        }).round(3)
        
        strategy_groups.columns = ['total_pnl', 'avg_pnl', 'position_count', 'total_investment']
        strategy_groups['win_rate'] = positions_df.groupby(['strategy', 'step_size']).apply(
            lambda x: (x['pnl_sol'] > 0).mean()
        )
        
        filters = config.get('visualization', {}).get('filters', {})
        min_occurrences = filters.get('min_strategy_occurrences', 2)
        
        strategy_groups = strategy_groups[strategy_groups['position_count'] >= min_occurrences]
        
        if strategy_groups.empty:
            return f"<p>No strategies with ≥{min_occurrences} positions found</p>"
            
        pivot_data = strategy_groups.reset_index().pivot(
            index='strategy', columns='step_size', values='avg_pnl'
        ).fillna(0)
        
        fig = go.Figure(data=go.Heatmap(
            z=pivot_data.values,
            x=pivot_data.columns,
            y=pivot_data.index,
            colorscale='RdYlGn',
            zmid=0,
            text=pivot_data.values,
            texttemplate='%{text:.3f}',
            textfont=dict(size=10),
            hovertemplate='<b>Strategy Performance</b><br>Strategy: %{y}<br>Step Size: %{x}<br>Avg PnL: %{z:.3f} SOL<extra></extra>'
        ))
        
        fig.update_layout(
            height=500,
            title=dict(
                text='Professional Strategy Performance Heatmap (Positions-Based)',
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            xaxis_title='Step Size',
            yaxis_title='Strategy',
            template='plotly_white'
        )
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create positions-based professional heatmap: {e}")
        return f"<p>Error creating fallback professional heatmap: {str(e)}</p>"


def create_strategy_avg_pnl_summary(config: Dict[str, Any], strategy_instances_path: str = "strategy_instances.csv") -> str:
    """Create AVG PnL summary chart replacing the current heatmap."""
    try:
        if not os.path.exists(strategy_instances_path):
            return "<div class='skipped'>strategy_instances.csv not found. Run log extraction and instance detection.</div>"
            
        strategy_instances_df = pd.read_csv(strategy_instances_path)
        
        filters = config.get('visualization', {}).get('filters', {})
        min_occurrences = filters.get('min_strategy_occurrences', 2)
        top_strategies = filters.get('top_strategies_only', 10)
        
        strategy_instances_df = strategy_instances_df[
            strategy_instances_df['position_count'] >= min_occurrences
        ]
        
        if strategy_instances_df.empty:
            return f"<div class='skipped'>No strategies with ≥{min_occurrences} positions found.</div>"
        
        if 'avg_pnl_percent' in strategy_instances_df.columns:
            strategy_instances_df = strategy_instances_df.sort_values(
                'avg_pnl_percent', ascending=True
            ).tail(top_strategies)
        else:
            strategy_instances_df = strategy_instances_df.head(top_strategies)
        
        strategy_instances_df['strategy_display_name'] = (
            strategy_instances_df['strategy'] + ' ' + 
            strategy_instances_df['step_size'] + ' ' +
            strategy_instances_df['investment_sol'].astype(str) + 'SOL' +
            ' (' + strategy_instances_df['position_count'].astype(str) + ')'
        )
        
        colors = ['#27ae60' if x >= 0 else '#c0392b' for x in strategy_instances_df['avg_pnl_percent']]
        
        fig = go.Figure()
        
        fig.add_trace(
            go.Bar(
                y=strategy_instances_df['strategy_display_name'],
                x=strategy_instances_df['avg_pnl_percent'],
                orientation='h',
                marker_color=colors,
                hovertemplate=(
                    '<b>%{y}</b><br>'
                    'Avg PnL: %{x:.2f}%<br>'
                    '<extra></extra>'
                )
            )
        )
        
        fig.add_vline(x=0, line_dash="dash", line_color="black", opacity=0.5)
        
        fig.update_layout(
            height=max(500, len(strategy_instances_df) * 40),
            title=dict(
                text=f'Strategy Performance Summary - AVG PnL (Top {len(strategy_instances_df)} Strategies)',
                font=dict(size=20, color='#2E3440'),
                x=0.5
            ),
            xaxis_title='Average PnL (%)',
            yaxis_title='Strategy (Position Count)',
            template='plotly_white',
            showlegend=False,
            margin=dict(l=250)
        )
        
        fig.update_yaxes(tickfont=dict(size=10))
        
        return pyo.plot(fig, output_type='div', include_plotlyjs=False)
        
    except Exception as e:
        logger.error(f"Failed to create strategy AVG PnL summary: {e}", exc_info=True)
        return f"<p>Error creating strategy AVG PnL summary: {str(e)}</p>"