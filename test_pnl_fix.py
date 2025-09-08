#!/usr/bin/env python3
"""
Test script to verify the improved PnL parsing logic with priority-based regex patterns
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from extraction.parsing_utils import parse_final_pnl_with_line_info, clean_ansi

def test_improved_pnl_parsing():
    """Test the improved PnL parsing with different scenarios"""
    
    print("🧪 Testing improved PnL parsing logic with priority-based regex patterns\n")
    
    # Test Case 1: Final PnL vs intermediate PnL (the original problem)
    print("=== Test Case 1: Final vs Intermediate PnL ===")
    test_lines_1 = [
        "INFO: Position opened successfully",  # line 0 (open_line_index)
        "INFO: Current position update...", 
        "INFO: Current position PnL: 1.48 SOL (Return: +45.2%)",  # Intermediate update (should be ignored)
        "INFO: Position status update...",
        "INFO: Market conditions changing...",
        "INFO: Final PnL: -0.04 SOL (Return: -1.2%)",  # Final PnL (should be matched)
        "INFO: Transaction confirmed - position closed"  # line 6 (close_line_index)
    ]
    
    result1 = parse_final_pnl_with_line_info(
        lines=test_lines_1,
        start_index=6,  # Close line
        lookback=10,
        debug_enabled=False,
        debug_file_path=None,
        open_line_index=0  # Open line
    )
    
    print(f"Result: PnL = {result1['pnl']} SOL, Pattern = {result1.get('pattern_used')}")
    expected = -0.04
    if result1['pnl'] is not None and abs(result1['pnl'] - expected) < 0.001:
        print("✅ PASS: Correctly identified final PnL over intermediate update\n")
    else:
        print(f"❌ FAIL: Expected {expected}, got {result1['pnl']}\n")
    
    # Test Case 2: Transaction confirmed context
    print("=== Test Case 2: Transaction Confirmed Context ===")
    test_lines_2 = [
        "INFO: Position opened",
        "INFO: Trading activity...",
        "INFO: Basic PnL: 0.5 SOL",  # Lower priority pattern
        "INFO: Transaction confirmed PnL: 0.85 SOL (Return: +8.2%)",  # Higher priority
        "INFO: Position closed"
    ]
    
    result2 = parse_final_pnl_with_line_info(
        lines=test_lines_2,
        start_index=4,
        lookback=10,
        debug_enabled=False,
        debug_file_path=None,
        open_line_index=0
    )
    
    print(f"Result: PnL = {result2['pnl']} SOL, Pattern = {result2.get('pattern_used')}")
    expected = 0.85
    if result2['pnl'] is not None and abs(result2['pnl'] - expected) < 0.001:
        print("✅ PASS: Correctly prioritized transaction confirmed PnL\n")
    else:
        print(f"❌ FAIL: Expected {expected}, got {result2['pnl']}\n")
    
    # Test Case 3: Closing context priority
    print("=== Test Case 3: Closing Context Priority ===")
    test_lines_3 = [
        "INFO: Position active",
        "INFO: PnL: 2.1 SOL (Return: +15%)",  # Standard pattern
        "INFO: Market update",
        "INFO: Closing PnL: 1.95 SOL (Return: +14.2%)",  # Higher priority closing context
        "INFO: Position closed"
    ]
    
    result3 = parse_final_pnl_with_line_info(
        lines=test_lines_3,
        start_index=4,
        lookback=10,
        debug_enabled=False,
        debug_file_path=None,
        open_line_index=0
    )
    
    print(f"Result: PnL = {result3['pnl']} SOL, Pattern = {result3.get('pattern_used')}")
    expected = 1.95
    if result3['pnl'] is not None and abs(result3['pnl'] - expected) < 0.001:
        print("✅ PASS: Correctly prioritized closing context PnL\n")
    else:
        print(f"❌ FAIL: Expected {expected}, got {result3['pnl']}\n")
    
    # Test Case 4: Position boundary constraint
    print("=== Test Case 4: Position Boundary Constraint ===")
    test_lines_4 = [
        "INFO: Previous position PnL: 5.0 SOL",  # Before current position (should be ignored)
        "INFO: Current position opened",  # line 1 (open_line_index)
        "INFO: Current activity...",
        "INFO: Current PnL: 0.3 SOL (Return: +2.1%)",  # Current position PnL
        "INFO: Position closed"  # line 4 (close_line_index)
    ]
    
    result4 = parse_final_pnl_with_line_info(
        lines=test_lines_4,
        start_index=4,
        lookback=10,
        debug_enabled=False,
        debug_file_path=None,
        open_line_index=1  # Constraint: don't search before line 1
    )
    
    print(f"Result: PnL = {result4['pnl']} SOL, Pattern = {result4.get('pattern_used')}")
    expected = 0.3
    if result4['pnl'] is not None and abs(result4['pnl'] - expected) < 0.001:
        print("✅ PASS: Correctly respected position boundary constraint\n")
    else:
        print(f"❌ FAIL: Expected {expected}, got {result4['pnl']}\n")
    
    print("🎉 Test suite completed! The improved PnL parsing logic:")
    print("   • Uses priority-based regex patterns")
    print("   • Prefers final/closing context over intermediate updates")
    print("   • Respects position boundaries to prevent cross-contamination")
    print("   • Provides pattern information for debugging")

if __name__ == "__main__":
    test_improved_pnl_parsing()