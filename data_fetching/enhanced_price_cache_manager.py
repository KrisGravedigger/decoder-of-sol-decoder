"""
Enhanced Price Cache Manager with Volume Data Support - TP/SL Optimizer Phase 1

Extends the existing PriceCacheManager to support OCHLV+Volume data collection
with a consistent, offline-first approach.
"""

import os
import json
import requests
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import logging

# AIDEV-VOLUME-CLAUDE: Import base class to extend
from reporting.price_cache_manager import PriceCacheManager

logger = logging.getLogger(__name__)

class EnhancedPriceCacheManager(PriceCacheManager):
    """
    Enhanced cache manager with volume data support for TP/SL optimization.
    
    Maintains full backward compatibility while adding:
    - Raw OCHLV+Volume data caching
    - Consistent and predictable offline-first operation
    - Volume data retrieval for position analysis
    - Cache completeness validation that is synchronized with fetch logic
    """
    
    def __init__(self, cache_dir: str = "price_cache"):
        super().__init__(cache_dir)
        self.raw_cache_dir = os.path.join(cache_dir, "raw")
        os.makedirs(self.raw_cache_dir, exist_ok=True)
        
    def fetch_ochlv_data(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                        use_cache_only: bool = False, force_refetch: bool = False) -> List[Dict]:
        """
        Fetch OCHLV+Volume data with an offline-first approach.
        """
        timeframe = self._determine_timeframe_from_duration(start_dt, end_dt)
        
        cached_data = self._load_raw_cache_for_period(pool_address, start_dt, end_dt, timeframe)
        
        is_sufficient = self._is_cache_data_sufficient(cached_data, start_dt, end_dt, timeframe)
        
        if is_sufficient and not force_refetch:
            logger.debug(f"Using sufficient cache for {pool_address}")
            all_data = cached_data
        else:
            if use_cache_only:
                logger.warning(f"Cache-only mode: Data for {pool_address} is insufficient/missing. Returning partial data.")
                all_data = cached_data
            else:
                logger.info(f"Cache insufficient or force_refetch=True for {pool_address}. Fetching from API.")
                all_data = self._fetch_and_merge_data_cross_month(pool_address, start_dt, end_dt, timeframe)
            
        return self._filter_ochlv_data_by_range(all_data, start_dt, end_dt)
    
    def _fetch_and_merge_data_cross_month(self, pool_address: str, start_dt: datetime, 
                                          end_dt: datetime, timeframe: str) -> List[Dict]:
        """
        Fetches OCHLV data from the API for the given period and merges it with existing cache.
        """
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        
        # We start with what's in the cache for the entire period
        all_data = self._load_raw_cache_for_period(pool_address, start_dt, end_dt, timeframe)
        
        for month_start, month_end in monthly_periods:
            api_data = self._fetch_ochlv_from_api(pool_address, month_start, month_end, timeframe)
            if api_data:
                all_data = self._merge_and_save_raw_cache(all_data, api_data, pool_address, month_start)
        
        return all_data

    def get_volume_for_position(self, position: Any) -> List[float]:
        """
        Get volume data for a specific position from the cache.
        """
        try:
            pool_address = getattr(position, 'pool_address', None)
            open_timestamp = getattr(position, 'open_timestamp', None) 
            close_timestamp = getattr(position, 'close_timestamp', None)
            
            if not all([pool_address, open_timestamp, close_timestamp]):
                return []
                
            if isinstance(open_timestamp, str):
                from reporting.data_loader import _parse_custom_timestamp
                open_timestamp = _parse_custom_timestamp(open_timestamp)
            if isinstance(close_timestamp, str):
                from reporting.data_loader import _parse_custom_timestamp  
                close_timestamp = _parse_custom_timestamp(close_timestamp)
                
            ochlv_data = self.fetch_ochlv_data(
                pool_address, open_timestamp, close_timestamp, use_cache_only=True
            )
            return [point.get('volume', 0.0) for point in ochlv_data]
            
        except Exception as e:
            logger.error(f"Failed to get volume for position: {e}")
            return []
    
    def validate_cache_completeness(self, position: Any) -> Dict[str, bool]:
        """
        Validate cache completeness for a position using the same logic as the fetcher.
        """
        try:
            pool_address = getattr(position, 'pool_address', None)
            open_timestamp = getattr(position, 'open_timestamp', None)
            close_timestamp = getattr(position, 'close_timestamp', None)
            
            if not all([pool_address, open_timestamp, close_timestamp]):
                return {'has_price_data': False, 'has_volume_data': False, 'is_complete': False}
                
            if isinstance(open_timestamp, str):
                from reporting.data_loader import _parse_custom_timestamp
                open_timestamp = _parse_custom_timestamp(open_timestamp)
            if isinstance(close_timestamp, str):
                from reporting.data_loader import _parse_custom_timestamp
                close_timestamp = _parse_custom_timestamp(close_timestamp)
                
            timeframe = self._determine_timeframe_from_duration(open_timestamp, close_timestamp)
            cached_data = self._load_raw_cache_for_period(pool_address, open_timestamp, close_timestamp, timeframe)
            
            is_sufficient = self._is_cache_data_sufficient(cached_data, open_timestamp, close_timestamp, timeframe)
            has_volume = any(p.get('volume', 0.0) > 0 for p in cached_data) if cached_data else False
            
            return {
                'has_price_data': is_sufficient,
                'has_volume_data': has_volume,
                'is_complete': is_sufficient and has_volume
            }
            
        except Exception as e:
            logger.error(f"Cache validation failed: {e}")
            return {'has_price_data': False, 'has_volume_data': False, 'is_complete': False}
    
    def _determine_timeframe_from_duration(self, start_dt: datetime, end_dt: datetime) -> str:
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        if duration_hours <= 4: return "10min"
        if duration_hours <= 12: return "30min" 
        if duration_hours <= 72: return "1h"
        return "4h"
    
    def _load_raw_cache_for_period(self, pool_address: str, start_dt: datetime, 
                                  end_dt: datetime, timeframe: str) -> List[Dict]:
        """
        Load raw cache data for a specific period, handling cross-month spans.
        """
        monthly_periods = self._split_into_monthly_periods(start_dt, end_dt)
        all_cached_data = []
        for month_start_period, _ in monthly_periods:
            month_str = month_start_period.strftime('%Y-%m')
            month_dir = os.path.join(self.raw_cache_dir, month_str)
            cache_file = os.path.join(month_dir, f"{pool_address}.json")
            if os.path.exists(cache_file):
                try:
                    with open(cache_file, 'r') as f:
                        data = json.load(f)
                    all_cached_data.extend(data)
                except Exception as e:
                    logger.error(f"Failed to load raw cache {cache_file}: {e}")
        
        unique_points = {self._parse_timestamp_to_unix(p['timestamp']): p for p in all_cached_data if isinstance(p, dict) and 'timestamp' in p}
        return sorted(unique_points.values(), key=lambda x: self._parse_timestamp_to_unix(x['timestamp']))

    def _is_cache_data_sufficient(self, cached_data: List[Dict], start_dt: datetime, 
                                 end_dt: datetime, timeframe: str) -> bool:
        """
        Check if cached data is sufficient, using robust quantity and time-span checks.
        """
        if not cached_data: return False
        
        # 1. Quantity Check
        expected_points = self._calculate_expected_data_points(start_dt, end_dt, timeframe)
        actual_points = len(cached_data)
        quantity_sufficient = (actual_points / expected_points if expected_points > 0 else 0) >= 0.80

        # 2. Time Span Check (More robust than start/end point check)
        request_span_seconds = (end_dt - start_dt).total_seconds()
        
        data_timestamps = [self._parse_timestamp_to_unix(p['timestamp']) for p in cached_data]
        data_start_ts = min(data_timestamps)
        data_end_ts = max(data_timestamps)
        data_span_seconds = data_end_ts - data_start_ts
        
        # The data should cover at least 80% of the requested time duration
        timespan_sufficient = (data_span_seconds / request_span_seconds if request_span_seconds > 0 else 0) >= 0.80
        
        is_sufficient = quantity_sufficient and timespan_sufficient

        deep_debug_logger = logging.getLogger('DEEP_DEBUG')
        if deep_debug_logger.isEnabledFor(logging.DEBUG):
            deep_debug_logger.debug(f"Cache sufficiency check for {start_dt} to {end_dt}:")
            deep_debug_logger.debug(f"  Quantity sufficient: {quantity_sufficient} ({actual_points}/{expected_points} points)")
            deep_debug_logger.debug(f"  Time span sufficient: {timespan_sufficient} ({data_span_seconds/3600:.1f}h / {request_span_seconds/3600:.1f}h covered)")
            deep_debug_logger.debug(f"  Final result: {'sufficient' if is_sufficient else 'insufficient'}")
            
        return is_sufficient

    def _calculate_expected_data_points(self, start_dt: datetime, end_dt: datetime, timeframe: str) -> int:
        duration_seconds = (end_dt - start_dt).total_seconds()
        interval_seconds = self._get_interval_seconds(timeframe)
        return max(1, int(duration_seconds / interval_seconds))
    
    def _fetch_ochlv_from_api(self, pool_address: str, start_dt: datetime, 
                             end_dt: datetime, timeframe: str) -> List[Dict]:
        """
        Fetch OCHLV+Volume data from Moralis API.
        """
        api_key = os.getenv("MORALIS_API_KEY")
        if not api_key:
            logger.error("MORALIS_API_KEY not found. Cannot fetch OCHLV data.")
            return []
            
        url = f"https://solana-gateway.moralis.io/token/mainnet/pairs/{pool_address}/ohlcv"
        headers = {"accept": "application/json", "X-API-Key": api_key}
        params = {
            "timeframe": timeframe,
            "fromDate": start_dt.strftime('%Y-%m-%d'),
            "toDate": (end_dt + timedelta(days=1)).strftime('%Y-%m-%d'),
            "currency": "usd"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=20)
            response.raise_for_status()
            data = response.json()
            api_result = data.get('result', []) if isinstance(data, dict) else data
            
            processed_data = []
            if isinstance(api_result, list):
                for point in api_result:
                    try:
                        processed_data.append({
                            'timestamp': self._parse_timestamp_to_unix(point.get('timestamp')),
                            'open': float(point.get('open', 0)),
                            'close': float(point.get('close', 0)),
                            'high': float(point.get('high', 0)),
                            'low': float(point.get('low', 0)),
                            'volume': float(point.get('volume', 0))
                        })
                    except (ValueError, TypeError, KeyError) as e:
                        logger.warning(f"Skipping invalid API data point: {point}. Error: {e}")
            
            logger.info(f"Fetched {len(processed_data)} OCHLV points from API for {pool_address}")
            time.sleep(0.6)
            return processed_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed for {pool_address}: {e}")
            return []
    
    def _merge_and_save_raw_cache(self, existing_data: List[Dict], new_data: List[Dict], 
                                 pool_address: str, month_start: datetime) -> List[Dict]:
        """
        Merge new data with existing data and save to the corresponding monthly raw cache file.
        """
        merged_map = {self._parse_timestamp_to_unix(p['timestamp']): p for p in existing_data}
        merged_map.update({self._parse_timestamp_to_unix(p['timestamp']): p for p in new_data})
        
        merged_data = sorted(list(merged_map.values()), key=lambda x: self._parse_timestamp_to_unix(x['timestamp']))
        
        month_str = month_start.strftime('%Y-%m')
        month_dir = os.path.join(self.raw_cache_dir, month_str)
        os.makedirs(month_dir, exist_ok=True)
        cache_file = os.path.join(month_dir, f"{pool_address}.json")
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(merged_data, f, indent=2)
            logger.info(f"Saved/Updated {len(merged_data)} points to raw cache: {os.path.basename(cache_file)}")
        except Exception as e:
            logger.error(f"Failed to save raw cache {cache_file}: {e}")
        return merged_data
    
    def _filter_ochlv_data_by_range(self, data: List[Dict], start_dt: datetime, end_dt: datetime) -> List[Dict]:
        start_ts = int(start_dt.timestamp())
        end_ts = int(end_dt.timestamp())
        
        filtered = [p for p in data if start_ts <= self._parse_timestamp_to_unix(p.get('timestamp')) <= end_ts]
        return sorted(filtered, key=lambda x: self._parse_timestamp_to_unix(x['timestamp']))
    
    def _parse_timestamp_to_unix(self, timestamp: Any) -> int:
        if isinstance(timestamp, (int, float)): return int(timestamp)
        if isinstance(timestamp, str):
            try:
                if 'T' in timestamp:
                    return int(datetime.fromisoformat(timestamp.replace('Z', '+00:00')).timestamp())
                return int(float(timestamp))
            except (ValueError, TypeError): return 0
        return 0