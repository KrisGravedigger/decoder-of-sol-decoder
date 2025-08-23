import logging
import os
import sys

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio_analysis.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from dotenv import load_dotenv
from typing import Optional
from typing import Dict
from datetime import datetime

# --- Setup Project Path & Environment ---
load_dotenv()
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Import Core Modules & Refactored Orchestrators ---
from utils.common import load_main_config, print_header
from extraction.log_extractor import run_extraction
from reporting.strategy_instance_detector import run_instance_detection
from reporting.analysis_runner import AnalysisRunner
from reporting.orchestrator import PortfolioAnalysisOrchestrator
from reporting.data_loader import load_and_prepare_positions
from reporting.price_cache_manager import PriceCacheManager
from data_fetching.main_data_orchestrator import data_fetching_menu
from data_fetching.cache_orchestrator import (
    enhanced_cache_fetching_menu, 
    validate_cache_completeness_for_positions, 
    check_volume_data_availability
)
from tools.cache_debugger import cache_debugger_menu

# --- Configure Logging ---
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio_analysis.log', mode='w'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configure Deep Debug Logging ---
deep_debug_handler = logging.FileHandler('deep_debug.log', mode='w')
deep_debug_handler.setLevel(logging.DEBUG)
deep_debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
deep_debug_handler.setFormatter(deep_debug_formatter)
logging.getLogger('DEEP_DEBUG').addHandler(deep_debug_handler)
logging.getLogger('DEEP_DEBUG').setLevel(logging.DEBUG)
logging.getLogger('DEEP_DEBUG').propagate = False

def get_mode_label(config: Dict, api_key: Optional[str]) -> str:
    """Determine current mode based on config and API key availability."""
    is_cache_only = config.get('api_settings', {}).get('cache_only', False)
    prefer_offline = config.get('data_source', {}).get('prefer_offline_cache', False)
    
    if is_cache_only or not api_key:
        return "(Offline Mode)"
    elif api_key and prefer_offline:
        return "(Hybrid Mode - Offline Preferred)"
    else:
        return "(Online Mode)"

def run_spot_vs_bidask_analysis_offline():
    """Wrapper function to run the simulation analysis in explicit offline mode."""
    print_header("Step 4: Spot vs. Bid-Ask Simulation (Offline)")
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)

        if positions_df.empty:
            print("[WARNING] No valid positions found to analyze after cleaning. Skipping simulation.")
            logger.warning("run_spot_vs_bidask_analysis_offline: positions_df is empty after loading.")
            return

        config = load_main_config()
        offline_runner = AnalysisRunner(api_key=None, config=config)
        offline_runner.analyze_all_positions(positions_df)
        print("Spot vs. Bid-Ask simulation (offline) completed successfully.")
        print("Note: Results are used in the comprehensive report, no separate file is generated here.")
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
    except Exception as e:
        logger.error(f"Spot vs. Bid-Ask simulation failed: {e}", exc_info=True)
        print(f"\n[ERROR] An error occurred during the simulation: {e}")

def run_comprehensive_report_offline():
    """Wrapper function to generate the final HTML report in explicit offline mode."""
    print_header("Step 5: Generate Comprehensive Report (Offline)")
    try:
        orchestrator = PortfolioAnalysisOrchestrator(api_key=None)
        result = orchestrator.run_comprehensive_analysis('positions_to_analyze.csv')
        if result.get('status') == 'SUCCESS':
            print("\nComprehensive report generated successfully!")
            report_path = result.get('files_generated', {}).get('html_report', 'N/A')
            print(f"📊 Find your interactive report at: {report_path}")
        else:
            print(f"\n[ERROR] Report generation failed: {result.get('error', 'Unknown error')}")
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
    except Exception as e:
        logger.error(f"Comprehensive reporting failed: {e}", exc_info=True)
        print(f"\n[ERROR] An error occurred during report generation: {e}")

