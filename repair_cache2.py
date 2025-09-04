import os
import json
import argparse
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

def is_file_suspicious(file_path: Path) -> bool:
    """
    Checks if a cache file is "poisoned".

    A file is considered suspicious if:
    1. It's empty or contains an empty JSON list '[]'.
    2. It contains data points, but NONE of them have valid price/volume data
       (i.e., all points are tombstones or API failures).
    """
    try:
        # Check for empty file
        if file_path.stat().st_size < 5: # 5 bytes is generous for '[]'
            return True

        with open(file_path, 'r') as f:
            data = json.load(f)

        # Check for empty list
        if not isinstance(data, list) or not data:
            return True

        # Check if all points are placeholders
        has_real_data = False
        for point in data:
            if isinstance(point, dict) and not point.get('is_tombstone') and not point.get('is_api_failure'):
                has_real_data = True
                break # Found at least one good point, file is safe

        return not has_real_data

    except (json.JSONDecodeError, IOError) as e:
        logging.warning(f"Could not process file {file_path}, skipping. Error: {e}")
        return False


def run_cache_repair(base_dir: str = "price_cache/raw", execute: bool = False):
    """
    Scans and optionally cleans the raw price cache directory.
    """
    cache_path = Path(base_dir)
    if not cache_path.is_dir():
        logging.error(f"Cache directory not found at: {cache_path}")
        return

    if execute:
        logging.warning("--- RUNNING IN EXECUTE MODE: Files will be deleted. ---")
    else:
        logging.info("--- RUNNING IN DRY-RUN MODE: No files will be deleted. ---")

    suspicious_files = []
    total_files_scanned = 0

    for root, _, files in os.walk(cache_path):
        for filename in files:
            if filename.endswith('.json'):
                total_files_scanned += 1
                file_path = Path(root) / filename
                if is_file_suspicious(file_path):
                    suspicious_files.append(file_path)

    if not suspicious_files:
        logging.info(f"Scan complete. No suspicious files found out of {total_files_scanned} scanned.")
        return

    logging.info(f"\nFound {len(suspicious_files)} suspicious files to be deleted:")
    for file_path in suspicious_files:
        print(f"  - {file_path}")

    if execute:
        print("\nDeleting files...")
        deleted_count = 0
        for file_path in suspicious_files:
            try:
                os.remove(file_path)
                print(f"  [DELETED] {file_path}")
                deleted_count += 1
            except OSError as e:
                logging.error(f"Failed to delete {file_path}: {e}")
        logging.info(f"\nSuccessfully deleted {deleted_count} files.")
    else:
        logging.warning("\nTo delete these files, run the script again with the --execute flag.")
        logging.warning("Example: python tools/repair_cache.py --execute")

    logging.info(f"\nSummary:")
    logging.info(f"  - Total files scanned: {total_files_scanned}")
    logging.info(f"  - Suspicious files found: {len(suspicious_files)}")
    logging.info(f"  - Action: {'Files DELETED' if execute else 'Dry-run, no changes made'}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan and repair the raw price cache.")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete the suspicious files. Default is a dry-run."
    )
    args = parser.parse_args()

    run_cache_repair(execute=args.execute)