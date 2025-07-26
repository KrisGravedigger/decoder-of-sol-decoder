from typing import Optional, List, Dict, Any


class Position:
    """Stores the state of a single, active trading position.
    
    Note: Only one position per token pair can be active at any given time.
    """
    
    def __init__(self, open_timestamp: str, bot_version: str, open_line_index: int, wallet_id: str = "unknown_wallet", source_file: str = "unknown_file"):
        """
        Initialize a new position.
        
        Args:
            open_timestamp: Timestamp when position was opened
            bot_version: Version of the trading bot
            line_index: Line number in log file where position was opened
        """
        self.open_timestamp = open_timestamp
        self.bot_version = bot_version
        self.open_line_index = open_line_index
        self.position_id = f"pos_{open_timestamp.replace('/', '-').replace(':', '-')}_{open_line_index}"
        self.token_pair: Optional[str] = None
        self.pool_address: Optional[str] = None
        self.initial_investment: Optional[float] = None
        self.actual_strategy: str = "UNKNOWN"
        self.close_timestamp: Optional[str] = None
        self.close_reason: Optional[str] = None
        self.final_pnl: Optional[float] = None
        self.close_line_index: Optional[int] = None
        self.retry_count: int = 0  # Track retry attempts
        self.wallet_id = wallet_id
        self.source_file = source_file
        self.initial_investment: Optional[float] = None
        self.final_pnl: Optional[float] = None
        self.take_profit: Optional[float] = None
        self.stop_loss: Optional[float] = None
        
        # PHASE 3A: Peak PnL tracking from logs
        self.max_profit_during_position: Optional[float] = None  # Maximum % profit during lifetime
        self.max_loss_during_position: Optional[float] = None    # Maximum % loss during lifetime  
        self.total_fees_collected: Optional[float] = None        # Total fees in SOL
        
        # AIDEV-PHASE-C-PLACEHOLDER: Post-close analysis fields (Phase 3B)
        # self.max_profit_post_close: Optional[float] = None
        # self.max_loss_post_close: Optional[float] = None
        # self.optimal_exit_time: Optional[datetime] = None
        # self.missed_opportunity_pct: Optional[float] = None

    @property
    def universal_position_id(self) -> str:
        """
        Universal position identifier across files based on pool_address + open_timestamp.
        
        This identifier allows tracking the same position across multiple log files,
        enabling proper deduplication and position completion tracking.
        
        Returns:
            str: Universal identifier in format "pool_address_open_timestamp"
        """
        return f"{self.pool_address}_{self.open_timestamp}"

    def is_context_complete(self) -> bool:
        """Check if position has complete context information."""
        return bool(self.token_pair and self.token_pair != "UNKNOWN-SOL")
    
    def is_position_complete(self) -> bool:
        """
        Check if position is complete (has close information).
        
        Returns:
            bool: True if position has close_timestamp and close_reason != "active_at_log_end"
        """
        return (self.close_timestamp is not None and 
                self.close_reason is not None and 
                self.close_reason != "active_at_log_end")

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors for this position."""
        errors = []
        if not self.token_pair: 
            errors.append("Missing token_pair")
        if not self.open_timestamp: 
            errors.append("Missing open_timestamp")
        if not self.pool_address: 
            errors.append("Missing pool_address")
        if not self.initial_investment: 
            errors.append("Missing investment_sol")
        if self.close_reason != "active_at_log_end" and not self.close_timestamp: 
            errors.append("Missing close_timestamp")
        return errors

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert position data to a dictionary for CSV export."""
        return {
            "position_id": self.position_id,
            "wallet_id": self.wallet_id,
            "source_file": self.source_file,
            "token_pair": self.token_pair,
            "pool_address": self.pool_address,
            "strategy_raw": self.actual_strategy,
            # AIDEV-NOTE-GEMINI: Added take_profit and stop_loss to the CSV output.
            "takeProfit": self.take_profit,
            "stopLoss": self.stop_loss,
            
            # PHASE 3A: Peak PnL backtest fields
            "max_profit_during_position": self.max_profit_during_position,
            "max_loss_during_position": self.max_loss_during_position,
            "total_fees_collected": self.total_fees_collected,
            
            "investment_sol": self.initial_investment,
            "pnl_sol": self.final_pnl,
            "open_timestamp": self.open_timestamp,
            "close_timestamp": self.close_timestamp,
            "close_reason": self.close_reason,
            "bot_version": self.bot_version,
            "retry_count": self.retry_count,
            "open_line_index": self.open_line_index,
            "close_line_index": self.close_line_index
        }