def run_full_pipeline(api_key: Optional[str]):
    """Executes the entire analysis pipeline from start to finish."""
    print_header("Executing Full Standard Pipeline")

    # Step 1 & 2
    print_header("Steps 1 & 2: Log Extraction & Strategy Detection")
    if not run_extraction(): return
    run_instance_detection()

    # Step 3 (Online) - Run in standard 'none' mode for a full pipeline run.
    from data_fetching.main_data_orchestrator import run_all_data_fetching
    print_header("Step 3: Data Fetching for Simulations & Reports")
    run_all_data_fetching(api_key, refetch_mode='none')
    
    # Step 4 (Offline)
    print_header("Step 4: Running Base Simulations")
    run_spot_vs_bidask_analysis_offline()

    # Step 5 (Offline)
    print_header("Step 5: Generating Comprehensive Report")
    run_comprehensive_report_offline()
        
    print_header("Full Standard Pipeline Completed")

def cache_analyzer_menu():
    """Cache validation and analysis menu for TP/SL Optimizer."""
    while True:
        print("\n" + "-"*70)
        print("--- Cache Management & Debugging ---")
        print("Manage and analyze OCHLV+Volume data for optimization.")
        print("-"*70)
        print("1. Fetch/Update OCHLV+Volume Data (Online)")
        print("2. Validate Cache Completeness for All Positions")
        print("3. Check Volume Data Availability (Sample)") 
        print("4. Cache Debugging Tools")
        print("5. Refresh Offline Processed Cache")
        print("6. Validate Offline Cache Completeness")
        print("7. Back to Main Menu")

        choice = input("Select an option (1-7): ")

        if choice == '1':
            enhanced_cache_fetching_menu()
        elif choice == '2':
            validate_cache_completeness_for_positions()
        elif choice == '3':
            check_volume_data_availability()
        elif choice == '4':
            cache_debugger_menu()
        elif choice == '5':
            # Refresh offline processed cache
            config = load_main_config()
            cache_manager = PriceCacheManager(config=config)
            cache_manager.refresh_offline_cache()
        elif choice == '6':
            # Validate offline cache completeness
            config = load_main_config()
            cache_manager = PriceCacheManager(config=config)
            cache_manager.validate_offline_cache_completeness()
        elif choice == '7':
            break
        else:
            print("Invalid choice, please try again.")

def tp_sl_analysis_menu():
    """
    TP/SL Analysis submenu.
    """
    while True:
        print("\n" + "="*70)
        print("--- Post-Close 'What-If' Analysis (Legacy Phase 3B) ---")
        print("="*70)
        print("1. Run post-close analysis for recent positions")
        print("2. Generate TP/SL optimization report")
        print("3. View analysis results and statistics")
        print("4. Export ML dataset for Phase 4")
        print("5. Back to main menu")
        
        choice = input("\nSelect option (1-5): ").strip()
        
        if choice == "1":
            run_post_close_analysis()
        elif choice == "2":
            generate_tp_sl_report()
        elif choice == "3":
            view_analysis_results()
        elif choice == "4":
            export_ml_dataset()
        elif choice == "5":
            break

def tp_sl_range_testing_menu():
    """
    TP/SL Range Testing submenu for Phase 4A.
    """
    while True:
        print("\n" + "="*70)
        print("--- TP/SL Range Testing & Optimization Submenu (Phase 4 & 5) ---")
        print("="*70)
        print("1. Run TP/SL range simulation for all positions")
        print("2. Generate range test report with heatmaps")
        print("3. View optimal TP/SL recommendations")
        print("4. Export detailed simulation results")
        print("5. Run TP/SL Optimization Engine (Phase 5)")
        print("6. Back to main menu")
        
        choice = input("\nSelect option (1-6): ").strip()
        
        if choice == "1":
            run_tp_sl_range_simulation()
        elif choice == "2":
            generate_range_test_report()
        elif choice == "3":
            view_optimal_recommendations()
        elif choice == "4":
            export_range_test_results()
        elif choice == "5":
            run_tp_sl_optimization_engine()
        elif choice == "6":
            break

