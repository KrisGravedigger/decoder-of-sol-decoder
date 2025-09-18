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
    Generate strategy-level performance insights.
    
    Metrics per strategy:
    - Best TLS Performance: Highest PnL with TLS enabled
    - Best Baseline Performance: Best TP/SL performance as percentage of total invested
    - TLS Advantage: Percentage improvement of best TLS vs baseline
    - Optimization Potential: Range between worst and best TLS results
    - Parameter Sensitivity: Standard deviation of TLS results
    
    Args:
        tls_results_df: DataFrame with TLS simulation results
        baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl
        
    Returns:
        Dictionary with summary statistics and HTML table for HTML template
    """
    if tls_results_df.empty:
        return {}
    
    try:
        summary_stats = {}
        table_rows = []
        
        # Sort strategies by date (newest first) for consistent ordering
        strategies = sort_strategies_by_date_descending([str(x) for x in tls_results_df['strategy_instance_id'].unique()])
        
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
        
        for strategy_id in strategies:
            strategy_data = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
            baseline_pnl = baseline_data.get(strategy_id, 0.0)
            
            if strategy_data.empty:
                continue
            
            # Get total_invested for this strategy for correct baseline percentage calculation
            total_invested = 1.0  # Default fallback
            if strategy_instances_df is not None:
                strategy_row = strategy_instances_df[strategy_instances_df['strategy_instance_id'] == strategy_id]
                if not strategy_row.empty:
                    total_invested = strategy_row.iloc[0]['total_invested']
            
            best_tls_pnl = strategy_data['simulated_pnl'].max()
            worst_tls_pnl = strategy_data['simulated_pnl'].min()
            avg_tls_pnl = strategy_data['simulated_pnl'].mean()
            std_tls_pnl = strategy_data['simulated_pnl'].std()
            
            # Calculate correct baseline PnL percentage: (best_tp_sl_pnl / total_invested) * 100
            optimal_tp_sl_pnl = optimal_tp_sl_data.get(strategy_id, baseline_pnl)
            baseline_pnl_pct = (optimal_tp_sl_pnl / total_invested * 100) if total_invested > 0 else 0.0
            
            # Convert to percentage using total_invested as denominator for consistency
            if total_invested > 0:
                best_tls_pnl_pct = (best_tls_pnl / total_invested) * 100
                avg_tls_pnl_pct = (avg_tls_pnl / total_invested) * 100
                optimization_potential_pct = ((best_tls_pnl - worst_tls_pnl) / total_invested) * 100
            else:
                # Fallback: treat values as percentage-like
                best_tls_pnl_pct = best_tls_pnl * 100
                avg_tls_pnl_pct = avg_tls_pnl * 100
                optimization_potential_pct = (best_tls_pnl - worst_tls_pnl) * 100
            
            # Calculate TLS Advantage using the PERCENTAGE values (not raw values)
            # Formula: ((Best_TLS_PnL% - Baseline_PnL%) / Baseline_PnL%) * 100
            if baseline_pnl_pct != 0:
                tls_advantage = ((best_tls_pnl_pct - baseline_pnl_pct) / abs(baseline_pnl_pct)) * 100
            else:
                tls_advantage = 0.0
            
            optimization_potential = best_tls_pnl - worst_tls_pnl
            
            summary_stats[strategy_id] = {
                'best_tls_pnl': best_tls_pnl,
                'baseline_pnl': baseline_pnl,
                'tls_advantage': tls_advantage,
                'optimization_potential': optimization_potential,
                'parameter_sensitivity': std_tls_pnl,
                'avg_performance': avg_tls_pnl,
                'total_combinations': len(strategy_data)
            }
            
            # Add row for HTML table
            table_rows.append({
                'strategy_id': strategy_id,
                'best_tls_pnl_pct': best_tls_pnl_pct,
                'baseline_pnl_pct': baseline_pnl_pct,
                'tls_advantage': tls_advantage,
                'avg_performance_pct': avg_tls_pnl_pct,
                'optimization_potential_pct': optimization_potential_pct,
                'total_combinations': len(strategy_data)
            })
        
        # Calculate overall summary metrics
        if summary_stats:
            strategies_improved = len([s for s in summary_stats.values() if s['tls_advantage'] > 0])
            total_strategies = len(summary_stats)
            improvement_rate = (strategies_improved / total_strategies * 100) if total_strategies > 0 else 0
            
            avg_advantage = np.mean([s['tls_advantage'] for s in summary_stats.values()])
            best_advantage = max([s['tls_advantage'] for s in summary_stats.values()])
            
            summary_stats['_overall'] = {
                'total_strategies': total_strategies,
                'strategies_improved': strategies_improved,
                'improvement_rate': improvement_rate,
                'avg_tls_advantage': avg_advantage,
                'best_tls_advantage': best_advantage
            }
        
        # Generate HTML table for per-strategy details
        table_html = """
        <div class="strategy-performance-table" style="margin-top: 20px;">
            <h4>📋 Strategy Performance Details</h4>
            <table class="table table-striped table-hover" id="strategy_performance_detail_table">
                <thead>
                    <tr>
                        <th>Strategy</th>
                        <th>Best TLS (%)</th>
                        <th>Baseline (%)</th>
                        <th>TLS Advantage</th>
                        <th>Avg Performance (%)</th>
                        <th>Optimization Range (%)</th>
                        <th>Combinations Tested</th>
                    </tr>
                </thead>
                <tbody>
        """
        
        for row in table_rows:
            # Color-code TLS advantage
            advantage_class = 'positive' if row['tls_advantage'] > 1 else ('negative' if row['tls_advantage'] < -1 else '')
            best_tls_class = 'positive' if row['best_tls_pnl_pct'] >= 0 else 'negative'
            baseline_class = 'positive' if row['baseline_pnl_pct'] >= 0 else 'negative'
            
            table_html += f"""
                <tr>
                    <td>
                        <a href="#" class="strategy-detail-link" data-strategy-id="{row['strategy_id']}" 
                           style="text-decoration: none; color: #3498db; font-weight: bold;">
                            {row['strategy_id']}
                        </a>
                    </td>
                    <td class="{best_tls_class}">{row['best_tls_pnl_pct']:.2f}%</td>
                    <td class="{baseline_class}">{row['baseline_pnl_pct']:.2f}%</td>
                    <td class="{advantage_class}"><strong>{row['tls_advantage']:+.2f}%</strong></td>
                    <td>{row['avg_performance_pct']:.2f}%</td>
                    <td>{row['optimization_potential_pct']:.2f}%</td>
                    <td>{row['total_combinations']}</td>
                </tr>
            """
        
        table_html += """
                </tbody>
            </table>
        </div>
        """
        
        summary_stats['_table_html'] = table_html
        
        return summary_stats
        
    except Exception as e:
        logger.error(f"Failed to create strategy performance summary: {e}")
        return {}