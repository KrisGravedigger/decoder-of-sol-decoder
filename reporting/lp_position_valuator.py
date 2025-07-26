"""
LP Position Valuator for TP/SL Optimizer Phase 3B

Calculates LP position value changes using mathematical formulas for
impermanent loss and concentrated liquidity systems.
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
    Calculate LP position value changes using mathematical formulas.
    Implements accurate Impermanent Loss calculations for concentrated liquidity.
    """
    
    def __init__(self, strategy_type: str, step_size: str, bin_step: int = 100):
        """
        Initialize LP position valuator.
        
        Args:
            strategy_type: "Bid-Ask" or "Spot"
            step_size: "WIDE", "MEDIUM", "NARROW", "SIXTYNINE"
            bin_step: Bin step parameter (default 100)
        """
        self.strategy_type = strategy_type
        self.step_size = step_size
        self.bin_step = bin_step
        self.price_factor = 1 + bin_step / 10000
        
        # Map step size to number of bins
        self.bin_map = {
            "WIDE": 50,
            "MEDIUM": 20, 
            "NARROW": 10,
            "SIXTYNINE": 69
        }
        self.num_bins = self.bin_map.get(step_size.upper(), 69)
        
    def calculate_position_value_at_price(self, position: 'Position', initial_price: float, current_price: float, 
                                        accumulated_fees: float) -> float:
        """
        Calculate LP position value at specific price point.
        
        Uses mathematical formulas from research:
        - Impermanent Loss for price movement impact
        - Concentrated liquidity considerations for bin-based strategies
        - Fee accumulation on top of asset value changes
        
        Args:
            position: Position object with investment_sol, pool_address
            current_price: Current token price in SOL
            accumulated_fees: Total fees accumulated up to this point
            
        Returns:
            Total position value in SOL
        """
        # Get initial investment and price
        initial_investment = position.initial_investment
        
        # For this implementation, we need the initial price when position was opened
        # This would ideally come from the first price point in position's price history
        # For now, we'll use a simplified approach
        
        # Calculate price ratio (we'd need initial price from position data)
        # Placeholder: assume we have access to initial price
        if initial_price <= 0:
            logger.warning(f"Invalid initial price for position {position.position_id}")
            return position.initial_investment + accumulated_fees
                
        price_ratio = current_price / initial_price
        
        if initial_price <= 0:
            logger.warning(f"Invalid initial price for position {position.position_id}")
            return initial_investment + accumulated_fees
            
        price_ratio = current_price / initial_price
        
        # Calculate impermanent loss using standard formula
        # IL = (2√k)/(k + 1) - 1, where k = price_ratio
        k = price_ratio
        impermanent_loss_factor = (2 * math.sqrt(k)) / (k + 1) - 1
        
        # For concentrated liquidity, IL is amplified
        # Using simplified model for bin-based systems
        concentration_factor = self._calculate_concentration_factor()
        amplified_il = impermanent_loss_factor * concentration_factor
        
        # Calculate asset value after IL
        asset_value = initial_investment * (1 + amplified_il)
        
        # Total position value includes assets + accumulated fees
        total_value = asset_value + accumulated_fees
        
        logger.debug(f"Position value calculation: price_ratio={price_ratio:.4f}, "
                    f"IL={impermanent_loss_factor:.4f}, amplified_IL={amplified_il:.4f}, "
                    f"asset_value={asset_value:.4f}, fees={accumulated_fees:.4f}, "
                    f"total={total_value:.4f}")
        
        return total_value
        
    def _calculate_concentration_factor(self) -> float:
        """
        Calculate concentration factor based on strategy and bin configuration.
        
        Concentrated positions experience amplified IL compared to full-range positions.
        """
        # Base concentration factors by step size
        concentration_factors = {
            "WIDE": 2.0,      # 2x amplification
            "MEDIUM": 3.0,    # 3x amplification  
            "NARROW": 4.0,    # 4x amplification
            "SIXTYNINE": 1.5  # 1.5x amplification
        }
        
        base_factor = concentration_factors.get(self.step_size.upper(), 2.0)
        
        # Bid-Ask strategies have additional concentration due to U-shaped distribution
        if self.strategy_type == "Bid-Ask":
            base_factor *= 1.2
            
        return base_factor
        
    def simulate_position_timeline(self, position: 'Position', price_data: List[Dict], 
                                 fee_data: List[float]) -> List[Dict]:
        """
        Simulate position value changes over extended timeline.
        
        Args:
            position: Position object
            price_data: List of price points with timestamp and close price
            fee_data: List of fees per candle (same length as price_data)
            
        Returns:
            List of {
                'timestamp': datetime,
                'price': float,
                'position_value_sol': float,
                'pnl_pct': float,
                'accumulated_fees': float
            }
        """
        if not price_data:
            return []
            
        timeline = []
        accumulated_fees = 0.0
        initial_investment = position.initial_investment
        
        for i, price_point in enumerate(price_data):
            timestamp = datetime.fromtimestamp(price_point['timestamp'])
            current_price = price_point['close']
            
            # Accumulate fees up to this point
            if i < len(fee_data):
                accumulated_fees += fee_data[i]
                
            # Calculate position value at this price
            # The initial price is the 'close' price of the first data point
            initial_price = price_data[0]['close']

            position_value = self.calculate_position_value_at_price(
                position, initial_price, current_price, accumulated_fees
            )
            
            # Calculate PnL percentage
            pnl_pct = ((position_value - initial_investment) / initial_investment * 100) if initial_investment > 0 else 0
            
            timeline.append({
                'timestamp': timestamp,
                'price': current_price,
                'position_value_sol': position_value,
                'pnl_pct': pnl_pct,
                'accumulated_fees': accumulated_fees
            })
            
        return timeline