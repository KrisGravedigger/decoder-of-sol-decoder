#!/usr/bin/env python3
"""
Backfill Peak PnL Data for Existing Positions

This script adds peak PnL and total fees data to existing positions in CSV.
Creates a backup before modification.
"""

import os
import sys
import csv
import logging
import shutil
from datetime import datetime
from typing import Dict, List, Optional
import yaml

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from extraction.parsing_utils import extract_peak_pnl_from_logs, extract_total_fees_from_logs, clean_ansi
from reporting.data_loader import _parse_custom_timestamp

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('BackfillPeakPnL')


def load_config() -> Dict:
    """Load configuration from portfolio_config.yaml."""
    config_path = "reporting/config/portfolio_config.yaml"
    try:
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        logger.warning(f"Config file not found: {config_path}, using defaults")
        return {}


def load_log_files(log_dir: str = "input") -> tuple[List[str], List[Dict]]:
    """
    Load all log files and create file mapping.
    
    Returns:
        Tuple of (all_lines, file_line_mapping)
    """
    all_lines = []
    file_line_mapping = []
    current_line_offset = 0
    
    for item in sorted(os.listdir(log_dir)):
        item_path = os.path.join(log_dir, item)
        
        if os.path.isdir(item_path):
            # Process subdirectory
            log_files = [f for f in sorted(os.listdir(item_path)) 
                        if f.startswith("app") and ".log" in f]
            for log_file in log_files:
                file_path = os.path.join(item_path, log_file)
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    file_lines = f.readlines()
                    all_lines.extend(file_lines)
                    line_count = len(file_lines)
                    file_line_mapping.append({
                        'start': current_line_offset,
                        'end': current_line_offset + line_count,
                        'file': os.path.join(item, log_file)
                    })
                    current_line_offset += line_count
        elif item.startswith("app") and ".log" in item:
            # Process file in root directory
            with open(item_path, 'r', encoding='utf-8', errors='ignore') as f:
                file_lines = f.readlines()
                all_lines.extend(file_lines)
                line_count = len(file_lines)
                file_line_mapping.append({
                    'start': current_line_offset,
                    'end': current_line_offset + line_count,
                    'file': item
                })
                current_line_offset += line_count
    
    logger.info(f"Loaded {len(all_lines)} lines from {len(file_line_mapping)} log files")
    return all_lines, file_line_mapping


def backfill_position(position: Dict, all_lines: List[str], config: Dict) -> Dict:
    """
    Backfill peak PnL data for a single position.
    
    Args:
        position: Position data from CSV
        all_lines: All log lines
        config: Configuration dictionary
        
    Returns:
        Updated position dictionary
    """
    # Skip if already has peak PnL data
    if (position.get('max_profit_during_position') is not None or 
        position.get('max_loss_during_position') is not None):
        return position
    
    # Skip active positions
    if position.get('close_reason') == 'active_at_log_end':
        logger.debug(f"Skipping active position {position.get('position_id')}")
        return position
    
    # Get line indices
    try:
        open_line_index = int(position.get('open_line_index', -1))
        close_line_index = int(position.get('close_line_index', -1))
    except (ValueError, TypeError):
        logger.warning(f"Invalid line indices for position {position.get('position_id')}")
        return position
    
    if open_line_index < 0 or close_line_index < 0:
        logger.warning(f"Missing line indices for position {position.get('position_id')}")
        return position
    
    # Get significance threshold from config
    significance_threshold = config.get('tp_sl_analysis', {}).get('significance_threshold', 0.01)
    
    # Extract peak PnL
    peak_pnl_data = extract_peak_pnl_from_logs(
        all_lines, open_line_index, close_line_index, significance_threshold
    )
    
    # Smart extraction based on close reason
    close_reason = position.get('close_reason', 'other')
    
    if close_reason == 'TP':
        # We already know max profit (final PnL)
        try:
            final_pnl = float(position.get('pnl_sol', 0))
            if final_pnl > 0:
                position['max_profit_during_position'] = round((final_pnl / float(position.get('investment_sol', 1))) * 100, 2)
        except (ValueError, TypeError):
            pass
        position['max_loss_during_position'] = peak_pnl_data.get('max_loss_pct')
        
    elif close_reason == 'SL':
        # We already know max loss (final PnL)
        position['max_profit_during_position'] = peak_pnl_data.get('max_profit_pct')
        try:
            final_pnl = float(position.get('pnl_sol', 0))
            if final_pnl < 0:
                position['max_loss_during_position'] = round((final_pnl / float(position.get('investment_sol', 1))) * 100, 2)
        except (ValueError, TypeError):
            pass
            
    else:  # 'LV', 'OOR', 'other'
        # Extract both
        position['max_profit_during_position'] = peak_pnl_data.get('max_profit_pct')
        position['max_loss_during_position'] = peak_pnl_data.get('max_loss_pct')
    
    # Extract total fees
    total_fees = extract_total_fees_from_logs(
        all_lines, open_line_index, close_line_index
    )
    position['total_fees_collected'] = total_fees
    
    # Log progress
    if peak_pnl_data.get('samples_found', 0) > 0:
        logger.info(f"Position {position.get('position_id')}: "
                   f"Max profit: {position.get('max_profit_during_position')}%, "
                   f"Max loss: {position.get('max_loss_during_position')}%, "
                   f"Fees: {position.get('total_fees_collected')} SOL, "
                   f"Samples: {peak_pnl_data.get('samples_found')}")
    else:
        logger.warning(f"No PnL samples found for position {position.get('position_id')}")
    
    return position


