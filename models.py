from typing import Optional, List, Dict, Any


class Position:
    """Stores the state of a single, active trading position.
    
    Note: Only one position per token pair can be active at any given time.
    """
    
    def __init__(self, open_timestamp: str, bot_version: str, line_index: int):
        """
        Initialize a new position.
        
        Args:
            open_timestamp: Timestamp when position was opened
            bot_version: Version of the trading bot
            line_index: Line number in log file where position was opened
        """
        self.open_timestamp = open_timestamp
        self.bot_version = bot_version
        self.open_line_index = line_index
        self.position_id = f"pos_{open_timestamp.replace('/', '-').replace(':', '-')}_{line_index}"
        self.token_pair: Optional[str] = None
        self.pool_address: Optional[str] = None
        self.initial_investment: Optional[float] = None
        self.actual_strategy: str = "UNKNOWN"
        self.close_timestamp: Optional[str] = None
        self.close_reason: Optional[str] = None
        self.final_pnl: Optional[float] = None
        self.close_line_index: Optional[int] = None
        self.retry_count: int = 0  # Track retry attempts

    def is_context_complete(self) -> bool:
        """Check if position has complete context information."""
        return bool(self.token_pair and self.token_pair != "UNKNOWN-SOL")

    def get_validation_errors(self) -> List[str]:
        """Get list of validation errors for this position."""
        errors = []
        if not self.pool_address: 
            errors.append("Missing pool_address")
        if not self.initial_investment: 
            errors.append("Missing initial_investment_sol")
        if not self.close_timestamp: 
            errors.append("Missing close_timestamp (position still active)")
        return errors

    def to_csv_row(self) -> Dict[str, Any]:
        """Convert position to CSV row dictionary."""
        return {
            "position_id": self.position_id, 
            "token_pair": self.token_pair,
            "pool_address": self.pool_address, 
            "open_timestamp": self.open_timestamp,
            "close_timestamp": self.close_timestamp, 
            "initial_investment_sol": self.initial_investment,
            "final_pnl_sol_from_log": self.final_pnl, 
            "actual_strategy_from_log": self.actual_strategy,
            "close_reason": self.close_reason, 
            "bot_version": self.bot_version,
        }