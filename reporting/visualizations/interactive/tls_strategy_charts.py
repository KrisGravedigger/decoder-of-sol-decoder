"""
TLS Strategy Charts for Phase 2 - Strategy Overview Visualization

Creates interactive strategy comparison charts enabling rapid identification
of high-performing strategies through visual overview and clickable navigation.
"""

import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from typing import Dict, Any, List
import numpy as np
from utils.common import sort_strategies_by_date_descending
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
    
    Args:
        total_pnl_sol: Sum of all position PnL for the strategy
        total_invested_sol: Sum of all investments for the strategy
        
    Returns:
        ROI percentage: (total_pnl / total_invested) * 100
    """
    return (total_pnl_sol / total_invested_sol * 100) if total_invested_sol > 0 else 0.0

def _prepare_strategy_performance_summary_data(tls_results_df: pd.DataFrame) -> Dict[str, Any]:
    """
    Prepares aggregated data for the strategy performance summary table.
    
    This function compares the total PnL (in SOL) of the best TSL combination
    against the total PnL of the best baseline (non-TSL) combination for each strategy.
    It also extracts the optimal parameters for both scenarios.

    Args:
        tls_results_df: DataFrame with raw TLS simulation results.

    Returns:
        A dictionary containing prepared 'table_rows' for rendering.
    """
    table_rows = []
    if tls_results_df.empty:
        return {'table_rows': []}
        
    strategies = sort_strategies_by_date_descending([str(x) for x in tls_results_df['strategy_instance_id'].unique()])

    # --- Data Loading (One time, for efficiency) ---
    strategy_instances_df = pd.read_csv("strategy_instances.csv") if os.path.exists("strategy_instances.csv") else pd.DataFrame()
    baseline_aggregated_df = pd.read_csv("reporting/output/range_test_aggregated.csv") if os.path.exists("reporting/output/range_test_aggregated.csv") else pd.DataFrame()

    # --- Main Loop per Strategy ---
    for strategy_id in strategies:
        strategy_data_tsl = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
        if strategy_data_tsl.empty:
            continue

        position_count = len(strategy_data_tsl['position_id'].unique())
        if not strategy_instances_df.empty:
            strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
            if not strategy_row.empty:
                position_count = strategy_row.iloc[0].get('analyzed_position_count', position_count)

        # --- TSL Calculations: Find best combination and its TOTAL PnL ---
        total_pnl_tsl_sol = 0.0
        optimal_params_tsl_str = "N/A"
        # Group by TSL parameters and calculate SUM of PnL for each combination
        total_pnl_per_combo_tsl = strategy_data_tsl.groupby(['tp_level', 'sl_level', 'tls_activation', 'tls_trail'])['simulated_pnl'].sum()
        
        if not total_pnl_per_combo_tsl.empty:
            # Find the combination with the highest total PnL
            total_pnl_tsl_sol = total_pnl_per_combo_tsl.max()
            best_combo_params = total_pnl_per_combo_tsl.idxmax()
            optimal_params_tsl_str = f"TP:{best_combo_params[0]} SL:{best_combo_params[1]}<br>Act:{best_combo_params[2]} Trl:{best_combo_params[3]}"

        # --- Baseline Calculations: Find best combination and its TOTAL PnL ---
        # AIDEV-NOTE-CLAUDE: Use UnifiedBaselineManager if available and enabled
        total_pnl_baseline_sol = 0.0
        optimal_params_baseline_str = "N/A"
        
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
                    if not baseline_aggregated_df.empty:
                        baseline_result = manager.calculate_strategy_baseline(
                            strategy_id, 
                            baseline_aggregated_df,
                            metric='total_pnl'
                        )
                        total_pnl_baseline_sol = baseline_result.baseline_sol
                        optimal_params_baseline_str = f"TP:{baseline_result.optimal_tp} SL:{baseline_result.optimal_sl}"
                        logger.debug(f"Using unified baseline for {strategy_id}: {total_pnl_baseline_sol:.4f} SOL")
                else:
                    # Legacy baseline calculation
                    if not baseline_aggregated_df.empty:
                        strategy_baseline_agg = baseline_aggregated_df[baseline_aggregated_df['strategy_instance_id'] == strategy_id]
                        if not strategy_baseline_agg.empty:
                            best_baseline_row = strategy_baseline_agg.loc[strategy_baseline_agg['total_pnl'].idxmax()]
                            total_pnl_baseline_sol = best_baseline_row['total_pnl']
                            optimal_params_baseline_str = f"TP:{best_baseline_row['tp_level']} SL:{best_baseline_row['sl_level']}"
            except Exception as e:
                logger.debug(f"UnifiedBaselineManager not enabled or error occurred: {e}")
                # Fallback to legacy
                if not baseline_aggregated_df.empty:
                    strategy_baseline_agg = baseline_aggregated_df[baseline_aggregated_df['strategy_instance_id'] == strategy_id]
                    if not strategy_baseline_agg.empty:
                        best_baseline_row = strategy_baseline_agg.loc[strategy_baseline_agg['total_pnl'].idxmax()]
                        total_pnl_baseline_sol = best_baseline_row['total_pnl']
                        optimal_params_baseline_str = f"TP:{best_baseline_row['tp_level']} SL:{best_baseline_row['sl_level']}"
        else:
            # Legacy baseline calculation
            if not baseline_aggregated_df.empty:
                strategy_baseline_agg = baseline_aggregated_df[baseline_aggregated_df['strategy_instance_id'] == strategy_id]
                if not strategy_baseline_agg.empty:
                    best_baseline_row = strategy_baseline_agg.loc[strategy_baseline_agg['total_pnl'].idxmax()]
                    total_pnl_baseline_sol = best_baseline_row['total_pnl']
                    optimal_params_baseline_str = f"TP:{best_baseline_row['tp_level']} SL:{best_baseline_row['sl_level']}"
        
        # --- New Comparison Metric ---
        tsl_advantage_pct = 0.0
        if total_pnl_baseline_sol != 0:
            tsl_advantage_pct = ((total_pnl_tsl_sol - total_pnl_baseline_sol) / abs(total_pnl_baseline_sol)) * 100
        elif total_pnl_tsl_sol > 0:
            tsl_advantage_pct = 100.0 # Baseline was zero, TSL is positive
        elif total_pnl_tsl_sol < 0:
            tsl_advantage_pct = -100.0 # Baseline was zero, TSL is negative

        table_rows.append({
            'strategy_id': strategy_id,
            'position_count': position_count,
            'total_pnl_tsl_sol': total_pnl_tsl_sol,
            'optimal_params_tsl_str': optimal_params_tsl_str,
            'total_pnl_baseline_sol': total_pnl_baseline_sol,
            'optimal_params_baseline_str': optimal_params_baseline_str,
            'tsl_advantage_pct': tsl_advantage_pct,
        })
    
    return {'table_rows': table_rows}


def create_strategy_overview_scatter(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float]) -> str:
    """Creates a scatter plot comparing TLS vs. Baseline performance for all strategies.

    This complex visualization provides a high-level overview of TLS effectiveness.
    Each strategy is represented on the x-axis, with PnL percentages on the y-axis.

    Visualization Logic:
    -   **Performance Range (Grey Bars):** A vertical grey bar for each strategy shows the
        full range of PnL outcomes across all tested TLS combinations, indicating volatility
        and potential.
    -   **Best TLS Result (Green Dot):** A prominent green dot marks the single best-performing
        TLS combination for that strategy, representing the optimal outcome.
    -   **Best Non-TLS Result (Yellow Dot):** A smaller yellow dot shows the best baseline
        (non-TLS) performance, providing a direct visual comparison point.
    -   **Interactivity:** Hovering over points reveals detailed parameters and PnL values.
        The chart title encourages users to click strategy names to filter the more
        detailed 4D grid view below.

    Data Transformation:
    -   Absolute PnL values from simulations are converted to percentages relative to the
        `total_invested` for each strategy instance to ensure fair comparison.
    -   Strategies are sorted by date (newest first) along the x-axis for relevance.

    Args:
        tls_results_df: DataFrame with detailed TLS simulation results.
        baseline_data: Dictionary mapping `strategy_instance_id` to its best non-TLS PnL.

    Returns:
        An HTML string containing the Plotly chart for embedding in the report.
    """
    if tls_results_df.empty:
        return "<p>No TLS data available for strategy overview</p>"
    
    try:
        # Sort strategies by date (newest first)
        strategies = sort_strategies_by_date_descending([str(x) for x in tls_results_df['strategy_instance_id'].unique()])
        
        if not strategies:
            return "<p>No strategies found in TLS data</p>"
        
        fig = go.Figure()
        
        # Add individual combination points for each strategy
        for strategy_id in strategies:
            strategy_results = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
            
            if strategy_results.empty:
                logger.debug(f"No results for strategy {strategy_id}")
                continue
            
            try:
               # Load strategy instances data for investment values to ensure consistent calculation
                import pandas as pd
                import os
                avg_invested = 1.0  # Default fallback
                if os.path.exists("strategy_instances.csv"):
                    strategy_instances_df = pd.read_csv("strategy_instances.csv")
                    strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                    if not strategy_row.empty:
                        total_invested = strategy_row.iloc[0]['total_invested']
                        position_count = strategy_row.iloc[0].get('analyzed_position_count', 1)
                        # AIDEV-NOTE-CLAUDE: Calculate average investment per position
                        avg_invested = total_invested / position_count if position_count > 0 else total_invested
                
                # AIDEV-NOTE-CLAUDE: Use average-based ROI calculation
                strategy_pnl_pct = strategy_results['simulated_pnl'].apply(
                    lambda x: calculate_strategy_roi_percentage(x, avg_invested)
                )
                
                # Ensure strategy_pnl_pct is not empty
                if len(strategy_pnl_pct) == 0:
                    logger.debug(f"Empty PnL percentage data for strategy {strategy_id}")
                    continue
                
                # Calculate PnL range for grey bar visualization using average investment
                # AIDEV-NOTE-CLAUDE: Use average investment for consistent percentage calculation
                min_pnl_pct = calculate_strategy_roi_percentage(strategy_results['simulated_pnl'].min(), avg_invested)
                max_pnl_pct = calculate_strategy_roi_percentage(strategy_results['simulated_pnl'].max(), avg_invested)
                
                # Add grey bar showing PnL range (min to max) instead of individual points
                if min_pnl_pct != max_pnl_pct:  # Only show bar if there's a range
                    fig.add_trace(go.Scatter(
                        x=[strategy_id, strategy_id],
                        y=[min_pnl_pct, max_pnl_pct],
                        mode='lines',
                        line=dict(
                            color='lightgray',
                            width=4
                        ),
                        opacity=0.6,  # Move opacity to trace level, not line level
                        hovertemplate=(
                            "<b>%{x}</b><br>" +
                            f"PnL Range: {min_pnl_pct:.2f}% to {max_pnl_pct:.2f}%<br>" +
                            f"Combinations Tested: {len(strategy_results)}<br>" +
                            "<extra></extra>"
                        ),
                        showlegend=False,
                        name=f"{strategy_id}_range"
                    ))
                
                # Best TLS result (green highlight) - use average-based calculation
                if len(strategy_results) > 0:  # Safety check
                    # Group by unique TP/SL/TLS combinations for this strategy
                    strategy_combos = strategy_results.groupby(
                        ['tp_level', 'sl_level', 'tls_activation', 'tls_trail']
                    ).agg({
                        'simulated_pnl': ['sum', 'count']  # Total PnL and count
                    }).reset_index()
                    
                    strategy_combos.columns = ['tp_level', 'sl_level', 'tls_activation', 'tls_trail', 'total_pnl', 'position_count']
                    
                    # Calculate average PnL % for each combination
                    strategy_combos['avg_pnl_pct'] = strategy_combos.apply(
                        lambda row: calculate_strategy_roi_percentage(
                            row['total_pnl'] / row['position_count'] if row['position_count'] > 0 else row['total_pnl'],
                            avg_invested
                        ), axis=1
                    )
                    
                    # Find best combination by average PnL %
                    if not strategy_combos.empty:
                        best_combo_idx = strategy_combos['avg_pnl_pct'].idxmax()
                        best_combo = strategy_combos.iloc[best_combo_idx]
                        
                        best_tls_pnl_pct = best_combo['avg_pnl_pct']
                        
                        fig.add_trace(go.Scatter(
                            x=[strategy_id],
                            y=[best_tls_pnl_pct],
                            mode='markers',
                            marker=dict(
                                size=8,
                                color='green',
                                opacity=1.0,
                                line=dict(width=1, color='darkgreen')
                            ),
                            hovertemplate=(
                                "<b>BEST TLS: %{x}</b><br>" +
                                "Avg PnL: %{y:.2f}%<br>" +
                                f"TP: {best_combo['tp_level']}%, SL: {best_combo['sl_level']}%<br>" +
                                f"TLS Act: {best_combo['tls_activation']}%, Trail: {best_combo['tls_trail']}%<br>" +
                                f"Positions: {int(best_combo['position_count'])}<br>" +
                                "<extra></extra>"
                            ),
                            showlegend=False,
                            name=f"{strategy_id}_best_tls"
                        ))
                else:
                    # Original single-point logic as fallback
                    best_tls_iloc_pos = strategy_results['simulated_pnl'].argmax()
                    best_tls_result = strategy_results.iloc[best_tls_iloc_pos]
                    
                    best_tls_pnl_pct = calculate_strategy_roi_percentage(
                        best_tls_result['simulated_pnl'], 
                        avg_invested
                    )
                    
                    fig.add_trace(go.Scatter(
                        x=[strategy_id],
                        y=[best_tls_pnl_pct],
                        mode='markers',
                        marker=dict(
                            size=8,
                            color='green',
                            opacity=1.0,
                            line=dict(width=1, color='darkgreen')
                        ),
                        hovertemplate=(
                            "<b>BEST TLS: %{x}</b><br>" +
                            "PnL: %{y:.2f}%<br>" +
                            f"TP: {best_tls_result['tp_level']}%, SL: {best_tls_result['sl_level']}%<br>" +
                            f"TLS Act: {best_tls_result['tls_activation']}%, Trail: {best_tls_result['tls_trail']}%<br>" +
                            "<extra></extra>"
                        ),
                        showlegend=False,
                        name=f"{strategy_id}_best_tls"
                    ))
                
                # Best non-TLS result (yellow highlight) - convert to percentage using average investment
                baseline_pnl = baseline_data.get(strategy_id, 0.0)
                if baseline_pnl != 0.0:
                    # AIDEV-NOTE-CLAUDE: Use average investment for baseline percentage
                    import pandas as pd
                    import os
                    avg_invested_baseline = 1.0  # Default fallback
                    if os.path.exists("strategy_instances.csv"):
                        strategy_instances_df = pd.read_csv("strategy_instances.csv")
                        # AIDEV-NOTE-CLAUDE: Filter out strategies with 0 analyzed positions
                        strategy_instances_df = strategy_instances_df[strategy_instances_df['analyzed_position_count'] > 0]
                        strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                        if not strategy_row.empty:
                            total_invested = strategy_row.iloc[0]['total_invested']
                            position_count = strategy_row.iloc[0].get('analyzed_position_count', 1)
                            avg_invested_baseline = total_invested / position_count if position_count > 0 else total_invested
                    
                    # Load optimal TP/SL data for correct baseline calculation
                    optimal_tp_sl_pnl = baseline_pnl  # Default fallback
                    if os.path.exists("reporting/output/range_test_aggregated.csv"):
                        agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                        strategy_agg_data = agg_df[agg_df['strategy_instance_id'] == strategy_id]
                        if not strategy_agg_data.empty:
                            optimal_tp_sl_pnl = strategy_agg_data.loc[strategy_agg_data['total_pnl'].idxmax(), 'total_pnl']
                    
                    # Calculate correct baseline PnL percentage using average investment
                    # AIDEV-NOTE-CLAUDE: Average-based calculation for consistency
                    baseline_pnl_pct = calculate_strategy_roi_percentage(optimal_tp_sl_pnl / position_count if position_count > 0 else optimal_tp_sl_pnl, avg_invested_baseline)
                    
                    fig.add_trace(go.Scatter(
                        x=[strategy_id],
                        y=[baseline_pnl_pct],
                        mode='markers',
                        marker=dict(
                            size=6,
                            color='gold',
                            opacity=1.0,
                            line=dict(width=1, color='orange')
                        ),
                        hovertemplate=(
                            "<b>BEST NON-TLS: %{x}</b><br>" +
                            "Baseline PnL: %{y:.2f}%<br>" +
                            "<extra></extra>"
                        ),
                        showlegend=False,
                        name=f"{strategy_id}_baseline"
                    ))
                    
            except Exception as strategy_error:
                logger.error(f"Error processing strategy {strategy_id}: {strategy_error}")
                continue
        
        # Add legend traces (invisible points for legend only)
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=8, color='green'),
            name='Best TLS Result',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='markers',
            marker=dict(size=6, color='gold'),
            name='Best Non-TLS Result',
            showlegend=True
        ))
        
        fig.add_trace(go.Scatter(
            x=[None], y=[None],
            mode='lines',
            line=dict(color='lightgray', width=4),
            opacity=0.6,  # Move opacity to trace level
            name='TLS Performance Range',
            showlegend=True,
            hoverinfo='skip'
        ))
        
        # Update layout with WebGL rendering for better performance
        fig.update_layout(
            title='TLS Strategy Performance Overview - Click strategy names to filter detailed view',
            xaxis_title='Strategy Instance',
            yaxis_title='PnL (%)',
            xaxis=dict(
                tickangle=45,
                tickmode='array',
                tickvals=strategies,
                ticktext=strategies
            ),
            height=600,
            template="plotly_white",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5
            ),
            margin=dict(b=150, t=80)  # Extra bottom margin for rotated labels, top margin for legend
        )
        
        # Enable WebGL rendering for better performance with large datasets
        fig.update_traces(marker_line_width=0, selector=dict(mode='markers'))
        
        return fig.to_html(include_plotlyjs=False, div_id="strategy_overview_scatter")
        
    except Exception as e:
        logger.error(f"Failed to create strategy overview scatter: {e}")
        return f"<p>Error generating strategy overview: {e}</p>"


def create_global_top_combinations_table(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float], top_count: int = 10) -> List[Dict[str, Any]]:
    """
    Calculates and returns data for a comprehensive ranking table.

    This function separates data preparation from presentation. It identifies the top-performing,
    unique TLS combinations across all strategies and enriches them with comparison metrics
    against their non-TLS baseline.

    Args:
        tls_results_df: DataFrame with TLS simulation results.
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl.
        top_count: Number of top combinations to return.

    Returns:
        A list of dictionaries, where each dictionary represents a row in the
        final table and contains all necessary data for rendering.
    """
    if tls_results_df.empty:
        return []
    
    try:
        # Load strategy instances data for total_invested values
        strategy_instances_df = pd.read_csv("strategy_instances.csv") if os.path.exists("strategy_instances.csv") else None
        
        # Load optimal TP/SL data for correct baseline calculation
        optimal_tp_sl_data = {}
        if os.path.exists("reporting/output/range_test_aggregated.csv"):
            agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
            optimal_df = agg_df.loc[agg_df.groupby('strategy_instance_id')['total_pnl'].idxmax()]
            optimal_tp_sl_data = optimal_df.set_index('strategy_instance_id')['total_pnl'].to_dict()
        
        # Calculate TLS benefit for all combinations
        enriched_results = []
        for _, row in tls_results_df.iterrows():
            strategy_id = row['strategy_instance_id']
            strategy_baseline = baseline_data.get(strategy_id, 0.0)
            
            total_invested = 1.0
            if strategy_instances_df is not None:
                strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_row.empty:
                    total_invested = strategy_row.iloc[0]['total_invested']
            
            optimal_tp_sl_pnl = optimal_tp_sl_data.get(strategy_id, strategy_baseline)
            # AIDEV-NOTE-CLAUDE: Use standardized ROI calculation
            baseline_pnl_pct = calculate_strategy_roi_percentage(optimal_tp_sl_pnl, total_invested)
            tls_pnl_pct = calculate_strategy_roi_percentage(row['simulated_pnl'], total_invested)
            
            tls_benefit = ((tls_pnl_pct - baseline_pnl_pct) / abs(baseline_pnl_pct)) * 100 if baseline_pnl_pct != 0 else 0.0
            
            enriched_results.append({
                'strategy_instance_id': strategy_id,
                'tp_level': row['tp_level'],
                'sl_level': row['sl_level'],
                'tls_activation': row['tls_activation'],
                'tls_trail': row['tls_trail'],
                'tls_pnl': tls_pnl_pct,
                'tls_pnl_raw': row['simulated_pnl'],
                'baseline_pnl': baseline_pnl_pct,
                'tls_benefit': tls_benefit
            })
        
        all_combinations = sorted(enriched_results, key=lambda x: x['tls_pnl_raw'], reverse=True)
        
        seen_strategies = set()
        top_combinations_data = []
        for combo in all_combinations:
            if combo['strategy_instance_id'] not in seen_strategies:
                # Add CSS classes for rendering
                benefit = combo['tls_benefit']
                combo['benefit_class'] = 'positive' if benefit > 1 else 'negative' if benefit < -1 else ''
                combo['tls_pnl_class'] = 'positive' if combo['tls_pnl'] >= 0 else 'negative'
                combo['baseline_pnl_class'] = 'positive' if combo['baseline_pnl'] >= 0 else 'negative'
                
                top_combinations_data.append(combo)
                seen_strategies.add(combo['strategy_instance_id'])
                
                if len(top_combinations_data) >= top_count:
                    break
        
        return top_combinations_data
        
    except Exception as e:
        logger.error(f"Failed to create global top combinations data: {e}", exc_info=True)
        return []


def create_strategy_performance_summary(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float]) -> Dict[str, Any]:
    """
    Generates an HTML table summarizing and comparing TSL vs Baseline performance.

    This function acts as the presentation layer. It calls the data preparation
    function and then renders an HTML table designed for direct comparison
    of the most profitable TSL vs. non-TSL strategies.

    Args:
        tls_results_df: DataFrame with TLS simulation results.
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl (used by other functions).

    Returns:
        A dictionary containing the final rendered '_table_html' string.
    """
    try:
        prepared_data = _prepare_strategy_performance_summary_data(tls_results_df)
        table_rows = prepared_data.get('table_rows', [])
        
        if not table_rows:
            return {'_table_html': "<p>No data available for performance summary.</p>"}

        table_html = """
        <div class="strategy-performance-table" style="margin-top: 20px;">
            <h4>📋 TSL vs. Baseline Performance Comparison</h4>
            <div class="table-explanation" style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-size: 0.9em; border-left: 4px solid #3498db;">
                <h5 style="margin-top: 0;">🔍 How to Read This Table:</h5>
                <ul>
                    <li>This table compares the <strong>total PnL (in SOL)</strong> of the most profitable TSL setup against the most profitable Baseline (TP/SL only) setup for each strategy.</li>
                    <li><strong>Optimal Params</strong> shows the exact parameter combination that produced the corresponding total PnL.</li>
                    <li><strong>TSL vs Baseline (%)</strong> shows the percentage improvement (or decline) from using the optimal TSL strategy compared to the optimal Baseline strategy.</li>
                </ul>
            </div>
            <table class="table table-striped table-hover" id="strategy_performance_detail_table">
                <thead>
                    <tr>
                        <th>Strategy</th>
                        <th>Optimal TSL PnL (SOL)</th>
                        <th>Optimal TSL Params</th>
                        <th>Optimal Baseline PnL (SOL)</th>
                        <th>Optimal Baseline Params</th>
                        <th>TSL vs Baseline (%)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in table_rows:
            def pnl_class(val): return 'positive' if val >= 0 else 'negative'
            advantage_class = 'positive' if row['tsl_advantage_pct'] > 0 else ('negative' if row['tsl_advantage_pct'] < 0 else '')
            strategy_display_name = f"{row['strategy_id']} ({row['position_count']})"
            table_html += f"""
                <tr>
                    <td>
                        <a href="#" class="strategy-detail-link" data-strategy-id="{row['strategy_id']}" 
                           style="text-decoration: none; color: #3498db; font-weight: bold;">
                            {strategy_display_name}
                        </a>
                    </td>
                    <td class="{pnl_class(row['total_pnl_tsl_sol'])}"><b>{row['total_pnl_tsl_sol']:.3f}</b></td>
                    <td style="font-size: 0.8em; line-height: 1.4;">{row['optimal_params_tsl_str']}</td>
                    <td class="{pnl_class(row['total_pnl_baseline_sol'])}"><b>{row['total_pnl_baseline_sol']:.3f}</b></td>
                    <td style="font-size: 0.8em; line-height: 1.4;">{row['optimal_params_baseline_str']}</td>
                    <td class="{advantage_class}"><strong>{row['tsl_advantage_pct']:+.2f}%</strong></td>
                </tr>
            """
        
        table_html += "</tbody></table></div>"
        
        return {'_table_html': table_html}
        
    except Exception as e:
        logger.error(f"Failed to create strategy performance summary: {e}", exc_info=True)
        return {'_table_html': f"<p>Error generating performance summary: {e}</p>"}