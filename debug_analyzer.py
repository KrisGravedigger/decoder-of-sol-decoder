import re
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

import re
import logging
from typing import Dict, List, Optional, Any
from collections import defaultdict, Counter

# === CONTEXT EXPORT CONFIGURATION ===
# AIDEV-NOTE-CLAUDE: Detailed export settings - main switches come from log_extractor.py
CONTEXT_CONFIG = {
    # Context extraction settings  
    "context_lines_before": 70,
    "context_lines_after": 10,
    "export_all_contexts": True,  # False = only export filtered contexts
    
    # Close reason filtering (True = include in context export)
    "include_close_reasons": {
        "TP": False,          # Take Profit - DISABLED, already identified
        "SL": False,          # Stop Loss - DISABLED, already identified
        "LV": False,          # Low Volume - DISABLED, already identified
        "OOR": False,         # Out of Range - DISABLED, already identified
        "other": True         # All other cases (manual, unknown, etc.)
    },
    
    # Analysis helpers
    "group_unknown_contexts": True,  # Group similar unknown patterns
    "max_contexts_per_type": 5      # Limit contexts per close type
}

# Get logger
logger = logging.getLogger('DebugAnalyzer')

# === Context Analysis Helper ===

class CloseContextAnalyzer:
    """Analyzes close contexts and groups similar patterns."""
    
    def __init__(self, debug_enabled: bool = True, context_export_enabled: bool = True):
        """
        Initialize the context analyzer.
        
        Args:
            debug_enabled: Whether debug features are enabled (from main config)
            context_export_enabled: Whether context export is enabled (from main config)
        """
        self.debug_enabled = debug_enabled
        self.context_export_enabled = context_export_enabled
        self.close_contexts: List[Dict[str, Any]] = []
        self.pattern_groups: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    
    def guess_close_reason(self, context_lines: List[str]) -> str:
        """
        Klasyfikuj powód zamknięcia na podstawie precyzyjnych wzorców z analizy logów.
        
        Args:
            context_lines: Lines of context around the close event
            
        Returns:
            Guessed close reason: TP, SL, LV, OOR, or other
        """
        context_text = " ".join(context_lines)
        
        # AIDEV-NOTE-CLAUDE: Simplified patterns based on analysis (2025-06-20)
        
        # SL (Stop Loss) - highest priority as it's most specific
        if "Stop loss triggered:" in context_text:
            return "SL"
        
        # TP (Take Profit) - clear indicators
        if "Take profit triggered:" in context_text or "TAKEPROFIT!" in context_text:
            return "TP"
        
        # LV (Low Volume) - simplified pattern
        if "due to low volume" in context_text:
            return "LV"
        
        # OOR (Out of Range) - check after more specific ones
        if ("Closing position due to price range:" in context_text and 
            "Position was out of range for" in context_text):
            return "OOR"
        
        # Everything else goes to "other"
        return "other"
    
    def add_context(self, position, context_lines: List[str], close_line_index: int):
        """
        Add a close context for analysis.
        
        Args:
            position: Position that was closed
            context_lines: Lines of context around the close
            close_line_index: Line index where close was detected
        """
        guessed_reason = self.guess_close_reason(context_lines)
        
        context_data = {
            "position": position,
            "context_lines": context_lines,
            "close_line_index": close_line_index,
            "guessed_reason": guessed_reason,
            "context_hash": self._calculate_context_hash(context_lines)
        }
        
        self.close_contexts.append(context_data)
        self.pattern_groups[guessed_reason].append(context_data)
    
    def _calculate_context_hash(self, context_lines: List[str]) -> str:
        """
        Calculate a simple hash for grouping similar contexts.
        
        Args:
            context_lines: Lines of context
            
        Returns:
            Simple hash based on key phrases
        """
        # Extract key phrases for similarity matching
        text = " ".join(context_lines).lower()
        key_phrases = []
        
        # Common patterns that might indicate similar close reasons
        patterns = [
            r"pnl:\s*[-+]?\d+\.?\d*",
            r"return:\s*[-+]?\d+\.?\d*%",
            r"(take profit|stop loss|volume|range|manual)",
            r"(closed|withdrew|triggered|reached)"
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            key_phrases.extend(matches)
        
        return "|".join(sorted(set(key_phrases)))
    
    def should_export_context(self, guessed_reason: str, reason_counts: Dict[str, int]) -> bool:
        """
        Determine if context should be exported based on configuration.
        
        Args:
            guessed_reason: Guessed close reason
            reason_counts: Current counts of exported reasons
            
        Returns:
            True if context should be exported
        """
        if not CONTEXT_CONFIG["include_close_reasons"].get(guessed_reason, False):
            return False
        
        if reason_counts.get(guessed_reason, 0) >= CONTEXT_CONFIG["max_contexts_per_type"]:
            return False
        
        return True
    
    def export_contexts(self, output_file: str) -> Dict[str, int]:
        """
        Export contexts to analysis file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            Dictionary with export statistics
        """
        if not self.context_export_enabled:
            logger.info("Context export disabled in main configuration.")
            return {}
        
        if not self.close_contexts:
            logger.warning("No close contexts to export.")
            return {}
        
        reason_counts = Counter()
        exported_counts = Counter()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("CLOSE CONTEXTS ANALYSIS\n")
                f.write(f"Generated from {len(self.close_contexts)} position closures\n")
                f.write("=" * 80 + "\n\n")
                
                # Group and export by reason
                for reason, contexts in self.pattern_groups.items():
                    reason_counts[reason] = len(contexts)
                    
                    if not CONTEXT_CONFIG["include_close_reasons"].get(reason, False):
                        continue
                    
                    f.write(f"\n{'=' * 20} {reason.upper()} CONTEXTS {'=' * 20}\n")
                    f.write(f"Total found: {len(contexts)}\n")
                    
                    exported_for_reason = 0
                    for i, context_data in enumerate(contexts):
                        if exported_for_reason >= CONTEXT_CONFIG["max_contexts_per_type"]:
                            f.write(f"\n[... {len(contexts) - exported_for_reason} more {reason} contexts truncated]\n")
                            break
                        
                        pos = context_data["position"]
                        f.write(f"\n#{exported_for_reason + 1} Position {pos.token_pair} closed {pos.close_timestamp}\n")
                        f.write(f"Line index: {context_data['close_line_index']} | ")
                        f.write(f"PnL: {pos.final_pnl} SOL | ")
                        f.write(f"Strategy: {pos.actual_strategy}\n")
                        f.write("=" * 60 + " CONTEXT START " + "=" * 60 + "\n")
                        
                        for line in context_data["context_lines"]:
                            f.write(line)
                            if not line.endswith('\n'):
                                f.write('\n')
                        
                        f.write("=" * 60 + " CONTEXT END " + "=" * 62 + "\n")
                        exported_for_reason += 1
                    
                    exported_counts[reason] = exported_for_reason
                
                # Summary
                f.write(f"\n{'=' * 20} EXPORT SUMMARY {'=' * 20}\n")
                for reason in ["TP", "SL", "LV", "OOR", "other"]:
                    total = reason_counts.get(reason, 0)
                    exported = exported_counts.get(reason, 0)
                    status = "✓" if CONTEXT_CONFIG["include_close_reasons"].get(reason, False) else "✗"
                    f.write(f"{status} {reason:8} | Total: {total:3} | Exported: {exported:3}\n")
                
            logger.info(f"Context export completed. File: {output_file}")
            logger.info(f"Total contexts: {sum(reason_counts.values())}, Exported: {sum(exported_counts.values())}")
            
            return dict(exported_counts)
            
        except Exception as e:
            logger.error(f"Error exporting contexts to {output_file}: {e}")
            return {}

# === Main Debug Analyzer Class ===

class DebugAnalyzer:
    """Main debug and analysis coordinator."""
    
    def __init__(self, debug_enabled: bool = True, context_export_enabled: bool = True):
        """
        Initialize the debug analyzer.
        
        Args:
            debug_enabled: Whether debug features are enabled (from main config)
            context_export_enabled: Whether context export is enabled (from main config)
        """
        self.debug_enabled = debug_enabled
        self.context_export_enabled = context_export_enabled
        self.context_analyzer = CloseContextAnalyzer(debug_enabled, context_export_enabled)
        self.all_lines: List[str] = []
    
    def set_log_lines(self, lines: List[str]):
        """
        Set the log lines for context extraction.
        
        Args:
            lines: All lines from log files
        """
        self.all_lines = lines
    
    def extract_close_context(self, close_line_index: int) -> List[str]:
        """
        Extract context lines around a close event.
        
        Args:
            close_line_index: Line index where close was detected
            
        Returns:
            List of context lines
        """
        lines_before = CONTEXT_CONFIG["context_lines_before"]
        lines_after = CONTEXT_CONFIG["context_lines_after"]
        
        start_idx = max(0, close_line_index - lines_before)
        end_idx = min(len(self.all_lines), close_line_index + lines_after + 1)
        
        return self.all_lines[start_idx:end_idx]
    
    def process_close_event(self, position, close_line_index: int):
        """
        Process a close event for debug analysis.
        
        Args:
            position: Position that was closed
            close_line_index: Line index where close was detected
        """
        if not self.context_export_enabled:
            return
        
        context_lines = self.extract_close_context(close_line_index)
        self.context_analyzer.add_context(position, context_lines, close_line_index)
    
    def export_analysis(self, output_file: str) -> Dict[str, int]:
        """
        Export complete analysis to file.
        
        Args:
            output_file: Path to output file
            
        Returns:
            Dictionary with export statistics
        """
        return self.context_analyzer.export_contexts(output_file)
    
    def get_context_count(self) -> int:
        """
        Get total number of collected contexts.
        
        Returns:
            Number of close contexts collected
        """
        return len(self.context_analyzer.close_contexts)

# === Utility Functions ===

def get_context_config() -> Dict[str, Any]:
    """
    Get current context configuration.
    
    Returns:
        Context configuration dictionary
    """
    return CONTEXT_CONFIG.copy()