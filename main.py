import logging
import os
import sys
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
    level=logging.INFO,
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
    print_header("Executing Full Pipeline")

    # Step 1 & 2
    print_header("Steps 1 & 2: Log Extraction & Strategy Detection")
    if not run_extraction(): return
    run_instance_detection()

    # Step 3 (Online) - Run in standard 'none' mode for a full pipeline run.
    from data_fetching.main_data_orchestrator import run_all_data_fetching
    run_all_data_fetching(api_key, refetch_mode='none')
    
    # Step 4 (Offline)
    run_spot_vs_bidask_analysis_offline()

    # Step 5 (Offline)
    run_comprehensive_report_offline()
        
    print_header("Full Pipeline Completed")

def cache_analyzer_menu():
    """Cache validation and analysis menu for TP/SL Optimizer."""
    while True:
        print("\n" + "-"*70)
        print("--- TP/SL Optimizer: Cache Analysis & Management ---")
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
        print("--- TP/SL ANALYSIS & OPTIMIZATION ---")
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
        print("--- MAIN MENU ---")
        print("="*70)
        print("1. Step 1: Process Logs and Extract Positions")
        print("2. Step 2: Detect Strategy Instances")
        print("3. Step 3: Fetch/Update Main Report Data (Online Step)")
        mode_label = get_mode_label(config, api_key)
        print(f"4. Step 4: Run Base Simulations {mode_label}")
        print(f"5. Step 5: Generate Comprehensive Report {mode_label}")
        print("6. TP/SL Optimizer: Cache Management (OCHLV+Volume)")
        print("7. Run Full Pipeline (Steps 1 -> 5)")
        print("8. TP/SL Analysis & Optimization")
        print("9. Exit")
        
        choice = input("Select an option (1-8): ")

        if choice == '1':
            print_header("Step 1: Log Processing")
            run_extraction()
        elif choice == '2':
            print_header("Step 2: Strategy Instance Detection")
            run_instance_detection()
        elif choice == '3':
            data_fetching_menu(api_key)
        elif choice == '4':
            run_spot_vs_bidask_analysis_offline()
        elif choice == '5':
            run_comprehensive_report_offline()
        elif choice == '6':
            cache_analyzer_menu()
        elif choice == '7':
            run_full_pipeline(api_key)
        elif choice == '8':
            tp_sl_analysis_menu()
        elif choice == '9':
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