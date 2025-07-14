import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path



# Failed position detection patterns
FAILED_POSITION_PATTERNS = [
    r'Transactions failed to confirm after \d+ attempts',
    r'Error creating a position:.*failed',
    r'Error creating a position:.*Transactions failed',
    r'Failed to create position',
    r'Position creation failed', 
    r'Transaction failed after multiple attempts',
    r'Could not confirm transaction after \d+ attempts',
    r'Error.*creating.*position',
]

# AIDEV-NOTE-GEMINI: Added success patterns to prevent "silent failures" from being treated as successful.
SUCCESS_CONFIRMATION_PATTERNS = [
    # Pattern 1: Catches summary lines like "bidask: 12345 | OPENED..." or "spot: 12345 | OPENED..."
    r'(bidask|spot|spot-onesided):\s*\d+',
    # Pattern 2: Catches explicit pool creation logs like "Opened a new pool for..."
    r'Opened a new pool for',
    # Pattern 3: A generic fallback for future formats
    r'Position successfully created',
]
# AIDEV-NOTE-CLAUDE: This ensures project root is on the path for module resolution
# This is a robust way to handle imports in a nested structure.
sys.path.append(str(Path(__file__).resolve().parent.parent))

# === MAIN DEBUG CONFIGURATION ===
# AIDEV-NOTE-CLAUDE: Master debug controls - these override settings in debug_analyzer.py
DEBUG_ENABLED = False                    # Master switch for all debug features
DEBUG_LEVEL = "DEBUG"                   # "DEBUG" for detailed logs, "INFO" for standard logs
CONTEXT_EXPORT_ENABLED = True          # Enable/disable context export completely
DETAILED_POSITION_LOGGING = True       # Enable/disable detailed position event logging

# AIDEV-NOTE-CLAUDE: Imports updated to reflect new project structure.
from core.models import Position
from extraction.parsing_utils import (
    clean_ansi, find_context_value, normalize_token_pair,
    extract_close_timestamp, parse_position_from_open_line,
    parse_final_pnl_with_line_info
)
from tools.debug_analyzer import DebugAnalyzer

# --- Configuration ---
LOG_DIR = "input"
OUTPUT_CSV = "positions_to_analyze.csv"
CONTEXT_EXPORT_FILE = "close_contexts_analysis.txt"
MIN_PNL_THRESHOLD = 0.01  # Skip positions with PnL between -0.01 and +0.01 SOL
STRATEGY_DIAGNOSTIC_ENABLED = True  # Enable strategy parsing diagnostics
STRATEGY_DIAGNOSTIC_FILE = "strategy_parsing_diagnostic.txt"

