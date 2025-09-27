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

        # AIDEV-NOTE-GEMINI: Critical Business Logic for OOR (Out of Range).
        # This loop simulates the position's value over time, applying the unique OOR
        # logic specific to the SOL Decoder bot's 1-sided (SOL-only) entry strategy.
        #
        # Key Principles:
        # 1. 1-Sided Entry: The position is entered entirely with SOL.
        # 2. OOR Condition: For this strategy, OOR only occurs when the price moves
        #    ABOVE the upper bin range. A move below the range would trigger the Stop Loss first.
        # 3. OOR Value Lock: When OOR happens, the entire liquidity has been converted
        #    back to SOL. The position's value becomes "locked" at the initial SOL investment
        #    plus any fees accumulated up to that point. The position stops earning fees
        #    but its value in SOL no longer changes until the price re-enters the range.
        #
        # This implementation "bakes" the OOR effect directly into the generated timeline's
        # PnL values, making subsequent TP/SL/TLS checks much simpler as they don't need
        # to re-evaluate the OOR state.

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
                # AIDEV-NOTE-GEMINI: Value is locked to SOL principal + earned fees, per bot's strategy.
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


def simulate_position_exit_with_tls(position_data: List[Dict], tp_level: float, sl_level: float,
                                   tls_activation: float, tls_trail: float,
                                   initial_investment: float) -> Dict[str, Any]:
    """
    Simulates a position exit with TP, SL, and fixed-reference Trailing Stop Loss (TLS).
    AIDEV-NOTE-GEMINI: This is the centralized, authoritative implementation of the TLS exit logic.

    Args:
        position_data: Timeline data with pnl_pct, pnl_pct_high, pnl_pct_low.
        tp_level: Take profit level (%).
        sl_level: Stop loss level (%).
        tls_activation: TLS activation profit level (%).
        tls_trail: TLS trail distance from activation level (%).
        initial_investment: The initial investment amount in SOL.

    Returns:
        A dictionary with simulation exit results.
    """
    if not position_data:
        return {
            'exit_reason': 'NO_DATA', 'final_pnl': 0.0, 'final_pnl_pct': 0.0,
            'exit_price': 0.0, 'tls_activated': False, 'peak_pnl_reached': 0.0
        }

    # AIDEV-TLS-GEMINI: State tracking for the simulation lifetime.
    peak_pnl_achieved = 0.0
    tls_is_activated = False
    # AIDEV-TLS-GEMINI: The dynamic_sl starts as the original SL. It can only increase.
    dynamic_sl_level = -sl_level

    for point in position_data:
        pnl_high = point.get('pnl_pct_high', point['pnl_pct'])
        pnl_low = point.get('pnl_pct_low', point['pnl_pct'])

        # 1. Update the highest PnL achieved so far during this candle's lifetime.
        peak_pnl_achieved = max(peak_pnl_achieved, pnl_high)

        # 2. Check for TLS activation. This happens only once.
        if not tls_is_activated and peak_pnl_achieved >= tls_activation:
            tls_is_activated = True
            # AIDEV-TLS-GEMINI: CRITICAL LOGIC - The new SL is a fixed reference from the ACTIVATION point, not the peak.
            # This prevents the SL from creeping up too aggressively with every minor price spike.
            new_sl_from_tls = tls_activation - tls_trail
            dynamic_sl_level = max(dynamic_sl_level, new_sl_from_tls)

        # --- EXIT CONDITION CHECKS (IN ORDER OF PRIORITY) ---

        # A. Take Profit check (on the candle's high)
        if pnl_high >= tp_level:
            # AIDEV-NOTE-GEMINI: We assume the exit happens at the exact TP level for consistent PnL calculation.
            final_pnl_pct = tp_level
            exit_reason = 'TP'
            break

        # B. Stop Loss / Trailing Stop Loss check (on the candle's low)
        if pnl_low <= dynamic_sl_level:
            final_pnl_pct = dynamic_sl_level
            # AIDEV-TLS-GEMINI: The reason is 'TLS' only if the dynamic SL was improved by the TLS activation.
            exit_reason = 'TLS' if tls_is_activated and dynamic_sl_level > -sl_level else 'SL'
            break
    
    else: # This 'else' belongs to the 'for' loop, executing only if no 'break' occurred.
        # Position ran to the end of the data without hitting TP or SL/TLS.
        final_point = position_data[-1]
        final_pnl_pct = final_point['pnl_pct']
        exit_reason = 'END'
        point = final_point # Use the final point for exit price info

    final_pnl = initial_investment * (final_pnl_pct / 100.0)

    return {
        'exit_reason': exit_reason,
        'final_pnl': final_pnl,
        'final_pnl_pct': final_pnl_pct,
        'exit_price': point['price'],
        'tls_activated': tls_is_activated,
        'peak_pnl_reached': peak_pnl_achieved
    }