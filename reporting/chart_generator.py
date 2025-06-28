"""
Chart Generator for Portfolio Analytics

Creates timestamped visualization charts including equity curves,
drawdown analysis, strategy heatmaps, and cost impact charts.
"""

import logging
import os
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Any
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
from matplotlib.figure import Figure
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates portfolio analytics charts with timestamp naming.
    
    Creates professional visualizations for equity curves, drawdown analysis,
    strategy performance heatmaps, and infrastructure cost impact charts.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize chart generator with configuration.
        
        Args:
            config_path (str): Path to YAML configuration file
        """
        self.config = self._load_config(config_path)
        self.output_dir = "reporting/output/charts"
        self.timestamp_format = self.config['visualization']['timestamp_format']
        self._ensure_charts_directory()
        
        # Set chart style
        plt.style.use('default')
        sns.set_palette("husl")
        
        logger.info("Chart Generator initialized")
        
    def _load_config(self, config_path: str) -> Dict:
        """Load YAML configuration with error handling."""
        try:
            with open(config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            logger.warning(f"Config file not found: {config_path}, using defaults")
            return {'visualization': {'timestamp_format': '%Y%m%d_%H%M'}}
            
    def _ensure_charts_directory(self):
        """Create charts output directory if it doesn't exist."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            logger.info(f"Created charts directory: {self.output_dir}")
            
    def _generate_timestamp(self) -> str:
        """Generate timestamp for chart filenames."""
        return datetime.now().strftime(self.timestamp_format)
        
    def _save_chart(self, fig: Figure, chart_name: str, timestamp: str) -> str:
        """
        Save chart with timestamped filename.
        
        Args:
            fig (Figure): Matplotlib figure to save
            chart_name (str): Base name for chart
            timestamp (str): Timestamp string
            
        Returns:
            str: Path to saved chart file
        """
        filename = f"{chart_name}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        
        try:
            # AIDEV-FIX: Removed `bbox_inches='tight'`. This is the primary fix for the
            # image orientation issue. Layout is now managed by `plt.tight_layout(rect=[...])`
            # within the chart creation methods.
            fig.savefig(filepath, dpi=300, 
                       facecolor='white', edgecolor='none')
            logger.info(f"Saved chart: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save chart {filename}: {e}")
            raise
            
    def create_equity_curve(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """
        Create equity curve chart showing SOL and USDC performance over time.
        
        Args:
            analysis_result (Dict[str, Any]): Portfolio analysis results
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Path to saved chart file
        """
        daily_df = analysis_result['raw_data']['daily_returns_df']
        sol_rates = analysis_result['raw_data']['sol_rates']
        
        if daily_df.empty:
            logger.warning("No daily data available for equity curve")
            # Create empty chart
            fig, ax = plt.subplots(figsize=(12, 8))
            ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('Portfolio Equity Curve - No Data')
            return self._save_chart(fig, 'equity_curve', timestamp)
            
        # Prepare data
        daily_df = daily_df.copy()
        positions_df = analysis_result['raw_data']['positions_df']
        cost_summary = analysis_result['infrastructure_cost_impact']
        
        # Convert SOL PnL to USDC and calculate cost impact
        daily_df['cumulative_pnl_usdc'] = 0.0
        daily_df['cumulative_cost_sol'] = 0.0
        daily_df['net_pnl_sol'] = 0.0
        
        cumulative_cost = 0.0
        daily_cost_usd = cost_summary.get('daily_cost_usd', 11.67)  # Fallback for safety
        
        for idx, row in daily_df.iterrows():
            date_str = row['date'].strftime("%Y-%m-%d")
            
            # Convert SOL to USDC
            if date_str in sol_rates:
                sol_price = sol_rates[date_str]
                daily_df.at[idx, 'cumulative_pnl_usdc'] = row['cumulative_pnl_sol'] * sol_price
                
                # Calculate daily infrastructure cost in SOL using actual config value
                daily_cost_sol = daily_cost_usd / sol_price
                cumulative_cost += daily_cost_sol
                
                daily_df.at[idx, 'cumulative_cost_sol'] = cumulative_cost
                daily_df.at[idx, 'net_pnl_sol'] = row['cumulative_pnl_sol'] - cumulative_cost
                
        # Create figure with dual y-axes
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                      gridspec_kw={'height_ratios': [3, 1]})
        
        # Main equity curve
        ax1.plot(daily_df['date'], daily_df['cumulative_pnl_sol'], 
                label='Gross SOL PnL', linewidth=2, color='#FF6B35')
        ax1.plot(daily_df['date'], daily_df['net_pnl_sol'], 
                label='Net SOL PnL (after costs)', linewidth=2, color='#D2001C', linestyle='-.')
        
        # Secondary axis for USDC
        ax1_twin = ax1.twinx()
        ax1_twin.plot(daily_df['date'], daily_df['cumulative_pnl_usdc'], 
                     label='USDC PnL', linewidth=2, color='#004E89', linestyle='--')
        
        # Fill area showing cost impact
        ax1.fill_between(daily_df['date'], daily_df['cumulative_pnl_sol'], daily_df['net_pnl_sol'],
                        alpha=0.3, color='red', label='Infrastructure Cost Impact')
        
        # Formatting
        ax1.set_title('Portfolio Equity Curve - Dual Currency Analysis', 
                     fontsize=16, fontweight='bold', pad=20)
        ax1.set_xlabel('Date', fontsize=12)
        ax1.set_ylabel('Cumulative PnL (SOL)', fontsize=12, color='#FF6B35')
        ax1_twin.set_ylabel('Cumulative PnL (USDC)', fontsize=12, color='#004E89')
        
        # Grid and formatting
        ax1.grid(True, alpha=0.3)
        ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
        ax1.xaxis.set_major_locator(mdates.WeekdayLocator())
        plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45)
        
        # Legends
        ax1.legend(loc='upper left')
        ax1_twin.legend(loc='upper right')
        
        # Add zero line
        ax1.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # SOL price chart in subplot
        if sol_rates:
            sol_dates = [datetime.strptime(date, "%Y-%m-%d") for date in sol_rates.keys()]
            sol_prices = list(sol_rates.values())
            
            ax2.plot(sol_dates, sol_prices, color='#7209B7', linewidth=2)
            ax2.set_ylabel('SOL/USDC Price', fontsize=10, color='#7209B7')
            ax2.set_xlabel('Date', fontsize=10)
            ax2.grid(True, alpha=0.3)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m-%d'))
            
        plt.tight_layout()
        return self._save_chart(fig, 'equity_curve', timestamp)
        
    def create_drawdown_analysis(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """
        Create drawdown analysis chart showing peak-to-trough declines.
        
        Args:
            analysis_result (Dict[str, Any]): Portfolio analysis results
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Path to saved chart file
        """
        daily_df = analysis_result['raw_data']['daily_returns_df']
        
        if daily_df.empty:
            logger.warning("No daily data available for drawdown analysis")
            fig, ax = plt.subplots(figsize=(12, 6))
            ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('Drawdown Analysis - No Data')
            return self._save_chart(fig, 'drawdown_analysis', timestamp)
            
        # Calculate drawdown
        daily_df = daily_df.copy()
        cumulative = daily_df['cumulative_pnl_sol']
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max.abs() * 100
        
        # Create figure
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), 
                                      gridspec_kw={'height_ratios': [2, 1]})
        
        # Equity curve with peaks highlighted
        ax1.plot(daily_df['date'], cumulative, linewidth=2, color='#004E89', label='Cumulative PnL')
        ax1.plot(daily_df['date'], running_max, linewidth=1, color='#FF6B35', 
                linestyle='--', alpha=0.7, label='Running Maximum')
        
        # Fill drawdown areas
        ax1.fill_between(daily_df['date'], cumulative, running_max, 
                        where=(cumulative < running_max), color='red', alpha=0.2, 
                        interpolate=True, label='Drawdown Periods')
        
        ax1.set_title('Portfolio Drawdown Analysis', fontsize=16, fontweight='bold')
        ax1.set_ylabel('Cumulative PnL (SOL)', fontsize=12)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Drawdown percentage chart
        ax2.fill_between(daily_df['date'], drawdown, 0, where=(drawdown < 0), 
                        color='red', alpha=0.6, interpolate=True)
        ax2.plot(daily_df['date'], drawdown, linewidth=1, color='darkred')
        
        # Highlight maximum drawdown
        max_dd_idx = drawdown.idxmin()
        max_dd_value = drawdown.min()
        max_dd_date = daily_df.iloc[max_dd_idx]['date']
        
        ax2.scatter(max_dd_date, max_dd_value, color='red', s=100, zorder=5)
        ax2.annotate(f'Max DD: {max_dd_value:.1f}%', 
                    xy=(max_dd_date, max_dd_value), xytext=(10, 10),
                    textcoords='offset points', fontsize=10, fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.3', facecolor='yellow', alpha=0.7))
        
        ax2.set_title('Drawdown Percentage', fontsize=12)
        ax2.set_ylabel('Drawdown (%)', fontsize=10)
        ax2.set_xlabel('Date', fontsize=10)
        ax2.grid(True, alpha=0.3)
        ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
        
        # Format dates
        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
            ax.xaxis.set_major_locator(mdates.WeekdayLocator())
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45)
            
        plt.tight_layout()
        return self._save_chart(fig, 'drawdown_analysis', timestamp)
        
    def create_strategy_heatmap(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """
        Create strategy performance heatmap using strategy_instances.csv data.
        
        Args:
            analysis_result (Dict[str, Any]): Portfolio analysis results
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Path to saved chart file
        """
        positions_df = analysis_result['raw_data']['positions_df']
        
        if positions_df.empty:
            logger.warning("No positions data available for strategy heatmap")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', 
                   transform=ax.transAxes, fontsize=16)
            ax.set_title('Strategy Performance Heatmap - No Data')
            return self._save_chart(fig, 'strategy_heatmap', timestamp)
            
        try:
            # Load strategy instances data
            strategy_instances_file = "strategy_instances.csv"
            if not os.path.exists(strategy_instances_file):
                logger.warning(f"Strategy instances file not found: {strategy_instances_file}")
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, 'strategy_instances.csv not found', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_title('Strategy Performance Heatmap - Missing Data')
                return self._save_chart(fig, 'strategy_heatmap', timestamp)
                
            strategy_instances_df = pd.read_csv(strategy_instances_file)
            
            # Apply filters from config
            filters = self.config.get('visualization', {}).get('filters', {})
            min_occurrences = filters.get('min_strategy_occurrences', 3)
            top_strategies = filters.get('top_strategies_only', 10)
            
            # Filter by minimum occurrences
            strategy_instances_df = strategy_instances_df[
                strategy_instances_df['position_count'] >= min_occurrences
            ]
            
            if strategy_instances_df.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, f'No strategies with ≥{min_occurrences} positions', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_title('Strategy Performance Heatmap - Insufficient Data')
                return self._save_chart(fig, 'strategy_heatmap', timestamp)
                
            # Parse step_size from strategy column
            logger.info("Parsing step_size from strategy column")
            
            def extract_step_size(strategy_str):
                """Extract step_size from strategy string."""
                if pd.isna(strategy_str):
                    return 'UNKNOWN'
                
                import re
                
                match = re.search(r'\b(MEDIUM|WIDE|NARROW|SIXTYNINE)\b', str(strategy_str), re.IGNORECASE)
                if match:
                    return match.group(1).upper()
                
                words = str(strategy_str).split()
                if words:
                    last_word = words[-1].upper()
                    if last_word in ['MEDIUM', 'WIDE', 'NARROW', 'SIXTYNINE']:
                        return last_word
                
                return 'MEDIUM'
            
            def extract_strategy_name(strategy_str):
                """Extract clean strategy name from strategy string."""
                if pd.isna(strategy_str):
                    return 'Unknown'
                
                strategy_clean = str(strategy_str)
                for step_size in ['MEDIUM', 'WIDE', 'NARROW', 'SIXTYNINE']:
                    strategy_clean = strategy_clean.replace(step_size, '').strip()
                
                strategy_clean = ' '.join(strategy_clean.split())
                strategy_clean = strategy_clean.rstrip('() -')
                
                return strategy_clean if strategy_clean else 'Unknown'
            
            # Apply parsing
            strategy_instances_df['step_size'] = strategy_instances_df['strategy'].apply(extract_step_size)
            strategy_instances_df['strategy_clean'] = strategy_instances_df['strategy'].apply(extract_strategy_name)
            
            logger.info(f"Parsed step sizes: {strategy_instances_df['step_size'].value_counts().to_dict()}")
            logger.info(f"Parsed strategies: {strategy_instances_df['strategy_clean'].value_counts().to_dict()}")
            
            # Sort by performance score and take top N
            if 'performance_score' in strategy_instances_df.columns:
                strategy_instances_df = strategy_instances_df.sort_values(
                    'performance_score', ascending=False
                ).head(top_strategies)
            elif 'avg_pnl_percent' in strategy_instances_df.columns:
                strategy_instances_df = strategy_instances_df.sort_values(
                    'avg_pnl_percent', ascending=False
                ).head(top_strategies)
            else:
                strategy_instances_df = strategy_instances_df.head(top_strategies)
            
            # Calculate Sharpe ratio for each strategy instance
            strategy_instances_df = strategy_instances_df.copy()
            
            for idx, strategy_instance in strategy_instances_df.iterrows():
                instance_positions = positions_df[
                    positions_df['strategy_instance_id'] == strategy_instance['strategy_instance_id']
                ]
                
                if len(instance_positions) > 1:
                    daily_pnl = {}
                    for _, pos in instance_positions.iterrows():
                        close_date = pos['close_timestamp'].date()
                        pnl = pos['pnl_sol']
                        if close_date in daily_pnl:
                            daily_pnl[close_date] += pnl
                        else:
                            daily_pnl[close_date] = pnl
                    
                    daily_returns = pd.Series(list(daily_pnl.values()))
                    
                    if len(daily_returns) > 1 and daily_returns.std() > 0:
                        risk_free_daily = 0.04 / 365
                        avg_return = daily_returns.mean()
                        std_return = daily_returns.std()
                        sharpe = (avg_return - risk_free_daily) / std_return * np.sqrt(365)
                        strategy_instances_df.at[idx, 'sharpe_ratio'] = sharpe
                    else:
                        strategy_instances_df.at[idx, 'sharpe_ratio'] = 0.0
                else:
                    strategy_instances_df.at[idx, 'sharpe_ratio'] = 0.0
            
            # Create strategy name for better readability
            strategy_instances_df['strategy_name'] = (
                strategy_instances_df['strategy_clean'] + ' ' + 
                strategy_instances_df['step_size'] + ' ' +
                strategy_instances_df['initial_investment'].astype(str) + 'SOL (' +
                strategy_instances_df['position_count'].astype(str) + ')'
            )
            
            # Create heatmap data
            metrics = ['avg_pnl_percent', 'win_rate', 'sharpe_ratio']
            metric_labels = ['Avg PnL %', 'Win Rate', 'Sharpe Ratio']
            
            # Prepare filter info for subtitle
            total_instances = len(pd.read_csv("strategy_instances.csv")) if os.path.exists("strategy_instances.csv") else 0
            filter_info = f"Showing {len(strategy_instances_df)} of {total_instances} strategies (min {min_occurrences} positions)"
            
            fig, axes = plt.subplots(1, 3, figsize=(20, 10))
            fig.suptitle('Strategy Performance Heatmap (Top Strategies)', fontsize=16, fontweight='bold')
            
            # Add subtitle with filter information
            fig.text(0.5, 0.95, filter_info, ha='center', va='center', fontsize=12, 
                    style='italic', color='gray')
            
            for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
                if metric not in strategy_instances_df.columns:
                    continue
                    
                heatmap_data = strategy_instances_df.set_index('strategy_name')[[metric]]
                
                sns.heatmap(heatmap_data, annot=True, fmt='.2f', 
                           cmap='RdYlGn', center=0 if metric == 'avg_pnl_percent' else None,
                           ax=axes[i], cbar_kws={'shrink': 0.8})
                
                axes[i].set_title(label, fontsize=12, fontweight='bold')
                axes[i].set_xlabel('')
                axes[i].set_ylabel('Strategy Instance' if i == 0 else '')
                
                axes[i].tick_params(axis='y', rotation=0)

            # AIDEV-FIX-V2: Using `tight_layout` with the `rect` parameter.
            # This makes space for `suptitle` while allowing the layout engine
            # to automatically adjust for long tick labels, fixing all layout issues.
            plt.tight_layout(rect=[0, 0, 1, 0.93])
            
            return self._save_chart(fig, 'strategy_heatmap', timestamp)
            
        except Exception as e:
            logger.error(f"Failed to create strategy heatmap: {e}")
            logger.info("Attempting fallback to positions-based heatmap")
            try:
                return self._create_positions_based_heatmap(positions_df, timestamp)
            except Exception as fallback_error:
                logger.error(f"Fallback heatmap also failed: {fallback_error}")
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, f'Heatmap failed: {str(e)}\nFallback failed: {str(fallback_error)}', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=10)
                ax.set_title('Strategy Performance Heatmap - Error')
                return self._save_chart(fig, 'strategy_heatmap', timestamp)
                
    def _create_positions_based_heatmap(self, positions_df: pd.DataFrame, timestamp: str) -> str:
        """
        Create heatmap based on positions data when strategy_instances.csv is unavailable.
        """
        logger.info("Creating positions-based strategy heatmap as fallback")
        
        try:
            # Map columns to work with actual CSV structure
            csv_mapping = {
                'strategy': 'actual_strategy_from_log',
                'pnl': 'final_pnl_sol_from_log', 
                'investment': 'initial_investment_sol'
            }
            
            # Check if required columns exist
            missing_cols = [col for col in csv_mapping.values() if col not in positions_df.columns]
            if missing_cols:
                logger.warning(f"Missing columns for fallback heatmap: {missing_cols}")
                if 'pnl_sol' in positions_df.columns: csv_mapping['pnl'] = 'pnl_sol'
                if 'strategy' in positions_df.columns: csv_mapping['strategy'] = 'strategy'
                if 'investment_sol' in positions_df.columns: csv_mapping['investment'] = 'investment_sol'
            
            # Parse strategy and step_size
            def parse_strategy_parts(strategy_str):
                if pd.isna(strategy_str):
                    return 'Unknown', 'MEDIUM'
                
                import re
                
                match = re.search(r'\b(MEDIUM|WIDE|NARROW|SIXTYNINE)\b', str(strategy_str), re.IGNORECASE)
                step_size = match.group(1).upper() if match else 'MEDIUM'
                
                strategy_clean = str(strategy_str)
                for step in ['MEDIUM', 'WIDE', 'NARROW', 'SIXTYNINE']:
                    strategy_clean = strategy_clean.replace(step, '').strip()
                strategy_clean = ' '.join(strategy_clean.split()).rstrip('() -')
                strategy_name = strategy_clean if strategy_clean else 'Bid-Ask'
                
                return strategy_name, step_size
            
            # Apply parsing
            strategy_parts = positions_df[csv_mapping['strategy']].apply(parse_strategy_parts)
            positions_df = positions_df.copy()
            positions_df['strategy_parsed'] = [parts[0] for parts in strategy_parts]
            positions_df['step_size_parsed'] = [parts[1] for parts in strategy_parts]
            
            # Group by strategy and step_size
            strategy_groups = positions_df.groupby(['strategy_parsed', 'step_size_parsed']).agg({
                csv_mapping['pnl']: ['sum', 'mean', 'count'],
                csv_mapping['investment']: 'sum'
            }).round(3)
            
            # Flatten column names
            strategy_groups.columns = ['total_pnl', 'avg_pnl', 'position_count', 'total_investment']
            strategy_groups['win_rate'] = positions_df.groupby(['strategy_parsed', 'step_size_parsed']).apply(
                lambda x: (x[csv_mapping['pnl']] > 0).mean() * 100
            )
            strategy_groups['roi_percent'] = (strategy_groups['total_pnl'] / 
                                            strategy_groups['total_investment'] * 100)
            
            # Apply filters
            filters = self.config.get('visualization', {}).get('filters', {})
            min_occurrences = filters.get('min_strategy_occurrences', 3)
            
            strategy_groups = strategy_groups[strategy_groups['position_count'] >= min_occurrences]
            
            if strategy_groups.empty:
                fig, ax = plt.subplots(figsize=(10, 6))
                ax.text(0.5, 0.5, f'No strategies with ≥{min_occurrences} positions', 
                       ha='center', va='center', transform=ax.transAxes, fontsize=14)
                ax.set_title('Strategy Performance Heatmap - Insufficient Data')
                return self._save_chart(fig, 'strategy_heatmap', timestamp)
                
            # Create pivot table for heatmap
            metrics = ['avg_pnl', 'win_rate', 'roi_percent']
            metric_labels = ['Avg PnL (SOL)', 'Win Rate (%)', 'ROI %']
            
            # Prepare filter info
            total_positions = len(positions_df)
            used_positions = strategy_groups['position_count'].sum()
            filter_info = f"Using {used_positions} of {total_positions} positions (min {min_occurrences} per strategy)"
            
            fig, axes = plt.subplots(1, 3, figsize=(18, 8))
            fig.suptitle('Strategy Performance Heatmap (Positions-Based)', fontsize=16, fontweight='bold')
            
            # Add subtitle with filter information
            fig.text(0.5, 0.94, filter_info, ha='center', va='center', fontsize=12, 
                    style='italic', color='gray')
            
            for i, (metric, label) in enumerate(zip(metrics, metric_labels)):
                try:
                    pivot_data = strategy_groups.reset_index().pivot(
                        index='strategy_parsed', columns='step_size_parsed', values=metric
                    ).fillna(0)
                    
                    sns.heatmap(pivot_data, annot=True, fmt='.2f', cmap='RdYlGn', 
                               center=0 if metric == 'avg_pnl' else pivot_data.mean().mean(),
                               ax=axes[i], cbar_kws={'shrink': 0.8})
                    
                    axes[i].set_title(label, fontsize=12, fontweight='bold')
                    axes[i].set_xlabel('Step Size', fontsize=10)
                    axes[i].set_ylabel('Strategy' if i == 0 else '')
                    
                except Exception as e:
                    logger.warning(f"Failed to create {metric} heatmap: {e}")
                    axes[i].text(0.5, 0.5, f'Error: {metric}', ha='center', va='center', 
                               transform=axes[i].transAxes)
                    axes[i].set_title(f'{label} - Error', fontsize=12)
                
            # AIDEV-FIX-V2: Using `tight_layout` with `rect` here as well.
            plt.tight_layout(rect=[0, 0, 1, 0.92])
            
            return self._save_chart(fig, 'strategy_heatmap', timestamp)
            
        except Exception as e:
            logger.error(f"Failed to create positions-based heatmap: {e}")
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.text(0.5, 0.5, f'Fallback heatmap error: {str(e)}', 
                   ha='center', va='center', transform=ax.transAxes, fontsize=12)
            ax.set_title('Strategy Performance Heatmap - Fallback Error')
            return self._save_chart(fig, 'strategy_heatmap', timestamp)
            
    def create_cost_impact_chart(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """
        Create infrastructure cost impact comparison chart.
        
        Args:
            analysis_result (Dict[str, Any]): Portfolio analysis results
            timestamp (str): Timestamp for filename
            
        Returns:
            str: Path to saved chart file
        """
        sol_metrics = analysis_result['sol_denomination']
        usdc_metrics = analysis_result['usdc_denomination']
        cost_summary = analysis_result['infrastructure_cost_impact']
        
        # Prepare data for comparison
        categories = ['SOL Denomination', 'USDC Denomination']
        gross_pnl = [
            sol_metrics['total_pnl_sol'] + cost_summary.get('total_cost_sol', 0),
            usdc_metrics['total_pnl_usdc'] + cost_summary.get('total_cost_usd', 0)
        ]
        net_pnl = [
            sol_metrics['net_pnl_after_costs'],
            usdc_metrics['net_pnl_after_costs']
        ]
        costs = [
            cost_summary.get('total_cost_sol', 0),
            cost_summary.get('total_cost_usd', 0)
        ]
        
        # Create figure
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle('Infrastructure Cost Impact Analysis', fontsize=16, fontweight='bold')
        
        # 1. Gross vs Net PnL Comparison
        x = np.arange(len(categories))
        width = 0.35
        
        bars1 = ax1.bar(x - width/2, gross_pnl, width, label='Gross PnL', color='#004E89', alpha=0.8)
        bars2 = ax1.bar(x + width/2, net_pnl, width, label='Net PnL', color='#FF6B35', alpha=0.8)
        
        ax1.set_title('Gross vs Net PnL Comparison', fontsize=12, fontweight='bold')
        ax1.set_ylabel('PnL Amount', fontsize=10)
        ax1.set_xticks(x)
        ax1.set_xticklabels(categories)
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                ax1.annotate(f'{height:.2f}',
                           xy=(bar.get_x() + bar.get_width() / 2, height),
                           xytext=(0, 3), textcoords="offset points",
                           ha='center', va='bottom', fontsize=9)
        
        # 2. Cost Impact Percentage
        def calculate_cost_impact(costs, gross_pnl):
            if gross_pnl > 0:
                return costs / gross_pnl * 100
            elif gross_pnl < 0:
                return costs / abs(gross_pnl) * 100
            else:
                return 0
        
        cost_impact_sol = calculate_cost_impact(costs[0], gross_pnl[0])
        cost_impact_usdc = calculate_cost_impact(costs[1], gross_pnl[1])
        
        impact_percentages = [cost_impact_sol, cost_impact_usdc]
        bars3 = ax2.bar(categories, impact_percentages, color=['#7209B7', '#A663CC'], alpha=0.8)
        
        title_suffix = " (as % of absolute PnL)" if gross_pnl[0] < 0 else ""
        ax2.set_title(f'Infrastructure Cost Impact (%){title_suffix}', fontsize=12, fontweight='bold')
        ax2.set_ylabel('Cost Impact (%)', fontsize=10)
        ax2.grid(True, alpha=0.3)
        
        for i, bar in enumerate(bars3):
            height = bar.get_height()
            ax2.annotate(f'{height:.1f}%',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # 3. Daily Cost Allocation
        period_days = cost_summary.get('period_days', 30)
        daily_costs = [cost_summary.get('total_cost_sol', 0) / period_days,
                      cost_summary.get('total_cost_usd', 0) / period_days]
        
        bars4 = ax3.bar(categories, daily_costs, color=['#FF6B35', '#004E89'], alpha=0.6)
        ax3.set_title('Daily Infrastructure Cost', fontsize=12, fontweight='bold')
        ax3.set_ylabel('Daily Cost', fontsize=10)
        ax3.grid(True, alpha=0.3)
        
        for i, bar in enumerate(bars4):
            height = bar.get_height()
            ax3.annotate(f'{height:.3f}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3), textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
        
        # 4. Break-even Analysis
        break_even_days = cost_summary.get('break_even_days', 0)
        analysis_days = cost_summary.get('period_days', 30)
        gross_pnl_sol = cost_summary.get('gross_pnl_sol', 0)
        
        if gross_pnl_sol > 0 and break_even_days > 0 and break_even_days < analysis_days:
            sizes = [break_even_days, analysis_days - break_even_days]
            labels = [f'Break-even\n({break_even_days:.0f} days)', 
                     f'Profitable\n({analysis_days - break_even_days:.0f} days)']
            colors = ['#FF6B35', '#004E89']
            
            ax4.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
            ax4.set_title(f'Break-even Analysis\n(Total: {analysis_days} days)', 
                         fontsize=12, fontweight='bold')
        else:
            ax4.text(0.5, 0.5, f'Break-even: {break_even_days:.0f} days\nAnalysis: {analysis_days} days', 
                    ha='center', va='center', transform=ax4.transAxes, fontsize=12)
            ax4.set_title('Break-even Analysis', fontsize=12, fontweight='bold')
        
        plt.tight_layout()
        return self._save_chart(fig, 'cost_impact', timestamp)
        
    def generate_all_charts(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """
        Generate all portfolio charts with consistent timestamp.
        
        Args:
            analysis_result (Dict[str, Any]): Portfolio analysis results
            
        Returns:
            Dict[str, str]: Dictionary of chart names to file paths
        """
        timestamp = self._generate_timestamp()
        chart_files = {}
        
        try:
            # Generate each chart type
            chart_types = [
                ('equity_curve', self.create_equity_curve),
                ('drawdown_analysis', self.create_drawdown_analysis),
                ('strategy_heatmap', self.create_strategy_heatmap),
                ('cost_impact', self.create_cost_impact_chart)
            ]
            
            for chart_name, chart_function in chart_types:
                try:
                    file_path = chart_function(analysis_result, timestamp)
                    chart_files[chart_name] = file_path
                    logger.info(f"Generated {chart_name} chart")
                except Exception as e:
                    logger.error(f"Failed to generate {chart_name} chart: {e}")
                    chart_files[chart_name] = f"ERROR: {str(e)}"
                    
            # Close all matplotlib figures to free memory
            plt.close('all')
            
            logger.info(f"Generated {len([f for f in chart_files.values() if not f.startswith('ERROR')])} charts successfully")
            return chart_files
            
        except Exception as e:
            logger.error(f"Chart generation failed: {e}")
            return {'error': str(e)}


if __name__ == "__main__":
    # Test chart generator with sample data
    # AIDEV-NOTE: Assumes portfolio_analytics.py exists and can be imported
    try:
        from portfolio_analytics import PortfolioAnalytics
    except ImportError:
        print("Skipping test run: portfolio_analytics.py not found.")
        PortfolioAnalytics = None

    if PortfolioAnalytics:
        try:
            # Load sample analysis
            analytics = PortfolioAnalytics()
            analysis_result = analytics.analyze_portfolio()
            
            if 'error' not in analysis_result:
                # Generate charts
                chart_gen = ChartGenerator()
                chart_files = chart_gen.generate_all_charts(analysis_result)
                
                print("Charts generated:")
                for chart_name, file_path in chart_files.items():
                    print(f"  {chart_name}: {file_path}")
        except Exception as e:
            logger.error(f"Operation failed: {e}")
            raise