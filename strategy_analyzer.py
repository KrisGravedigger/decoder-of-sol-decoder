import math
from typing import List, Dict, Tuple, Optional

class StrategyAnalyzer:
    """Runs strategy simulations based on historical data."""
    
    def __init__(self, bin_step: int, num_bins: int = 69, step_size: str = "UNKNOWN"):
        """
        Initialize the strategy analyzer.
        
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
        Run all 4 simulations for given position and price history.
        
        Args:
            position_data: Dictionary containing position information
            price_history: List of price data points with 'close' and 'timestamp' keys
            
        Returns:
            Dictionary with simulation results for each strategy
        """
        if not price_history:
            return {"error": "No price history available for simulation."}

        initial_sol = position_data['initial_investment_sol']
        initial_price = price_history[0]['close']
        final_price = price_history[-1]['close']
        price_ratio = final_price / initial_price

        # Fee estimation based on actual PnL and IL
        # Actual_PnL = PnL_from_fees + PnL_from_price_change (IL)
        # For 1-Sided, IL is zero when price drops, and when it rises, it's opportunity cost
        # (we held SOL instead of token which gained value).
        # For simplification, we assume PnL from price change for 1-sided is 0.
        # Then all profit/loss (except SL/TP) is from fees. This is simplified but sufficient for comparison.
        # In your case, actual strategy was 1-Sided, so:
        actual_pnl_from_log = position_data.get('final_pnl_sol_from_log')
        # If no PnL available, assume 0.5% fees from investment as baseline
        estimated_total_fees = actual_pnl_from_log if actual_pnl_from_log is not None else initial_sol * 0.005

        results = {}
        spot_distribution = self._calculate_spot_distribution(initial_sol)
        bidask_distribution = self._calculate_bidask_distribution(initial_sol)

        # Run simulations
        results['1-Sided Spot'] = self._simulate_1sided(
            spot_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        results['1-Sided Bid-Ask'] = self._simulate_1sided(
            bidask_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        # PLACEHOLDER: 2-sided strategies not implemented (too risky for current use)
        # Can be developed later if needed for comparison purposes
        # results['Spot (2-Sided)'] = self._simulate_2sided(...)
        # results['Bid-Ask (2-Sided)'] = self._simulate_2sided(...)
        
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
        
        # PnL from asset value change (IL)
        # We sell SOL for tokens as price rises
        sol_converted = sum(distribution[:active_bin_index])
        
        # Average purchase price of tokens
        tokens_bought = 0
        if sol_converted > 0:
            for i in range(active_bin_index):
                # Improved average price calculation
                bin_start_price = initial_price * (self.price_factor ** i)
                bin_end_price = initial_price * (self.price_factor ** (i + 1))
                avg_bin_price = (bin_start_price + bin_end_price) / 2
                tokens_bought += distribution[i] / avg_bin_price
        
        remaining_sol = initial_sol - sol_converted
        final_asset_value = (tokens_bought * final_price) + remaining_sol
        pnl_from_assets = final_asset_value - initial_sol

        # PnL from fees
        # Fees are proportional to liquidity in active bin
        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[min(active_bin_index, len(distribution)-1)]
        # Avoid division by zero if spot_liquidity_per_bin is 0
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