def main():
    """Main backfill process."""
    csv_file = "positions_to_analyze.csv"
    
    if not os.path.exists(csv_file):
        logger.error(f"CSV file not found: {csv_file}")
        logger.error("Please run extraction first to generate positions_to_analyze.csv")
        return 1
    
    # Load configuration
    config = load_config()
    logger.info("Loaded configuration")
    
    # Create backup
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = f"{csv_file}.backup_{timestamp}"
    shutil.copy2(csv_file, backup_file)
    logger.info(f"Created backup: {backup_file}")
    
    # Load existing positions
    positions = []
    with open(csv_file, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        positions = list(reader)
    
    logger.info(f"Loaded {len(positions)} positions from CSV")
    
    # Load all log files
    all_lines, file_mapping = load_log_files()
    
    # Process positions
    updated_count = 0
    error_count = 0
    
    for i, position in enumerate(positions):
        try:
            original_has_data = (
                position.get('max_profit_during_position') is not None or 
                position.get('max_loss_during_position') is not None
            )
            
            updated_position = backfill_position(position, all_lines, config)
            
            new_has_data = (
                updated_position.get('max_profit_during_position') is not None or 
                updated_position.get('max_loss_during_position') is not None
            )
            
            if not original_has_data and new_has_data:
                updated_count += 1
            
            positions[i] = updated_position
            
            if (i + 1) % 10 == 0:
                logger.info(f"Processed {i + 1}/{len(positions)} positions...")
                
        except Exception as e:
            logger.error(f"Error processing position {position.get('position_id')}: {e}")
            error_count += 1
    
    # Write updated CSV
    if positions:
        # Get all unique fieldnames
        all_fieldnames = set()
        for pos in positions:
            all_fieldnames.update(pos.keys())
        
        # Ensure new fields are included
        required_fields = ['max_profit_during_position', 'max_loss_during_position', 'total_fees_collected']
        all_fieldnames.update(required_fields)
        
        # Sort fieldnames for consistent output
        fieldnames = sorted(list(all_fieldnames))
        
        with open(csv_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(positions)
        
        logger.info(f"Updated CSV written to {csv_file}")
    
    # Summary
    logger.info("=" * 60)
    logger.info("BACKFILL SUMMARY:")
    logger.info(f"Total positions: {len(positions)}")
    logger.info(f"Updated with new data: {updated_count}")
    logger.info(f"Errors: {error_count}")
    logger.info(f"Backup saved to: {backup_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())