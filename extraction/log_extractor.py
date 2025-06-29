import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

# === MAIN DEBUG CONFIGURATION ===
# AIDEV-NOTE-CLAUDE: Master debug controls - these override settings in debug_analyzer.py
DEBUG_ENABLED = False                    # Master switch for all debug features
DEBUG_LEVEL = "DEBUG"                   # "DEBUG" for detailed logs, "INFO" for standard logs
CONTEXT_EXPORT_ENABLED = True          # Enable/disable context export completely
DETAILED_POSITION_LOGGING = True       # Enable/disable detailed position event logging

# Import our modules - updated paths for extraction/ subfolder
from models import Position
from parsing_utils import (
    clean_ansi, find_context_value, normalize_token_pair,
    extract_close_timestamp, parse_strategy_from_context,
    parse_initial_investment, parse_final_pnl_with_line_info
)
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

    def _process_open_event(self, timestamp: str, version: str, index: int):
        """
        Process a position opening event.
        
        Args:
            timestamp: Event timestamp
            version: Bot version
            index: Line index in log
        """
        token_pair = normalize_token_pair(
            find_context_value([r'TARGET POOL:\s*(.*-SOL)'], self.all_lines, index, 50)
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
            existing_position.retry_count += 1
            
            # Update only the fields that might change with retry
            existing_position.open_timestamp = timestamp
            existing_position.bot_version = version
            existing_position.open_line_index = index
            
            # Re-parse pool and strategy (might have changed)
            existing_position.pool_address = find_context_value([
                r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
                r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
            ], self.all_lines, index, 50)
            
            existing_position.actual_strategy = parse_strategy_from_context(
                self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            
            # CRITICAL: Re-parse investment amount
            existing_position.initial_investment = parse_initial_investment(
                self.all_lines, index, 100, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            
            # Don't log every retry, will log summary when position is finalized
            return  # Don't create new position!
            
        # Determine wallet_id and source_file based on line index
        wallet_id, source_file = self._get_file_info_for_line(index)

        # Only create new position if none exists
        pos = Position(timestamp, version, index, wallet_id=wallet_id, source_file=source_file)
        pos.token_pair = token_pair
        
        pos.pool_address = find_context_value([
            r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
            r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
        ], self.all_lines, index, 50)
        
        pos.actual_strategy = parse_strategy_from_context(
            self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
        )
        
        # CRITICAL CHANGE: Search for investment in wider forward-looking window
        pos.initial_investment = parse_initial_investment(
            self.all_lines, index, 100, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
        )
        
        self.active_positions[pos.position_id] = pos
        
        if DETAILED_POSITION_LOGGING:
            retry_info = f" (succeeded after {pos.retry_count} retries)" if pos.retry_count > 0 else ""
            logger.info(f"Opened position: {pos.position_id} ({pos.token_pair}) | Open detected at line {index + 1}{retry_info}")

    def _process_close_event_without_timestamp(self, index: int):
        """
        Process a position closing event that doesn't have timestamp in the line.
        
        Args:
            index: Line index in log
        """
        if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
            logger.info(f"Processing close event at line {index + 1}")
            line_clean = clean_ansi(self.all_lines[index])
            logger.info(f"Cleaned line: {line_clean.strip()}")
        
        line_clean = clean_ansi(self.all_lines[index])
        
        # Extract token pair from "Removing positions in" line in lookback
        closed_pair = None
        for i in range(index, max(-1, index - 50), -1):
            line = clean_ansi(self.all_lines[i])
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
            pos.close_timestamp = extract_close_timestamp(
                self.all_lines, index, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            pos.close_reason = self._classify_close_reason(index)
            pos.close_line_index = index  # AIDEV-NOTE-CLAUDE: Store for context export
            pnl_result = parse_final_pnl_with_line_info(
                self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            pos.final_pnl = pnl_result['pnl']
            
            # AIDEV-NOTE-CLAUDE: Process close event for debug analysis
            self.debug_analyzer.process_close_event(pos, index)
            
            self.finalized_positions.append(pos)
            # Find and delete by matching position ID
            for pos_id, active_pos in list(self.active_positions.items()):
                if active_pos == pos:
                    del self.active_positions[pos_id]
                    break
            
            if DETAILED_POSITION_LOGGING:
                pnl_line_info = f" | PnL found at line {pnl_result['line_number']}" if pnl_result['line_number'] else " | PnL not found"
                logger.info(f"Closed position: {pos.position_id} ({pos.token_pair}) | Close detected at line {index + 1} | Reason: {pos.close_reason} | PnL: {pos.final_pnl}{pnl_line_info}")
        else:
            if DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG":
                logger.debug(f"Found closing for {closed_pair} at line {index + 1}, but no active position found for this pair.")
    
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

    def _get_file_info_for_line(self, line_index: int) -> tuple:
        """
        Get wallet_id and source_file for a given line index.
        
        Args:
            line_index: Index of line in all_lines
            
        Returns:
            Tuple of (wallet_id, source_file)
        """
        # Find which file this line belongs to
        for file_info in self.file_line_mapping:
            if file_info['start'] <= line_index < file_info['end']:
                return file_info['wallet_id'], file_info['source_file']
        
        # Fallback if not found
        return "unknown_wallet", "unknown_file"

    def run(self, log_dir: str) -> List[Dict[str, Any]]:
        """
        Run the complete log parsing process.
        
        Args:
            log_dir: Directory containing log files or subdirectories with log files
            
        Returns:
            List of validated position dictionaries
        """
        # AIDEV-NOTE-CLAUDE: Enhanced to support wallet subdirectories
        log_files_info = []  # List of tuples: (file_path, wallet_id, source_file)
        
        # Check for direct log files in log_dir
        if os.path.exists(log_dir):
            direct_files = [f for f in os.listdir(log_dir) if f.startswith("app") and ".log" in f]
            for f in direct_files:
                log_files_info.append((os.path.join(log_dir, f), "main_wallet", f))
            
            # Check for subdirectories (wallet folders)
            for item in os.listdir(log_dir):
                item_path = os.path.join(log_dir, item)
                if os.path.isdir(item_path):
                    wallet_id = item  # Subfolder name = wallet_id
                    wallet_files = [f for f in os.listdir(item_path) if f.startswith("app") and ".log" in f]
                    for f in wallet_files:
                        full_path = os.path.join(item_path, f)
                        source_file = f"{wallet_id}/{f}"  # Include wallet in source path
                        log_files_info.append((full_path, wallet_id, source_file))
        
        if not log_files_info:
            logger.warning(f"No log files found in {log_dir} or its subdirectories")
            return []

        # Process all log files and track their sources
        file_line_mapping = []  # Track which lines come from which files
        
        for file_path, wallet_id, source_file in log_files_info:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
                start_index = len(self.all_lines)
                self.all_lines.extend(file_lines)
                end_index = len(self.all_lines)
                
                # Track line ranges for this file
                file_line_mapping.append({
                    'start': start_index,
                    'end': end_index,
                    'wallet_id': wallet_id,
                    'source_file': source_file
                })
        
        logger.info(f"Processing {len(self.all_lines)} lines from {len(log_files_info)} log files across {len(set(info[1] for info in log_files_info))} wallets")
        
        # Store file mapping for position creation
        self.file_line_mapping = file_line_mapping

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
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', clean_ansi(line_content))
            if not timestamp_match: 
                continue
            
            timestamp = timestamp_match.group(1)
            version_match = re.search(r'(v[\d.]+)', clean_ansi(line_content))
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
                    timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', clean_ansi(create_line))
                    if timestamp_match:
                        timestamp = timestamp_match.group(1)
                        version_match = re.search(r'(v[\d.]+)', clean_ansi(create_line))
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


def run_extraction(log_dir: str = LOG_DIR, output_csv: str = OUTPUT_CSV) -> bool:
    """
    Run the complete log extraction process.
    
    Args:
        log_dir: Directory containing log files (default: "input")
        output_csv: Output CSV file path (default: "positions_to_analyze.csv")
        
    Returns:
        True if extraction successful, False otherwise
    """
    # AIDEV-TODO-CLAUDE: Future enhancement - add options for duplicate handling
    # (skip, update, or prompt user choice) and custom sorting preferences
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
        # Load existing data if CSV exists
        existing_data = []
        existing_position_ids = set()
        
        if os.path.exists(output_csv):
            with open(output_csv, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                existing_data = list(reader)
                existing_position_ids = {row['position_id'] for row in existing_data}
            logger.info(f"Loaded {len(existing_data)} existing positions from {output_csv}")
        
        # Filter out duplicate position_ids from new data
        new_data = [pos for pos in extracted_data if pos['position_id'] not in existing_position_ids]
        skipped_duplicates = len(extracted_data) - len(new_data)
        
        if skipped_duplicates > 0:
            logger.info(f"Skipped {skipped_duplicates} duplicate positions (already in CSV)")
        
        if not new_data and existing_data:
            logger.info("No new positions to add. CSV file unchanged.")
            return True
        
        # Combine existing + new data
        all_data = existing_data + new_data
        
        # Sort by open_timestamp (chronological order)
        all_data.sort(key=lambda x: x['open_timestamp'])
        
        # Write combined data
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            if all_data:  # Safety check
                writer = csv.DictWriter(f, fieldnames=all_data[0].keys())
                writer.writeheader()
                writer.writerows(all_data)
        
        logger.info(f"Successfully saved {len(all_data)} total positions ({len(new_data)} new, {len(existing_data)} existing) to {output_csv}")
        return True
        
    except Exception as e:
        logger.error(f"Error processing CSV file {output_csv}: {e}")
        return False


if __name__ == "__main__":
    run_extraction()