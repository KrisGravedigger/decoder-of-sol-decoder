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


def parse_open_details_from_context(lines: List[str], start_index: int, lookback: int, lookahead: int = 50, debug_enabled: bool = False) -> Dict[str, Any]:
    """
    Parse position opening details (strategy, TP, SL) from log context.
    Finds the most complete log line within the search window.
    
    Args:
        lines: All log lines
        start_index: Starting line index
        lookback: Number of lines to look back
        lookahead: Number of lines to look ahead
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        A dictionary with 'strategy', 'tp', and 'sl' keys.
    """
    force_debug = True # Keep this for now

    search_start = max(0, start_index - lookback)
    search_end = min(len(lines), start_index + lookahead)

    best_fallback_strategy = "UNKNOWN"
    # AIDEV-NOTE-GEMINI: Default result dictionary.
    final_details = {
        'strategy': "UNKNOWN",
        'tp': None,
        'sl': None
    }

    # Search backwards to find the most recent, definitive log line first.
    for i in range(search_end - 1, search_start - 1, -1):
        line = clean_ansi(lines[i])
        
        # --- Attempt to parse all details from the current line ---
        base_strategy = None
        step_size = None
        tp = None
        sl = None

        # Check for a line that could contain strategy info
        is_strategy_line = re.search(r'(bidask|spot-onesided|spot|\[(Spot|Bid-Ask) \(1-Sided\))', line, re.IGNORECASE)
        
        if is_strategy_line:
            # 1. Parse Strategy Type
            log_summary_match = re.search(r'(bidask|spot-onesided|spot):\s*\d+', line, re.IGNORECASE)
            if log_summary_match:
                strategy_text = log_summary_match.group(1).lower()
                if "spot" in strategy_text: base_strategy = "Spot (1-Sided)"
                elif "bidask" in strategy_text: base_strategy = "Bid-Ask (1-Sided)"
            else: # Fallback to bracket format
                bracket_match = re.search(r'\[(Spot|Bid-Ask) \(1-Sided\)', line)
                if bracket_match:
                    base_strategy = f"{bracket_match.group(1)} (1-Sided)"

            # 2. Parse Step Size
            step_size_match = re.search(r'STEP SIZE:\s*(WIDE|SIXTYNINE|MEDIUM|NARROW)', line, re.IGNORECASE)
            if step_size_match:
                step_size = step_size_match.group(1).upper()

            # 3. Parse Take Profit & Stop Loss
            tp_match = re.search(r'TAKEPROFIT:\s*([\d\.]+)%', line)
            if tp_match:
                tp = float(tp_match.group(1))

            sl_match = re.search(r'STOPLOSS:\s*([\d\.]+)%', line)
            if sl_match:
                sl = float(sl_match.group(1))

            # --- Decision Logic ---
            if base_strategy:
                # Perfect Match: We have strategy and step size. This is the definitive line.
                if step_size:
                    final_details['strategy'] = f"{base_strategy} {step_size}"
                    final_details['tp'] = tp
                    final_details['sl'] = sl
                    if debug_enabled or force_debug:
                        logger.debug(f"Found COMPLETE match on line {i + 1}: {final_details}. Returning.")
                    return final_details
                
                # Partial Match: Store as fallback if we don't have one yet, and KEEP SEARCHING.
                if best_fallback_strategy == "UNKNOWN":
                    best_fallback_strategy = base_strategy
                    # Also store TP/SL if found on this partial line
                    final_details['tp'] = tp if final_details['tp'] is None else final_details['tp']
                    final_details['sl'] = sl if final_details['sl'] is None else final_details['sl']
                    if debug_enabled or force_debug:
                        logger.debug(f"Found PARTIAL match on line {i + 1}: '{base_strategy}'. Storing as fallback and continuing.")

    # If loop finishes, return the best we could find.
    final_details['strategy'] = best_fallback_strategy
    if debug_enabled or force_debug:
        logger.debug(f"Search complete. Returning best found details: {final_details}")
    
    return final_details


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