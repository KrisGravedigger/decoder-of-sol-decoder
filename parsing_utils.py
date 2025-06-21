import re
import logging
from typing import List, Optional, Dict, Any

# Get logger
logger = logging.getLogger('ParsingUtils')


def clean_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)


def find_context_value(patterns: List[str], lines: List[str], start_index: int, lookback: int) -> Optional[str]:
    """
    Find a value matching one of the patterns within a lookback window.
    
    Args:
        patterns: List of regex patterns to search for
        lines: All log lines
        start_index: Starting line index
        lookback: Number of lines to look back
        
    Returns:
        First matching value found, or None
    """
    for i in range(start_index, max(-1, start_index - lookback), -1):
        for pattern in patterns:
            match = re.search(pattern, clean_ansi(lines[i]))
            if match: 
                return match.group(1).strip()
    return None


def normalize_token_pair(text: Optional[str]) -> Optional[str]:
    """
    Extract and normalize token pair from text.
    
    Args:
        text: Text containing potential token pair
        
    Returns:
        Normalized token pair string or None
    """
    if not text: 
        return None
    match = re.search(r'([\w\s().-]+-SOL)', clean_ansi(text))
    return match.group(1).strip() if match else None


def extract_close_timestamp(lines: List[str], close_line_index: int, debug_enabled: bool = False) -> str:
    """
    Extract timestamp from close event context.
    
    Args:
        lines: All log lines
        close_line_index: Line index where close was detected
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        Timestamp string or "UNKNOWN" if not found
    """
    # Try to extract timestamp from close line itself
    close_line = clean_ansi(lines[close_line_index])
    timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', close_line)
    if timestamp_match:
        if debug_enabled:
            logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from close line {close_line_index + 1}")
        return timestamp_match.group(1)
    
    # Look for timestamp in nearby lines (prefer lines before close)
    search_range = 10  # Look 10 lines before and after
    
    # First search backwards (more likely to have relevant timestamp)
    for i in range(close_line_index - 1, max(-1, close_line_index - search_range), -1):
        line = clean_ansi(lines[i])
        timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            if debug_enabled:
                logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (backward search)")
            return timestamp_match.group(1)
    
    # Then search forward if nothing found backward
    for i in range(close_line_index + 1, min(len(lines), close_line_index + search_range)):
        line = clean_ansi(lines[i])
        timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            if debug_enabled:
                logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (forward search)")
            return timestamp_match.group(1)
    
    if debug_enabled:
        logger.debug(f"No timestamp found in {search_range} lines around close at line {close_line_index + 1}")
    return "UNKNOWN"


def parse_strategy_from_context(lines: List[str], start_index: int, lookback: int, debug_enabled: bool = False) -> str:
    """
    Parse strategy from log context with step size detection.
    
    Args:
        lines: All log lines
        start_index: Starting line index
        lookback: Number of lines to look back
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        Strategy string with step size: "Spot (1-Sided) WIDE", "Bid-Ask (1-Sided) SIXTYNINE", etc. or "UNKNOWN"
    """
    lookahead = 30  # Fixed lookahead value
    
    if debug_enabled:
        logger.debug(f"Parsing strategy from line {start_index + 1}, looking back {lookback} lines and ahead {lookahead} lines")
    
    # Search both backward and forward
    search_start = max(0, start_index - lookback)
    search_end = min(len(lines), start_index + lookahead)
    
    # FIRST PASS: Look for bracket format with step size (highest priority)
    for i in range(search_start, search_end):
        line = clean_ansi(lines[i])
        
        # Pattern 1: [Spot (1-Sided)/... or [Bid-Ask (1-Sided)/... with step size detection
        strategy_match = re.search(r'\[(Spot|Bid-Ask) \(1-Sided\)', line)
        if strategy_match:
            strategy_type = strategy_match.group(1)  # "Spot" or "Bid-Ask"
            base_strategy = f"{strategy_type} (1-Sided)"
            
            if debug_enabled:
                logger.debug(f"Found base strategy '{base_strategy}' at line {i + 1}")
                logger.debug(f"Full line content: {line}")
            
            # Extract step size - try multiple patterns
            step_size_patterns = [
                r'Step Size:\s*(WIDE|SIXTYNINE|MEDIUM|NARROW)',  # with optional whitespace
                r'/Step Size:\s*(WIDE|SIXTYNINE|MEDIUM|NARROW)/',  # with slashes
                r'Step Size:\s*([A-Z]+)',  # any uppercase word after Step Size
            ]
            
            step_size = None
            for pattern in step_size_patterns:
                step_size_match = re.search(pattern, line, re.IGNORECASE)
                if step_size_match:
                    step_size = step_size_match.group(1).upper()
                    if debug_enabled:
                        logger.debug(f"Found step size '{step_size}' using pattern: {pattern}")
                    break
            
            if step_size and step_size in ['WIDE', 'SIXTYNINE', 'MEDIUM', 'NARROW']:
                result = f"{base_strategy} {step_size}"
                if debug_enabled:
                    logger.debug(f"Returning strategy with step size: '{result}'")
                return result
            else:
                # Found bracket format but no valid step size - still return it
                if debug_enabled:
                    logger.debug(f"Found bracket format but no valid step size, returning: '{base_strategy}'")
                return base_strategy
    
    # SECOND PASS: Look for text format (fallback)
    for i in range(search_start, search_end):
        line = clean_ansi(lines[i])
        
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
            
            if debug_enabled:
                logger.debug(f"Found strategy '{result}' at line {i + 1} (text format: '{strategy_text}') - fallback")
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
            
            if debug_enabled:
                logger.debug(f"Found strategy '{result}' at line {i + 1} (summary format: '{strategy_text}') - fallback")
            return result
    
    if debug_enabled:
        logger.debug(f"No strategy pattern found in {lookback} lines lookback + {lookahead} lines lookahead from line {start_index + 1}")
    return "UNKNOWN"


