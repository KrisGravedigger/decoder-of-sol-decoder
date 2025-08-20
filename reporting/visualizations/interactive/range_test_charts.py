"""
Range Test Charts for TP/SL Optimizer Phase 4A

Creates interactive heatmaps for TP/SL parameter optimization.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List
import numpy as np


def create_range_test_heatmap(aggregated_df: pd.DataFrame, strategy_id: str, 
                            metric: str = 'total_pnl') -> str:
    """
    Create interactive heatmap for a single strategy's TP/SL grid results.
    
    Args:
        aggregated_df: Aggregated results DataFrame
        strategy_id: Strategy instance ID to plot
        metric: Metric to use for heatmap color
        
    Returns:
        HTML string of the plotly chart
    """
    # Filter for specific strategy
    strategy_data = aggregated_df[aggregated_df['strategy_instance_id'] == strategy_id]
    
    if strategy_data.empty:
        return "<p>No data available for this strategy</p>"
        
    # Pivot data for heatmap
    pivot_data = strategy_data.pivot(
        index='tp_level',
        columns='sl_level', 
        values=metric
    )
    
    # Create hover text with additional metrics
    win_rate_pivot = strategy_data.pivot(index='tp_level', columns='sl_level', values='win_rate')
    tp_rate_pivot = strategy_data.pivot(index='tp_level', columns='sl_level', values='tp_rate')
    position_counts = strategy_data.pivot(index='tp_level', columns='sl_level', values='position_count')
    
    hover_text = []
    for i, tp in enumerate(pivot_data.index):
        row_text = []
        for j, sl in enumerate(pivot_data.columns):
            val = pivot_data.iloc[i, j]
            win_rate = win_rate_pivot.iloc[i, j] if not pd.isna(win_rate_pivot.iloc[i, j]) else 0
            tp_rate = tp_rate_pivot.iloc[i, j] if not pd.isna(tp_rate_pivot.iloc[i, j]) else 0
            pos_count = position_counts.iloc[i, j] if not pd.isna(position_counts.iloc[i, j]) else 0
            
            text = f"TP: {tp}%, SL: {sl}%<br>"
            text += f"{metric}: {val:.3f}<br>"
            text += f"Win Rate: {win_rate:.1f}% (TP: {tp_rate:.1f}%)<br>"
            text += f"Positions: {int(pos_count)}"
            row_text.append(text)
        hover_text.append(row_text)
        
    # Create heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_data.values,
        x=[f"{sl}%" for sl in pivot_data.columns],
        y=[f"{tp}%" for tp in pivot_data.index],
        text=hover_text,
        hovertemplate='%{text}<extra></extra>',
        colorscale='RdYlGn',
        colorbar=dict(title=metric.replace('_', ' ').title())
    ))
    
    # Update layout
    fig.update_layout(
        title=f"TP/SL Optimization Heatmap - {strategy_id}",
        xaxis_title="Stop Loss (%)",
        yaxis_title="Take Profit (%)",
        height=500,
        template="plotly_white"
    )
    
    # Add annotation for optimal point
    max_val = pivot_data.max().max()
    max_pos = pivot_data.stack().idxmax()
    fig.add_annotation(
        x=f"{max_pos[1]}%",
        y=f"{max_pos[0]}%",
        text="★",
        showarrow=False,
        font=dict(size=20, color="red")
    )
    
    return fig.to_html(include_plotlyjs=False, div_id=f"heatmap_{strategy_id}")


def create_optimal_settings_table(aggregated_df: pd.DataFrame, 
                                metric: str = 'total_pnl',
                                top_n: int = 10) -> str:
    """
    Create a summary table of optimal TP/SL settings per strategy.
    
    Args:
        aggregated_df: Aggregated results DataFrame
        metric: Metric to optimize for
        top_n: Number of top strategies to show
        
    Returns:
        HTML table string
    """
    # Find optimal settings for each strategy
    optimal_rows = []
    
    for strategy_id in aggregated_df['strategy_instance_id'].unique():
        strategy_data = aggregated_df[aggregated_df['strategy_instance_id'] == strategy_id]
        
        # Find row with maximum metric value
        optimal_idx = strategy_data[metric].idxmax()
        optimal_row = strategy_data.loc[optimal_idx]
        
        optimal_rows.append({
            'Strategy': strategy_id,
            'Optimal TP': f"{optimal_row['tp_level']}%",
            'Optimal SL': f"{optimal_row['sl_level']}%", 
            metric.replace('_', ' ').title(): f"{optimal_row[metric]:.3f}",
            'Win Rate': f"{optimal_row['win_rate']:.1f}% (TP: {optimal_row['tp_rate']:.1f}%)",
            'Positions': int(optimal_row['position_count'])
        })
        
    # Convert to DataFrame and sort
    optimal_df = pd.DataFrame(optimal_rows)
    optimal_df = optimal_df.sort_values(metric.replace('_', ' ').title(), ascending=False).head(top_n)
    
    # Create HTML table
    table_html = optimal_df.to_html(
        index=False,
        classes='table table-striped table-hover',
        table_id='optimal_settings_table'
    )
    
    return table_html


def create_strategy_comparison_chart(aggregated_df: pd.DataFrame,
                                   metric: str = 'total_pnl') -> str:
    """
    Create a bar chart comparing optimal performance across strategies.
    
    Args:
        aggregated_df: Aggregated results DataFrame
        metric: Metric to compare
        
    Returns:
        HTML string of the plotly chart
    """
    # Find optimal metric value for each strategy
    optimal_values = []
    
    for strategy_id in aggregated_df['strategy_instance_id'].unique():
        strategy_data = aggregated_df[aggregated_df['strategy_instance_id'] == strategy_id]
        max_value = strategy_data[metric].max()
        
        optimal_values.append({
            'strategy': strategy_id,
            'value': max_value
        })
        
    # Sort and take top strategies
    optimal_df = pd.DataFrame(optimal_values)
    optimal_df = optimal_df.sort_values('value', ascending=False).head(15)
    
    # Create bar chart
    fig = go.Figure(data=[
        go.Bar(
            x=optimal_df['strategy'],
            y=optimal_df['value'],
            text=[f"{v:.3f}" for v in optimal_df['value']],
            textposition='auto',
            marker_color='lightblue'
        )
    ])
    
    fig.update_layout(
        title=f"Optimal {metric.replace('_', ' ').title()} by Strategy",
        xaxis_title="Strategy Instance",
        yaxis_title=metric.replace('_', ' ').title(),
        xaxis_tickangle=-45,
        height=400,
        template="plotly_white"
    )
    
    return fig.to_html(include_plotlyjs=False, div_id="strategy_comparison")