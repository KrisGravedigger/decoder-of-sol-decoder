"""
TLS 4D Grid Charts for Phase 3 - 4D Parameter Grid Visualization

Creates sophisticated grid-based mini-heatmaps enabling visual identification 
of optimal parameter "islands" across 4D TLS space. This module is responsible
for generating the data structures and Plotly HTML snippets that are rendered
by the Jinja2 template into an interactive grid.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List, Tuple, Optional
import numpy as np
import logging
import os

logger = logging.getLogger(__name__)

# AIDEV-NOTE-CLAUDE: Import UnifiedBaselineManager for consistent baselines
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


def detect_tested_tls_ranges(tls_results_df: pd.DataFrame) -> Tuple[List[float], List[float]]:
    """Extracts the actual tested TLS parameter ranges from the simulation results.

    It is critical that the grid visualization displays exactly what was tested, rather
    than relying on the original configuration file. This ensures data integrity and
    prevents rendering empty rows or columns for parameters that were not simulated.

    Args:
        tls_results_df (pd.DataFrame): The DataFrame containing raw TLS simulation results,
            which must include 'tls_activation' and 'tls_trail' columns.

    Returns:
        Tuple[List[float], List[float]]: A tuple containing two sorted lists of unique
        values: (tls_activation_range, tls_trail_range). Returns empty lists if
        the input is empty or columns are missing.
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to detect_tested_tls_ranges")
        return [], []
    
    try:
        # AIDEV-NOTE-CLAUDE: Convert to float and sort to ensure a consistent grid layout.
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
    """Calculates a global, symmetric, diverging color scale for PnL percentages.

    This function is critical for visual consistency across all mini-heatmaps. By using a
    single color scale, it allows for direct and accurate comparison of performance between
    different TLS parameter combinations. The scale is centered at zero to clearly
    distinguish between profit and loss.

    Args:
        tls_results_df (pd.DataFrame): The DataFrame with all TLS simulation results.
        strategy_instances_df (Optional[pd.DataFrame]): DataFrame containing strategy instance
            metadata, used to calculate PnL percentages from absolute SOL values.

    Returns:
        Dict[str, Any]: A configuration dictionary containing the symmetric min/max PnL
        values ('global_min_pnl', 'global_max_pnl') and the Plotly color scale list
        ('color_scale').
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
            # AIDEV-PERF-CLAUDE: Using a merge is more efficient than iterating for large datasets.
            merged_df = pd.merge(tls_results_df, strategy_instances_df[['strategy_instance_id', 'total_invested']], on='strategy_instance_id', how='left')
            merged_df['total_invested'] = merged_df['total_invested'].fillna(1.0) # Avoid division by zero
            valid_investment = merged_df['total_invested'] > 0
            # AIDEV-NOTE-CLAUDE: Calculate average PnL per position for each strategy
            # Group by strategy to get averages
            strategy_groups = merged_df.loc[valid_investment].groupby('strategy_instance_id').agg({
                'simulated_pnl': 'mean',
                'total_invested': 'mean'
            }).reset_index()
            
            # Calculate ROI using averages: (avg_pnl / avg_invested) * 100
            pnl_percentages = []
            for _, row in strategy_groups.iterrows():
                avg_pnl = row['simulated_pnl']
                avg_invested = row['total_invested'] / len(merged_df[merged_df['strategy_instance_id'] == row['strategy_instance_id']])
                pnl_pct = calculate_strategy_roi_percentage(avg_pnl, avg_invested)
                pnl_percentages.append(pnl_pct)
        
        if not pnl_percentages:
            # Fallback if strategy instances are not available or no valid investments
            pnl_percentages = (tls_results_df['simulated_pnl'] * 100).tolist()

        if not pnl_percentages:
            # Final fallback for empty data
             return {'global_min_pnl': -1.0, 'global_max_pnl': 1.0, 'color_scale': [[0.0, '#e74c3c'], [0.5, '#f39c12'], [1.0, '#27ae60']]}

        # AIDEV-4D-VIZ-CLAUDE: Dynamic scale based on actual data range
        # This ensures proper color differentiation even for small value ranges
        global_min_pnl = float(min(pnl_percentages)) if pnl_percentages else -1.0
        global_max_pnl = float(max(pnl_percentages)) if pnl_percentages else 1.0
        
        # Calculate the actual range
        pnl_range = global_max_pnl - global_min_pnl
        
        # For symmetric scale around zero, but with better granularity
        if pnl_range < 0.1:  # Very narrow range - use actual min/max
            symmetric_min = global_min_pnl - 0.01  # Small padding
            symmetric_max = global_max_pnl + 0.01
        else:
            # Find the center point and create symmetric scale
            center = (global_min_pnl + global_max_pnl) / 2
            half_range = max(abs(global_max_pnl - center), abs(center - global_min_pnl))
            
            # Add 10% padding for better visibility
            padding = half_range * 0.1
            symmetric_min = center - half_range - padding
            symmetric_max = center + half_range + padding
        
        logger.info(f"Dynamic color scale - Min: {symmetric_min:.2f}%, Max: {symmetric_max:.2f}%, Range: {pnl_range:.2f}%")
        
        # AIDEV-4D-VIZ-CLAUDE: A 5-point diverging scale provides better visual contrast,
        # especially for values near zero, compared to a simple 3-point scale.
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
        # Return safe defaults in case of failure
        return {
            'global_min_pnl': -5.0,
            'global_max_pnl': 5.0,
            'color_scale': [[0.0, '#e74c3c'], [0.5, '#fef9e7'], [1.0, '#27ae60']]
        }


def create_mini_heatmap(tls_activation: float, tls_trail: float,
                       tls_results_df: pd.DataFrame,
                       global_color_config: Dict[str, Any],
                       strategy_instances_df: Optional[pd.DataFrame] = None) -> Tuple[Optional[str], float]:
    """Generates a single TPxSL mini-heatmap for a specific TLS combination.

    This function filters the main results for a given TLS activation/trail pair,
    pivots the data to form a TPxSL matrix, and renders it as a self-contained
    Plotly HTML div. It adheres to the global color scale for consistency.

    Args:
        tls_activation (float): The specific TLS activation level to filter for.
        tls_trail (float): The specific TLS trail level to filter for.
        tls_results_df (pd.DataFrame): The main DataFrame of all TLS simulation results.
        global_color_config (Dict[str, Any]): The global color scale configuration.
        strategy_instances_df (Optional[pd.DataFrame]): Data for calculating PnL percentages.

    Returns:
        Tuple[Optional[str], float]: A tuple containing:
        - The generated HTML string for the Plotly chart div, or None if no data.
        - The best PnL percentage found within this specific heatmap's data.
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

        # AIDEV-NOTE-CLAUDE: The z-matrix must contain PnL percentages to match the
        # global color scale, which is also based on percentages.
        z_matrix_pct = []
        for sl in sl_levels:
            row_pct = []
            for tp in tp_levels:
                cell_data = filtered_data[
                    (filtered_data['tp_level'] == tp) &
                    (filtered_data['sl_level'] == sl)
                ]
                
                if not cell_data.empty:
                    # AIDEV-NOTE-CLAUDE: Calculate average PnL % using avg per position / avg investment
                    pnl_percentages = []
                    if strategy_instances_df is not None:
                        merged_cell_data = pd.merge(cell_data, strategy_instances_df[['strategy_instance_id', 'total_invested', 'analyzed_position_count']], on='strategy_instance_id', how='left')
                        merged_cell_data['total_invested'] = merged_cell_data['total_invested'].fillna(1.0).replace(0, 1.0)
                        merged_cell_data['analyzed_position_count'] = merged_cell_data['analyzed_position_count'].fillna(1).replace(0, 1)
                        
                        # Calculate average investment per position for each strategy
                        merged_cell_data['avg_investment_per_position'] = merged_cell_data['total_invested'] / merged_cell_data['analyzed_position_count']
                        
                        # Use average PnL and average investment
                        for strategy_id in merged_cell_data['strategy_instance_id'].unique():
                            strategy_data = merged_cell_data[merged_cell_data['strategy_instance_id'] == strategy_id]
                            avg_pnl = strategy_data['simulated_pnl'].mean()
                            avg_investment = strategy_data['avg_investment_per_position'].iloc[0]
                            pnl_pct = calculate_strategy_roi_percentage(avg_pnl, avg_investment)
                            pnl_percentages.append(pnl_pct)
                                                         
                    if pnl_percentages:
                        avg_pnl_pct = np.mean(pnl_percentages)
                    else:
                        avg_pnl_pct = 0.0
                    row_pct.append(avg_pnl_pct)
                else:
                    row_pct.append(None)
            z_matrix_pct.append(row_pct)

        # AIDEV-NOTE-CLAUDE: 'best_performance_pct' is the local maximum for this specific
        # heatmap. This value is used to color the cell's header in the final grid.
        best_performance_pct = np.nanmax(z_matrix_pct) if np.any(z_matrix_pct) else 0.0

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

        # AIDEV-4D-VIZ-CLAUDE: Layout adjustments are critical to prevent axis labels from
        # being cropped in the compact grid view.
        fig.update_layout(
            title=f"TLS({tls_activation}%, {tls_trail}%)",
            height=240,
            margin=dict(l=35, r=10, t=40, b=60), # Larger bottom margin for labels
            xaxis=dict(title="TP", title_font_size=10, tickfont_size=8),
            yaxis=dict(title="SL", title_font_size=10, tickfont_size=8),
            title_font_size=12
        )
        
        # AIDEV-NOTE-CLAUDE: Returning a self-contained HTML div is a pragmatic choice that
        # simplifies injection into the Jinja2 template.
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
    """Orchestrates the creation of the complete 4D grid of mini-heatmaps.

    This function builds the main data structure that the frontend JavaScript consumes
    to render and filter the interactive 4D grid. It iterates through all tested
    TLS activation and trail combinations, generating a mini-heatmap for each one.

    Args:
        tls_results_df (pd.DataFrame): The complete dataset of TLS simulation results.
        strategy_filter (Optional[str]): If provided, filters the data for a specific
            strategy_instance_id before generating the grid.
        strategy_instances_df (Optional[pd.DataFrame]): Data for PnL percentage calculations.
        baseline_data (Optional[Dict[str, float]]): Baseline performance data for comparison,
            mapping strategy_instance_id to its best non-TLS PnL.
        include_win_rate_data (bool): Whether to calculate and include win rate data.
        global_color_config_override (Optional[Dict[str, Any]]): A pre-calculated global
            color scale to use, preventing recalculation for each strategy.

    Returns:
        Dict[str, Any]: A dictionary that fully complies with the Frontend Data Contract.
        It contains the nested 'grid_data' list, range information, color configuration,
        and baseline info required by the Jinja2 template and its JavaScript.
    """
    if tls_results_df.empty:
        logger.warning("Empty TLS results DataFrame provided to create_4d_tls_grid")
        return {
            'grid_data': [], 'global_color_config': {}, 'tls_activation_range': [],
            'tls_trail_range': [], 'error': 'No TLS data available'
        }
    
    try:
        if strategy_filter and strategy_filter != 'all' and strategy_filter != 'All Strategies':
            filtered_df = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_filter]
            if filtered_df.empty:
                logger.warning(f"No data found for strategy filter: {strategy_filter}")
                return {'grid_data': [], 'global_color_config': {}, 'tls_activation_range': [],
                        'tls_trail_range': [], 'error': f'No data for strategy: {strategy_filter}'}
        else:
            filtered_df = tls_results_df
        
        tls_activation_range, tls_trail_range = detect_tested_tls_ranges(filtered_df)
        
        if not tls_activation_range or not tls_trail_range:
            logger.warning("No valid TLS ranges detected in data")
            return {'grid_data': [], 'global_color_config': {}, 'tls_activation_range': [],
                    'tls_trail_range': [], 'error': 'No valid TLS parameter ranges found'}
        
        if global_color_config_override:
            global_color_config = global_color_config_override
            logger.info("Using provided global color scale override.")
        else:
            logger.info("Calculating new global color scale based on filtered data.")
            global_color_config = calculate_global_color_scale(filtered_df, strategy_instances_df)
        
        grid_data = []
        baseline_info = None
        
        # AIDEV-INTEGRATE-CLAUDE: Use UnifiedBaselineManager for baseline if available
        if strategy_filter and baseline_data:
            baseline_pnl = baseline_data.get(strategy_filter, 0.0)
            
            if UNIFIED_MANAGER_AVAILABLE:
                try:
                    import yaml
                    config_path = "reporting/config/portfolio_config.yaml"
                    config = {}
                    if os.path.exists(config_path):
                        with open(config_path, 'r') as f:
                            config = yaml.safe_load(f)
                    
                    if config.get('unified_baseline', {}).get('enabled', False):
                        manager = UnifiedBaselineManager(config)
                        baseline_pnl = manager.get_tls_comparison_baseline(strategy_filter, filtered_df)
                except Exception as e:
                    logger.debug(f"Failed to use UnifiedBaselineManager: {e}")
            
            if strategy_instances_df is not None:
                strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_filter]
                if not strategy_info.empty:
                    total_invested = strategy_info.iloc[0]['total_invested']
                    # AIDEV-NOTE-CLAUDE: Use standardized ROI calculation
                    baseline_pct = calculate_strategy_roi_percentage(baseline_pnl, total_invested)
                    baseline_info = {'strategy_id': strategy_filter, 'baseline_pnl_sol': baseline_pnl, 'baseline_pnl_pct': baseline_pct}
        
        for activation in tls_activation_range:
            row_data = []
            for trail in tls_trail_range:
                heatmap_html, best_performance_pct = create_mini_heatmap(
                    activation, trail, filtered_df, global_color_config, strategy_instances_df
                )
                
                header_class = 'performance-average'
                if best_performance_pct > 5.0: header_class = 'performance-excellent'
                elif best_performance_pct > 1.0: header_class = 'performance-good'
                
                tls_improvement = None
                if baseline_info and best_performance_pct is not None:
                    tls_improvement = best_performance_pct - baseline_info['baseline_pnl_pct']
                
                cell_win_rate = None
                if include_win_rate_data and heatmap_html is not None:
                    cell_data = filtered_df[(filtered_df['tls_activation'] == activation) & (filtered_df['tls_trail'] == trail)]
                    if not cell_data.empty:
                        positive_results = 0
                        for _, pos_row in cell_data.iterrows():
                            pos_strategy_id = pos_row['strategy_instance_id']
                            # AIDEV-NOTE-CLAUDE: Use average investment per position
                            if strategy_instances_df is not None:
                                pos_strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == pos_strategy_id]
                                if not pos_strategy_info.empty:
                                    total_invested = pos_strategy_info.iloc[0]['total_invested']
                                    position_count = pos_strategy_info.iloc[0].get('analyzed_position_count', 1)
                                    avg_invested = total_invested / position_count if position_count > 0 else total_invested
                                else:
                                    avg_invested = 1.0
                            else:
                                avg_invested = 1.0
                            
                            pos_pnl_pct = calculate_strategy_roi_percentage(pos_row['simulated_pnl'], avg_invested)
                            if pos_pnl_pct > 0: positive_results += 1
                        cell_win_rate = (positive_results / len(cell_data) * 100) if len(cell_data) > 0 else 0
                
                cell_data = filtered_df[(filtered_df['tls_activation'] == activation) & (filtered_df['tls_trail'] == trail)]
                cell_strategy_ids = [str(x) for x in cell_data['strategy_instance_id'].unique()] if not cell_data.empty else []
                
                is_single_mode = bool(strategy_filter and strategy_filter != 'all' and strategy_filter != 'All Strategies')
                primary_strategy_id = strategy_filter if is_single_mode else (cell_strategy_ids[0] if cell_strategy_ids else None)
                strategy_ids = [strategy_filter] if is_single_mode and cell_strategy_ids else cell_strategy_ids

                # AIDEV-NOTE-CLAUDE: This dictionary is the "Cell Object" defined in the Frontend Data Contract.
                # Every key here is required by the JavaScript for display or filtering.
                row_data.append({
                    'tls_activation': float(activation),
                    'tls_trail': float(trail),
                    'heatmap_html': heatmap_html,
                    'best_performance': float(best_performance_pct) if best_performance_pct is not None else 0.0,
                    'header_class': header_class,
                    'title': f'TLS({activation}%, {trail}%)',
                    'has_data': heatmap_html is not None,
                    'tls_improvement': float(tls_improvement) if tls_improvement is not None else None,
                    'win_rate': float(cell_win_rate) if cell_win_rate is not None else None,
                    'strategy_ids': strategy_ids,
                    'primary_strategy_id': primary_strategy_id,
                    'is_single_strategy_mode': is_single_mode
                })
            
            grid_data.append(row_data)
        
        logger.info(f"Created 4D TLS grid: {len(tls_activation_range)} rows × {len(tls_trail_range)} columns.")
        
        always_visible_baseline = None
        if strategy_filter and baseline_data and strategy_instances_df is not None:
            strategy_baseline_pnl = baseline_data.get(strategy_filter, 0.0)
            strategy_info = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_filter]
            if not strategy_info.empty:
                total_invested = strategy_info.iloc[0]['total_invested']
                baseline_pct = (strategy_baseline_pnl / total_invested * 100) if total_invested > 0 else 0
                always_visible_baseline = {
                    'strategy_id': strategy_filter, 'baseline_pnl_pct': baseline_pct,
                    'display_text': f"Current baseline to beat: {baseline_pct:.2f}%"
                }
        elif baseline_data: # Global baseline for "All Strategies" view
            baseline_values = list(baseline_data.values())
            if baseline_values and strategy_instances_df is not None:
                avg_baseline = np.mean(baseline_values)
                avg_total_invested = strategy_instances_df['total_invested'].mean() if 'total_invested' in strategy_instances_df.columns else 1.0
                baseline_pct = (avg_baseline / avg_total_invested * 100) if avg_total_invested > 0 else 0
                always_visible_baseline = {
                    'strategy_id': 'all', 'baseline_pnl_pct': baseline_pct,
                    'display_text': f"Average baseline across all strategies: {baseline_pct:.2f}%"
                }
        
        # AIDEV-NOTE-CLAUDE: This final dictionary is the "Grid Object" defined in the contract.
        return {
            'grid_data': grid_data,
            'global_color_config': global_color_config,
            'tls_activation_range': tls_activation_range,
            'tls_trail_range': tls_trail_range,
            'total_combinations': int(len(tls_activation_range) * len(tls_trail_range)),
            'strategy_filter': strategy_filter,
            'baseline_info': baseline_info,
            'always_visible_baseline': always_visible_baseline,
            'available_strategies': [str(x) for x in tls_results_df['strategy_instance_id'].unique()] if not tls_results_df.empty else []
        }
        
    except Exception as e:
        logger.error(f"Failed to create 4D TLS grid: {e}", exc_info=True)
        return {'grid_data': [], 'global_color_config': {}, 'tls_activation_range': [],
                'tls_trail_range': [], 'error': f'Grid generation failed: {str(e)}'}


def get_strategy_list_for_dropdown(tls_results_df: pd.DataFrame) -> List[str]:
    """Extracts and sorts a list of unique strategy IDs for populating UI dropdowns.

    Args:
        tls_results_df (pd.DataFrame): The DataFrame with all TLS simulation results.

    Returns:
        List[str]: A list of unique strategy instance IDs, sorted by date descending.
    """
    try:
        if tls_results_df.empty:
            return []
        
        # AIDEV-INTEGRATE-CLAUDE: This relies on a shared utility function for consistent sorting.
        from utils.common import sort_strategies_by_date_descending
        strategies = [str(x) for x in tls_results_df['strategy_instance_id'].unique()]
        return sort_strategies_by_date_descending(strategies)
        
    except Exception as e:
        logger.error(f"Failed to get strategy list for dropdown: {e}")
        return []

# NOTE: Functions create_grid_filter_controls, apply_grid_filters, and
# enhance_min_performance_slider_display were removed as they were identified
# as dead code. The filtering logic is now handled entirely by client-side JavaScript.
# This aligns with the refactoring goal of separating backend data preparation from
# frontend presentation logic.