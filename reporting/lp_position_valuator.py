"""
LP Position Valuator for TP/SL Optimizer Phase 3B

Calculates LP position value changes using an improved approximation model
for impermanent loss in concentrated liquidity systems.
"""

import logging
import math
from typing import Dict, List, Optional, Any
from datetime import datetime

logger = logging.getLogger(__name__)

from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Position


class LPPositionValuator:
    """
    Calculates LP position value changes using a refined approximation model for
    Impermanent Loss (IL) that considers the position's price range.
    """
    
    # AIDEV-NOTE-GEMINI: This is a key heuristic. It defines the maximum IL
    # percentage when the price reaches the opposite edge of the bin range.
    # 7.5% is a reasonable assumption for a moderately concentrated pool.
    # HUMAN-REVIEW: Adjust this value based on empirical data if available.
    MAX_IL_AT_EDGE = 0.075

    def __init__(self, strategy_type: str, step_size: str, bin_step: int = 100):
        self.strategy_type = strategy_type
        self.step_size = step_size
        
    def _calculate_il_reduction_factor(self, position: 'Position', current_price: float) -> float:
        """
        Calculates a reduction factor (0.0 to 1.0) based on an approximated IL.
        A factor of 1.0 means 0% IL, 0.925 means 7.5% IL.
        """
        min_price = getattr(position, 'min_bin_price', None)
        max_price = getattr(position, 'max_bin_price', None)

        if not all([min_price, max_price]) or min_price >= max_price:
            return 1.0 # No range data, assume no IL

        # For 1-sided entry, the reference point for zero IL is the top of the range.
        entry_price_assumption = max_price
        
        # 1. Calculate how "deep" the current price is within the range (0.0 to 1.0)
        total_range = max_price - min_price
        distance_from_entry = entry_price_assumption - current_price
        range_utilization = max(0, min(1, distance_from_entry / total_range))
        
        # 2. Apply a curve (quadratic) to model accelerating IL
        curve_factor = range_utilization ** 2
        
        # 3. Calculate the final IL percentage
        il_percentage = self.MAX_IL_AT_EDGE * curve_factor
        
        return 1.0 - il_percentage

    def calculate_in_range_value(self, position: 'Position', initial_price: float, current_price: float, 
                                 accumulated_fees: float) -> float:
        """
        Calculates the position value assuming the price is WITHIN the bin range.
        """
        initial_investment = position.initial_investment
        if initial_price <= 0:
            return initial_investment + accumulated_fees

        # 1. Calculate the value as if it were a simple "buy & hold"
        buy_and_hold_value = initial_investment * (current_price / initial_price)
        
        # 2. Calculate the IL reduction factor based on the price's position in the range
        il_reduction_factor = self._calculate_il_reduction_factor(position, current_price)

        # 3. Apply the reduction to get the final asset value
        asset_value = buy_and_hold_value * il_reduction_factor
        
        return asset_value + accumulated_fees

    def simulate_position_timeline(self, position: 'Position', price_data: List[Dict], 
                                 fee_data: List[float]) -> List[Dict]:
        """
        Simulates position value over a timeline, correctly handling OOR state and
        calculating PnL for high and low prices for accurate backtesting.
        """
        if not price_data:
            return []
            
        timeline = []
        accumulated_fees = 0.0
        initial_investment = position.initial_investment
        initial_price = price_data[0]['close']
        
        min_price = getattr(position, 'min_bin_price', None)
        max_price = getattr(position, 'max_bin_price', None)
        
        is_oor = False
        oor_value = 0.0

        for i, price_point in enumerate(price_data):
            timestamp = datetime.fromtimestamp(price_point['timestamp'])
            
            # Extract OCHL prices from the candle
            current_price = price_point['close']
            high_price = price_point['high']
            low_price = price_point['low']
            
            if i < len(fee_data):
                accumulated_fees += fee_data[i]

            position_value = 0.0
            position_value_high = 0.0
            position_value_low = 0.0
            
            # Check for OOR condition based on the closing price of the candle
            is_currently_out_of_range = (min_price is not None and current_price < min_price) or \
                                        (max_price is not None and current_price > max_price)

            if not is_oor and is_currently_out_of_range:
                # Transition to OOR: lock the value based on this candle's close
                is_oor = True
                oor_value = initial_investment + accumulated_fees
                position_value = oor_value
            elif is_oor:
                # Already OOR: value is locked in SOL terms
                position_value = oor_value
            else:
                # Still in range: calculate value dynamically for close, high, and low
                position_value = self.calculate_in_range_value(position, initial_price, current_price, accumulated_fees)
                position_value_high = self.calculate_in_range_value(position, initial_price, high_price, accumulated_fees)
                position_value_low = self.calculate_in_range_value(position, initial_price, low_price, accumulated_fees)

            if is_oor:
                # If OOR, high and low values are the same as the locked value
                position_value_high = position_value
                position_value_low = position_value
            
            # Calculate PnL percentages for all three price points
            pnl_pct = ((position_value - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
            pnl_pct_high = ((position_value_high - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
            pnl_pct_low = ((position_value_low - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
            
            timeline.append({
                'timestamp': timestamp,
                'price': current_price, # price still refers to 'close'
                'position_value_sol': position_value,
                'pnl_pct': pnl_pct,
                'pnl_pct_high': pnl_pct_high,
                'pnl_pct_low': pnl_pct_low,
                'accumulated_fees': accumulated_fees
            })
            
        return timeline