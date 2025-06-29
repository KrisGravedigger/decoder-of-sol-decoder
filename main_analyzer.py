import os
import csv
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv
import shutil
from typing import Dict, List, Optional, Any

# Imports from our modules
import extraction.log_extractor as log_extractor
from strategy_analyzer import StrategyAnalyzer

# --- Configuration ---
LOG_DIR = "input"
POSITIONS_CSV = "positions_to_analyze.csv"
FINAL_REPORT_CSV = "final_analysis_report.csv"
DETAILED_REPORTS_DIR = "detailed_reports"
PRICE_CACHE_DIR = "price_cache"

# Load environment variables from .env file
load_dotenv()
MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")

# Logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('MainAnalyzer')

def parse_timestamp_str(timestamp_str: str) -> Optional[datetime]:
    """
    Parse timestamp string to datetime object.
    
    Args:
        timestamp_str: Timestamp string in format MM/DD-HH:MM:SS
        
    Returns:
        Parsed datetime object or None if parsing fails
    """
    if not isinstance(timestamp_str, str): 
        return None
    try:
        if "-24:" in timestamp_str:
            logger.warning(f"Detected invalid hour '24' in '{timestamp_str}'. Changing to '23:59:59'.")
            date_part, time_part = timestamp_str.split('-')
            h, m, s = time_part.split(':')
            if h == '24': 
                timestamp_str = f"{date_part}-23:59:59"
        
        return datetime.strptime(f"2025/{timestamp_str}", "%Y/%m/%d-%H:%M:%S")
    except (ValueError, TypeError) as e:
        logger.error(f"Error parsing date '{timestamp_str}': {e}")
        return None

def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    """
    Fetch price history for a pool from Moralis API.
    
    Version 6: Improved timeframe selection and robust API response parsing.
    
    Args:
        pool_address: Pool address to fetch prices for
        start_dt: Start datetime
        end_dt: End datetime
        
    Returns:
        List of price data dictionaries with 'timestamp' and 'close' keys
    """
    os.makedirs(PRICE_CACHE_DIR, exist_ok=True)
    
    start_unix = int(start_dt.timestamp())
    end_unix = int(end_dt.timestamp())
    cache_file = os.path.join(PRICE_CACHE_DIR, f"{pool_address}_{start_unix}_{end_unix}.json")

    # Check cache first
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Loading prices from cache for {pool_address}")
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Cache file error, fetching data from API.")

    # Calculate appropriate timeframe based on duration
    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    
    # --- KEY CHANGE: Improved timeframe selection ---
    if duration_hours <= 4: 
        timeframe = "10min"  # Instead of 15min
    elif duration_hours <= 12: 
        timeframe = "30min"
    elif duration_hours <= 72: 
        timeframe = "1h"
    else: 
        timeframe = "4h"
    # ------------------------------------------------

    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
    headers = {"accept": "application/json", "X-API-Key": MORALIS_API_KEY}
    
    start_date_str = start_dt.strftime('%Y-%m-%d')
    end_date_str = end_dt.strftime('%Y-%m-%d')

    # Extend end date if needed
    if start_date_str >= end_date_str:
        end_date_extended = end_dt + timedelta(days=1)
        end_date_str = end_date_extended.strftime('%Y-%m-%d')
        logger.debug(f"Extended 'toDate' to: {end_date_str}")
    
    params = {
        "timeframe": timeframe, 
        "fromDate": start_date_str, 
        "toDate": end_date_str, 
        "currency": "usd"
    }
    
    try:
        logger.info(f"Fetching prices for {pool_address} (API params: {params})...")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        processed_data = []
        api_result = data.get('result', []) if isinstance(data, dict) else data
        
        # --- CHANGE: Robust API response parsing ---
        if isinstance(api_result, list):
            for d in api_result:
                if isinstance(d, dict) and 'close' in d:
                    # Check for 'time' or 'timestamp' key
                    ts_val = d.get('time') or d.get('timestamp')
                    if ts_val:
                        # 'time' is in milliseconds, 'timestamp' might be ISO 8601
                        ts = 0
                        if isinstance(ts_val, (int, float, str)) and str(ts_val).isdigit():
                            ts = int(ts_val) // 1000
                        elif isinstance(ts_val, str):
                            try:
                                ts_dt = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                ts = int(ts_dt.timestamp())
                            except ValueError:
                                logger.warning(f"Failed to parse date string: {ts_val}")
                                continue
                        else:
                            continue

                        if start_unix <= ts <= end_unix:
                            processed_data.append({'timestamp': ts, 'close': float(d['close'])})
                    else:
                        logger.warning(f"Received candle without 'time' or 'timestamp' key: {d}")
                else:
                    logger.warning(f"Received invalid candle format from API: {d}")
            processed_data.sort(key=lambda x: x['timestamp'])
        # -------------------------------------------

        # Cache the results
        with open(cache_file, 'w') as f: 
            json.dump(processed_data, f)
            
        return processed_data
        
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} for {pool_address}: {e.response.text}")
        return []
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error for {pool_address}: {e}")
        return []

