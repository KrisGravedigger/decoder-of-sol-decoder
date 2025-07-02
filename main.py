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

    # Step 3: Spot vs. Bid-Ask Simulation
    logger.info("Pipeline Step 3: Running Spot vs. Bid-Ask simulation...")
    print("\n[3/4] Running Spot vs. Bid-Ask simulation...")
    try:
        run_spot_vs_bidask_analysis(api_key)
        print("Spot vs. Bid-Ask simulation completed successfully.")
    except Exception as e:
        logger.error(f"Pipeline stopped: Spot vs. Bid-Ask simulation failed: {e}", exc_info=True)
        print(f"Error during simulation: {e}. Aborting pipeline.")
        return

    # Step 4: Comprehensive Reporting
    logger.info("Pipeline Step 4: Generating comprehensive portfolio report...")
    print("\n[4/4] Generating comprehensive portfolio report...")
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
        print_header("Main Menu - LP Strategy Analyzer")
        print("1. Step 1: Process Logs and Extract Positions")
        print("2. Step 2: Detect Strategy Instances (generates strategy_instances.csv)")
        print("3. Step 3: Run Base Simulations (Spot vs. Bid-Ask)")
        print("4. Step 4: Generate Portfolio Reports & Analysis (Menu)")
        print("5. Run Full Pipeline (Step 1 -> 2 -> 3 -> 4)")
        print("6. Exit")
        
        choice = input("Select an option (1-6): ")

        if choice == '1':
            print_header("Step 1: Log Processing")
            run_extraction()
        elif choice == '2':
            print_header("Step 2: Strategy Instance Detection")
            run_instance_detection()
        elif choice == '3':
            print_header("Step 3: Spot vs. Bid-Ask Simulation")
            run_spot_vs_bidask_analysis(api_key)
        elif choice == '4':
            reporting_menu(orchestrator)
        elif choice == '5':
            run_full_pipeline(api_key)
        elif choice == '6':
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

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
    except Exception as e:
        logger.error(f"An unexpected error occurred in the main menu: {e}", exc_info=True)
        print(f"\nA critical error occurred: {e}")