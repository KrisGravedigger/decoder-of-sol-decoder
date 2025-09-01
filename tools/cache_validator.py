import os
import pandas as pd
import json
from tqdm import tqdm
import sys
from datetime import datetime, timedelta, timezone

# --- Setup Project Path ---
# This allows the script to be run from anywhere and still find project modules
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.append(project_root)
# --- End Setup ---

from utils.common import load_main_config
from reporting.data_loader import _parse_custom_timestamp

def check_cache_for_position(position, config, cache_base_path):
    """Checks raw and processed cache availability for a single position."""
    
    # 1. Determine the required time range
    max_sim_days = config.get('range_testing', {}).get('max_simulation_days', 7)
    open_ts = position['open_timestamp']
    close_ts = position['close_timestamp']
    end_ts = close_ts + timedelta(days=max_sim_days)
    
    required_months = set(
        (open_ts + timedelta(n)).strftime('%Y-%m') 
        for n in range((end_ts - open_ts).days + 2)
    )
    
    # 2. Check for required cache files
    raw_path = os.path.join(cache_base_path, 'raw')
    processed_path = os.path.join(cache_base_path, 'offline_processed')
    
    raw_files_status = "OK"
    processed_files_status = "OK"
    raw_data_completeness = "PENDING"
    
    # Check raw files
    for month in required_months:
        expected_file = os.path.join(raw_path, month, f"{position['pool_address']}.json")
        if not os.path.exists(expected_file):
            raw_files_status = f"MISSING FILE for month {month}"
            break
            
    # Check processed files
    for month in required_months:
        expected_file = os.path.join(processed_path, month, f"{position['pool_address']}.json")
        if not os.path.exists(expected_file):
            processed_files_status = f"MISSING FILE for month {month}"
            break

    # 3. If raw files exist, check data completeness
    if raw_files_status == "OK":
        all_timestamps = set()
        try:
            for month in required_months:
                file_path = os.path.join(raw_path, month, f"{position['pool_address']}.json")
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    
                    # Handle both formats: {"result": [...]} and [...]
                    result_list = data.get('result', []) if isinstance(data, dict) else data
                    
                    for entry in result_list:
                        if 'timestamp' in entry and entry['timestamp'] is not None:
                            timestamp_val = entry['timestamp']
                            ts = None
                            
                            # --- ROBUSTNESS FIX 2: Handle multiple timestamp formats ---
                            if isinstance(timestamp_val, str):
                                # Handle ISO string format, e.g., "2024-08-21T14:00:00.000Z"
                                ts = datetime.fromisoformat(timestamp_val.replace('Z', '+00:00'))
                            elif isinstance(timestamp_val, (int, float)):
                                # Handle Unix timestamp (assuming seconds), e.g., 1724248800
                                ts = datetime.fromtimestamp(timestamp_val, tz=timezone.utc)
                            
                            if ts:
                                all_timestamps.add(ts.replace(tzinfo=None)) # Use naive datetime for comparison
            
            # Check for gaps. We expect hourly data.
            current_ts = open_ts.replace(minute=0, second=0, microsecond=0)
            gaps = []
            while current_ts < end_ts:
                if current_ts not in all_timestamps:
                    gaps.append(current_ts.strftime('%Y-%m-%d %H:%M'))
                current_ts += timedelta(hours=1)
            
            if not gaps:
                raw_data_completeness = "OK"
            else:
                raw_data_completeness = f"GAP DETECTED (e.g., at {gaps[0]})"
                
        except (IOError, json.JSONDecodeError) as e:
            raw_data_completeness = f"ERROR reading file: {e}"

    return {
        "position_id": position['position_id'],
        "raw_files": raw_files_status,
        "processed_files": processed_files_status,
        "raw_data_completeness": raw_data_completeness,
        "required_range": f"{open_ts.strftime('%Y-%m-%d')} to {end_ts.strftime('%Y-%m-%d')}"
    }


def main():
    """Main diagnostic function."""
    print("--- Cache Validator for TP/SL Simulator ---")
    
    # --- CONFIG ---
    # TARGET_STRATEGY_ID = "Bid-Ask (1-Sided) SIXTYNINE_TP6_SL9_2025-08-08_731d9f"
    TARGET_STRATEGY_ID = "Bid-Ask (1-Sided) SIXTYNINE_TP6_SL9_2025-06-23_b1bee1"
    POSITIONS_FILE = "positions_to_analyze.csv"
    CACHE_BASE_PATH = "price_cache"
    
    try:
        df = pd.read_csv(POSITIONS_FILE)
    except FileNotFoundError:
        print(f"ERROR: {POSITIONS_FILE} not found.")
        return

    # Convert timestamps
    df['open_timestamp'] = df['open_timestamp'].apply(_parse_custom_timestamp)
    df['close_timestamp'] = df['close_timestamp'].apply(_parse_custom_timestamp)
    
    # Filter for target strategy
    target_df = df[df['strategy_instance_id'] == TARGET_STRATEGY_ID]
    
    if target_df.empty:
        print(f"ERROR: No positions found for strategy_instance_id: '{TARGET_STRATEGY_ID}'")
        return
        
    print(f"Found {len(target_df)} positions for strategy '{TARGET_STRATEGY_ID}'. Analyzing cache...\n")
    
    config = load_main_config()
    results = []
    
    for _, row in tqdm(target_df.iterrows(), total=len(target_df), desc="Analyzing positions"):
        result = check_cache_for_position(row, config, CACHE_BASE_PATH)
        results.append(result)
        
    results_df = pd.DataFrame(results)
    
    print("\n--- CACHE VALIDATION REPORT ---")
    print(results_df.to_string())

    print("\n--- SUMMARY ---")
    ok_count = len(results_df[
        (results_df['raw_files'] == 'OK') &
        (results_df['processed_files'] == 'OK') &
        (results_df['raw_data_completeness'] == 'OK')
    ])
    print(f"✅ Positions with complete cache: {ok_count} / {len(results_df)}")
    
    missing_raw = results_df[results_df['raw_files'] != 'OK']
    if not missing_raw.empty:
        print(f"❌ Positions with missing RAW files: {len(missing_raw)}")
        
    missing_processed = results_df[results_df['processed_files'] != 'OK']
    if not missing_processed.empty:
        print(f"❌ Positions with missing PROCESSED files: {len(missing_processed)}")
        
    incomplete_raw = results_df[results_df['raw_data_completeness'] != 'OK']
    if not incomplete_raw.empty:
        print(f"❌ Positions with incomplete RAW data (gaps): {len(incomplete_raw)}")
    

if __name__ == "__main__":
    main()