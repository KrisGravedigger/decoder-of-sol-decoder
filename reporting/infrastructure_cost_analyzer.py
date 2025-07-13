import logging
import json
import os
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional
import pandas as pd
import yaml

# AIDEV-NOTE-CLAUDE: Import PriceCacheManager to replace old cache logic
from .price_cache_manager import PriceCacheManager

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class InfrastructureCostAnalyzer:
    def __init__(self, config_path: str = "reporting/config/portfolio_config.yaml", api_key: Optional[str] = None):
        self.config = self._load_config(config_path)
        self.api_key = api_key
        
        self.monthly_costs = self.config.get('infrastructure_costs', {}).get('monthly', {})
        self.daily_cost_usd = sum(self.monthly_costs.values()) / 30
        
        logger.info(f"Daily infrastructure cost: ${self.daily_cost_usd:.2f} USD")
        if not self.api_key:
            logger.warning("InfrastructureCostAnalyzer initialized without an API key. Will operate in cache-only mode.")
        
    def _load_config(self, config_path: str) -> Dict:
        try:
            with open(config_path, 'r') as f: return yaml.safe_load(f)
        except (FileNotFoundError, yaml.YAMLError) as e:
            logger.error(f"Error loading config {config_path}: {e}")
            raise

    def get_sol_usdc_rates(self, start_date: str, end_date: str) -> Dict[str, Optional[float]]:
        """
        Get daily SOL/USDC prices using the centralized PriceCacheManager.
        AIDEV-NOTE-GEMINI: This function now specifically requests 1-day candles.
        """
        logger.info(f"Fetching SOL/USDC rates from {start_date} to {end_date} via PriceCacheManager.")
        cache_manager = PriceCacheManager()
        sol_usdc_pool = "58oQChx4yWmvKdwLLZzBi4ChoCc2fqCUWBkwMihLYQo2"
        
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d") + timedelta(days=1)
        
        # AIDEV-NOTE-GEMINI: Switched to '1d' timeframe for SOL/USDC portfolio-level analysis, as requested.
        price_data = cache_manager.get_price_data(
            pool_address=sol_usdc_pool,
            start_dt=start_dt,
            end_dt=end_dt,
            timeframe='1d',
            api_key=self.api_key
        )
        
        if not price_data:
            logger.warning("No SOL/USDC price data returned from PriceCacheManager.")
            return {d.strftime("%Y-%m-%d"): None for d in pd.date_range(start_date, end_date)}
            
        df = pd.DataFrame(price_data)
        df['date'] = pd.to_datetime(df['timestamp'], unit='s').dt.date
        
        daily_prices_df = df.sort_values('timestamp').groupby('date')['close'].last()
        
        all_dates = pd.date_range(start=start_date, end=end_date)
        rates_series = daily_prices_df.reindex(all_dates.date, method=None)
        
        rates_series_filled = rates_series.ffill().bfill()

        final_rates = {date.strftime('%Y-%m-%d'): price for date, price in rates_series_filled.items()}
            
        return final_rates

    def calculate_daily_costs(self, sol_rates: Dict[str, Optional[float]]) -> Dict[str, Dict[str, float]]:
        """Calculates daily costs using pre-fetched SOL rates."""
        daily_costs = {}
        fallback_price = 150.0

        for date_str, sol_price in sol_rates.items():
            price_to_use = sol_price if sol_price is not None else fallback_price
            if sol_price is None:
                logger.warning(f"Using fallback SOL price for {date_str} for cost calculation.")

            daily_costs[date_str] = {
                "cost_usd": self.daily_cost_usd, "cost_sol": self.daily_cost_usd / price_to_use if price_to_use > 0 else 0.0, "sol_price": price_to_use
            }
        return daily_costs
        
    def allocate_costs_to_positions(self, positions_df: pd.DataFrame, sol_rates: Dict[str, Optional[float]]) -> pd.DataFrame:
        """
        Allocates daily infrastructure costs to active positions.
        AIDEV-NOTE-GEMINI: This method now accepts pre-fetched sol_rates to avoid redundant API calls.
        """
        if positions_df.empty: return positions_df
        
        df = positions_df.copy()
        df['open_timestamp'] = pd.to_datetime(df['open_timestamp'])
        df['close_timestamp'] = pd.to_datetime(df['close_timestamp'])
        
        if not sol_rates:
            logger.warning("No SOL rates provided. Skipping cost allocation.")
            df['infrastructure_cost_sol'] = 0
            df['infrastructure_cost_usd'] = 0
            return df
        
        # We no longer need to fetch rates here, we just use what was passed in.
        daily_costs = self.calculate_daily_costs(sol_rates)
        
        if not daily_costs:
            logger.warning("No daily cost data calculated. Skipping cost allocation.")
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