"""
Enhanced Price Cache Manager - The Single Source of Truth for Price Data

This class is the SOLE orchestrator for all price cache operations. It replaces the
legacy PriceCacheManager and provides backward-compatible methods while using a
modern, robust, and structured caching mechanism.
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any, Tuple, TYPE_CHECKING
import logging

if TYPE_CHECKING:
    from core.models import Position

from reporting.price_cache_manager import PriceCacheManager

logger = logging.getLogger(__name__)
CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD = 5

class EnhancedPriceCacheManager(PriceCacheManager):
    """
    The primary cache manager for all price data.
    - Manages raw OCHLV+Volume cache in a structured /raw/YYYY-MM/ directory.
    - Manages processed {ts, close} cache in a structured /offline_processed/YYYY-MM/ directory.
    - Provides data to both new and legacy modules, ensuring backward compatibility.
    """

    def __init__(self, config: Optional[Dict] = None, api_key: Optional[str] = None):
        # AIDEV-NOTE-CLAUDE: We pass a hardcoded dir to super() as this class now controls all paths.
        super().__init__(cache_dir="price_cache", config=config)
        self.api_key = api_key or os.getenv("MORALIS_API_KEY")
        self.raw_cache_dir = os.path.join(self.cache_dir, "raw")
        # AIDEV-NOTE-CLAUDE: offline_processed_cache_dir is the new standard, replacing offline_cache_dir
        self.offline_processed_cache_dir = os.path.join(self.cache_dir, "offline_processed")
        os.makedirs(self.raw_cache_dir, exist_ok=True)
        os.makedirs(self.offline_processed_cache_dir, exist_ok=True)

    def get_price_data(self, pool_address: str, start_dt: datetime, end_dt: datetime,
                         timeframe: str, api_key: Optional[str] = None,
                         force_refetch: bool = False, **kwargs) -> List[Dict]:
        """
        [PRIMARY METHOD] Get price data with smart caching and guaranteed continuous output.
        This is the modern replacement for the legacy get_price_data method.
        """
        if api_key: self.api_key = api_key

        interval_seconds = self._get_interval_seconds(timeframe)
        aligned_start_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds))
        aligned_end_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds))

        # 1. Try to load from the clean, processed cache first.
        all_data = self._load_monthly_cache_files(self.offline_processed_cache_dir, pool_address, aligned_start_dt, aligned_end_dt)
        
        # 2. Find gaps in the processed cache
        gaps = self._find_data_gaps(all_data, aligned_start_dt, aligned_end_dt, force_refetch, interval_seconds)

        if gaps:
            # 3. If gaps exist, try to fill them using the raw OCHLV cache
            raw_ochlv_data = self._load_monthly_cache_files(self.raw_cache_dir, pool_address, aligned_start_dt, aligned_end_dt)
            
            # 4. Find gaps in the raw OCHLV cache
            raw_gaps = self._find_data_gaps(raw_ochlv_data, aligned_start_dt, aligned_end_dt, force_refetch, interval_seconds)

            # 5. If raw cache also has gaps, fetch from API
            if raw_gaps and not kwargs.get('use_cache_only'):
                new_ochlv_data = self._fetch_and_fill_gaps_from_api(pool_address, raw_gaps, timeframe)
                if new_ochlv_data:
                    # Save new raw data and merge it
                    raw_ochlv_data = self._merge_and_save_data(self.raw_cache_dir, pool_address, raw_ochlv_data, new_ochlv_data)
                    # IMPORTANT: After fetching, we must refresh the processed cache to reflect new data
                    self.refresh_offline_processed_cache_for_pool(pool_address)
                    # Reload the processed cache to get the most up-to-date data
                    all_data = self._load_monthly_cache_files(self.offline_processed_cache_dir, pool_address, aligned_start_dt, aligned_end_dt)

        # 6. Final processing: align, forward-fill, and filter
        timestamp_map = self._map_to_candle_boundaries(all_data, interval_seconds)
        final_data = self._conservative_forward_fill(timestamp_map, interval_seconds, aligned_start_dt, aligned_end_dt)
        self._log_placeholder_warnings(final_data, pool_address, timeframe)
        
        return self._filter_data_by_range(final_data, start_dt, end_dt)
    
    def refresh_offline_processed_cache(self):
        """
        Converts all raw OCHLV data into the simple {timestamp, close} format.
        """
        print("\nRefreshing offline processed cache from raw OCHLV data...")
        processed_count = 0
        if not os.path.exists(self.raw_cache_dir):
            print("Raw cache directory does not exist. Nothing to process.")
            return

        for month_dir in sorted(os.listdir(self.raw_cache_dir)):
            full_month_path = os.path.join(self.raw_cache_dir, month_dir)
            if os.path.isdir(full_month_path):
                for filename in os.listdir(full_month_path):
                    if filename.endswith('.json'):
                        pool_address = filename.replace('.json', '')
                        if self.refresh_offline_processed_cache_for_pool(pool_address):
                            processed_count += 1
        print(f"✅ Processed {processed_count} raw cache files into the offline cache.")

    def refresh_offline_processed_cache_for_pool(self, pool_address: str) -> bool:
        """Refreshes the processed cache for a single pool."""
        try:
            # Load all raw data for the pool across all months
            raw_data = self._load_monthly_cache_files(self.raw_cache_dir, pool_address, datetime(2023,1,1), datetime.now())
            if not raw_data: return False
            
            processed_data = [{'timestamp': d['timestamp'], 'close': d['close']} for d in raw_data if 'timestamp' in d and 'close' in d]
            
            # Save to processed cache, splitting by month
            self._merge_and_save_data(self.offline_processed_cache_dir, pool_address, [], processed_data)
            return True
        except Exception as e:
            logger.error(f"Failed to process raw cache for {pool_address}: {e}")
            return False

    # --- Helper methods moved and adapted from legacy manager ---

    def validate_cache_completeness(self, position: 'Position') -> Dict[str, Any]:
        """
        [PRIMARY VALIDATION METHOD] Checks if the raw cache contains complete OCHLV+Volume data
        for a position's required simulation timeframe (including post-close period).

        Args:
            position (Position): A position-like object with pool_address, open_timestamp,
                                 and close_timestamp attributes.

        Returns:
            Dict[str, Any]: A dictionary containing validation results:
                            - 'is_complete' (bool)
                            - 'has_price_data' (bool)
                            - 'has_volume_data' (bool)
        """
        try:
            # 1. Determine the full required time range for simulation
            if not self.config: # Lazy load config if not provided
                from utils.common import load_main_config
                self.config = load_main_config()

            max_sim_days = self.config.get('range_testing', {}).get('max_simulation_days', 7)
            start_dt = position.open_timestamp
            end_dt = position.close_timestamp + timedelta(days=max_sim_days)

            # 2. Determine timeframe and load all relevant raw data
            timeframe = self._determine_timeframe_from_duration(start_dt, end_dt)
            interval_seconds = self._get_interval_seconds(timeframe)
            raw_data = self._load_monthly_cache_files(self.raw_cache_dir, position.pool_address, start_dt, end_dt)

            if not raw_data:
                return {'is_complete': False, 'has_price_data': False, 'has_volume_data': False}

            # 3. Check for price data completeness (gap detection), now aware of tombstones
            # We now check if a timestamp is either present with data or marked as a tombstone.
            covered_timestamps = {
                self._align_timestamp_to_boundary(d['timestamp'], interval_seconds) 
                for d in raw_data
            }
            
            current_ts = self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds)
            end_ts = self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds)
            
            has_gaps = False
            while current_ts <= end_ts:
                if current_ts not in covered_timestamps:
                    has_gaps = True
                    break
                current_ts += interval_seconds
            
            has_price_data = not has_gaps

            # 4. Check for volume data availability
            has_volume_data = any(d.get('volume', 0) > 0 for d in raw_data)

            # 5. Determine overall completeness
            is_complete = has_price_data and has_volume_data

            return {'is_complete': is_complete, 'has_price_data': has_price_data, 'has_volume_data': has_volume_data}
        
        except Exception as e:
            logger.error(f"Cache validation failed for pool {position.pool_address}: {e}", exc_info=True)
            return {'is_complete': False, 'has_price_data': False, 'has_volume_data': False}

    def _fetch_and_fill_gaps_from_api(self, pool_address: str, gaps: List[Tuple[datetime, datetime]], timeframe: str) -> List[Dict]:
        """
        Fetches data from API for gaps and creates 'tombstone' placeholders for intervals
        where the API confirms no data exists. This prevents infinite re-fetching loops.
        """
        if not self.api_key:
            logger.warning(f"Gaps found for {pool_address} but no API key. Cannot fetch.")
            return []

        all_new_data = []
        interval_seconds = self._get_interval_seconds(timeframe)

        for gap_start, gap_end in gaps:
            logger.info(f"Processing gap for {pool_address} from {gap_start} to {gap_end}")
            
            # Fetch data from API for the entire gap period
            api_data = self._fetch_ochlv_from_api(pool_address, gap_start, gap_end, timeframe)
            all_new_data.extend(api_data)
            
            # --- AIDEV-NOTE-CLAUDE: START OF TOMBSTONE LOGIC ---
            # Create a set of timestamps for which the API actually returned data
            returned_timestamps = {self._align_timestamp_to_boundary(p['timestamp'], interval_seconds) for p in api_data}
            
            # Iterate through all expected timestamps in the gap
            current_ts = self._align_timestamp_to_boundary(int(gap_start.timestamp()), interval_seconds)
            end_ts = self._align_timestamp_to_boundary(int(gap_end.timestamp()), interval_seconds)
            
            while current_ts <= end_ts:
                # If the API did not return data for this specific timestamp, create a tombstone
                if current_ts not in returned_timestamps:
                    tombstone = {
                        'timestamp': current_ts,
                        'open': -1, 'high': -1, 'low': -1, 'close': -1,
                        'volume': -1, 'is_tombstone': True
                    }
                    all_new_data.append(tombstone)
                current_ts += interval_seconds
            # --- END OF TOMBSTONE LOGIC ---
            
            time.sleep(0.6) # API rate limit

        return all_new_data

    def _load_monthly_cache_files(self, base_dir: str, pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        """Loads all relevant monthly cache files for a given period from the new structure."""
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        all_data = []
        for month_start, _ in monthly_periods:
            month_str = month_start.strftime('%Y-%m')
            cache_file = os.path.join(base_dir, month_str, f"{pool_address}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                        all_data.extend(data if isinstance(data, list) else [])
                except Exception as e:
                    logger.error(f"Failed to load cache file {cache_file}: {e}")
        
        unique_points = {d['timestamp']: d for d in all_data if isinstance(d, dict) and 'timestamp' in d}
        return sorted(unique_points.values(), key=lambda x: x['timestamp'])

    def _find_data_gaps(self, existing_data: List[Dict], start_dt: datetime, end_dt: datetime, force_refetch: bool, interval_seconds: int) -> List[Tuple[datetime, datetime]]:
        """Finds time gaps in a list of data points, more robustly."""
        if force_refetch: return [(start_dt, end_dt)]
        if not existing_data: return [(start_dt, end_dt)]

        gaps = []
        # Timestamps of existing data points
        existing_timestamps = {p['timestamp'] for p in existing_data}
        
        # Iterate through expected timestamps and find missing ones
        current_ts = self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds)
        end_ts = self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds)
        
        while current_ts <= end_ts:
            if current_ts not in existing_timestamps:
                gap_start_ts = current_ts
                # Find the end of this gap
                while current_ts <= end_ts and current_ts not in existing_timestamps:
                    current_ts += interval_seconds
                gap_end_ts = current_ts - interval_seconds
                gaps.append((datetime.fromtimestamp(gap_start_ts, tz=timezone.utc), datetime.fromtimestamp(gap_end_ts, tz=timezone.utc)))
            else:
                current_ts += interval_seconds
        
        return gaps

    def _merge_and_save_data(self, base_dir: str, pool_address: str, existing_data: List[Dict], new_data: List[Dict]) -> List[Dict]:
        """
        Merges new data with existing data already on disk and saves to the correct monthly files.
        This function is now safe against data loss by always reading the full monthly cache before writing.
        """
        # AIDEV-NOTE-CLAUDE: This logic was completely rewritten to prevent data loss.
        # The previous version was overwriting monthly cache files with partial data.
        
        all_incoming_data = existing_data + new_data
        
        # Group all incoming points by month
        monthly_updates = {}
        for point in all_incoming_data:
            if not isinstance(point, dict) or 'timestamp' not in point: continue
            month_str = datetime.fromtimestamp(point['timestamp'], tz=timezone.utc).strftime('%Y-%m')
            if month_str not in monthly_updates: monthly_updates[month_str] = {}
            monthly_updates[month_str][point['timestamp']] = point

        # Process each month that has updates
        for month_str, new_points_map in monthly_updates.items():
            month_dir = os.path.join(base_dir, month_str)
            os.makedirs(month_dir, exist_ok=True)
            cache_file = os.path.join(month_dir, f"{pool_address}.json")

            # 1. Read the complete existing data for this month from the file
            full_month_data_map = {}
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        disk_data = json.load(f)
                        if isinstance(disk_data, list):
                            for point in disk_data:
                                if isinstance(point, dict) and 'timestamp' in point:
                                    full_month_data_map[point['timestamp']] = point
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Could not read existing cache file {cache_file}, it will be overwritten. Error: {e}")

            # 2. Merge by overwriting existing points with new ones
            full_month_data_map.update(new_points_map)

            # 3. Save the complete, merged data back to the file
            sorted_points = sorted(full_month_data_map.values(), key=lambda x: x['timestamp'])
            try:
                with open(cache_file, 'w') as f:
                    json.dump(sorted_points, f, indent=2)
            except Exception as e:
                logger.error(f"Failed to save cache file {cache_file}: {e}")

        # Return a fully merged and sorted list of all incoming data points for in-memory use
        final_merged = {p['timestamp']: p for p in all_incoming_data if isinstance(p, dict) and 'timestamp' in p}
        return sorted(final_merged.values(), key=lambda x: x['timestamp'])

    def _conservative_forward_fill(self, data_map: Dict[int, float], interval_seconds: int, start_dt: datetime, end_dt: datetime) -> List[Dict]:
        """Performs a robust forward-fill on the data map to guarantee a continuous series."""
        filled_data = []
        last_valid_price = None
        
        # Find the first available price to start filling
        sorted_keys = sorted(data_map.keys())
        if sorted_keys:
            first_available_ts = sorted_keys[0]
            if first_available_ts <= int(start_dt.timestamp()):
                last_valid_price = data_map[first_available_ts]

        current_ts = self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds)
        end_ts = self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds)

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

    # --- Unchanged helper methods ---
    
    def _get_interval_seconds(self, timeframe: str) -> int:
        return {"10min": 600, "30min": 1800, "1h": 3600, "4h": 14400, "1d": 86400}.get(timeframe, 3600)

    def _align_timestamp_to_boundary(self, timestamp: int, interval_seconds: int) -> int:
        return (timestamp // interval_seconds) * interval_seconds

    def _map_to_candle_boundaries(self, data: List[Dict], interval_seconds: int) -> Dict[int, float]:
        timestamp_map = {}
        for point in data:
            aligned_ts = self._align_timestamp_to_boundary(point['timestamp'], interval_seconds)
            current_price = point.get('close', 0.0)
            if current_price > 0: timestamp_map[aligned_ts] = current_price
        return timestamp_map

    def _log_placeholder_warnings(self, filled_data: List[Dict], pool_address: str, timeframe: str):
        if not filled_data: return
        consecutive_fills = 0
        for point in filled_data:
            if point.get('is_forward_filled'): consecutive_fills += 1
            else:
                if consecutive_fills >= CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD:
                    logger.warning(f"SIGNIFICANT DATA GAP: Filled a gap of {consecutive_fills} points for {pool_address} ({timeframe}).")
                consecutive_fills = 0
        if consecutive_fills >= CONSECUTIVE_PLACEHOLDER_WARNING_THRESHOLD:
            logger.warning(f"SIGNIFICANT DATA GAP: Filled a gap of {consecutive_fills} points for {pool_address} ({timeframe}) at the end of the range.")
    
    def _split_into_monthly_periods(self, start_dt: datetime, end_dt: datetime) -> List[Tuple[datetime, datetime]]:
        periods = []
        current = start_dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        while current <= end_dt:
            next_month_start = (current.replace(day=28) + timedelta(days=4)).replace(day=1)
            periods.append((current, next_month_start - timedelta(seconds=1)))
            current = next_month_start
        return periods

    def _filter_data_by_range(self, data: List[Dict], start_dt: datetime, end_dt: datetime) -> List[Dict]:
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        return sorted([p for p in data if start_ts <= p.get('timestamp', 0) <= end_ts], key=lambda x: x['timestamp'])

    def _determine_timeframe_from_duration(self, start_dt: datetime, end_dt: datetime) -> str:
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        if duration_hours <= 24: return "10min"
        if duration_hours <= 72: return "30min"
        return "1h"
        
    def _fetch_ochlv_from_api(self, pool_address: str, start_dt: datetime, end_dt: datetime, timeframe: str) -> List[Dict]:
        """
        Fetches OCHLV data from Moralis API, with robust error handling, pagination, a circuit breaker,
        and a critical workaround for the fromDate == toDate bug.
        """
        if not self.api_key:
            return []

        # --- CIRCUIT BREAKER ---
        if not hasattr(self, '_api_circuit_breaker_open'): self._api_circuit_breaker_open = False
        if self._api_circuit_breaker_open:
            logger.warning(f"API circuit breaker is open. Skipping request for {pool_address}.")
            return []

        url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
        headers = {"accept": "application/json", "X-API-Key": self.api_key}
        
        # --- AIDEV-NOTE-CLAUDE: CRITICAL MORALIS API WORKAROUND ---
        # The API returns 400 Bad Request if fromDate == toDate.
        # This logic ensures we always request at least a one-day range.
        from_date_str = start_dt.strftime('%Y-%m-%d')
        to_date_str = end_dt.strftime('%Y-%m-%d')
        
        if from_date_str == to_date_str:
            api_end_dt = end_dt + timedelta(days=1)
            to_date_str = api_end_dt.strftime('%Y-%m-%d')
            logger.info(f"Applying Moralis single-day workaround for {from_date_str}.")
        # --- END WORKAROUND ---

        params = {
            "timeframe": timeframe,
            "fromDate": from_date_str,
            "toDate": to_date_str,
            "limit": 500
        }
        
        all_results = []
        page_count = 0
        while True:
            page_count += 1
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code in [401, 403, 429]:  # Unauthorized, Forbidden, Too Many Requests
                    error_reason = "Unknown"
                    if response.status_code == 401: error_reason = "Unauthorized (Invalid API Key?)"
                    if response.status_code == 403: error_reason = "Forbidden (Permission Denied)"
                    if response.status_code == 429: error_reason = "Too Many Requests (API credits likely exhausted)"
                    
                    logger.error(f"CRITICAL API ERROR ({response.status_code} - {error_reason}) for {pool_address}. Opening circuit breaker.")
                    self._api_circuit_breaker_open = True
                    return []  # Stop immediately
                response.raise_for_status()
                data = response.json()
                api_result = data.get('result', [])
                if isinstance(api_result, list): all_results.extend(api_result)
                cursor = data.get('cursor')
                if cursor:
                    params['cursor'] = cursor
                    time.sleep(0.3)
                else:
                    break
            except requests.exceptions.HTTPError as e:
                logger.error(f"API HTTPError (likely 400 Bad Request) for {pool_address} with params {params}. The pair may not be supported. Error: {e}")
                return []
            except requests.exceptions.RequestException as e:
                logger.error(f"API RequestException for {pool_address}. Returning partial data if any. Error: {e}")
                break

        processed_data = []
        for point in all_results:
            try:
                processed_data.append({
                    'timestamp': int(datetime.fromisoformat(point['timestamp'].replace('Z', '+00:00')).timestamp()),
                    'open': float(point.get('open', 0)), 'close': float(point.get('close', 0)),
                    'high': float(point.get('high', 0)), 'low': float(point.get('low', 0)),
                    'volume': float(point.get('volume', 0))
                })
            except (ValueError, TypeError, KeyError): pass
        
        unique_points = {d['timestamp']: d for d in processed_data}
        final_data = sorted(unique_points.values(), key=lambda x: x['timestamp'])

        logger.info(f"Fetched {len(final_data)} total unique OCHLV points in {page_count} page(s) for {pool_address} from {params['fromDate']} to {params['toDate']}")
        return final_data