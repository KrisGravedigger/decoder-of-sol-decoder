import os
import re
import csv
import logging
from typing import Dict, List, Optional, Any
import sys
from pathlib import Path

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
    extract_close_timestamp, parse_strategy_from_context,
    parse_initial_investment, parse_final_pnl_with_line_info
)
from tools.debug_analyzer import DebugAnalyzer

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
        self.debug_analyzer = DebugAnalyzer(
            debug_enabled=DEBUG_ENABLED,
            context_export_enabled=CONTEXT_EXPORT_ENABLED
        )
        self.file_line_mapping: List[Dict[str, Any]] = []

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
        
        existing_position = next((pos for pos in self.active_positions.values() if pos.token_pair == token_pair), None)

        if existing_position:
            existing_position.retry_count += 1
            existing_position.open_timestamp = timestamp
            existing_position.bot_version = version
            existing_position.open_line_index = index
            existing_position.pool_address = find_context_value([
                r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
                r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
            ], self.all_lines, index, 50)
            existing_position.actual_strategy = parse_strategy_from_context(
                self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            existing_position.initial_investment = parse_initial_investment(
                self.all_lines, index, 100, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
            )
            return
            
        wallet_id, source_file = self._get_file_info_for_line(index)

        pos = Position(timestamp, version, index, wallet_id=wallet_id, source_file=source_file)
        pos.token_pair = token_pair
        pos.pool_address = find_context_value([
            r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', 
            r'dexscreener\.com/solana/([a-zA-Z0-9]+)'
        ], self.all_lines, index, 50)
        pos.actual_strategy = parse_strategy_from_context(
            self.all_lines, index, 50, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
        )
        pos.initial_investment = parse_initial_investment(
            self.all_lines, index, 100, debug_enabled=(DEBUG_ENABLED and DEBUG_LEVEL == "DEBUG")
        )
        
        self.active_positions[pos.position_id] = pos
        
        if DETAILED_POSITION_LOGGING:
            logger.info(f"Opened position: {pos.position_id} ({pos.token_pair}) | Open detected at line {index + 1}")

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

        for i, line_content in enumerate(self.all_lines):
            if "position and withdrew liquidity" in line_content:
                self._process_close_event_without_timestamp(i)
                continue
            
            timestamp_match = re.search(r'v[\d.]+-(\d{2}/\d{2}-\d{2}:\d{2}:\d{2})', clean_ansi(line_content))
            if not timestamp_match: continue
            
            timestamp = timestamp_match.group(1)
            version = re.search(r'(v[\d.]+)', clean_ansi(line_content)).group(1) if re.search(r'(v[\d.]+)', clean_ansi(line_content)) else "vUNKNOWN"

            if "Creating a position" in line_content:
                self._process_open_event(timestamp, version, i)

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
                    pos['final_pnl_sol_from_log'] is not None):
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