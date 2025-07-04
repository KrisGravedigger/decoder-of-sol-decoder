#!/usr/bin/env python3
"""
Fix Column Names Script - Plan A Implementation
Replaces old column names with new clean names across all Python files.
"""

import os
import re
from pathlib import Path

# Column name mappings
REPLACEMENTS = {
    'investment_sol': 'investment_sol',
    'pnl_sol': 'pnl_sol', 
    'strategy_raw': 'strategy_raw'
}

def process_file(file_path):
    """Process a single Python file and apply column name replacements."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        original_content = content
        changes_made = []
        
        # Apply all replacements
        for old_name, new_name in REPLACEMENTS.items():
            if old_name in content:
                content = content.replace(old_name, new_name)
                changes_made.append(f"{old_name} → {new_name}")
        
        # Write back only if changes were made
        if content != original_content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            print(f"✅ {file_path}: {', '.join(changes_made)}")
            return len(changes_made)
        
        return 0
        
    except Exception as e:
        print(f"❌ Error processing {file_path}: {e}")
        return 0

def main():
    """Main function to process all Python files."""
    print("🔧 Starting column name cleanup (Plan A)...")
    print("=" * 60)
    
    total_files = 0
    total_changes = 0
    
    # Find all Python files
    for py_file in Path('.').rglob('*.py'):
        if py_file.is_file():
            total_files += 1
            changes = process_file(py_file)
            total_changes += changes
    
    print("=" * 60)
    print(f"📊 Summary:")
    print(f"   Files processed: {total_files}")
    print(f"   Files modified: {total_changes}")
    print(f"   Column mappings applied:")
    for old_name, new_name in REPLACEMENTS.items():
        print(f"     • {old_name} → {new_name}")
    
    if total_changes > 0:
        print("\n✅ Column name cleanup completed successfully!")
        print("🔄 Next steps:")
        print("   1. Test the pipeline: python main.py")
        print("   2. Check CSV header: head -1 positions_to_analyze.csv")
        print("   3. Verify no old names remain: grep -r 'investment_sol' . --include='*.py'")
    else:
        print("\n💡 No changes were needed - files already use clean column names.")

if __name__ == "__main__":
    main()