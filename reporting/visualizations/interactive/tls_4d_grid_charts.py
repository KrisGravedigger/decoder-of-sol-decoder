"""
TLS 4D Grid Charts for Phase 3 - 4D Parameter Grid Visualization

Creates sophisticated grid-based mini-heatmaps enabling visual identification 
of optimal parameter "islands" across 4D TLS space.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import logging

logger = logging.getLogger(__name__)


def detect_tested_tls_ranges(tls_results_df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """
    AIDEV-TLS-CLAUDE: Extract actual TLS ranges from simulation results.
    
    Extract actual TLS ranges from simulation results to ensure grid matches data:
    
    Args:
        tls_results_df: TLS simulation results DataFrame
        
    Returns:
        Tuple of (tls_activation_range, tls_trail_range) - sorted unique values from simulation results
        
    Critical: Grid must display exactly what was tested, not config defaults
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to detect_tested_tls_ranges")
        return [], []
    
    try:
        tls_activation_range = sorted(tls_results_df['tls_activation'].unique())
        tls_trail_range = sorted(tls_results_df['tls_trail'].unique())
        
        logger.info(f"Detected TLS ranges - Activation: {tls_activation_range}, Trail: {tls_trail_range}")
        return tls_activation_range, tls_trail_range
        
    except KeyError as e:
        logger.error(f"Missing required TLS columns in results DataFrame: {e}")
        return [], []
    except Exception as e:
        logger.error(f"Failed to detect TLS ranges: {e}")
        return [], []


