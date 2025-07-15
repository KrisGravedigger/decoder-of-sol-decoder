"""
Smart Price Cache Manager with Gap Detection and Repair capabilities.

Handles efficient caching of price data with monthly files and incremental updates.
Only fetches missing data gaps from API, maximizing cache utilization.
Includes a 'force_refetch' mode to repair cache and provides warnings for filled gaps.
Returns a guaranteed continuous, forward-filled dataset for the requested range.
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# AIDEV-NOTE-GEMINI: Configurable threshold for placeholder warnings, as requested.
CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD = 5

class PriceCacheManager:
    """
    Manages price data caching with smart gap detection, placeholder warnings, and a repair mode.
    
    Cache structure: pool_timeframe_YYYY-MM.json
    Strategy: 
    1. Align requested timestamps to candle boundaries immediately.
    2. Fetch all available real data from cache and API (or force re-fetch).
    3. If API confirms a gap is empty, save 'empty' placeholders to prevent re-fetching.
    4. Perform a final, robust forward-fill to guarantee a continuous dataset.
    5. Log warnings about the size of filled gaps.
    """
    
    def __init__(self, cache_dir: str = "price_cache"):
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        
    def get_price_data(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                    timeframe: str, api_key: Optional[str] = None,
                    force_refetch: bool = False) -> List[Dict]:
        """
        Get price data with smart caching and guaranteed continuous output.
        
        Args:
            pool_address (str): Pool address
            start_dt (datetime): Start datetime
            end_dt (datetime): End datetime
            timeframe (str): Timeframe (10min, 30min, 1h, 4h)
            api_key (Optional[str]): API key for fetching missing data
            force_refetch (bool): If True, re-fetches data even for cached empty gaps.
            
        Returns:
            List[Dict]: Price data with timestamp and close keys, continuous and forward-filled.
        """
        interval_seconds = self._get_interval_seconds(timeframe)

        aligned_start_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds))
        aligned_end_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds))
        
        logger.debug(f"Getting price data for {pool_address} ({timeframe}): {start_dt} to {end_dt}")
        if force_refetch:
            logger.info("Force re-fetch mode is ON. Will re-query API for empty gaps.")
        
        monthly_periods = self._split_into_monthly_periods(aligned_start_dt, aligned_end_dt)
        
        all_data = []
        
        for month_start, month_end in monthly_periods:
            month_data = self._get_monthly_data(
                pool_address, month_start, month_end, timeframe, api_key, force_refetch
            )
            all_data.extend(month_data)
        
        timestamp_map = self._map_to_candle_boundaries(all_data, interval_seconds)

        final_data = self._conservative_forward_fill(
            timestamp_map, 
            interval_seconds, 
            aligned_start_dt, 
            aligned_end_dt
        )
        
        # AIDEV-NOTE-GEMINI: Log warnings about filled gaps, as requested.
        self._log_placeholder_warnings(final_data, pool_address, timeframe)
        
        logger.debug(f"Returning {len(final_data)} price points for {pool_address} (aligned and forward-filled)")
        
        return final_data
    
    def _split_into_monthly_periods(self, start_dt: datetime, end_dt: datetime) -> List[Tuple[datetime, datetime]]:
        """Splits a date range into monthly periods for file-based caching."""
        periods = []
        current = start_dt
        while current <= end_dt:
            month_start = current.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            next_month = (month_start.replace(day=28) + timedelta(days=4)).replace(day=1)
            month_end_boundary = next_month - timedelta(seconds=1)
            period_start = max(current, month_start)
            period_end = min(end_dt, month_end_boundary)
            if period_start <= period_end:
                periods.append((period_start, period_end))
            current = next_month
        return periods
    
    def _get_monthly_data(self, pool_address: str, month_start: datetime, month_end: datetime,
                         timeframe: str, api_key: Optional[str], force_refetch: bool) -> List[Dict]:
        """Gets data for a single month, handling cache, gaps, and API calls."""
        month_str = month_start.strftime('%Y-%m')
        cache_filename = f"{pool_address}_{timeframe}_{month_str}.json"
        cache_path = os.path.join(self.cache_dir, cache_filename)
        
        existing_data = self._load_cache_file(cache_path)
        
        gaps = self._find_data_gaps(existing_data, month_start, month_end, timeframe, force_refetch)
        
        if not gaps:
            return self._filter_existing_data(existing_data, month_start, month_end)
        
        if not api_key:
            logger.warning(f"Cache-only mode: Found {len(gaps)} gaps but no API key provided")
            return self._filter_existing_data(existing_data, month_start, month_end)
        
        new_data_from_api = []
        for gap_start, gap_end in gaps:
            logger.info(f"Fetching gap for {pool_address}: {gap_start} to {gap_end}")
            gap_data = self._fetch_from_api(pool_address, gap_start, gap_end, timeframe, api_key)
            
            if gap_data and gap_data[0].get('api_request_failed'):
                logger.warning(f"Skipping gap {gap_start} to {gap_end} due to API failure - will retry later")
                continue # Do not create placeholders for failed requests
            
            if gap_data: # API returned real data
                new_data_from_api.extend(gap_data)
            else: # API succeeded but returned no data, create placeholders to prevent re-fetching
                logger.info(f"Gap is empty according to API. Creating cache placeholders for {gap_start} to {gap_end}")
                placeholders = self._create_empty_placeholders(gap_start, gap_end, timeframe)
                new_data_from_api.extend(placeholders)

            time.sleep(0.6)
        
        if new_data_from_api:
            merged_data = self._merge_and_save(existing_data, new_data_from_api, cache_path)
            return self._filter_existing_data(merged_data, month_start, month_end)
        else:
            return self._filter_existing_data(existing_data, month_start, month_end)

    def _create_empty_placeholders(self, start_dt: datetime, end_dt: datetime, timeframe: str) -> List[Dict]:
        """Creates a list of empty placeholders for a given time range to prevent future API calls."""
        placeholders = []
        interval_seconds = self._get_interval_seconds(timeframe)
        current_ts = self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds)
        end_ts = self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds)
        
        while current_ts <= end_ts:
            placeholders.append({
                'timestamp': current_ts,
                'close': 0.0, # Zero price indicates a placeholder
                'is_placeholder': True
            })
            current_ts += interval_seconds
        return placeholders

    def _load_cache_file(self, cache_path: str) -> List[Dict]:
        if not os.path.exists(cache_path): return []
        try:
            with open(cache_path, 'r') as f: data = json.load(f)
            return data if isinstance(data, list) else []
        except Exception as e:
            logger.warning(f"Failed to load cache {cache_path}: {e}")
            return []
    
    def _find_data_gaps(self, existing_data: List[Dict], start_dt: datetime, end_dt: datetime, 
                       timeframe: str, force_refetch: bool) -> List[Tuple[datetime, datetime]]:
        """Finds gaps in data. In force_refetch mode, placeholders are also considered gaps."""
        interval_seconds = self._get_interval_seconds(timeframe)
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp())
        
        # AIDEV-NOTE-GEMINI: Logic to handle 'force_refetch' mode, as requested.
        existing_timestamps = set()
        for p in existing_data:
            ts = p['timestamp']
            is_real_data = p.get('close', 0.0) > 0 and not p.get('is_placeholder')
            if force_refetch:
                # In force_refetch mode, only real data counts as "existing"
                if is_real_data: existing_timestamps.add(ts)
            else:
                # In normal mode, any data (real or placeholder) counts as "existing"
                existing_timestamps.add(ts)

        expected_timestamps = []
        current_ts = self._align_timestamp_to_boundary(start_unix, interval_seconds)
        end_ts_aligned = self._align_timestamp_to_boundary(end_unix, interval_seconds)
        while current_ts <= end_ts_aligned:
            expected_timestamps.append(current_ts)
            current_ts += interval_seconds
        
        missing_timestamps = sorted([ts for ts in expected_timestamps if ts not in existing_timestamps])
        
        if not missing_timestamps: return []
        
        gaps = []
        gap_start = missing_timestamps[0]
        for i in range(1, len(missing_timestamps)):
            if missing_timestamps[i] - missing_timestamps[i-1] > interval_seconds:
                gaps.append((datetime.fromtimestamp(gap_start), datetime.fromtimestamp(missing_timestamps[i-1])))
                gap_start = missing_timestamps[i]
        gaps.append((datetime.fromtimestamp(gap_start), datetime.fromtimestamp(missing_timestamps[-1])))
        
        return gaps
    
    def _get_interval_seconds(self, timeframe: str) -> int:
        intervals = {"10min": 600, "30min": 1800, "1h": 3600, "4h": 14400, "1d": 86400}
        return intervals[timeframe]
    
    def _filter_existing_data(self, data: List[Dict], start_dt: datetime, end_dt: datetime) -> List[Dict]:
        start_unix = int(start_dt.timestamp())
        end_unix = int(end_dt.timestamp())
        return sorted([d for d in data if start_unix <= d['timestamp'] <= end_unix], key=lambda x: x['timestamp'])
    
    def _fetch_from_api(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                       timeframe: str, api_key: str) -> List[Dict]:
        """Fetches data from API, returns real data, empty list, or failure marker."""
        url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
        headers = {"accept": "application/json", "X-API-Key": api_key}
        params = {"timeframe": timeframe, "fromDate": start_dt.strftime('%Y-%m-%d'), 
                  "toDate": (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'), "currency": "usd"}
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            processed_data = []
            api_result = data.get('result', []) if isinstance(data, dict) else data
            if isinstance(api_result, list):
                # Process and validate data points
                for d in api_result:
                    try:
                        ts_val = d.get('time') or d.get('timestamp')
                        ts = int(int(ts_val) / 1000) if str(ts_val).isdigit() else int(datetime.fromisoformat(ts_val.replace('Z', '+00:00')).timestamp())
                        if start_dt.timestamp() <= ts <= end_dt.timestamp():
                            processed_data.append({'timestamp': ts, 'close': float(d['close'])})
                    except (ValueError, TypeError, KeyError):
                        continue
            logger.info(f"Fetched {len(processed_data)} valid points from API.")
            return sorted(processed_data, key=lambda x: x['timestamp'])
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return [{'api_request_failed': True, 'error': str(e)}]

    def _align_timestamp_to_boundary(self, timestamp: int, interval_seconds: int) -> int:
        return (timestamp // interval_seconds) * interval_seconds
    
    def _map_to_candle_boundaries(self, data: List[Dict], interval_seconds: int) -> Dict[int, float]:
        """Maps raw data points to aligned candle timestamps, preferring real data."""
        timestamp_map = {}
        for point in data:
            aligned_ts = self._align_timestamp_to_boundary(point['timestamp'], interval_seconds)
            current_price = point.get('close', 0.0)
            if current_price > 0:
                timestamp_map[aligned_ts] = current_price
        return timestamp_map
    
    def _conservative_forward_fill(self, data_map: Dict[int, float], interval_seconds: int, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        """Performs a robust forward-fill on the data map to guarantee a continuous series."""
        filled_data = []
        last_valid_price = None
        if data_map:
            sorted_keys = sorted(data_map.keys())
            if sorted_keys: last_valid_price = data_map[sorted_keys[0]]

        current_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        while current_ts <= end_ts:
            price = data_map.get(current_ts)
            if price is not None and price > 0:
                last_valid_price = price
            if last_valid_price is not None:
                filled_data.append({
                    'timestamp': current_ts,
                    'close': last_valid_price,
                    'is_forward_filled': (price is None or price <= 0)
                })
            current_ts += interval_seconds
        return filled_data

    def _log_placeholder_warnings(self, filled_data: List[Dict], pool_address: str, timeframe: str):
        """AIDEV-NOTE-GEMINI: New method to log warnings about filled gaps, as requested."""
        if not filled_data: return
        
        consecutive_fills = 0
        for point in filled_data:
            if point.get('is_forward_filled'):
                consecutive_fills += 1
            else:
                if consecutive_fills > 0:
                    start_time = datetime.fromtimestamp(point['timestamp'] - consecutive_fills * self._get_interval_seconds(timeframe))
                    msg = (f"Filled a gap of {consecutive_fills} consecutive missing data point(s) "
                           f"for {pool_address} ({timeframe}) starting around {start_time.strftime('%Y-%m-%d %H:%M')}.")
                    if consecutive_fills >= CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD:
                        logger.warning(f"SIGNIFICANT DATA GAP: {msg}")
                    else:
                        logger.info(f"Data gap note: {msg}")
                consecutive_fills = 0
        
        if consecutive_fills > 0: # Handle case where gap is at the very end
            start_time = datetime.fromtimestamp(filled_data[-1]['timestamp'] - (consecutive_fills - 1) * self._get_interval_seconds(timeframe))
            msg = (f"Filled a gap of {consecutive_fills} consecutive missing data point(s) "
                   f"for {pool_address} ({timeframe}) at the end of the range, starting around {start_time.strftime('%Y-%m-%d %H:%M')}.")
            if consecutive_fills >= CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD:
                logger.warning(f"SIGNIFICANT DATA GAP: {msg}")
            else:
                logger.info(f"Data gap note: {msg}")

    def _merge_and_save(self, existing_data: List[Dict], new_data: List[Dict], cache_path: str) -> List[Dict]:
        """Merges new data with existing, deduplicates, and saves to cache."""
        merged_map = {point['timestamp']: point for point in existing_data}
        merged_map.update({point['timestamp']: point for point in new_data})
        merged_data = sorted(list(merged_map.values()), key=lambda x: x['timestamp'])
        
        try:
            with open(cache_path, 'w') as f: json.dump(merged_data, f, indent=2)
            logger.info(f"Updated cache: {os.path.basename(cache_path)} ({len(merged_data)} total points)")
        except Exception as e:
            logger.error(f"Failed to save cache {cache_path}: {e}")
        
        return merged_data