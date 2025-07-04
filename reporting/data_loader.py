"""
Data Loader and Preparator for Portfolio Analytics

Handles loading, validation, cleaning, and preparation of position data
from CSV files.
"""

import logging
from datetime import datetime, timedelta
import pandas as pd

logger = logging.getLogger(__name__)


def _parse_custom_timestamp(ts_str: str) -> pd.Timestamp:
    """
    Parse non-standard timestamps like "MM/DD-HH:MM:SS".
    Handles the "24:XX" hour format by rolling over to the next day.
    """
    # AIDEV-FIX: Add a guard for non-string or empty inputs.
    if not isinstance(ts_str, str) or not ts_str or pd.isna(ts_str):
        return pd.NaT

    try:
        # Format: "05/12-20:57:08" -> "2025-05-12 20:57:08"
        date_part, time_part = ts_str.split('-')
        month, day = date_part.split('/')

        hour, minute, second = time_part.split(':')
        hour = int(hour)

        # Assume current year (2025) - this may need adjustment if data spans years
        # AIDEV-NOTE: This assumes data is from the current or a future year.
        # For historical data spanning years, a more sophisticated logic might be needed.
        current_year = datetime.now().year 
        base_date = datetime(current_year, int(month), int(day))

        # Handle hour 24 as next day hour 0
        if hour >= 24:
            hour = hour - 24
            base_date = base_date + timedelta(days=1)

        final_datetime = base_date.replace(hour=hour, minute=int(minute), second=int(second))
        return pd.to_datetime(final_datetime)

    except Exception as e:
        logger.warning(f"Failed to parse custom timestamp '{ts_str}': {e}")
        return pd.NaT


def load_and_prepare_positions(file_path: str, min_threshold: float) -> pd.DataFrame:
    """
    Load, validate, and prepare positions data from a CSV file.

    This function includes logic for:
    - Reading the CSV.
    - Mapping column names from the raw CSV to a standardized format.
    - Parsing strategy and step size from raw strategy strings.
    - Handling standard and non-standard timestamp formats.
    - Filtering positions based on a minimum PnL threshold.

    Args:
        file_path (str): Path to the positions CSV file.
        min_threshold (float): Minimum absolute PnL in SOL to include a position.

    Returns:
        pd.DataFrame: A cleaned and prepared DataFrame of positions.

    Raises:
        FileNotFoundError: If the positions file doesn't exist.
        ValueError: If required columns are missing after mapping.
    """
    try:
        positions_df = pd.read_csv(file_path)
        logger.info(f"Loaded {len(positions_df)} positions from {file_path}")
    except FileNotFoundError:
        logger.error(f"Positions file not found: {file_path}")
        raise

    # Validate required columns (no mapping needed)
    required_csv_columns = ['pnl_sol', 'strategy_raw', 'investment_sol']
    missing_csv_columns = [col for col in required_csv_columns if col not in positions_df.columns]
    if missing_csv_columns:
        raise ValueError(f"Missing required CSV columns: {missing_csv_columns}")

    # Extract strategy and step_size from strategy_raw
    positions_df['strategy'] = positions_df['strategy_raw'].str.extract(r'(Bid-Ask|Spot)', expand=False)
    positions_df['step_size'] = positions_df['strategy_raw'].str.extract(r'(SIXTYNINE|MEDIUM|NARROW|WIDE)', expand=False)
    positions_df['strategy'] = positions_df['strategy'].fillna('Bid-Ask')
    positions_df['step_size'] = positions_df['step_size'].fillna('MEDIUM')
    logger.info(f"Strategies found: {positions_df['strategy'].value_counts().to_dict()}")
    logger.info(f"Step sizes found: {positions_df['step_size'].value_counts().to_dict()}")

    # Validate final required columns
    required_columns = ['pnl_sol', 'strategy', 'step_size', 'investment_sol']
    missing_columns = [col for col in required_columns if col not in positions_df.columns]
    if missing_columns:
        raise ValueError(f"Missing required columns after mapping: {missing_columns}")

    # Convert timestamps with robust mixed-format handling
    for col in ['open_timestamp', 'close_timestamp']:
        if col in positions_df.columns:
            # AIDEV-FIX: Robustly handle mixed standard and custom timestamp formats.
            original_ts_col = positions_df[col].copy()
            positions_df[col] = pd.to_datetime(original_ts_col, errors='coerce')
            
            failed_indices = positions_df[col].isnull()
            if failed_indices.any():
                logger.info(f"Applying custom timestamp parser for {failed_indices.sum()} values in '{col}'")
                # Apply custom parser only to the original strings of the failed rows
                custom_parsed = original_ts_col[failed_indices].apply(_parse_custom_timestamp)
                positions_df.loc[failed_indices, col] = custom_parsed

            # Remove any rows where timestamp parsing ultimately failed
            initial_rows = len(positions_df)
            positions_df = positions_df.dropna(subset=[col])
            if len(positions_df) < initial_rows:
                logger.warning(f"Removed {initial_rows - len(positions_df)} rows with unparseable timestamps in '{col}'")


    if 'open_timestamp' in positions_df.columns and not positions_df.empty:
        logger.info(f"Successfully parsed timestamps. Date range: {positions_df['open_timestamp'].min()} to {positions_df['close_timestamp'].max()}")

    # Apply minimum threshold filter
    initial_count = len(positions_df)
    positions_df = positions_df[abs(positions_df['pnl_sol']) >= min_threshold].copy()
    filtered_count = len(positions_df)
    if filtered_count < initial_count:
        logger.info(f"Filtered {initial_count - filtered_count} positions below {min_threshold} SOL threshold")

    return positions_df