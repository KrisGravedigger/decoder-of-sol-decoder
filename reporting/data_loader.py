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

    This function includes logic for:
    - Reading the CSV.
    - Parsing strategy and step size from raw strategy strings.
    - Handling standard and non-standard timestamp formats.
    - Filtering positions based on a minimum PnL threshold.
    - Dropping rows with unparseable or missing timestamps needed for analysis.

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

    # Validate required columns
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

    # Convert timestamps with robust mixed-format handling
    for col in ['open_timestamp', 'close_timestamp']:
        if col in positions_df.columns:
            # AIDEV-NOTE-CLAUDE: Logic now handles active positions by dropping them from analysis.
            initial_rows = len(positions_df)
            
            # Convert to pandas datetime, coercing errors to NaT (Not a Time)
            # This handles both standard formats and blank values (like in active_at_log_end)
            positions_df[col] = pd.to_datetime(positions_df[col], errors='coerce')
            
            failed_indices = positions_df[col].isnull()
            if failed_indices.any():
                logger.info(f"Applying custom timestamp parser for {failed_indices.sum()} values in '{col}'")
                # Apply custom parser only where standard parsing failed
                # The custom parser returns datetime or None (which becomes NaT)
                custom_parsed = positions_df.loc[failed_indices, col].astype(str).apply(_parse_custom_timestamp)
                positions_df.loc[failed_indices, col] = pd.to_datetime(custom_parsed, errors='coerce')

            # AIDEV-NOTE-CLAUDE: This is a critical step. It removes any rows where the timestamp
            # could not be parsed, which includes positions with 'active_at_log_end'
            # as they have a null close_timestamp. This makes the analysis resilient.
            positions_df = positions_df.dropna(subset=[col])
            if len(positions_df) < initial_rows:
                logger.warning(
                    f"Removed {initial_rows - len(positions_df)} rows with unparseable or missing "
                    f"timestamps in '{col}'. This is expected for 'active_at_log_end' positions."
                )

    if 'open_timestamp' in positions_df.columns and not positions_df.empty:
        logger.info(f"Successfully parsed timestamps. Date range: {positions_df['open_timestamp'].min()} to {positions_df['close_timestamp'].max()}")

    # Apply minimum threshold filter
    initial_count = len(positions_df)
    positions_df = positions_df[abs(positions_df['pnl_sol']) >= min_threshold].copy()
    filtered_count = len(positions_df)
    if filtered_count < initial_count:
        logger.info(f"Filtered {initial_count - filtered_count} positions below {min_threshold} SOL threshold")

    return positions_df