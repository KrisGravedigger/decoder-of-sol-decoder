import logging
import os
import json
import random
from datetime import datetime

from utils.common import print_header
from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
from reporting.data_loader import load_and_prepare_positions

logger = logging.getLogger(__name__)


def test_enhanced_cache_manager():
    """Test the enhanced cache manager with a sample position."""
    print_header("Enhanced Cache Manager Test")
    
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        
        if positions_df.empty:
            print("[WARNING] No positions found in positions_to_analyze.csv")
            return
            
        test_index = random.randint(0, len(positions_df) - 1)
        test_position = positions_df.iloc[test_index]
        
        print(f"Testing with randomly selected position #{test_index + 1}/{len(positions_df)}")
        print(f"Position: {test_position.get('position_id', 'Unknown')}, Pair: {test_position.get('token_pair', 'Unknown')}")
        
        enhanced_cache = EnhancedPriceCacheManager()
        
        print("\n1. Testing cache-only OCHLV data fetch...")
        try:
            ochlv_data = enhanced_cache.fetch_ochlv_data(
                pool_address=test_position.get('pool_address'),
                start_dt=test_position.get('open_timestamp'),
                end_dt=test_position.get('close_timestamp'),
                use_cache_only=True
            )
            print(f"   ✓ Retrieved {len(ochlv_data)} OCHLV data points")
        except Exception as e:
            print(f"   ✗ Cache-only test failed: {e}")
            
        print("\n2. Testing volume data extraction...")
        try:
            class SimplePosition:
                def __init__(self, row):
                    self.pool_address = row.get('pool_address')
                    self.open_timestamp = row.get('open_timestamp')
                    self.close_timestamp = row.get('close_timestamp')
            
            simple_pos = SimplePosition(test_position)
            volume_data = enhanced_cache.get_volume_for_position(simple_pos)
            print(f"   ✓ Extracted {len(volume_data)} volume data points")
            
        except Exception as e:
            print(f"   ✗ Volume extraction test failed: {e}")
            
        print("\n3. Testing cache validation...")
        try:
            validation_result = enhanced_cache.validate_cache_completeness(simple_pos)
            print(f"   Cache validation result:")
            print(f"     Has price data:  {validation_result['has_price_data']}")
            print(f"     Has volume data: {validation_result['has_volume_data']}")
            print(f"     Is complete:     {validation_result['is_complete']}")
        except Exception as e:
            print(f"   ✗ Cache validation test failed: {e}")
            
        print("\n✓ Enhanced cache manager test completed.")
        
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found.")
    except Exception as e:
        logger.error(f"Enhanced cache manager test failed: {e}", exc_info=True)
        print(f"\n[ERROR] Test failed: {e}")

def debug_cache_locations():
    """Debug function to check cache file locations and contents."""
    print_header("Debug Cache Locations")
    
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        if positions_df.empty:
            print("[WARNING] No positions found")
            return
            
        test_position = positions_df.iloc[0]
        print(f"Debugging cache for: {test_position.get('position_id')}")
        
        enhanced_cache = EnhancedPriceCacheManager()
        
        raw_cache_dir = enhanced_cache.raw_cache_dir
        print(f"\nRaw cache directory: {raw_cache_dir}")
        if os.path.exists(raw_cache_dir):
            print("  Subdirectories:", ", ".join(d for d in os.listdir(raw_cache_dir) if os.path.isdir(os.path.join(raw_cache_dir, d))))
        else:
            print("  Raw cache directory does not exist")
            
        old_cache_dir = enhanced_cache.cache_dir
        print(f"\nOld price cache directory: {old_cache_dir}")
        if os.path.exists(old_cache_dir):
            files = [f for f in os.listdir(old_cache_dir) if f.endswith('.json')]
            print(f"  Contains {len(files)} JSON files")
        else:
            print("  Old cache directory does not exist")

        pool_address = test_position.get('pool_address')
        open_timestamp = test_position.get('open_timestamp') 
        close_timestamp = test_position.get('close_timestamp')
        
        print(f"\nTesting cache loading for specific position:")
        print(f"  Pool: {pool_address}")
        print(f"  Period: {open_timestamp} - {close_timestamp}")
        
        timeframe = enhanced_cache._determine_timeframe_from_duration(open_timestamp, close_timestamp)
        print(f"  Determined timeframe: {timeframe}")
        
        cached_data = enhanced_cache._load_raw_cache_for_period(
            pool_address, open_timestamp, close_timestamp, timeframe
        )
        print(f"  Raw cache returned: {len(cached_data)} points")
        
        if cached_data:
            first_ts = enhanced_cache._parse_timestamp_to_unix(cached_data[0]['timestamp'])
            last_ts = enhanced_cache._parse_timestamp_to_unix(cached_data[-1]['timestamp'])
            print(f"  Cached period: {datetime.fromtimestamp(first_ts)} to {datetime.fromtimestamp(last_ts)}")

    except Exception as e:
        print(f"Debug failed: {e}")

def cache_debugger_menu():
    """Displays the menu for cache debugging tools."""
    while True:
        print("\n" + "-"*70)
        print("--- Cache Debugging Tools ---")
        print("-"*70)
        print("1. Test Enhanced Cache Manager (random position)")
        print("2. Debug Cache Locations and Structure")
        print("3. Back")

        choice = input("Select an option (1-3): ")

        if choice == '1':
            test_enhanced_cache_manager()
        elif choice == '2':
            debug_cache_locations()
        elif choice == '3':
            break
        else:
            print("Invalid choice, please try again.")