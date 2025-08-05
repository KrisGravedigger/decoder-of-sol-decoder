"""
TP/SL Optimizer Engine for Phase 5

Provides prescriptive analytics to identify statistically optimal TP/SL parameters
per strategy based on historical simulation data.
"""

import logging
import yaml
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import os

logger = logging.getLogger(__name__)


class TpSlOptimizer:
    """
    Optimization engine that analyzes pre-computed simulation data to provide
    actionable TP/SL recommendations with net effect analysis and EV-based floors.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize optimizer with configuration and load data.
        
        Args:
            config_path: Path to portfolio configuration file
        """
        self.config = self._load_config(config_path)
        self.optimization_config = self.config.get('optimization_engine', {})
        
        # Check if optimization is enabled
        if not self.optimization_config.get('enable', False):
            raise ValueError("Optimization engine is disabled in configuration")
        
        # Load required data files
        self._load_data_files()
        
        # Time weighting configuration
        self.time_weighting_enabled = self.optimization_config.get('time_weighting', {}).get('enable', True)
        self.last_n_days_full_weight = self.optimization_config.get('time_weighting', {}).get('last_n_days_full_weight', 7)
        self.decay_period_weeks = self.optimization_config.get('time_weighting', {}).get('decay_period_weeks', 4)
        self.minimum_weight = self.optimization_config.get('time_weighting', {}).get('minimum_weight', 0.5)
        
        # Statistical significance threshold
        self.min_positions_for_optimization = self.optimization_config.get('min_positions_for_optimization', 30)
        
        logger.info(f"TP/SL Optimizer initialized with time weighting: {self.time_weighting_enabled}")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
            
    def _load_data_files(self):
        """Load required CSV files."""
        try:
            # Load simulation results
            self.detailed_results = pd.read_csv("reporting/output/range_test_detailed_results.csv")
            logger.info(f"Loaded {len(self.detailed_results)} simulation results")
            
            # Load positions data
            self.positions_df = pd.read_csv("positions_to_analyze.csv")
            # Parse timestamps
            from reporting.data_loader import _parse_custom_timestamp
            self.positions_df['open_timestamp'] = self.positions_df['open_timestamp'].apply(_parse_custom_timestamp)
            self.positions_df['close_timestamp'] = self.positions_df['close_timestamp'].apply(_parse_custom_timestamp)
            logger.info(f"Loaded {len(self.positions_df)} positions")
            
            # Load strategy instances
            self.strategy_instances = pd.read_csv("strategy_instances.csv")
            logger.info(f"Loaded {len(self.strategy_instances)} strategy instances")
            
        except FileNotFoundError as e:
            logger.error(f"Required data file not found: {e}")
            raise
            
    def run_optimization(self) -> Dict[str, Any]:
        """
        Main entry point to run the complete optimization analysis.
        
        Returns:
            Dictionary containing optimization results and visualizations
        """
        logger.info("Starting TP/SL optimization analysis...")
        
        # Filter strategies with sufficient positions
        qualified_strategies = self.strategy_instances[
            self.strategy_instances['analyzed_position_count'] >= self.min_positions_for_optimization
        ]['strategy_instance_id'].tolist()
        
        logger.info(f"Found {len(qualified_strategies)} strategies with >= {self.min_positions_for_optimization} positions")
        
        if not qualified_strategies:
            return {
                'status': 'NO_QUALIFIED_STRATEGIES',
                'message': f'No strategies found with at least {self.min_positions_for_optimization} positions'
            }
            
        # Run optimization for each qualified strategy
        optimization_results = {}
        successfully_analyzed = 0
        
        for strategy_id in qualified_strategies:
            logger.info(f"Optimizing strategy: {strategy_id}")
            
            # Get strategy data - ensure we have simulation results
            strategy_data = self.detailed_results[
                self.detailed_results['strategy_instance_id'] == strategy_id
            ].copy()
            
            # Verify we have the required simulation data
            if 'simulated_pnl_pct' not in strategy_data.columns:
                logger.error(f"Missing simulated_pnl_pct data for strategy {strategy_id}")
                continue
            
            # Merge with position timestamps for time weighting
            strategy_data = strategy_data.merge(
                self.positions_df[['position_id', 'open_timestamp']],
                on='position_id',
                how='left'
            )
            
            # Apply time weighting if enabled
            if self.time_weighting_enabled:
                strategy_data = self._apply_time_weighting(strategy_data)
            else:
                strategy_data['weight'] = 1.0
                
            # Calculate net effect for each TP/SL combination
            net_effect_results = self._calculate_net_effect(strategy_id, strategy_data)
            
            if net_effect_results.empty:
                logger.warning(f"No net effect results for strategy {strategy_id}")
                continue
                
            successfully_analyzed += 1
            
            # Find optimal TP/SL combination
            optimal_combo = net_effect_results.loc[net_effect_results['net_pnl_impact'].idxmax()]
            
            # Calculate EV-based SL floor analysis
            sl_floor_analysis = self._calculate_ev_based_sl_floor(strategy_data)

            optimization_results[strategy_id] = {
                'net_effect_matrix': net_effect_results,
                'optimal_tp': optimal_combo['tp_level'],
                'optimal_sl': optimal_combo['sl_level'],
                'optimal_net_impact': optimal_combo['net_pnl_impact'],
                'sl_floor_analysis': sl_floor_analysis,  # Now a DataFrame instead of Dict
                'position_count': len(strategy_data['position_id'].unique()),
                'time_weighted': self.time_weighting_enabled
            }
            
        # Generate visualizations
        visualizations = self._generate_visualizations(optimization_results)
        
        return {
            'status': 'SUCCESS',
            'optimization_results': optimization_results,
            'visualizations': visualizations,
            'summary': self._generate_summary(optimization_results, successfully_analyzed),
            'timestamp': datetime.now().isoformat()
        }
        
    def _calculate_net_effect(self, strategy_id: str, strategy_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate net PnL impact for each TP/SL combination for a strategy.
        
        Categorizes each position's outcome as Improved/Neutral/Degraded
        relative to baseline performance.
        """
        # Get strategy's baseline TP/SL from strategy_instances
        baseline_info = self.strategy_instances[
            self.strategy_instances['strategy_instance_id'] == strategy_id
        ].iloc[0]
        
        baseline_tp = baseline_info['takeProfit']
        baseline_sl = baseline_info['stopLoss']
        
        # Find baseline performance for each position
        baseline_data = strategy_data[
            (strategy_data['tp_level'] == baseline_tp) & 
            (strategy_data['sl_level'] == baseline_sl)
        ][['position_id', 'simulated_pnl_pct', 'weight']].rename(
            columns={'simulated_pnl_pct': 'baseline_pnl_pct'}
        )
        
        # Merge baseline with all combinations
        merged_data = strategy_data.merge(baseline_data, on='position_id', suffixes=('', '_baseline'))
        
        # Calculate improvement
        merged_data['pnl_improvement'] = merged_data['simulated_pnl_pct'] - merged_data['baseline_pnl_pct']
        
        # Categorize positions
        merged_data['impact_category'] = pd.cut(
            merged_data['pnl_improvement'],
            bins=[-np.inf, -0.1, 0.1, np.inf],
            labels=['Degraded', 'Neutral', 'Improved']
        )
        
        # Calculate weighted net effect for each TP/SL combination
        net_effects = []
        
        for (tp, sl), group in merged_data.groupby(['tp_level', 'sl_level']):
            # Use the weight from time decay
            weighted_improvement = (group['pnl_improvement'] * group['weight']).sum()
            total_weight = group['weight'].sum()
            
            net_pnl_impact = weighted_improvement / total_weight if total_weight > 0 else 0
            
            # Count categories
            category_counts = group['impact_category'].value_counts()
            
            # AIDEV-NOTE-CLAUDE: PnL-based win rate - a win is any exit with positive PnL
            # This correctly handles TP, OOR, and END scenarios based on actual profitability
            wins_weight = group[group['simulated_pnl_pct'] > 0]['weight'].sum()
            total_weight = group['weight'].sum()
            
            weighted_win_rate = (wins_weight / total_weight * 100) if total_weight > 0 else 0
            
            net_effects.append({
                'tp_level': tp,
                'sl_level': sl,
                'net_pnl_impact': net_pnl_impact,
                'improved_count': category_counts.get('Improved', 0),
                'neutral_count': category_counts.get('Neutral', 0),
                'degraded_count': category_counts.get('Degraded', 0),
                'total_positions': len(group),
                'weighted_win_rate': weighted_win_rate
            })
            
        return pd.DataFrame(net_effects)
        
    def _calculate_ev_based_sl_floor(self, strategy_data: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate EV analysis for all TP/SL combinations.
        
        Returns a DataFrame with detailed breakdown of historical vs required win rates
        for debugging and visualization purposes.
        """
        ev_analysis_results = []
        
        # Get unique TP and SL levels
        tp_levels = sorted(strategy_data['tp_level'].unique())
        sl_levels = sorted(strategy_data['sl_level'].unique())
        
        for tp in tp_levels:
            tp_data = strategy_data[strategy_data['tp_level'] == tp]
            
            for sl in sl_levels:
                sl_data = tp_data[tp_data['sl_level'] == sl]
                
                if len(sl_data) == 0:
                    # Add empty row for missing combinations
                    ev_analysis_results.append({
                        'tp_level': tp,
                        'sl_level': sl,
                        'historical_win_rate': 0.0,
                        'required_win_rate': sl / (tp + sl),
                        'sample_size': 0,
                        'is_viable': False,
                        'margin': -1.0
                    })
                    continue
                
                # AIDEV-NOTE-CLAUDE: PnL-based win rate - a win is any exit with positive PnL
                # This correctly handles TP, OOR, and END scenarios based on actual profitability
                
                # First, we need to get the simulated results for this TP/SL combination
                # from the detailed results that should be available in the strategy data
                tp_sl_data = strategy_data[
                    (strategy_data['tp_level'] == tp) & 
                    (strategy_data['sl_level'] == sl)
                ]
                
                if len(tp_sl_data) == 0:
                    continue
                
                wins_weight = tp_sl_data[tp_sl_data['simulated_pnl_pct'] > 0]['weight'].sum()
                total_weight = tp_sl_data['weight'].sum()
                
                if total_weight == 0:
                    continue
                    
                historical_win_rate = wins_weight / total_weight
                
                # Calculate required win rate
                required_win_rate = sl / (tp + sl)
                
                # Check viability
                is_viable = historical_win_rate > required_win_rate
                margin = historical_win_rate - required_win_rate
                
                # Store all data for debugging
                ev_analysis_results.append({
                    'tp_level': tp,
                    'sl_level': sl,
                    'historical_win_rate': historical_win_rate,
                    'required_win_rate': required_win_rate,
                    'sample_size': len(sl_data),
                    'is_viable': is_viable,
                    'margin': margin,
                    'tp_count': len(sl_data[sl_data['exit_reason'] == 'TP']),
                    'sl_count': len(sl_data[sl_data['exit_reason'] == 'SL']),
                    'end_count': len(sl_data[sl_data['exit_reason'] == 'END'])
                })
        
        # Convert to DataFrame for easier manipulation
        ev_df = pd.DataFrame(ev_analysis_results)
        
        # Log debug information
        viable_count = ev_df['is_viable'].sum()
        logger.info(f"EV Analysis: {viable_count}/{len(ev_df)} TP/SL combinations are viable")
        
        if viable_count == 0:
            # Log why nothing is viable
            best_margin = ev_df.loc[ev_df['margin'].idxmax()]
            logger.warning(f"No viable SL floors found. Best margin was {best_margin['margin']:.3f} "
                        f"at TP={best_margin['tp_level']}%, SL={best_margin['sl_level']}% "
                        f"(Historical: {best_margin['historical_win_rate']:.3f}, "
                        f"Required: {best_margin['required_win_rate']:.3f})")
        
        return ev_df
        
    def _apply_time_weighting(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Apply time-based weighting to positions based on open_timestamp.
        
        Recent positions get higher weights according to configuration.
        """
        df = df.copy()
        
        # Calculate days since position opened
        current_date = pd.Timestamp.now()
        df['days_since_open'] = (current_date - df['open_timestamp']).dt.days
        
        # Apply weighting formula
        def calculate_weight(days_since_open):
            if days_since_open <= self.last_n_days_full_weight:
                return 1.0
            
            # Calculate decay
            days_in_decay = days_since_open - self.last_n_days_full_weight
            weeks_in_decay = days_in_decay / 7.0
            
            # Linear decay
            decay_rate = (1.0 - self.minimum_weight) / (self.decay_period_weeks)
            weight = 1.0 - (decay_rate * weeks_in_decay)
            
            return max(self.minimum_weight, min(1.0, weight))
            
        df['weight'] = df['days_since_open'].apply(calculate_weight)
        
        logger.debug(f"Applied time weighting: min={df['weight'].min():.2f}, "
                    f"max={df['weight'].max():.2f}, mean={df['weight'].mean():.2f}")
        
        return df
        
    def _generate_visualizations(self, optimization_results: Dict) -> Dict[str, str]:
        """
        Generate the three required visualizations:
        1. Strategy Performance Matrix
        2. Win Rate vs Required Win Rate Chart
        3. Dynamic SL Floor Table
        """
        visualizations = {}
        
        # 1. Strategy Performance Matrix
        matrix_fig = self._create_performance_matrix(optimization_results)
        visualizations['performance_matrix'] = matrix_fig.to_html(div_id="performance_matrix")
        
        # 2. Win Rate vs Required Win Rate Chart (for top strategy)
        if optimization_results:
            # Get the strategy with highest optimal net impact
            best_strategy = max(optimization_results.items(), 
                              key=lambda x: x[1]['optimal_net_impact'])[0]
            
            win_rate_fig = self._create_win_rate_chart(
                best_strategy, 
                optimization_results[best_strategy]
            )
            visualizations['win_rate_chart'] = win_rate_fig.to_html(div_id="win_rate_chart")
            
        # 3. Dynamic SL Floor Table
        sl_floor_fig = self._create_sl_floor_table(optimization_results)
        visualizations['sl_floor_table'] = sl_floor_fig.to_html(div_id="sl_floor_table")
        
        return visualizations
        
    def _create_performance_matrix(self, optimization_results: Dict) -> go.Figure:
        """Create interactive table showing net PnL impact for each strategy."""
        data = []
        
        # AIDEV-TODO-CLAUDE: Significance threshold of 0.1 could be made configurable in the future
        significance_threshold = 0.1
        
        for strategy_id, results in optimization_results.items():
            # Get strategy name components
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
            # Check if improvement meets significance threshold
            if abs(results['optimal_net_impact']) > significance_threshold:
                optimal_tp = f"{results['optimal_tp']}%"
                optimal_sl = f"{results['optimal_sl']}%"
                net_impact = f"{results['optimal_net_impact']:.2f}%"
            else:
                optimal_tp = "No significant improvement"
                optimal_sl = "No significant improvement"
                net_impact = "~0.00%"
            
            data.append({
                'Strategy': strategy_id,
                'Current TP': f"{strategy_info['takeProfit']}%",
                'Current SL': f"{strategy_info['stopLoss']}%",
                'Optimal TP': optimal_tp,
                'Optimal SL': optimal_sl,
                'Net Impact': net_impact,
                'Positions': results['position_count'],
                'Weighted': '✓' if results['time_weighted'] else '✗'
            })
            
        df = pd.DataFrame(data)
        
        # Create color scale for Net Impact
        colors = []
        for impact_str in df['Net Impact']:
            if impact_str == "~0.00%":
                colors.append('lightgray')
            else:
                impact_val = float(impact_str.strip('%'))
                colors.append('red' if impact_val < 0 else 'green')
        
        fig = go.Figure(data=[go.Table(
            header=dict(
                values=list(df.columns),
                fill_color='paleturquoise',
                align='left',
                font=dict(size=12, color='black')
            ),
            cells=dict(
                values=[df[col] for col in df.columns],
                fill_color=[['white']*len(df) if i != 5 
                           else colors for i in range(len(df.columns))],
                align='left',
                font=dict(size=11)
            )
        )])
        
        fig.update_layout(
            title="Strategy Performance Matrix - Net PnL Impact of Optimal TP/SL",
            height=400 + len(data) * 30,
            margin=dict(l=0, r=0, t=40, b=0)
        )
        
        return fig
        
    def _create_win_rate_chart(self, strategy_id: str, strategy_results: Dict) -> go.Figure:
        """
        Create comprehensive win rate visualization showing both historical and required rates.
        """
        ev_analysis_df = strategy_results['sl_floor_analysis']
        
        # Prepare data
        tp_levels = sorted(ev_analysis_df['tp_level'].unique())
        sl_levels = sorted(ev_analysis_df['sl_level'].unique())
        
        fig = go.Figure()
        
        # Color palette for different TP levels
        colors = px.colors.qualitative.Set1
        
        # Add lines for each TP level
        for i, tp in enumerate(tp_levels):
            color = colors[i % len(colors)]
            tp_data = ev_analysis_df[ev_analysis_df['tp_level'] == tp]
            
            # Required win rate line (theoretical)
            fig.add_trace(go.Scatter(
                x=tp_data['sl_level'],
                y=tp_data['required_win_rate'] * 100,
                mode='lines',
                name=f'Required (TP={tp}%)',
                line=dict(color=color, dash='dash', width=2),
                legendgroup=f'tp{tp}'
            ))
            
            # Historical win rate line (actual)
            fig.add_trace(go.Scatter(
                x=tp_data['sl_level'],
                y=tp_data['historical_win_rate'] * 100,
                mode='lines+markers',
                name=f'Historical (TP={tp}%)',
                line=dict(color=color, width=3),
                marker=dict(size=8),
                legendgroup=f'tp{tp}',
                customdata=tp_data[['sample_size', 'tp_count', 'sl_count', 'end_count']],
                hovertemplate=(
                    'SL: %{x}%<br>' +
                    'Win Rate: %{y:.1f}%<br>' +
                    'Sample Size: %{customdata[0]}<br>' +
                    'TP/SL/END: %{customdata[1]}/%{customdata[2]}/%{customdata[3]}<br>' +
                    '<extra></extra>'
                )
            ))
            
        # Add viability zones if any exist
        viable_zones = ev_analysis_df[ev_analysis_df['is_viable'] == True]
        if not viable_zones.empty:
            for tp in tp_levels:
                tp_viable = viable_zones[viable_zones['tp_level'] == tp]
                if not tp_viable.empty:
                    deepest_viable_sl = tp_viable['sl_level'].max()
                    
                    fig.add_shape(
                        type="rect",
                        x0=deepest_viable_sl,
                        x1=max(sl_levels),
                        y0=0,
                        y1=100,
                        fillcolor="green",
                        opacity=0.1,
                        layer="below",
                        line_width=0,
                    )
                    fig.add_annotation(
                        x=deepest_viable_sl + 0.5,
                        y=95,
                        text=f"Viable zone<br>TP={tp}%",
                        showarrow=False,
                        font=dict(size=10)
                    )
        else:
            # Add annotation explaining no viable zones
            fig.add_annotation(
                x=np.mean(sl_levels),
                y=50,
                text="No viable SL levels found<br>(Historical win rate < Required win rate for all combinations)",
                showarrow=False,
                font=dict(size=12, color="red"),
                bgcolor="white",
                bordercolor="red",
                borderwidth=2
            )
        
        # Add a reference line at 50% win rate
        fig.add_hline(
            y=50, 
            line_dash="dot", 
            line_color="gray",
            annotation_text="50% Win Rate",
            annotation_position="bottom right"
        )
        
        fig.update_layout(
            title=f"Win Rate Analysis - {strategy_id}<br><sub>Comparing Historical Performance vs Mathematical Requirements</sub>",
            xaxis_title="Stop Loss Level (%)",
            yaxis_title="Win Rate (%)",
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            height=600,
            showlegend=True,
            legend=dict(
                groupclick="toggleitem",
                tracegroupgap=10
            )
        )
        
        return fig
        
    def _create_sl_floor_table(self, optimization_results: Dict) -> go.Figure:
        """Create summary table showing deepest viable SL for each TP level."""
        data = []
        
        for strategy_id, results in optimization_results.items():
            strategy_name = strategy_id.split('_')[0]  # Short name
            ev_analysis_df = results['sl_floor_analysis']
            
            # Filter for viable combinations only
            viable_df = ev_analysis_df[ev_analysis_df['is_viable'] == True]
            
            if not viable_df.empty:
                # For each TP level, find the deepest viable SL
                for tp in sorted(viable_df['tp_level'].unique()):
                    tp_viable = viable_df[viable_df['tp_level'] == tp]
                    deepest_row = tp_viable.loc[tp_viable['sl_level'].idxmax()]
                    
                    data.append({
                        'Strategy': strategy_name,
                        'TP Level': f"{tp}%",
                        'Deepest Viable SL': f"{deepest_row['sl_level']}%",
                        'Historical Win Rate': f"{deepest_row['historical_win_rate']*100:.1f}%",
                        'Required Win Rate': f"{deepest_row['required_win_rate']*100:.1f}%",
                        'Safety Margin': f"{deepest_row['margin']*100:.1f}%",
                        'Sample Size': int(deepest_row['sample_size'])
                    })
        
        if not data:
            # Create diagnostic table when no viable floors found
            diagnostic_data = []
            
            # Find the best (least negative) margins for diagnosis
            for strategy_id, results in optimization_results.items():
                strategy_name = strategy_id.split('_')[0]
                ev_df = results['sl_floor_analysis']
                
                # Get best margin for each TP
                for tp in sorted(ev_df['tp_level'].unique()):
                    tp_data = ev_df[ev_df['tp_level'] == tp]
                    best_row = tp_data.loc[tp_data['margin'].idxmax()]
                    
                    diagnostic_data.append({
                        'Strategy': strategy_name,
                        'TP': f"{tp}%",
                        'Best SL Tested': f"{best_row['sl_level']}%",
                        'Historical WR': f"{best_row['historical_win_rate']*100:.1f}%",
                        'Required WR': f"{best_row['required_win_rate']*100:.1f}%",
                        'Gap': f"{best_row['margin']*100:.1f}%",
                        'TP/SL/END': f"{int(best_row['tp_count'])}/{int(best_row['sl_count'])}/{int(best_row['end_count'])}"
                    })
            
            if diagnostic_data:
                diag_df = pd.DataFrame(diagnostic_data)
                fig = go.Figure(data=[go.Table(
                    header=dict(
                        values=["Diagnostic: Why No Viable SL Found"] + list(diag_df.columns),
                        fill_color='salmon',
                        align='left',
                        font=dict(size=12, color='white')
                    ),
                    cells=dict(
                        values=[["Historical win rates are below mathematical requirements"]] + 
                            [diag_df[col] for col in diag_df.columns],
                        fill_color='mistyrose',
                        align='left',
                        font=dict(size=11)
                    )
                )])
                fig.update_layout(
                    title="SL Floor Analysis - Diagnostic View (No Viable Floors Found)",
                    height=max(400, 100 + len(diagnostic_data) * 25),
                    margin=dict(l=0, r=0, t=40, b=0)
                )
            else:
                fig = go.Figure(data=[go.Table(
                    header=dict(values=["Message"]),
                    cells=dict(values=[["No data available for SL floor analysis"]])
                )])
        else:
            df = pd.DataFrame(data)
            
            # Color code safety margin
            margins = [float(x.strip('%')) for x in df['Safety Margin']]
            colors = ['red' if x < 5 else 'yellow' if x < 10 else 'green' for x in margins]
            
            fig = go.Figure(data=[go.Table(
                header=dict(
                    values=list(df.columns),
                    fill_color='lightblue',
                    align='left',
                    font=dict(size=12, color='black')
                ),
                cells=dict(
                    values=[df[col] for col in df.columns],
                    fill_color=[['white']*len(df) if i != 5 
                            else colors for i in range(len(df.columns))],
                    align='left',
                    font=dict(size=11)
                )
            )])
            
            fig.update_layout(
                title="Dynamic SL Floor Analysis - Deepest Viable Stop Loss by Take Profit Level",
                height=max(400, 100 + len(data) * 25),
                margin=dict(l=0, r=0, t=40, b=0)
            )
        
        return fig
        
    def _generate_summary(self, optimization_results: Dict, successfully_analyzed: int) -> Dict[str, Any]:
        """Generate summary statistics from optimization results."""
        if not optimization_results:
            return {'total_strategies': 0, 'successfully_analyzed': 0}
            
        improvements = []
        changes_recommended = 0
        
        # AIDEV-TODO-CLAUDE: Significance threshold of 0.1 could be made configurable in the future
        significance_threshold = 0.1
        
        for strategy_id, results in optimization_results.items():
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
            # Check if change is recommended (meets significance threshold)
            if abs(results['optimal_net_impact']) > significance_threshold and \
               (results['optimal_tp'] != strategy_info['takeProfit'] or 
                results['optimal_sl'] != strategy_info['stopLoss']):
                changes_recommended += 1
                
            improvements.append(results['optimal_net_impact'])
            
        return {
            'total_strategies': len(optimization_results),
            'successfully_analyzed': successfully_analyzed,
            'changes_recommended': changes_recommended,
            'avg_improvement': np.mean(improvements) if improvements else 0,
            'max_improvement': max(improvements) if improvements else 0,
            'time_weighted': self.time_weighting_enabled
        }
        
    def export_recommendations(self, results: Dict[str, Any], 
                             output_path: str = "reporting/output/tp_sl_recommendations.csv") -> str:
        """
        Export optimization recommendations to CSV.
        
        Args:
            results: Optimization results from run_optimization()
            output_path: Path for output CSV
            
        Returns:
            Path to exported file
        """
        if results['status'] != 'SUCCESS':
            logger.warning("Cannot export recommendations - optimization did not succeed")
            return ""
            
        recommendations = []
        
        # AIDEV-TODO-CLAUDE: Significance threshold of 0.1 could be made configurable in the future
        significance_threshold = 0.1
        
        for strategy_id, strategy_results in results['optimization_results'].items():
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
            # Only export if improvement meets significance threshold
            if abs(strategy_results['optimal_net_impact']) > significance_threshold:
                recommendations.append({
                    'strategy_instance_id': strategy_id,
                    'strategy': strategy_info['strategy'],
                    'step_size': strategy_info['step_size'],
                    'investment_sol': strategy_info['investment_sol'],
                    'current_tp': strategy_info['takeProfit'],
                    'current_sl': strategy_info['stopLoss'],
                    'recommended_tp': strategy_results['optimal_tp'],
                    'recommended_sl': strategy_results['optimal_sl'],
                    'expected_improvement_pct': strategy_results['optimal_net_impact'],
                    'position_count': strategy_results['position_count'],
                    'confidence': 'HIGH' if strategy_results['position_count'] >= 50 else 'MEDIUM'
                })
            else:
                recommendations.append({
                    'strategy_instance_id': strategy_id,
                    'strategy': strategy_info['strategy'],
                    'step_size': strategy_info['step_size'],
                    'investment_sol': strategy_info['investment_sol'],
                    'current_tp': strategy_info['takeProfit'],
                    'current_sl': strategy_info['stopLoss'],
                    'recommended_tp': 'KEEP_CURRENT',
                    'recommended_sl': 'KEEP_CURRENT',
                    'expected_improvement_pct': 0.0,
                    'position_count': strategy_results['position_count'],
                    'confidence': 'NO_CHANGE_RECOMMENDED'
                })
            
        df = pd.DataFrame(recommendations)
        df.to_csv(output_path, index=False)
        logger.info(f"Exported {len(recommendations)} recommendations to {output_path}")
        
        return output_path


# Helper function for integration
def run_tp_sl_optimization():
    """Run the TP/SL optimization and return results."""
    try:
        optimizer = TpSlOptimizer()
        results = optimizer.run_optimization()
        
        if results['status'] == 'SUCCESS':
            # Export recommendations
            optimizer.export_recommendations(results)
            
        return results
        
    except Exception as e:
        logger.error(f"TP/SL optimization failed: {e}")
        return {
            'status': 'ERROR',
            'error': str(e)
        }