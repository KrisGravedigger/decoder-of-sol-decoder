import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any

# === MAIN DEBUG CONFIGURATION ===
# AIDEV-NOTE-CLAUDE: Master debug controls - these override settings in debug_analyzer.py
DEBUG_ENABLED = False                    # Master switch for all debug features
DEBUG_LEVEL = "DEBUG"                   # "DEBUG" for detailed logs, "INFO" for standard logs
CONTEXT_EXPORT_ENABLED = True          # Enable/disable context export completely
DETAILED_POSITION_LOGGING = True       # Enable/disable detailed position event logging

# Import debug functionality
from debug_analyzer import DebugAnalyzer

# --- Configuration ---
LOG_DIR = "input"
OUTPUT_CSV = "positions_to_analyze.csv"
CONTEXT_EXPORT_FILE = "close_contexts_analysis.txt"
MIN_PNL_THRESHOLD = 0.01  # Skip positions with PnL between -0.01 and +0.01 SOL

# Logging configuration
log_level = logging.DEBUG if (DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
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
        self.close_line_index: Optional[int] = None  # AIDEV-NOTE-CLAUDE: Added for context export

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
        # AIDEV-NOTE-CLAUDE: Pass main debug settings to analyzer
        self.debug_analyzer = DebugAnalyzer(
            debug_enabled=DEBUG_ENABLED,
            context_export_enabled=CONTEXT_EXPORT_ENABLED
        )

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

    def _extract_close_timestamp(self, close_line_index: int) -> str:
        """
        Extract timestamp from close event context.
        
        Args:
            close_line_index: Line index where close was detected
            
        Returns:
            Timestamp string or "UNKNOWN" if not found
        """
        # Try to extract timestamp from close line itself
        close_line = self._clean_ansi(self.all_lines[close_line_index])
        timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', close_line)
        if timestamp_match:
            if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from close line {close_line_index + 1}")
            return timestamp_match.group(1)
        
        # Look for timestamp in nearby lines (prefer lines before close)
        search_range = 10  # Look 10 lines before and after
        
        # First search backwards (more likely to have relevant timestamp)
        for i in range(close_line_index - 1, max(-1, close_line_index - search_range), -1):
            line = self._clean_ansi(self.all_lines[i])
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                    logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (backward search)")
                return timestamp_match.group(1)
        
        # Then search forward if nothing found backward
        for i in range(close_line_index + 1, min(len(self.all_lines), close_line_index + search_range)):
            line = self._clean_ansi(self.all_lines[i])
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
            if timestamp_match:
                if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                    logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (forward search)")
                return timestamp_match.group(1)
        
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            logger.debug(f"No timestamp found in {search_range} lines around close at line {close_line_index + 1}")
        return "UNKNOWN"

    def _parse_strategy_from_context(self, start_index: int, lookback: int, lookahead: int = 30) -> str:
        """
        Parse strategy from log context with improved pattern matching.
        
        Args:
            start_index: Starting line index
            lookback: Number of lines to look back
            lookahead: Number of lines to look ahead
            
        Returns:
            Strategy string: "Spot (1-Sided)", "Bid-Ask (Wide)", etc. or "UNKNOWN"
        """
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            logger.debug(f"Parsing strategy from line {start_index + 1}, looking back {lookback} lines and ahead {lookahead} lines")
        
        # Search both backward and forward
        search_start = max(0, start_index - lookback)
        search_end = min(len(self.all_lines), start_index + lookahead)
        
        for i in range(search_start, search_end):
            line = self._clean_ansi(self.all_lines[i])
            
            # Dummy operation to maintain timing
            if ("spot" in line.lower() or "bid" in line.lower() or "strategy" in line.lower()):
                _ = line.strip()  # Force evaluation without logging
            
            # Pattern 1: [Spot (1-Sided)/... or [Bid-Ask (1-Sided)/...
                strategy_match = re.search(r'\[(Spot|Bid-Ask) \(1-Sided\)', line)
                if strategy_match:
                    strategy_type = strategy_match.group(1)  # "Spot" or "Bid-Ask"
                    
                    # Check for WIDE in Step Size
                    if "Step Size:WIDE" in line:
                        result = f"{strategy_type} (Wide)"
                        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                            logger.debug(f"Found strategy '{result}' at line {i + 1} (bracket format)")
                        return result
                    else:
                        result = f"{strategy_type} (1-Sided)"
                        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                            logger.debug(f"Found strategy '{result}' at line {i + 1} (bracket format)")
                        return result
                
                # Pattern 2: "using the spot-onesided strategy" or "using the bidask strategy"
                text_strategy_match = re.search(r'using the (spot-onesided|bidask|spot|bid-ask) strategy', line)
                if text_strategy_match:
                    strategy_text = text_strategy_match.group(1)
                    if strategy_text == "spot-onesided" or strategy_text == "spot":
                        result = "Spot (1-Sided)"
                    elif strategy_text == "bidask" or strategy_text == "bid-ask":
                        result = "Bid-Ask (1-Sided)"
                    else:
                        result = "UNKNOWN"
                    
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found strategy '{result}' at line {i + 1} (text format: '{strategy_text}')")
                    return result
                
                # Pattern 3: "spot-onesided:" or "bidask:" at start of summary line
                summary_match = re.search(r'^.*?(spot-onesided|bidask|spot|bid-ask):', line)
                if summary_match:
                    strategy_text = summary_match.group(1)
                    if strategy_text == "spot-onesided" or strategy_text == "spot":
                        result = "Spot (1-Sided)"
                    elif strategy_text == "bidask" or strategy_text == "bid-ask":
                        result = "Bid-Ask (1-Sided)"
                    else:
                        result = "UNKNOWN"
                    
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found strategy '{result}' at line {i + 1} (summary format: '{strategy_text}')")
                    return result
                else:
                    result = f"{strategy_type} (1-Sided)"
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found strategy '{result}' at line {i + 1}")
                    return result
                
                # DEBUG: Test specific pattern for line 1001421
                if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG" and "using the" in line and "strategy" in line:
                    logger.debug(f"TESTING Line {i + 1}: '{line.strip()}'")
                    test_match = re.search(r'using the (spot-onesided|bidask|spot|bid-ask) strategy', line)
                    logger.debug(f"Pattern 2 match result: {test_match}")
                    if test_match:
                        logger.debug(f"Matched group: '{test_match.group(1)}'")
        
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            logger.debug(f"No strategy pattern found in {lookback} lines lookback + {lookahead} lines lookahead from line {start_index + 1}")
        return "UNKNOWN"

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
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found investment amount '{match.group(1)}' from 'PnL+Start' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)

            # Pattern 2: PnL line with "Initial"
            # Example: Pnl Calculation: ... - Initial 11.10968 SOL
            if "Pnl Calculation:" in line and "Initial" in line:
                match = re.search(r'Initial\s*([\d\.]+)\s*SOL', line)
                if match:
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found investment amount '{match.group(1)}' from 'Pnl Calculation+Initial' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)
            
            # Pattern 3: Position opening line - more specific
            if ("Creating a position and adding liquidity" in line or 
                "Creating a position with" in line) and "Error" not in line:
                match = re.search(r'with\s*([\d\.]+)\s*SOL', line)
                if match:
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found investment amount '{match.group(1)}' from 'Creating+with' pattern at line {i+1}")
                    return round(float(match.group(1)), 4)
                
            # Pattern 4: Direct liquidity addition line
            if "adding liquidity of" in line and "SOL" in line and "Error" not in line:
                match = re.search(r'and\s*([\d\.]+)\s*SOL', line)
                if match:
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found investment amount '{match.group(1)}' from 'adding liquidity' pattern at line {i+1}")
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
                    if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                        logger.debug(f"Found PnL value {pnl_value} at line {i + 1}: {line.strip()}")
                    return {'pnl': pnl_value, 'line_number': i + 1}
        
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
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
            if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                logger.debug(f"Skipped opening at line {index + 1}, missing token pair.")
            return
        
        # Check if position for this token pair already exists
        existing_position = None
        existing_position_id = None
        for pos_id, pos in self.active_positions.items():
            if pos.token_pair == token_pair:
                existing_position = pos
                existing_position_id = pos_id
                break

        if existing_position:
            # Update existing position with new data but KEEP THE SAME OBJECT
            # AIDEV-NOTE-CLAUDE: Track retry count for cleaner logging
            if not hasattr(existing_position, 'retry_count'):
                existing_position.retry_count = 1
            existing_position.retry_count += 1
            
            # Update only the fields that might change with retry
            existing_position.open_timestamp = timestamp
            existing_position.bot_version = version
            existing_position.open_line_index = index
            
            # Re-parse pool and strategy (might have changed)
            existing_position.pool_address = self._find_context_value([
                r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
                r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
            ], index, 50)
            
            existing_position.actual_strategy = self._parse_strategy_from_context(index, 50)
            
            # CRITICAL: Re-parse investment amount
            existing_position.initial_investment = self._parse_initial_investment(index, 0, 100)
            
            # Don't log every retry, will log summary when position is finalized
            return  # Don't create new position!
            
        # Only create new position if none exists
        pos = Position(timestamp, version, index)
        pos.token_pair = token_pair
        
        pos.pool_address = self._find_context_value([
            r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
            r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
        ], index, 50)
        
        pos.actual_strategy = self._parse_strategy_from_context(index, 50)
        
        # CRITICAL CHANGE: Search for investment in wider forward-looking window
        pos.initial_investment = self._parse_initial_investment(index, 0, 100)
        
        self.active_positions[pos.position_id] = pos
        
        if DETAILED_POSITION_LOGGING:
            retry_info = f" (succeeded after {pos.retry_count} retries)" if hasattr(pos, 'retry_count') else ""
            logger.info(f"Opened position: {pos.position_id} ({pos.token_pair}) | Open detected at line {index + 1}{retry_info}")

    def _process_close_event_without_timestamp(self, index: int):
        """
        Process a position closing event that doesn't have timestamp in the line.
        
        Args:
            index: Line index in log
        """
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            logger.info(f"Processing close event at line {index + 1}")
            line_clean = self._clean_ansi(self.all_lines[index])
            logger.info(f"Cleaned line: {line_clean.strip()}")
        
        line_clean = self._clean_ansi(self.all_lines[index])
        
        # Extract token pair from "Removing positions in" line in lookback
        closed_pair = None
        for i in range(index, max(-1, index - 50), -1):
            line = self._clean_ansi(self.all_lines[i])
            remove_match = re.search(r'Removing positions in\s+([A-Za-z0-9\s\-_()]+\-SOL)', line)
            if remove_match:
                closed_pair = remove_match.group(1).strip()
                break

        if not closed_pair:
            if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                logger.debug(f"Found closing pattern at line {index + 1}, but could not extract token pair from 'Removing positions' lines.")
            return
        
        # Find matching active position for this token pair
        matching_position = next((pos for pos_id, pos in self.active_positions.items() 
                                if pos.token_pair == closed_pair), None)
        
        if matching_position:
            pos = matching_position
            # Extract close timestamp from context
            pos.close_timestamp = self._extract_close_timestamp(index)
            pos.close_reason = self._classify_close_reason(index)
            pos.close_line_index = index  # AIDEV-NOTE-CLAUDE: Store for context export
            pnl_result = self._parse_final_pnl_with_line_info(index, 50)
            pos.final_pnl = pnl_result['pnl']
            
            # AIDEV-NOTE-CLAUDE: Process close event for debug analysis
            self.debug_analyzer.process_close_event(pos, index)
            
            self.finalized_positions.append(pos)
            del self.active_positions[pos.position_id]
            
            if DETAILED_POSITION_LOGGING:
                pnl_line_info = f" | PnL found at line {pnl_result['line_number']}" if pnl_result['line_number'] else " | PnL not found"
                logger.info(f"Closed position: {pos.position_id} ({pos.token_pair}) | Close detected at line {index + 1} | Reason: {pos.close_reason} | PnL: {pos.final_pnl}{pnl_line_info}")
        else:
            if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
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

        # AIDEV-NOTE-CLAUDE: Set log lines for debug analyzer
        self.debug_analyzer.set_log_lines(self.all_lines)

        for i, line_content in enumerate(self.all_lines):
            # Check for closing pattern first (doesn't require timestamp)
            if "position and withdrew liquidity" in line_content:
                if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
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

            if "Added liquidity of" in line_content and "SOL" in line_content:
                # Now look back to find the corresponding "Creating a position" line
                create_line_index = None
                for j in range(i - 1, max(i - 100, -1), -1):  # Look back up to 100 lines
                    if "Creating a position" in self.all_lines[j]:
                        create_line_index = j
                        break
                
                if create_line_index is not None:
                    # Extract timestamp from the create line
                    create_line = self.all_lines[create_line_index]
                    timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', self._clean_ansi(create_line))
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        version_match = re.search(r'(v[\d.]+)', self._clean_ansi(create_line))
                        version = version_match.group(1) if version_match else "vUNKNOWN"
                        self._process_open_event(timestamp, version, create_line_index)

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
                if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                    logger.debug(f"Skipped position {pos.position_id} ({pos.token_pair}) - PnL {pos.final_pnl} SOL below threshold {MIN_PNL_THRESHOLD}")
                skipped_low_pnl += 1
                continue
                
            validated_positions.append(pos.to_csv_row())
        
        # Debug: Count potential closing patterns
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            closing_pattern_count = sum(1 for line in self.all_lines if "Closed" in line and "position and withdrew liquidity" in line)
            logger.info(f"Found {closing_pattern_count} lines matching closing pattern in total.")

        logger.info(f"Found {len(self.finalized_positions)} positions. {len(validated_positions)} have complete data for analysis. {skipped_low_pnl} skipped due to low PnL (< {MIN_PNL_THRESHOLD} SOL).")
        return validated_positions
    
    def _classify_close_reason(self, close_line_index: int) -> str:
        """
        Classify close reason based on context around close event.
        
        Args:
            close_line_index: Line index where close was detected
            
        Returns:
            Close reason: TP, SL, LV, OOR, or other
        """
        # Extract context around close event
        context_lines_before = 40  # Smaller window than debug export
        context_lines_after = 5
        
        start_idx = max(0, close_line_index - context_lines_before)
        end_idx = min(len(self.all_lines), close_line_index + context_lines_after + 1)
        
        context_text = " ".join(self.all_lines[start_idx:end_idx])
        
        # AIDEV-NOTE-CLAUDE: Business logic classification - always active
        
        # SL (Stop Loss) - highest priority as it's most specific
        if "Stop loss triggered:" in context_text:
            return "SL"
        
        # TP (Take Profit) - clear indicators
        if "Take profit triggered:" in context_text or "TAKEPROFIT!" in context_text:
            return "TP"
        
        # LV (Low Volume) - simplified pattern
        if "due to low volume" in context_text:
            return "LV"
        
        # OOR (Out of Range) - check after more specific ones
        if ("Closing position due to price range:" in context_text and 
            "Position was out of range for" in context_text):
            return "OOR"
        
        # Everything else
        return "other"

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
    
    # AIDEV-NOTE-CLAUDE: Export close contexts for analysis if enabled
    if CONTEXT_EXPORT_ENABLED and parser.debug_analyzer.get_context_count() > 0:
        context_stats = parser.debug_analyzer.export_analysis(CONTEXT_EXPORT_FILE)
        logger.info(f"Context export statistics: {dict(context_stats)}")
    
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