def generate_text_report(position_data: Dict, simulation_results: Dict) -> str:
    """
    Generate a detailed text report for a position analysis.
    
    Args:
        position_data: Position data dictionary
        simulation_results: Strategy simulation results
        
    Returns:
        Formatted text report as string
    """
    report = []
    report.append("="*60)
    report.append(f"POSITION ANALYSIS: {position_data['token_pair']}")
    report.append(f"Pool: {position_data['pool_address']}")
    report.append(f"Period: {position_data['open_timestamp']} -> {position_data['close_timestamp']}")
    report.append("="*60)
    
    report.append(f"\n--- INPUT DATA ---")
    initial_investment = position_data.get('initial_investment_sol', 0)
    report.append(f"Investment: {initial_investment:.4f} SOL")
    report.append(f"Actual strategy: {position_data.get('actual_strategy_from_log', 'N/A')}")
    final_pnl_log = position_data.get('final_pnl_sol_from_log')
    report.append(f"Actual PnL (from log): {final_pnl_log if final_pnl_log is not None else 'N/A'}")

    report.append(f"\n--- SIMULATION RESULTS (PnL in SOL) ---")
    
    if not simulation_results or 'error' in simulation_results:
        report.append("Error during simulation or no results available.")
    else:
        sorted_results = sorted(simulation_results.items(), 
                              key=lambda item: item[1].get('pnl_sol', -9e9), 
                              reverse=True)
        
        for name, res in sorted_results:
            pnl = res.get('pnl_sol', 0)
            fees = res.get('pnl_from_fees', 0)
            il = res.get('pnl_from_il', 0)
            report.append(f"\n- Strategy: {name}")
            report.append(f"  > Total PnL: {pnl:+.5f} SOL ({res.get('return_pct', 0):.2f}%)")
            report.append(f"    (Est. fees: {fees:+.5f} | Est. value change/IL: {il:+.5f})")

        report.append("\n" + "="*60)
        report.append(f"BEST STRATEGY: {sorted_results[0][0]}")
        report.append("="*60)
    
    return "\n".join(report)

