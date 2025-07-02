import os
import csv
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
import logging
import shutil
from typing import Dict, List, Optional, Any
import sys

# AIDEV-NOTE-CLAUDE: Ensure correct path for sibling imports
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)

from simulations.spot_vs_bidask_simulator import SpotVsBidAskSimulator
from .data_loader import _parse_custom_timestamp

# --- Configuration ---
POSITIONS_CSV = "positions_to_analyze.csv"
FINAL_REPORT_CSV = "final_analysis_report.csv"
DETAILED_REPORTS_DIR = "detailed_reports"
PRICE_CACHE_DIR = "price_cache"

logger = logging.getLogger('AnalysisRunner')

# AIDEV-NOTE-CLAUDE: API key is now passed as an argument for reliability.
def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime, api_key: Optional[str]) -> List[Dict]:
    """Fetch price history for a pool from Moralis API."""
    os.makedirs(PRICE_CACHE_DIR, exist_ok=True)
    
    start_unix = int(start_dt.timestamp())
    end_unix = int(end_dt.timestamp())
    cache_file = os.path.join(PRICE_CACHE_DIR, f"{pool_address}_{start_unix}_{end_unix}.json")

    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                logger.info(f"Loading prices from cache for {pool_address}")
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            logger.warning("Cache file error, attempting to fetch from API.")

    if not api_key:
        logger.warning(f"Cache-only mode: Price data for {pool_address} not found in cache. Skipping API call.")
        return []

    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    
    if duration_hours <= 4: timeframe = "10min"
    elif duration_hours <= 12: timeframe = "30min"
    elif duration_hours <= 72: timeframe = "1h"
    else: timeframe = "4h"

    url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
    headers = {"accept": "application/json", "X-API-Key": api_key}
    
    start_date_str = start_dt.strftime('%Y-%m-%d')
    end_date_str = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
    
    params = {"timeframe": timeframe, "fromDate": start_date_str, "toDate": end_date_str, "currency": "usd"}
    
    try:
        logger.info(f"Fetching prices for {pool_address} (API params: {params})...")
        response = requests.get(url, headers=headers, params=params, timeout=20)
        response.raise_for_status()
        data = response.json()
        
        processed_data = []
        api_result = data.get('result', []) if isinstance(data, dict) else data
        
        if isinstance(api_result, list):
            for d in api_result:
                if isinstance(d, dict) and 'close' in d:
                    ts_val = d.get('time') or d.get('timestamp')
                    if ts_val:
                        ts = 0
                        if isinstance(ts_val, (int, float, str)) and str(ts_val).isdigit():
                            ts = int(ts_val) // 1000
                        elif isinstance(ts_val, str):
                            try:
                                ts_dt = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                ts = int(ts_dt.timestamp())
                            except ValueError: continue
                        else: continue

                        if start_unix <= ts <= end_unix:
                            processed_data.append({'timestamp': ts, 'close': float(d['close'])})
            processed_data.sort(key=lambda x: x['timestamp'])

        with open(cache_file, 'w') as f: 
            json.dump(processed_data, f)
            
        return processed_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching prices for {pool_address}: {e}")
        return []

def generate_text_report(position_data: Dict, simulation_results: Dict) -> str:
    """Generate a detailed text report for a position analysis."""
    report = []
    report.append("="*60)
    report.append(f"POSITION ANALYSIS: {position_data['token_pair']}")
    report.append(f"Pool: {position_data['pool_address']}")
    report.append(f"Period: {position_data['open_timestamp']} -> {position_data['close_timestamp']}")
    report.append("="*60)
    report.append(f"\n--- INPUT DATA ---")
    report.append(f"Investment: {position_data.get('initial_investment_sol', 0):.4f} SOL")
    report.append(f"Actual strategy: {position_data.get('actual_strategy_from_log', 'N/A')}")
    report.append(f"Actual PnL (from log): {position_data.get('final_pnl_sol_from_log', 'N/A')}")
    report.append(f"\n--- SIMULATION RESULTS (PnL in SOL) ---")
    
    if not simulation_results or 'error' in simulation_results:
        report.append("Error during simulation or no results available.")
    else:
        sorted_results = sorted(simulation_results.items(), key=lambda item: item[1].get('pnl_sol', -9e9), reverse=True)
        for name, res in sorted_results:
            report.append(f"\n- Strategy: {name}")
            report.append(f"  > Total PnL: {res.get('pnl_sol', 0):+.5f} SOL ({res.get('return_pct', 0):.2f}%)")
            report.append(f"    (Est. fees: {res.get('pnl_from_fees', 0):+.5f} | Est. value change/IL: {res.get('pnl_from_il', 0):+.5f})")
        report.append("\n" + "="*60)
        report.append(f"BEST STRATEGY: {sorted_results[0][0]}")
        report.append("="*60)
    return "\n".join(report)

