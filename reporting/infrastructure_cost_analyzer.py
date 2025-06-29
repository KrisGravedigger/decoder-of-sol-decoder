"""
Infrastructure Cost Analyzer for Portfolio Analytics

Handles daily flat allocation of monthly infrastructure costs
and conversion between USD and SOL using historical rates.
"""

import logging
import json
import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import yaml

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class InfrastructureCostAnalyzer:
    """
    Analyzes infrastructure costs and allocates them to trading positions.
    
    Handles daily flat allocation of monthly costs and currency conversion
    using historical SOL/USDC exchange rates.
    """
    
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml"):
        """
        Initialize cost analyzer with configuration.
        
        Args:
            config_path (str): Path to YAML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config file is invalid
        """
        self.config = self._load_config(config_path)
        self.monthly_costs = self.config['infrastructure_costs']['monthly']
        self.daily_cost_usd = sum(self.monthly_costs.values()) / 30
        self.price_cache_file = "price_cache/sol_usdc_daily.json"
        self._ensure_cache_directory()
        
        # AIDEV-NOTE-CLAUDE: Daily flat allocation = total monthly costs / 30 days
        total_monthly = sum(self.monthly_costs.values())
        logger.info(f"Monthly costs breakdown: {self.monthly_costs}")
        logger.info(f"Total monthly cost: ${total_monthly:.2f}")
        logger.info(f"Daily infrastructure cost: ${self.daily_cost_usd:.2f} USD")
        
    def _load_config(self, config_path: str) -> Dict:
        """
        Load and validate YAML configuration.
        
        Args:
            config_path (str): Path to configuration file
            
        Returns:
            Dict: Parsed configuration data
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            yaml.YAMLError: If config is invalid
        """
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_path}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Invalid YAML configuration: {e}")
            raise
            
    def _ensure_cache_directory(self):
        """Create price cache directory if it doesn't exist."""
        cache_dir = os.path.dirname(self.price_cache_file)
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir)
            logger.info(f"Created cache directory: {cache_dir}")
            
    def _load_price_cache(self) -> Dict[str, float]:
        """
        Load SOL/USDC historical prices from cache.
        
        Returns:
            Dict[str, float]: Date string to price mapping
        """
        if os.path.exists(self.price_cache_file):
            try:
                with open(self.price_cache_file, 'r') as f:
                    cache = json.load(f)
                logger.info(f"Loaded {len(cache)} cached SOL/USDC prices")
                return cache
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning("Price cache file corrupted, starting fresh")
                return {}
        return {}
        
    def _save_price_cache(self, cache: Dict[str, float]):
        """
        Save SOL/USDC prices to cache file.
        
        Args:
            cache (Dict[str, float]): Price data to save
        """
        try:
            with open(self.price_cache_file, 'w') as f:
                json.dump(cache, f, indent=2)
            logger.info(f"Saved {len(cache)} prices to cache")
        except Exception as e:
            logger.error(f"Failed to save price cache: {e}")
            
    def _fetch_sol_usdc_price(self, date: str) -> Optional[float]:
        """
        Fetch SOL/USDC price for specific date via Moralis API.
        
        Args:
            date (str): Date in YYYY-MM-DD format
            
        Returns:
            Optional[float]: SOL price in USDC, None if failed
        """
        # AIDEV-NOTE-CLAUDE: Using working Moralis endpoint from main_analyzer.py
        try:
            # For SOL price, we'll use a major SOL pool (e.g., SOL/USDC on Raydium)
            # This is a well-known SOL/USDC pool address
            sol_usdc_pool = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"  # Raydium SOL/USDC
            
            # Convert date to datetime range
            date_obj = datetime.strptime(date, "%Y-%m-%d")
            start_dt = date_obj
            end_dt = date_obj + timedelta(days=1)
            
            # Use same endpoint as main_analyzer.py
            start_unix = int(start_dt.timestamp())
            end_unix = int(end_dt.timestamp())
            
            url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{sol_usdc_pool}/ohlcv"
            headers = {
                "accept": "application/json", 
                "X-API-Key": os.getenv("MORALIS_API_KEY", "")
            }
            
            params = {
                "timeframe": "1h",  # Daily data
                "fromDate": date,
                "toDate": (date_obj + timedelta(days=1)).strftime("%Y-%m-%d"),
                "currency": "usd"
            }
            
            # Respect rate limiting
            time.sleep(0.6)
            
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            
            data = response.json()
            
            # Parse response similar to main_analyzer.py
            api_result = data.get('result', []) if isinstance(data, dict) else data
            
            if isinstance(api_result, list) and len(api_result) > 0:
                # Get last candle of the day (closing price)
                last_candle = api_result[-1]
                if isinstance(last_candle, dict) and 'close' in last_candle:
                    price = float(last_candle['close'])
                    logger.info(f"Fetched SOL/USDC price for {date}: ${price:.2f}")
                    return price
                else:
                    logger.warning(f"Invalid candle format for {date}: {last_candle}")
                    return None
            else:
                logger.warning(f"No price data available for {date}")
                return None
                
        except requests.RequestException as e:
            logger.error(f"API request failed for {date}: {e}")
            return None
        except (KeyError, ValueError, TypeError) as e:
            logger.error(f"Failed to parse price data for {date}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching price for {date}: {e}")
            return None
            
    def get_sol_usdc_rates(self, start_date: str, end_date: str) -> Dict[str, float]:
        """
        Get SOL/USDC historical rates for date range.
        
        Args:
            start_date (str): Start date in YYYY-MM-DD format
            end_date (str): End date in YYYY-MM-DD format
            
        Returns:
            Dict[str, float]: Date to SOL/USDC price mapping
            
        Raises:
            ValueError: If date format is invalid
        """
        # AIDEV-NOTE-CLAUDE: Incremental cache updates - fetch only missing dates
        cache = self._load_price_cache()
        
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            raise
            
        # Generate date range
        current_date = start_dt
        missing_dates = []
        
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str not in cache:
                missing_dates.append(date_str)
            current_date += timedelta(days=1)
            
        # Fetch missing dates
        if missing_dates:
            logger.info(f"Fetching {len(missing_dates)} missing SOL/USDC prices")
            
            for date in missing_dates:
                price = self._fetch_sol_usdc_price(date)
                if price is not None:
                    cache[date] = price
                else:
                    # AIDEV-NOTE-CLAUDE: Fallback price if API fails (approximate SOL price)
                    fallback_price = 150.0  # Reasonable SOL price fallback
                    logger.warning(f"Using fallback price ${fallback_price} for {date}")
                    cache[date] = fallback_price
                    
            # Save updated cache
            self._save_price_cache(cache)
        else:
            logger.info("All required dates found in cache")
            
        # Return requested range
        result = {}
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            if date_str in cache:
                result[date_str] = cache[date_str]
            current_date += timedelta(days=1)
            
        return result
        
    def calculate_daily_costs(self, analysis_start: str, analysis_end: str) -> Dict[str, Dict[str, float]]:
        """
        Calculate daily infrastructure costs in both USD and SOL.
        
        Args:
            analysis_start (str): Start date in YYYY-MM-DD format
            analysis_end (str): End date in YYYY-MM-DD format
            
        Returns:
            Dict[str, Dict[str, float]]: Daily costs with structure:
                {
                    "2025-06-01": {
                        "cost_usd": 11.67,
                        "cost_sol": 0.083,
                        "sol_price": 140.50
                    }
                }
        """
        # Get SOL/USDC rates for period
        sol_rates = self.get_sol_usdc_rates(analysis_start, analysis_end)
        
        daily_costs = {}
        
        try:
            start_dt = datetime.strptime(analysis_start, "%Y-%m-%d")
            end_dt = datetime.strptime(analysis_end, "%Y-%m-%d")
        except ValueError as e:
            logger.error(f"Invalid date format: {e}")
            raise
            
        current_date = start_dt
        while current_date <= end_dt:
            date_str = current_date.strftime("%Y-%m-%d")
            
            if date_str in sol_rates:
                sol_price = sol_rates[date_str]
                cost_sol = self.daily_cost_usd / sol_price
                
                daily_costs[date_str] = {
                    "cost_usd": self.daily_cost_usd,
                    "cost_sol": cost_sol,
                    "sol_price": sol_price
                }
            else:
                logger.warning(f"No SOL price available for {date_str}, skipping cost calculation")
                
            current_date += timedelta(days=1)
            
        logger.info(f"Calculated costs for {len(daily_costs)} days")
        return daily_costs
        
    def allocate_costs_to_positions(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        """
        Allocate infrastructure costs to trading positions.
        
        Args:
            positions_df (pd.DataFrame): Trading positions data
            
        Returns:
            pd.DataFrame: Positions with added cost columns
        """
        if positions_df.empty:
            logger.warning("No positions provided for cost allocation")
            return positions_df
            
        # Ensure required columns exist
        required_cols = ['open_timestamp', 'close_timestamp']
        missing_cols = [col for col in required_cols if col not in positions_df.columns]
        if missing_cols:
            raise ValueError(f"Missing required columns: {missing_cols}")
            
        # Convert timestamps to datetime if needed
        positions_df = positions_df.copy()
        for col in ['open_timestamp', 'close_timestamp']:
            if not pd.api.types.is_datetime64_any_dtype(positions_df[col]):
                positions_df[col] = pd.to_datetime(positions_df[col])
                
        # Get date range from positions
        min_date = positions_df['open_timestamp'].min().strftime("%Y-%m-%d")
        max_date = positions_df['close_timestamp'].max().strftime("%Y-%m-%d")
        
        # Calculate daily costs
        daily_costs = self.calculate_daily_costs(min_date, max_date)
        
        # AIDEV-NOTE-CLAUDE: Daily flat allocation across all positions on each day
        # Count positions active on each day
        daily_position_counts = {}
        for date_str in daily_costs.keys():
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
            
            # Count positions active on this date
            active_positions = 0
            for _, pos in positions_df.iterrows():
                open_date = pos['open_timestamp'].date()
                close_date = pos['close_timestamp'].date()
                
                if open_date <= date_obj <= close_date:
                    active_positions += 1
                    
            daily_position_counts[date_str] = active_positions
            
        # Allocate costs to positions
        positions_df['infrastructure_cost_usd'] = 0.0
        positions_df['infrastructure_cost_sol'] = 0.0
        
        for idx, position in positions_df.iterrows():
            total_cost_usd = 0.0
            total_cost_sol = 0.0
            
            # Calculate cost for each day position was active
            current_date = position['open_timestamp'].date()
            end_date = position['close_timestamp'].date()
            
            while current_date <= end_date:
                date_str = current_date.strftime("%Y-%m-%d")
                
                if date_str in daily_costs and daily_position_counts[date_str] > 0:
                    # Allocate daily cost evenly among active positions
                    daily_cost_usd = daily_costs[date_str]['cost_usd'] / daily_position_counts[date_str]
                    daily_cost_sol = daily_costs[date_str]['cost_sol'] / daily_position_counts[date_str]
                    
                    total_cost_usd += daily_cost_usd
                    total_cost_sol += daily_cost_sol
                    
                current_date += timedelta(days=1)
                
            positions_df.at[idx, 'infrastructure_cost_usd'] = total_cost_usd
            positions_df.at[idx, 'infrastructure_cost_sol'] = total_cost_sol
            
        logger.info(f"Allocated infrastructure costs to {len(positions_df)} positions")
        return positions_df
        
    def generate_cost_summary(self, positions_df: pd.DataFrame, period_days: int) -> Dict:
        """
        Generate infrastructure cost impact summary.
        
        Args:
            positions_df (pd.DataFrame): Positions with cost allocations
            period_days (int): Analysis period in days
            
        Returns:
            Dict: Cost impact summary
        """
        if 'infrastructure_cost_usd' not in positions_df.columns:
            logger.warning("Positions don't have cost allocations")
            return {}
            
        total_cost_usd = positions_df['infrastructure_cost_usd'].sum()
        total_cost_sol = positions_df['infrastructure_cost_sol'].sum()
        
        # Calculate gross PnL
        gross_pnl_sol = positions_df['pnl_sol'].sum() if 'pnl_sol' in positions_df.columns else 0
        
        # Cost impact
        cost_impact_percent = (total_cost_sol / abs(gross_pnl_sol) * 100) if gross_pnl_sol != 0 else 0
        
        summary = {
            'period_days': period_days,
            'total_cost_usd': total_cost_usd,
            'total_cost_sol': total_cost_sol,
            'daily_cost_usd': self.daily_cost_usd,
            'gross_pnl_sol': gross_pnl_sol,
            'net_pnl_sol': gross_pnl_sol - total_cost_sol,
            'cost_impact_percent': cost_impact_percent,
            'break_even_days': abs(gross_pnl_sol / (total_cost_sol / period_days)) if total_cost_sol > 0 else 0,
            'positions_analyzed': len(positions_df)
        }
        
        logger.info(f"Cost impact: {cost_impact_percent:.1f}% of gross PnL")
        return summary


if __name__ == "__main__":
    # Test the cost analyzer
    analyzer = InfrastructureCostAnalyzer()
    
    # Test with sample date range
    costs = analyzer.calculate_daily_costs("2025-06-01", "2025-06-05")
    print(f"Sample costs: {costs}")