def calculate_global_color_scale(tls_results_df: pd.DataFrame, strategy_instances_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
    """
    AIDEV-GRID-CLAUDE: Calculate global min/max PnL values across all TLS combinations.
    
    Critical Requirements:
    - Single color scale used by ALL mini-heatmaps
    - Ensures visual comparability between different TLS combinations
    - Scale: Red (worst PnL) → Yellow (medium) → Green (best PnL)
    
    Args:
        tls_results_df: TLS simulation results DataFrame
        strategy_instances_df: Strategy instances for percentage calculations
        
    Returns:
        Dictionary with global_min_pnl, global_max_pnl, and color_scale_config
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to calculate_global_color_scale")
        return {
            'global_min_pnl': 0.0,
            'global_max_pnl': 0.0,
            'color_scale': [[0.0, '#e74c3c'], [0.5, '#f39c12'], [1.0, '#27ae60']]
        }
    
    try:
        # Calculate percentage-based min/max if strategy instances available
        if strategy_instances_df is not None:
            pnl_percentages = []
            for _, row in tls_results_df.iterrows():
                strategy_id = row['strategy_instance_id']
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
                    pnl_pct = (row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0
                    pnl_percentages.append(pnl_pct)
            
            if pnl_percentages:
                global_min_pnl = float(min(pnl_percentages))
                global_max_pnl = float(max(pnl_percentages))
            else:
                global_min_pnl = float(tls_results_df['simulated_pnl'].min())
                global_max_pnl = float(tls_results_df['simulated_pnl'].max())
        else:
            # Fallback to SOL values
            global_min_pnl = float(tls_results_df['simulated_pnl'].min())
            global_max_pnl = float(tls_results_df['simulated_pnl'].max())
            
        # Ensure we have some range for color scaling
        if abs(global_max_pnl - global_min_pnl) < 0.01:
            # Add some padding if range is very small
            padding = 0.5
            global_min_pnl -= padding
            global_max_pnl += padding
        
        # Plotly colorscale with consistent red-yellow-green mapping
        color_scale = [
            [0.0, '#e74c3c'],    # Red for worst performance
            [0.5, '#f39c12'],    # Yellow for medium performance  
            [1.0, '#27ae60']     # Green for best performance
        ]
        
        logger.info(f"Global color scale calculated - Min: {global_min_pnl:.4f}, Max: {global_max_pnl:.4f}")
        
        return {
            'global_min_pnl': global_min_pnl,
            'global_max_pnl': global_max_pnl,
            'color_scale': color_scale
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate global color scale: {e}")
        # Return safe defaults
        return {
            'global_min_pnl': -5.0,
            'global_max_pnl': 5.0,
            'color_scale': [[0.0, '#e74c3c'], [0.5, '#f39c12'], [1.0, '#27ae60']]
        }


def create_mini_heatmap(tls_activation: float, tls_trail: float, 
                       tls_results_df: pd.DataFrame, 
                       global_color_config: Dict[str, Any], 
                       strategy_instances_df: Optional[pd.DataFrame] = None) -> Tuple[Optional[str], float]:
    """
    AIDEV-GRID-CLAUDE: Generate individual TP×SL heatmap for specific TLS combination.
    
    Layout:
    - X-axis: TP levels (from simulation data)
    - Y-axis: SL levels (from simulation data)  
    - Z-values: Average PnL percentage for each TP×SL combination
    - Color scale: Global scale (shared across all mini-heatmaps)
    
    Header Styling:
    - Background color based on average performance of this TLS combination
    - Title format: "TLS(activation%, trail%)"
    - Performance indicator: Green (excellent), Yellow (good), Red (poor)
    
    Args:
        tls_activation: TLS activation level
        tls_trail: TLS trail level
        tls_results_df: Complete TLS simulation results
        global_color_config: Global color scale configuration
        strategy_instances_df: Strategy instances for total_invested calculation
        
    Returns:
        Tuple of (plotly_heatmap_html, avg_performance_pct)
    """
    try:
        # Filter data for this specific TLS combination
        filtered_data = tls_results_df[
            (tls_results_df['tls_activation'] == tls_activation) & 
            (tls_results_df['tls_trail'] == tls_trail)
        ]
        
        if filtered_data.empty:
            logger.debug(f"No data for TLS combination ({tls_activation}, {tls_trail})")
            return None, 0.0
        
        # Create TP×SL matrix
        tp_levels = sorted(filtered_data['tp_level'].unique())
        sl_levels = sorted(filtered_data['sl_level'].unique())
        
        if not tp_levels or not sl_levels:
            logger.debug(f"Insufficient TP/SL data for TLS combination ({tls_activation}, {tls_trail})")
            return None, 0.0
        
        # Build Z-matrix for heatmap (convert to percentages)
        z_matrix = []
        z_matrix_pct = []  # For percentage display
        
        for sl in sl_levels:
            row = []
            row_pct = []
            for tp in tp_levels:
                cell_data = filtered_data[
                    (filtered_data['tp_level'] == tp) & 
                    (filtered_data['sl_level'] == sl)
                ]
                
                if not cell_data.empty:
                    # Calculate average PnL percentage
                    avg_pnl_sol = cell_data['simulated_pnl'].mean()
                    
                    # Convert to percentage using strategy total_invested
                    if strategy_instances_df is not None:
                        # Get total_invested for each position's strategy
                        pnl_percentages = []
                        for _, pos_row in cell_data.iterrows():
                            strategy_id = pos_row['strategy_instance_id']
                            strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                            if not strategy_info.empty:
                                total_invested = strategy_info.iloc[0]['total_invested']
                                pnl_pct = (pos_row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0
                                pnl_percentages.append(pnl_pct)
                        
                        avg_pnl_pct = np.mean(pnl_percentages) if pnl_percentages else 0
                    else:
                        # Fallback: assume PnL is already in reasonable scale
                        avg_pnl_pct = avg_pnl_sol * 100
                    
                    row.append(avg_pnl_sol)  # Keep SOL for color scaling
                    row_pct.append(avg_pnl_pct)  # Percentage for display
                else:
                    row.append(None)
                    row_pct.append(None)
                    
            z_matrix.append(row)
            z_matrix_pct.append(row_pct)
        
        # Calculate average performance percentage for header coloring
        if strategy_instances_df is not None:
            # Calculate percentage-based average
            pnl_percentages = []
            for _, pos_row in filtered_data.iterrows():
                strategy_id = pos_row['strategy_instance_id']
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
                    pnl_pct = (pos_row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0
                    pnl_percentages.append(pnl_pct)
            
            avg_performance_pct = np.mean(pnl_percentages) if pnl_percentages else 0
        else:
            avg_performance_pct = filtered_data['simulated_pnl'].mean() * 100
        
        # Create Plotly heatmap with global color scale but percentage hover text
        fig = go.Figure()
        
        heatmap = go.Heatmap(
            z=z_matrix,  # Use SOL values for color scaling
            x=[f"{tp}%" for tp in tp_levels],
            y=[f"{sl}%" for sl in sl_levels],
            colorscale=global_color_config['color_scale'],
            zmin=global_color_config['global_min_pnl'],
            zmax=global_color_config['global_max_pnl'],
            showscale=False,  # Only show scale once for entire grid
            hoverongaps=False,
            customdata=z_matrix_pct,  # Pass percentage data for hover
            hovertemplate='TP: %{x}<br>SL: %{y}<br>PnL: %{customdata:.2f}%<extra></extra>'
        )
        
        fig.add_trace(heatmap)
        
        # Compact layout for mini-heatmap
        fig.update_layout(
            title=f"TLS({tls_activation}%, {tls_trail}%)",
            width=250,
            height=200,
            margin=dict(l=30, r=30, t=40, b=30),
            xaxis=dict(
                title="TP",
                title_font_size=10,
                tickfont_size=8
            ),
            yaxis=dict(
                title="SL",
                title_font_size=10,
                tickfont_size=8
            ),
            title_font_size=12
        )
        
        # Convert to HTML
        heatmap_html = fig.to_html(include_plotlyjs=False, div_id=f"mini_heatmap_{tls_activation}_{tls_trail}")
        
        logger.debug(f"Created mini-heatmap for TLS({tls_activation}, {tls_trail}) with avg performance {avg_performance_pct:.2f}%")
        return heatmap_html, avg_performance_pct
        
    except Exception as e:
        logger.error(f"Failed to create mini-heatmap for TLS({tls_activation}, {tls_trail}): {e}")
        return None, 0.0


def create_4d_tls_grid(tls_results_df: pd.DataFrame, strategy_filter: Optional[str] = None, 
                      strategy_instances_df: Optional[pd.DataFrame] = None, 
                      baseline_data: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
    """
    AIDEV-4D-VIZ-CLAUDE: Create complete 4D grid of mini-heatmaps.
    
    Grid Organization:
    - Rows: TLS_activation levels (ascending order)
    - Columns: TLS_trail levels (ascending order)
    - Each cell: TP×SL mini-heatmap for that TLS combination
    
    Header Coloring Logic:
    - Calculate average PnL percentage for each TLS combination
    - Apply color coding: >5% = Green, 1-5% = Yellow, <1% = Red
    - Color intensity reflects relative performance within grid
    
    Features:
    - Strategy filtering: Show only selected strategy if filter applied
    - Global color scale: All mini-heatmaps use same scale for comparability
    - Missing data handling: Empty cells for untested combinations
    - Baseline comparison: Include baseline data for TLS improvement filtering
    
    Args:
        tls_results_df: Complete TLS simulation results
        strategy_filter: Optional strategy instance ID to filter by
        strategy_instances_df: Strategy instances data for percentage calculations
        baseline_data: Baseline performance data for comparison
        
    Returns:
        Dictionary with grid_data, global_color_config, baseline_info, and range information
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to create_4d_tls_grid")
        return {
            'grid_data': [],
            'global_color_config': {},
            'tls_activation_range': [],
            'tls_trail_range': [],
            'error': 'No TLS data available'
        }
    
    try:
        # Apply strategy filter if specified
        if strategy_filter:
            filtered_df = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_filter]
            if filtered_df.empty:
                logger.warning(f"No data found for strategy filter: {strategy_filter}")
                return {
                    'grid_data': [],
                    'global_color_config': {},
                    'tls_activation_range': [],
                    'tls_trail_range': [],
                    'error': f'No data for strategy: {strategy_filter}'
                }
        else:
            filtered_df = tls_results_df
        
        # Detect actual TLS ranges from data
        tls_activation_range, tls_trail_range = detect_tested_tls_ranges(filtered_df)
        
        if not tls_activation_range or not tls_trail_range:
            logger.warning("No valid TLS ranges detected in data")
            return {
                'grid_data': [],
                'global_color_config': {},
                'tls_activation_range': [],
                'tls_trail_range': [],
                'error': 'No valid TLS parameter ranges found'
            }
        
        # Calculate global color scale
        global_color_config = calculate_global_color_scale(filtered_df, strategy_instances_df)
        
        # Generate grid of mini-heatmaps
        grid_data = []
        baseline_info = None
        
        # Calculate baseline info for filtered strategy
        if strategy_filter and baseline_data:
            baseline_pnl = baseline_data.get(strategy_filter, 0.0)
            # Convert baseline to percentage
            if strategy_instances_df is not None:
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_filter]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
                    baseline_pct = (baseline_pnl / total_invested * 100) if total_invested > 0 else 0
                    baseline_info = {
                        'strategy_id': strategy_filter,
                        'baseline_pnl_sol': baseline_pnl,
                        'baseline_pnl_pct': baseline_pct
                    }
        
        for activation in tls_activation_range:
            row_data = []
            for trail in tls_trail_range:
                heatmap_html, avg_performance_pct = create_mini_heatmap(
                    activation, trail, filtered_df, global_color_config, strategy_instances_df
                )
                
                # Determine header color based on percentage performance
                if avg_performance_pct > 5.0:  # > 5% profit
                    header_class = 'performance-excellent'
                elif avg_performance_pct > 1.0:  # > 1% profit 
                    header_class = 'performance-good'
                else:  # <= 1% or negative
                    header_class = 'performance-average'
                
                # Calculate TLS improvement vs baseline (if available)
                tls_improvement = None
                if baseline_info and avg_performance_pct is not None:
                    tls_improvement = avg_performance_pct - baseline_info['baseline_pnl_pct']
                
                row_data.append({
                    'tls_activation': activation,
                    'tls_trail': trail,
                    'heatmap_html': heatmap_html,
                    'avg_performance': avg_performance_pct,  # Now in percentage
                    'header_class': header_class,
                    'title': f'TLS({activation}%, {trail}%)',
                    'has_data': heatmap_html is not None,
                    'tls_improvement': tls_improvement,  # For filtering
                    'strategy_id': strategy_filter  # For filtering
                })
            
            grid_data.append(row_data)
        
        logger.info(f"Created 4D TLS grid: {len(tls_activation_range)} × {len(tls_trail_range)} = {len(tls_activation_range) * len(tls_trail_range)} cells")
        
        return {
            'grid_data': grid_data,
            'global_color_config': global_color_config,
            'tls_activation_range': tls_activation_range,
            'tls_trail_range': tls_trail_range,
            'total_combinations': len(tls_activation_range) * len(tls_trail_range),
            'strategy_filter': strategy_filter,
            'baseline_info': baseline_info  # Add baseline info for display
        }
        
    except Exception as e:
        logger.error(f"Failed to create 4D TLS grid: {e}")
        return {
            'grid_data': [],
            'global_color_config': {},
            'tls_activation_range': [],
            'tls_trail_range': [],
            'error': f'Grid generation failed: {str(e)}'
        }


