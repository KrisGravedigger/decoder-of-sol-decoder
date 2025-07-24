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
from typing import Dict, List, Optional, Tuple, Any
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
    
    def __init__(self, cache_dir: str = "price_cache", config: Optional[Dict] = None):
        self.cache_dir = cache_dir
        self.config = config or {}
        self.offline_cache_dir = os.path.join(cache_dir, "offline_processed")
        
        # Create cache directories
        os.makedirs(cache_dir, exist_ok=True)
        os.makedirs(self.offline_cache_dir, exist_ok=True)
        
        # User choice memory for interactive gap handling
        self._user_choice_memory = None
        
    def get_price_data(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                    timeframe: str, api_key: Optional[str] = None,
                    force_refetch: bool = False, use_raw_cache: Optional[bool] = None) -> List[Dict]:
        """
        Get price data with smart caching and guaranteed continuous output.
        Now supports offline-first mode with raw cache conversion.
        
        Args:
            pool_address (str): Pool address
            start_dt (datetime): Start datetime
            end_dt (datetime): End datetime
            timeframe (str): Timeframe (10min, 30min, 1h, 4h)
            api_key (Optional[str]): API key for fetching missing data
            force_refetch (bool): If True, re-fetches data even for cached empty gaps.
            use_raw_cache (Optional[bool]): If True, prefer offline cache. If None, use config.
            
        Returns:
            List[Dict]: Price data with timestamp and close keys, continuous and forward-filled.
        """
        # Determine cache preference
        if use_raw_cache is None:
            use_raw_cache = self.config.get('data_source', {}).get('prefer_offline_cache', False)
        
        interactive_gap_handling = self.config.get('data_source', {}).get('interactive_gap_handling', True)
        
        interval_seconds = self._get_interval_seconds(timeframe)
        aligned_start_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(start_dt.timestamp()), interval_seconds))
        aligned_end_dt = datetime.fromtimestamp(self._align_timestamp_to_boundary(int(end_dt.timestamp()), interval_seconds))
        
        logger.debug(f"Getting price data for {pool_address} ({timeframe}): {start_dt} to {end_dt}")
        logger.debug(f"Cache mode: {'offline-first' if use_raw_cache else 'online-first'}")
        
        # Reset user choice memory at start of new batch
        if hasattr(self, '_batch_start'):
            if not self._batch_start:
                self._user_choice_memory = None
                self._batch_start = True
        else:
            self._batch_start = True
        
        # Try cache hierarchy
        all_data = []
        data_source = "none"
        
        if use_raw_cache:
            # 1. Check offline processed cache first
            offline_data, status = self._check_offline_cache_completeness(
                pool_address, aligned_start_dt, aligned_end_dt, timeframe
            )
            
            if status == 'complete':
                all_data = offline_data
                data_source = "offline_processed"
                logger.info(f"Using complete offline cache for {pool_address}")
            elif status == 'partial' and interactive_gap_handling:
                # Handle incomplete data interactively
                choice, _ = self._handle_incomplete_data(
                    pool_address, aligned_start_dt, aligned_end_dt, timeframe
                )
                
                if choice == 'use_partial':
                    all_data = offline_data
                    data_source = "offline_processed_partial"
                    logger.info(f"Using partial offline cache for {pool_address}")
                elif choice == 'try_fallback':
                    # Try to generate from raw cache
                    try:
                        from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
                        enhanced_cache = EnhancedPriceCacheManager(self.cache_dir)
                        
                        raw_data = enhanced_cache.fetch_ochlv_data(
                            pool_address, aligned_start_dt, aligned_end_dt,
                            use_cache_only=True, force_refetch=False
                        )
                        
                        if raw_data:
                            converted_data = self._generate_offline_cache(
                                pool_address, aligned_start_dt, aligned_end_dt, timeframe, raw_data
                            )
                            all_data = converted_data
                            data_source = "generated_from_raw"
                            logger.info(f"Generated offline cache from raw for {pool_address}")
                    except Exception as e:
                        logger.error(f"Failed to generate from raw cache: {e}")
                elif choice == 'skip':
                    logger.info(f"Skipping position {pool_address} per user choice")
                    return []
            
            # If still no data, try to generate from raw
            if not all_data and not interactive_gap_handling:
                try:
                    from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
                    enhanced_cache = EnhancedPriceCacheManager(self.cache_dir)
                    
                    raw_data = enhanced_cache.fetch_ochlv_data(
                        pool_address, aligned_start_dt, aligned_end_dt,
                        use_cache_only=True, force_refetch=False
                    )
                    
                    if raw_data:
                        converted_data = self._generate_offline_cache(
                            pool_address, aligned_start_dt, aligned_end_dt, timeframe, raw_data
                        )
                        all_data = converted_data
                        data_source = "generated_from_raw"
                        logger.info(f"Auto-generated offline cache from raw for {pool_address}")
                except Exception as e:
                    logger.error(f"Failed to auto-generate from raw cache: {e}")
        
        # Fall back to existing online cache logic if needed
        if not all_data:
            logger.debug(f"Falling back to standard cache for {pool_address}")
            monthly_periods = self._split_into_monthly_periods(aligned_start_dt, aligned_end_dt)
            
            for month_start, month_end in monthly_periods:
                month_data = self._get_monthly_data(
                    pool_address, month_start, month_end, timeframe, api_key, force_refetch
                )
                all_data.extend(month_data)
            
            data_source = "online_cache" if all_data else "api"
        
        logger.debug(f"Data source for {pool_address}: {data_source}")
        
        timestamp_map = self._map_to_candle_boundaries(all_data, interval_seconds)
        final_data = self._conservative_forward_fill(
            timestamp_map, 
            interval_seconds, 
            aligned_start_dt, 
            aligned_end_dt
        )
        
        # Log warnings about filled gaps
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
    
    def _generate_offline_cache(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                               timeframe: str, raw_data: List[Dict]) -> List[Dict]:
        """
        Convert OCHLV data to simple price format and save to offline cache.
        
        Args:
            pool_address: Pool address
            start_dt: Start datetime
            end_dt: End datetime  
            timeframe: Timeframe
            raw_data: Raw OCHLV data
            
        Returns:
            List[Dict]: Converted price data with timestamp and close keys
        """
        # Convert OCHLV to simple format (extract timestamp and close)
        converted_data = []
        for point in raw_data:
            if isinstance(point, dict) and 'timestamp' in point and 'close' in point:
                converted_data.append({
                    'timestamp': point['timestamp'],
                    'close': point['close']
                })
        
        if not converted_data:
            return []
            
        # Save to offline cache using same monthly structure
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        
        for month_start, month_end in monthly_periods:
            month_str = month_start.strftime('%Y-%m')
            cache_filename = f"{pool_address}_{timeframe}_{month_str}.json"
            cache_path = os.path.join(self.offline_cache_dir, cache_filename)
            
            # Load existing offline cache data
            existing_data = self._load_cache_file(cache_path)
            
            # Filter converted data for this month
            month_data = self._filter_existing_data(converted_data, month_start, month_end)
            
            if month_data:
                # Merge and save
                merged_data = self._merge_and_save(existing_data, month_data, cache_path)
                
        return converted_data
    
    def _check_offline_cache_completeness(self, pool_address: str, start_dt: datetime, 
                                        end_dt: datetime, timeframe: str) -> Tuple[List[Dict], str]:
        """
        Check offline cache completeness for a position.
        
        Returns:
            Tuple of (data, status) where status is 'complete', 'partial', or 'missing'
        """
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        all_data = []
        
        for month_start, month_end in monthly_periods:
            month_str = month_start.strftime('%Y-%m')
            cache_filename = f"{pool_address}_{timeframe}_{month_str}.json"
            cache_path = os.path.join(self.offline_cache_dir, cache_filename)
            
            month_data = self._load_cache_file(cache_path)
            if month_data:
                filtered_data = self._filter_existing_data(month_data, month_start, month_end)
                all_data.extend(filtered_data)
        
        if not all_data:
            return [], 'missing'
            
        # Check coverage
        expected_points = self._calculate_expected_points(start_dt, end_dt, timeframe)
        actual_points = len(all_data)
        
        coverage_ratio = actual_points / expected_points if expected_points > 0 else 0
        
        if coverage_ratio >= 0.95:  # 95% coverage threshold
            return all_data, 'complete'
        elif coverage_ratio >= 0.5:  # 50% coverage threshold
            return all_data, 'partial'
        else:
            return all_data, 'missing'
    
    def _calculate_expected_points(self, start_dt: datetime, end_dt: datetime, timeframe: str) -> int:
        """Calculate expected number of data points for a time range."""
        interval_seconds = self._get_interval_seconds(timeframe)
        duration_seconds = (end_dt - start_dt).total_seconds()
        return max(1, int(duration_seconds / interval_seconds))
    
    def _handle_incomplete_data(self, pool_address: str, start_dt: datetime, 
                              end_dt: datetime, timeframe: str) -> Tuple[Optional[str], bool]:
        """
        Handle incomplete data with interactive user choice.
        
        Returns:
            Tuple of (user_choice, apply_to_all)
        """
        # Check if we have a memory choice
        if self._user_choice_memory:
            return self._user_choice_memory, True
            
        print(f"\n⚠️  Incomplete data detected for {pool_address}")
        print(f"   Period: {start_dt.strftime('%Y-%m-%d %H:%M')} to {end_dt.strftime('%Y-%m-%d %H:%M')}")
        print("\nOptions:")
        print("1. Use partial data and continue")
        print("2. Try fallback to raw cache generation")
        print("3. Skip this position")
        print("4. Use partial data for ALL remaining positions")
        print("5. Try fallback for ALL remaining positions")
        print("6. Skip ALL positions with missing data")
        
        while True:
            choice = input("\nSelect option (1-6): ").strip()
            
            if choice == '1':
                return 'use_partial', False
            elif choice == '2':
                return 'try_fallback', False
            elif choice == '3':
                return 'skip', False
            elif choice == '4':
                self._user_choice_memory = ('use_partial', True)
                return 'use_partial', True
            elif choice == '5':
                self._user_choice_memory = ('try_fallback', True)
                return 'try_fallback', True
            elif choice == '6':
                self._user_choice_memory = ('skip', True)
                return 'skip', True
            else:
                print("Invalid choice. Please select 1-6.")
    
    def refresh_offline_cache(self):
        """Refresh offline cache from raw OCHLV data."""
        print("\nRefreshing offline processed cache from raw OCHLV data...")
        
        # Import locally to avoid circular imports
        from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
        enhanced_cache = EnhancedPriceCacheManager(self.cache_dir)
        
        # Get list of all raw cache files
        raw_dir = os.path.join(self.cache_dir, "raw")
        if not os.path.exists(raw_dir):
            print("No raw cache directory found. Please fetch OCHLV data first.")
            return
            
        processed_count = 0
        for month_dir in os.listdir(raw_dir):
            month_path = os.path.join(raw_dir, month_dir)
            if not os.path.isdir(month_path):
                continue
                
            for filename in os.listdir(month_path):
                if filename.endswith('.json'):
                    pool_address = filename.replace('.json', '')
                    raw_file_path = os.path.join(month_path, filename)
                    
                    try:
                        with open(raw_file_path, 'r') as f:
                            raw_data = json.load(f)
                            
                        if raw_data:
                            # Convert and save to offline cache
                            # We need to determine the date range from the data
                            timestamps = [self._parse_timestamp_to_unix(d['timestamp']) for d in raw_data]
                            start_dt = datetime.fromtimestamp(min(timestamps))
                            end_dt = datetime.fromtimestamp(max(timestamps))
                            
                            # Guess timeframe from data density
                            timeframe = self._guess_timeframe_from_data(raw_data)
                            
                            self._generate_offline_cache(pool_address, start_dt, end_dt, timeframe, raw_data)
                            processed_count += 1
                            
                    except Exception as e:
                        logger.error(f"Failed to process {filename}: {e}")
                        
        print(f"Processed {processed_count} raw cache files into offline cache.")
    
    def _guess_timeframe_from_data(self, data: List[Dict]) -> str:
        """Guess timeframe from data point spacing."""
        if len(data) < 2:
            return "1h"  # Default
            
        # Calculate average interval
        timestamps = sorted([self._parse_timestamp_to_unix(d['timestamp']) for d in data[:10]])
        intervals = [timestamps[i+1] - timestamps[i] for i in range(len(timestamps)-1)]
        avg_interval = sum(intervals) / len(intervals) if intervals else 3600
        
        # Map to closest timeframe
        if avg_interval < 900:  # < 15 min
            return "10min"
        elif avg_interval < 2700:  # < 45 min
            return "30min"
        elif avg_interval < 7200:  # < 2 hours
            return "1h"
        else:
            return "4h"
    
    def validate_offline_cache_completeness(self):
        """Validate offline cache completeness for all positions."""
        print("\nValidating offline cache completeness...")
        
        try:
            # Load positions
            from reporting.data_loader import load_and_prepare_positions
            positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
            
            if positions_df.empty:
                print("No positions found in positions_to_analyze.csv")
                return
                
            complete_count = 0
            partial_count = 0
            missing_count = 0
            
            for idx, row in positions_df.iterrows():
                pool_address = row.get('pool_address')
                start_dt = row.get('open_timestamp')
                end_dt = row.get('close_timestamp')
                
                if not all([pool_address, start_dt, end_dt]):
                    missing_count += 1
                    continue
                    
                # Determine timeframe
                timeframe = self._get_timeframe_for_duration(start_dt, end_dt)
                
                # Check offline cache
                _, status = self._check_offline_cache_completeness(pool_address, start_dt, end_dt, timeframe)
                
                if status == 'complete':
                    complete_count += 1
                elif status == 'partial':
                    partial_count += 1
                else:
                    missing_count += 1
                    
            total = len(positions_df)
            print(f"\nOffline Cache Status:")
            print(f"  Complete: {complete_count}/{total} ({complete_count/total*100:.1f}%)")
            print(f"  Partial:  {partial_count}/{total} ({partial_count/total*100:.1f}%)")
            print(f"  Missing:  {missing_count}/{total} ({missing_count/total*100:.1f}%)")
            
        except Exception as e:
            logger.error(f"Offline cache validation failed: {e}")
            print(f"Error during validation: {e}")
    
    def _parse_timestamp_to_unix(self, timestamp: Any) -> int:
        """Parse various timestamp formats to unix timestamp."""
        if isinstance(timestamp, (int, float)):
            return int(timestamp)
        if isinstance(timestamp, str):
            try:
                # Try ISO format first
                if 'T' in timestamp:
                    return int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp())
                # Try parsing as number
                return int(float(timestamp))
            except (ValueError, TypeError):
                return 0
        return 0