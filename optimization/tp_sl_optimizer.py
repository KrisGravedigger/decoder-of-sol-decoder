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
        # AIDEV-TODO-CLAUDE: Centralize file paths in the configuration file instead of hardcoding them here to improve maintainability.
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
        
        for strategy_id in qualified_strategies:
            logger.info(f"Optimizing strategy: {strategy_id}")
            
            # Get strategy data
            strategy_data = self.detailed_results[
                self.detailed_results['strategy_instance_id'] == strategy_id
            ].copy()
            
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
                
            # AIDEV-NOTE-GEMINI: This check is critical. It prevents crashes if the baseline TP/SL for a strategy isn't found in the simulation results, making the loop robust.
            # Calculate net effect for each TP/SL combination
            net_effect_results = self._calculate_net_effect(strategy_id, strategy_data)
            
            if net_effect_results.empty:
                logger.warning(f"Could not calculate net effect for strategy {strategy_id}. "
                               f"This usually means its baseline TP/SL is not in the range test data. Skipping.")
                continue

            # Find optimal TP/SL combination
            optimal_combo = net_effect_results.loc[net_effect_results['net_pnl_impact'].idxmax()]
            
            # Calculate EV-based SL floor analysis
            sl_floor_analysis = self._calculate_ev_based_sl_floor(strategy_data)
            
            optimization_results[strategy_id] = {
                'net_effect_matrix': net_effect_results,
                'optimal_tp': optimal_combo['tp_level'],
                'optimal_sl': optimal_combo['sl_level'],
                'optimal_net_impact': optimal_combo['net_pnl_impact'],
                'sl_floor_analysis': sl_floor_analysis,
                'position_count': len(strategy_data['position_id'].unique()),
                'time_weighted': self.time_weighting_enabled
            }
            
        # Generate visualizations
        visualizations = self._generate_visualizations(optimization_results)
        
        return {
            'status': 'SUCCESS',
            'optimization_results': optimization_results,
            'visualizations': visualizations,
            'summary': self._generate_summary(optimization_results),
            'timestamp': datetime.now().isoformat()
        }

    # AIDEV-TPSL-CLAUDE: Core optimization logic. Calculates the net PnL impact by comparing every TP/SL combo against a baseline, categorizing each position's outcome.    
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
        ][['position_id', 'simulated_pnl_pct']].rename(
            columns={'simulated_pnl_pct': 'baseline_pnl_pct'}
        )
        
        # Merge baseline with all combinations
        merged_data = strategy_data.merge(baseline_data, on='position_id', suffixes=('', '_baseline'))
        
        # Calculate improvement
        merged_data['pnl_improvement'] = merged_data['simulated_pnl_pct'] - merged_data['baseline_pnl_pct']
        
        # AIDEV-TODO-CLAUDE: The 'Neutral' category threshold (0.1%) is hardcoded. Consider making this configurable in portfolio_config.yaml for more flexible analysis.
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
            
            net_effects.append({
                'tp_level': tp,
                'sl_level': sl,
                'net_pnl_impact': net_pnl_impact,
                'improved_count': category_counts.get('Improved', 0),
                'neutral_count': category_counts.get('Neutral', 0),
                'degraded_count': category_counts.get('Degraded', 0),
                'total_positions': len(group),
                'weighted_win_rate': (group[group['exit_reason'] == 'TP']['weight'].sum() / 
                                    total_weight * 100) if total_weight > 0 else 0
            })
            
        return pd.DataFrame(net_effects)

    # AIDEV-TPSL-CLAUDE: Implements the Expected Value (EV) model to find the deepest viable SL where historical performance justifies the risk.    
    def _calculate_ev_based_sl_floor(self, strategy_data: pd.DataFrame) -> Dict[float, float]:
        """
        Calculate the deepest viable SL for each TP level based on Expected Value.
        
        Uses formula: P_win > SL_Level / (TP_Level + SL_Level)
        """
        sl_floor_results = {}
        
        # Get unique TP levels
        tp_levels = sorted(strategy_data['tp_level'].unique())
        sl_levels = sorted(strategy_data['sl_level'].unique(), reverse=True)  # Start from deepest
        
        for tp in tp_levels:
            tp_data = strategy_data[strategy_data['tp_level'] == tp]
            
            for sl in sl_levels:
                sl_data = tp_data[tp_data['sl_level'] == sl]
                
                if len(sl_data) == 0:
                    continue
                    
                # Calculate weighted win rate
                total_weight = sl_data['weight'].sum()
                if total_weight == 0:
                    continue
                    
                weighted_wins = sl_data[sl_data['exit_reason'] == 'TP']['weight'].sum()
                historical_win_rate = weighted_wins / total_weight
                
                # Calculate required win rate
                required_win_rate = sl / (tp + sl)
                
                # Check if SL is viable
                if historical_win_rate > required_win_rate:
                    sl_floor_results[tp] = {
                        'viable_sl': sl,
                        'historical_win_rate': historical_win_rate,
                        'required_win_rate': required_win_rate,
                        'margin': historical_win_rate - required_win_rate
                    }
                    break  # Found the deepest viable SL for this TP
                    
        return sl_floor_results

    # AIDEV-PERF-CLAUDE: Implements a linear time decay weighting to prioritize recent position performance, making the analysis more sensitive to current market conditions.    
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
        
        for strategy_id, results in optimization_results.items():
            # Get strategy name components
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
            data.append({
                'Strategy': strategy_id,
                'Current TP': f"{strategy_info['takeProfit']}%",
                'Current SL': f"{strategy_info['stopLoss']}%",
                'Optimal TP': f"{results['optimal_tp']}%",
                'Optimal SL': f"{results['optimal_sl']}%",
                'Net Impact': f"{results['optimal_net_impact']:.2f}%",
                'Positions': results['position_count'],
                'Weighted': '✓' if results['time_weighted'] else '✗'
            })
            
        df = pd.DataFrame(data)
        
        # Create color scale for Net Impact
        net_impacts = [float(x.strip('%')) for x in df['Net Impact']]
        colors = ['red' if x < 0 else 'green' for x in net_impacts]
        
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
        """Create win rate vs required win rate chart for a strategy."""
        sl_floor_data = strategy_results['sl_floor_analysis']
        net_effect_matrix = strategy_results['net_effect_matrix']
        
        # Prepare data for chart
        tp_levels = sorted(sl_floor_data.keys())
        sl_levels = sorted(net_effect_matrix['sl_level'].unique())
        
        fig = go.Figure()
        
        # Add required win rate lines for each TP level
        for tp in tp_levels:
            required_rates = [sl / (tp + sl) * 100 for sl in sl_levels]
            fig.add_trace(go.Scatter(
                x=sl_levels,
                y=required_rates,
                mode='lines',
                name=f'Required (TP={tp}%)',
                line=dict(dash='dash')
            ))
            
        # Add historical win rate line
        historical_rates = []
        for sl in sl_levels:
            sl_data = net_effect_matrix[net_effect_matrix['sl_level'] == sl]
            if not sl_data.empty:
                # Average across all TP levels for this SL
                avg_win_rate = sl_data['weighted_win_rate'].mean()
                historical_rates.append(avg_win_rate)
            else:
                historical_rates.append(0)
                
        fig.add_trace(go.Scatter(
            x=sl_levels,
            y=historical_rates,
            mode='lines+markers',
            name='Historical Win Rate',
            line=dict(color='black', width=3),
            marker=dict(size=8)
        ))
        
        # Add viability zones
        for tp, floor_data in sl_floor_data.items():
            fig.add_shape(
                type="rect",
                x0=floor_data['viable_sl'],
                x1=max(sl_levels),
                y0=0,
                y1=100,
                fillcolor="green",
                opacity=0.1,
                layer="below",
                line_width=0,
            )
            fig.add_annotation(
                x=floor_data['viable_sl'] + 0.5,
                y=95,
                text=f"Viable zone<br>TP={tp}%",
                showarrow=False,
                font=dict(size=10)
            )
            
        fig.update_layout(
            title=f"Win Rate Analysis - {strategy_id}",
            xaxis_title="Stop Loss Level (%)",
            yaxis_title="Win Rate (%)",
            yaxis=dict(range=[0, 100]),
            hovermode='x unified',
            height=500,
            showlegend=True
        )
        
        return fig
        
    def _create_sl_floor_table(self, optimization_results: Dict) -> go.Figure:
        """Create summary table showing deepest viable SL for each TP level."""
        data = []
        
        for strategy_id, results in optimization_results.items():
            strategy_name = strategy_id.split('_')[0]  # Short name
            
            for tp, floor_data in results['sl_floor_analysis'].items():
                data.append({
                    'Strategy': strategy_name,
                    'TP Level': f"{tp}%",
                    'Deepest Viable SL': f"{floor_data['viable_sl']}%",
                    'Historical Win Rate': f"{floor_data['historical_win_rate']*100:.1f}%",
                    'Required Win Rate': f"{floor_data['required_win_rate']*100:.1f}%",
                    'Safety Margin': f"{floor_data['margin']*100:.1f}%"
                })
                
        if not data:
            # Create empty table with message
            fig = go.Figure(data=[go.Table(
                header=dict(values=["Message"]),
                cells=dict(values=[["No viable SL floors found"]])
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
        
    def _generate_summary(self, optimization_results: Dict) -> Dict[str, Any]:
        """Generate summary statistics from optimization results."""
        if not optimization_results:
            return {'total_strategies': 0}
            
        improvements = []
        changes_recommended = 0
        
        for strategy_id, results in optimization_results.items():
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
            # Check if change is recommended
            if (results['optimal_tp'] != strategy_info['takeProfit'] or 
                results['optimal_sl'] != strategy_info['stopLoss']):
                changes_recommended += 1
                
            improvements.append(results['optimal_net_impact'])
            
        return {
            'total_strategies': len(optimization_results),
            'changes_recommended': changes_recommended,
            'avg_improvement': np.mean(improvements),
            'max_improvement': max(improvements),
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
        
        for strategy_id, strategy_results in results['optimization_results'].items():
            strategy_info = self.strategy_instances[
                self.strategy_instances['strategy_instance_id'] == strategy_id
            ].iloc[0]
            
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