🌐 Language Policy
CRITICAL RULE: Regardless of conversation language, ALL code updates and CLAUDE.md modifications must be in English. This ensures consistency in codebase and documentation.
🎯 Project Objectives
Main Goals

 Bot Performance Analysis - Extract position data from SOL Decoder bot logs
 LP Strategy Optimization - Simulate alternative Meteora DLMM strategies for found positions
 Strategy Ranking - Identify best strategy combinations for different market conditions
 Analysis Automation - Complete pipeline from logs to comparative reports
 TP/SL Optimization - ML-driven optimization of take profit and stop loss levels
 Post-Exit Analysis - Forward-looking profitability analysis beyond historical close points

Project Success Criteria
MVP (current): Tool generates relative strategy rankings for each position with accuracy sufficient for trend and pattern identification.
Long-term: System provides reliable strategic recommendations with precise financial simulations and ML-optimized TP/SL levels.
📋 Coding Conventions
Structure and Organization

Maximum file length: 600 lines of code
When file exceeds 600 lines: time for refactoring (split into modules)
Naming: snake_case for functions/variables, PascalCase for classes

Documentation

Docstrings: Mandatory for all functions and classes
Docstring format: Google style with complete parameter and return value descriptions
Example:

pythondef fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    """
    Fetch price history for a pool from Moralis API.
    
    Args:
        pool_address (str): Meteora pool address to fetch prices for
        start_dt (datetime): Start datetime for price range
        end_dt (datetime): End datetime for price range
        
    Returns:
        List[Dict]: Price data with 'timestamp' and 'close' keys
        
    Raises:
        requests.RequestException: When API call fails
        ValueError: When datetime range is invalid
    """
Anchor Comments (AI Navigation Comments)
Format: # [TAG]-[AI_ID]: [comment content] (max 120 characters)
Available tags:

# AIDEV-NOTE-CLAUDE: - important performance/business logic information
# AIDEV-TODO-CLAUDE: - planned improvements/tasks
# AIDEV-QUESTION-CLAUDE: - doubts to discuss with human
# AIDEV-NOTE-GEMINI: - information added by Gemini
# AIDEV-TODO-GEMINI: - tasks planned by Gemini

Anchor comment usage rules:

Before scanning files: always locate existing AIDEV-* anchors first
When modifying code: update related anchors
DO NOT remove AIDEV-NOTE without explicit human instruction
Add anchors when code is:

too long or complex
very important
confusing or potentially buggy
performance-critical



Usage examples:
python# AIDEV-NOTE-CLAUDE: perf-critical; Moralis API cache mechanism - avoid duplicate requests
def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    # Implementation...

# AIDEV-TODO-CLAUDE: add pool_address format validation (ticket: SOL-123)  
def validate_meteora_pool_address(address: str) -> bool:
    # Current implementation...

# AIDEV-QUESTION-CLAUDE: should timeframe selection be adaptive or fixed? 
# Context: current 10min/30min/1h/4h may not cover all use cases
def calculate_optimal_timeframe(duration_hours: float) -> str:
    # Timeframe selection logic...
Refactoring Rules at 600+ Lines

Extract business logic to separate modules (parsers/, analyzers/, utils/)
Create utils.py for helper functions (timestamp parsing, validation)
Separate layers (data extraction, price fetching, strategy simulation, reporting)
Add AIDEV-NOTE about refactoring reason

Business Logic vs Debug Features

Close reason classification: Core business logic in log_extractor.py (always active)
Context export: Debug feature in debug_analyzer.py (configurable)
Performance consideration: Business logic uses smaller context window (25 lines) vs debug export (80 lines)
Data completeness: All CSV data should be available regardless of debug settings

🚦 Rules for Claude
🎯 You can do without asking

