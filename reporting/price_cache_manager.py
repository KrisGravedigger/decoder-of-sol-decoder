"""
Smart Price Cache Manager with Gap Detection

Handles efficient caching of price data with monthly files and incremental updates.
Only fetches missing data gaps from API, maximizing cache utilization.
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class PriceCacheManager:
    """
    Manages price data caching with smart gap detection and incremental updates.
    
    Cache structure: pool_timeframe_YYYY-MM.json
    Strategy: Only fetch missing data gaps, never refetch existing candles.
    """
    
    def __init__(self, cache_dir: str = "price_cache"):
        """
        Initialize cache manager.
        
        Args:
            cache_dir (str): Directory for cache files
        """
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_price_data(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                      timeframe: str, api_key: Optional[str] = None) -> List[Dict]:
        """
        Get price data with smart caching - only fetch missing gaps.
        
        Args:
            pool_address (str): Pool address
            start_dt (datetime): Start datetime
            end_dt (datetime): End datetime  
            timeframe (str): Timeframe (10min, 30min, 1h, 4h)
            api_key (Optional[str]): API key for fetching missing data
            
        Returns:
            List[Dict]: Price data with timestamp and close keys
        """
        logger.info(f"Getting price data for {pool_address} ({timeframe}): {start_dt} to {end_dt}")
        
        # Step 1: Split request into monthly periods
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        
        all_data = []
        
        # Step 2: Process each month
        for month_start, month_end in monthly_periods:
            month_data = self._get_monthly_data(
                pool_address, month_start, month_end, timeframe, api_key
            )
            all_data.extend(month_data)
        
        # Step 3: Filter to exact requested range and sort
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp())
        
        filtered_data = [
            d for d in all_data 
            if start_unix <= d['timestamp'] <= end_unix
        ]
        
        filtered_data.sort(key=lambda x: x['timestamp'])
        
        logger.info(f"Returning {len(filtered_data)} price points for {pool_address}")
        return filtered_data
    
    def _split_into_monthly_periods(self, start_dt: datetime, end_dt: datetime) -> List[Tuple[datetime, datetime]]:
        """
        Split date range into monthly periods.
        
        Args:
            start_dt (datetime): Start datetime
            end_dt (datetime): End datetime
            
        Returns:
            List[Tuple[datetime, datetime]]: List of (month_start, month_end) tuples
        """
        periods = []
        current = start_dt
        
        while current <= end_dt:
            # Month boundaries
            month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            
            # Next month first day
            if month_start.month == 12:
                next_month = month_start.replace(year=month_start.year + 1, month=1)
            else:
                next_month = month_start.replace(month=month_start.month + 1)
            
            # Month end (last second of month)
            month_end = next_month - timedelta(seconds=1)
            
            # Constrain to actual request range
            period_start = max(current, month_start)
            period_end = min(end_dt, month_end)
            
            if period_start <= period_end:
                periods.append((period_start, period_end))
            
            current = next_month
        
        return periods
    
    def _get_monthly_data(self, pool_address: str, month_start: datetime, month_end: datetime,
                         timeframe: str, api_key: Optional[str]) -> List[Dict]:
        """
        Get data for a single month with gap detection.
        
        Args:
            pool_address (str): Pool address
            month_start (datetime): Month start datetime
            month_end (datetime): Month end datetime
            timeframe (str): Timeframe
            api_key (Optional[str]): API key
            
        Returns:
            List[Dict]: Price data for the month
        """
        month_str = month_start.strftime('%Y-%m')
        cache_filename = f"{pool_address}_{timeframe}_{month_str}.json"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        # Load existing cache
        existing_data = self._load_cache_file(cache_path)
        
        # Find gaps in required period
        gaps = self._find_data_gaps(existing_data, month_start, month_end, timeframe)
        
        if not gaps:
            logger.info(f"No gaps found for {pool_address} in {month_str}")
            return self._filter_existing_data(existing_data, month_start, month_end)
        
        if not api_key:
            logger.warning(f"Cache-only mode: Found {len(gaps)} gaps but no API key provided")
            return self._filter_existing_data(existing_data, month_start, month_end)
        
        # Fetch missing data for each gap
        new_data = []
        for gap_start, gap_end in gaps:
            logger.info(f"Fetching gap: {gap_start} to {gap_end}")
            gap_data = self._fetch_from_api(pool_address, gap_start, gap_end, timeframe, api_key)
            new_data.extend(gap_data)
            
            # Rate limiting
            time.sleep(0.6)
        
        # Merge with existing and save
        if new_data:
            merged_data = self._merge_and_save(existing_data, new_data, cache_path)
            return self._filter_existing_data(merged_data, month_start, month_end)
        else:
            return self._filter_existing_data(existing_data, month_start, month_end)
    
    def _load_cache_file(self, cache_path: str) -> List[Dict]:
        """Load existing cache file."""
        if not os.path.exists(cache_path):
            return []
        
        try:
            with open(cache_path, 'r') as f:
                data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return []
    
    def _find_data_gaps(self, existing_data: List[Dict], start_dt: datetime, end_dt: datetime, 
                       timeframe: str) -> List[Tuple[datetime, datetime]]:
        """
        Find gaps in existing data for the required period.
        
        Args:
            existing_data (List[Dict]): Existing cached data
            start_dt (datetime): Required start datetime
            end_dt (datetime): Required end datetime
            timeframe (str): Timeframe for interval calculation
            
        Returns:
            List[Tuple[datetime, datetime]]: List of gap periods to fetch
        """
        if not existing_data:
            return [(start_dt, end_dt)]
        
        # Calculate expected interval in seconds
        interval_seconds = self._get_interval_seconds(timeframe)
        
        # Get existing timestamps in required range
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp())
        
        existing_timestamps = set()
        for point in existing_data:
            ts = point['timestamp']
            if start_unix <= ts <= end_unix:
                existing_timestamps.add(ts)
        
        # Generate expected timestamps
        expected_timestamps = []
        current_ts = start_unix
        while current_ts <= end_unix:
            expected_timestamps.append(current_ts)
            current_ts += interval_seconds
        
        # Find missing timestamps
        missing_timestamps = [ts for ts in expected_timestamps if ts not in existing_timestamps]
        
        if not missing_timestamps:
            return []
        
        # Group consecutive missing timestamps into gaps
        gaps = []
        gap_start = None
        prev_ts = None
        
        for ts in sorted(missing_timestamps):
            if gap_start is None:
                gap_start = ts
            elif prev_ts is not None and ts - prev_ts > interval_seconds * 1.5:
                # Gap in missing timestamps - end current gap, start new one
                gaps.append((datetime.fromtimestamp(gap_start), datetime.fromtimestamp(prev_ts)))
                gap_start = ts
            
            prev_ts = ts
        
        # Add final gap
        if gap_start is not None:
            gaps.append((datetime.fromtimestamp(gap_start), datetime.fromtimestamp(prev_ts)))
        
        return gaps
    
    def _get_interval_seconds(self, timeframe: str) -> int:
        """Get interval in seconds for timeframe."""
        intervals = {
            "10min": 600,
            "30min": 1800, 
            "1h": 3600,
            "4h": 14400
        }
        return intervals.get(timeframe, 3600)
    
    def _filter_existing_data(self, data: List[Dict], start_dt: datetime, end_dt: datetime) -> List[Dict]:
        """Filter data to requested datetime range."""
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp())
        
        filtered = [
            d for d in data 
            if start_unix <= d['timestamp'] <= end_unix
        ]
        
        return sorted(filtered, key=lambda x: x['timestamp'])
    
    def _fetch_from_api(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                       timeframe: str, api_key: str) -> List[Dict]:
        """
        Fetch price data from Moralis API for specific gap.
        
        Args:
            pool_address (str): Pool address
            start_dt (datetime): Gap start datetime
            end_dt (datetime): Gap end datetime
            timeframe (str): Timeframe
            api_key (str): API key
            
        Returns:
            List[Dict]: Price data from API
        """
        url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
        headers = {"accept": "application/json", "X-API-Key": api_key}
        
        start_date_str = start_dt.strftime('%Y-%m-%d')
        end_date_str = (end_dt + timedelta(days=1)).strftime('%Y-%m-%d')
        
        params = {
            "timeframe": timeframe,
            "fromDate": start_date_str,
            "toDate": end_date_str,
            "currency": "usd"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            
            processed_data = []
            api_result = data.get('result', []) if isinstance(data, dict) else data
            
            if isinstance(api_result, list):
                start_unix = int(start_dt.timestamp())
                end_unix = int(end_dt.timestamp())
                
                for d in api_result:
                    if isinstance(d, dict) and 'close' in d:
                        ts_val = d.get('time') or d.get('timestamp')
                        if ts_val:
                            ts = 0
                            if isinstance(ts_val, (int, float, str)) and str(ts_val).isdigit():
                                ts = int(ts_val) // 1000
                            elif isinstance(ts_val, str):
                                try:
                                    ts_dt = datetime.fromisoformat(ts_val.replace('Z', '+00:00'))
                                    ts = int(ts_dt.timestamp())
                                except ValueError:
                                    continue
                            else:
                                continue

                            if start_unix <= ts <= end_unix:
                                processed_data.append({
                                    'timestamp': ts,
                                    'close': float(d['close'])
                                })
                
                processed_data.sort(key=lambda x: x['timestamp'])
            
            logger.info(f"Fetched {len(processed_data)} points from API for gap")
            return processed_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for gap {start_dt} to {end_dt}: {e}")
            return []
    
    def _merge_and_save(self, existing_data: List[Dict], new_data: List[Dict], 
                       cache_path: str) -> List[Dict]:
        """
        Merge new data with existing and save to cache file.
        
        Args:
            existing_data (List[Dict]): Existing cached data
            new_data (List[Dict]): New data from API
            cache_path (str): Path to cache file
            
        Returns:
            List[Dict]: Merged data
        """
        # Combine all data
        all_data = existing_data + new_data
        
        # Remove duplicates based on timestamp
        seen_timestamps = set()
        merged_data = []
        
        for point in all_data:
            ts = point['timestamp']
            if ts not in seen_timestamps:
                seen_timestamps.add(ts)
                merged_data.append(point)
        
        # Sort chronologically
        merged_data.sort(key=lambda x: x['timestamp'])
        
        # Save to file
        try:
            with open(cache_path, 'w') as f:
                json.dump(merged_data, f, indent=2)
            logger.info(f"Updated cache: {os.path.basename(cache_path)} ({len(merged_data)} total points)")
        except Exception as e:
            logger.error(f"Failed to save cache {cache_path}: {e}")
        
        return merged_data