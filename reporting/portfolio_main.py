"""
Portfolio Analytics Main CLI

Command-Line Interface and interactive menu for orchestrating the complete 
portfolio analysis workflow.
"""

import logging
import os
import sys
import argparse
from typing import Dict, Any

# AIDEV-NOTE-CLAUDE: This structure allows running the script from the project root
# It finds the 'reporting' directory and adds it to the path.
sys.path.append(os.getcwd())
from orchestrator import PortfolioAnalysisOrchestrator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('reporting/output/portfolio_analysis.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


def print_results(result: Dict[str, Any]):
    """Prints a formatted summary of the analysis results."""
    if not isinstance(result, dict) or result.get('status') != 'SUCCESS':
        error_msg = result.get('error', 'Unknown error') if isinstance(result, dict) else str(result)
        print(f"\nANALYSIS FAILED: {error_msg}")
        return

    print("\n" + "="*50)
    print("PORTFOLIO ANALYSIS COMPLETED")
    print("="*50)

    # Print key portfolio metrics if available
    if 'sol_denomination' in result:
        sol = result['sol_denomination']
        print(f"Total PnL: {sol.get('total_pnl_sol', 0):+.3f} SOL")
        print(f"Sharpe Ratio: {sol.get('sharpe_ratio', 0):.2f}")
        print(f"Win Rate: {sol.get('win_rate', 0)*100:.1f}%")

    # Handle comprehensive results
    if 'portfolio_analysis' in result:
        if 'sol_denomination' in result['portfolio_analysis']:
            sol = result['portfolio_analysis']['sol_denomination']
            print(f"Total PnL: {sol.get('total_pnl_sol', 0):+.3f} SOL")
            print(f"Sharpe Ratio: {sol.get('sharpe_ratio', 0):.2f}")
        if 'correlation_analysis' in result and 'error' not in result['correlation_analysis']:
            corr = result['correlation_analysis']['correlation_metrics']
            print(f"Market Correlation: {corr.get('pearson_correlation', 0):.3f}")
        if 'weekend_analysis' in result and 'error' not in result['weekend_analysis']:
            rec = result['weekend_analysis']['recommendations']
            print(f"Weekend Recommendation: {rec.get('primary_recommendation', 'N/A')}")
    
    # Print generated files
    if 'files_generated' in result:
        print("\nFiles Generated:")
        for key, value in result['files_generated'].items():
            if isinstance(value, str):
                print(f"  - {key.replace('_', ' ').title()}: {value}")
            elif isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    print(f"  - {sub_key.replace('_', ' ').title()}: {sub_value}")
    
    print(f"\nExecution Time: {result.get('execution_time_seconds', 0):.1f} seconds")


def interactive_menu(orchestrator: PortfolioAnalysisOrchestrator, file: str):
    """Displays an interactive menu for the user to choose an analysis."""
    while True:
        print("\n--- Portfolio Analytics Interactive Menu ---")
        print("1. Run Comprehensive Analysis (Portfolio + Correlation + Weekend + HTML Report)")
        print("2. Run Quick Portfolio Analysis (Reports only, no charts)")
        print("3. Analyze Specific Period")
        print("4. Exit")
        
        choice = input("Enter your choice (1-4): ")

        if choice == '1':
            result = orchestrator.run_comprehensive_analysis(file)
            print_results(result)
        elif choice == '2':
            result = orchestrator.run_quick_analysis(file)
            print_results(result)
        elif choice == '3':
            start_date = input("Enter start date (YYYY-MM-DD): ")
            end_date = input("Enter end date (YYYY-MM-DD): ")
            result = orchestrator.analyze_specific_period(start_date, end_date, file)
            print_results(result)
        elif choice == '4':
            print("Exiting...")
            break
        else:
            print("Invalid choice. Please try again.")

def main():
    """Main entry point for portfolio analysis."""
    parser = argparse.ArgumentParser(description='Portfolio Analytics for LP Strategy Optimization')
    parser.add_argument('--file', '-f', default='positions_to_analyze.csv', help='Path to positions CSV file')
    parser.add_argument('--config', '-c', default='reporting/config/portfolio_config.yaml', help='Path to configuration file')
    parser.add_argument('-m', '--mode', choices=['comprehensive', 'quick', 'period'], help='Analysis mode to run directly')
    parser.add_argument('--start-date', help='Start date for period analysis (YYYY-MM-DD)')
    parser.add_argument('--end-date', help='End date for period analysis (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    try:
        orchestrator = PortfolioAnalysisOrchestrator(args.config)
        
        if args.mode:
            result = None
            if args.mode == 'comprehensive':
                result = orchestrator.run_comprehensive_analysis(args.file)
            elif args.mode == 'quick':
                result = orchestrator.run_quick_analysis(args.file)
            elif args.mode == 'period':
                if not (args.start_date and args.end_date):
                    print("Error: --start-date and --end-date are required for period mode.")
                    return 1
                result = orchestrator.analyze_specific_period(args.start_date, args.end_date, args.file)
            
            if result:
                print_results(result)
        else:
            # No mode specified, launch interactive menu
            interactive_menu(orchestrator, args.file)
            
        return 0

    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        print("\nAnalysis interrupted by user")
        return 1
    except Exception as e:
        logger.error(f"An unexpected error occurred in main: {e}", exc_info=True)
        print(f"\nAn unexpected error occurred: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())