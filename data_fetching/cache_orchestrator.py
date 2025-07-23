import logging
from typing import Literal
from datetime import datetime, timedelta

from utils.common import print_header
from data_fetching.enhanced_price_cache_manager import EnhancedPriceCacheManager
from reporting.data_loader import load_and_prepare_positions

logger = logging.getLogger(__name__)


def fetch_enhanced_cache_data(mode: Literal['fill_gaps', 'force_refetch']):
    """Fetch OCHLV+Volume data for positions using EnhancedPriceCacheManager."""
    mode_description = {
        'fill_gaps': "Fill Gaps Only",
        'force_refetch': "Force Refetch All"
    }
    print_header(f"Fetch OCHLV+Volume Data ({mode_description[mode]})")
    
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        total_positions = len(positions_df)
        
        if total_positions == 0:
            print("[WARNING] No positions found in positions_to_analyze.csv")
            return
            
        print(f"Found {total_positions} positions to process...")
        
        user_input = input(f"\n[SAFETY VALVE] This will connect to the API in '{mode_description[mode]}' mode. This may use API credits. Continue? (Y/n): ")
        if user_input.lower().strip() not in ('y', ''):
            print("Enhanced cache fetching cancelled by user.")
            return
            
        enhanced_cache = EnhancedPriceCacheManager()
        
        print(f"\nProcessing OCHLV+Volume data:")
        print("-" * 80)
        
        successful_fetches = 0
        skipped_complete = 0
        skipped_old = 0
        failed_fetches = 0
        
        for idx, row in positions_df.iterrows():
            progress_idx = positions_df.index.get_loc(idx) + 1
            position_id = row.get('position_id', f"pos_{progress_idx}")
            token_pair = row.get('token_pair', 'Unknown')
            
            print(f"[{progress_idx}/{total_positions}] Processing {position_id} ({token_pair})...", end=' ')

            class SimplePosition:
                def __init__(self, row):
                    self.pool_address = row.get('pool_address')
                    self.open_timestamp = row.get('open_timestamp')
                    self.close_timestamp = row.get('close_timestamp')
            
            position_obj = SimplePosition(row)

            if mode == 'fill_gaps':
                validation_result = enhanced_cache.validate_cache_completeness(position_obj)
                is_complete = validation_result['is_complete']
                
                if is_complete:
                    print("✓ Skipping (already complete)")
                    skipped_complete += 1
                    continue

                # PRAGMATIC CACHE RULE: Don't try to fix old, incomplete positions
                # This rule should ONLY apply if we have already tried to fetch data before (i.e., cache exists but is partial)
                has_any_data = validation_result['has_price_data'] # We use this as a proxy for "cache exists"
                position_close_date = row.get('close_timestamp')
                
                if has_any_data and position_close_date < datetime.now() - timedelta(days=2):
                    print("✓ Skipping (old, known-incomplete)")
                    skipped_old +=1
                    continue

            try:
                # Fetch OCHLV data for this position
                ochlv_data = enhanced_cache.fetch_ochlv_data(
                    pool_address=row.get('pool_address'),
                    start_dt=row.get('open_timestamp'),
                    end_dt=row.get('close_timestamp'),
                    use_cache_only=False,
                    force_refetch=(mode == 'force_refetch')
                )
                
                if ochlv_data:
                    is_complete_after = enhanced_cache.validate_cache_completeness(position_obj)['is_complete']
                    status_icon = "✓" if is_complete_after else "⚠️"
                    status_text = "Complete" if is_complete_after else "Partial"
                    
                    volume_points = sum(1 for p in ochlv_data if p.get('volume', 0) > 0)
                    print(f"{status_icon} Fetched {len(ochlv_data)} pts ({volume_points} vol) -> {status_text}")
                    successful_fetches += 1
                else:
                    print("✗ No data returned")
                    failed_fetches += 1
                    
            except Exception as e:
                print(f"✗ Error: {e}")
                failed_fetches += 1
                logger.error(f"Failed to fetch data for {position_id}: {e}")
                
        print("-" * 80)
        print(f"\nEnhanced Cache Fetching Summary:")
        print(f"  Total positions:    {total_positions}")
        print(f"  Skipped (complete): {skipped_complete}")
        print(f"  Skipped (old):      {skipped_old}")
        print(f"  Fetched/Updated:    {successful_fetches}")
        print(f"  Failed:             {failed_fetches}")
        
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
    except Exception as e:
        logger.error(f"Enhanced cache fetching failed: {e}", exc_info=True)
        print(f"\n[ERROR] Enhanced cache fetching failed: {e}")


def enhanced_cache_fetching_menu():
    """Displays the sub-menu for fetching OCHLV+Volume data."""
    while True:
        print("\n" + "-"*70)
        print("--- OCHLV+Volume Cache Fetching Options ---")
        print("This step populates the enhanced cache for the TP/SL Optimizer.")
        print("-"*70)
        print("1. Fill Gaps Only (Recommended - skips complete & very old positions)")
        print("2. Force Refetch All Data (Re-downloads all data, uses more API credits)")
        print("3. Back")

        choice = input("Select an option (1-3): ")

        if choice == '1':
            fetch_enhanced_cache_data(mode='fill_gaps')
            break
        elif choice == '2':
            fetch_enhanced_cache_data(mode='force_refetch')
            break
        elif choice == '3':
            break
        else:
            print("Invalid choice, please try again.")


