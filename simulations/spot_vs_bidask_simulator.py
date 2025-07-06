import math
import logging
from typing import List, Dict, Tuple, Optional
import pandas as pd

# Configure logging
logger = logging.getLogger(__name__)

class SpotVsBidAskSimulator: # AIDEV-NOTE-CLAUDE: Renamed class from StrategyAnalyzer
    """
    Runs Spot vs. Bid-Ask strategy simulations based on historical data.
    Formerly known as StrategyAnalyzer.
    """
    
    def __init__(self, bin_step: int, num_bins: int = 69, step_size: str = "UNKNOWN"):
        """
        Initialize the strategy simulator.
        
        Args:
            bin_step: Price step between bins in basis points (from pool data)
            num_bins: Number of bins in the liquidity distribution  
            step_size: Step size configuration from logs (WIDE/MEDIUM/NARROW/SIXTYNINE)
        """
        self.bin_step = bin_step
        self.step_size = step_size
        self.price_factor = 1 + self.bin_step / 10000
        
        # Adjust num_bins based on step_size if it's at default value
        if num_bins == 69:  # Only adjust if using default
            if step_size == "WIDE":
                self.num_bins = 50
            elif step_size == "MEDIUM":
                self.num_bins = 20
            elif step_size == "NARROW":
                self.num_bins = 10
            elif step_size == "SIXTYNINE":
                self.num_bins = 69
            else:
                self.num_bins = num_bins  # Keep default if step_size unknown
        else:
            self.num_bins = num_bins  # Use explicitly provided value

    def _calculate_spot_distribution(self, initial_sol: float) -> List[float]:
        """
        Calculate uniform liquidity distribution (Spot strategy).
        
        Args:
            initial_sol: Initial SOL investment amount
            
        Returns:
            List of SOL amounts per bin (uniform distribution)
        """
        return [initial_sol / self.num_bins] * self.num_bins

    def _calculate_bidask_distribution(self, initial_sol: float) -> List[float]:
        """
        Calculate U-shaped liquidity distribution for 1-sided Bid-Ask strategy.
        Based on DLMM research: Weight(x) = α × (x^β + (1-x)^β)
        
        Args:
            initial_sol: Initial SOL investment amount
            
        Returns:
            List of SOL amounts per bin (U-shaped distribution)
        """
        alpha = 1.0  # Scaling coefficient
        beta = 2.0   # Shape parameter (β > 1 for U-shaped effect)
        
        weights = []
        for i in range(self.num_bins):
            # Normalize bin position to [0, 1]
            x = i / (self.num_bins - 1) if self.num_bins > 1 else 0
            # U-shaped weight function from research
            weight = alpha * (x**beta + (1-x)**beta)
            weights.append(weight)
        
        total_weight = sum(weights)
        return [initial_sol * w / total_weight for w in weights]

    def _get_active_bin_from_price_ratio(self, price_ratio: float) -> int:
        """
        Calculate which bin is active based on price change.
        
        Args:
            price_ratio: Final price / initial price
            
        Returns:
            Active bin index
        """
        if price_ratio <= 1:
            return 0
        active_bin = math.floor(math.log(price_ratio) / math.log(self.price_factor))
        return min(active_bin, self.num_bins - 1)

    def run_all_simulations(self, position_data: Dict, price_history: List[Dict]) -> Dict:
        """
        Run all 1-sided simulations for a given position and price history.
        
        Args:
            position_data: Dictionary containing position information
            price_history: List of price data points with 'close' and 'timestamp' keys
            
        Returns:
            Dictionary with simulation results for each strategy
        """
        if not price_history:
            return {"error": "No price history available for simulation."}

        # AIDEV-NOTE-CLAUDE: Use correct runtime column name 'investment_sol'
        if 'investment_sol' not in position_data:
            available_keys = list(position_data.keys())
            logger.error(f"Missing 'investment_sol' column. Available: {available_keys}")
            return {'error': f'Missing investment_sol column'}
        
        initial_sol = position_data['investment_sol']
        
        if pd.isna(initial_sol) or initial_sol <= 0:
            logger.warning(f"Invalid investment_sol value: {initial_sol}")
            return {'error': f'Invalid investment amount: {initial_sol}'}
        
        if pd.isna(initial_sol) or initial_sol <= 0:
            logger.warning(f"Invalid investment_sol value: {initial_sol}")
            return {'error': f'Invalid investment amount: {initial_sol}'}
        # AIDEV-DEBUG-CLAUDE: Enhanced logging to trace zero price source
        initial_price = price_history[0]['close']
        final_price = price_history[-1]['close']
        
        logger.debug(f"Simulator received {len(price_history)} price points")
        logger.debug(f"First point: {price_history[0]}")
        logger.debug(f"Last point: {price_history[-1]}")
        
        # AIDEV-NOTE-CLAUDE: Prevent division by zero from placeholder/invalid price data
        if initial_price == 0 or final_price == 0:
            logger.warning(f"⚠️  SIMULATION ERROR: Zero price detected after forward-fill: initial={initial_price}, final={final_price}")
            logger.warning(f"   Pool: {position_data.get('pool_address', 'UNKNOWN')}")
            logger.warning(f"   Token: {position_data.get('token_pair', 'UNKNOWN')}")
            logger.warning(f"   Price history length: {len(price_history)}")
            return {'error': f'Invalid price data - contains zero values after cleaning: initial={initial_price}, final={final_price}'}
        
        price_ratio = final_price / initial_price

        actual_pnl_from_log = position_data.get('pnl_sol')
        estimated_total_fees = actual_pnl_from_log if actual_pnl_from_log is not None else initial_sol * 0.005

        results = {}
        spot_distribution = self._calculate_spot_distribution(initial_sol)
        bidask_distribution = self._calculate_bidask_distribution(initial_sol)

        results['1-Sided Spot'] = self._simulate_1sided(
            spot_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        results['1-Sided Bid-Ask'] = self._simulate_1sided(
            bidask_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        
        return results

    def _simulate_1sided(self, distribution: List[float], price_ratio: float, 
                        initial_price: float, final_price: float, 
                        initial_sol: float, fee_budget: float) -> Dict:
        """
        Simulate 1-Sided entry (SOL only).
        
        Args:
            distribution: SOL distribution across bins
            price_ratio: Final/initial price ratio
            initial_price: Starting token price
            final_price: Ending token price
            initial_sol: Initial SOL investment
            fee_budget: Estimated total fees earned
            
        Returns:
            Dictionary with simulation results
        """
        active_bin_index = self._get_active_bin_from_price_ratio(price_ratio)
        
        sol_converted = sum(distribution[:active_bin_index])
        
        tokens_bought = 0
        if sol_converted > 0:
            for i in range(active_bin_index):
                bin_start_price = initial_price * (self.price_factor ** i)
                bin_end_price = initial_price * (self.price_factor ** (i + 1))
                avg_bin_price = (bin_start_price + bin_end_price) / 2
                tokens_bought += distribution[i] / avg_bin_price
        
        remaining_sol = initial_sol - sol_converted
        final_asset_value = (tokens_bought * final_price) + remaining_sol
        pnl_from_assets = final_asset_value - initial_sol

        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[min(active_bin_index, len(distribution)-1)]
        liquidity_ratio = active_bin_liquidity / spot_liquidity_per_bin if spot_liquidity_per_bin > 0 else 1.0
        
        pnl_from_fees = fee_budget * liquidity_ratio
        
        total_pnl = pnl_from_assets + pnl_from_fees
        
        return {
            'pnl_sol': total_pnl,
            'return_pct': (total_pnl / initial_sol) * 100,
            'pnl_from_fees': pnl_from_fees,
            'pnl_from_il': pnl_from_assets,
            'activated_bins': active_bin_index,
            'step_size': getattr(self, 'step_size', 'UNKNOWN'),
            'num_bins_used': self.num_bins
        }
    # AIDEV-NOTE-CLAUDE: Wide vs 69 bins comparison INTENTIONALLY NOT IMPLEMENTED
    # Reason: Wide creates 2-4 positions for bin step 50-125 (logged as single position)
    # Implementation would require: multi-position simulation, liquidity distribution guessing, 
    # complex bin step handling - all for post-factum analysis with limited business value.
    # Anti-Sawtooth strategy also INTENTIONALLY IGNORED - it's position management (rebalancing),
    # not bin distribution method. Our simulations assume bot chose optimal strategy already.
    # Decision date: 2025-06-22. ROI: 20% benefit for 80% effort - rejected.
    # Alternative priorities: ML TP/SL optimization, post-exit analysis.
