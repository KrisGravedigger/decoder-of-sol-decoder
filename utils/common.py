import yaml
import logging
import re
from datetime import datetime
from typing import List

logger = logging.getLogger(__name__)

def load_main_config() -> dict:
    """Loads the main YAML configuration."""
    try:
        with open("reporting/config/portfolio_config.yaml", 'r') as f:
            return yaml.safe_load(f)
    except (FileNotFoundError, yaml.YAMLError) as e:
        logger.error(f"Could not load or parse portfolio_config.yaml: {e}", exc_info=True)
        return {}

def print_header(title: str):
    """Prints a formatted header."""
    print("\n" + "="*70)
    print(f"--- {title.upper()} ---")
    print("="*70)

def extract_date_from_strategy_name(strategy_name: str) -> datetime:
    """
    Extract date from strategy name format: {strategy}_TP{tp}_SL{sl}_{YYYY-MM-DD}_{hash}
    
    Args:
        strategy_name: Strategy instance ID containing date
        
    Returns:
        datetime object extracted from name, or datetime.min if not found
        
    Example:
        "Spot (1-Sided) SIXTYNINE_TP8_SL9_2025-08-02_f52538" -> datetime(2025, 8, 2)
    """
    try:
        # Pattern to match YYYY-MM-DD format in strategy names
        date_pattern = r'(\d{4}-\d{2}-\d{2})'
        match = re.search(date_pattern, strategy_name)
        
        if match:
            date_str = match.group(1)
            return datetime.strptime(date_str, '%Y-%m-%d')
        else:
            logger.warning(f"Could not extract date from strategy name: {strategy_name}")
            return datetime.min
            
    except Exception as e:
        logger.error(f"Error extracting date from strategy name '{strategy_name}': {e}")
        return datetime.min

def sort_strategies_by_date_descending(strategy_list: List[str]) -> List[str]:
    """
    Sort strategy names by their embedded date in descending order (newest first).
    
    Args:
        strategy_list: List of strategy instance IDs
        
    Returns:
        List of strategy IDs sorted by date (newest first)
    """
    try:
        # Create tuples of (strategy_name, extracted_date) and sort by date descending
        strategy_dates = [(strategy, extract_date_from_strategy_name(strategy)) for strategy in strategy_list]
        sorted_strategies = sorted(strategy_dates, key=lambda x: x[1], reverse=True)
        return [strategy for strategy, _ in sorted_strategies]
    except Exception as e:
        logger.error(f"Error sorting strategies by date: {e}")
        return strategy_list  # Return original list if sorting fails