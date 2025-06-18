import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any

# --- Configuration ---
LOG_DIR = "input"
OUTPUT_CSV = "positions_to_analyze.csv"
MIN_PNL_THRESHOLD = 0.01  # Skip positions with PnL between -0.01 and +0.01 SOL

# Logging configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('LogExtractor')

# === Helper Classes ===

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

# === Main Parser Class ===

class LogParser:
    """Manages the entire log parsing process."""

    def __init__(self):
        """Initialize the log parser."""
        self.all_lines: List[str] = []
        self.active_positions: Dict[str, Position] = {}
        self.finalized_positions: List[Position] = []

    def _clean_ansi(self, text: str) -> str:
        """Remove ANSI escape sequences from text."""
        return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

    def _find_context_value(self, patterns: List[str], start_index: int, lookback: int) -> Optional[str]:
        """
        Find a value matching one of the patterns within a lookback window.
        
        Args:
            patterns: List of regex patterns to search for
            start_index: Starting line index
            lookback: Number of lines to look back
            
        Returns:
            First matching value found, or None
        """
        for i in range(start_index, max(-1, start_index - lookback), -1):
            for pattern in patterns:
                match = re.search(pattern, self._clean_ansi(self.all_lines[i]))
                if match: 
                    return match.group(1).strip()
        return None

    def _normalize_token_pair(self, text: Optional[str]) -> Optional[str]:
        """
        Extract and normalize token pair from text.
        
        Args:
            text: Text containing potential token pair
            
        Returns:
            Normalized token pair string or None
        """
        if not text: 
            return None
        match = re.search(r'([\w\s().-]+-SOL)', self._clean_ansi(text))
        return match.group(1).strip() if match else None

    def _parse_initial_investment(self, start_index: int, lookback: int, lookahead: int) -> Optional[float]:
        """
        Parse initial investment amount from log context.
        
        Version 5: Aggressive search for investment amount in forward-looking window.
        
        Args:
            start_index: Starting line index
            lookback: Lines to look back (unused in this version)
            lookahead: Lines to look ahead
            
        Returns:
            Initial investment amount in SOL or None
        """
        search_start = start_index
        search_end = min(len(self.all_lines), start_index + lookahead)

        for i in range(search_start, search_end):
            line = self._clean_ansi(self.all_lines[i])

            # Pattern 1: Most reliable - PnL line with "Start:"
            # Example: PnL: 0.05403 SOL (Return: +0.49%) | Start: 11.10968 SOL → Current: 11.16371 SOL
            if "PnL:" in line and "Start:" in line:
                match = re.search(r'Start:\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'PnL+Start' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)

            # Pattern 2: PnL line with "Initial"
            # Example: Pnl Calculation: ... - Initial 11.10968 SOL
            if "Pnl Calculation:" in line and "Initial" in line:
                match = re.search(r'Initial\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'Pnl Calculation+Initial' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)
            
            # Pattern 3: Position opening line
            if "Creating a position" in line:
                match = re.search(r'with\s*([\d\.]+)\s*SOL', line)
                if match:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'Creating+with' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)

        logger.warning(f"Could not find investment amount for position opened at line {start_index + 1}")
        return None
        
    def _parse_final_pnl(self, start_index: int, lookback: int) -> Optional[float]:
        """
        Parse final PnL from log context.
        
        Args:
            start_index: Starting line index
            lookback: Number of lines to look back
            
        Returns:
            Final PnL amount in SOL or None
        """
        result = self._parse_final_pnl_with_line_info(start_index, lookback)
        return result['pnl']

    def _parse_final_pnl_with_line_info(self, start_index: int, lookback: int) -> Dict[str, Any]:
        """
        Parse final PnL from log context with line number information.
        
        Args:
            start_index: Starting line index
            lookback: Number of lines to look back
            
        Returns:
            Dictionary with 'pnl' (float or None) and 'line_number' (int or None)
        """
        for i in range(start_index, max(-1, start_index - lookback), -1):
            line = self._clean_ansi(self.all_lines[i])
            if "PnL:" in line and "Return:" in line:
                match = re.search(r'PnL:\s*(-?\d+\.?\d*)\s*SOL', line)
                if match: 
                    pnl_value = round(float(match.group(1)), 5)
                    logger.debug(f"Found PnL value {pnl_value} at line {i + 1}: {line.strip()}")
                    return {'pnl': pnl_value, 'line_number': i + 1}
        
        logger.debug(f"No PnL found in lookback range {start_index + 1} to {max(1, start_index - lookback + 2)}")
        return {'pnl': None, 'line_number': None}

    def _process_open_event(self, timestamp: str, version: str, index: int):
        """
        Process a position opening event.
        
        Args:
            timestamp: Event timestamp
            version: Bot version
            index: Line index in log
        """
        token_pair = self._normalize_token_pair(
            self._find_context_value([r'TARGET POOL:\s*(.*-SOL)'], index, 50)
        )
        if not token_pair:
            logger.debug(f"Skipped opening at line {index + 1}, missing token pair.")
            return

        pos = Position(timestamp, version, index)
        pos.token_pair = token_pair
        
        pos.pool_address = self._find_context_value([
            r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
            r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
        ], index, 50)
        
        pos.actual_strategy = self._find_context_value([
            r'\[(Spot \(1-Sided\)|Bid-Ask \(1-Sided\)|Spot \(Wide\)|Bid-Ask \(Wide\))'
        ], index, 50) or "UNKNOWN"
        
        # CRITICAL CHANGE: Search for investment in wider forward-looking window
        pos.initial_investment = self._parse_initial_investment(index, 0, 100)
        
        self.active_positions[pos.position_id] = pos
        logger.info(f"Opened position: {pos.position_id} ({pos.token_pair}) | Inv: {pos.initial_investment} | Pool: {pos.pool_address}")

    def _process_close_event(self, timestamp: str, index: int):
        """
        Process a position closing event.
        
        Looks for the definitive closing pattern: "Closed" + "position and withdrew liquidity"
        which unambiguously indicates that a position has been actually closed (not just warned).
        
        Args:
            timestamp: Event timestamp
            index: Line index in log
        """
        logger.info(f"Processing close event at line {index + 1}")
        line_clean = self._clean_ansi(self.all_lines[index])
        logger.info(f"Cleaned line: {line_clean.strip()}")
        
        # Check for definitive closing pattern
        if not ("Closed" in line_clean and "position and withdrew liquidity" in line_clean):
            return
        
        # Extract token pair directly from the closing line
        token_match = re.search(r'Closed\s+([A-Za-z0-9\-_]+\-SOL)', line_clean)
        if not token_match:
            logger.debug(f"Found closing pattern at line {index + 1}, but could not extract token pair.")
            return
        
        closed_pair = token_match.group(1)
        
        # Find matching active position for this token pair
        matching_position = next((pos for pos_id, pos in self.active_positions.items() 
                                if pos.token_pair == closed_pair), None)
        
        if matching_position:
            pos = matching_position
            pos.close_timestamp = timestamp
            pos.close_reason = "position_closed"  # Generic reason since we have definitive closing
            pnl_result = self._parse_final_pnl_with_line_info(index, 20)
            pos.final_pnl = pnl_result['pnl']
            
            self.finalized_positions.append(pos)
            del self.active_positions[pos.position_id]
            pnl_line_info = f" | PnL found at line {pnl_result['line_number']}" if pnl_result['line_number'] else " | PnL not found"
            logger.info(f"Closed position: {pos.position_id} ({pos.token_pair}) | Close detected at line {index + 1} | Reason: {pos.close_reason} | PnL: {pos.final_pnl}{pnl_line_info}")
        else:
            logger.debug(f"Found closing for {closed_pair} at line {index + 1}, but no active position found for this pair.")

    def _process_close_event_without_timestamp(self, index: int):
        """
        Process a position closing event that doesn't have timestamp in the line.
        
        Args:
            index: Line index in log
        """
        logger.info(f"Processing close event at line {index + 1}")
        line_clean = self._clean_ansi(self.all_lines[index])
        logger.info(f"Cleaned line: {line_clean.strip()}")
        
        # Extract token pair directly from the closing line
        token_match = re.search(r'Closed\s+([A-Za-z0-9\-_]+\-SOL)', line_clean)
        if not token_match:
            logger.debug(f"Found closing pattern at line {index + 1}, but could not extract token pair.")
            return
        
        closed_pair = token_match.group(1)
        
        # Find matching active position for this token pair
        matching_position = next((pos for pos_id, pos in self.active_positions.items() 
                                if pos.token_pair == closed_pair), None)
        
        if matching_position:
            pos = matching_position
            # Use estimated timestamp based on surrounding lines or default
            pos.close_timestamp = "UNKNOWN"  # We'll improve this later
            pos.close_reason = "position_closed"
            pnl_result = self._parse_final_pnl_with_line_info(index, 20)
            pos.final_pnl = pnl_result['pnl']
            
            self.finalized_positions.append(pos)
            del self.active_positions[pos.position_id]
            pnl_line_info = f" | PnL found at line {pnl_result['line_number']}" if pnl_result['line_number'] else " | PnL not found"
            logger.info(f"Closed position: {pos.position_id} ({pos.token_pair}) | Close detected at line {index + 1} | Reason: {pos.close_reason} | PnL: {pos.final_pnl}{pnl_line_info}")
        else:
            logger.debug(f"Found closing for {closed_pair} at line {index + 1}, but no active position found for this pair.")
    
    def run(self, log_dir: str) -> List[Dict[str, Any]]:
        """
        Run the complete log parsing process.
        
        Args:
            log_dir: Directory containing log files
            
        Returns:
            List of validated position dictionaries
        """
        log_files = sorted([f for f in os.listdir(log_dir) if f.startswith("app") and ".log" in f])
        if not log_files:
            logger.warning(f"No log files found in {log_dir}")
            return []

        for f in log_files: 
            self.all_lines.extend(open(os.path.join(log_dir, f), 'r', encoding='utf-8', errors='ignore'))
        logger.info(f"Processing {len(self.all_lines)} lines from {len(log_files)} log files.")

        for i, line_content in enumerate(self.all_lines):
            # Check for closing pattern first (doesn't require timestamp)
            if "Closed" in line_content and "position and withdrew liquidity" in line_content:
                logger.info(f"Found closing pattern at line {i + 1}: {line_content.strip()}")
                # For closing events, we'll extract timestamp differently or use a default
                self._process_close_event_without_timestamp(i)
                continue
            
            # Regular timestamp-based processing
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', self._clean_ansi(line_content))
            if not timestamp_match: 
                continue
            
            timestamp = timestamp_match.group(1)
            version_match = re.search(r'(v[\d.]+)', self._clean_ansi(line_content))
            version = version_match.group(1) if version_match else "vUNKNOWN"

            if "Creating a position" in line_content: 
                self._process_open_event(timestamp, version, i)

        # Process remaining active positions
        for pos_id, pos in self.active_positions.items():
            pos.close_reason = "active_at_log_end"
            self.finalized_positions.append(pos)
            logger.warning(f"Position {pos_id} ({pos.token_pair}) remained active at end of logs.")

        # Validate and filter positions
        validated_positions = []
        skipped_low_pnl = 0
        
        for pos in self.finalized_positions:
            errors = pos.get_validation_errors()
            if errors:
                logger.warning(f"Rejected position {pos.position_id} ({pos.token_pair}). Errors: {', '.join(errors)}")
                continue
                
            # Skip positions with insignificant PnL
            if pos.final_pnl is not None and abs(pos.final_pnl) < MIN_PNL_THRESHOLD:
                logger.debug(f"Skipped position {pos.position_id} ({pos.token_pair}) - PnL {pos.final_pnl} SOL below threshold {MIN_PNL_THRESHOLD}")
                skipped_low_pnl += 1
                continue
                
            validated_positions.append(pos.to_csv_row())
        
        # Debug: Count potential closing patterns
        closing_pattern_count = sum(1 for line in self.all_lines if "Closed" in line and "position and withdrew liquidity" in line)
        logger.info(f"Found {closing_pattern_count} lines matching closing pattern in total.")

        logger.info(f"Found {len(self.finalized_positions)} positions. {len(validated_positions)} have complete data for analysis. {skipped_low_pnl} skipped due to low PnL (< {MIN_PNL_THRESHOLD} SOL).")
        return validated_positions

def run_extraction(log_dir: str = LOG_DIR, output_csv: str = OUTPUT_CSV) -> bool:
    """
    Run the complete log extraction process.
    
    Args:
        log_dir: Directory containing log files (default: "input")
        output_csv: Output CSV file path (default: "positions_to_analyze.csv")
        
    Returns:
        True if extraction successful, False otherwise
    """
    logger.info("Starting data extraction from logs...")
    os.makedirs(log_dir, exist_ok=True)
    
    parser = LogParser()
    extracted_data = parser.run(log_dir)
    
    if not extracted_data:
        logger.error("Failed to extract any complete positions. CSV file will not be created.")
        return False
        
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=extracted_data[0].keys())
            writer.writeheader()
            writer.writerows(extracted_data)
        logger.info(f"Successfully saved {len(extracted_data)} positions to file {output_csv}")
        return True
    except Exception as e:
        logger.error(f"Error writing to CSV file {output_csv}: {e}")
        return False

if __name__ == "__main__":
    run_extraction()