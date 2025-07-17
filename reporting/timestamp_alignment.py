"""
Timestamp Alignment Module

Handles proper alignment of arbitrary timestamps to API candle intervals
following Python best practices.
"""

from datetime import datetime, timezone
from typing import Tuple, Dict, Optional
import math
from enum import Enum

class TimeFrame(Enum):
    """Supported timeframes with their interval seconds."""
    MIN_10 = ("10min", 600)
    MIN_30 = ("30min", 1800) 
    HOUR_1 = ("1h", 3600)
    HOUR_4 = ("4h", 14400)
    
    def __init__(self, label: str, seconds: int):
        self.label = label
        self.seconds = seconds
    
    @classmethod
    def from_string(cls, timeframe_str: str) -> 'TimeFrame':
        """Convert string timeframe to enum."""
        for tf in cls:
            if tf.label == timeframe_str:
                return tf
        raise ValueError(f"Unsupported timeframe: {timeframe_str}")

class TimestampAligner:
    """
    Handles alignment of arbitrary timestamps to API candle boundaries.
    
    Follows Python best practices:
    - Immutable operations
    - Pure functions 
    - Comprehensive type hints
    - Clear separation of concerns
    """
    
    @staticmethod
    def align_to_candle_boundary(
        timestamp: datetime, 
        timeframe: TimeFrame,
        alignment: str = "floor"
    ) -> datetime:
        """
        Align timestamp to nearest candle boundary.
        
        Args:
            timestamp (datetime): Arbitrary timestamp to align
            timeframe (TimeFrame): Target timeframe for alignment
            alignment (str): "floor", "ceil", or "nearest"
            
        Returns:
            datetime: Aligned timestamp at candle boundary
            
        Raises:
            ValueError: If alignment parameter is invalid
        """
        if alignment not in ["floor", "ceil", "nearest"]:
            raise ValueError(f"Invalid alignment: {alignment}. Use 'floor', 'ceil', or 'nearest'")
        
        # Ensure UTC timezone for consistent calculations
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        
        # Convert to Unix timestamp for interval math
        unix_ts = timestamp.timestamp()
        interval_seconds = timeframe.seconds
        
        if alignment == "floor":
            aligned_unix = math.floor(unix_ts / interval_seconds) * interval_seconds
        elif alignment == "ceil":
            aligned_unix = math.ceil(unix_ts / interval_seconds) * interval_seconds
        else:  # nearest
            aligned_unix = round(unix_ts / interval_seconds) * interval_seconds
        
        return datetime.fromtimestamp(aligned_unix, tz=timezone.utc)
    
    @staticmethod
    def create_aligned_range(
        start_time: datetime,
        end_time: datetime, 
        timeframe: TimeFrame
    ) -> Tuple[datetime, datetime]:
        """
        Create properly aligned start/end range for API requests.
        
        Uses floor for start (to include requested period) and ceil for end
        (to ensure complete coverage).
        
        Args:
            start_time (datetime): Requested start time
            end_time (datetime): Requested end time
            timeframe (TimeFrame): Timeframe for alignment
            
        Returns:
            Tuple[datetime, datetime]: (aligned_start, aligned_end)
        """
        aligned_start = TimestampAligner.align_to_candle_boundary(
            start_time, timeframe, "floor"
        )
        aligned_end = TimestampAligner.align_to_candle_boundary(
            end_time, timeframe, "ceil" 
        )
        
        return aligned_start, aligned_end
    
    @staticmethod
    def find_nearest_candle_timestamp(
        target_timestamp: datetime,
        available_candles: Dict[int, float],
        timeframe: TimeFrame,
        max_deviation_candles: int = 1
    ) -> Optional[datetime]:
        """
        Find nearest available candle timestamp to target.
        
        Args:
            target_timestamp (datetime): Target timestamp to find candle for
            available_candles (Dict[int, float]): Available candle data {unix_ts: price}
            timeframe (TimeFrame): Timeframe for deviation calculation
            max_deviation_candles (int): Maximum candles deviation allowed
            
        Returns:
            Optional[datetime]: Nearest candle timestamp or None if too far
        """
        target_unix = target_timestamp.timestamp()
        max_deviation_seconds = max_deviation_candles * timeframe.seconds
        
        # Find closest available timestamp
        closest_unix = None
        min_distance = float('inf')
        
        for candle_unix in available_candles.keys():
            distance = abs(candle_unix - target_unix)
            if distance < min_distance and distance <= max_deviation_seconds:
                min_distance = distance
                closest_unix = candle_unix
        
        return datetime.fromtimestamp(closest_unix, tz=timezone.utc) if closest_unix else None

