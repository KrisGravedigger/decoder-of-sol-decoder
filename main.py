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
from reporting.analysis_runner import run_spot_vs_bidask_analysis
from reporting.orchestrator import PortfolioAnalysisOrchestrator

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('portfolio_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# --- Configure Deep Debug Logging ---
deep_debug_handler = logging.FileHandler('deep_debug.log', mode='w')
deep_debug_handler.setLevel(logging.DEBUG)
deep_debug_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
deep_debug_handler.setFormatter(deep_debug_formatter)

deep_logger = logging.getLogger('DEEP_DEBUG')
deep_logger.setLevel(logging.DEBUG)
deep_logger.addHandler(deep_debug_handler)
deep_logger.propagate = False  # Don't send to root logger

diag_logger = logging.getLogger('DIAGNOSTIC')
diag_logger.setLevel(logging.DEBUG)
diag_logger.addHandler(deep_debug_handler)
diag_logger.propagate = True  # Also show in console


def load_main_config() -> dict:
    """Loads the main YAML configuration."""
    try:
        with open("reporting/config/portfolio_config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning("portfolio_config.yaml not found. Running with default settings.")
        return {}
    except yaml.YAMLError as e:
        logger.error(f"Error parsing portfolio_config.yaml: {e}")
        return {}


def print_header(title: str):
    """Prints a formatted header."""
    print("\n" + "="*70)
    print(f"--- {title.upper()} ---")
    print("="*70)


def run_full_pipeline(api_key: Optional[str]):
    """Executes the entire analysis pipeline from start to finish."""
    print_header("Executing Full Pipeline")

    # Step 1: Log Extraction
    logger.info("Pipeline Step 1: Running log extraction...")
    print("\n[1/5] Running log extraction...")
    if not run_extraction():
        logger.error("Pipeline stopped: Log extraction failed.")
        return
    print("Log extraction completed successfully.")

    # Step 2: Strategy Instance Detection
    logger.info("Pipeline Step 2: Running strategy instance detection...")
    print("\n[2/5] Running strategy instance detection...")
    try:
        run_instance_detection()
    except Exception as e:
        logger.error(f"Pipeline stopped: Strategy instance detection failed: {e}", exc_info=True)
        return
    print("Strategy instance detection completed successfully.")

    # Step 3: Central Data Fetching (The only online step)
    logger.info("Pipeline Step 3: Running Central Data Fetching...")
    print("\n[3/5] Fetching all historical data...")
    run_all_data_fetching(api_key)
    print("Data fetching completed.")
    
    # Step 4: Spot vs. Bid-Ask Simulation (Offline)
    logger.info("Pipeline Step 4: Running Spot vs. Bid-Ask simulation (Offline)...")
    print("\n[4/5] Running Spot vs. Bid-Ask simulation...")
    try:
        run_spot_vs_bidask_analysis(api_key=None) # Explicitly offline
    except Exception as e:
        logger.error(f"Pipeline stopped: Spot vs. Bid-Ask simulation failed: {e}", exc_info=True)
        return
    print("Spot vs. Bid-Ask simulation completed successfully.")

    # Step 5: Comprehensive Reporting (Offline)
    logger.info("Pipeline Step 5: Generating comprehensive portfolio report (Offline)...")
    print("\n[5/5] Generating comprehensive portfolio report...")
    try:
        orchestrator = PortfolioAnalysisOrchestrator() # Explicitly offline
        result = orchestrator.run_comprehensive_analysis('positions_to_analyze.csv')
        if result.get('status') == 'SUCCESS':
            print("Comprehensive report generated successfully.")
            print(f"Find your report at: {result.get('files_generated', {}).get('html_report')}")
        else:
            print(f"Error during reporting: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Pipeline stopped: Comprehensive reporting failed: {e}", exc_info=True)
        return
        
    print_header("Full Pipeline Completed")



def main_menu():
    """Displays the main interactive menu."""
    config = load_main_config()
    is_cache_only = config.get('api_settings', {}).get('cache_only', False)

    api_key = os.getenv("MORALIS_API_KEY")

    if is_cache_only:
        print("\n" + "!"*70)
        print("!!! CACHE-ONLY MODE IS ACTIVE (via config.yaml) !!!")
        print("!!! No API calls will be made. The program will rely         !!!")
        print("!!! exclusively on data from the /price_cache/ directory.    !!!")
        print("!"*70)
        api_key = None
    elif not api_key:
        logger.error("MORALIS_API_KEY not found in .env file. API calls will fail.")
        print("\nWARNING: MORALIS_API_KEY not found in .env file.")

    # Orchestrator for reporting menu is ALWAYS initialized in offline mode.
    orchestrator = PortfolioAnalysisOrchestrator()

    while True:
        print("\n" + "="*70)
        print("--- MAIN MENU ---")
        print("="*70)
        print("1. Step 1: Process Logs and Extract Positions")
        print("2. Step 2: Detect Strategy Instances")
        print("3. Step 3: Fetch ALL Historical Data (Online Step)")
        print("4. Step 4: Run Base Simulations (Offline)")
        print("5. Step 5: Generate Portfolio Reports (Offline)")
        print("6. Run Full Pipeline (Steps 1 -> 2 -> 3 -> 4 -> 5)")
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
            print_header("Step 4: Spot vs. Bid-Ask Simulation (Offline)")
            # This step runs offline, so no api_key is passed
            run_spot_vs_bidask_analysis(api_key=None)
        elif choice == '5':
            # Orchestrator is already initialized in offline mode
            reporting_menu(orchestrator)
        elif choice == '6':
            run_full_pipeline(api_key)
        elif choice == '7':
            print("Exiting application...")
            break
        else:
            print("Invalid choice, please try again.")

def run_full_pipeline(api_key: Optional[str]):
    """Executes the entire analysis pipeline from start to finish."""
    print_header("Executing Full Pipeline")

    # Step 1 & 2: Data Preparation
    print("\n[1-2/5] Running Log Extraction & Strategy Detection...")
    if not run_extraction(): return
    try:
        run_instance_detection()
    except Exception as e:
        logger.error(f"Pipeline stopped: Strategy instance detection failed: {e}", exc_info=True)
        return
    print("Log Extraction & Strategy Detection completed.")

    # Step 3: Central Data Fetching (The only online step)
    print("\n[3/5] Fetching all historical data...")
    run_all_data_fetching(api_key)
    print("Data fetching completed.")
    
    # Step 4: Spot vs. Bid-Ask Simulation (Offline)
    print("\n[4/5] Running Spot vs. Bid-Ask simulation (Offline)...")
    try:
        run_spot_vs_bidask_analysis(api_key=None) # Explicitly offline
    except Exception as e:
        logger.error(f"Pipeline stopped: Spot vs. Bid-Ask simulation failed: {e}", exc_info=True)
        return
    print("Spot vs. Bid-Ask simulation completed successfully.")

    # Step 5: Comprehensive Reporting (Offline)
    print("\n[5/5] Generating comprehensive portfolio report (Offline)...")
    try:
        orchestrator = PortfolioAnalysisOrchestrator() # Explicitly offline
        result = orchestrator.run_comprehensive_analysis('positions_to_analyze.csv')
        if result.get('status') == 'SUCCESS':
            print("Comprehensive report generated successfully.")
            print(f"Find your report at: {result.get('files_generated', {}).get('html_report')}")
        else:
            print(f"Error during reporting: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Pipeline stopped: Comprehensive reporting failed: {e}", exc_info=True)
        return
        
    print_header("Full Pipeline Completed")

def run_all_data_fetching(api_key: Optional[str]):
    """
    Central data fetching function. Populates cache for all positions and SOL/USDC rates.
    This is the ONLY function that should use the API key for fetching.
    """
    if not api_key:
        print("Error: No API key available. Cannot run data fetching.")
        logger.warning("run_all_data_fetching called without API key. Aborting.")
        return

    print_header("Step 3: Central Data Fetching")
    logger.info("--- Starting Central Data Fetching Step ---")

    # --- Part 1: Fetch per-position price history for simulations ---
    print("\n[Part 1/2] Fetching price history for each position to populate cache...")
    try:
        positions_df = pd.read_csv("positions_to_analyze.csv")
        total_positions = len(positions_df)
        print(f"Found {total_positions} positions to process.")
    except FileNotFoundError:
        print("Error: positions_to_analyze.csv not found. Please run Step 1 first.")
        logger.error("Data fetching failed: positions_to_analyze.csv not found.")
        return

    from reporting.analysis_runner import fetch_price_history
    from reporting.data_loader import _parse_custom_timestamp
    
    # Safety Valve: Ask for confirmation only once, after the 5th position.
    if total_positions > 5:
        try:
            user_input = input(f"\n[SAFETY VALVE] This step will process {total_positions} positions and may use API credits. Continue? (Y/n): ")
            if user_input.lower().strip() == 'n':
                print("Stopping data fetching as requested.")
                logger.warning("User stopped data fetching at safety valve.")
                return # Exit the function entirely
            else:
                print("Continuing with all positions...")
        except KeyboardInterrupt:
            print("\nStopping data fetching as requested.")
            logger.warning("User stopped data fetching via Ctrl+C.")
            return

    for idx, row in enumerate(positions_df.itertuples()):
        position_id = getattr(row, 'position_id', f"index_{row.Index}")
        print(f"Processing cache for position {idx + 1}/{total_positions} ({position_id})...", end='\r')

        try:
            start_dt = _parse_custom_timestamp(str(row.open_timestamp))
            end_dt = _parse_custom_timestamp(str(row.close_timestamp))
            if pd.notna(start_dt) and pd.notna(end_dt) and end_dt > start_dt:
                fetch_price_history(row.pool_address, start_dt, end_dt, api_key)
            else:
                logger.warning(f"Skipping fetch for position {position_id} due to invalid timestamps.")
        except Exception as e:
            logger.error(f"Error fetching data for position {position_id}: {e}")
    print("\nProcessing complete for all positions.                          ") # Whitespace to clear the line

    print("\n[Part 2/2] Fetching SOL/USDC daily rates...")
    # --- Part 2: Fetch SOL/USDC daily rates for reporting ---
    try:
        from reporting.infrastructure_cost_analyzer import InfrastructureCostAnalyzer
        positions_df['open_dt'] = positions_df['open_timestamp'].apply(_parse_custom_timestamp)
        positions_df['close_dt'] = positions_df['close_timestamp'].apply(_parse_custom_timestamp)
        min_date = positions_df['open_dt'].min().strftime('%Y-%m-%d')
        max_date = positions_df['close_dt'].max().strftime('%Y-%m-%d')
        print(f"Fetching SOL/USDC rates for period: {min_date} to {max_date}")

        cost_analyzer = InfrastructureCostAnalyzer(api_key=api_key)
        sol_rates = cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        
        successful = sum(1 for rate in sol_rates.values() if rate is not None)
        print(f"Fetched/updated {successful} daily SOL/USDC rates.")
    except Exception as e:
        logger.error(f"Failed to fetch SOL/USDC rates: {e}")
        print(f"Error fetching SOL/USDC rates: {e}")
        
    print("\nCentral Data Fetching complete. Cache is populated.")
    logger.info("--- Central Data Fetching Step Finished ---")

def reporting_menu(orchestrator: PortfolioAnalysisOrchestrator):
    """Displays the submenu for reporting and analysis."""
    while True:
        print_header("Reporting and Analysis Menu")
        print("1. Generate Comprehensive Report (Portfolio + Correlation + Weekend + HTML)")
        print("2. Generate Quick Report (Text-only, no charts)")
        print("3. Analyze Specific Period (Not Implemented)")
        print("4. Back to Main Menu")
        
        choice = input("Select an option (1-4): ")
        
        if choice == '1':
            print_header("Generating Comprehensive Report")
            result = orchestrator.run_comprehensive_analysis('positions_to_analyze.csv')
            if result.get('status') == 'SUCCESS':
                print(f"Report generated. Check file: {result.get('files_generated', {}).get('html_report')}")
            else:
                print(f"Error: {result.get('error')}")
        elif choice == '2':
            print_header("Generating Quick Report")
            result = orchestrator.run_quick_analysis('positions_to_analyze.csv')
            if result.get('status') == 'SUCCESS':
                print("Text reports generated:")
                for report_type, path in result.get('files_generated', {}).items():
                    print(f" - {report_type}: {path}")
            else:
                print(f"Error: {result.get('error')}")
        elif choice == '3':
            print_header("Analyze Specific Period")
            print("This feature is not yet implemented.")
        elif choice == '4':
            break
        else:
            print("Invalid choice, please try again.")

def fetch_sol_usdc_rates_menu(api_key: Optional[str]):
    """Menu for fetching SOL/USDC historical rates."""
    if not api_key:
        print("Error: No API key available. Cannot fetch SOL/USDC rates in cache-only mode.")
        print("Historical rates are needed for portfolio analysis.")
        return
    
    try:
        from reporting.infrastructure_cost_analyzer import InfrastructureCostAnalyzer
        
        # Get date range from positions file
        try:
            import pandas as pd
            positions_df = pd.read_csv("positions_to_analyze.csv")
            
            if positions_df.empty:
                print("No positions found in positions_to_analyze.csv")
                return
            
            # Parse dates and find range
            from reporting.data_loader import _parse_custom_timestamp
            positions_df['open_dt'] = positions_df['open_timestamp'].apply(_parse_custom_timestamp)
            positions_df['close_dt'] = positions_df['close_timestamp'].apply(_parse_custom_timestamp)
            
            min_date = positions_df['open_dt'].min().strftime('%Y-%m-%d')
            max_date = positions_df['close_dt'].max().strftime('%Y-%m-%d')
            
            print(f"Detected date range from positions: {min_date} to {max_date}")
            
        except Exception as e:
            logger.warning(f"Could not detect date range from positions: {e}")
            min_date = "2025-05-01"
            max_date = "2025-07-31"
            print(f"Using default date range: {min_date} to {max_date}")
        
        # Initialize cost analyzer and fetch rates
        print("Fetching SOL/USDC historical rates...")
        cost_analyzer = InfrastructureCostAnalyzer(api_key=api_key)
        
        sol_rates = cost_analyzer.get_sol_usdc_rates(min_date, max_date)
        
        # Count successful vs failed fetches
        successful = sum(1 for rate in sol_rates.values() if rate is not None)
        total = len(sol_rates)
        failed = total - successful
        
        print(f"\nSOL/USDC Rate Fetching Results:")
        print(f"  Total days: {total}")
        print(f"  Successfully fetched: {successful}")
        print(f"  Failed/cached: {failed}")
        
        if failed > 0:
            print(f"  Note: {failed} days may use cached or fallback values")
        
        print(f"\nRates saved to: price_cache/sol_usdc_daily.json")
        print("These rates will be used for portfolio analysis and cost calculations.")
        
    except Exception as e:
        logger.error(f"Failed to fetch SOL/USDC rates: {e}")
        print(f"Error fetching SOL/USDC rates: {e}")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main menu: {e}", exc_info=True)
        print(f"\nA critical error occurred: {e}")