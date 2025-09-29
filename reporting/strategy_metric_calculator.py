import pandas as pd
import os
import logging
from typing import Dict

logger = logging.getLogger(__name__)

class StrategyMetricsCalculator:
    """
    Central service for calculating strategy metrics, using strategy_instances.csv
    as the single source of truth for invested capital.
    """
    def __init__(self, strategy_instances_path: str = "strategy_instances.csv"):
        self._strategy_data: Dict[str, float] = {}
        if os.path.exists(strategy_instances_path):
            try:
                df = pd.read_csv(strategy_instances_path)
                # Use a dictionary for O(1) lookup performance
                self._strategy_data = df.set_index('strategy_instance_id')['total_invested'].to_dict()
                logger.info(f"StrategyMetricsCalculator initialized with data for {len(self._strategy_data)} strategies.")
            except Exception as e:
                logger.error(f"Failed to load strategy instances data: {e}", exc_info=True)
        else:
            logger.warning(f"Strategy instances file not found at {strategy_instances_path}. PnL percentages will be 0.")

    def get_pnl_percentage(self, strategy_id: str, simulated_pnl_sol: float) -> float:
        """
        Calculates the PnL percentage (ROIC) for a given strategy and simulation result.
        
        Args:
            strategy_id (str): The ID of the strategy instance.
            simulated_pnl_sol (float): The PnL in SOL from a simulation.
            
        Returns:
            float: The calculated PnL percentage.
        """
        # Ensure the key is a string for consistent lookup
        total_invested = self._strategy_data.get(str(strategy_id))
        
        if total_invested is None:
            # This can happen for strategies filtered out, it's not an error.
            # logger.debug(f"No investment data found for strategy_id: {strategy_id}. Cannot calculate percentage.")
            return 0.0
            
        if total_invested == 0:
            return 0.0
            
        return (simulated_pnl_sol / total_invested) * 100

    def get_total_investment(self, strategy_id: str) -> float:
        """
        Returns the total invested amount for a given strategy.
        
        Args:
            strategy_id (str): The ID of the strategy instance.
            
        Returns:
            float: The total invested amount in SOL, or 0.0 if not found.
        """
        return self._strategy_data.get(str(strategy_id), 0.0)