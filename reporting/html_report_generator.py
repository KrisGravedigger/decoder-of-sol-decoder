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
import numpy as np
import concurrent.futures

from .visualizations import interactive as interactive_charts
from .visualizations.interactive import range_test_charts
from utils.common import sort_strategies_by_date_descending

# AIDEV-INTEGRATE-CLAUDE: Import UnifiedBaselineManager for validation
try:
    from simulations.unified_baseline_manager import UnifiedBaselineManager
    UNIFIED_MANAGER_AVAILABLE = True
except ImportError:
    UNIFIED_MANAGER_AVAILABLE = False

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
        
        # AIDEV-NOTE-CLAUDE: Initialize UnifiedBaselineManager if available and enabled
        self.baseline_manager = None
        if UNIFIED_MANAGER_AVAILABLE and config and config.get('unified_baseline', {}).get('enabled', False):
            try:
                self.baseline_manager = UnifiedBaselineManager(config)
                logger.info("UnifiedBaselineManager initialized for HTML report generation")
            except Exception as e:
                logger.warning(f"Failed to initialize UnifiedBaselineManager: {e}")
        
        logger.info("HTML Report Generator initialized")
        
    def generate_comprehensive_report(self, 
                                    portfolio_analysis: Dict[str, Any],
                                    correlation_analysis: Optional[Dict[str, Any]] = None,
                                    weekend_analysis: Optional[Dict[str, Any]] = None,
                                    strategy_simulations: Optional[List[Dict]] = None,
                                    tls_analysis: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate comprehensive HTML report combining all analyses.
        """
        logger.info("Generating comprehensive HTML report...")
        
        try:
            timestamp = datetime.now().strftime(self.timestamp_format)
            
            charts = self._generate_interactive_charts(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations, tls_analysis
            )
            
            template_data = self._prepare_template_data(
                portfolio_analysis, correlation_analysis, weekend_analysis, strategy_simulations, tls_analysis, charts
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
                                   strategy_simulations: Optional[List[Dict]],
                                   tls_analysis: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
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
                # Sort strategies by date (newest first) for heatmaps - show all strategies
                strategies = sort_strategies_by_date_descending(agg_df['strategy_instance_id'].unique().tolist())
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

        # TLS Analysis Charts (Phase 1, 2 & 3)
        if tls_analysis and tls_analysis.get('status') == 'SUCCESS':
            try:
                # Phase 1: Basic comparison charts
                charts['tls_comparison_summary'] = self._create_tls_comparison_chart(tls_analysis)
                charts['tls_strategy_effectiveness'] = self._create_tls_effectiveness_chart(tls_analysis)
                
                # Phase 2: Strategy overview visualizations
                detailed_results = tls_analysis.get('detailed_results')
                baseline_comparison = tls_analysis.get('baseline_comparison')
                
                if detailed_results is not None and baseline_comparison is not None:
                    baseline_data = self._extract_baseline_data(baseline_comparison)
                    strategy_overview_charts = self._generate_tls_strategy_overview_charts(detailed_results, baseline_data)
                    charts.update(strategy_overview_charts)
                    
                    # Phase 3: 4D Grid Visualization
                    grid_charts = self._generate_tls_4d_grid_charts(detailed_results)
                    charts.update(grid_charts)
                    
                    # Phase 4: Grouped Ranking
                    grouped_charts = self._generate_tls_grouped_ranking_charts(detailed_results, baseline_data)
                    charts.update(grouped_charts)
                    
                logger.info("Generated TLS analysis charts (Phase 1, 2 & 3)")
            except Exception as e:
                logger.warning(f"Could not generate TLS charts: {e}")

        return charts
            
    def _prepare_template_data(self, 
                             portfolio_analysis: Dict[str, Any],
                             correlation_analysis: Optional[Dict[str, Any]],
                             weekend_analysis: Optional[Dict[str, Any]],
                             strategy_simulations: Optional[List[Dict]],
                             tls_analysis: Optional[Dict[str, Any]],
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
                
                # Sort strategies by date (newest first) before creating the map
                sorted_strategies = sort_strategies_by_date_descending(optimal_df['strategy_instance_id'].tolist())
                optimal_df = optimal_df.set_index('strategy_instance_id').reindex(sorted_strategies)
                optimal_settings_map = optimal_df[['tp_level', 'sl_level']].to_dict('index')
        except Exception as e:
            logger.warning(f"Could not generate optimal settings map for interactive tool: {e}")

        # Pass tested TP/SL levels to the template for JS logic
        tested_tp_levels = self.config.get('range_testing', {}).get('tp_levels', [])
        tested_sl_levels = self.config.get('range_testing', {}).get('sl_levels', [])
        
        # Prepare TLS analysis data for template
        tls_summary = None
        tls_4d_data = None
        if tls_analysis and tls_analysis.get('status') == 'SUCCESS':
            baseline_comparison = tls_analysis.get('baseline_comparison')
            if baseline_comparison is not None:
                # Handle both DataFrame and dict cases
                if hasattr(baseline_comparison, 'empty'):
                    if not baseline_comparison.empty:
                        total_strategies = len(baseline_comparison)
                        improved_strategies = len(baseline_comparison[baseline_comparison['tls_improves_performance']])
                        improvement_rate = (improved_strategies / total_strategies * 100) if total_strategies > 0 else 0
                        avg_benefit = baseline_comparison['tls_benefit_pct'].mean()
                        
                        # Get top 5 TLS improvements for table
                        top_improvements = baseline_comparison.nlargest(5, 'tls_benefit_pct').to_dict('records')
                        
                        tls_summary = {
                            'total_strategies': total_strategies,
                            'improved_strategies': improved_strategies,
                            'improvement_rate': improvement_rate,
                            'avg_benefit': avg_benefit,
                            'top_improvements': top_improvements
                        }
                elif isinstance(baseline_comparison, list) and baseline_comparison:
                    # Handle list of dicts
                    total_strategies = len(baseline_comparison)
                    improved_strategies = len([row for row in baseline_comparison if row.get('tls_improves_performance', False)])
                    improvement_rate = (improved_strategies / total_strategies * 100) if total_strategies > 0 else 0
                    
                    tls_benefits = [row['tls_benefit_pct'] for row in baseline_comparison]
                    avg_benefit = sum(tls_benefits) / len(tls_benefits) if tls_benefits else 0
                    
                    # Get top 5 TLS improvements for table
                    top_improvements = sorted(baseline_comparison, key=lambda x: x['tls_benefit_pct'], reverse=True)[:5]
                    
                    tls_summary = {
                        'total_strategies': total_strategies,
                        'improved_strategies': improved_strategies,
                        'improvement_rate': improvement_rate,
                        'avg_benefit': avg_benefit,
                        'top_improvements': top_improvements
                    }
            
            # Prepare TLS 4D grid data for template
            # AIDEV-FIX-GEMINI: Prepare data for JS, ensuring the 'all strategies' grid is stored separately
            if charts.get('tls_4d_grid_data'):
                strategy_grids = charts.get('tls_strategy_grids', {})
                # Store the main grid under a special key for JS to easily access
                strategy_grids['__all_strategies__'] = charts['tls_4d_grid_data']
                
                tls_4d_data = {
                    'grid_data': charts['tls_4d_grid_data'], # Main grid for initial render
                    'available_strategies': charts.get('tls_available_strategies', []),
                    'strategy_grids': strategy_grids # Contains all individual grids + the main one
                }
        
        # Prepare TLS grouped ranking data for template
        tls_grouped_data = None
        if tls_analysis and tls_analysis.get('status') == 'SUCCESS' and charts.get('tls_grouped_combinations_exist'):
            tls_grouped_data = {
                'table_data': charts.get('tls_grouped_table_data', []),
                'summary': charts.get('tls_grouped_summary', {}),
                'grouped_combinations': True
            }

        # AIDEV-INTEGRATE-CLAUDE: Unified baseline validation for Phase 2
        unified_baseline_data = None
        if UNIFIED_MANAGER_AVAILABLE and self.config.get('unified_baseline', {}).get('enabled', False):
            try:
                manager = UnifiedBaselineManager(self.config)
                
                # Load range test results if available
                range_df = None
                if os.path.exists("reporting/output/range_test_aggregated.csv"):
                    range_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                
                # Get TLS results if available
                tls_df = None
                if tls_analysis and 'detailed_results' in tls_analysis:
                    tls_df = tls_analysis['detailed_results']
                    if not isinstance(tls_df, pd.DataFrame) and isinstance(tls_df, list):
                        tls_df = pd.DataFrame(tls_df)
                
                # Run validation if we have data
                if range_df is not None:
                    validation_report = manager.validate_consistency(range_df, tls_df)
                    
                    # Generate comparison report
                    comparison_df = manager.generate_comparison_report(range_df, tls_df)
                    
                    unified_baseline_data = {
                        'validation_passed': validation_report.is_consistent,
                        'consistency_rate': validation_report.to_dict()['consistency_rate'],
                        'inconsistencies': validation_report.inconsistencies[:5],  # Show top 5
                        'warnings': validation_report.warnings[:5],
                        'recommendations': comparison_df.to_dict('records') if not comparison_df.empty else [],
                        'total_strategies': validation_report.total_strategies,
                        'consistent_strategies': validation_report.consistent_strategies
                    }
                    
                    logger.info(f"Unified baseline validation: {validation_report.consistent_strategies}/{validation_report.total_strategies} consistent")
                    
            except Exception as e:
                logger.warning(f"Could not generate unified baseline validation: {e}")
        
        template_data = {
            'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            'portfolio_analysis': portfolio_analysis,
            'correlation_analysis': correlation_analysis,
            'weekend_analysis': formatted_weekend_data,
            'strategy_simulations': strategy_simulations,
            'tls_analysis': tls_analysis,  # Add TLS analysis data
            'tls_summary': tls_summary,    # Add processed TLS summary
            'tls_4d_data': tls_4d_data,    # Add TLS 4D grid data
            'tls_grouped_data': tls_grouped_data,  # Add TLS grouped ranking data
            'best_sim_strategy': best_sim_strategy,
            'charts': charts,
            'config': self.config,
            'plotly_js': pyo.get_plotlyjs(),
            'enriched_simulation_json': enriched_simulation_json,
            'optimal_settings_json': json.dumps(optimal_settings_map),
            'tested_tp_levels_json': json.dumps(sorted(tested_tp_levels)),
            'tested_sl_levels_json': json.dumps(sorted(tested_sl_levels)),
            'unified_baseline_data': unified_baseline_data  # AIDEV-INTEGRATE-CLAUDE: Add validation data
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
    
    def _create_tls_comparison_chart(self, tls_analysis: Dict[str, Any]) -> str:
        """Create TLS vs Baseline comparison chart."""
        try:
            import plotly.graph_objects as go
            from plotly.offline import plot
            
            baseline_comparison = tls_analysis.get('baseline_comparison')
            if baseline_comparison is None:
                return "<p>No TLS comparison data available</p>"
            
            # Convert DataFrame to dict if needed
            if hasattr(baseline_comparison, 'empty') and baseline_comparison.empty:
                return "<p>No TLS comparison data available</p>"
            
            if hasattr(baseline_comparison, 'to_dict'):
                baseline_data = baseline_comparison.to_dict('records')
            else:
                baseline_data = baseline_comparison
                
            if not baseline_data:
                return "<p>No TLS comparison data available</p>"
            
            # Create scatter plot: TLS benefit vs number of strategies
            fig = go.Figure()
            
            # Extract data for plotting
            baseline_pnl = [row['baseline_pnl'] for row in baseline_data]
            best_tls_pnl = [row['best_tls_pnl'] for row in baseline_data]
            strategy_names = [row['strategy_instance_id'] for row in baseline_data]
            tls_benefits = [row['tls_benefit_pct'] for row in baseline_data] # <-- POPRAWKA
            
            # Add scatter points
            fig.add_trace(go.Scatter(
                x=baseline_pnl,
                y=best_tls_pnl,
                mode='markers',
                text=strategy_names,
                hovertemplate="<b>%{text}</b><br>" +
                            "Baseline: %{x:.4f} SOL<br>" +
                            "TLS Best: %{y:.4f} SOL<br>" +
                            "<extra></extra>",
                marker=dict(
                    size=8,
                    color=tls_benefits,
                    colorscale='RdYlGn',
                    colorbar=dict(title="TLS Benefit (%)"),
                    line=dict(width=1, color='black')
                ),
                name='Strategies'
            ))
            
            # Add diagonal line (break-even)
            min_val = min(min(baseline_pnl), min(best_tls_pnl))
            max_val = max(max(baseline_pnl), max(best_tls_pnl))
            
            fig.add_trace(go.Scatter(
                x=[min_val, max_val],
                y=[min_val, max_val],
                mode='lines',
                line=dict(dash='dash', color='gray'),
                name='Break-even',
                hoverinfo='skip'
            ))
            
            fig.update_layout(
                title='TLS vs Baseline Performance Comparison',
                xaxis_title='Baseline PnL (SOL)',
                yaxis_title='Best TLS PnL (SOL)',
                height=500,
                showlegend=True
            )
            
            return plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create TLS comparison chart: {e}")
            return f"<p>Error generating TLS comparison chart: {e}</p>"
    
    def _extract_baseline_data(self, baseline_comparison) -> Dict[str, float]:
        """Extract baseline data from comparison results."""
        baseline_data = {}
        
        if baseline_comparison is None:
            return baseline_data
            
        try:
            # Handle DataFrame
            if hasattr(baseline_comparison, 'empty'):
                if not baseline_comparison.empty:
                    for _, row in baseline_comparison.iterrows():
                        baseline_data[row['strategy_instance_id']] = row['baseline_pnl']
            # Handle list of dicts
            elif isinstance(baseline_comparison, list):
                for row in baseline_comparison:
                    baseline_data[row['strategy_instance_id']] = row['baseline_pnl']
            # Handle dict
            elif isinstance(baseline_comparison, dict):
                baseline_data = baseline_comparison
                
        except Exception as e:
            logger.warning(f"Failed to extract baseline data: {e}")
            
        return baseline_data
    
    def _generate_tls_strategy_overview_charts(self, detailed_results, baseline_data: Dict[str, float]) -> Dict[str, Any]:
        """Generate Phase 2 TLS strategy overview visualization components."""
        try:
            from reporting.visualizations.interactive.tls_strategy_charts import (
                create_strategy_overview_scatter,
                create_global_top_combinations_table,
                create_strategy_performance_summary
            )
            
            # Convert detailed_results to DataFrame if needed
            if hasattr(detailed_results, 'empty'):
                tls_df = detailed_results
            elif isinstance(detailed_results, list):
                tls_df = pd.DataFrame(detailed_results)
            else:
                logger.warning("Unexpected detailed_results format for TLS charts")
                return {}
            
            if tls_df.empty:
                logger.warning("No TLS detailed results available for strategy overview")
                return {}
            
            # Generate strategy overview charts
            # AIDEV-NOTE-CLAUDE: Pass unified baseline if available
            if self.baseline_manager and not baseline_data:
                # Generate baseline data from UnifiedBaselineManager
                baseline_data = {}
                for strategy_id in tls_df['strategy_instance_id'].unique():
                    baseline_result = self.baseline_manager.calculate_strategy_baseline(
                        strategy_id, tls_df, metric='total_pnl'
                    )
                    baseline_data[strategy_id] = baseline_result.baseline_sol
            
            strategy_scatter_chart = create_strategy_overview_scatter(tls_df, baseline_data)
            # REFACTORED: This now returns a list of dictionaries (data), not HTML
            top_combinations_data = create_global_top_combinations_table(tls_df, baseline_data)
            performance_summary = create_strategy_performance_summary(tls_df, baseline_data)
            
            return {
                'tls_strategy_scatter_chart': strategy_scatter_chart,
                'tls_top_combinations_data': top_combinations_data, # NEW: Pass data to template
                'tls_performance_summary': performance_summary
            }
            
        except Exception as e:
            logger.error(f"Failed to generate TLS strategy overview charts: {e}")
            return {}
    
    def _generate_tls_4d_grid_charts(self, tls_detailed_results: pd.DataFrame) -> Dict[str, Any]:
        """
        AIDEV-FIX-CLAUDE: Create complete 4D grid, now with parallel processing for performance.
        
        - Generates grid data for "All Strategies".
        - Generates grid data for EACH individual strategy in parallel using ProcessPoolExecutor.
        - Passes all generated grids to the template for dynamic JS switching.
        """
        try:
            from reporting.visualizations.interactive.tls_4d_grid_charts import (
                create_4d_tls_grid,
                get_strategy_list_for_dropdown,
                calculate_global_color_scale
            )
        except ImportError as e:
            logger.error(f"DIAGNOSTYKA: KRYTYCZNY BŁĄD importu z tls_4d_grid_charts: {e}")
            return {}

        try:
            strategy_instances_df = pd.read_csv("strategy_instances.csv") if os.path.exists("strategy_instances.csv") else None
            baseline_data = None
            if os.path.exists("reporting/output/range_test_aggregated.csv"):
                agg_df = pd.read_csv("reporting/output/range_test_aggregated.csv")
                optimal_df = agg_df.loc[agg_df.groupby('strategy_instance_id')['total_pnl'].idxmax()]
                baseline_data = optimal_df.set_index('strategy_instance_id')['total_pnl'].to_dict()

            # 1. AIDEV-FIX-CLAUDE: Calculate a single, global, diverging color scale for ALL charts.
            logger.info("Calculating global diverging color scale for all TLS data...")
            global_color_config = calculate_global_color_scale(
                tls_detailed_results, 
                strategy_instances_df
            )
            
            # 2. Generate the main "All Strategies" grid.
            logger.info("Generating grid for 'All Strategies' view...")
            all_strategies_grid_data = create_4d_tls_grid(
                tls_detailed_results,
                strategy_filter=None,
                strategy_instances_df=strategy_instances_df,
                baseline_data=baseline_data,
                include_win_rate_data=True,
                global_color_config_override=global_color_config
            )
            
            # 3. AIDEV-FIX-CLAUDE: Generate grids for each strategy in parallel.
            strategy_grids = {}
            available_strategies = get_strategy_list_for_dropdown(tls_detailed_results)
            logger.info(f"Generating individual grids for {len(available_strategies)} strategies in parallel...")
            
            # Using ProcessPoolExecutor for CPU-bound tasks (Pandas operations)
            with concurrent.futures.ProcessPoolExecutor() as executor:
                # Map strategies to future jobs
                future_to_strategy = {
                    executor.submit(
                        create_4d_tls_grid,
                        tls_detailed_results,
                        strategy_id, # Pass strategy_id as the filter
                        strategy_instances_df,
                        baseline_data,
                        True,
                        global_color_config # Pass the SAME global config to all processes
                    ): strategy_id for strategy_id in available_strategies
                }
                
                for future in concurrent.futures.as_completed(future_to_strategy):
                    strategy_id = future_to_strategy[future]
                    try:
                        strategy_grids[strategy_id] = future.result()
                    except Exception as exc:
                        logger.error(f"Generating grid for strategy {strategy_id} failed: {exc}")

            logger.info("Successfully finished generating all TLS 4D grid visualizations.")
            
            return {
                'tls_4d_grid_data': all_strategies_grid_data,
                'tls_available_strategies': available_strategies,
                'tls_strategy_grids': strategy_grids  # This contains grids for EACH strategy
            }
            
        except Exception as e:
            logger.error(f"Failed to generate TLS 4D grid charts: {e}", exc_info=True)
            return {}
    
    def _create_tls_effectiveness_chart(self, tls_analysis: Dict[str, Any]) -> str:
        """Create TLS effectiveness summary chart."""
        try:
            import plotly.graph_objects as go
            from plotly.offline import plot
            
            baseline_comparison = tls_analysis.get('baseline_comparison')
            if baseline_comparison is None:
                return "<p>No TLS effectiveness data available</p>"
            
            # Convert DataFrame to dict if needed
            if hasattr(baseline_comparison, 'empty') and baseline_comparison.empty:
                return "<p>No TLS effectiveness data available</p>"
            
            if hasattr(baseline_comparison, 'to_dict'):
                baseline_data = baseline_comparison.to_dict('records')
            else:
                baseline_data = baseline_comparison
                
            if not baseline_data:
                return "<p>No TLS effectiveness data available</p>"
            
            # Calculate summary statistics
            total_strategies = len(baseline_data)
            improved_count = len([row for row in baseline_data if row.get('tls_improves_performance', False)])
            improvement_rate = (improved_count / total_strategies * 100) if total_strategies > 0 else 0
            
            tls_benefits = [row['tls_benefit_pct'] for row in baseline_data] # <-- POPRAWKA
            avg_benefit = sum(tls_benefits) / len(tls_benefits) if tls_benefits else 0
            best_benefit = max(tls_benefits) if tls_benefits else 0
            worst_impact = min(tls_benefits) if tls_benefits else 0
            
            # Create bar chart
            fig = go.Figure()
            
            categories = ['Improvement Rate (%)', 'Avg Benefit (%)', 'Best Benefit (%)', 'Worst Impact (%)']
            values = [improvement_rate, avg_benefit, best_benefit, worst_impact]
            colors = ['blue', 'green' if avg_benefit > 0 else 'red', 'darkgreen', 'darkred' if worst_impact < 0 else 'orange']
            
            fig.add_trace(go.Bar(
                x=categories,
                y=values,
                marker_color=colors,
                text=[f"{v:.1f}" for v in values],
                textposition='auto'
            ))
            
            fig.update_layout(
                title=f'TLS Effectiveness Summary ({total_strategies} Strategies)',
                yaxis_title='Percentage',
                height=400,
                showlegend=False
            )
            
            return plot(fig, output_type='div', include_plotlyjs=False)
            
        except Exception as e:
            logger.error(f"Failed to create TLS effectiveness chart: {e}")
            return f"<p>Error generating TLS effectiveness chart: {e}</p>"
    
    def _generate_tls_grouped_ranking_charts(self, tls_detailed_results: pd.DataFrame, baseline_data: Dict[str, float]) -> Dict[str, Any]:
        """
        Generate TLS grouped ranking visualizations for Phase 4.
        
        Args:
            tls_detailed_results: DataFrame with TLS simulation results
            baseline_data: Dictionary mapping strategy_id -> best_non_tls_pnl
            
        Returns:
            Dictionary with grouped ranking charts and data
        """
        try:
            from reporting.visualizations.interactive.tls_grouped_ranking import (
                group_4d_combinations,
                prepare_grouped_ranking_data, # MODIFIED: Use new data prep function
                create_group_summary_statistics
            )
            
            # Load strategy instances data for percentage calculations
            strategy_instances_df = None
            if os.path.exists("strategy_instances.csv"):
                strategy_instances_df = pd.read_csv("strategy_instances.csv")
            
            # Generate 4D groupings
            grouped_combinations = group_4d_combinations(
                tls_detailed_results, 
                baseline_data, 
                strategy_instances_df=strategy_instances_df,
                max_combined_distance=4.0
            )
            
            if not grouped_combinations:
                logger.warning("No TLS grouped combinations generated")
                return {}
            
            # Create structured data for the ranking table
            grouped_table_data = prepare_grouped_ranking_data(grouped_combinations)
            
            # Generate summary statistics
            grouped_summary = create_group_summary_statistics(grouped_combinations)
            
            logger.info(f"Generated TLS grouped ranking with {len(grouped_combinations)} groups")
            
            return {
                'tls_grouped_table_data': grouped_table_data,
                'tls_grouped_summary': grouped_summary,
                'tls_grouped_combinations_exist': True if grouped_combinations else False
            }
            
        except Exception as e:
            logger.error(f"Failed to generate TLS grouped ranking charts: {e}")
            return {}