class CacheRequestOptimizer:
    """
    Optimizes cache requests by aligning timestamps before API calls.
    
    Prevents creation of unnecessary placeholder timestamps that don't
    align with API candle boundaries.
    """
    
    def __init__(self, aligner: TimestampAligner = None):
        """Initialize with optional custom aligner."""
        self.aligner = aligner or TimestampAligner()
    
    def optimize_request_range(
        self,
        raw_start: datetime,
        raw_end: datetime,
        timeframe_str: str
    ) -> Tuple[datetime, datetime, Dict[str, any]]:
        """
        Optimize request range for API efficiency.
        
        Args:
            raw_start (datetime): Raw start timestamp from position
            raw_end (datetime): Raw end timestamp from position  
            timeframe_str (str): Timeframe string (e.g., "30min")
            
        Returns:
            Tuple containing:
                - Optimized start datetime
                - Optimized end datetime  
                - Metadata dict with alignment info
        """
        timeframe = TimeFrame.from_string(timeframe_str)
        
        # Ensure timezone consistency - convert naive to UTC if needed
        if raw_start.tzinfo is None:
            raw_start = raw_start.replace(tzinfo=timezone.utc)
        if raw_end.tzinfo is None:
            raw_end = raw_end.replace(tzinfo=timezone.utc)
        
        # Create aligned range
        aligned_start, aligned_end = self.aligner.create_aligned_range(
            raw_start, raw_end, timeframe
        )
        
        # Calculate alignment metadata
        start_shift = (aligned_start - raw_start).total_seconds()
        end_shift = (aligned_end - raw_end).total_seconds()
        
        metadata = {
            'original_start': raw_start,
            'original_end': raw_end,
            'start_shift_seconds': start_shift,
            'end_shift_seconds': end_shift,
            'timeframe': timeframe.label,
            'alignment_applied': True
        }
        
        return aligned_start, aligned_end, metadata

# Integration point for existing price_cache_manager.py
def integrate_with_cache_manager():
    """
    Example integration with existing cache manager.
    Replace the timestamp handling in get_price_data method.
    """
    optimizer = CacheRequestOptimizer()
    
    # In price_cache_manager.py, replace:
    # OLD: cache_manager.get_price_data(pool_address, start_dt, end_dt, timeframe, api_key)
    # NEW: 
    """
    def get_price_data(self, pool_address: str, start_dt: datetime, end_dt: datetime, 
                      timeframe: str, api_key: Optional[str] = None) -> List[Dict]:
        # NEW: Optimize timestamps before processing
        optimizer = CacheRequestOptimizer()
        aligned_start, aligned_end, alignment_metadata = optimizer.optimize_request_range(
            start_dt, end_dt, timeframe
        )
        
        # Log alignment info for transparency
        if alignment_metadata['start_shift_seconds'] != 0 or alignment_metadata['end_shift_seconds'] != 0:
            logger.info(f"Timestamp alignment applied: start shifted {alignment_metadata['start_shift_seconds']}s, "
                       f"end shifted {alignment_metadata['end_shift_seconds']}s")
        
        # Continue with existing logic using aligned timestamps
        monthly_periods = self._split_into_monthly_periods(aligned_start, aligned_end)
        # ... rest of existing code unchanged
    """

# Unit tests (would be in separate test file)
def test_alignment_examples():
    """Example test cases demonstrating the fix."""
    aligner = TimestampAligner()
    
    # Test case from our bug
    problematic_time = datetime(2025, 6, 6, 13, 58, 57, tzinfo=timezone.utc)
    timeframe = TimeFrame.MIN_30
    
    aligned = aligner.align_to_candle_boundary(problematic_time, timeframe, "floor")
    expected = datetime(2025, 6, 6, 13, 30, 0, tzinfo=timezone.utc)
    
    assert aligned == expected, f"Expected {expected}, got {aligned}"
    
    aligned_ceil = aligner.align_to_candle_boundary(problematic_time, timeframe, "ceil")  
    expected_ceil = datetime(2025, 6, 6, 14, 0, 0, tzinfo=timezone.utc)
    
    assert aligned_ceil == expected_ceil, f"Expected {expected_ceil}, got {aligned_ceil}"

if __name__ == "__main__":
    # Run basic tests
    test_alignment_examples()
    print("✅ Timestamp alignment tests passed!")
    
    # Demonstrate the fix
    optimizer = CacheRequestOptimizer()
    
    # Simulate our problematic case
    raw_start = datetime(2025, 6, 6, 13, 58, 57, tzinfo=timezone.utc)
    raw_end = datetime(2025, 6, 6, 21, 29, 11, tzinfo=timezone.utc)
    
    aligned_start, aligned_end, metadata = optimizer.optimize_request_range(
        raw_start, raw_end, "30min"
    )
    
    print(f"\n🔧 TIMESTAMP ALIGNMENT DEMO:")
    print(f"   Original: {raw_start} → {raw_end}")
    print(f"   Aligned:  {aligned_start} → {aligned_end}")
    print(f"   Shifts: start {metadata['start_shift_seconds']}s, end {metadata['end_shift_seconds']}s")