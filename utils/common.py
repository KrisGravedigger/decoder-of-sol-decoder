import yaml
import logging

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