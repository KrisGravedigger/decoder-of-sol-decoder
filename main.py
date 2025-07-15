import logging
import os
import sys
from dotenv import load_dotenv
import yaml
from typing import Optional
import pandas as pd

# --- Setup Project Path & Environment ---
load_dotenv()
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.append(project_root)

# --- Import Core Modules ---
from extraction.log_extractor import run_extraction
from reporting.strategy_instance_detector import run_instance_detection
# AIDEV-NOTE-GEMINI: Import the CLASS, not the deleted function.
from reporting.analysis_runner import AnalysisRunner
from reporting.orchestrator import PortfolioAnalysisOrchestrator
# AIDEV-NOTE-GEMINI: Import the centralized timestamp parser
from reporting.data_loader import _parse_custom_timestamp, load_and_prepare_positions


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

def load_main_config() -> dict:
    """Loads the main YAML configuration."""
    try:
        with open("reporting/config/portfolio_config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error(f"Could not load or parse portfolio_config.yaml: {e}", exc_info=True)
        return {}

def print_header(title: str):
    """Prints a formatted header."""
    print("\n" + "="*70)
    print(f"--- {title.upper()} ---")
    print("="*70)

def run_all_data_fetching(api_key: Optional[str]):
    """
    Central data fetching function. This is the ONLY function that should use the API key.
    It populates the cache for both per-position simulations and daily SOL/USDC rates.
    """
    if not api_key:
        print("\n[ERROR] No API key available. Cannot run data fetching.")
        logger.warning("run_all_data_fetching called without API key. Aborting.")
        return

    print_header("Step 3: Central Data Fetching (Online Step)")
    logger.info("--- Starting Central Data Fetching ---")

    try:
        positions_df = pd.read_csv("positions_to_analyze.csv")
        total_positions = len(positions_df)
        print(f"Found {total_positions} positions to process for cache population.")
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
        logger.error("Data fetching failed: positions_to_analyze.csv not found.")
        return

    # --- Safety Valve ---
    user_input = input(f"\n[SAFETY VALVE] This step will connect to the API to fill cache for {total_positions} positions. This may use API credits. Continue? (Y/n): ")
    if user_input.lower().strip() not in ('y', ''):
        print("Data fetching cancelled by user.")
        logger.warning("User stopped data fetching at safety valve.")
        return

    # AIDEV-NOTE-GEMINI: Data Integrity Fix.
    # We must parse timestamps immediately after reading the CSV to ensure all
    # downstream functions receive correct datetime objects, not strings.
    for col in ['open_timestamp', 'close_timestamp']:
        # Try standard datetime conversion first, which is fast.
        positions_df[col] = pd.to_datetime(positions_df[col], errors='coerce')
        
        # For rows that failed standard parsing, try the custom parser.
        failed_mask = positions_df[col].isnull()
        if failed_mask.any():
            # Apply custom parser only to strings in the original column for failed rows.
            # This handles cases where the original column name might be different.
            original_col_name = col
            if col == 'open_timestamp':
                # Heuristic to find the original raw string column if it exists
                if 'open' in positions_df.columns: original_col_name = 'open'
            elif col == 'close_timestamp':
                if 'close' in positions_df.columns: original_col_name = 'close'

            # Ensure we are applying to string representations
            positions_df.loc[failed_mask, col] = positions_df.loc[failed_mask, original_col_name].astype(str).apply(
                lambda x: _parse_custom_timestamp(x) if pd.notna(x) and x.lower() != 'nat' else pd.NaT
            )

    # Drop rows where timestamps are still invalid, which is expected for active positions
    positions_df.dropna(subset=['open_timestamp', 'close_timestamp'], inplace=True)
    total_positions_after_cleaning = len(positions_df) # Update total after dropping rows
    print(f"Found {total_positions_after_cleaning} valid, closed positions to process for cache population.")


    # --- Part 1: Fetch per-position price history for simulations ---
    print("\n[Part 1/2] Populating cache for position simulations...")
    online_runner = AnalysisRunner(api_key=api_key)
    # Use iterrows() for DataFrames with guaranteed correct dtypes
    for idx, row in positions_df.iterrows():
        # Recalculate index for progress display after cleaning
        progress_idx = positions_df.index.get_loc(idx) + 1
        position_id = row.get('position_id', f"index_{idx}")
        print(f"  Processing cache for position {progress_idx}/{total_positions_after_cleaning}...", end='\r')

        try:
            # Now that the DataFrame has correct dtypes, to_dict() works as expected.
            online_runner.analyze_single_position(row.to_dict())
        except Exception as e:
            logger.error(f"Error populating cache for position {position_id}: {e}")
    print("\n  Position cache processing complete.                            ")

    # --- Part 2: Fetch SOL/USDC daily rates for reporting ---
    print("\n[Part 2/2] Populating cache for SOL/USDC daily rates...")
    try:
        from reporting.infrastructure_cost_analyzer import InfrastructureCostAnalyzer

        # AIDEV-NOTE-GEMINI: FIX - We now use the already parsed, correct timestamp columns.
        min_date = positions_df['open_timestamp'].min()
        max_date = positions_df['close_timestamp'].max()

        if pd.notna(min_date) and pd.notna(max_date):
            # Add buffer for EMA calculations
            config = load_main_config()
            buffer_days = config.get('market_analysis', {}).get('ema_period', 50)
            fetch_start_dt = min_date - pd.Timedelta(days=buffer_days)
            
            print(f"  Fetching SOL/USDC rates for period: {fetch_start_dt.date()} to {max_date.date()}")
            cost_analyzer = InfrastructureCostAnalyzer(api_key=api_key)
            cost_analyzer.get_sol_usdc_rates(fetch_start_dt.strftime('%Y-%m-%d'), max_date.strftime('%Y-%m-%d'))
            print("  SOL/USDC rates cache updated.")
        else:
            print("[WARNING] Could not determine date range from positions. Skipping SOL/USDC rate fetching.")

    except Exception as e:
        logger.error(f"Failed to fetch SOL/USDC rates: {e}", exc_info=True)
        print(f"[ERROR] An error occurred while fetching SOL/USDC rates: {e}")

    print("\nCentral Data Fetching complete. Cache is populated.")
    logger.info("--- Central Data Fetching Finished ---")

def run_spot_vs_bidask_analysis_offline():
    """Wrapper function to run the simulation analysis in explicit offline mode."""
    print_header("Step 4: Spot vs. Bid-Ask Simulation (Offline)")
    try:
        # AIDEV-NOTE-GEMINI: Data Integrity Fix.
        # Use the centralized loader to ensure timestamps are correctly parsed
        # and data is clean before passing to the analysis runner.
        # We use a threshold of 0 to avoid filtering anything out at this stage.
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)

        if positions_df.empty:
            print("[WARNING] No valid positions found to analyze after cleaning. Skipping simulation.")
            logger.warning("run_spot_vs_bidask_analysis_offline: positions_df is empty after loading.")
            return

        # Initialize runner with NO API KEY to force cache-only operation
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
        # Initialize orchestrator with NO API KEY
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

    # Step 3 (Online)
    run_all_data_fetching(api_key)
    
    # Step 4 (Offline)
    run_spot_vs_bidask_analysis_offline()

    # Step 5 (Offline)
    run_comprehensive_report_offline()
        
    print_header("Full Pipeline Completed")

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
        print("3. Step 3: Fetch/Update All Historical Data (Online Step)")
        print("4. Step 4: Run Base Simulations (Offline - requires Step 3)")
        print("5. Step 5: Generate Comprehensive Report (Offline - requires Steps 3 & 4)")
        print("6. Run Full Pipeline (Steps 1 -> 5)")
        print("7. Exit")
        
        choice = input("Select an option (1-7): ")

        if choice == '1':
            print_header("Step 1: Log Processing")
            run_extraction()
        elif choice == '2':
            print_header("Step 2: Strategy Instance Detection")
            run_instance_detection()
        elif choice == '3':
            # This is the ONLY step that should get the api_key
            run_all_data_fetching(api_key)
        elif choice == '4':
            # This step runs offline
            run_spot_vs_bidask_analysis_offline()
        elif choice == '5':
            # This step also runs offline
            run_comprehensive_report_offline()
        elif choice == '6':
            run_full_pipeline(api_key)
        elif choice == '7':
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