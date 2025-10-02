# quick_pool_diagnostic.py
import os, re

pool = "BkocTzcvrhjwy38EYVyvhhVydeyqedasLVCJ8Z2HFyCN"
files = [f"input/app-0_20250907incomplete.log", f"input/app-0_20250921.log"]

for filepath in files:
    if not os.path.exists(filepath): continue
    print(f"\n=== {filepath} ===")
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    for i, line in enumerate(lines, 1):
        if pool in line:
            print(f"\nLine {i}: {line[:200]}")
            # Szukaj OPENED w okolicy
            opened_found = False
            for j in range(max(0, i-200), min(len(lines), i+50)):
                if "OPENED" in lines[j] and pool in lines[j]:
                    print(f"  -> OPENED found at line {j+1}")
                    opened_found = True
                    break
            if not opened_found:
                print(f"  -> NO OPENED event found within -200/+50 lines")