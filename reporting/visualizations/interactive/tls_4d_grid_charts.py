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
        tls_activation_range = sorted([float(x) for x in tls_results_df['tls_activation'].unique()])
        tls_trail_range = sorted([float(x) for x in tls_results_df['tls_trail'].unique()])
        
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
    AIDEV-FIX-CLAUDE: Calculate a DIVERGING global min/max PnL scale centered at 0.
    
    Critical Requirements:
    - Single color scale used by ALL mini-heatmaps for comparability.
    - Scale is centered at 0: Red (negative) -> Yellow (zero) -> Green (positive).
    - This enhances visual contrast for small but significant PnL changes.
    
    Args:
        tls_results_df: TLS simulation results DataFrame
        strategy_instances_df: Strategy instances for percentage calculations
        
    Returns:
        Dictionary with symmetric min/max PnL and a diverging color scale.
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to calculate_global_color_scale")
        return {
            'global_min_pnl': -1.0,
            'global_max_pnl': 1.0,
            'color_scale': [[0.0, '#e74c3c'], [0.5, '#f39c12'], [1.0, '#27ae60']]
        }
    
    try:
        pnl_percentages = []
        if strategy_instances_df is not None and not strategy_instances_df.empty:
            # Merge to efficiently get total_invested for all results
            merged_df = pd.merge(tls_results_df, strategy_instances_df[['strategy_instance_id', 'total_invested']], on='strategy_instance_id', how='left')
            merged_df['total_invested'] = merged_df['total_invested'].fillna(1.0) # Avoid division by zero
            valid_investment = merged_df['total_invested'] > 0
            pnl_percentages = (merged_df.loc[valid_investment, 'simulated_pnl'] / merged_df.loc[valid_investment, 'total_invested'] * 100).tolist()
        
        if not pnl_percentages:
            # Fallback if strategy instances are not available or no valid investments
            pnl_percentages = (tls_results_df['simulated_pnl'] * 100).tolist()

        if not pnl_percentages:
            # Final fallback for empty data
             return {'global_min_pnl': -1.0, 'global_max_pnl': 1.0, 'color_scale': [[0.0, '#e74c3c'], [0.5, '#f39c12'], [1.0, '#27ae60']]}

        # AIDEV-FIX-CLAUDE: Logic for diverging scale
        global_min_pnl = float(min(pnl_percentages))
        global_max_pnl = float(max(pnl_percentages))
        
        # Determine the maximum absolute value to make the scale symmetric around 0
        max_abs_val = max(abs(global_min_pnl), abs(global_max_pnl))
        if max_abs_val < 0.5: # Ensure a minimum range for better visuals
            max_abs_val = 0.5

        symmetric_min = -max_abs_val
        symmetric_max = max_abs_val
        
        # AIDEV-FIX-GEMINI: Define a more vibrant 5-point diverging colorscale
        # This makes near-zero values more distinct and improves overall readability.
        color_scale = [
            [0.0,  '#d73027'],  # Dark Red
            [0.4,  '#fc8d59'],  # Light Red/Orange
            [0.5,  '#fee08b'],  # Saturated Yellow (for zero)
            [0.6,  '#91cf60'],  # Light Green
            [1.0,  '#1a9850']   # Dark Green
        ]
        
        logger.info(f"Diverging global color scale calculated - Range: [{symmetric_min:.2f}%, {symmetric_max:.2f}%]")
        
        return {
            'global_min_pnl': symmetric_min,
            'global_max_pnl': symmetric_max,
            'color_scale': color_scale
        }
        
    except Exception as e:
        logger.error(f"Failed to calculate global color scale: {e}", exc_info=True)
        # Return safe defaults
        return {
            'global_min_pnl': -5.0,
            'global_max_pnl': 5.0,
            'color_scale': [[0.0, '#e74c3c'], [0.5, '#fef9e7'], [1.0, '#27ae60']]
        }