def run_spot_vs_bidask_analysis(api_key: Optional[str]):
    """Main analysis function that coordinates the Spot vs. Bid-Ask simulation."""
    if not api_key:
        logger.warning("No API key provided. Running in cache-only mode for Spot vs Bid-Ask analysis.")

    if os.path.exists(PRICE_CACHE_DIR) and not os.listdir(PRICE_CACHE_DIR):
        logger.info(f"Cleaning empty price cache folder: {PRICE_CACHE_DIR}")
        shutil.rmtree(PRICE_CACHE_DIR)
    
    logger.info(f"Loading positions from file {POSITIONS_CSV}")
    try:
        positions_df = pd.read_csv(POSITIONS_CSV)
        logger.info(f"Loaded {len(positions_df)} positions for Spot vs. Bid-Ask analysis.")
    except FileNotFoundError:
        logger.error(f"File {POSITIONS_CSV} not found or empty. Run log extraction first.")
        print(f"Error: File {POSITIONS_CSV} not found. Please run step 1 first.")
        return

    os.makedirs(DETAILED_REPORTS_DIR, exist_ok=True)
    all_final_results = []

    for index, position in positions_df.iterrows():
        logger.info(f"\n--- Analyzing position {index+1}/{len(positions_df)}: {position['token_pair']} ---")
        position_dict = position.to_dict()

        start_dt = _parse_custom_timestamp(position['open_timestamp'])
        end_dt = _parse_custom_timestamp(position['close_timestamp'])

        if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
            logger.warning(f"Skipped position {position.get('position_id', 'N/A')} due to invalid dates.")
            continue
            
        price_history = fetch_price_history(position['pool_address'], start_dt, end_dt, api_key)
        time.sleep(0.6) # Rate limiting
        
        if not price_history:
            logger.warning(f"No price history for {position['token_pair']}. Skipping simulation.")
            continue
        
        import re
        strategy_str = position.get('actual_strategy_from_log', '')
        step_match = re.search(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', strategy_str)
        step_size = step_match.group(1) if step_match else "UNKNOWN"
        bin_step = 100
        
        analyzer = SpotVsBidAskSimulator(bin_step=bin_step, step_size=step_size)
        simulation_results = analyzer.run_all_simulations(position_dict, price_history)
        
        report_filename_safe = f"{position['token_pair'].replace('/', '_')}_{str(position['open_timestamp']).replace('/','-').replace(':','-')}.txt"
        report_filename = os.path.join(DETAILED_REPORTS_DIR, report_filename_safe)
        
        text_report = generate_text_report(position_dict, simulation_results)
        with open(report_filename, 'w', encoding='utf-8') as f: f.write(text_report)
        logger.info(f"Saved detailed report: {report_filename}")
        
        best_strategy_name = "error"
        best_pnl = None
        if simulation_results and 'error' not in simulation_results:
            best_strategy_name = max(simulation_results, key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            best_pnl = simulation_results[best_strategy_name].get('pnl_sol')

        final_row = {**position_dict, "best_sim_strategy": best_strategy_name, "best_sim_pnl": best_pnl}
        
        if simulation_results and 'error' not in simulation_results:
            for name, res in simulation_results.items():
                column_name = f"pnl_{name.replace(' ','_').lower()}"
                final_row[column_name] = res.get('pnl_sol')
        
        all_final_results.append(final_row)

    logger.info(f"\nSaving final Spot vs. Bid-Ask comprehensive report...")
    if all_final_results:
        final_df = pd.DataFrame(all_final_results)
        final_df.to_csv(FINAL_REPORT_CSV, index=False, encoding='utf-8')
        logger.info(f"Saved final report to: {FINAL_REPORT_CSV}")
    else:
        logger.warning("No final results were generated.")
        
    logger.info("\nSpot vs. Bid-Ask analysis completed!")