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
        Simulates position value over a timeline, correctly handling OOR state.
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
            current_price = price_point['close']
            
            if i < len(fee_data):
                accumulated_fees += fee_data[i]

            position_value = 0.0
            
            # Check for OOR condition
            is_currently_out_of_range = (min_price is not None and current_price < min_price) or \
                                        (max_price is not None and current_price > max_price)

            if not is_oor and is_currently_out_of_range:
                # First time hitting OOR: lock the value.
                # At OOR, we are 100% in SOL, so value is initial investment + fees.
                is_oor = True
                oor_value = initial_investment + accumulated_fees
                position_value = oor_value
            elif is_oor:
                # Already OOR, value is locked.
                position_value = oor_value
            else:
                # Still in range, calculate value dynamically.
                position_value = self.calculate_in_range_value(
                    position, initial_price, current_price, accumulated_fees
                )
            
            pnl_pct = ((position_value - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
            
            timeline.append({
                'timestamp': timestamp,
                'price': current_price,
                'position_value_sol': position_value,
                'pnl_pct': pnl_pct,
                'accumulated_fees': accumulated_fees
            })
            
        return timeline