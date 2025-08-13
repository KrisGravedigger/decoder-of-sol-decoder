import re
import logging
from typing import List, Optional, Dict, Any, Tuple
import pandas as pd
from datetime import datetime

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

        # AIDEV-NOTE-CLAUDE: Corrected 24:xx handling. This bot's format uses 24:xx
        # to mean 00:xx on the SAME day, not the next day.
        if hour >= 24:
            hour = hour - 24  # e.g., 24 becomes 0, 25 becomes 1 etc.
            # Do NOT increment the day.

        final_datetime = base_date.replace(hour=hour, minute=int(minute), second=int(second))
        return final_datetime

    except (ValueError, IndexError) as e:
        logger.warning(f"Failed to parse custom timestamp '{ts_str}': {e}")
        return None


def clean_ansi(text: str) -> str:
    """Remove ANSI escape sequences, emoji, and other problematic Unicode characters."""
    if not text:
        return text
    
    # Remove ANSI escape sequences
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)
    
    # Remove emoji and other problematic Unicode characters
    text = re.sub(r'[\U0001F600-\U0001F64F]', '', text)  # Emoticons
    text = re.sub(r'[\U0001F300-\U0001F5FF]', '', text)  # Symbols & pictographs
    text = re.sub(r'[\U0001F680-\U0001F6FF]', '', text)  # Transport & map symbols
    text = re.sub(r'[\U0001F1E0-\U0001F1FF]', '', text)  # Flags (iOS)
    text = re.sub(r'[\U00002600-\U000027BF]', '', text)  # Miscellaneous symbols
    text = re.sub(r'[\U0001f900-\U0001f9ff]', '', text)  # Supplemental Symbols and Pictographs
    text = re.sub(r'[\U00002700-\U000027bf]', '', text)  # Dingbats
    text = re.sub(r'[\u200b-\u200d\ufeff]', '', text)  # Zero-width spaces and BOM
    
    return text.strip()


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

