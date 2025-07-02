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
            errors.append("Missing initial_investment_sol")
        if self.close_reason != "active_at_log_end" and not self.close_timestamp: 
            errors.append("Missing close_timestamp")
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
            "wallet_id": self.wallet_id,
            "source_file": self.source_file,
            "strategy_instance_id": "",  # Empty, will be filled by strategy_instance_detector
        }