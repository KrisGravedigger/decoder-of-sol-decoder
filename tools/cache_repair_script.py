#!/usr/bin/env python3
"""
Cache Repair Script - Fix Zero Placeholders

Repairs existing cache files by applying proper forward-fill logic
to zero placeholders, converting them to use valid nearby prices.
"""

import json
import os
import glob
from typing import List, Dict
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def repair_cache_file(cache_path: str) -> bool:
    """
    Repair a single cache file by fixing zero placeholders.
    
    Args:
        cache_path (str): Path to cache file
        
    Returns:
        bool: True if file was modified, False if no changes needed
    """
    try:
        # Load existing data
        with open(cache_path, 'r') as f:
            data = json.load(f)
        
        if not isinstance(data, list) or len(data) == 0:
            logger.info(f"Skipping {os.path.basename(cache_path)} - empty or invalid")
            return False
        
        # Apply forward-fill repair
        repaired_data = []
        last_valid_price = None
        changes_made = 0
        
        # First pass - find any valid price to use as fallback
        valid_prices = [item.get('close', 0) for item in data if item.get('close', 0) > 0]
        fallback_price = valid_prices[0] if valid_prices else 0.000001
        
        # Second pass - repair zero placeholders
        for i, item in enumerate(data):
            current_price = item.get('close', 0)
            is_placeholder = item.get('is_placeholder', False)
            
            if current_price > 0:
                # Valid price - update last_valid_price and keep as-is
                last_valid_price = current_price
                repaired_data.append(item.copy())
            elif is_placeholder and current_price <= 0:
                # Zero placeholder - apply forward fill
                if last_valid_price and last_valid_price > 0:
                    repair_price = last_valid_price
                else:
                    # Look ahead for next valid price (backward fill)
                    future_price = None
                    for j in range(i + 1, len(data)):
                        if data[j].get('close', 0) > 0:
                            future_price = data[j]['close']
                            break
                    repair_price = future_price if future_price else fallback_price
                
                # Create repaired item
                repaired_item = item.copy()
                repaired_item['close'] = repair_price
                repaired_item['repaired_from_zero'] = True
                repaired_data.append(repaired_item)
                changes_made += 1
            else:
                # Non-placeholder with zero price - might be legitimate API data
                repaired_data.append(item.copy())
        
        if changes_made > 0:
            # Create backup
            backup_path = cache_path + '.backup'
            if not os.path.exists(backup_path):
                with open(backup_path, 'w') as f:
                    json.dump(data, f, indent=2)
            
            # Save repaired data
            with open(cache_path, 'w') as f:
                json.dump(repaired_data, f, indent=2)
            
            logger.info(f"✅ Repaired {os.path.basename(cache_path)}: {changes_made} zero placeholders fixed")
            return True
        else:
            logger.info(f"✅ {os.path.basename(cache_path)}: No repairs needed")
            return False
            
    except Exception as e:
        logger.error(f"❌ Failed to repair {cache_path}: {e}")
        return False

def repair_all_cache_files(cache_dir: str = "price_cache") -> Dict[str, int]:
    """
    Repair all cache files in the cache directory.
    
    Args:
        cache_dir (str): Cache directory path
        
    Returns:
        Dict[str, int]: Statistics about repairs made
    """
    if not os.path.exists(cache_dir):
        logger.error(f"Cache directory not found: {cache_dir}")
        return {'error': 1}
    
    # Find all JSON cache files
    cache_pattern = os.path.join(cache_dir, "*.json")
    cache_files = glob.glob(cache_pattern)
    
    if not cache_files:
        logger.warning(f"No cache files found in {cache_dir}")
        return {'files_found': 0}
    
    logger.info(f"Found {len(cache_files)} cache files to check")
    
    stats = {
        'files_checked': 0,
        'files_repaired': 0,
        'files_no_changes': 0,
        'files_errors': 0
    }
    
    for cache_file in sorted(cache_files):
        # Skip backup files
        if cache_file.endswith('.backup'):
            continue
            
        stats['files_checked'] += 1
        
        try:
            was_repaired = repair_cache_file(cache_file)
            if was_repaired:
                stats['files_repaired'] += 1
            else:
                stats['files_no_changes'] += 1
        except Exception as e:
            logger.error(f"Error processing {cache_file}: {e}")
            stats['files_errors'] += 1
    
    return stats

def main():
    """Main repair function with summary."""
    print("🔧 Cache Repair Script - Fixing Zero Placeholders")
    print("=" * 50)
    
    # Run repair process
    stats = repair_all_cache_files()
    
    # Print summary
    print("\n📊 REPAIR SUMMARY:")
    print(f"   Files checked: {stats.get('files_checked', 0)}")
    print(f"   Files repaired: {stats.get('files_repaired', 0)}")
    print(f"   Files unchanged: {stats.get('files_no_changes', 0)}")
    print(f"   Files with errors: {stats.get('files_errors', 0)}")
    
    if stats.get('files_repaired', 0) > 0:
        print(f"\n✅ SUCCESS: {stats['files_repaired']} cache files were repaired!")
        print("   Backup files (.backup) were created automatically")
        print("   You can now re-run your analysis with fixed data")
    else:
        print("\n✅ All cache files were already in good condition")
    
    if stats.get('files_errors', 0) > 0:
        print(f"\n⚠️  {stats['files_errors']} files had errors - check logs above")

if __name__ == "__main__":
    main()