import os
import json
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def repair_file(file_path: Path, execute: bool) -> tuple[int, int]:
    """
    Removes all 'is_tombstone' entries from a JSON cache file.
    Returns (tombstones_found, tombstones_removed).
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        if not isinstance(data, list):
            return 0, 0

        tombstones_found = sum(1 for p in data if isinstance(p, dict) and p.get('is_tombstone'))
        
        if tombstones_found == 0:
            return 0, 0

        if execute:
            # Create a new list without the tombstones
            repaired_data = [p for p in data if not (isinstance(p, dict) and p.get('is_tombstone'))]
            with open(file_path, 'w') as f:
                json.dump(repaired_data, f, indent=2)
            
            # AIDEV-FIX: Also remove the corresponding stale 'offline_processed' cache file.
            try:
                relative_path = file_path.relative_to(Path("price_cache/raw"))
                processed_file = Path("price_cache/offline_processed") / relative_path
                if processed_file.exists():
                    processed_file.unlink()
                    logging.info(f"  -> Removed corresponding stale processed file: {processed_file}")
            except Exception as e:
                logging.warning(f"  -> Could not remove processed file for {file_path}: {e}")

            return tombstones_found, tombstones_found
        else:
            # In dry-run, we only report what we found
            return tombstones_found, 0

    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Could not process {file_path}. Error: {e}")
        return 0, 0

def run_cache_repair(base_dir: str = "price_cache/raw", execute: bool = False):
    """
    Scans and surgically removes all 'is_tombstone' entries from raw cache files.
    """
    cache_path = Path(base_dir)
    if not cache_path.is_dir():
        logging.error(f"Cache directory not found at: {cache_path}")
        return

    mode = "EXECUTE MODE" if execute else "DRY-RUN MODE"
    logging.info(f"--- RUNNING IN {mode}: Scanning for 'tombstones' to remove. ---")

    files_to_repair = []
    total_tombstones = 0
    total_files_scanned = 0

    for root, _, files in os.walk(cache_path):
        for filename in files:
            if filename.endswith('.json'):
                total_files_scanned += 1
                file_path = Path(root) / filename
                tombstones, _ = repair_file(file_path, execute=False) # Always dry-run first to count
                if tombstones > 0:
                    total_tombstones += tombstones
                    files_to_repair.append((file_path, tombstones))

    if not files_to_repair:
        logging.info(f"Scan complete. No tombstones found in {total_files_scanned} files.")
        return

    logging.info(f"\nFound {total_tombstones} total tombstones in {len(files_to_repair)} files:")
    for file_path, count in files_to_repair:
        print(f"  - {file_path} ({count} tombstones)")

    if execute:
        print("\nRepairing files...")
        removed_count = 0
        for file_path, _ in files_to_repair:
            _, removed = repair_file(file_path, execute=True)
            if removed > 0:
                print(f"  [REPAIRED] Removed {removed} tombstones from {file_path}")
                removed_count += removed
        logging.info(f"\nSuccessfully removed a total of {removed_count} tombstones.")
    else:
        logging.warning("\nTo permanently remove these tombstones, run the script again with the --execute flag.")
        logging.warning("Example: python tools/repair_cache.py --execute")

    logging.info(f"\nSummary:")
    logging.info(f"  - Total files scanned: {total_files_scanned}")
    logging.info(f"  - Files with tombstones: {len(files_to_repair)}")
    logging.info(f"  - Total tombstones found: {total_tombstones}")
    logging.info(f"  - Action: {'Tombstones REMOVED' if execute else 'Dry-run, no changes made'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Remove 'tombstones' from the raw price cache to force re-validation.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually remove the tombstone entries. Default is a dry-run."
    )
    args = parser.parse_args()
    run_cache_repair(execute=args.execute)