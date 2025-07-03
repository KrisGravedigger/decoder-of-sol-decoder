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
from .data_loader import _parse_custom_timestamp
from .price_cache_manager import PriceCacheManager

# --- Configuration ---
POSITIONS_CSV = "positions_to_analyze.csv"
FINAL_REPORT_CSV = "final_analysis_report.csv"
DETAILED_REPORTS_DIR = "detailed_reports"

logger = logging.getLogger('AnalysisRunner')

# AIDEV-NOTE-CLAUDE: Simplified fetch function - delegates to smart cache manager
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
    # Determine optimal timeframe
    duration_hours = (end_dt - start_dt).total_seconds() / 3600
    
    if duration_hours <= 4: 
        timeframe = "10min"
    elif duration_hours <= 12: 
        timeframe = "30min"
    elif duration_hours <= 72: 
        timeframe = "1h"
    else: 
        timeframe = "4h"
    
    # Delegate to smart cache manager
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
    
    def analyze_all_positions(self, positions_df: pd.DataFrame) -> List[Dict]:
        """
        Analyze all positions with strategy comparisons.
        
        Args:
            positions_df (pd.DataFrame): Positions to analyze
            
        Returns:
            List[Dict]: Analysis results for each position
        """
        results = []
        
        for index, position in positions_df.iterrows():
            logger.info(f"Analyzing position {index+1}/{len(positions_df)}: {position['token_pair']}")
            
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
            start_dt = _parse_custom_timestamp(position_dict['open_timestamp'])
            end_dt = _parse_custom_timestamp(position_dict['close_timestamp'])

            if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
                logger.warning(f"Invalid timestamps for position {position_dict.get('position_id', 'N/A')}")
                return None
                
            # Fetch price history using smart cache
            price_history = fetch_price_history(
                position_dict['pool_address'], start_dt, end_dt, self.api_key
            )
            
            if not price_history:
                logger.warning(f"No price history for {position_dict['token_pair']}")
                return None
            
            # Extract step size from strategy string
            import re
            strategy_str = position_dict.get('actual_strategy_from_log', '')
            step_match = re.search(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', strategy_str)
            step_size = step_match.group(1) if step_match else "UNKNOWN"
            
            # Run simulations
            analyzer = SpotVsBidAskSimulator(bin_step=100, step_size=step_size)
            simulation_results = analyzer.run_all_simulations(position_dict, price_history)
            
            if not simulation_results or 'error' in simulation_results:
                return None
            
            # Determine best strategy
            best_strategy_name = max(simulation_results, key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            
            return {
                'position_id': position_dict.get('position_id'),
                'token_pair': position_dict.get('token_pair'),
                'best_strategy': best_strategy_name,
                'simulation_results': simulation_results
            }
            
        except Exception as e:
            logger.error(f"Analysis failed for position {position_dict.get('position_id')}: {e}")
            return None

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

    # AIDEV-NOTE-CLAUDE: Test limit - first 20 positions only for testing
    test_limit = 20
    positions_to_test = positions_df.head(test_limit)
    logger.info(f"TEST MODE: Analyzing first {len(positions_to_test)} positions only")

    os.makedirs(DETAILED_REPORTS_DIR, exist_ok=True)
    all_final_results = []

    for index, position in positions_to_test.iterrows():
        logger.info(f"\n--- Analyzing position {index+1}/{len(positions_to_test)}: {position['token_pair']} ---")
        position_dict = position.to_dict()

        start_dt = _parse_custom_timestamp(position['open_timestamp'])
        end_dt = _parse_custom_timestamp(position['close_timestamp'])

        if pd.isna(start_dt) or pd.isna(end_dt) or start_dt >= end_dt:
            logger.warning(f"Skipped position {position.get('position_id', 'N/A')} due to invalid dates.")
            continue
            
        # AIDEV-NOTE-CLAUDE: Smart cache system - only fetches missing data gaps
        price_history = fetch_price_history(position['pool_address'], start_dt, end_dt, api_key)
        
        # Rate limiting between positions (not needed within smart cache)
        time.sleep(0.6)
        
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
        with open(report_filename, 'w', encoding='utf-8') as f: 
            f.write(text_report)
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