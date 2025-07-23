import logging
import os
import sys
from dotenv import load_dotenv
from typing import Optional

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


def run_spot_vs_bidask_analysis_offline():
    """Wrapper function to run the simulation analysis in explicit offline mode."""
    print_header("Step 4: Spot vs. Bid-Ask Simulation (Offline)")
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)

        if positions_df.empty:
            print("[WARNING] No valid positions found to analyze after cleaning. Skipping simulation.")
            logger.warning("run_spot_vs_bidask_analysis_offline: positions_df is empty after loading.")
            return

        offline_runner = AnalysisRunner(api_key=None)
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
        print("5. Back to Main Menu")

        choice = input("Select an option (1-5): ")

        if choice == '1':
            enhanced_cache_fetching_menu()
        elif choice == '2':
            validate_cache_completeness_for_positions()
        elif choice == '3':
            check_volume_data_availability()
        elif choice == '4':
            cache_debugger_menu()
        elif choice == '5':
            break
        else:
            print("Invalid choice, please try again.")


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
        print("4. Step 4: Run Base Simulations (Offline - requires Step 3)")
        print("5. Step 5: Generate Comprehensive Report (Offline - requires Steps 3 & 4)")
        print("6. TP/SL Optimizer: Cache Management (OCHLV+Volume)")
        print("7. Run Full Pipeline (Steps 1 -> 5)")
        print("8. Exit")
        
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