def parse_final_pnl_with_line_info(lines: List[str], start_index: int, lookback: int, 
                                   debug_enabled: bool = False,
                                   debug_file_path: Optional[str] = None) -> Dict[str, Any]:
    """
    Parse final PnL from log context with line number information and debug tracing.
    
    Args:
        lines: All log lines
        start_index: Starting line index
        lookback: Number of lines to look back
        debug_enabled: Whether debug logging is enabled
        debug_file_path: Path to a debug trace file.
        
    Returns:
        Dictionary with 'pnl' (float or None) and 'line_number' (int or None)
    """
    # AIDEV-NOTE: Increased lookback from 70 to 150 to catch PnL lines that are logged far before the final close confirmation.
    lookback = 150
    
    def _trace(msg: str):
        if debug_file_path:
            with open(debug_file_path, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')

    _trace("\n--- TRACING PnL PARSING ---")
    _trace(f"Starting search for PnL from line {start_index + 1}, looking back {lookback} lines.")

    for i in range(start_index, max(-1, start_index - lookback), -1):
        line = clean_ansi(lines[i])
        if debug_file_path:
            _trace(f"  [Line {i+1}] Checking: {line.strip()}")
        if "PnL:" in line and "Return:" in line:
            if debug_file_path:
                _trace(f"    -> Found potential PnL line.")
            match = re.search(r'PnL:\s*(-?\d+\.?\d*)\s*SOL', line)
            if match: 
                pnl_value = round(float(match.group(1)), 5)
                if debug_file_path:
                    _trace(f"    --> SUCCESS: Matched PnL value '{pnl_value}' at line {i + 1}.")
                if debug_enabled:
                    logger.debug(f"Found PnL value {pnl_value} at line {i + 1}: {line.strip()}")
                return {'pnl': pnl_value, 'line_number': i + 1}
            else:
                if debug_file_path:
                    _trace(f"    --> FAILED: 'PnL:' and 'Return:' present, but regex did not match.")
    
    if debug_file_path:
        _trace("--- PnL PARSING FAILED: No matching line found in lookback range. ---\n")
    if debug_enabled:
        logger.debug(f"No PnL found in lookback range {start_index + 1} to {max(1, start_index - lookback + 2)}")
    return {'pnl': None, 'line_number': None}

def extract_peak_pnl_from_logs(lines: List[str], start_line: int, end_line: int, 
                              significance_threshold: float = 0.01,
                              debug_file_path: Optional[str] = None,
                              position_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Extract maximum profit and loss percentages from logs between two line indices.
    Includes a targeted debugging feature to write the full context to a file.
    
    Args:
        lines: All log lines
        start_line: Position open line index  
        end_line: Position close line index
        significance_threshold: Minimum absolute % to consider (from config)
        debug_file_path: Optional. If provided, writes detailed context to this file.
        position_id: Optional. Required if debug_file_path is used.
        
    Returns:
        A dictionary with peak pnl data and sample count for diagnostics.
    """
    max_profit = None
    max_loss = None
    samples_found = 0
    pnl_pattern = re.compile(r'SOL\s*\(Return:\s*([+-]?\d+\.?\d*)\s*%\)', re.IGNORECASE)
    
    debug_lines_to_write = []
    is_debug_run = debug_file_path and position_id

    if is_debug_run:
        debug_lines_to_write.append(f"\n{'='*40} START OF POSITION: {position_id} {'='*40}\n")
        debug_lines_to_write.append(f"Analyzing lines from {start_line + 1} to {min(end_line + 1, len(lines))}\n")
        debug_lines_to_write.append(f"Significance Threshold: {significance_threshold}%\n")
        debug_lines_to_write.append(f"{'-'*100}\n\n")

    for i in range(start_line, min(end_line + 1, len(lines))):
        line = lines[i]
        cleaned_line = clean_ansi(line)
        matches = pnl_pattern.findall(cleaned_line)
        
        if is_debug_run:
            debug_line_prefix = ""
            if matches:
                try:
                    pct_value = float(matches[0])
                    if abs(pct_value) >= significance_threshold:
                        debug_line_prefix = ">>> MATCH FOUND:           "
                    else:
                        debug_line_prefix = ">>> MATCH SKIPPED (Threshold): "
                except (ValueError, TypeError):
                    pass # Ignore conversion errors for debug display
            debug_lines_to_write.append(f"{debug_line_prefix}Line {i+1:7}: {line.rstrip()}\n")

        for match in matches:
            try:
                pct_value = float(match)
                samples_found += 1
                
                if pct_value > 0 and abs(pct_value) >= significance_threshold:
                    if max_profit is None or pct_value > max_profit:
                        max_profit = pct_value
                
                if pct_value < 0 and abs(pct_value) >= significance_threshold:
                    if max_loss is None or pct_value < max_loss:
                        max_loss = pct_value
            except (ValueError, TypeError):
                continue
    
    if is_debug_run:
        debug_lines_to_write.append(f"\n{'-'*100}\n")
        debug_lines_to_write.append(f"Result: max_profit={max_profit}, max_loss={max_loss}, samples_found={samples_found}\n")
        debug_lines_to_write.append(f"{'='*40} END OF POSITION: {position_id} {'='*42}\n\n")
        with open(debug_file_path, 'a', encoding='utf-8') as f:
            f.writelines(debug_lines_to_write)

    return {
        'max_profit_pct': max_profit,
        'max_loss_pct': max_loss,
        'samples_found': samples_found
    }


def extract_total_fees_from_logs(lines: List[str], start_line: int, end_line: int,
                                 debug_file_path: Optional[str] = None) -> Optional[float]:
    """
    Extract total fees collected, prioritizing the "Pnl Calculation" line for accuracy.
    This version removes the unreliable fallback method to prevent incorrect data.
    
    Args:
        lines: All log lines
        start_line: Position open line index
        end_line: Position close line index
        debug_file_path: Path to a debug trace file.
        
    Returns:
        Total fees in SOL or None if not found
    """
    # AIDEV-NOTE: Increased lookback from 50 to 150 to catch fee lines that are logged far before the final close confirmation.
    lookback = 150
    
    def _trace(msg: str):
        if debug_file_path:
            with open(debug_file_path, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')

    _trace("\n--- TRACING FEE EXTRACTION ---")
    _trace(f"Scanning from line {end_line + 1} back to {max(start_line - 1, end_line - lookback)}.")
    _trace("--- [PRIMARY METHOD] Searching for 'Pnl Calculation:' line ---")
    
    # Primary Method: Search for the detailed 'Pnl Calculation' line. This is the only reliable source.
    for i in range(end_line, max(start_line - 1, end_line - lookback), -1):
        line = clean_ansi(lines[i])
        if debug_file_path:
            _trace(f"  [Line {i+1}] Checking: {line.strip()}")
        
        if "Pnl Calculation:" in line:
            if debug_file_path:
                _trace(f"    -> Found potential 'Pnl Calculation' line.")
            claimed_match = re.search(r'Claimed:\s*([\d.]+)\s*SOL', line, re.IGNORECASE)
            fees_included_match = re.search(r'([\d.]+)\s*SOL\s*\(Fees Tokens Included\)', line, re.IGNORECASE)
            initial_match = re.search(r'Initial\s*([\d.]+)\s*SOL', line, re.IGNORECASE)
            
            if debug_file_path:
                _trace(f"      - Claimed match: {'OK' if claimed_match else 'FAIL'}")
                _trace(f"      - Fees Included match: {'OK' if fees_included_match else 'FAIL'}")
                _trace(f"      - Initial match: {'OK' if initial_match else 'FAIL'}")

            if fees_included_match and initial_match:
                claimed_fees = float(claimed_match.group(1)) if claimed_match else 0.0
                position_value_with_fees = float(fees_included_match.group(1))
                initial_investment = float(initial_match.group(1))
                
                if debug_file_path:
                    _trace(f"        -> Extracted values: claimed={claimed_fees}, val_w_fees={position_value_with_fees}, initial={initial_investment}")
                
                unclaimed_fees = max(0, position_value_with_fees - initial_investment)
                total_fees = claimed_fees + unclaimed_fees
                
                if debug_file_path:
                    _trace(f"        -> Calculated: unclaimed_fees={unclaimed_fees}, total_fees={total_fees}")
                    _trace(f"    --> SUCCESS (Primary): Found total fees: {round(total_fees, 6)}")
                
                logger.debug(f"Fees from Pnl Calc line: Claimed={claimed_fees}, Unclaimed={unclaimed_fees}, Total={total_fees}")
                return round(total_fees, 6)
            else:
                if debug_file_path:
                    _trace("    --> FAILED (Primary): 'Pnl Calculation' line found but malformed. ABORTING fee extraction for this line.")
                logger.warning(f"Found 'Pnl Calculation' line but it was malformed. Skipping fee extraction. Line {i+1}")
                # AIDEV-NOTE: Continue searching, maybe a better formatted line exists.
                continue

    # AIDEV-NOTE: Fallback method has been removed as it was producing wildly inaccurate results.
    # It is better to have no data (None) than incorrect data.
    if debug_file_path:
        _trace("--- FEE EXTRACTION FAILED: No valid 'Pnl Calculation:' line found in lookback range. ---\n")
    return None

def extract_dlmm_range(log_lines: List[str], open_line_index: int) -> Tuple[Optional[float], Optional[float]]:
    """
    Extract min and max price range from DLMM pool log messages.
    
    AIDEV-TPSL-CLAUDE: Fixed conversion - logs show SOL prices, we need USDC prices.
    Multiply by SOL/USDC rate instead of dividing!
    """
    # Search upwards from the open line (max 60 lines)
    for i in range(open_line_index, max(-1, open_line_index - 60), -1):
        line = clean_ansi(log_lines[i])
        
        if "Pool out of range to the bottom" in line:
            bottom_match = re.search(r'price reaches: \$([0-9.]+)', line)
            if bottom_match:
                try:
                    min_price_sol = float(bottom_match.group(1))
                    
                    # Look for the corresponding top range
                    for j in range(max(0, i-5), min(len(log_lines), i+6)):
                        next_line = clean_ansi(log_lines[j])
                        if "Pool out of range to the top" in next_line:
                            top_match = re.search(r'price reaches: \$([0-9.]+)', next_line)
                            if top_match:
                                max_price_sol = float(top_match.group(1))
                                
                                # CRITICAL FIX: Logs show price in SOL, we need USDC
                                # MULTIPLY by SOL price, not divide!
                                sol_price_usd = _extract_sol_price_near_position(log_lines, open_line_index)
                                
                                if sol_price_usd and sol_price_usd > 0:
                                    # Convert: token_price_in_usdc = token_price_in_sol * sol_price_in_usdc
                                    min_price_usdc = min_price_sol * sol_price_usd
                                    max_price_usdc = max_price_sol * sol_price_usd
                                    
                                    logger.debug(f"Converted bin range from SOL [{min_price_sol:.6f}, {max_price_sol:.6f}] "
                                               f"to USDC [{min_price_usdc:.6f}, {max_price_usdc:.6f}] "
                                               f"(SOL price: ${sol_price_usd})")
                                    return min_price_usdc, max_price_usdc
                                else:
                                    # Can't convert without SOL price
                                    logger.warning(f"Cannot convert SOL bin prices without SOL/USDC rate at line {open_line_index + 1}")
                                    return None, None
                                    
                except ValueError:
                    logger.warning(f"Failed to parse DLMM range values at line {i + 1}")
    
    logger.debug(f"No DLMM range found for position at line {open_line_index + 1}")
    return None, None


def _extract_sol_price_near_position(log_lines: List[str], position_line: int) -> Optional[float]:
    """
    Extract SOL/USD price from logs near position opening.
    
    Looks for patterns like:
    - "SOL: $165.25"
    - "SOL/USDC: 165.25"
    - "SOL Price: $165.25"
    """
    # Search in vicinity of position opening (before and after)
    search_range = 100
    
    for i in range(max(0, position_line - search_range), 
                   min(len(log_lines), position_line + search_range)):
        line = clean_ansi(log_lines[i])
        
        # Multiple patterns for SOL price
        patterns = [
            r'SOL[:/]?\s*\$?([\d.]+)',           # SOL: $165.25 or SOL/165.25
            r'SOL/USDC[:\s]+\$?([\d.]+)',        # SOL/USDC: 165.25
            r'SOL\s+Price[:\s]+\$?([\d.]+)',     # SOL Price: $165.25
            r'price.*SOL.*\$?([\d.]+)',          # any price...SOL...$165
        ]
        
        for pattern in patterns:
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                try:
                    price = float(match.group(1))
                    # Sanity check - SOL price should be between $10 and $1000
                    if 10 < price < 1000:
                        logger.debug(f"Found SOL price ${price} at line {i + 1}")
                        return price
                except ValueError:
                    continue
    
    # Fallback: use approximate SOL price for May 2025
    # This should be configured or fetched from API
    DEFAULT_SOL_PRICE = 165.0  # Approximate for your data period
    logger.warning(f"Could not find SOL price in logs, using default ${DEFAULT_SOL_PRICE}")
    return DEFAULT_SOL_PRICE

def extract_oor_parameters(log_lines: List[str], start_line: int, end_line: int) -> Dict[str, Optional[float]]:
    """
    Extracts OOR timeout and price threshold from log lines.

    Searches for a line matching:
    "...Will close after X minutes if still out of range.Price is Y% out of range..."
    between the position open and close events.

    Args:
        log_lines: All log lines.
        start_line: Position open line index.
        end_line: Position close line index.

    Returns:
        A dictionary with 'timeout_minutes' and 'threshold_pct', or None values if not found.
    """
    timeout_pattern = re.compile(r'Will close after ([\d.]+) minutes', re.IGNORECASE)
    threshold_pattern = re.compile(r'Price is ([\d.]+)% out of range', re.IGNORECASE)

    # Search only within the position's lifetime
    for i in range(start_line, min(end_line + 1, len(log_lines))):
        cleaned_line = clean_ansi(log_lines[i])

        timeout_match = timeout_pattern.search(cleaned_line)
        threshold_match = threshold_pattern.search(cleaned_line)

        # Both patterns must be present on the same line to ensure context is correct
        if timeout_match and threshold_match:
            try:
                timeout = float(timeout_match.group(1))
                threshold = float(threshold_match.group(1))
                logger.debug(f"Found OOR params on line {i+1}: Timeout={timeout}m, Threshold={threshold}%")
                return {'timeout_minutes': timeout, 'threshold_pct': threshold}
            except (ValueError, TypeError):
                logger.warning(f"Could not parse OOR params from line {i+1}")
                continue # Try next line in case of parsing error
    
    # Return a dictionary with None values if no matching line is found
    return {'timeout_minutes': None, 'threshold_pct': None}