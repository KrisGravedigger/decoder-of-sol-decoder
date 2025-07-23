import logging
import os
from typing import Optional, Literal
import pandas as pd

from utils.common import print_header, load_main_config
from reporting.analysis_runner import AnalysisRunner
from reporting.data_loader import load_and_prepare_positions
from reporting.infrastructure_cost_analyzer import InfrastructureCostAnalyzer

logger = logging.getLogger(__name__)


def run_all_data_fetching(api_key: Optional[str], refetch_mode: Literal['none', 'all', 'sol_only'] = 'none'):
    """
    Central data fetching function with different cache-handling modes.
    This is the ONLY function that should use the API key for the main report data.
    """
    if not api_key:
        print("\n[ERROR] No API key available. Cannot run data fetching.")
        logger.warning("run_all_data_fetching called without API key. Aborting.")
        return

    mode_description = {
        'none': "Standard Fetch (new data only)",
        'all': "FORCE REFETCH ALL (positions & SOL/USDC)",
        'sol_only': "FORCE REFETCH SOL/USDC only"
    }
    print_header(f"Step 3: Central Data Fetching ({mode_description[refetch_mode]})")
    logger.info(f"--- Starting Central Data Fetching (mode: {refetch_mode}) ---")

    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        total_positions = len(positions_df)
        print(f"Found {total_positions} valid, closed positions to process.")
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
        logger.error("Data fetching failed: positions_to_analyze.csv not found.")
        return

    # --- Safety Valve ---
    user_input = input(f"\n[SAFETY VALVE] This step will connect to the API. Mode: '{mode_description[refetch_mode]}'. This may use API credits. Continue? (Y/n): ")
    if user_input.lower().strip() not in ('y', ''):
        print("Data fetching cancelled by user.")
        logger.warning(f"User stopped data fetching at safety valve (mode: {refetch_mode}).")
        return
        
    # --- Part 1: Fetch per-position price history for simulations ---
    if refetch_mode in ['none', 'all']:
        print(f"\n[Part 1/2] Populating cache for position simulations...")
        force_position_refetch = (refetch_mode == 'all')
        
        online_runner = AnalysisRunner(api_key=api_key, force_refetch=force_position_refetch)
        
        for idx, row in positions_df.iterrows():
            progress_idx = positions_df.index.get_loc(idx) + 1
            position_id = row.get('position_id', f"index_{idx}")
            print(f"  Processing cache for position {progress_idx}/{total_positions}...", end='\r')

            try:
                online_runner.analyze_single_position(row.to_dict())
            except Exception as e:
                logger.error(f"Error populating cache for position {position_id}: {e}")
        print("\n  Position cache processing complete.                            ")
    else:
        print("\n[Part 1/2] Skipping position simulation cache (mode is 'sol_only').")

    # --- Part 2: Fetch SOL/USDC daily rates for reporting ---
    print("\n[Part 2/2] Populating cache for SOL/USDC daily rates...")
    try:
        min_date = positions_df['open_timestamp'].min()
        max_date = positions_df['close_timestamp'].max()

        if pd.notna(min_date) and pd.notna(max_date):
            config = load_main_config()
            buffer_days = config.get('market_analysis', {}).get('ema_period', 50)
            fetch_start_dt = min_date - pd.Timedelta(days=buffer_days)
            
            force_sol_refetch = (refetch_mode in ['all', 'sol_only'])

            print(f"  Fetching SOL/USDC rates for period: {fetch_start_dt.date()} to {max_date.date()}")
            cost_analyzer = InfrastructureCostAnalyzer(api_key=api_key)
            cost_analyzer.get_sol_usdc_rates(
                fetch_start_dt.strftime('%Y-%m-%d'), 
                max_date.strftime('%Y-%m-%d'),
                force_refetch=force_sol_refetch
            )
            print("  SOL/USDC rates cache updated.")
        else:
            print("[WARNING] Could not determine date range from positions. Skipping SOL/USDC rate fetching.")

    except Exception as e:
        logger.error(f"Failed to fetch SOL/USDC rates: {e}", exc_info=True)
        print(f"[ERROR] An error occurred while fetching SOL/USDC rates: {e}")

    print("\nCentral Data Fetching complete. Cache is populated.")
    logger.info("--- Central Data Fetching Finished ---")


def data_fetching_menu(api_key: Optional[str]):
    """Displays the sub-menu for data fetching options."""
    while True:
        print("\n" + "-"*70)
        print("--- Data Fetching Options (Step 3) ---")
        print("This step connects to the API to populate the local price cache.")
        print("-"*70)
        print("1. Fetch new data only (Standard)")
        print("2. Force refetch ALL placeholders (Fixes all gaps, uses more API credits)")
        print("3. Force refetch SOL-USDC placeholders only (Fixes market chart gaps)")
        print("4. Back to Main Menu")

        choice = input("Select an option (1-4): ")

        if choice == '1':
            run_all_data_fetching(api_key, refetch_mode='none')
            break
        elif choice == '2':
            run_all_data_fetching(api_key, refetch_mode='all')
            break
        elif choice == '3':
            run_all_data_fetching(api_key, refetch_mode='sol_only')
            break
        elif choice == '4':
            break
        else:
            print("Invalid choice, please try again.")