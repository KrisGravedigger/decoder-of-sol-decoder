"""
Fee Simulator for TP/SL Optimizer Phase 3B

Simulates fee accumulation for post-close periods using actual position fee rates.
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from core.models import Position

logger = logging.getLogger(__name__)


class FeeSimulator:
    """
    Simulate fee accumulation for post-close periods using actual historical fee rates.
    """
    
    def __init__(self, config: Dict):
        """
        Initialize fee simulator.
        
        Args:
            config: Configuration dictionary from portfolio_config.yaml
        """
        self.config = config
        
    def calculate_fee_allocation(self, position: 'Position', 
                               position_volume_data: List[Dict],
                               post_close_volume_data: List[Dict]) -> List[float]:
        """
        Calculate fee allocation for post-close simulation based on actual position performance.
        
        Algorithm:
        1. Calculate actual fee rate from position: fee_rate = total_fees / position_volume
        2. Apply same fee rate to post-close volume: fees = volume * fee_rate
        3. Return fees per candle
        
        Args:
            position: Position object with total_fees_collected
            position_volume_data: Volume data during position lifetime
            post_close_volume_data: Volume data for post-close period
            
        Returns:
            List of fees per candle for simulation
        """
        # Get total fees collected during position lifetime
        total_fees_collected = getattr(position, 'total_fees_collected', None)
        
        if total_fees_collected is None or total_fees_collected <= 0:
            logger.warning(f"No fee data available for position {position.position_id}")
            return [0.0] * len(post_close_volume_data)
        
        # Calculate total volume during position lifetime
        position_total_volume = sum(d.get('volume', 0) for d in position_volume_data)
        
        if position_total_volume <= 0:
            logger.warning(f"No volume data during position lifetime for {position.position_id}")
            return [0.0] * len(post_close_volume_data)
        
        # Calculate actual fee rate from this specific position
        actual_fee_rate = total_fees_collected / position_total_volume
        
        logger.debug(f"Position {position.position_id}: "
                    f"collected {total_fees_collected:.4f} SOL fees on "
                    f"{position_total_volume:.0f} volume = "
                    f"{actual_fee_rate:.6f} fee rate")
        
        # Apply the same fee rate to post-close volume
        allocated_fees = []
        for candle_data in post_close_volume_data:
            candle_volume = candle_data.get('volume', 0)
            candle_fee = candle_volume * actual_fee_rate
            allocated_fees.append(candle_fee)
        
        total_post_close_fees = sum(allocated_fees)
        logger.debug(f"Post-close simulation: estimated {total_post_close_fees:.4f} SOL "
                    f"additional fees from {sum(d.get('volume', 0) for d in post_close_volume_data):.0f} volume")
        
        return allocated_fees
    
    def estimate_fee_rate_from_position(self, position: 'Position', position_volume_data: List[Dict]) -> float:
        """
        Calculate the actual fee rate from a position's historical performance.
        
        Args:
            position: Position with total_fees_collected
            position_volume_data: Historical volume data during position lifetime
            
        Returns:
            Actual fee rate as decimal (e.g., 0.0005 = 0.05%)
        """
        total_fees = getattr(position, 'total_fees_collected', 0.0)
        
        if not total_fees or total_fees <= 0:
            logger.warning(f"No fee data for position {position.position_id}")
            return 0.0
            
        # Calculate total volume during position lifetime
        total_volume = sum(d.get('volume', 0) for d in position_volume_data)
        
        if total_volume <= 0:
            logger.warning(f"No volume data for position {position.position_id}")
            return 0.0
            
        # Calculate actual fee rate
        fee_rate = total_fees / total_volume
        
        # Log for transparency
        logger.info(f"Position {position.position_id} actual fee rate: {fee_rate:.6f} "
                   f"({fee_rate*100:.4f}%) from {total_fees:.4f} SOL fees on "
                   f"{total_volume:.0f} volume")
        
        return fee_rate