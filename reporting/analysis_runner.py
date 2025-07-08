import os
import csv
import time
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
# AIDEV-NOTE-CLAUDE: Import the custom timestamp parser as per CLAUDE.md
from .data_loader import _parse_custom_timestamp
from .price_cache_manager import PriceCacheManager

# --- Configuration ---
POSITIONS_CSV = "positions_to_analyze.csv"
FINAL_REPORT_CSV = "final_analysis_report.csv"
DETAILED_REPORTS_DIR = "detailed_reports"

logger = logging.getLogger('AnalysisRunner')

def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime, api_key: Optional[str]) -> List[Dict]:
    """
    Fetch price history with smart caching via PriceCacheManager.
    
    Args:
        pool_address (str): Pool address
        start_dt (datetime): Start datetime
        end_dt (datetime): End datetime
        api_key (Optional[str]): API key for fetching missing data
        
    Returns:
        List[Dict]: Price data with timestamp and close keys
    """
    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    
    if duration_hours <= 4: 
        timeframe = "10min"
    elif duration_hours <= 12: 
        timeframe = "30min"
    elif duration_hours <= 72: 
        timeframe = "1h"
    else: 
        timeframe = "4h"
    
    cache_manager = PriceCacheManager()
    return cache_manager.get_price_data(pool_address, start_dt, end_dt, timeframe, api_key)

def generate_text_report(position_data: Dict, simulation_results: Dict) -> str:
    """Generate a detailed text report for a position analysis."""
    report = []
    report.append("="*60)
    report.append(f"POSITION ANALYSIS: {position_data['token_pair']}")
    report.append(f"Pool: {position_data['pool_address']}")
    report.append(f"Period: {position_data['open_timestamp']} -> {position_data['close_timestamp']}")
    report.append("="*60)
    report.append(f"\n--- INPUT DATA ---")
    report.append(f"Investment: {position_data.get('investment_sol', 0):.4f} SOL")
    report.append(f"Actual strategy: {position_data.get('strategy_raw', 'N/A')}")
    report.append(f"Actual PnL (from log): {position_data.get('pnl_sol', 'N/A')}")
    report.append(f"\n--- SIMULATION RESULTS (PnL in SOL) ---")
    
    if not simulation_results or 'error' in simulation_results:
        report.append("Error during simulation or no results available.")
    else:
        # Use .get('pnl_sol', -9e9) for safe sorting even if a strategy fails
        sorted_results = sorted(simulation_results.items(), key=lambda item: item[1].get('pnl_sol', -9e9), reverse=True)
        for name, res in sorted_results:
            report.append(f"\n- Strategy: {name}")
            report.append(f"  > Total PnL: {res.get('pnl_sol', 0):+.5f} SOL ({res.get('return_pct', 0):.2f}%)")
            report.append(f"    (Est. fees: {res.get('pnl_from_fees', 0):+.5f} | Est. value change/IL: {res.get('pnl_from_il', 0):+.5f})")
        
        if sorted_results:
            report.append("\n" + "="*60)
            report.append(f"BEST STRATEGY: {sorted_results[0][0]}")
            report.append("="*60)
    return "\n".join(report)