def run_tp_sl_range_simulation():
    """Run TP/SL range testing simulation."""
    try:
        from simulations.range_test_simulator import TpSlRangeSimulator
        from reporting.data_loader import load_and_prepare_positions
        from reporting.post_close_analyzer import PostCloseAnalyzer
        
        print("\nLoading enriched positions data...")
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", 0.01)
        
        # Check if strategy_instance_id exists
        if 'strategy_instance_id' not in positions_df.columns:
            print("❌ ERROR: positions_to_analyze.csv is not enriched with strategy_instance_id!")
            print("Please run Step 2 (Detect Strategies & Enrich Data) first.")
            return
            
        config = load_main_config()
        if not config.get('range_testing', {}).get('enable', False):
            print("❌ Range testing is disabled in config. Set range_testing.enable: true")
            return
        
        # Create a single, correctly configured analyzer instance
        post_close_analyzer = PostCloseAnalyzer()
            
        simulator = TpSlRangeSimulator(config, post_close_analyzer)
        print(f"\nRunning simulation for {len(positions_df)} positions...")
        print(f"TP levels: {config['range_testing']['tp_levels']}")
        print(f"SL levels: {config['range_testing']['sl_levels']}")
        
        results = simulator.run_simulation(positions_df)
        
        print(f"\n✅ Simulation complete!")
        print(f"  Total simulations: {len(results['detailed_results'])}")
        print(f"  Strategy instances analyzed: {len(results['aggregated_results'])}")
        
        # Save results
        results['detailed_results'].to_csv("reporting/output/range_test_detailed_results.csv", index=False)
        results['aggregated_results'].to_csv("reporting/output/range_test_aggregated.csv", index=False)
        print("\nResults saved to reporting/output/")
        
    except Exception as e:
        logger.error(f"Range simulation failed: {e}", exc_info=True)
        print(f"❌ Simulation failed: {e}")

def generate_range_test_report():
    """Generate HTML report with range test heatmaps."""
    try:
        print("\nGenerating range test report...")
        # This will be integrated into the main HTML report
        print("✅ Range test results will be included in the next comprehensive report generation (Step 5)")
        
    except Exception as e:
        print(f"❌ Report generation failed: {e}")

def view_optimal_recommendations():
    """View optimal TP/SL recommendations per strategy."""
    try:
        import pandas as pd
        
        agg_results = pd.read_csv("reporting/output/range_test_aggregated.csv")
        config = load_main_config()
        metric = config.get('range_testing', {}).get('primary_ranking_metric', 'total_pnl')
        
        # Find best combination for each strategy
        optimal = agg_results.loc[agg_results.groupby('strategy_instance_id')[metric].idxmax()]
        
        print("\n" + "="*70)
        print("OPTIMAL TP/SL RECOMMENDATIONS")
        print("="*70)
        print(f"Based on: {metric}")
        print("-"*70)
        
        for _, row in optimal.iterrows():
            print(f"\nStrategy: {row['strategy_instance_id']}")
            print(f"  Optimal TP: {row['tp_level']}%")
            print(f"  Optimal SL: {row['sl_level']}%")
            print(f"  {metric}: {row[metric]:.3f}")
            
    except FileNotFoundError:
        print("❌ No simulation results found. Please run simulation first (option 1).")
    except Exception as e:
        print(f"❌ Failed to view recommendations: {e}")

def export_range_test_results():
    """Export detailed range test results."""
    try:
        print("\n✅ Results already exported to:")
        print("  - reporting/output/range_test_detailed_results.csv")
        print("  - reporting/output/range_test_aggregated.csv")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