# Logging configuration
log_level = logging.DEBUG if (DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG") else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger('LogExtractor')


# === STRATEGY PARSING DIAGNOSTIC ===
STRATEGY_DIAGNOSTIC_ENABLED = True  # Enable strategy parsing diagnostics
STRATEGY_DIAGNOSTIC_FILE = "strategy_parsing_diagnostic.txt"

class StrategyParsingDiagnostic:
    """Diagnostic tool for strategy parsing issues - missing step_size detection."""
    
    def __init__(self, enabled: bool = True):
        """Initialize strategy parsing diagnostic."""
        self.enabled = enabled
        self.diagnostic_cases: List[Dict[str, Any]] = []
        self.all_lines: List[str] = []
        self.file_line_mapping: List[Dict[str, Any]] = []
        
    def set_log_data(self, lines: List[str], file_mapping: List[Dict[str, Any]]):
        """Set log lines and file mapping for diagnostic."""
        self.all_lines = lines
        self.file_line_mapping = file_mapping
        
    def _get_file_info_for_line(self, line_index: int) -> tuple[str, str]:
        """Get wallet_id and source_file for a given line index."""
        for file_info in self.file_line_mapping:
            if file_info['start'] <= line_index < file_info['end']:
                return file_info['wallet_id'], file_info['source_file']
        return "unknown_wallet", "unknown_file"
        
    def detect_missing_step_size(self, strategy_raw: str, line_index: int, investment_amount: float = None):
        """
        Detect cases where step_size might be missing from strategy name.
        
        Args:
            strategy_raw: Extracted strategy string
            line_index: Line index where strategy was parsed
            investment_amount: Investment amount if available
        """
        if not self.enabled:
            return
            
        # Check if strategy is missing step_size
        strategy_lower = strategy_raw.lower()
        has_step_size = any(step in strategy_lower for step in ['wide', 'medium', 'sixtynine', 'narrow'])
        
        # Criteria for suspicion:
        # 1. No step_size in strategy name
        # 2. Investment amount suggests it might be Wide (>7 SOL)
        is_suspicious = (
            not has_step_size and 
            investment_amount is not None and 
            investment_amount > 7.0  # Wide-range investment threshold
        )
        
        if is_suspicious or not has_step_size:
            wallet_id, source_file = self._get_file_info_for_line(line_index)
            
            # Extract context around the line
            context_lines_before = 30
            context_lines_after = 30
            start_idx = max(0, line_index - context_lines_before)
            end_idx = min(len(self.all_lines), line_index + context_lines_after + 1)
            
            context_lines = self.all_lines[start_idx:end_idx]
            
            diagnostic_case = {
                'strategy_raw': strategy_raw,
                'investment_amount': investment_amount,
                'line_index': line_index,
                'wallet_id': wallet_id,
                'source_file': source_file,
                'context_lines': context_lines,
                'context_start_line': start_idx,
                'is_suspicious': is_suspicious,
                'reason': 'Missing step_size + high investment' if is_suspicious else 'Missing step_size'
            }
            
            self.diagnostic_cases.append(diagnostic_case)
            
            if DETAILED_POSITION_LOGGING:
                logger.warning(f"Strategy parsing diagnostic: {diagnostic_case['reason']} | "
                              f"Strategy: '{strategy_raw}' | Investment: {investment_amount} SOL | "
                              f"File: {source_file} | Line: {line_index + 1}")
    
    def export_diagnostic(self, output_file: str) -> Dict[str, int]:
        """
        Export strategy parsing diagnostic to file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            Dictionary with export statistics
        """
        if not self.enabled or not self.diagnostic_cases:
            logger.info("No strategy parsing diagnostic cases to export.")
            return {}
            
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("STRATEGY PARSING DIAGNOSTIC REPORT\n")
                f.write(f"Generated from {len(self.diagnostic_cases)} suspicious cases\n")
                f.write("=" * 80 + "\n\n")
                
                f.write("SUMMARY:\n")
                f.write("This report shows cases where strategy parsing might be incomplete.\n")
                f.write("Look for patterns in log format that cause step_size detection failure.\n\n")
                
                suspicious_count = sum(1 for case in self.diagnostic_cases if case['is_suspicious'])
                missing_count = len(self.diagnostic_cases) - suspicious_count
                
                f.write(f"Cases found:\n")
                f.write(f"  - {suspicious_count} suspicious (missing step_size + high investment)\n")
                f.write(f"  - {missing_count} missing step_size (normal investment)\n\n")
                
                # Group by file for easier analysis
                cases_by_file = {}
                for case in self.diagnostic_cases:
                    file_key = case['source_file']
                    if file_key not in cases_by_file:
                        cases_by_file[file_key] = []
                    cases_by_file[file_key].append(case)
                
                for file_name, file_cases in cases_by_file.items():
                    f.write(f"\n{'=' * 20} FILE: {file_name} {'=' * 20}\n")
                    f.write(f"Cases in this file: {len(file_cases)}\n\n")
                    
                    for i, case in enumerate(file_cases, 1):
                        f.write(f"--- CASE #{i} ---\n")
                        f.write(f"Strategy: '{case['strategy_raw']}'\n")
                        f.write(f"Investment: {case['investment_amount']} SOL\n")
                        f.write(f"Line: {case['line_index'] + 1} (context starts at line {case['context_start_line'] + 1})\n")
                        f.write(f"Reason: {case['reason']}\n")
                        f.write(f"File: {case['wallet_id']}/{case['source_file']}\n")
                        f.write("\n" + "=" * 60 + " CONTEXT START " + "=" * 60 + "\n")
                        
                        for line_idx, line in enumerate(case['context_lines']):
                            actual_line_num = case['context_start_line'] + line_idx + 1
                            marker = ">>> " if line_idx == 30 else "    "  # Mark the target line
                            f.write(f"{marker}Line {actual_line_num:6}: {line}")
                            if not line.endswith('\n'):
                                f.write('\n')
                        
                        f.write("=" * 60 + " CONTEXT END " + "=" * 62 + "\n\n")
                
                f.write(f"\n{'=' * 20} ANALYSIS RECOMMENDATIONS {'=' * 20}\n")
                f.write("1. Look for log format patterns that differ between working and failing cases\n")
                f.write("2. Check if bot version changes correlate with parsing failures\n")
                f.write("3. Examine context around target lines (marked with >>>) for strategy mentions\n")
                f.write("4. Update parsing_utils.py regex patterns if format changes detected\n")
            
            logger.info(f"Strategy parsing diagnostic exported to {output_file}")
            logger.info(f"Total cases: {len(self.diagnostic_cases)}, Suspicious: {suspicious_count}")
            
            return {
                'total_cases': len(self.diagnostic_cases),
                'suspicious_cases': suspicious_count,
                'missing_step_size': missing_count
            }
            
        except Exception as e:
            logger.error(f"Error exporting strategy diagnostic: {e}")
            return {}

# === Main Parser Class ===

class LogParser:
    """Manages the entire log parsing process."""

    def __init__(self):
        """Initialize the log parser."""
        self.all_lines: List[str] = []
        self.active_positions: Dict[str, Position] = {}
        self.finalized_positions: List[Position] = []
        self.debug_analyzer = DebugAnalyzer(
            debug_enabled=DEBUG_ENABLED,
            context_export_enabled=CONTEXT_EXPORT_ENABLED
        )
        self.strategy_diagnostic = StrategyParsingDiagnostic(enabled=STRATEGY_DIAGNOSTIC_ENABLED)
        self.file_line_mapping: List[Dict[str, Any]] = []

    def _process_open_event(self, line_content: str, index: int):
        """
        Process a position opening event using the new single-line parsing logic.
        Implements "Superseded" logic for handling position restarts.

        Args:
            line_content (str): The full log line that matched the 'OPENED' event.
            index (int): The line index in the log.
        """
        if self._check_for_failed_position(index, "unknown_pair"):
            return

        details = parse_position_from_open_line(
            line_content, index, self.all_lines, 
            debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
        )

        if not details:
            return

        token_pair = normalize_token_pair(details.get('token_pair'))
        if not token_pair:
            return

        # AIDEV-NOTE-CLAUDE: New "Superseded" logic implementation as discussed.
        # This handles cases where a new position for a pair is opened before the old one was closed.
        if token_pair in self.active_positions:
            old_position = self.active_positions[token_pair]
            old_position.close_reason = "Superseded"
            old_position.close_timestamp = details['timestamp']
            old_position.close_line_index = index
            self.finalized_positions.append(old_position)
            del self.active_positions[token_pair]
            logger.warning(
                f"Position for {token_pair} (opened at line {old_position.open_line_index + 1}) "
                f"was superseded by a new one at line {index + 1}. Closing the old one."
            )

        # Create and populate the new position object
        folder_wallet_id, source_file = self._get_file_info_for_line(index)
        
        # AIDEV-NOTE-CLAUDE: The Position's wallet_id is now the source of truth from the log line.
        # The folder_wallet_id is used for file tracking/grouping if needed elsewhere.
        pos = Position(
            details['timestamp'], details['version'], index,
            wallet_id=details.get('wallet_address', folder_wallet_id), 
            source_file=source_file
        )
        
        pos.token_pair = token_pair
        pos.pool_address = details.get('pool_address')
        pos.actual_strategy = details.get('actual_strategy', 'UNKNOWN')
        pos.take_profit = details.get('take_profit', 0.0)
        pos.stop_loss = details.get('stop_loss', 0.0)
        pos.initial_investment = details.get('initial_investment')
        
        self.active_positions[pos.position_id] = pos
        
        self.strategy_diagnostic.detect_missing_step_size(
            pos.actual_strategy, index, pos.initial_investment
        )

        if DETAILED_POSITION_LOGGING:
            logger.info(
                f"Opened position: {pos.position_id} ({pos.token_pair}) | "
                f"TP: {pos.take_profit}% SL: {pos.stop_loss}% | "
                f"File: {source_file}, Line: {index + 1}"
            )

    def _process_close_event_without_timestamp(self, index: int):
        """
        Process a position closing event that doesn't have a timestamp in the line.
        
        Args:
            index: Line index in log
        """
        closed_pair = None
        for i in range(index, max(-1, index - 50), -1):
            line = clean_ansi(self.all_lines[i])
            remove_match = re.search(r'Removing positions in\s+([A-Za-z0-9\s\-_()]+\-SOL)', line)
            if remove_match:
                closed_pair = remove_match.group(1).strip()
                break

        if not closed_pair:
            return
        
        matching_position = next((pos for pos in self.active_positions.values() if pos.token_pair == closed_pair), None)
        
        if matching_position:
            pos = matching_position
            pos.close_timestamp = extract_close_timestamp(self.all_lines, index, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG"))
            pos.close_reason = self._classify_close_reason(index)
            pos.close_line_index = index
            pnl_result = parse_final_pnl_with_line_info(self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG"))
            pos.final_pnl = pnl_result['pnl']
            
            self.debug_analyzer.process_close_event(pos, index)
            
            self.finalized_positions.append(pos)
            del self.active_positions[pos.position_id]
            
            if DETAILED_POSITION_LOGGING:
                pnl_line_info = f" | PnL found at line {pnl_result['line_number']}" if pnl_result['line_number'] else " | PnL not found"
                logger.info(f"Closed position: {pos.position_id} ({pos.token_pair}) | Close detected at line {index + 1} | Reason: {pos.close_reason} | PnL: {pos.final_pnl}{pnl_line_info}")

    def _classify_close_reason(self, close_line_index: int) -> str:
        """
        Classify close reason based on context around close event.
        
        Args:
            close_line_index: Line index where close was detected
            
        Returns:
            Close reason: TP, SL, LV, OOR, or other
        """
        context_lines_before, context_lines_after = 40, 5
        start_idx = max(0, close_line_index - context_lines_before)
        end_idx = min(len(self.all_lines), close_line_index + context_lines_after + 1)
        context_text = " ".join(self.all_lines[start_idx:end_idx])
        
        if "Stop loss triggered:" in context_text: return "SL"
        if "Take profit triggered:" in context_text or "TAKEPROFIT!" in context_text: return "TP"
        if "due to low volume" in context_text: return "LV"
        if "Closing position due to price range:" in context_text and "Position was out of range for" in context_text: return "OOR"
        return "other"

    def _get_file_info_for_line(self, line_index: int) -> tuple[str, str]:
        """Get wallet_id and source_file for a given line index."""
        for file_info in self.file_line_mapping:
            if file_info['start'] <= line_index < file_info['end']:
                return file_info['wallet_id'], file_info['source_file']
        return "unknown_wallet", "unknown_file"

    def run(self, log_dir: str) -> List[Dict[str, Any]]:
        """
        Run the complete log parsing process.
        
        Args:
            log_dir: Directory containing log files or subdirectories
            
        Returns:
            List of validated position dictionaries
        """
        log_files_info = []
        if os.path.exists(log_dir):
            # AIDEV-NOTE-CLAUDE: Sort files chronologically to handle cross-file positions properly
            for item in sorted(os.listdir(log_dir)):
                item_path = os.path.join(log_dir, item)
                wallet_id = "main_wallet" if os.path.isfile(item_path) else item
                
                if os.path.isdir(item_path):
                    # AIDEV-NOTE-CLAUDE: Sort files within subdirectories as well
                    files_to_scan = [os.path.join(item_path, f) for f in sorted(os.listdir(item_path)) if f.startswith("app") and ".log" in f]
                elif item.startswith("app") and ".log" in item:
                    files_to_scan = [item_path]
                else:
                    files_to_scan = []

                for f_path in files_to_scan:
                    source_file = os.path.join(wallet_id, os.path.basename(f_path)) if wallet_id != "main_wallet" else os.path.basename(f_path)
                    log_files_info.append((f_path, wallet_id, source_file))
        
        if not log_files_info:
            logger.warning(f"No log files found in {log_dir} or its subdirectories.")
            return []

        current_line_offset = 0
        for file_path, wallet_id, source_file in log_files_info:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
                self.all_lines.extend(file_lines)
                line_count = len(file_lines)
                self.file_line_mapping.append({
                    'start': current_line_offset, 'end': current_line_offset + line_count,
                    'wallet_id': wallet_id, 'source_file': source_file
                })
                current_line_offset += line_count
        
        logger.info(f"Processing {len(self.all_lines)} lines from {len(log_files_info)} log files.")
        self.debug_analyzer.set_log_lines(self.all_lines)
        self.strategy_diagnostic.set_log_data(self.all_lines, self.file_line_mapping)

        for i, line_content in enumerate(self.all_lines):
            # AIDEV-NOTE-CLAUDE: The main loop now triggers on the specific "| OPENED " string,
            # making the entry point for opening positions much more reliable.
            if "| OPENED " in line_content:
                self._process_open_event(line_content, i)
            elif "position and withdrew liquidity" in line_content:
                self._process_close_event_without_timestamp(i)

        for pos in self.active_positions.values():
            pos.close_reason = "active_at_log_end"
            self.finalized_positions.append(pos)
            logger.warning(f"Position {pos.position_id} ({pos.token_pair}) remained active at end of logs.")

        validated_positions = []
        skipped_low_pnl = 0
        for pos in self.finalized_positions:
            if pos.get_validation_errors():
                logger.warning(f"Rejected position {pos.position_id}: {', '.join(pos.get_validation_errors())}")
                continue
            if pos.final_pnl is not None and abs(pos.final_pnl) < MIN_PNL_THRESHOLD:
                skipped_low_pnl += 1
                continue
            validated_positions.append(pos.to_csv_row())
        
        logger.info(f"Found {len(self.finalized_positions)} positions. {len(validated_positions)} have complete data. {skipped_low_pnl} skipped due to low PnL.")
        return validated_positions
    
    def _check_for_failed_position(self, start_index: int, token_pair: str) -> bool:
        """
        Check if position creation failed within the lookahead window.
        A position is considered FAILED if:
        1. An explicit failure message is found.
        2. NO explicit success confirmation is found within the window.
        """
        # AIDEV-NOTE-GEMINI: Increased window to 150 to catch delayed messages.
        search_window = 150
        search_end = min(len(self.all_lines), start_index + search_window)
        
        success_found = False
        for i in range(start_index, search_end):
            line = clean_ansi(self.all_lines[i])
            
            # First, check for explicit failure
            for pattern in FAILED_POSITION_PATTERNS:
                if re.search(pattern, line, re.IGNORECASE):
                    if DETAILED_POSITION_LOGGING:
                        logger.warning(f"FAILED (Explicit): Position creation for {token_pair} at line {start_index + 1} failed with error on line {i + 1}.")
                    return True  # Failure detected

            # If no failure, check for explicit success
            if not success_found:
                for pattern in SUCCESS_CONFIRMATION_PATTERNS:
                    if re.search(pattern, line, re.IGNORECASE):
                        success_found = True
                        break # Success found, no need to check other success patterns for this line
        
        # After checking the whole window, decide the outcome
        if not success_found:
            if DETAILED_POSITION_LOGGING:
                logger.warning(f"FAILED (Silent): No success confirmation found for {token_pair} opened at line {start_index + 1} within {search_window} lines.")
            return True # No success confirmation means it's a silent failure

        # If we get here, it means success was found and no failure was found.
        if DETAILED_POSITION_LOGGING:
            logger.debug(f"SUCCESS: Position creation for {token_pair} at line {start_index + 1} confirmed successfully.")
        return False


def run_extraction(log_dir: str = LOG_DIR, output_csv: str = OUTPUT_CSV) -> bool:
    """
    Run the complete log extraction process with enhanced deduplication logic.
    
    Args:
        log_dir: Directory containing log files.
        output_csv: Output CSV file path.
        
    Returns:
        True if extraction successful, False otherwise.
    """
    logger.info("Starting data extraction from logs...")
    os.makedirs(log_dir, exist_ok=True)
    
    parser = LogParser()
    extracted_data = parser.run(log_dir)
    
    if CONTEXT_EXPORT_ENABLED and parser.debug_analyzer.get_context_count() > 0:
        context_stats = parser.debug_analyzer.export_analysis(CONTEXT_EXPORT_FILE)
        logger.info(f"Context export statistics: {dict(context_stats)}")
    
    if STRATEGY_DIAGNOSTIC_ENABLED:
        strategy_stats = parser.strategy_diagnostic.export_diagnostic(STRATEGY_DIAGNOSTIC_FILE)
        logger.info(f"Strategy diagnostic statistics: {dict(strategy_stats)}")
    
    if not extracted_data:
        logger.error("Failed to extract any complete positions. CSV file will not be created.")
        return False
        
    try:
        existing_data = []
        if os.path.exists(output_csv):
            with open(output_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_data = [row for row in reader]
        
        # AIDEV-NOTE-CLAUDE: Enhanced deduplication using pool_address + open_timestamp
        existing_position_ids = {row['position_id'] for row in existing_data}
        existing_universal_ids = {f"{row['pool_address']}_{row['open_timestamp']}" for row in existing_data if row['pool_address'] and row['open_timestamp']}

        # Create mapping of existing positions for update logic
        existing_positions_map = {f"{row['pool_address']}_{row['open_timestamp']}" : row 
                                for row in existing_data 
                                if row['pool_address'] and row['open_timestamp']}

        processed_data = []
        updated_count = 0
        skipped_count = 0

        for pos in extracted_data:
            # Skip positions missing pool_address (these would fail validation anyway)
            if not pos['pool_address'] or not pos['open_timestamp']:
                logger.warning(f"Skipping position {pos['position_id']} - missing pool_address or open_timestamp")
                continue
                
            universal_id = f"{pos['pool_address']}_{pos['open_timestamp']}"
            
            if pos['position_id'] in existing_position_ids:
                # Skip exact duplicate
                skipped_count += 1
                continue
            elif universal_id in existing_universal_ids:
                # Found same position (pool_address + open_timestamp)
                existing_pos = existing_positions_map[universal_id]
                
                # Check if we should update: existing is incomplete and new is complete
                if (existing_pos['close_reason'] == 'active_at_log_end' and 
                    pos['close_reason'] != 'active_at_log_end' and 
                    pos['pnl_sol'] is not None):
                    # Update existing position with complete data
                    processed_data.append(pos)
                    updated_count += 1
                    logger.info(f"Updated position {universal_id}: {existing_pos['close_reason']} → {pos['close_reason']}")
                else:
                    # Skip duplicate (don't import second occurrence)
                    skipped_count += 1
                    logger.info(f"Skipped duplicate position {universal_id}")
                    continue
            else:
                # New position
                processed_data.append(pos)

        new_data = processed_data
        
        if new_data or updated_count > 0:
            # AIDEV-NOTE-CLAUDE: Merge existing + new data, removing positions that were updated
            updated_universal_ids = {f"{pos['pool_address']}_{pos['open_timestamp']}" 
                                   for pos in new_data 
                                   if f"{pos['pool_address']}_{pos['open_timestamp']}" in existing_universal_ids}
            
            # Keep existing positions that weren't updated
            filtered_existing = [pos for pos in existing_data 
                                if not (pos['pool_address'] and pos['open_timestamp'] and 
                                       f"{pos['pool_address']}_{pos['open_timestamp']}" in updated_universal_ids)]
            
            all_data = filtered_existing + new_data
            all_data.sort(key=lambda x: x['open_timestamp'])
            
            with open(output_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
            
            logger.info(f"Successfully processed {len(all_data)} total positions:")
            logger.info(f"  - {len(filtered_existing)} existing positions retained")
            logger.info(f"  - {len(new_data) - updated_count} new positions added")
            logger.info(f"  - {updated_count} positions updated (incomplete → complete)")
            logger.info(f"  - {skipped_count} duplicate positions skipped")
        else:
            logger.info("No new positions to add. CSV file unchanged.")
            
        return True
        
    except Exception as e:
        logger.error(f"Error processing CSV file {output_csv}: {e}", exc_info=True)
        return False


if __name__ == "__main__":
    run_extraction()