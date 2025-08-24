# tools/debug_post_close.py

import logging
import pandas as pd
from datetime import datetime
import os
import sys

# --- Setup Project Path ---
# This allows the script to find other modules like 'core', 'reporting', etc.
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from core.models import Position
from reporting.post_close_analyzer import PostCloseAnalyzer
from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager

# --- Configure Logging ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Helper Function to Create a Position Object ---
def create_position_from_csv_row(csv_row_data: str) -> Position:
    """Creates a Position object from a single line of CSV data."""
    from io import StringIO
    
    # The first line is header, second is data
    csv_data = "position_id,wallet_id,source_file,token_pair,pool_address,strategy_raw,takeProfit,stopLoss,max_profit_during_position,max_loss_during_position,total_fees_collected,min_bin_price,max_bin_price,oor_timeout_minutes,oor_threshold_pct,investment_sol,pnl_sol,open_timestamp,close_timestamp,close_reason,bot_version,retry_count,open_line_index,close_line_index,strategy_instance_id\n" + csv_row_data
    
    df = pd.read_csv(StringIO(csv_data))
    row = df.iloc[0]

    # AIDEV-NOTE-CLAUDE: Must handle the custom timestamp format from SOL Decoder logs.
    # This is a common source of errors.
    def _parse_custom_timestamp(ts_str: str) -> datetime:
        """ Simplified parser for 'MM/DD-HH:MM:SS' format. """
        if not isinstance(ts_str, str) or not ts_str:
            return None
        try:
            # Assume current year for simplicity in this debug script
            current_year = datetime.now().year
            # Format: "05/19-13:18:03"
            dt_obj = datetime.strptime(f"{current_year}/{ts_str}", "%Y/%m/%d-%H:%M:%S")
            return dt_obj
        except ValueError:
            logger.error(f"Failed to parse timestamp: {ts_str}")
            return None

    # Create a simple object that mimics the Position class for the analyzer
    class SimplePosition:
        def __init__(self, series):
            self.position_id = series.get('position_id')
            self.pool_address = series.get('pool_address')
            self.open_timestamp = _parse_custom_timestamp(series.get('open_timestamp'))
            self.close_timestamp = _parse_custom_timestamp(series.get('close_timestamp'))
            self.initial_investment = float(series.get('investment_sol'))
            self.final_pnl = float(series.get('pnl_sol'))
            self.close_reason = series.get('close_reason')
            self.actual_strategy = series.get('strategy_raw')
            self.total_fees_collected = float(series.get('total_fees_collected')) if pd.notna(series.get('total_fees_collected')) else 0.0
            
    return SimplePosition(row)

# --- Main Diagnostic Function ---
def diagnose_post_close_analyzer():
    logger.info("--- Starting Post-Close Analyzer Diagnosis ---")

    # 1. Your example position data
    csv_row = "pos_08-02-18-52-10_62468886,5dJVc7cJkjrNEm1U9g9HHE6ntxktDcuEbnj9iJaku9rJ,app-2_20250810.log,IMAGINE-SOL,96cggYYFkPiKwiYrQSDhEhtJRRAb28E6kUZHqtmnN9y6,Spot (1-Sided) SIXTYNINE,8.0,9.0,0.16,,0.00725,0.0043753934403016,0.0101571633435574,10.0,2.5,10.49,0.01605,08/02-18:52:10,08/02-19:07:28,OOR,0.13.36,0,62468886,62469644.0,Spot (1-Sided) SIXTYNINE_10.49_8_9_24a03b"
    
    # 2. Create the position object
    position = create_position_from_csv_row(csv_row)
    if not position or not position.open_timestamp or not position.close_timestamp:
        logger.error("Failed to create a valid position object. Aborting.")
        return

    logger.info(f"Successfully created position object for: {position.position_id}")
    logger.info(f"Pool Address: {position.pool_address}")
    logger.info(f"Open Time: {position.open_timestamp}")
    logger.info(f"Close Time: {position.close_timestamp}")

    # 3. Instantiate the analyzer and its cache manager
    # We will add detailed logging inside the analyzer's methods
    analyzer = PostCloseAnalyzer()
    
    # --- DEEP DIVE INTO THE ANALYSIS PROCESS ---
    logger.info("\n--- STEP 1: Calculating post-close period ---")
    end_datetime, extension_hours = analyzer._calculate_post_close_period(position)
    logger.info(f"Calculated post-close period: {extension_hours:.2f} hours")
    logger.info(f"Data will be fetched from {position.close_timestamp} to {end_datetime}")

    logger.info("\n--- STEP 2: Fetching post-close data via cache_manager.fetch_post_close_data ---")
    # This is the critical function call
    post_close_data = analyzer.cache_manager.fetch_post_close_data(position, extension_hours)
    
    if post_close_data:
        logger.info(f"SUCCESS: Fetched {len(post_close_data)} data points for the post-close period.")
        first_point = post_close_data[0]
        last_point = post_close_data[-1]
        logger.info(f"First data point timestamp: {datetime.fromtimestamp(first_point.get('timestamp'))}")
        logger.info(f"Last data point timestamp: {datetime.fromtimestamp(last_point.get('timestamp'))}")
    else:
        logger.error("FAILURE: fetch_post_close_data returned NO DATA. This is the root cause of the problem.")
        logger.error("Investigate the logs from EnhancedPriceCacheManager to see why the cache lookup or API fetch failed.")

    logger.info("\n--- Diagnosis Complete ---")

if __name__ == "__main__":
    diagnose_post_close_analyzer()