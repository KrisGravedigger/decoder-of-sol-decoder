import logging
import os
import sys
from dotenv import load_dotenv
import yaml
from typing import Optional

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
    print("\n[1/4] Running log extraction...")
    if not run_extraction():
        logger.error("Pipeline stopped: Log extraction failed.")
        print("Error during log extraction. Aborting pipeline.")
        return
    print("Log extraction completed successfully.")

    # Step 2: Strategy Instance Detection
    logger.info("Pipeline Step 2: Running strategy instance detection...")
    print("\n[2/4] Running strategy instance detection...")
    try:
        run_instance_detection()
        print("Strategy instance detection completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline stopped: Strategy instance detection failed: {e}", exc_info=True)
        print(f"Error during instance detection: {e}. Aborting pipeline.")
        return

    # Step 3: SOL/USDC Rates (optional - skip if cache exists)
    logger.info("Pipeline Step 3: Checking SOL/USDC rates...")
    print("\n[3/5] Checking SOL/USDC historical rates...")
    # Note: This step is optional and will be skipped if sufficient cache exists
    
    # Step 4: Spot vs. Bid-Ask Simulation  
    logger.info("Pipeline Step 4: Running Spot vs. Bid-Ask simulation...")
    print("\n[4/5] Running Spot vs. Bid-Ask simulation...")
    try:
        run_spot_vs_bidask_analysis(api_key)
        print("Spot vs. Bid-Ask simulation completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline stopped: Spot vs. Bid-Ask simulation failed: {e}", exc_info=True)
        print(f"Error during simulation: {e}. Aborting pipeline.")
        return

    # Step 5: Comprehensive Reporting
    logger.info("Pipeline Step 5: Generating comprehensive portfolio report...")
    print("\n[5/5] Generating comprehensive portfolio report...")
    try:
        orchestrator = PortfolioAnalysisOrchestrator(api_key=api_key)
        result = orchestrator.run_comprehensive_analysis('positions_to_analyze.csv')
        if result.get('status') == 'SUCCESS':
            print("Comprehensive report generated successfully.")
            print(f"Find your report at: {result.get('files_generated', {}).get('html_report')}")
        else:
            print(f"Error during reporting: {result.get('error', 'Unknown error')}")
    except Exception as e:
        logger.error(f"Pipeline stopped: Comprehensive reporting failed: {e}", exc_info=True)
        print(f"Error during reporting: {e}. Aborting pipeline.")
        return
        
    print_header("Full Pipeline Completed")


def main_menu():
    """Displays the main interactive menu."""
    config = load_main_config()
    is_cache_only = config.get('api_settings', {}).get('cache_only', False)

    api_key = os.getenv("MORALIS_API_KEY")

    if is_cache_only:
        print("\n" + "!"*70)
        print("!!! CACHE-ONLY MODE IS ACTIVE !!!")
        print("!!! No API calls will be made. The program will rely         !!!")
        print("!!! exclusively on data from the /price_cache/ directory.    !!!")
        print("!"*70)
        api_key = None
    elif not api_key:
        logger.error("MORALIS_API_KEY not found in .env file. API calls will fail.")
        print("\nWARNING: MORALIS_API_KEY not found in .env file.")

    orchestrator = PortfolioAnalysisOrchestrator(api_key=api_key)

    while True:
        print("\n" + "="*70)
        print("--- MAIN MENU ---")
        print("="*70)
        print("1. Step 1: Process Logs and Extract Positions")
        print("2. Step 2: Detect Strategy Instances (generates strategy_instances.csv)")
        print("3. Step 3: Fetch SOL/USDC Historical Rates (for portfolio analysis)")
        print("4. Step 4: Run Base Simulations (Spot vs. Bid-Ask)")
        print("5. Step 5: Generate Portfolio Reports & Analysis (Menu)")
        print("6. Run Full Pipeline (Step 1 -> 2 -> 3 -> 4 -> 5)")
        print("7. Exit")
        
        choice = input("Select an option (1-7): ")

        if choice == '1':
            print_header("Step 1: Log Processing")
            run_extraction()
        elif choice == '2':
            print_header("Step 2: Strategy Instance Detection")
            run_instance_detection()
        elif choice == '3':
            print_header("Step 3: Fetch SOL/USDC Historical Rates")
            fetch_sol_usdc_rates_menu(api_key)
        elif choice == '4':
            print_header("Step 4: Spot vs. Bid-Ask Simulation")
            run_spot_vs_bidask_analysis(api_key)
        elif choice == '5':
            reporting_menu(orchestrator)
        elif choice == '6':
            run_full_pipeline(api_key)
        elif choice == '7':
            print("Exiting application...")
            break
        else:
            print("Invalid choice, please try again.")

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