def parse_initial_investment(lines: List[str], start_index: int, lookahead: int, debug_enabled: bool = False) -> Optional[float]:
    """
    Parse initial investment amount from log context.
    
    Args:
        lines: All log lines
        start_index: Starting line index
        lookahead: Lines to look ahead
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        Initial investment amount in SOL or None
    """
    search_start = start_index
    search_end = min(len(lines), start_index + lookahead)

    for i in range(search_start, search_end):
        line = clean_ansi(lines[i])

        # Pattern 1: Most reliable - PnL line with "Start:"
        # Example: PnL: 0.05403 SOL (Return: +0.49%) | Start: 11.10968 SOL → Current: 11.16371 SOL
        if "PnL:" in line and "Start:" in line:
            match = re.search(r'Start:\s*([\d\.]+)\s*SOL', line)
            if match:
                if debug_enabled:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'PnL+Start' pattern at line {i+1}")
                return round(float(match.group(1)), 4)

        # Pattern 2: PnL line with "Initial"
        # Example: Pnl Calculation: ... - Initial 11.10968 SOL
        if "Pnl Calculation:" in line and "Initial" in line:
            match = re.search(r'Initial\s*([\d\.]+)\s*SOL', line)
            if match:
                if debug_enabled:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'Pnl Calculation+Initial' pattern at line {i+1}")
                return round(float(match.group(1)), 4)
        
        # Pattern 3: Position opening line - more specific
        if ("Creating a position and adding liquidity" in line or 
            "Creating a position with" in line) and "Error" not in line:
            match = re.search(r'with\s*([\d\.]+)\s*SOL', line)
            if match:
                if debug_enabled:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'Creating+with' pattern at line {i+1}")
                return round(float(match.group(1)), 4)
            
        # Pattern 4: Direct liquidity addition line
        if "adding liquidity of" in line and "SOL" in line and "Error" not in line:
            match = re.search(r'and\s*([\d\.]+)\s*SOL', line)
            if match:
                if debug_enabled:
                    logger.debug(f"Found investment amount '{match.group(1)}' from 'adding liquidity' pattern at line {i+1}")
                return round(float(match.group(1)), 4)

    logger.warning(f"Could not find investment amount for position opened at line {start_index + 1}")
    return None
        

def parse_final_pnl_with_line_info(lines: List[str], start_index: int, lookback: int, debug_enabled: bool = False) -> Dict[str, Any]:
    """
    Parse final PnL from log context with line number information.
    
    Args:
        lines: All log lines
        start_index: Starting line index
        lookback: Number of lines to look back
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        Dictionary with 'pnl' (float or None) and 'line_number' (int or None)
    """
    for i in range(start_index, max(-1, start_index - lookback), -1):
        line = clean_ansi(lines[i])
        if "PnL:" in line and "Return:" in line:
            match = re.search(r'PnL:\s*(-?\d+\.?\d*)\s*SOL', line)
            if match: 
                pnl_value = round(float(match.group(1)), 5)
                if debug_enabled:
                    logger.debug(f"Found PnL value {pnl_value} at line {i + 1}: {line.strip()}")
                return {'pnl': pnl_value, 'line_number': i + 1}
    
    if debug_enabled:
        logger.debug(f"No PnL found in lookback range {start_index + 1} to {max(1, start_index - lookback + 2)}")
    return {'pnl': None, 'line_number': None}