def run_tp_sl_optimization_engine():
    """Run Phase 5 TP/SL Optimization Engine."""
    try:
        from optimization.tp_sl_optimizer import run_tp_sl_optimization
        
        print("\n" + "="*70)
        print("RUNNING TP/SL OPTIMIZATION ENGINE (Phase 5)")
        print("="*70)
        
        # Check prerequisites
        if not os.path.exists("reporting/output/range_test_detailed_results.csv"):
            print("❌ ERROR: Range test results not found!")
            print("Please run Phase 4A simulation first (option 1).")
            return
            
        config = load_main_config()
        if not config.get('optimization_engine', {}).get('enable', False):
            print("❌ Optimization engine is disabled in config.")
            print("Set optimization_engine.enable: true in portfolio_config.yaml")
            return
            
        print("Analyzing simulation results to find optimal TP/SL parameters...")
        print(f"Minimum positions required: {config.get('optimization_engine', {}).get('min_positions_for_optimization', 30)}")
        print(f"Time weighting: {'Enabled' if config.get('optimization_engine', {}).get('time_weighting', {}).get('enable', True) else 'Disabled'}")
        
        results = run_tp_sl_optimization()
        
        if results['status'] == 'SUCCESS':
            summary = results['summary']
            print(f"\n✅ Optimization complete!")
            print(f"  Strategies analyzed: {summary['total_strategies']}")
            print(f"  Changes recommended: {summary['changes_recommended']}")
            print(f"  Average improvement: {summary['avg_improvement']:.2f}%")
            print(f"  Maximum improvement: {summary['max_improvement']:.2f}%")
            print("\nRecommendations exported to: reporting/output/tp_sl_recommendations.csv")
            print("Optimization results will be included in the next comprehensive report.")
            
        elif results['status'] == 'NO_QUALIFIED_STRATEGIES':
            print(f"\n⚠️  {results['message']}")
            print("Consider lowering min_positions_for_optimization in config.")
            
        else:
            print(f"\n❌ Optimization failed: {results.get('error', 'Unknown error')}")
            
    except Exception as e:
        logger.error(f"Optimization engine failed: {e}")
        print(f"❌ Failed to run optimization: {e}")

def run_post_close_analysis():
    """
    Run post-close analysis with user feedback.
    """
    try:
        from reporting.post_close_analyzer import PostCloseAnalyzer
        from reporting.data_loader import load_and_prepare_positions
        
        analyzer = PostCloseAnalyzer()
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", 0.01)
        
        print(f"\nLoaded {len(positions_df)} positions for analysis...")
        
        # Apply filters and show results
        filtered_df = analyzer.apply_scope_filters(positions_df)
        print(f"After applying filters: {len(filtered_df)} positions selected")
        
        if filtered_df.empty:
            print("No positions meet analysis criteria. Check configuration filters.")
            return
            
        # Run analysis with progress
        results = analyzer.run_bulk_analysis(filtered_df)
        
        print(f"\n✅ Analysis complete!")
        print(f"  Successful: {results['successful_analyses']}/{results['total_positions']}")
        print(f"  Missed opportunities identified: {results['positions_with_missed_upside']}")
        print(f"  Average missed upside: {results['avg_missed_upside_pct']:.1f}%")
        
        # Save results for later viewing
        import json
        with open("reporting/output/tp_sl_analysis_results.json", "w") as f:
            json.dump(results, f, indent=2, default=str)
        print("\nResults saved to reporting/output/tp_sl_analysis_results.json")
        
    except Exception as e:
        logger.error(f"Post-close analysis failed: {e}")
        print(f"❌ Analysis failed: {e}")