def main():
    """Main analysis function that coordinates the entire process."""
    if not MORALIS_API_KEY:
        logger.error("Missing MORALIS_API_KEY in .env file! Aborting analysis.")
        return

    # Clean old cache
    if os.path.exists(PRICE_CACHE_DIR):
        logger.info(f"Cleaning old cache from folder: {PRICE_CACHE_DIR}")
        shutil.rmtree(PRICE_CACHE_DIR)
    
    logger.info("Step 1: Running log extractor...")
    if not log_extractor.run_extraction(log_dir=LOG_DIR, output_csv=POSITIONS_CSV):
        logger.error("Log extraction failed. Analysis aborted.")
        return
        
    logger.info(f"\nStep 2: Loading positions from file {POSITIONS_CSV}")
    try:
        positions_df = pd.read_csv(POSITIONS_CSV)
        logger.info(f"Loaded {len(positions_df)} positions for analysis.")
    except (FileNotFoundError, pd.errors.EmptyDataError):
        logger.error(f"File {POSITIONS_CSV} not found or empty. Aborted.")
        return

    logger.info("\nStep 3: Starting analysis and simulation...")
    os.makedirs(DETAILED_REPORTS_DIR, exist_ok=True)
    all_final_results = []
    
    # Extract step size and bin step from position data
    step_size = "UNKNOWN"
    bin_step = 100  # Default fallback

    # Try to extract step size from actual_strategy_from_log
    for index, position in positions_df.iterrows():
        strategy_str = position.get('actual_strategy_from_log', '')
        if any(size in strategy_str for size in ['WIDE', 'MEDIUM', 'NARROW', 'SIXTYNINE']):
            # Extract step size from first position and use for all (assumes same pool type)
            import re
            step_match = re.search(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', strategy_str)
            if step_match:
                step_size = step_match.group(1)
            break

    logger.info(f"Using strategy analyzer with step_size={step_size}, bin_step={bin_step}")
    analyzer = StrategyAnalyzer(bin_step=bin_step, step_size=step_size) 

    for index, position in positions_df.iterrows():
        logger.info(f"\n--- Analyzing position {index+1}/{len(positions_df)}: {position['token_pair']} ---")
        position_dict = position.to_dict()

        start_dt = parse_timestamp_str(position['open_timestamp'])
        end_dt = parse_timestamp_str(position['close_timestamp'])

        if not start_dt or not end_dt or start_dt >= end_dt:
            logger.warning(f"Skipped position {position['position_id']} due to invalid dates.")
            continue
            
        price_history = fetch_price_history(position['pool_address'], start_dt, end_dt)
        time.sleep(0.6)  # Rate limiting
        
        if not price_history:
            logger.warning(f"No price history for {position['token_pair']}. Skipping simulation.")
            continue
            
        simulation_results = analyzer.run_all_simulations(position_dict, price_history)
        
        # Generate detailed text report
        text_report = generate_text_report(position_dict, simulation_results)
        report_filename = os.path.join(
            DETAILED_REPORTS_DIR, 
            f"{position['token_pair'].replace('/', '_')}_{position['open_timestamp'].replace('/','-').replace(':','-')}.txt"
        )
        with open(report_filename, 'w', encoding='utf-8') as f: 
            f.write(text_report)
        logger.info(f"Saved detailed report: {report_filename}")
        
        # Determine best strategy
        best_strategy_name = "error"
        best_pnl = None
        if simulation_results and 'error' not in simulation_results:
            best_strategy_name = max(simulation_results, 
                                   key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            best_pnl = simulation_results[best_strategy_name].get('pnl_sol')

        # Prepare final result row
        final_row = { 
            **position_dict, 
            "best_sim_strategy": best_strategy_name, 
            "best_sim_pnl": best_pnl 
        }
        
        # Add individual strategy results
        if simulation_results and 'error' not in simulation_results:
            for name, res in simulation_results.items():
                column_name = f"pnl_{name.replace(' ','_').lower()}"
                final_row[column_name] = res.get('pnl_sol')
        
        all_final_results.append(final_row)

    logger.info(f"\nStep 4: Saving final comprehensive report...")
    if all_final_results:
        final_df = pd.DataFrame(all_final_results)
        cols = list(final_df.columns)
        preferred_order = [
            "position_id", "token_pair", "pool_address", "open_timestamp", "close_timestamp", 
            "initial_investment_sol", "final_pnl_sol_from_log", "best_sim_strategy", "best_sim_pnl"
        ]
        ordered_cols = preferred_order + [c for c in cols if c not in preferred_order]
        final_df = final_df[ordered_cols]
        final_df.to_csv(FINAL_REPORT_CSV, index=False, encoding='utf-8')
        logger.info(f"Saved final report to: {FINAL_REPORT_CSV}")
    else:
        logger.warning("No final results generated.")
        
    logger.info("\nAnalysis completed successfully!")

if __name__ == "__main__":
    main()