import math
from typing import List, Dict, Tuple, Optional

class StrategyAnalyzer:
    """Runs strategy simulations based on historical data."""
    
    def __init__(self, bin_step: int, num_bins: int = 69):
        """
        Initialize the strategy analyzer.
        
        Args:
            bin_step: Price step between bins in basis points
            num_bins: Number of bins in the liquidity distribution
        """
        self.bin_step = bin_step
        self.num_bins = num_bins
        self.price_factor = 1 + self.bin_step / 10000

    def _calculate_spot_distribution(self, initial_sol: float) -> List[float]:
        """
        Calculate uniform liquidity distribution (Spot strategy).
        
        Args:
            initial_sol: Initial SOL investment amount
            
        Returns:
            List of SOL amounts per bin
        """
        return [initial_sol / self.num_bins] * self.num_bins

    def _calculate_bidask_distribution(self, initial_sol: float) -> List[float]:
        """
        Calculate progressive liquidity distribution (Bid-Ask strategy).
        More liquidity at the edges.
        
        Args:
            initial_sol: Initial SOL investment amount
            
        Returns:
            List of SOL amounts per bin
        """
        weights = [
            math.exp((i - self.num_bins / 2)**2 / (2 * (self.num_bins / 3)**2)) 
            for i in range(self.num_bins)
        ]
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
        results['Spot (1-Sided)'] = self._simulate_1sided(
            spot_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        results['Bid-Ask (1-Sided)'] = self._simulate_1sided(
            bidask_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        results['Spot (Wide)'] = self._simulate_wide(
            spot_distribution, price_ratio, initial_price, final_price, initial_sol, estimated_total_fees
        )
        results['Bid-Ask (Wide)'] = self._simulate_wide(
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
        
        # PnL from asset value change (IL)
        # We sell SOL for tokens as price rises
        sol_converted = sum(distribution[:active_bin_index])
        
        # Average purchase price of tokens
        tokens_bought = 0
        if sol_converted > 0:
            for i in range(active_bin_index):
                bin_price = initial_price * (self.price_factor ** (i + 0.5))
                tokens_bought += distribution[i] / bin_price
        
        remaining_sol = initial_sol - sol_converted
        final_asset_value = (tokens_bought * final_price) + remaining_sol
        pnl_from_assets = final_asset_value - initial_sol

        # PnL from fees
        # Fees are proportional to liquidity in active bin
        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[active_bin_index]
        # Avoid division by zero if spot_liquidity_per_bin is 0
        liquidity_ratio = active_bin_liquidity / spot_liquidity_per_bin if spot_liquidity_per_bin > 0 else 1.0
        
        pnl_from_fees = fee_budget * liquidity_ratio
        
        total_pnl = pnl_from_assets + pnl_from_fees
        
        return {
            'pnl_sol': total_pnl,
            'return_pct': (total_pnl / initial_sol) * 100,
            'pnl_from_fees': pnl_from_fees,
            'pnl_from_il': pnl_from_assets,
            'activated_bins': active_bin_index
        }

    def _simulate_wide(self, distribution: List[float], price_ratio: float, 
                      initial_price: float, final_price: float, 
                      initial_sol: float, fee_budget: float) -> Dict:
        """
        Simulate Wide entry (50/50 value split at start).
        
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
        center_bin_index = self.num_bins // 2
        
        # Initial state: half value in SOL, half in tokens
        initial_sol_half = initial_sol / 2
        initial_tokens_value = initial_sol / 2
        initial_tokens = initial_tokens_value / initial_price
        
        # HODL value (holding 50/50 without LP)
        hodl_value = (initial_tokens * final_price) + initial_sol_half
        
        # LP value (with IL consideration)
        lp_value = 2 * math.sqrt(initial_tokens * final_price * initial_sol_half)  # Simplified LP value formula
        
        pnl_from_assets = lp_value - initial_sol

        # PnL from fees
        # Fees are proportional to liquidity in active bin
        active_bin_index = center_bin_index + self._get_active_bin_from_price_ratio(price_ratio) - (self.num_bins//2 if price_ratio < 1 else 0)
        active_bin_index = max(0, min(active_bin_index, self.num_bins - 1))

        spot_liquidity_per_bin = initial_sol / self.num_bins
        active_bin_liquidity = distribution[active_bin_index]
        liquidity_ratio = active_bin_liquidity / spot_liquidity_per_bin if spot_liquidity_per_bin > 0 else 1.0
        
        pnl_from_fees = fee_budget * liquidity_ratio
        
        total_pnl = pnl_from_assets + pnl_from_fees

        return {
            'pnl_sol': total_pnl,
            'return_pct': (total_pnl / initial_sol) * 100,
            'pnl_from_fees': pnl_from_fees,
            'pnl_from_il': pnl_from_assets,
        }