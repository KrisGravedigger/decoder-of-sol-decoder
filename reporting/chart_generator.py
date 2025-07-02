"""
Chart Generator for Portfolio Analytics

Creates timestamped visualization charts including equity curves,
drawdown analysis, strategy heatmaps, and cost impact charts.
"""

import logging
import os
from datetime import datetime
from typing import Dict, Any
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.figure import Figure
import yaml

from visualizations.equity_curve import plot_equity_curve
from visualizations.drawdown import plot_drawdown_analysis
from visualizations.strategy_heatmap import plot_heatmap_from_instances, plot_heatmap_from_positions
from visualizations.cost_impact import plot_cost_impact

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChartGenerator:
    """
    Generates portfolio analytics charts by orchestrating specific plotting functions.
    """

    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """Initialize chart generator with configuration."""
        self.config = self._load_config(config_path)
        self.output_dir = "reporting/output/charts"
        self.timestamp_format = self.config['visualization']['timestamp_format']
        self._ensure_charts_directory()
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
        """Save chart with timestamped filename."""
        filename = f"{chart_name}_{timestamp}.png"
        filepath = os.path.join(self.output_dir, filename)
        try:
            fig.savefig(filepath, dpi=300, facecolor='white', edgecolor='none')
            logger.info(f"Saved chart: {filepath}")
            return filepath
        except Exception as e:
            logger.error(f"Failed to save chart {filename}: {e}")
            raise
    
    def _create_empty_chart(self, title: str, chart_name: str, timestamp: str) -> str:
        """Creates and saves a chart indicating no data is available."""
        fig, ax = plt.subplots(figsize=(12, 8))
        ax.text(0.5, 0.5, 'No Data Available', ha='center', va='center', transform=ax.transAxes, fontsize=16)
        ax.set_title(title)
        return self._save_chart(fig, chart_name, timestamp)

    def create_equity_curve(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """Create equity curve chart."""
        if analysis_result['raw_data']['daily_returns_df'].empty:
            logger.warning("No daily data for equity curve")
            return self._create_empty_chart('Portfolio Equity Curve - No Data', 'equity_curve', timestamp)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [3, 1]})
        plot_equity_curve(ax1, ax2, analysis_result)
        plt.tight_layout()
        return self._save_chart(fig, 'equity_curve', timestamp)

    def create_drawdown_analysis(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """Create drawdown analysis chart."""
        if analysis_result['raw_data']['daily_returns_df'].empty:
            logger.warning("No daily data for drawdown analysis")
            return self._create_empty_chart('Drawdown Analysis - No Data', 'drawdown_analysis', timestamp)

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 10), gridspec_kw={'height_ratios': [2, 1]})
        plot_drawdown_analysis(ax1, ax2, analysis_result)
        plt.tight_layout()
        return self._save_chart(fig, 'drawdown_analysis', timestamp)

    def create_strategy_heatmap(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """Create strategy performance heatmap."""
        if analysis_result['raw_data']['positions_df'].empty:
            logger.warning("No positions data for strategy heatmap")
            return self._create_empty_chart('Strategy Heatmap - No Data', 'strategy_heatmap', timestamp)

        fig, axes = plt.subplots(1, 3, figsize=(20, 10))
        try:
            if not os.path.exists("strategy_instances.csv"):
                raise FileNotFoundError("strategy_instances.csv not found, using fallback.")
            plot_heatmap_from_instances(fig, axes, analysis_result, self.config)
        except Exception as e:
            logger.warning(f"Failed to create heatmap from instances ({e}), attempting fallback.")
            plt.close(fig) # Close the old figure
            fig, axes = plt.subplots(1, 3, figsize=(18, 8)) # Create a new one for fallback
            try:
                plot_heatmap_from_positions(fig, axes, analysis_result['raw_data']['positions_df'], self.config)
            except Exception as fallback_e:
                logger.error(f"Fallback heatmap also failed: {fallback_e}")
                plt.close(fig) # Close again
                return self._create_empty_chart(f'Heatmap Failed: {fallback_e}', 'strategy_heatmap', timestamp)

        plt.tight_layout(rect=[0, 0, 1, 0.93])
        return self._save_chart(fig, 'strategy_heatmap', timestamp)

    def create_cost_impact_chart(self, analysis_result: Dict[str, Any], timestamp: str) -> str:
        """Create infrastructure cost impact chart."""
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        plot_cost_impact(fig, axes, analysis_result)
        plt.tight_layout()
        return self._save_chart(fig, 'cost_impact', timestamp)

    def generate_all_charts(self, analysis_result: Dict[str, Any]) -> Dict[str, str]:
        """Generate all portfolio charts with a consistent timestamp."""
        timestamp = self._generate_timestamp()
        chart_files = {}
        chart_functions = {
            'equity_curve': self.create_equity_curve,
            'drawdown_analysis': self.create_drawdown_analysis,
            'strategy_heatmap': self.create_strategy_heatmap,
            'cost_impact': self.create_cost_impact_chart
        }

        for name, func in chart_functions.items():
            try:
                chart_files[name] = func(analysis_result, timestamp)
            except Exception as e:
                logger.error(f"Failed to generate {name} chart: {e}", exc_info=True)
                chart_files[name] = f"ERROR: {e}"
        
        plt.close('all')
        logger.info(f"Generated {len([f for f in chart_files.values() if not f.startswith('ERROR')])} charts successfully.")
        return chart_files