Add anchor comments with CLAUDE tag
Discuss LP strategy business logic (but don't implement without specification)
Implement according to specification when simulation parameters are clearly defined

⚠️ You can propose (but not implement)

Code refactoring - propose plan, wait for approval
API call optimizations - describe benefits, don't introduce automatically
Simulation algorithm improvements - discuss mathematics, don't change without permission
File structure changes - only with explicit permission

🚫 Absolute prohibitions

Don't assume LP strategy logic - Meteora DLMM parameters are specific, always ask
Don't implement Moralis API optimizations without consent (only propose)
Don't remove anchor comments without instructions
Don't change fee calculation logic - this is core business logic

📋 Change Implementation Process

First skeleton/plan of changes for discussion
After approval - complete code with precise "find and replace" instructions
Code changes: using "find and replace" method with exact location
New code: indicate exactly where to paste

🔄 Refactoring (soft-stop at 600+ lines)

Suggest refactoring but allow continuation without it
When refactoring: check function by function that all functionalities are preserved
Format: "I suggest refactoring, but can continue without it if you prefer"

📏 File Length Monitoring

At 600+ lines: gently suggest refactoring with each modification
Don't block work if user decides to continue

📖 Session Management Rules
🎯 Single Task Per Session

One session = one task (plus minor improvements if needed)
Never use same chat for multiple unrelated tasks
If human tries to start new task: remind about this rule (but don't force - not a hard stop)

🔔 Task Completion Reminders

When task seems complete: remind human to test script and update CLAUDE.md
When human confirms testing: automatically suggest all CLAUDE.md updates needed

✅ Session Closure Protocol

Human confirms testing completed: provide complete CLAUDE.md update suggestions
Focus on: Session History, Working Features, Project Status, any structural changes

📚 Domain Dictionary
Data Sources & APIs

Primary Price API - Moralis API (Solana gateway)
Rate Limiting - 0.6s between requests, automatic caching
Supported Timeframes - 10min, 30min, 1h, 4h (adaptive selection)
Cache Strategy - JSON files per pool/timerange in price_cache/

Meteora DLMM Terminology

DLMM - Decentralized Liquidity Market Maker (Meteora protocol)
Bin - discrete price range in liquidity pool
Bin Step - price spacing between bins (in basis points)
Active Bin - bin containing current market price
Price Factor - price multiplier between bins (1 + bin_step/10000)

SOL Decoder Bot Terminology

LP Strategy - liquidity provision strategy (Spot/Bid-Ask × 1-Sided/Wide)
Bid-Ask Distribution - progressive liquidity distribution (more at edges)
Spot Distribution - uniform liquidity distribution
1-Sided Entry - entry with SOL only
Wide Entry - entry with 50/50 SOL/Token split
Step Size - bin size configuration (WIDE/SIXTYNINE/MEDIUM/NARROW)

Financial Metrics

IL (Impermanent Loss) - loss due to relative price changes of assets
PnL from Fees - profit from trading fees
Take Profit (TP) - automatic close when profit target reached
Stop Loss (SL) - automatic close when loss threshold exceeded
Post-Exit Analysis - forward-looking profitability analysis beyond historical close
ML-Optimized Levels - TP/SL levels determined by machine learning algorithms
PnL Filtering - exclusion of positions with insignificant profit/loss (< threshold)

Close Reason Types

TP (Take Profit) - automatic close when profit target reached (patterns: "Take profit triggered:", "🎯 TAKEPROFIT!")
SL (Stop Loss) - automatic close when loss threshold exceeded (pattern: "Stop loss triggered:")
LV (Low Volume) - close due to volume drop below threshold (pattern: "due to low volume")
OOR (Out of Range) - close when price moved beyond bin range and exceeded timeout (pattern: "Closing position due to price range:")
other - all other close types (manual, unknown, system errors, etc.)

🗂️ Project Structure
project/
├── main_analyzer.py         - main orchestrator (extraction → analysis → reporting)
├── log_extractor.py         - main parser with debug controls and close reason classification (~430 lines)
├── debug_analyzer.py        - context analysis and export system (~200 lines)
├── strategy_analyzer.py     - LP strategy simulation engine for Meteora DLMM
├── models.py               - Position class and data models (~50 lines)
├── parsing_utils.py        - universal parsing utilities (~250 lines)
├── input/                  - SOL Decoder bot log files (automatically processes newest)
├── output/                 - analysis results
│   ├── detailed_reports/   - detailed per-position reports
│   └── final_analysis_report.csv - summary with strategy rankings
├── close_contexts_analysis.txt - exported close contexts for pattern analysis
├── price_cache/            - cached price data from Moralis API
└── .env                    - API configuration (MORALIS_API_KEY)
File Handling Rules

Input: all *.log files starting with "app" in input/ directory
Cache: automatic Moralis API response caching (JSON files)
Reports: individual text reports + collective CSV

🏃‍♂️ Project Status
Last Update: 2025-06-21
Current Version: MVP v1.4
Working Features:

Position extraction from SOL Decoder logs ✅ (improved 33%)
Historical price data fetching from Moralis API ✅
4 LP strategy simulation (Spot/Bid-Ask × 1-Sided/Wide) ✅
Comparative report generation ✅
PnL-based position filtering ✅
Debug system with configurable context export ✅
Close reason classification (TP/SL/LV/OOR/other) ✅
Business logic close reason detection (always active) ✅
Duplicate position prevention ✅
Position retry handling with data updates ✅
Strategy detection from logs ✅ (~90% accuracy)
Step size detection (WIDE/SIXTYNINE/MEDIUM/NARROW) ✅
Close timestamp extraction ✅
CSV append mode with deduplication ✅
Modular architecture with proper separation of concerns ✅

In Progress:

Financial simulation accuracy improvements 🔄

Next:

Strategy performance analysis by close reason type 📋
ML-driven TP/SL level optimization 📋
Post-exit analysis (forward-looking candle testing) 📋
Precise fee calculations per-candle 📋

📝 Session History
2025-06-13: Position Exit Date Accuracy

Goal: Fixes in position exit date determination
Achieved: 100% completed - parser correctly identifies close events
Issues: -
Next Steps: Create filter to skip positions without significant PnL

2025-06-17: CLAUDE.md Setup & Roadmap

Goal: Create project bible and define development priorities
Achieved: CLAUDE.md template customization, roadmap clarification
Issues: -
Next Steps: Begin accuracy improvements and TP/SL optimization research

2025-06-18: PnL Filtering Implementation

Goal: Skip positions with insignificant PnL (-0.01 to +0.01 SOL) from analysis
Achieved: Added MIN_PNL_THRESHOLD filter in log_extractor.py validation section
Issues: -
Next Steps: Improve close reason identification accuracy

2025-06-19: Debug System & Context Export Implementation

Goal: Add comprehensive debug system with close context analysis capabilities
Achieved:

Refactored log_extractor.py (648→390 lines) + new debug_analyzer.py (280 lines)
Added configurable debug system with master switches in log_extractor.py
Implemented context export (70 lines before + 10 after close events)
Added close reason classification system (TP/SL/LV/OOR/manual/unknown)
Created filtered export with configurable limits per close type


Technical Changes:

Separated debug functionality into dedicated module
Added DEBUG_ENABLED, CONTEXT_EXPORT_ENABLED master switches
Implemented CloseContextAnalyzer with pattern recognition
Added close_line_index tracking for context extraction


Files: log_extractor.py (refactored), debug_analyzer.py (new)
Issues: -
Next Steps: Analyze generated contexts to develop precise close reason classification patterns

2025-06-20: Close Reason Classification Integration

Goal: Move close reason classification from debug-only to core business logic
Achieved:

Analyzed 10 unknown contexts from new log batch (64 total closures)
Identified TP patterns: "Take profit triggered:" and "🎯 TAKEPROFIT!"
Simplified classification logic (TP/SL/LV/OOR/other)
Moved classification from debug_analyzer.py to log_extractor.py core logic
Added _classify_close_reason() method with optimized 25-line context window
Close reasons now always populated in CSV regardless of debug settings


Technical Changes:

Close reason classification active in all runs, not just debug mode
Reduced context analysis window for performance (25 vs 80 lines)
Simplified LV pattern to just "due to low volume"
Consolidated manual/unknown cases into "other" category


Files: log_extractor.py (enhanced), debug_analyzer.py (patterns refined)
Issues: -
Next Steps: Distribution logic verification

2025-06-20: Duplicate Position Fix & Retry Handling

Goal: Resolve duplicate positions created by bot's multiple transaction attempts
Achieved:

Fixed duplicate position creation when bot retries failed transactions
Changed logic from delete/recreate to update existing position on retry
Added retry count tracking for cleaner logging output
Improved close pattern matching (removed "Closed" requirement)
Enhanced PnL parsing with extended lookback window (20→50 lines)
Added error filtering in investment amount parsing
Position extraction efficiency improved by 33% (49→65 positions)


Technical Changes:

Method _process_open_event() now updates existing positions instead of creating new ones
Preserved original position_id across multiple retry attempts
Added retry_count attribute to track transaction attempts
Implemented cleaner logging showing retry count in parentheses


Files: log_extractor.py (position handling logic rewritten)
Issues: All major parsing issues resolved ✅
Next Steps: Strategy performance analysis by close reason type

2025-06-21: Major Refactoring & Enhanced Parsing

Goal: Fix syntax errors, refactor oversized files, improve strategy detection and close timestamps
Achieved:

Fixed syntax error in _parse_strategy_from_context() - incorrect indentation levels
Major refactoring - split 711-line log_extractor.py into modular structure:

Created models.py (~50 lines) - Position class
Created parsing_utils.py (~250 lines) - all parsing functions
Reduced log_extractor.py to ~430 lines
Updated debug_analyzer.py (~200 lines) - removed duplicate logic


Strategy detection improved to ~90% accuracy:

Added 3 pattern types: bracket format, text format, summary format
Added lookahead parameter for forward searching
Handles both "Spot (1-Sided)" and "Bid-Ask (Wide)" variants


Close timestamp extraction - no more "UNKNOWN" timestamps:

Extracts from close line or searches ±10 lines
Prioritizes backward search for relevance


CSV handling enhanced:

Append mode instead of overwrite
Duplicate detection by position_id
Chronological sorting by open_timestamp
Detailed statistics logging




Technical Changes:

Moved all parsing functions to parsing_utils.py
Each parsing function accepts debug_enabled parameter
Removed guess_close_reason() duplication from debug_analyzer
Better separation of concerns - business logic vs debug features
Maintained full compatibility with main_analyzer.py


Files Modified:

log_extractor.py (refactored from 711→430 lines)
debug_analyzer.py (updated, removed duplication)
models.py (new file)
parsing_utils.py (new file)


Issues: All syntax and structural issues resolved ✅
Next Steps: Test the refactored system, then proceed with strategy performance analysis

2025-06-21: Step Size Detection Implementation

Goal: Add step size information (WIDE/SIXTYNINE/MEDIUM/NARROW) to strategy detection
Achieved:

Step size detection implemented - now extracts step size from bracket format logs
Parser prioritization fixed - bracket format (with step size) now checked before text format
Strategy output enhanced - results now show "Bid-Ask (1-Sided) SIXTYNINE", "Spot (1-Sided) WIDE", etc.
Function signature compatibility - resolved TypeError by removing conflicting parameters


Technical Changes:

Modified parse_strategy_from_context() in parsing_utils.py
Added two-pass search: first for bracket format, then text format as fallback
Added step size regex patterns: r'Step Size:\s*(WIDE|SIXTYNINE|MEDIUM|NARROW)'
Removed lookahead parameter to fix function call compatibility
Enhanced debug logging to track step size detection


Files Modified: parsing_utils.py (strategy parsing logic enhanced)
Issues: Parser prioritization and step size extraction working correctly ✅
Next Steps: Strategy performance analysis by step size and close reason combinations