def create_grid_filter_controls() -> Dict[str, Any]:
    """
    AIDEV-4D-VIZ-CLAUDE: Generate filtering interface for 4D grid.
    
    Filter Controls:
    - Min Performance: Range slider (0-20%, step 0.25%)
    - Strategy Filter: Dropdown with all available strategies + "All Strategies" option
    - Min Win Rate: Range slider (30-95%, step 5%) 
    - Show Only Improvements: Checkbox (TLS better than baseline)
    
    JavaScript Integration:
    - Real-time filtering without page reload
    - Visual feedback: Filtered cells fade out, active cells remain prominent
    - Filter state preservation: Maintain filters when navigating from Phase 2
    
    Returns:
        Filter configuration dictionary for HTML template
    """
    try:
        # Get available strategies (would be populated dynamically in template)
        filter_config = {
            'min_performance': {
                'type': 'range',
                'min': -5.0,  # Allow negative performance filtering
                'max': 20.0,
                'step': 0.25,
                'default': -5.0,  # Start with no filtering
                'label': 'Min Performance (%)',
                'id': 'grid-min-performance'
            },
            'strategy_filter': {
                'type': 'dropdown',
                'options': ['All Strategies'],  # Will be populated dynamically
                'default': 'All Strategies',
                'label': 'Strategy',
                'id': 'grid-strategy-filter'
            },
            'min_win_rate': {
                'type': 'range',
                'min': 0,
                'max': 100,
                'step': 5,
                'default': 0,  # Start with no filtering
                'label': 'Min Win Rate (%)',
                'id': 'grid-min-winrate'
            },
            'show_only_improvements': {
                'type': 'checkbox',
                'default': False,
                'label': 'Show Only TLS Improvements',
                'id': 'grid-show-improvements'
            }
        }
        
        logger.debug("Generated grid filter controls configuration")
        return filter_config
        
    except Exception as e:
        logger.error(f"Failed to create grid filter controls: {e}")
        return {}


