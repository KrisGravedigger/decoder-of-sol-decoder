import logging
import json
import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import yaml

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InfrastructureCostAnalyzer:
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml", api_key: Optional[str] = None):
        self.config = self._load_config(config_path)
        # AIDEV-NOTE-CLAUDE: API key is passed during initialization. Can be None for cache-only mode.
        self.api_key = api_key
        
        self.monthly_costs = self.config.get('infrastructure_costs', {}).get('monthly', {})
        self.daily_cost_usd = sum(self.monthly_costs.values()) / 30
        self.price_cache_file = "price_cache/sol_usdc_daily.json"
        self._ensure_cache_directory()
        logger.info(f"Daily infrastructure cost: ${self.daily_cost_usd:.2f} USD")
        if not self.api_key:
            logger.warning("InfrastructureCostAnalyzer initialized without an API key. Will operate in cache-only mode.")
        
    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f: return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading config {config_path}: {e}")
            raise

    def _ensure_cache_directory(self):
        os.makedirs(os.path.dirname(self.price_cache_file), exist_ok=True)

    def _load_price_cache(self) -> Dict[str, float]:
        if not os.path.exists(self.price_cache_file): return {}
        try:
            with open(self.price_cache_file, 'r') as f: return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError): return {}
        
    def _save_price_cache(self, cache: Dict[str, float]):
        try:
            with open(self.price_cache_file, 'w') as f: json.dump(cache, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save price cache: {e}")

    def _fetch_sol_usdc_price(self, date: str) -> Optional[float]:
        # AIDEV-NOTE-CLAUDE: Cache-only mode implementation.
        # If no API key is provided, do not attempt to fetch.
        if not self.api_key:
            logger.warning(f"Cache-only mode: SOL/USDC price for {date} not found in cache. Skipping API call.")
            return None

        sol_usdc_pool = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
        date_obj = datetime.strptime(date, "%Y-%m-%d")
        url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{sol_usdc_pool}/ohlcv"
        headers = {"accept": "application/json", "X-API-Key": self.api_key}
        params = {
            "timeframe": "1h", "fromDate": date,
            "toDate": (date_obj + timedelta(days=1)).strftime("%Y-%m-%d"), "currency": "usd"
        }
        time.sleep(0.6) # Rate limiting
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json().get('result', [])
            if data and isinstance(data, list) and data[-1].get('close') is not None:
                price = float(data[-1]['close'])
                logger.info(f"Fetched SOL/USDC price for {date}: ${price:.2f}")
                return price
            logger.warning(f"No price data available for {date}")
            return None
        except requests.RequestException as e:
            logger.error(f"API request failed for {date}: {e}")
            return None
            
    def get_sol_usdc_rates(self, start_date: str, end_date: str) -> Dict[str, Optional[float]]:
        cache = self._load_price_cache()
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        
        all_dates = [d.strftime("%Y-%m-%d") for d in pd.date_range(start_dt, end_dt)]
        missing_dates = [d for d in all_dates if d not in cache]

        if missing_dates:
            logger.info(f"Fetching {len(missing_dates)} missing SOL/USDC prices")
            for date in missing_dates:
                price = self._fetch_sol_usdc_price(date)
                cache[date] = price # Can be None if fetch fails
                if price is None: logger.warning(f"Failed to fetch price for {date}, will be recorded as null.")
            self._save_price_cache(cache)
        
        return {d: cache.get(d) for d in all_dates}

    def calculate_daily_costs(self, analysis_start: str, analysis_end: str) -> Dict[str, Dict[str, float]]:
        sol_rates = self.get_sol_usdc_rates(analysis_start, analysis_end)
        daily_costs = {}
        fallback_price = 150.0  # Used if a specific day's price is unavailable

        for date_str, sol_price in sol_rates.items():
            price_to_use = sol_price if sol_price is not None else fallback_price
            if sol_price is None:
                logger.warning(f"Using fallback SOL price for {date_str} for cost calculation.")

            daily_costs[date_str] = {
                "cost_usd": self.daily_cost_usd, "cost_sol": self.daily_cost_usd / price_to_use, "sol_price": price_to_use
            }
        return daily_costs
        
    def allocate_costs_to_positions(self, positions_df: pd.DataFrame) -> pd.DataFrame:
        if positions_df.empty: return positions_df
        
        df = positions_df.copy()
        df['open_timestamp'] = pd.to_datetime(df['open_timestamp'])
        df['close_timestamp'] = pd.to_datetime(df['close_timestamp'])
        
        min_date, max_date = df['open_timestamp'].min(), df['close_timestamp'].max()
        if pd.isna(min_date) or pd.isna(max_date):
            logger.warning("Could not determine date range from positions. Skipping cost allocation.")
            df['infrastructure_cost_sol'] = 0
            df['infrastructure_cost_usd'] = 0
            return df

        daily_costs = self.calculate_daily_costs(min_date.strftime("%Y-%m-%d"), max_date.strftime("%Y-%m-%d"))
        
        if not daily_costs:
            logger.warning("No daily cost data available. Skipping cost allocation.")
            df['infrastructure_cost_sol'] = 0
            df['infrastructure_cost_usd'] = 0
            return df
            
        date_range = pd.to_datetime(list(daily_costs.keys()))
        daily_active_pos = [((df['open_timestamp'].dt.date <= d.date()) & (df['close_timestamp'].dt.date >= d.date())).sum() for d in date_range]
        daily_pos_counts = pd.Series(daily_active_pos, index=date_range)
        
        def calculate_pos_cost(row):
            pos_days = pd.date_range(row['open_timestamp'].date(), row['close_timestamp'].date())
            cost = 0
            for day in pos_days:
                day_str = day.strftime('%Y-%m-%d')
                if day in daily_pos_counts.index and daily_pos_counts[day] > 0 and day_str in daily_costs:
                    cost += daily_costs[day_str]['cost_sol'] / daily_pos_counts[day]
            return cost
            
        df['infrastructure_cost_sol'] = df.apply(calculate_pos_cost, axis=1)
        avg_sol_price = sum(v['sol_price'] for v in daily_costs.values()) / len(daily_costs) if daily_costs else 150
        df['infrastructure_cost_usd'] = df['infrastructure_cost_sol'] * avg_sol_price

        return df

    def generate_cost_summary(self, positions_df: pd.DataFrame, period_days: int) -> Dict:
        if 'infrastructure_cost_sol' not in positions_df.columns:
            return {'error': 'Cost allocation was not performed.'}
            
        total_cost_sol = positions_df['infrastructure_cost_sol'].sum()
        gross_pnl_sol = positions_df['pnl_sol'].sum()
        return {
            'total_cost_sol': total_cost_sol,
            'gross_pnl_sol': gross_pnl_sol,
            'net_pnl_sol': gross_pnl_sol - total_cost_sol,
            'cost_impact_percent': (total_cost_sol / abs(gross_pnl_sol) * 100) if gross_pnl_sol != 0 else 0,
        }