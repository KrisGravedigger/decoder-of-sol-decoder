"""
HTML Report Generator Module

Creates comprehensive interactive HTML reports combining:
- Portfolio analytics results
- Market correlation analysis
- Weekend parameter impact analysis
- Spot vs. Bid-Ask simulations
- Interactive charts and visualizations
"""

import logging
import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
import plotly.offline as pyo
from jinja2 import Environment, FileSystemLoader
import pandas as pd

from .visualizations import interactive as interactive_charts
from .visualizations.interactive import range_test_charts

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class HTMLReportGenerator:
    """
    Generates comprehensive HTML reports with interactive charts.
    """
    
    def __init__(self, output_dir: str = "reporting/output", config: Dict[str, Any] = None):
        """
        Initialize HTML report generator.
        """
        self.output_dir = output_dir
        self.config = config or {}
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.templates_dir = os.path.join(base_dir, "templates")
        self.timestamp_format = "%Y%m%d_%H%M"
        
        os.makedirs(self.output_dir, exist_ok=True)
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir), autoescape=True)
        logger.info("HTML Report Generator initialized")
        
    def generate_comprehensive_report(self, 
                                    portfolio_analysis: Dict[str, Any],
                                    correlation_analysis: Optional[Dict[str, Any]] = None,
                                    weekend_analysis: Optional[Dict[str, Any]] = None,
                                    strategy_simulations: Optional[List[Dict]] = None) -> str:
        """
        Generate comprehensive HTML report combining all analyses.
        """
        logger.info("Generating comprehensive HTML report...")
        
        try:
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            charts = self._generate_interactive_charts(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations
            )
            
            template_data = self._prepare_template_data(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations, charts
            )
            
            html_content = self._render_html_template(template_data)
            
            filename = f"comprehensive_report_{timestamp}.html"
            filepath = os.path.join(self.output_dir, filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
                
            logger.info(f"Comprehensive HTML report saved: {filepath}")
            return filepath
            
        except Exception as e:
            logger.error(f"Failed to generate HTML report: {e}", exc_info=True)
            raise
            
    def _generate_interactive_charts(self, 
                                   portfolio_analysis: Dict[str, Any],
                                   correlation_analysis: Optional[Dict[str, Any]],
                                   weekend_analysis: Optional[Dict[str, Any]],
                                   strategy_simulations: Optional[List[Dict]]) -> Dict[str, str]:
        """
        Generate interactive Plotly charts for the report.
        """
        charts = {}
        
        charts['metrics_summary'] = interactive_charts.create_metrics_summary_chart(portfolio_analysis)
        charts['professional_equity_curve'] = interactive_charts.create_professional_equity_curve(portfolio_analysis)
        charts['professional_drawdown'] = interactive_charts.create_professional_drawdown_analysis(portfolio_analysis)
        charts['professional_strategy_heatmap'] = interactive_charts.create_professional_strategy_heatmap(portfolio_analysis, self.config if hasattr(self, 'config') else {})
        charts['professional_cost_impact'] = interactive_charts.create_professional_cost_impact(portfolio_analysis)
        charts['strategy_avg_pnl_summary'] = interactive_charts.create_strategy_avg_pnl_summary(self.config if hasattr(self, 'config') else {})
        
        if correlation_analysis and 'error' not in correlation_analysis:
            charts['correlation_analysis'] = interactive_charts.create_correlation_chart(correlation_analysis)
            charts['trend_performance'] = interactive_charts.create_trend_performance_chart(correlation_analysis)
            charts['ema_trend_chart'] = interactive_charts.create_ema_trend_chart(correlation_analysis)
            
        if weekend_analysis and not weekend_analysis.get('analysis_skipped'):
             if 'error' not in weekend_analysis:
                charts['weekend_comparison'] = interactive_charts.create_weekend_comparison_chart(weekend_analysis)
        
        if strategy_simulations:
            charts['strategy_simulation_comparison'] = interactive_charts.create_strategy_simulation_chart(strategy_simulations, portfolio_analysis)

        # Range Test Charts (Phase 4A)
        try:
            if os.path.exists("reporting/output/range_test_aggregated.csv"):
                agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                strategies = agg_df['strategy_instance_id'].unique()[:5]
                charts['range_test_heatmaps'] = []
                for strategy_id in strategies:
                    heatmap_html = range_test_charts.create_range_test_heatmap(agg_df, strategy_id, self.config.get('range_testing', {}).get('primary_ranking_metric', 'total_pnl'))
                    charts['range_test_heatmaps'].append({'strategy_id': strategy_id, 'html': heatmap_html})
                charts['range_test_optimal_table'] = range_test_charts.create_optimal_settings_table(agg_df, self.config.get('range_testing', {}).get('primary_ranking_metric', 'total_pnl'))
                charts['range_test_comparison'] = range_test_charts.create_strategy_comparison_chart(agg_df, self.config.get('range_testing', {}).get('primary_ranking_metric', 'total_pnl'))
        except Exception as e:
            logger.warning(f"Could not generate range test charts: {e}")

        # Phase 5: TP/SL Optimization Results
        try:
            if os.path.exists("reporting/output/tp_sl_recommendations.csv"):
                from optimization.tp_sl_optimizer import run_tp_sl_optimization
                optimization_results = run_tp_sl_optimization()
                if optimization_results['status'] == 'SUCCESS':
                    charts['optimization_matrix'] = optimization_results['visualizations']['performance_matrix']
                    charts['optimization_win_rate'] = optimization_results['visualizations']['win_rate_chart']
                    charts['optimization_sl_floor'] = optimization_results['visualizations']['sl_floor_table']
                    charts['optimization_summary'] = optimization_results['summary']
        except Exception as e:
            logger.warning(f"Could not generate optimization charts: {e}")

        return charts
            
    def _prepare_template_data(self, 
                             portfolio_analysis: Dict[str, Any],
                             correlation_analysis: Optional[Dict[str, Any]],
                             weekend_analysis: Optional[Dict[str, Any]],
                             strategy_simulations: Optional[List[Dict]],
                             charts: Dict[str, str]) -> Dict[str, Any]:
        """Prepare data for HTML template."""
        
        formatted_weekend_data = self._format_weekend_data(weekend_analysis)
        best_sim_strategy = self._get_best_sim_strategy(strategy_simulations)
        enriched_simulation_json = self._prepare_enriched_simulation_data()
        # AIDEV-NOTE-CLAUDE: Create a map of optimal settings for the interactive tool
        optimal_settings_map = {}
        try:
            if os.path.exists("reporting/output/range_test_aggregated.csv"):
                agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                metric = self.config.get('range_testing', {}).get('primary_ranking_metric', 'total_pnl')
                optimal_df = agg_df.loc[agg_df.groupby('strategy_instance_id')[metric].idxmax()]
                optimal_settings_map = optimal_df.set_index('strategy_instance_id')[['tp_level', 'sl_level']].to_dict('index')
        except Exception as e:
            logger.warning(f"Could not generate optimal settings map for interactive tool: {e}")

        # Pass tested TP/SL levels to the template for JS logic
        tested_tp_levels = self.config.get('range_testing', {}).get('tp_levels', [])
        tested_sl_levels = self.config.get('range_testing', {}).get('sl_levels', [])

        template_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'portfolio_analysis': portfolio_analysis,
            'correlation_analysis': correlation_analysis,
            'weekend_analysis': formatted_weekend_data,
            'strategy_simulations': strategy_simulations,
            'best_sim_strategy': best_sim_strategy,
            'charts': charts,
            'config': self.config,
            'plotly_js': pyo.get_plotlyjs(),
            'enriched_simulation_json': enriched_simulation_json,
            'optimal_settings_json': json.dumps(optimal_settings_map),
            'tested_tp_levels_json': json.dumps(sorted(tested_tp_levels)),
            'tested_sl_levels_json': json.dumps(sorted(tested_sl_levels))
        }
        
        return template_data

    def _format_weekend_data(self, weekend_analysis: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        if not weekend_analysis or weekend_analysis.get('analysis_skipped') or 'error' in weekend_analysis:
            return {'is_valid': False, 'raw': weekend_analysis}
        comparison = weekend_analysis.get('performance_comparison', {})
        return {
            'is_valid': True, 'raw': weekend_analysis,
            'metadata': weekend_analysis.get('analysis_metadata', {}),
            'recommendations': weekend_analysis.get('recommendations', {}),
            'current_scenario': comparison.get('current_scenario', {}),
            'alternative_scenario': comparison.get('alternative_scenario', {}),
            'impact_analysis': comparison.get('impact_analysis', {}),
        }

    def _get_best_sim_strategy(self, simulation_results: Optional[List[Dict]]) -> Optional[Dict]:
        if not simulation_results: return None
        sim_pnl = {}
        for res in simulation_results:
            if not res or 'simulation_results' not in res: continue
            for name, data in res['simulation_results'].items():
                if 'pnl_sol' in data:
                    sim_pnl[name] = sim_pnl.get(name, 0) + data['pnl_sol']
        if not sim_pnl: return None
        best_name = max(sim_pnl, key=sim_pnl.get)
        return {'name': best_name, 'pnl': sim_pnl[best_name]}

    def _prepare_enriched_simulation_data(self) -> str:
        """Prepare enriched simulation data for Phase 4B interactive tool."""
        try:
            if not os.path.exists("reporting/output/range_test_detailed_results.csv"):
                return json.dumps([])
            detailed_results_df = pd.read_csv("reporting/output/range_test_detailed_results.csv")
            positions_df = pd.read_csv("positions_to_analyze.csv")
            strategy_instances_df = pd.read_csv("strategy_instances.csv")
            
            from reporting.data_loader import _parse_custom_timestamp
            positions_df['open_timestamp'] = positions_df['open_timestamp'].apply(_parse_custom_timestamp)
            
            enriched_df = pd.merge(detailed_results_df, positions_df[['position_id', 'open_timestamp']], on='position_id', how='left')
            enriched_df = pd.merge(enriched_df, strategy_instances_df[['strategy_instance_id', 'analyzed_position_count']], on='strategy_instance_id', how='left')
            enriched_df['open_timestamp'] = enriched_df['open_timestamp'].dt.strftime('%Y-%m-%d %H:%M:%S')
            enriched_df = enriched_df.where(pd.notnull(enriched_df), None)
            
            logger.info(f"Enriched {len(enriched_df)} simulation results for Phase 4B")
            return enriched_df.to_json(orient='records')
        except Exception as e:
            logger.error(f"Failed to prepare enriched simulation data: {e}")
            return json.dumps([])

    def _render_html_template(self, template_data: Dict[str, Any]) -> str:
        """Render HTML template with data."""
        try:
            template = self.jinja_env.get_template('comprehensive_report.html')
            return template.render(**template_data)
        except Exception as e:
            logger.error(f"Failed to render HTML template: {e}")
            raise