"""
Data Loader and Preparator for Portfolio Analytics

Handles loading, validation, cleaning, and preparation of position data
from CSV files.
"""
import logging
import pandas as pd
import sys
from pathlib import Path

# AIDEV-NOTE-CLAUDE: This ensures project root is on the path for module resolution
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

# AIDEV-NOTE-CLAUDE: Import moved to a shared utility to avoid code duplication.
from extraction.parsing_utils import _parse_custom_timestamp

logger = logging.getLogger(__name__)


def load_and_prepare_positions(file_path: str, min_threshold: float) -> pd.DataFrame:
    """
    Load, validate, and prepare positions data from a CSV file.

    This function is now the SINGLE SOURCE OF TRUTH for data loading and cleaning,
    including robust, multi-format timestamp parsing.
    """
    try:
        positions_df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(positions_df)} positions from {file_path}")
    except FileNotFoundError:
        logger.error(f"Positions file not found: {file_path}")
        raise

    # AIDEV-NOTE-GEMINI: Standardized column name validation
    required_csv_columns = ['pnl_sol', 'strategy_raw', 'investment_sol']
    if not all(col in positions_df.columns for col in required_csv_columns):
        raise ValueError(f"Missing one or more required columns in {file_path}: {required_csv_columns}")

    # Extract strategy and step_size
    positions_df['strategy'] = positions_df['strategy_raw'].str.extract(r'(Bid-Ask|Spot)', expand=False).fillna('Bid-Ask')
    positions_df['step_size'] = positions_df['strategy_raw'].str.extract(r'(SIXTYNINE|MEDIUM|NARROW|WIDE)', expand=False).fillna('MEDIUM')
    
    # --- Robust Timestamp Parsing ---
    for col in ['open_timestamp', 'close_timestamp']:
        if col in positions_df.columns:
            initial_rows = len(positions_df)
            
            # Convert to string to handle various inputs, then parse
            # This ensures that previously parsed datetime objects are also handled
            str_timestamps = positions_df[col].astype(str)
            parsed_dates = []
            for ts_str in str_timestamps:
                if pd.isna(ts_str) or ts_str.lower() in ['nan', 'nat', '']:
                    parsed_dates.append(pd.NaT)
                    continue
                
                # Try standard parsing first (it's faster)
                dt = pd.to_datetime(ts_str, errors='coerce')
                
                # If standard fails, try custom parser
                if pd.isna(dt):
                    try:
                        dt = _parse_custom_timestamp(ts_str)
                    except (ValueError, IndexError):
                        dt = pd.NaT # Failed both parsers
                
                parsed_dates.append(dt)

            positions_df[col] = pd.Series(parsed_dates, index=positions_df.index)

            # Drop rows where parsing failed for either timestamp
            positions_df = positions_df.dropna(subset=[col])
            
            if len(positions_df) < initial_rows:
                logger.warning(
                    f"Removed {initial_rows - len(positions_df)} rows with unparseable or missing "
                    f"timestamps in '{col}'. This is expected for active positions."
                )

    # Apply minimum threshold filter
    initial_count = len(positions_df)
    positions_df = positions_df[abs(positions_df['pnl_sol']) >= min_threshold].copy()
    if filtered_count := len(positions_df) < initial_count:
        logger.info(f"Filtered {initial_count - filtered_count} positions below {min_threshold} SOL threshold")

    if not positions_df.empty:
        logger.info(f"Data preparation complete. Returning {len(positions_df)} valid positions.")
        
    return positions_df