class AnalysisRunner:
    """
    Main analysis runner for Spot vs Bid-Ask strategy comparisons.
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize analysis runner.
        
        Args:
            api_key (Optional[str]): Moralis API key
        """
        self.api_key = api_key
        if not api_key:
            logger.warning("AnalysisRunner initialized without API key - cache-only mode")
    
    def _smart_timestamp_parser(self, timestamp_str: str) -> Optional[datetime]:
        """
        Smart timestamp parser that handles both custom SOL Decoder format and standard format.
        
        Args:
            timestamp_str (str): Timestamp string to parse
            
        Returns:
            Optional[datetime]: Parsed datetime or None if parsing fails
        """
        if pd.isna(timestamp_str) or timestamp_str == '' or str(timestamp_str).lower() == 'nan':
            return None
            
        # Check if it's SOL Decoder format (MM/DD-HH:MM:SS)
        # Format has slash, dash, and when split by dash should give exactly 2 parts
        if '/' in timestamp_str and '-' in timestamp_str and len(timestamp_str.split('-')) == 2:
            return _parse_custom_timestamp(timestamp_str)
        else:
            # Standard format - use pandas directly
            try:
                return pd.to_datetime(timestamp_str)
            except Exception as e:
                logger.warning(f"Failed to parse standard timestamp '{timestamp_str}': {e}")
                return None

    def analyze_all_positions(self, positions_df: pd.DataFrame) -> List[Dict]:
        """
        Analyze all positions with strategy comparisons.
        
        Args:
            positions_df (pd.DataFrame): Positions to analyze
            
        Returns:
            List[Dict]: Analysis results for each position
        """
        results = []
        # AIDEV-NOTE-CLAUDE: Use enumerate to get a correct loop counter (idx).
        # The row index from iterrows() can be non-sequential after filtering.
        total_positions = len(positions_df)
        for idx, (original_index, position) in enumerate(positions_df.iterrows()):
            logger.info(f"Analyzing position {idx + 1}/{total_positions}: {position['token_pair']} (pos_id: {position.get('position_id', 'N/A')})")
            
            result = self.analyze_single_position(position.to_dict())
            if result:
                results.append(result)
        
        return results
    
    def analyze_single_position(self, position_dict: Dict) -> Optional[Dict]:
        """
        Analyze single position with strategy comparison.
        
        Args:
            position_dict (Dict): Position data
            
        Returns:
            Optional[Dict]: Analysis result or None if failed
        """
        try:
            # AIDEV-NOTE-CLAUDE: Debug logging for missing column investigation
            logger.debug(f"Position {position_dict.get('position_id', 'UNKNOWN')} keys: {sorted(position_dict.keys())}")
            
            # Check for required columns before proceeding
            # AIDEV-NOTE-CLAUDE: Use actual runtime column names, not CSV header names
            required_columns = ['investment_sol', 'open_timestamp', 'close_timestamp', 'pool_address', 'token_pair']
            missing_columns = [col for col in required_columns if col not in position_dict]
            
            if missing_columns:
                logger.error(f"Missing required columns for position {position_dict.get('position_id', 'UNKNOWN')}: {missing_columns}")
                logger.error(f"Available keys: {list(position_dict.keys())}")
                return None
            
            # AIDEV-NOTE-CLAUDE: Smart timestamp parsing - handle both SOL Decoder and standard formats
            start_dt = self._smart_timestamp_parser(str(position_dict['open_timestamp']))
            end_dt = self._smart_timestamp_parser(str(position_dict['close_timestamp']))

            if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
                logger.warning(f"Invalid or unparseable timestamps for position {position_dict.get('position_id', 'N/A')}. open='{position_dict['open_timestamp']}', close='{position_dict['close_timestamp']}'")
                return None
                
            price_history = fetch_price_history(
                position_dict['pool_address'], start_dt, end_dt, self.api_key
            )
            
            # AIDEV-DEBUG-CLAUDE: Check price data structure and content
            if price_history:
                logger.info(f"Got {len(price_history)} price points. First: {price_history[0] if price_history else 'NONE'}, Last: {price_history[-1] if price_history else 'NONE'}")
                
                # Check for zero prices and warn
                zero_count = sum(1 for p in price_history if p.get('close', 0) <= 0)
                if zero_count > 0:
                    logger.warning(f"⚠️  DATA QUALITY WARNING: {zero_count}/{len(price_history)} price points have zero/negative values for {position_dict['token_pair']}")
                
                # Apply forward fill to clean zero prices
                price_history = self._forward_fill_price_history(price_history, position_dict['token_pair'])
            
            if not price_history:
                logger.warning(f"No price history for {position_dict['token_pair']}. Skipping simulation for this position.")
                return {
                    'position_id': position_dict.get('position_id'),
                    'token_pair': position_dict.get('token_pair'),
                    'best_strategy': 'ERROR - No Price History',
                    'simulation_results': {'error': 'No price history available'}
                }
            
            import re
            strategy_str = position_dict.get('strategy_raw', '')
            step_match = re.search(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', str(strategy_str), re.IGNORECASE)
            step_size = step_match.group(1).upper() if step_match else "UNKNOWN"
            
            analyzer = SpotVsBidAskSimulator(bin_step=100, step_size=step_size)
            simulation_results = analyzer.run_all_simulations(position_dict, price_history)
            
            if not simulation_results or 'error' in simulation_results:
                best_strategy_name = 'ERROR - Simulation Failed'
            else:
                best_strategy_name = max(simulation_results, key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            
            return {
                'position_id': position_dict.get('position_id'),
                'token_pair': position_dict.get('token_pair'),
                'best_strategy': best_strategy_name,
                'simulation_results': simulation_results
            }
            
        except Exception as e:
            logger.error(f"Analysis failed for position {position_dict.get('position_id')}: {e}", exc_info=True)
            return None
        
    def _forward_fill_price_history(self, price_history: List[Dict], token_pair: str) -> List[Dict]:
        """
        Apply forward fill to handle missing price data.
        
        Args:
            price_history (List[Dict]): Raw price data from cache
            token_pair (str): Token pair name for logging
            
        Returns:
            List[Dict]: Cleaned price data with forward-filled prices
        """
        if not price_history:
            return price_history
            
        cleaned_history = []
        last_valid_price = None
        missing_periods = []
        
        for i, item in enumerate(price_history):
            price = item.get('close', 0)
            timestamp = item.get('timestamp', 0)
            
            if price <= 0:
                if last_valid_price is not None:
                    # Forward-fill with last valid price
                    new_item = item.copy()
                    new_item['close'] = last_valid_price
                    new_item['forward_filled'] = True
                    cleaned_history.append(new_item)
                    
                    # Track missing period for warning
                    if not missing_periods or missing_periods[-1]['end_idx'] != i - 1:
                        missing_periods.append({'start_idx': i, 'end_idx': i, 'timestamp': timestamp})
                    else:
                        missing_periods[-1]['end_idx'] = i
                        
                    logger.debug(f"Forward-filled price gap for {token_pair}")
                else:
                    # Skip until we find first valid price
                    logger.debug(f"Skipping invalid price at start for {token_pair}")
                    continue
            else:
                # Valid price found
                last_valid_price = price
                new_item = item.copy()
                new_item['forward_filled'] = False
                cleaned_history.append(new_item)
        
        # Generate comprehensive warnings for missing data periods
        if missing_periods:
            logger.warning(f"📊 MISSING DATA WARNING for {token_pair}:")
            for period in missing_periods:
                start_time = datetime.fromtimestamp(period['timestamp']).strftime('%Y-%m-%d %H:%M')
                if period['start_idx'] == period['end_idx']:
                    logger.warning(f"   • Missing price data at {start_time}")
                else:
                    count = period['end_idx'] - period['start_idx'] + 1
                    logger.warning(f"   • Missing price data for {count} consecutive periods starting {start_time}")
        
        # If all prices were zero, create minimal fallback
        if not cleaned_history and price_history:
            logger.warning(f"⚠️  CRITICAL: All prices were zero for {token_pair}, creating fallback data")
            fallback_price = 0.000001  # Minimal non-zero price to prevent division by zero
            for item in price_history:
                new_item = item.copy()
                new_item['close'] = fallback_price
                new_item['forward_filled'] = True
                new_item['fallback_data'] = True
                cleaned_history.append(new_item)
        
        return cleaned_history

def run_spot_vs_bidask_analysis(api_key: Optional[str]):
    """Main analysis function that coordinates the Spot vs. Bid-Ask simulation."""
    if not api_key:
        logger.warning("No API key provided. Running in cache-only mode for Spot vs Bid-Ask analysis.")

    logger.info(f"Loading positions from file {POSITIONS_CSV}")
    try:
        positions_df = pd.read_csv(POSITIONS_CSV)
        logger.info(f"Loaded {len(positions_df)} positions for Spot vs. Bid-Ask analysis.")
    except FileNotFoundError:
        logger.error(f"File {POSITIONS_CSV} not found or empty. Run log extraction first.")
        print(f"Error: File {POSITIONS_CSV} not found. Please run step 1 first.")
        return

    # AIDEV-NOTE-CLAUDE: API rate limiting - test mode with x positions max
    """
    test_limit = 5
    if len(positions_df) > test_limit:
        positions_to_run = positions_df.head(test_limit)
        logger.info(f"Test mode: analyzing first {test_limit} positions (out of {len(positions_df)} total).")
    else:
        positions_to_run = positions_df
        logger.info(f"Analyzing all {len(positions_to_run)} positions.")
    """

    positions_to_run = positions_df

    os.makedirs(DETAILED_REPORTS_DIR, exist_ok=True)
    
    runner = AnalysisRunner(api_key=api_key)
    all_simulation_results = runner.analyze_all_positions(positions_to_run)

    # Process results for final CSV report
    processed_results_for_df = []
    for result in all_simulation_results:
        if not result or 'position_id' not in result:
            continue
            
        # Find original position data to merge with results
        original_position_series = positions_df[positions_df['position_id'] == result['position_id']]
        if original_position_series.empty:
            logger.warning(f"Could not find original data for position_id: {result['position_id']}")
            continue
        original_position = original_position_series.iloc[0].to_dict()
        
        final_row = {
            **original_position, 
            "best_sim_strategy": result.get('best_strategy'),
        }

        sim_results = result.get('simulation_results', {})
        if sim_results and 'error' not in sim_results:
            best_strategy_pnl = sim_results.get(result.get('best_strategy'), {}).get('pnl_sol')
            final_row["best_sim_pnl"] = best_strategy_pnl
            for name, res in sim_results.items():
                column_name = f"pnl_{name.replace(' ','_').lower()}"
                final_row[column_name] = res.get('pnl_sol')
        
        processed_results_for_df.append(final_row)
        
        # Generate text report for each position
        report_filename_safe = f"{result['token_pair'].replace('/', '_')}_{str(original_position['open_timestamp']).replace('/','-').replace(':','-')}.txt"
        report_filename = os.path.join(DETAILED_REPORTS_DIR, report_filename_safe)
        
        text_report = generate_text_report(original_position, sim_results)
        with open(report_filename, 'w', encoding='utf-8') as f: 
            f.write(text_report)
        logger.info(f"Saved detailed report: {report_filename}")

    logger.info(f"\nSaving final Spot vs. Bid-Ask comprehensive report...")
    if processed_results_for_df:
        final_df = pd.DataFrame(processed_results_for_df)
        final_df.to_csv(FINAL_REPORT_CSV, index=False, encoding='utf-8')
        logger.info(f"Saved final report to: {FINAL_REPORT_CSV}")
    else:
        logger.warning("No final results were generated for the comprehensive report.")
        
    logger.info("\nSpot vs. Bid-Ask analysis completed!")