def generate_tp_sl_report():
    """
    Generate comprehensive TP/SL optimization report.
    """
    try:
        import json
        
        # Load previous analysis results
        with open("reporting/output/tp_sl_analysis_results.json", "r") as f:
            results = json.load(f)
            
        # Generate report content
        report_lines = [
            "="*70,
            "TP/SL OPTIMIZATION ANALYSIS REPORT",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "="*70,
            "",
            f"Total Positions Analyzed: {results['total_positions']}",
            f"Successful Analyses: {results['successful_analyses']}",
            f"Positions with Missed Upside (>2%): {results['positions_with_missed_upside']}",
            f"Average Missed Upside: {results['avg_missed_upside_pct']:.1f}%",
            "",
            "TOP MISSED OPPORTUNITIES:",
            "-"*50,
        ]
        
        # Sort by missed upside
        sorted_results = sorted(
            [r for r in results['analysis_results'] if r['analysis_successful'] and r.get('missed_upside_pct', 0) > 0],
            key=lambda x: x['missed_upside_pct'],
            reverse=True
        )[:10]
        
        for r in sorted_results:
            report_lines.append(
                f"{r['position_id']}: {r['missed_upside_pct']:.1f}% missed upside, "
                f"optimal exit after {r['days_to_optimal_exit']:.1f} days"
            )
            
        # Save report
        report_path = f"reporting/output/tp_sl_optimization_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        with open(report_path, "w") as f:
            f.write("\n".join(report_lines))
            
        print(f"\n✅ Report generated: {report_path}")
        
    except FileNotFoundError:
        print("❌ No analysis results found. Please run analysis first (option 1).")
    except Exception as e:
        print(f"❌ Report generation failed: {e}")

def view_analysis_results():
    """
    View summary of analysis results.
    """
    try:
        import json
        
        with open("reporting/output/tp_sl_analysis_results.json", "r") as f:
            results = json.load(f)
            
        print("\n" + "="*70)
        print("TP/SL ANALYSIS RESULTS SUMMARY")
        print("="*70)
        print(f"Total Positions: {results['total_positions']}")
        print(f"Successfully Analyzed: {results['successful_analyses']}")
        print(f"Positions with Missed Upside: {results['positions_with_missed_upside']}")
        print(f"Average Missed Upside: {results['avg_missed_upside_pct']:.1f}%")
        
        # Show distribution
        if results['analysis_results']:
            missed_upsides = [r['missed_upside_pct'] for r in results['analysis_results'] 
                            if r['analysis_successful'] and r.get('missed_upside_pct', 0) > 0]
            
            if missed_upsides:
                print(f"\nMissed Upside Distribution:")
                print(f"  Min: {min(missed_upsides):.1f}%")
                print(f"  Max: {max(missed_upsides):.1f}%")
                print(f"  Median: {sorted(missed_upsides)[len(missed_upsides)//2]:.1f}%")
                
    except FileNotFoundError:
        print("❌ No analysis results found. Please run analysis first (option 1).")
    except Exception as e:
        print(f"❌ Failed to view results: {e}")

def export_ml_dataset():
    """
    Export ML dataset for Phase 4.
    """
    try:
        from reporting.post_close_analyzer import PostCloseAnalyzer
        
        analyzer = PostCloseAnalyzer()
        output_path = analyzer.export_ml_dataset()
        
        print(f"\n✅ ML dataset exported to: {output_path}")
        
    except Exception as e:
        print(f"❌ Export failed: {e}")

# --- New Menu Wrapper Functions ---

def run_data_preparation_pipeline():
    """Step 1 & 2 combined: Log Processing and Strategy Enrichment."""
    print_header("Steps 1 & 2: Log Processing & Strategy Enrichment")
    if not run_extraction(): return
    run_instance_detection()
    print_header("Data Preparation Completed")

def run_core_analysis_and_report_pipeline():
    """Steps 4 & 5 combined: Run Base Simulations and Generate Report."""
    print_header("Steps 4 & 5: Running Analysis & Generating Report")
    run_spot_vs_bidask_analysis_offline()
    run_comprehensive_report_offline()
    print_header("Core Analysis & Reporting Completed")

