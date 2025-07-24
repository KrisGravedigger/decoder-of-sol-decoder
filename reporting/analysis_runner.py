import os
import pandas as pd
from datetime import datetime
import logging
from typing import Dict, List, Optional, Any
import sys
import re

# AIDEV-NOTE-CLAUDE: Ensure correct path for sibling imports
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if project_root not in sys.path:
    sys.path.append(project_root)

from simulations.spot_vs_bidask_simulator import SpotVsBidAskSimulator
from reporting.data_loader import _parse_custom_timestamp
from reporting.price_cache_manager import PriceCacheManager

logger = logging.getLogger(__name__)

class AnalysisRunner:
    """
    Main analysis runner for Spot vs Bid-Ask strategy comparisons.
    It now uses the centralized PriceCacheManager directly.
    """

    # AIDEV-NOTE-GEMINI: Constructor updated to accept force_refetch.
    def __init__(self, api_key: Optional[str] = None, force_refetch: bool = False, use_cache_only: bool = False, config: Optional[Dict] = None):
        """
        Initialize analysis runner.

        Args:
            api_key (Optional[str]): Moralis API key for the PriceCacheManager.
            force_refetch (bool): If True, forces re-fetching of cached data.
            use_cache_only (bool): If True, operates in cache-only mode for TP/SL optimization.
            config (Optional[Dict]): Configuration dictionary.
        """
        self.api_key = api_key
        self.force_refetch = force_refetch
        self.use_cache_only = use_cache_only
        self.config = config or {}
        
        # AIDEV-VOLUME-CLAUDE: Use enhanced cache manager when use_cache_only is True
        if use_cache_only:
            from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
            self.cache_manager = EnhancedPriceCacheManager()
        else:
            self.cache_manager = PriceCacheManager(config=config)
        if not api_key:
            logger.warning("AnalysisRunner initialized in CACHE-ONLY mode.")
        if force_refetch:
            logger.info("AnalysisRunner initialized in FORCE-REFETCH mode.")
        if use_cache_only:
            logger.info("AnalysisRunner initialized in ENHANCED CACHE-ONLY mode for TP/SL optimization.")


    def _get_timeframe_for_duration(self, start_dt: datetime, end_dt: datetime) -> str:
        """Determines the optimal timeframe based on the position's duration."""
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        if duration_hours <= 4: return "10min"
        if duration_hours <= 12: return "30min"
        if duration_hours <= 72: return "1h"
        return "4h"

    def analyze_all_positions(self, positions_df: pd.DataFrame) -> List[Dict]:
        """
        Analyze all positions with strategy comparisons.
        
        Args:
            positions_df (pd.DataFrame): Positions to analyze
            
        Returns:
            List[Dict]: Analysis results for each position
        """
        results = []
        total_positions = len(positions_df)
        for idx, (original_index, position) in enumerate(positions_df.iterrows()):
            logger.debug(f"Analyzing position {idx + 1}/{total_positions}: {position['token_pair']} (pos_id: {position.get('position_id', 'N/A')})")
            
            result = self.analyze_single_position(position.to_dict())
            if result:
                results.append(result)
        
        return results
    
    def analyze_single_position(self, position_dict: Dict) -> Optional[Dict]:
        """
        Analyze a single position with strategy comparison.
        
        Args:
            position_dict (Dict): Position data
            
        Returns:
            Optional[Dict]: Analysis result or None if failed
        """
        try:
            required_columns = ['investment_sol', 'open_timestamp', 'close_timestamp', 'pool_address', 'token_pair']
            if any(col not in position_dict for col in required_columns):
                logger.error(f"Skipping position due to missing required columns. Position ID: {position_dict.get('position_id', 'N/A')}")
                return None

            # AIDEV-NOTE-GEMINI: Centralized parsing is now enforced upstream in main.py.
            # We can rely on receiving datetime objects.
            start_dt = position_dict.get('open_timestamp')
            end_dt = position_dict.get('close_timestamp')

            # This safety check is still valuable to catch any residual data issues.
            if not isinstance(start_dt, (pd.Timestamp, datetime)) or not isinstance(end_dt, (pd.Timestamp, datetime)):
                logger.error(f"FATAL DATA ERROR in analysis_runner: Invalid timestamp types for position {position_dict.get('position_id', 'N/A')}. open_dt: {type(start_dt)}, close_dt: {type(end_dt)}. Skipping.")
                return None
            
            if end_dt <= start_dt:
                logger.error(f"FATAL DATA ERROR in analysis_runner: close_timestamp is before open_timestamp for position {position_dict.get('position_id', 'N/A')}. Skipping.")
                return None
                
            # Use the centralized cache manager to get price data
            timeframe = self._get_timeframe_for_duration(start_dt, end_dt)
            price_history = self.cache_manager.get_price_data(
                pool_address=position_dict['pool_address'], 
                start_dt=start_dt, 
                end_dt=end_dt, 
                timeframe=timeframe,
                api_key=self.api_key,
                force_refetch=self.force_refetch # AIDEV-NOTE-GEMINI: Pass the flag here.
            )
            
            if not price_history:
                logger.warning(f"No price history for {position_dict['token_pair']}. Skipping simulation.")
                return {'position_id': position_dict.get('position_id'), 'token_pair': position_dict['token_pair'], 'best_strategy': 'ERROR - No Price History', 'simulation_results': {'error': 'No price history available'}}

            step_match = re.search(r'(WIDE|MEDIUM|NARROW|SIXTYNINE)', str(position_dict.get('strategy_raw', '')), re.IGNORECASE)
            step_size = step_match.group(1).upper() if step_match else "UNKNOWN"
            
            try:
                investment_sol_float = float(position_dict['investment_sol'])
                pnl_sol_float = float(position_dict['pnl_sol']) if pd.notna(position_dict.get('pnl_sol')) else None
            except (ValueError, TypeError):
                logger.error(f"Invalid numeric data for position {position_dict.get('position_id', 'N/A')}. Skipping.")
                return {'position_id': position_dict.get('position_id'), 'token_pair': position_dict['token_pair'], 'best_strategy': 'ERROR - Invalid Input Data', 'simulation_results': {'error': 'Invalid numeric input data.'}}

            analyzer = SpotVsBidAskSimulator(bin_step=100, step_size=step_size)
            simulation_results = analyzer.run_all_simulations(
                investment_sol=investment_sol_float,
                pnl_sol=pnl_sol_float,
                price_history=price_history,
                open_timestamp=start_dt,
                close_timestamp=end_dt,
                close_reason=position_dict.get('close_reason', 'other')
            )
            
            best_strategy_name = 'ERROR'
            if simulation_results and not simulation_results.get('error'):
                best_strategy_name = max(simulation_results, key=lambda k: simulation_results[k].get('pnl_sol', -9e9))
            
            return {
                'position_id': position_dict.get('position_id'),
                'token_pair': position_dict.get('token_pair'),
                'best_strategy': best_strategy_name,
                'simulation_results': simulation_results
            }
            
        except Exception as e:
            logger.error(f"Analysis failed for position {position_dict.get('position_id', 'N/A')}: {e}", exc_info=True)
            return None