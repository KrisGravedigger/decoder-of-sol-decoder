# check_specific_lines.py
import os

targets = [
    ("input/app-0_20250907incomplete.log", 14063459),
    ("input/app-0_20250921.log", 15838316)
]

context_size = 30  # 30 linii przed i po (razem 61 linii)

for filepath, line_number in targets:
    print("=" * 100)
    print(f"FILE: {filepath}")
    print(f"TARGET LINE: {line_number}")
    print("=" * 100)
    
    if not os.path.exists(filepath):
        print(f"ERROR: File not found: {filepath}\n")
        continue
    
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        # Convert to 0-based index
        target_idx = line_number - 1
        
        start_idx = max(0, target_idx - context_size)
        end_idx = min(len(lines), target_idx + context_size + 1)
        
        print(f"\nShowing lines {start_idx + 1} to {end_idx}")
        print(f"Total lines in file: {len(lines)}\n")
        
        for i in range(start_idx, end_idx):
            marker = ">>> " if i == target_idx else "    "
            # Clean line for display
            line_content = lines[i].rstrip()
            # Limit length for readability
            if len(line_content) > 200:
                line_content = line_content[:200] + "..."
            print(f"{marker}{i+1:>9}: {line_content}")
        
        print("\n")
        
    except Exception as e:
        print(f"ERROR reading file: {e}\n")

print("=" * 100)
print("ANALYSIS COMPLETE")
print("=" * 100)