def run_full_optimization_pipeline(api_key: Optional[str]):
    """Executes the entire analysis pipeline including optimization (Steps 1-5 + Phase 4/5)."""
    print_header("Executing Full Optimization Pipeline")

    # 1. Data Preparation (Steps 1 & 2)
    print_header("1. Log Extraction & Strategy Enrichment")
    if not run_extraction(): return
    run_instance_detection()

    # 2. Data Fetching Online (Step 3)
    print_header("2. Data Fetching for Simulations & Reports")
    from data_fetching.main_data_orchestrator import run_all_data_fetching
    run_all_data_fetching(api_key, refetch_mode='none')
    
    # 3. Base Simulation (Part of original Step 4)
    print_header("3. Running Base Spot vs. Bid-Ask Simulations")
    run_spot_vs_bidask_analysis_offline()
    
    # 4. TP/SL Range Simulation (Phase 4A Prerequisite)
    print_header("4. Running TP/SL Range Simulation (Phase 4A Prerequisite)")
    run_tp_sl_range_simulation()

    # 5. Optimization Engine (Phase 5)
    print_header("5. Running TP/SL Optimization Engine (Phase 5)")
    run_tp_sl_optimization_engine()

    # 6. Final Report Generation (Step 5)
    print_header("6. Generating Comprehensive Report with All Analyses")
    run_comprehensive_report_offline()
        
    print_header("Full Optimization Pipeline Completed")


def main_menu():
    """Displays the main interactive menu."""
    config = load_main_config()
    is_cache_only = config.get('api_settings', {}).get('cache_only', False)
    api_key = os.getenv("MORALIS_API_KEY")

    if is_cache_only:
        print("\n" + "!"*70)
        print("!!! CACHE-ONLY MODE IS ACTIVE (via config.yaml) !!!")
        print("!!! No new API calls will be made.                   !!!")
        print("!"*70)
        api_key = None # Override API key
    elif not api_key:
        logger.warning("MORALIS_API_KEY not found in .env file. API-dependent steps will fail.")

    while True:
        print("\n" + "="*70)
        print("--- SOL DECODER PORTFOLIO ANALYZER ---")
        mode_label = get_mode_label(config, api_key)
        print(f"Current Operational Mode: {mode_label}")
        print("="*70)
        print("--- CORE WORKFLOW ---")
        print("1. Data Preparation (Logs -> Enriched Positions)")
        print("2. Data Fetching (Online: Get market data for analysis)")
        print("3. Reporting (Offline: Generate report from prepared data)")
        print("-"*70)
        print("--- AUTOMATED PIPELINES ---")
        print("4. Full Standard Pipeline (Steps 1-3 -> Report with Phase 4A/B)")
        print("5. Full Optimization Pipeline (Steps 1-3 -> Phase 4A Sim -> Phase 5 Engine -> Final Report)")
        print("-"*70)
        print("--- ADVANCED ANALYSIS & TOOLS ---")
        print("6. TP/SL Range Testing & Optimization Submenu (Phase 4 & 5)")
        print("7. Post-Close 'What-If' Analysis (Legacy Phase 3B)")
        print("8. Cache Management & Debugging")
        print("0. Exit")
        
        choice = input("Select an option (0-8): ")

        if choice == '1':
            run_data_preparation_pipeline()
        elif choice == '2':
            data_fetching_menu(api_key)
        elif choice == '3':
            run_core_analysis_and_report_pipeline()
        elif choice == '4':
            run_full_pipeline(api_key)
        elif choice == '5':
            run_full_optimization_pipeline(api_key)
        elif choice == '6':
            tp_sl_range_testing_menu()
        elif choice == '7':
            tp_sl_analysis_menu()
        elif choice == '8':
            cache_analyzer_menu()
        elif choice == '0':
            print("Exiting application...")
            break
        else:
            print("Invalid choice, please try again.")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.critical(f"An unhandled exception occurred in main: {e}", exc_info=True)
        print(f"\n[CRITICAL ERROR] An unexpected error occurred: {e}")