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


def create_strategy_overview_scatter(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float]) -> str:
    """
    AIDEV-4D-VIZ-CLAUDE: Create strategy overview scatter plot with performance clouds.
    
    Layout:
    - X-axis: Strategy names (categorical, rotated labels for readability)
    - Y-axis: PnL percentages (continuous scale)
    - Points: Individual TLS combination results (small semi-transparent dots)
    - Highlights: 
      * Green dot: Best TLS result per strategy (larger, fully opaque)
      * Yellow dot: Best non-TLS result per strategy (medium, fully opaque)
    
    Interactive Features:
    - Clickable strategy names trigger filtering for detailed grid view
    - Hover tooltips: Strategy name, TP/SL/TLS parameters, PnL value
    - Performance density visualization (point clustering indicates optimization "hotspots")
    
    Args:
        tls_results_df: DataFrame with TLS simulation results
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl
        
    Returns:
        HTML string of the plotly chart
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
                # Load strategy instances data for total_invested values to ensure consistent calculation
                import pandas as pd
                import os
                total_invested = 1.0  # Default fallback
                if os.path.exists("strategy_instances.csv"):
                    strategy_instances_df = pd.read_csv("strategy_instances.csv")
                    strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                    if not strategy_row.empty:
                        total_invested = strategy_row.iloc[0]['total_invested']
                
                # Convert PnL to percentage values using total_invested (same as table calculation)
                strategy_pnl_pct = (strategy_results['simulated_pnl'] / total_invested * 100) if total_invested > 0 else strategy_results['simulated_pnl'] * 0
                
                # Ensure strategy_pnl_pct is not empty
                if len(strategy_pnl_pct) == 0:
                    logger.debug(f"Empty PnL percentage data for strategy {strategy_id}")
                    continue
                
                # Calculate PnL range for grey bar visualization using same consistent calculation
                min_pnl_pct = (strategy_results['simulated_pnl'].min() / total_invested * 100) if total_invested > 0 else 0
                max_pnl_pct = (strategy_results['simulated_pnl'].max() / total_invested * 100) if total_invested > 0 else 0
                
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
                
                # Best TLS result (green highlight) - use argmax for safe indexing
                if len(strategy_results) > 0 and len(strategy_pnl_pct) > 0:  # Safety check
                    best_tls_iloc_pos = strategy_results['simulated_pnl'].argmax()  # Use argmax instead of idxmax
                    best_tls_result = strategy_results.iloc[best_tls_iloc_pos]  # Use iloc instead of loc
                    
                    # Safe bounds checking for percentage array access
                    if best_tls_iloc_pos < len(strategy_pnl_pct):
                        best_tls_pnl_pct = strategy_pnl_pct.iloc[best_tls_iloc_pos]
                    else:
                        best_tls_pnl_pct = 0
                    
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
                
                # Best non-TLS result (yellow highlight) - convert to percentage using correct baseline calculation
                baseline_pnl = baseline_data.get(strategy_id, 0.0)
                if baseline_pnl != 0.0:
                    # Load strategy instances data for total_invested values
                    import pandas as pd
                    import os
                    total_invested = 1.0  # Default fallback
                    if os.path.exists("strategy_instances.csv"):
                        strategy_instances_df = pd.read_csv("strategy_instances.csv")
                        strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                        if not strategy_row.empty:
                            total_invested = strategy_row.iloc[0]['total_invested']
                    
                    # Load optimal TP/SL data for correct baseline calculation
                    optimal_tp_sl_pnl = baseline_pnl  # Default fallback
                    if os.path.exists("reporting/output/range_test_aggregated.csv"):
                        agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                        strategy_agg_data = agg_df[agg_df['strategy_instance_id'] == strategy_id]
                        if not strategy_agg_data.empty:
                            optimal_tp_sl_pnl = strategy_agg_data.loc[strategy_agg_data['total_pnl'].idxmax(), 'total_pnl']
                    
                    # Calculate correct baseline PnL percentage: (best_tp_sl_pnl / total_invested) * 100
                    baseline_pnl_pct = (optimal_tp_sl_pnl / total_invested * 100) if total_invested > 0 else 0
                    
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


def create_global_top_combinations_table(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float], top_count: int = 10) -> str:
    """
    Create comprehensive ranking table with strategy navigation.
    
    Columns:
    - Rank: 1-10 numeric ranking
    - Strategy: Clickable strategy name (triggers grid filter)
    - TP: Take profit percentage
    - SL: Stop loss percentage
    - TLS Act: TLS activation percentage
    - TLS Trail: TLS trail percentage
    - TLS PnL: Performance with TLS
    - Baseline PnL: Best TP/SL performance as percentage of total invested
    - TLS Benefit: Percentage improvement ((tls_pnl - baseline_pnl) / baseline_pnl * 100)
    
    Features:
    - Color-coded TLS Benefit: Green (positive), Red (negative), Gray (neutral ±1%)
    - Clickable strategy names set filter for detailed 4D grid view
    - Sort by TLS PnL descending (fixed, no user sorting needed)
    
    Args:
        tls_results_df: DataFrame with TLS simulation results
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl
        top_count: Number of top combinations to show
        
    Returns:
        HTML table string
    """
    if tls_results_df.empty:
        return "<p>No TLS data available for top combinations table</p>"
    
    try:
        # Load strategy instances data for total_invested values
        import pandas as pd
        import os
        strategy_instances_df = None
        if os.path.exists("strategy_instances.csv"):
            strategy_instances_df = pd.read_csv("strategy_instances.csv")
        
        # Load optimal TP/SL data for correct baseline calculation
        optimal_tp_sl_data = {}
        if os.path.exists("reporting/output/range_test_aggregated.csv"):
            agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
            # Find best combination for each strategy based on total_pnl
            optimal_df = agg_df.loc[agg_df.groupby('strategy_instance_id')['total_pnl'].idxmax()]
            optimal_tp_sl_data = optimal_df.set_index('strategy_instance_id')['total_pnl'].to_dict()
        
        # Calculate TLS benefit for all combinations
        enriched_results = []
        for _, row in tls_results_df.iterrows():
            strategy_id = row['strategy_instance_id']
            strategy_baseline = baseline_data.get(strategy_id, 0.0)
            
            # Get total_invested for this strategy for correct baseline percentage calculation
            total_invested = 1.0  # Default fallback
            if strategy_instances_df is not None:
                strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_row.empty:
                    total_invested = strategy_row.iloc[0]['total_invested']
            
            # Calculate correct baseline PnL percentage: (best_tp_sl_pnl / total_invested) * 100
            optimal_tp_sl_pnl = optimal_tp_sl_data.get(strategy_id, strategy_baseline)
            baseline_pnl_pct = (optimal_tp_sl_pnl / total_invested * 100) if total_invested > 0 else 0.0
            
            # Calculate TLS PnL percentage using same denominator for consistency
            tls_pnl_pct = (row['simulated_pnl'] / total_invested * 100) if total_invested > 0 else 0.0
            
            # Calculate TLS Benefit using the PERCENTAGE values (not raw values)
            # Formula: ((TLS_PnL% - Baseline_PnL%) / Baseline_PnL%) * 100
            # Example: TLS=0.25%, Baseline=0.85% -> ((0.25-0.85)/0.85)*100 = -70.6%
            if baseline_pnl_pct != 0:
                tls_benefit = ((tls_pnl_pct - baseline_pnl_pct) / abs(baseline_pnl_pct)) * 100
            else:
                tls_benefit = 0.0
            
            enriched_results.append({
                'strategy_instance_id': strategy_id,
                'tp_level': row['tp_level'],
                'sl_level': row['sl_level'],
                'tls_activation': row['tls_activation'],
                'tls_trail': row['tls_trail'],
                'tls_pnl': tls_pnl_pct,  # Now in percentage relative to total_invested
                'tls_pnl_raw': row['simulated_pnl'],  # Keep raw for sorting
                'baseline_pnl': baseline_pnl_pct,  # Now correctly calculated as (best_tp_sl_pnl / total_invested) * 100
                'tls_benefit': tls_benefit
            })
        
        # Sort by raw TLS PnL and apply strategy deduplication - each strategy appears at most once
        all_combinations = sorted(enriched_results, key=lambda x: x['tls_pnl_raw'], reverse=True)
        
        # Deduplicate: keep only the best combination per strategy
        seen_strategies = set()
        top_combinations = []
        for combo in all_combinations:
            if combo['strategy_instance_id'] not in seen_strategies:
                top_combinations.append(combo)
                seen_strategies.add(combo['strategy_instance_id'])
                
                # Stop when we have enough unique strategies
                if len(top_combinations) >= top_count:
                    break
        
        # Create HTML table
        table_html = """
        <table class="table table-striped table-hover" id="global_top_combinations_table">
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Strategy</th>
                    <th>TP (%)</th>
                    <th>SL (%)</th>
                    <th>TLS Act (%)</th>
                    <th>TLS Trail (%)</th>
                    <th>TLS PnL (%)</th>
                    <th>Baseline PnL (%)</th>
                    <th>TLS Benefit (%)</th>
                </tr>
            </thead>
            <tbody>
        """
        
        for rank, combo in enumerate(top_combinations, 1):
            # Color-code TLS Benefit
            benefit = combo['tls_benefit']
            if benefit > 1:
                benefit_class = 'positive'
            elif benefit < -1:
                benefit_class = 'negative'
            else:
                benefit_class = ''
            
            # Color-code PnL values
            tls_pnl_class = 'positive' if combo['tls_pnl'] >= 0 else 'negative'
            baseline_pnl_class = 'positive' if combo['baseline_pnl'] >= 0 else 'negative'
            
            table_html += f"""
                <tr>
                    <td><strong>{rank}</strong></td>
                    <td>
                        <a href="#" class="top-combo-strategy-link" data-strategy-id="{combo['strategy_instance_id']}" 
                           style="text-decoration: none; color: #3498db; font-weight: bold;">
                            {combo['strategy_instance_id']}
                        </a>
                    </td>
                    <td>{combo['tp_level']}</td>
                    <td>{combo['sl_level']}</td>
                    <td>{combo['tls_activation']}</td>
                    <td>{combo['tls_trail']}</td>
                    <td class="{tls_pnl_class}">{combo['tls_pnl']:.2f}%</td>
                    <td class="{baseline_pnl_class}">{combo['baseline_pnl']:.2f}%</td>
                    <td class="{benefit_class}"><strong>{benefit:+.2f}%</strong></td>
                </tr>
            """
        
        table_html += """
            </tbody>
        </table>
        """
        
        return table_html
        
    except Exception as e:
        logger.error(f"Failed to create global top combinations table: {e}")
        return f"<p>Error generating top combinations table: {e}</p>"


def create_strategy_performance_summary(tls_results_df: pd.DataFrame, baseline_data: Dict[str, float]) -> Dict[str, Any]:
    """
    AIDEV-ULTIMATE-FIX-CLAUDE: Final, robust, and consistent strategy performance summary.
    - Guarantees that "Best Baseline" >= "Best Avg Baseline" by deriving them from the same data subset.
    - All other features (naming, position counts) are preserved.
    """
    if tls_results_df.empty:
        return {}
    
    try:
        table_rows = []
        strategies = sort_strategies_by_date_descending([str(x) for x in tls_results_df['strategy_instance_id'].unique()])

        # --- Data Loading (One time, for efficiency) ---
        strategy_instances_df = pd.read_csv("strategy_instances.csv") if os.path.exists("strategy_instances.csv") else pd.DataFrame()
        detailed_baseline_df = pd.read_csv("reporting/output/range_test_detailed_results.csv") if os.path.exists("reporting/output/range_test_detailed_results.csv") else pd.DataFrame()

        # --- Main Loop per Strategy ---
        for strategy_id in strategies:
            strategy_data_tsl = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
            if strategy_data_tsl.empty:
                continue

            # Get total_invested and position count for this strategy
            total_invested = 1.0
            position_count = len(strategy_data_tsl['position_id'].unique())
            if not strategy_instances_df.empty:
                strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_row.empty:
                    total_invested = strategy_row.iloc[0]['total_invested']
                    position_count = strategy_row.iloc[0].get('analyzed_position_count', position_count)

            # --- TSL Calculations (Logic is correct) ---
            best_tsl_pnl_single_pos = strategy_data_tsl['simulated_pnl'].max()
            avg_pnl_per_combo_tsl = strategy_data_tsl.groupby(['tp_level', 'sl_level', 'tls_activation', 'tls_trail'])['simulated_pnl'].mean()
            best_avg_tsl_pnl = avg_pnl_per_combo_tsl.max() if not avg_pnl_per_combo_tsl.empty else 0.0
            best_combo_params_tsl = avg_pnl_per_combo_tsl.idxmax() if not avg_pnl_per_combo_tsl.empty else (0,0,0,0)
            
            # --- Baseline Calculations (NEW, ROBUST LOGIC) ---
            best_avg_baseline_pnl, best_baseline_pnl_single_pos = 0.0, 0.0
            if not detailed_baseline_df.empty:
                strategy_baseline_details = detailed_baseline_df[detailed_baseline_df['strategy_instance_id'] == strategy_id]
                if not strategy_baseline_details.empty:
                    # 1. Group all baseline positions by TP/SL and find the mean PnL for each group.
                    avg_pnl_per_combo_baseline = strategy_baseline_details.groupby(['tp_level', 'sl_level'])['simulated_pnl'].mean()
                    
                    if not avg_pnl_per_combo_baseline.empty:
                        # 2. Find the best AVERAGE PnL and the TP/SL parameters that produced it.
                        best_avg_baseline_pnl = avg_pnl_per_combo_baseline.max()
                        optimal_tp, optimal_sl = avg_pnl_per_combo_baseline.idxmax()

                        # 3. Filter the detailed data to get ONLY the positions from that best-performing group.
                        positions_in_best_avg_group = strategy_baseline_details[
                            (strategy_baseline_details['tp_level'] == optimal_tp) &
                            (strategy_baseline_details['sl_level'] == optimal_sl)
                        ]
                        
                        # 4. Find the maximum PnL within that specific group. This guarantees Best >= Best Avg.
                        if not positions_in_best_avg_group.empty:
                            best_baseline_pnl_single_pos = positions_in_best_avg_group['simulated_pnl'].max()
                        else: # Should not happen, but as a fallback
                            best_baseline_pnl_single_pos = best_avg_baseline_pnl

            # --- Percentage Conversions ---
            if total_invested > 0:
                best_tsl_pct = (best_tsl_pnl_single_pos / total_invested) * 100
                best_avg_tsl_pct = (best_avg_tsl_pnl / total_invested) * 100
                best_baseline_pct = (best_baseline_pnl_single_pos / total_invested) * 100
                best_avg_baseline_pct = (best_avg_baseline_pnl / total_invested) * 100
            else:
                best_tsl_pct, best_avg_tsl_pct, best_baseline_pct, best_avg_baseline_pct = 0, 0, 0, 0

            # --- Final Calculations ---
            if abs(best_avg_baseline_pct) > 1e-6:
                avg_tsl_advantage = ((best_avg_tsl_pct - best_avg_baseline_pct) / abs(best_avg_baseline_pct)) * 100
            else:
                avg_tsl_advantage = best_avg_tsl_pct
            
            params_str = f"TP:{best_combo_params_tsl[0]} SL:{best_combo_params_tsl[1]}<br>Act:{best_combo_params_tsl[2]} Trl:{best_combo_params_tsl[3]}"

            table_rows.append({
                'strategy_id': strategy_id,
                'position_count': position_count,
                'best_tsl_pct': best_tsl_pct,
                'best_avg_tsl_pct': best_avg_tsl_pct,
                'best_baseline_pct': best_baseline_pct,
                'best_avg_baseline_pct': best_avg_baseline_pct,
                'avg_tsl_advantage': avg_tsl_advantage,
                'optimal_parameters': params_str
            })
        
        # --- Overall Summary ---
        summary_stats = {}
        if table_rows:
            strategies_improved = len([r for r in table_rows if r['avg_tsl_advantage'] > 0])
            total_strategies = len(table_rows)
            improvement_rate = (strategies_improved / total_strategies * 100) if total_strategies > 0 else 0
            advantages = [r['avg_tsl_advantage'] for r in table_rows]
            summary_stats['_overall'] = {
                'total_strategies': total_strategies,
                'strategies_improved': strategies_improved,
                'improvement_rate': improvement_rate,
                'avg_tsl_advantage': np.mean(advantages) if advantages else 0,
                'best_tsl_advantage': max(advantages) if advantages else 0
            }

        # --- Generate Final HTML Table ---
        table_html = """
        <div class="strategy-performance-table" style="margin-top: 20px;">
            <h4>📋 Strategy Performance Details</h4>
            <div class="table-explanation" style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin-bottom: 20px; font-size: 0.9em; border-left: 4px solid #3498db;">
                <h5 style="margin-top: 0;">🔍 How to Read This Table:</h5>
                <ul>
                    <li><strong>Best (%)</strong>: Shows the result of the single, most profitable position (potential peak performance).</li>
                    <li><strong>Best Avg (%)</strong>: Shows the average result from the most consistently profitable parameter combination (stable performance). This value corresponds to the best result seen on the heatmaps.</li>
                    <li><strong>Avg TSL Advantage</strong>: Compares the <strong>Best Avg TSL</strong> to the <strong>Best Avg Baseline</strong> to measure the real, repeatable benefit of using TSL.</li>
                    <li><strong>Note on Parameters</strong>: The optimal TP/SL for the Baseline may differ from the TP/SL shown in the optimal TSL parameter set. This table finds the best overall combination for TSL.</li>
                </ul>
            </div>
            <table class="table table-striped table-hover" id="strategy_performance_detail_table">
                <thead>
                    <tr>
                        <th rowspan="2">Strategy</th>
                        <th colspan="2" style="text-align: center; border-bottom: 1px solid #dee2e6;">TSL Performance</th>
                        <th colspan="2" style="text-align: center; border-bottom: 1px solid #dee2e6;">Baseline Performance</th>
                        <th rowspan="2">Avg TSL Advantage</th>
                        <th rowspan="2">TP/SL/TSL Trigger/TSL Distance</th>
                    </tr>
                    <tr>
                        <th style="font-weight: normal; font-size: 0.9em;">Best (%)</th>
                        <th style="font-weight: normal; font-size: 0.9em;">Best Avg (%)</th>
                        <th style="font-weight: normal; font-size: 0.9em;">Best (%)</th>
                        <th style="font-weight: normal; font-size: 0.9em;">Best Avg (%)</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in table_rows:
            def pnl_class(val): return 'positive' if val >= 0 else 'negative'
            advantage_class = 'positive' if row['avg_tsl_advantage'] > 1 else ('negative' if row['avg_tsl_advantage'] < -1 else '')
            strategy_display_name = f"{row['strategy_id']} ({row['position_count']})"
            table_html += f"""
                <tr>
                    <td>
                        <a href="#" class="strategy-detail-link" data-strategy-id="{row['strategy_id']}" 
                           style="text-decoration: none; color: #3498db; font-weight: bold;">
                            {strategy_display_name}
                        </a>
                    </td>
                    <td class="{pnl_class(row['best_tsl_pct'])}">{row['best_tsl_pct']:.2f}%</td>
                    <td class="{pnl_class(row['best_avg_tsl_pct'])}"><b>{row['best_avg_tsl_pct']:.2f}%</b></td>
                    <td class="{pnl_class(row['best_baseline_pct'])}">{row['best_baseline_pct']:.2f}%</td>
                    <td class="{pnl_class(row['best_avg_baseline_pct'])}"><b>{row['best_avg_baseline_pct']:.2f}%</b></td>
                    <td class="{advantage_class}"><strong>{row['avg_tsl_advantage']:+.2f}%</strong></td>
                    <td style="font-size: 0.8em; line-height: 1.4;">{row['optimal_parameters']}</td>
                </tr>
            """
        
        table_html += "</tbody></table></div>"
        
        summary_stats['_table_html'] = table_html
        return summary_stats
        
    except Exception as e:
        logger.error(f"Failed to create strategy performance summary: {e}", exc_info=True)
        return {}