def create_mini_heatmap(tls_activation: float, tls_trail: float,
                       tls_results_df: pd.DataFrame,
                       global_color_config: Dict[str, Any],
                       strategy_instances_df: Optional[pd.DataFrame] = None) -> Tuple[Optional[str], float]:
    """
    AIDEV-FIX-2-CLAUDE: Generate individual TP×SL heatmap with corrected logic.
    - FIX 1: 'Best PnL' is now the max PnL from within this specific heatmap's data.
    - FIX 2: Heatmap `z` values are now correctly passed as percentages to match the global color scale.
    - FIX 3: Figure height and margins are adjusted to prevent label cropping.
    """
    try:
        filtered_data = tls_results_df[
            (tls_results_df['tls_activation'] == tls_activation) &
            (tls_results_df['tls_trail'] == tls_trail)
        ]
        
        if filtered_data.empty:
            return None, 0.0
        
        tp_levels = sorted(filtered_data['tp_level'].unique())
        sl_levels = sorted(filtered_data['sl_level'].unique())
        
        if not tp_levels or not sl_levels:
            return None, 0.0

        # Create the Z-matrix with PnL percentages for both coloring and hover info.
        z_matrix_pct = []
        for sl in sl_levels:
            row_pct = []
            for tp in tp_levels:
                cell_data = filtered_data[
                    (filtered_data['tp_level'] == tp) &
                    (filtered_data['sl_level'] == sl)
                ]
                
                if not cell_data.empty:
                    # Calculate average PnL percentage for this specific TP/SL cell
                    pnl_percentages = []
                    if strategy_instances_df is not None:
                        merged_cell_data = pd.merge(cell_data, strategy_instances_df[['strategy_instance_id', 'total_invested']], on='strategy_instance_id', how='left')
                        merged_cell_data['total_invested'] = merged_cell_data['total_invested'].fillna(1.0).replace(0, 1.0)
                        pnl_percentages = (merged_cell_data['simulated_pnl'] / merged_cell_data['total_invested'] * 100).tolist()
                    
                    avg_pnl_pct = np.mean(pnl_percentages) if pnl_percentages else 0
                    row_pct.append(avg_pnl_pct)
                else:
                    row_pct.append(None)
            z_matrix_pct.append(row_pct)

        # AIDEV-FIX-1: Calculate 'best_performance_pct' as the maximum value within this specific z_matrix.
        # This ensures each frame shows its own local best PnL.
        best_performance_pct = np.nanmax(z_matrix_pct) if np.any(z_matrix_pct) else 0.0

        # AIDEV-FIX-2: Use the z_matrix_pct for the heatmap's `z` value.
        # This aligns the data unit (percentage) with the global color scale unit (percentage), fixing the uniform color bug.
        fig = go.Figure(data=go.Heatmap(
            z=z_matrix_pct,
            x=[f"{tp}%" for tp in tp_levels],
            y=[f"{sl}%" for sl in sl_levels],
            colorscale=global_color_config['color_scale'],
            zmin=global_color_config['global_min_pnl'],
            zmax=global_color_config['global_max_pnl'],
            showscale=False,
            hoverongaps=False,
            hovertemplate='TP: %{x}<br>SL: %{y}<br>PnL: %{z:.2f}%<extra></extra>'
        ))

        # AIDEV-FIX-GEMINI: Further adjust layout to guarantee axis label visibility.
        fig.update_layout(
            title=f"TLS({tls_activation}%, {tls_trail}%)",
            height=240,  # Slightly more vertical space
            margin=dict(l=35, r=10, t=40, b=60),  # Significantly larger bottom margin for labels
            xaxis=dict(title="TP", title_font_size=10, tickfont_size=8),
            yaxis=dict(title="SL", title_font_size=10, tickfont_size=8),
            title_font_size=12
        )
        
        heatmap_html = fig.to_html(include_plotlyjs=False, full_html=False, div_id=f"mini_heatmap_{tls_activation}_{tls_trail}")
        
        return heatmap_html, best_performance_pct
        
    except Exception as e:
        logger.error(f"Failed to create mini-heatmap for TLS({tls_activation}, {tls_trail}): {e}", exc_info=True)
        return None, 0.0


