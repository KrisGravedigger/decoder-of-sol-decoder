import os
import re
import csv
from pathlib import Path

# AIDEV-NOTE-CLAUDE: This is a highly specialized diagnostic script. Its sole purpose is
# to find the "All Bundle transaction failed" log entries and trace them back to the specific
# position that was being closed. It generates a CSV report for comparison against the main
# positions.csv, as requested by the user for final verification.

LOG_DIR = "input"
OUTPUT_CSV = "failed_bundle_positions_report.csv"
BUNDLE_FAILURE_PATTERN = re.compile(r'All Bundle transaction failed', re.IGNORECASE)

# This pattern helps us find the start of the position that was being closed.
OPENED_PATTERN = re.compile(
    r'v(?P<version>[\d.]+)-(?P<timestamp>\d{2}/\d{2}-\d{2}:\d{2}:\d{2}).*OPENED\s*(?P<token_pair>[\w\s().-]+-SOL)'
)

def clean_ansi(text: str) -> str:
    """Remove ANSI escape sequences from text."""
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', text)

def find_preceding_open_event(lines: list, failure_index: int, lookback: int = 500) -> dict | None:
    """
    Searches backwards from a failure point to find the most recent position opening event.

    Args:
        lines (list): All lines from the log file.
        failure_index (int): The line number where the failure was detected.
        lookback (int): How many lines to search backwards.

    Returns:
        A dictionary with parsed position data or None if not found.
    """
    start_index = max(0, failure_index - lookback)
    for i in range(failure_index, start_index, -1):
        line = clean_ansi(lines[i])
        match = OPENED_PATTERN.search(line)
        if match:
            # We found the most recent 'OPENED' event before the failure.
            # This is very likely the position that failed to close.
            data = match.groupdict()
            
            # Try to get pool_address for a more robust ID
            pool_address = None
            for j in range(i, max(0, i - 60), -1):
                context_line = clean_ansi(lines[j])
                pool_match = re.search(r'app\.meteora\.ag/dlmm/([a-zA-Z0-9]+)', context_line)
                if pool_match:
                    pool_address = pool_match.group(1)
                    break
            data['pool_address'] = pool_address
            
            # Construct a universal position ID for easier matching
            if pool_address and data.get('timestamp'):
                data['position_id'] = f"{pool_address}_{data['timestamp']}"
            else:
                data['position_id'] = "ID_NOT_FOUND"

            return data
    return None

def investigate_failures(log_dir: str, output_csv: str):
    """
    Main function to run the investigation and generate the CSV report.
    """
    print("=" * 80)
    print("Starting Bundle Failure Investigation Script")
    print(f"Target pattern: '{BUNDLE_FAILURE_PATTERN.pattern}'")
    print(f"Outputting results to: '{output_csv}'")
    print("=" * 80)

    log_files = sorted(list(Path(log_dir).rglob('app*.log')))
    if not log_files:
        print(f"No log files found in '{log_dir}'.")
        return

    print(f"Found {len(log_files)} log files to scan...\n")

    failed_positions = []
    
    for file_path in log_files:
        print(f"Scanning {file_path}...")
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for i, line in enumerate(lines):
                if BUNDLE_FAILURE_PATTERN.search(clean_ansi(line)):
                    # Found a failure, now find the position it belongs to.
                    position_data = find_preceding_open_event(lines, i)
                    
                    if position_data:
                        report_entry = {
                            'position_id': position_data['position_id'],
                            'open_timestamp': position_data['timestamp'],
                            'token_pair': position_data['token_pair'].strip(),
                            'pool_address': position_data['pool_address'],
                            'failure_reason': 'All Bundle transaction failed',
                            'failure_line_number': i + 1,
                            'source_log_file': str(file_path)
                        }
                        failed_positions.append(report_entry)

        except Exception as e:
            print(f"  ERROR processing file {file_path}: {e}")
            
    # Write report to CSV
    if not failed_positions:
        print("\n✅ Investigation complete. No instances of 'All Bundle transaction failed' were found.")
        return
        
    print(f"\n🚨 Investigation complete. Found {len(failed_positions)} instances linked to positions.")
    
    try:
        with open(output_csv, 'w', newline='', encoding='utf-8') as f:
            fieldnames = failed_positions[0].keys()
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(failed_positions)
        print(f"Successfully generated report: '{output_csv}'")
    except Exception as e:
        print(f"  ERROR writing CSV report: {e}")

    print("=" * 80)


if __name__ == "__main__":
    if not os.path.isdir(LOG_DIR):
        print(f"Error: The log directory '{LOG_DIR}' does not exist.")
    else:
        investigate_failures(LOG_DIR, OUTPUT_CSV)