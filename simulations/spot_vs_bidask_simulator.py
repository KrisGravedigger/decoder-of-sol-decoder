import math
import logging
from typing import List, Dict, Tuple, Optional
import pandas as pd
import numpy as np
from datetime import datetime

logger = logging.getLogger(__name__)

class SpotVsBidAskSimulator:
    """
    Runs Spot vs. Bid-Ask strategy simulations based on historical data.
    Implements a heuristic matrix (v4.3 - Refined) to model fee potential.
    """
    
    def __init__(self, bin_step: int, num_bins: int = 69, step_size: str = "UNKNOWN"):
        self.bin_step = bin_step
        self.step_size = step_size
        self.price_factor = 1 + self.bin_step / 10000
        bin_map = {"WIDE": 50, "MEDIUM": 20, "NARROW": 10, "SIXTYNINE": 69}
        self.num_bins = bin_map.get(step_size.upper(), num_bins)

    def _calculate_spot_distribution(self, initial_sol: float) -> List[float]:
        return [initial_sol / self.num_bins] * self.num_bins if self.num_bins > 0 else []

    def _calculate_bidask_distribution(self, initial_sol: float) -> List[float]:
        if self.num_bins <= 1: return [initial_sol] if self.num_bins == 1 else []
        beta = 2.0
        weights = [(i / (self.num_bins - 1))**beta + (1 - i / (self.num_bins - 1))**beta for i in range(self.num_bins)]
        total_weight = sum(weights)
        return [initial_sol * w / total_weight for w in weights] if total_weight > 0 else []

    def _get_active_bin_from_price_ratio(self, price_ratio: float) -> int:
        if price_ratio <= 1: return 0
        try:
            active_bin = math.floor(math.log(price_ratio) / math.log(self.price_factor))
        except (ValueError, ZeroDivisionError):
            return 0
        return min(active_bin, self.num_bins - 1)

    def _calculate_pnl_from_assets(self, distribution: List[float], price_ratio: float, 
                             initial_price: float, final_price: float, 
                             initial_sol: float) -> Tuple[float, int]:
        active_bin_index = self._get_active_bin_from_price_ratio(price_ratio)
        if not distribution: return 0.0, 0
        
        # DEEP DEBUG: Track every single calculation
        logger = logging.getLogger('DEEP_DEBUG')
        logger.setLevel(logging.DEBUG)
        
        logger.debug("="*80)
        logger.debug("ENTERING _calculate_pnl_from_assets")
        logger.debug(f"Input parameters:")
        logger.debug(f"  initial_sol: {initial_sol}")
        logger.debug(f"  initial_price: {initial_price:.15e}")
        logger.debug(f"  final_price: {final_price:.15e}")
        logger.debug(f"  price_ratio: {price_ratio}")
        logger.debug(f"  active_bin_index: {active_bin_index}")
        logger.debug(f"  num_bins: {len(distribution)}")
        logger.debug(f"  price_factor: {self.price_factor}")
        logger.debug(f"  bin_step: {self.bin_step}")
        
        sol_converted = sum(distribution[:active_bin_index])
        logger.debug(f"SOL converted (sum of first {active_bin_index} bins): {sol_converted}")
        
        final_value_of_all_tokens = 0
        if sol_converted > 0:
            logger.debug(f"\nCalculating token values for {active_bin_index} activated bins:")
            for i in range(min(active_bin_index, 5)):  # Show first 5 bins in detail
                # Price at which we buy in this bin
                avg_bin_price = initial_price * (self.price_factor ** (i + 0.5))
                
                logger.debug(f"\n  Bin {i}:")
                logger.debug(f"    SOL in bin: {distribution[i]}")
                logger.debug(f"    Price factor for bin: {self.price_factor ** (i + 0.5)}")
                logger.debug(f"    Avg bin price: {avg_bin_price:.15e} = {initial_price:.15e} * {self.price_factor ** (i + 0.5)}")
                
                if avg_bin_price > 0:
                    # Tokens bought calculation
                    tokens_in_bin = distribution[i] / avg_bin_price
                    logger.debug(f"    Tokens bought: {tokens_in_bin:.15e} = {distribution[i]} / {avg_bin_price:.15e}")
                    
                    # Final value calculation
                    final_value_of_tokens_in_bin = tokens_in_bin * final_price
                    logger.debug(f"    Final value: {final_value_of_tokens_in_bin:.15e} = {tokens_in_bin:.15e} * {final_price:.15e}")
                    
                    # Alternative calculation (should be identical)
                    bin_price_ratio = final_price / avg_bin_price
                    alt_final_value = distribution[i] * bin_price_ratio
                    logger.debug(f"    Alt calculation: {alt_final_value:.15e} = {distribution[i]} * ({final_price:.15e} / {avg_bin_price:.15e})")
                    
                    final_value_of_all_tokens += final_value_of_tokens_in_bin
            
            if active_bin_index > 5:
                logger.debug(f"\n  ... (showing only first 5 bins, {active_bin_index - 5} more bins processed)")
                # Still calculate the rest
                for i in range(5, active_bin_index):
                    avg_bin_price = initial_price * (self.price_factor ** (i + 0.5))
                    if avg_bin_price > 0:
                        tokens_in_bin = distribution[i] / avg_bin_price
                        final_value_of_tokens_in_bin = tokens_in_bin * final_price
                        final_value_of_all_tokens += final_value_of_tokens_in_bin
        
        remaining_sol = initial_sol - sol_converted
        logger.debug(f"\nRemaining SOL (not converted): {remaining_sol} = {initial_sol} - {sol_converted}")
        
        # Total final value is the value of all our tokens + the SOL we didn't spend
        final_asset_value = final_value_of_all_tokens + remaining_sol
        logger.debug(f"\nFinal calculations:")
        logger.debug(f"  Total token value: {final_value_of_all_tokens:.15e}")
        logger.debug(f"  Remaining SOL: {remaining_sol}")
        logger.debug(f"  Final asset value: {final_asset_value:.15e}")
        logger.debug(f"  Initial SOL: {initial_sol}")
        logger.debug(f"  PnL from assets: {final_asset_value - initial_sol:.15e}")
        logger.debug("="*80)
        
        pnl_from_assets = final_asset_value - initial_sol
        return pnl_from_assets, active_bin_index

    def _calculate_fee_multiplier(self, close_reason: str, open_ts: datetime, close_ts: datetime, 
                                price_history: List[Dict], penetration_depth: float) -> float:
        duration_hours = (close_ts - open_ts).total_seconds() / 3600
        
        if close_reason == 'TP': return 1.0
        if close_reason == 'OOR': return 0.7
        
        if close_reason == 'SL':
            if duration_hours < 3: return 0.8 if penetration_depth < 0.5 else 0.9
            elif duration_hours <= 6:
                if penetration_depth < 0.5: return 0.7
                elif penetration_depth < 0.75: return 1.0
                else: return 1.1
            else:
                if penetration_depth < 0.5: return 0.6
                elif penetration_depth < 0.75: return 0.9
                else: return 1.2
        
        if close_reason == 'LV':
            prices = [p['close'] for p in price_history if p.get('close') and p['close'] > 0]
            if not prices: return 1.0
            initial_price, final_price, peak_price = prices[0], prices[-1], max(prices)
            reversal_factor = (final_price - initial_price) / (peak_price - initial_price) if (peak_price - initial_price) != 0 else 1.0
            reversal_factor = max(0, min(1, reversal_factor))
            
            x, neutral_point = penetration_depth, 2/3
            base_multiplier = (1.0 - 1.125 * ((neutral_point - x)**2)) if x < neutral_point else (1.0 + 4.5 * ((x - neutral_point)**2))
            
            log_hours = np.log([1, 6, 144])
            mod_points = [0.3, 1.0, 2.0]
            log_duration = np.log(duration_hours) if duration_hours > 0 else -np.inf
            time_modifier = np.interp(log_duration, log_hours, mod_points, left=0.3, right=2.0)
            
            return 1.0 + (base_multiplier - 1.0) * time_modifier * reversal_factor

        return 1.0

    def run_all_simulations(self, investment_sol: float, pnl_sol: Optional[float], price_history: List[Dict], 
                      open_timestamp: datetime, close_timestamp: datetime, close_reason: str) -> Dict:
        # DEEP DEBUG: Log all inputs
        logger = logging.getLogger('DEEP_DEBUG')
        logger.setLevel(logging.DEBUG)
        
        logger.debug("\n" + "="*80)
        logger.debug("ENTERING run_all_simulations")
        logger.debug(f"Inputs:")
        logger.debug(f"  investment_sol: {investment_sol} (type: {type(investment_sol)})")
        logger.debug(f"  pnl_sol: {pnl_sol} (type: {type(pnl_sol)})")
        logger.debug(f"  open_timestamp: {open_timestamp}")
        logger.debug(f"  close_timestamp: {close_timestamp}")
        logger.debug(f"  close_reason: {close_reason}")
        logger.debug(f"  price_history length: {len(price_history)}")
        
        prices = [p['close'] for p in price_history if p.get('close') and p['close'] > 0]
        if len(prices) < 2:
            return {'error': 'Insufficient valid price points for simulation.'}
            
        initial_price, final_price = prices[0], prices[-1]
        price_ratio = final_price / initial_price if initial_price > 0 else 1.0
        
        logger.debug(f"\nPrice analysis:")
        logger.debug(f"  First 5 prices: {prices[:5]}")
        logger.debug(f"  Last 5 prices: {prices[-5:]}")
        logger.debug(f"  Initial price: {initial_price:.15e}")
        logger.debug(f"  Final price: {final_price:.15e}")
        logger.debug(f"  Price ratio: {price_ratio}")

        if pd.notna(pnl_sol):
            fee_budget = max(0, pnl_sol)
        else:
            fee_budget = investment_sol * 0.001

        # --- Step 1: Calculate PnL from asset value change (IL) for both strategies ---
        spot_dist = self._calculate_spot_distribution(investment_sol)
        pnl_assets_spot, active_bins_idx = self._calculate_pnl_from_assets(
            spot_dist, price_ratio, initial_price, final_price, investment_sol
        )
        
        bidask_dist = self._calculate_bidask_distribution(investment_sol)
        pnl_assets_bidask, _ = self._calculate_pnl_from_assets(
            bidask_dist, price_ratio, initial_price, final_price, investment_sol
        )

        # --- Step 2: Estimate PnL from fees using a unified, advanced heuristic ---
        
        # Base fee assumption: 0.1% of investment is a reasonable estimate of potential fees
        # if the price action is significant. This acts as a base "fee budget".
        # We no longer use the flawed pnl_sol from logs here.
        base_fee_budget = investment_sol * 0.001

        # The 'Spot' strategy is our baseline - we assume it captures this base fee budget.
        pnl_fees_spot = base_fee_budget
        
        # The 'Bid-Ask' strategy's fee potential is adjusted by the advanced heuristic multiplier,
        # which considers duration, close reason, and price movement dynamics.
        penetration_depth = active_bins_idx / self.num_bins if self.num_bins > 0 else 0
        fee_multiplier = self._calculate_fee_multiplier(
            close_reason, open_timestamp, close_timestamp, price_history, penetration_depth
        )
        
        pnl_fees_bidask = base_fee_budget * fee_multiplier

        results = {}
        for name, pnl_assets, pnl_fees in [('1-Sided Spot', pnl_assets_spot, pnl_fees_spot), ('1-Sided Bid-Ask', pnl_assets_bidask, pnl_fees_bidask)]:
            total_pnl = pnl_assets + pnl_fees
            results[name] = {
                'pnl_sol': total_pnl,
                'return_pct': (total_pnl / investment_sol) * 100 if investment_sol > 0 else 0,
                'pnl_from_fees': pnl_fees,
                'pnl_from_il': pnl_assets,
                'activated_bins': active_bins_idx,
                'step_size': self.step_size,
                'num_bins_used': self.num_bins
            }
        return results