def create_4d_tls_grid(tls_results_df: pd.DataFrame, strategy_filter: Optional[str] = None, 
                      strategy_instances_df: Optional[pd.DataFrame] = None, 
                      baseline_data: Optional[Dict[str, float]] = None,
                      include_win_rate_data: bool = True,
                      global_color_config_override: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
        # HYBRID APPROACH: Client-side for "All", Server-side for specific strategies
        if strategy_filter and strategy_filter != 'all' and strategy_filter != 'All Strategies':
            # Server-side filtering for specific strategy selection
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
            # Client-side filtering for "All Strategies" - use all data
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
        if global_color_config_override:
            global_color_config = global_color_config_override
            logger.info("Using provided global color scale override.")
        else:
            logger.info("Calculating new global color scale based on filtered data.")
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
                heatmap_html, best_performance_pct = create_mini_heatmap(
                    activation, trail, filtered_df, global_color_config, strategy_instances_df
                )
                
                # Determine header color based on best percentage performance (changed from avg)
                if best_performance_pct > 5.0:  # > 5% profit
                    header_class = 'performance-excellent'
                elif best_performance_pct > 1.0:  # > 1% profit 
                    header_class = 'performance-good'
                else:  # <= 1% or negative
                    header_class = 'performance-average'
                
                # Calculate TLS improvement vs baseline (if available)
                tls_improvement = None
                if baseline_info and best_performance_pct is not None:
                    tls_improvement = best_performance_pct - baseline_info['baseline_pnl_pct']
                
                # Calculate win rate for this cell (if enabled)
                cell_win_rate = None
                if include_win_rate_data and heatmap_html is not None:
                    cell_data = filtered_df[
                        (filtered_df['tls_activation'] == activation) & 
                        (filtered_df['tls_trail'] == trail)
                    ]
                    if not cell_data.empty:
                        # Calculate win rate based on positive PnL positions
                        positive_results = 0
                        for _, pos_row in cell_data.iterrows():
                            pos_strategy_id = pos_row['strategy_instance_id']
                            pos_total_invested = 1.0
                            if strategy_instances_df is not None:
                                pos_strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == pos_strategy_id]
                                if not pos_strategy_info.empty:
                                    pos_total_invested = pos_strategy_info.iloc[0]['total_invested']
                            
                            pos_pnl_pct = (pos_row['simulated_pnl'] / pos_total_invested * 100) if pos_total_invested > 0 else 0
                            if pos_pnl_pct > 0:
                                positive_results += 1
                        
                        cell_win_rate = (positive_results / len(cell_data) * 100) if len(cell_data) > 0 else 0
                
                # Get actual strategy IDs from the cell data for proper filtering
                cell_data = filtered_df[
                    (filtered_df['tls_activation'] == activation) & 
                    (filtered_df['tls_trail'] == trail)
                ]
                
                # Extract unique strategy IDs from this cell's data
                cell_strategy_ids = [str(x) for x in cell_data['strategy_instance_id'].unique()] if not cell_data.empty else []
                
                # Determine strategy_id based on filtering mode
                if strategy_filter and strategy_filter != 'all' and strategy_filter != 'All Strategies':
                    # Single strategy mode: all cells have the same strategy_id
                    primary_strategy_id = strategy_filter
                    strategy_ids = [strategy_filter] if cell_strategy_ids else []
                else:
                    # All strategies mode: mixed data
                    primary_strategy_id = cell_strategy_ids[0] if cell_strategy_ids else None
                    strategy_ids = cell_strategy_ids
                
                row_data.append({
                    'tls_activation': float(activation),
                    'tls_trail': float(trail),
                    'heatmap_html': heatmap_html,
                    'best_performance': float(best_performance_pct) if best_performance_pct is not None else 0.0,  # Changed from avg to best
                    'header_class': header_class,
                    'title': f'TLS({activation}%, {trail}%)',
                    'has_data': heatmap_html is not None,
                    'tls_improvement': float(tls_improvement) if tls_improvement is not None else None,  # Ensure Python float
                    'win_rate': float(cell_win_rate) if cell_win_rate is not None else None,  # Ensure Python float
                    'strategy_ids': strategy_ids,  # Already a list of strings
                    'primary_strategy_id': primary_strategy_id,  # String
                    'is_single_strategy_mode': bool(strategy_filter and strategy_filter != 'all' and strategy_filter != 'All Strategies')
                })
            
            grid_data.append(row_data)
        
        logger.info(f"Created 4D TLS grid: {len(tls_activation_range)} × {len(tls_trail_range)} = {len(tls_activation_range) * len(tls_trail_range)} cells")
        
        # Calculate always-visible baseline information
        always_visible_baseline = None
        if strategy_filter and baseline_data and strategy_instances_df is not None:
            strategy_baseline_pnl = baseline_data.get(strategy_filter, 0.0)
            strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_filter]
            if not strategy_info.empty:
                total_invested = strategy_info.iloc[0]['total_invested']
                baseline_pct = (strategy_baseline_pnl / total_invested * 100) if total_invested > 0 else 0
                always_visible_baseline = {
                    'strategy_id': strategy_filter,
                    'baseline_pnl_pct': baseline_pct,
                    'display_text': f"Current baseline to beat: {baseline_pct:.2f}%"
                }
        elif baseline_data:  # Global baseline when no strategy filter
            # Calculate average baseline across all strategies
            baseline_values = list(baseline_data.values())
            if baseline_values and strategy_instances_df is not None:
                avg_baseline = np.mean(baseline_values)
                # Convert to approximate percentage (using average total_invested)
                avg_total_invested = strategy_instances_df['total_invested'].mean() if 'total_invested' in strategy_instances_df.columns else 1.0
                baseline_pct = (avg_baseline / avg_total_invested * 100) if avg_total_invested > 0 else 0
                always_visible_baseline = {
                    'strategy_id': 'all',
                    'baseline_pnl_pct': baseline_pct,
                    'display_text': f"Average baseline across all strategies: {baseline_pct:.2f}%"
                }
        
        return {
            'grid_data': grid_data,
            'global_color_config': global_color_config,
            'tls_activation_range': tls_activation_range,  # Already converted to Python floats
            'tls_trail_range': tls_trail_range,  # Already converted to Python floats
            'total_combinations': int(len(tls_activation_range) * len(tls_trail_range)),
            'strategy_filter': strategy_filter,
            'baseline_info': baseline_info,  # Legacy baseline info
            'always_visible_baseline': always_visible_baseline,  # NEW: Always visible baseline
            'available_strategies': [str(x) for x in tls_results_df['strategy_instance_id'].unique()] if not tls_results_df.empty else []  # For strategy dropdown
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


def create_grid_filter_controls(available_strategies: Optional[List[str]] = None) -> Dict[str, Any]:
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
        # Get available strategies (removed "All Strategies" option)
        # Populate strategy options from actual data
        strategy_options = []
        if available_strategies:
            strategy_options.extend(sorted(available_strategies))
        
        filter_config = {
            'min_performance': {
                'type': 'range',
                'min': -5.0,  # Allow negative performance filtering
                'max': 20.0,
                'step': 0.25,
                'default': -5.0,  # Start with no filtering
                'label': 'Min Performance (%)',
                'id': 'grid-min-performance',
                'scale_markers': [0, 5, 10, 15, 20],  # Add scale markers
                'zero_marker': True  # Highlight 0% marker
            },
            'strategy_filter': {
                'type': 'dropdown',
                'options': strategy_options,  # Now populated from actual data without "All Strategies"
                'default': strategy_options[0] if strategy_options else '',  # Default to first strategy
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
                'id': 'grid-min-winrate',
                'enabled': True  # Now fully enabled with data
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
                
                # Strategy filter - now fully implemented
                if filters.get('strategy') != 'All Strategies':
                    if cell.get('strategy_id') != filters.get('strategy'):
                        passes_filters = False
                
                # Win rate filter - now fully implemented
                min_win_rate = filters.get('minWinRate', 0)
                if cell.get('win_rate') is not None and cell.get('win_rate') < min_win_rate:
                    passes_filters = False
                
                # TLS improvement filter - now fully implemented
                if filters.get('showOnlyImprovements', False):
                    if cell.get('tls_improvement') is None or cell.get('tls_improvement') <= 0:
                        passes_filters = False
                
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


def get_strategy_list_for_dropdown(tls_results_df: pd.DataFrame) -> List[str]:
    """
    Extract sorted strategy list for dropdown population.
    
    Args:
        tls_results_df: TLS simulation results DataFrame
        
    Returns:
        List of strategy IDs sorted by date (newest first)
    """
    try:
        if tls_results_df.empty:
            return []
        
        from utils.common import sort_strategies_by_date_descending
        strategies = [str(x) for x in tls_results_df['strategy_instance_id'].unique()]
        return sort_strategies_by_date_descending(strategies)
        
    except Exception as e:
        logger.error(f"Failed to get strategy list for dropdown: {e}")
        return []


def enhance_min_performance_slider_display() -> str:
    """
    Generate enhanced HTML for min performance slider with scale markers.
    
    Returns:
        HTML string with enhanced slider display
    """
    return """
    <div class="slider-container enhanced-slider">
        <label for="grid-min-performance" class="form-label">Min Performance (%)</label>
        <div class="slider-wrapper">
            <input type="range" class="form-range" id="grid-min-performance" 
                   min="-5" max="20" step="0.25" value="-5">
            <div class="slider-scale">
                <span class="scale-marker zero-marker" data-value="0">0%</span>
                <span class="scale-marker" data-value="5">5%</span>
                <span class="scale-marker" data-value="10">10%</span>
                <span class="scale-marker" data-value="15">15%</span>
                <span class="scale-marker" data-value="20">20%</span>
            </div>
        </div>
        <div class="slider-value">Current: <span id="grid-performance-value">-5%</span></div>
    </div>
    
    <style>
    .enhanced-slider .slider-wrapper {
        position: relative;
        margin: 10px 0;
    }
    
    .enhanced-slider .slider-scale {
        display: flex;
        justify-content: space-between;
        margin-top: 5px;
        font-size: 0.8em;
        color: #6c757d;
    }
    
    .enhanced-slider .scale-marker {
        position: relative;
        text-align: center;
        flex: 1;
    }
    
    .enhanced-slider .zero-marker {
        font-weight: bold;
        color: #dc3545;
        background-color: #fff3cd;
        padding: 2px 4px;
        border-radius: 3px;
        border: 1px solid #ffc107;
    }
    
    .enhanced-slider .slider-value {
        text-align: center;
        margin-top: 5px;
        font-weight: bold;
    }
    </style>
    """