import re
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import pandas as pd

# Get logger
logger = logging.getLogger('ParsingUtils')


def _parse_custom_timestamp(ts_str: str) -> Optional[datetime]:
    """
    Parse non-standard timestamps like "MM/DD-HH:MM:SS" into datetime objects.
    Handles the "24:XX" hour format by rolling over to the next day.
    """
    if not isinstance(ts_str, str) or not ts_str:
        return None

    try:
        # Format: "05/12-20:57:08" -> "2025-05-12 20:57:08"
        date_part, time_part = ts_str.split('-')
        month, day = date_part.split('/')

        hour, minute, second = time_part.split(':')
        hour = int(hour)

        # Assume current year
        current_year = datetime.now().year
        base_date = datetime(current_year, int(month), int(day))

        # Handle hour 24 as next day hour 0
        if hour >= 24:
            hour = hour - 24
            base_date = base_date + timedelta(days=1)

        final_datetime = base_date.replace(hour=hour, minute=int(minute), second=int(second))
        return final_datetime

    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse custom timestamp '{ts_str}': {e}")
        return None


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


def extract_close_timestamp(lines: List[str], close_line_index: int, open_line_index: int, debug_enabled: bool = False) -> str:
    """
    Extract timestamp from close event context, respecting the open_line_index boundary.
    
    Args:
        lines: All log lines
        close_line_index: Line index where close was detected
        open_line_index: Line index where the position was opened. This is a hard boundary.
        debug_enabled: Whether debug logging is enabled
        
    Returns:
        Timestamp string or "UNKNOWN" if not found
    """
    close_line = clean_ansi(lines[close_line_index])
    timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', close_line)
    if timestamp_match:
        if debug_enabled:
            logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from close line {close_line_index + 1}")
        return timestamp_match.group(1)
    
    search_range = 25
    
    # Search backwards, but not past the line where the position was opened.
    # This hard boundary is the definitive fix for the "Time Machine" problem.
    start_search = close_line_index - 1
    end_search = max(open_line_index, close_line_index - search_range)

    for i in range(start_search, end_search, -1):
        line = clean_ansi(lines[i])
        timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            if debug_enabled:
                logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (backward search)")
            return timestamp_match.group(1)
    
    # Forward search remains a useful fallback.
    for i in range(close_line_index + 1, min(len(lines), close_line_index + search_range)):
        line = clean_ansi(lines[i])
        timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', line)
        if timestamp_match:
            if debug_enabled:
                logger.debug(f"Found close timestamp '{timestamp_match.group(1)}' from context line {i + 1} (forward search)")
            return timestamp_match.group(1)
    
    if debug_enabled:
        logger.warning(f"No timestamp found in context for close event at line {close_line_index + 1}. Boundary was line {open_line_index + 1}.")
    return "UNKNOWN"


def parse_position_from_open_line(line: str, line_index: int, all_lines: List[str], debug_enabled: bool = False) -> Optional[Dict[str, Any]]:
    """
    Parses all position details from a single "OPENED" log line and its immediate context.

    Args:
        line (str): The single log line containing the "...OPENED..." event.
        line_index (int): The index of the line in all_lines.
        all_lines (List[str]): All log lines for context searching (e.g., pool_address).
        debug_enabled (bool): Whether to enable debug logging.

    Returns:
        A dictionary containing all parsed position details, or None if parsing fails.
    """
    cleaned_line = clean_ansi(line)

    open_pattern = re.compile(
        r'v(?P<version>[\d.]+)-(?P<timestamp>\d{2}/\d{2}-\d{2}:\d{2}:\d{2}).*'
        r'(?P<strategy_type>bidask|spot|spot-onesided):\s*\d+\s*\|\s*OPENED\s*'
        r'(?P<token_pair>[\w\s().-]+-SOL)'
    )
    
    match = open_pattern.search(cleaned_line)
    if not match:
        if debug_enabled:
            logger.debug(f"Line {line_index + 1} did not match the main 'OPENED' pattern.")
        return None

    details = match.groupdict()

    step_size_match = re.search(r'STEP SIZE:\s*(WIDE|SIXTYNINE|MEDIUM|NARROW)', cleaned_line, re.IGNORECASE)
    step_size = step_size_match.group(1).upper() if step_size_match else "UNKNOWN"
    
    base_strategy = "Spot (1-Sided)" if "spot" in details['strategy_type'].lower() else "Bid-Ask (1-Sided)"
    details['actual_strategy'] = f"{base_strategy} {step_size}"

    tp_match = re.search(r'TAKEPROFIT:\s*([\d\.]+)%', cleaned_line, re.IGNORECASE)
    details['take_profit'] = float(tp_match.group(1)) if tp_match else 0.0
    
    sl_match = re.search(r'STOPLOSS:\s*([\d\.]+)%', cleaned_line, re.IGNORECASE)
    details['stop_loss'] = float(sl_match.group(1)) if sl_match else 0.0

    investment_match = re.search(r'Deposit \(Fixed Amount\)\s*:\s*([\d.]+)\s*SOL', cleaned_line, re.IGNORECASE)
    details['initial_investment'] = float(investment_match.group(1)) if investment_match else None
    
    wallet_match = re.search(r'Wallet:\s*([a-zA-Z0-9]+)', cleaned_line)
    details['wallet_address'] = wallet_match.group(1) if wallet_match else None

    pool_address = None
    for i in range(line_index, max(-1, line_index - 60), -1):
        context_line = clean_ansi(all_lines[i])
        pool_match = re.search(r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', context_line)
        if pool_match:
            pool_address = pool_match.group(1)
            if debug_enabled:
                logger.debug(f"Found pool address '{pool_address}' at line {i + 1} for open event at line {line_index + 1}.")
            break
    
    details['pool_address'] = pool_address

    if debug_enabled:
        logger.debug(f"Parsed details from line {line_index + 1}: {details}")

    return details

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