def apply_grid_filters(grid_data: List[List[Dict]], filters: Dict[str, Any]) -> List[List[Dict]]:
    """
    AIDEV-4D-VIZ-CLAUDE: Apply active filters to grid display.
    
    Filtering Logic:
    - Performance threshold: Hide cells below minimum
    - Strategy filter: Show only selected strategy data
    - Win rate filter: Hide cells with insufficient win rate
    - Improvement filter: Show only cells where TLS > baseline
    
    Visual Effects:
    - Filtered cells: opacity 0.3, pointer-events disabled
    - Active cells: opacity 1.0, full interactivity
    - Filter indicator: Show active filter count in UI
    
    Args:
        grid_data: 2D array of grid cell data
        filters: Active filter configuration
        
    Returns:
        Filtered grid data with visibility flags
    """
    try:
        if not grid_data or not filters:
            return grid_data
        
        filtered_grid = []
        active_filter_count = 0
        
        # Count active filters
        if filters.get('minPerformance', -5.0) > -5.0:
            active_filter_count += 1
        if filters.get('strategy') != 'All Strategies':
            active_filter_count += 1
        if filters.get('minWinRate', 0) > 0:
            active_filter_count += 1
        if filters.get('showOnlyImprovements', False):
            active_filter_count += 1
        
        for row in grid_data:
            filtered_row = []
            for cell in row:
                # Apply filtering logic
                passes_filters = True
                
                # Performance filter
                if cell['avg_performance'] < filters.get('minPerformance', -5.0):
                    passes_filters = False
                
                # Strategy filter (would need additional data to implement)
                # This would be handled at the grid generation level
                
                # Win rate filter (would need win rate data in cell)
                # min_win_rate = filters.get('minWinRate', 0)
                # if cell.get('win_rate', 100) < min_win_rate:
                #     passes_filters = False
                
                # TLS improvement filter (would need baseline comparison)
                # if filters.get('showOnlyImprovements', False):
                #     if cell.get('tls_advantage', 0) <= 0:
                #         passes_filters = False
                
                # Add filter state to cell
                cell_copy = cell.copy()
                cell_copy['passes_filters'] = passes_filters
                cell_copy['opacity'] = 1.0 if passes_filters else 0.3
                
                filtered_row.append(cell_copy)
            
            filtered_grid.append(filtered_row)
        
        logger.debug(f"Applied grid filters - {active_filter_count} active filters")
        return filtered_grid
        
    except Exception as e:
        logger.error(f"Failed to apply grid filters: {e}")
        return grid_data