def validate_cache_completeness_for_positions():
    """Validate cache completeness for all positions in the analysis file."""
    print_header("Cache Validation for Positions")
    
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        total_positions = len(positions_df)
        
        if total_positions == 0:
            print("[WARNING] No positions found in positions_to_analyze.csv")
            return
            
        print(f"Validating cache for {total_positions} positions...")
        
        enhanced_cache = EnhancedPriceCacheManager()
        
        validation_results = {'complete': 0, 'has_price_only': 0, 'missing_data': 0, 'total': total_positions}
        
        print("\nValidation Progress:")
        print("-" * 80)
        print(f"{'Position':<15} {'Pool Address':<20} {'Price Data':<12} {'Volume Data':<12} {'Status':<10}")
        print("-" * 80)
        
        for idx, row in positions_df.iterrows():
            position_id = row.get('position_id', f"pos_{idx}")
            pool_address = row.get('pool_address', 'Unknown')[:18] + "..."
            
            class SimplePosition:
                def __init__(self, row):
                    self.pool_address = row.get('pool_address')
                    self.open_timestamp = row.get('open_timestamp')
                    self.close_timestamp = row.get('close_timestamp')
            
            validation_result = enhanced_cache.validate_cache_completeness(SimplePosition(row))
            
            has_price = "✓" if validation_result['has_price_data'] else "✗"
            has_volume = "✓" if validation_result['has_volume_data'] else "✗"
            
            if validation_result['is_complete']:
                status = "Complete"
                validation_results['complete'] += 1
            elif validation_result['has_price_data']:
                status = "Price Only"
                validation_results['has_price_only'] += 1
            else:
                status = "Missing"
                validation_results['missing_data'] += 1
                
            print(f"{position_id:<15} {pool_address:<20} {has_price:<12} {has_volume:<12} {status:<10}")
            
        print("-" * 80)
        print(f"\nValidation Summary:")
        print(f"  Complete (Price + Volume): {validation_results['complete']}/{total_positions} ({validation_results['complete']/total_positions*100:.1f}%)")
        print(f"  Price Data Only:           {validation_results['has_price_only']}/{total_positions} ({validation_results['has_price_only']/total_positions*100:.1f}%)")
        print(f"  Missing Data:              {validation_results['missing_data']}/{total_positions} ({validation_results['missing_data']/total_positions*100:.1f}%)")
            
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
    except Exception as e:
        logger.error(f"Cache validation failed: {e}", exc_info=True)
        print(f"\n[ERROR] Cache validation failed: {e}")

def check_volume_data_availability():
    """Check volume data availability for a sample of positions."""
    print_header("Volume Data Availability Check")
    
    try:
        positions_df = load_and_prepare_positions("positions_to_analyze.csv", min_threshold=0.0)
        if positions_df.empty:
            print("[WARNING] No positions found in positions_to_analyze.csv")
            return
            
        sample_size = min(10, len(positions_df))
        sample_positions = positions_df.head(sample_size)
        
        print(f"Checking volume data for {sample_size} sample positions...")
        
        enhanced_cache = EnhancedPriceCacheManager()
        
        print("\nVolume Data Analysis:")
        print("-" * 100)
        print(f"{'Position':<15} {'Token Pair':<20} {'Duration':<12} {'Volume Points':<14} {'Avg Volume':<12} {'Status':<10}")
        print("-" * 100)
        
        total_volume_points = 0
        positions_with_volume = 0
        
        for idx, row in sample_positions.iterrows():
            position_id = row.get('position_id', f"pos_{idx}")
            token_pair = row.get('token_pair', 'Unknown')[:18]
            
            class SimplePosition:
                def __init__(self, row):
                    self.pool_address = row.get('pool_address')
                    self.open_timestamp = row.get('open_timestamp')
                    self.close_timestamp = row.get('close_timestamp')

            simple_pos = SimplePosition(row)
            volume_data = enhanced_cache.get_volume_for_position(simple_pos)
            
            duration = simple_pos.close_timestamp - simple_pos.open_timestamp
            duration_str = f"{duration.total_seconds()/3600:.1f}h"
                
            volume_points = len(volume_data)
            avg_volume = sum(volume_data) / len(volume_data) if volume_data else 0
            
            if volume_points > 0:
                positions_with_volume += 1
                total_volume_points += volume_points
                status = "✓ Available"
            else:
                status = "✗ Missing"
                
            print(f"{position_id:<15} {token_pair:<20} {duration_str:<12} {volume_points:<14} {avg_volume:<12.1f} {status:<10}")
            
        print("-" * 100)
        print(f"\nVolume Data Summary:")
        print(f"  Positions with volume data: {positions_with_volume}/{sample_size}")
        
    except FileNotFoundError:
        print("\n[ERROR] positions_to_analyze.csv not found. Please run Step 1/2 first.")
    except Exception as e:
        logger.error(f"Volume data check failed: {e}", exc_info=True)
        print(f"\n[ERROR] Volume data check failed: {e}")