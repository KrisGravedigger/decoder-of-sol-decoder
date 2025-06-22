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

🚫 Rejected Features & Rationale

Wide vs 69 Bins Comparison Analysis:
- **Issue**: Wide creates 2-4 positions for bin step 50-125, logged as single position by SOL Decoder
- **Implementation complexity**: HIGH - would require multi-position simulation logic, liquidity distribution speculation, complex bin step handling
- **Business value**: LOW - post-factum analysis with limited predictive value, users rarely change Wide/69 settings manually
- **Decision**: Not implemented due to disproportionate effort-to-benefit ratio (80% work for 20% value)
- **Date**: 2025-06-22
- **Alternative priorities**: ML TP/SL optimization, post-exit analysis

Anti-Sawtooth Strategy Analysis:
- **Issue**: Anti-Sawtooth uses frequent rebalancing within 3-5% price ranges (position management strategy)
- **Impact on simulations**: NONE - management strategy, not bin distribution method
- **Current approach**: Simulations assume bot already chose optimal strategy; our bin distribution logic (U-shaped/uniform) remains valid
- **Decision**: No changes needed to existing simulation logic
- **Date**: 2025-06-22

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
Step Size - bin size configuration affecting number and range of bins

SOL Decoder Bot Terminology

LP Strategy - liquidity provision strategy (Spot/Bid-Ask × 1-Sided/2-Sided)
1-Sided Entry - entry with SOL only (no initial 50/50 split)
2-Sided Entry - entry with 50/50 SOL/Token split (placeholder in current implementation)
Step Size Configuration:
  - WIDE: ~50 bins, broader price range
  - MEDIUM: ~20 bins, moderate price range  
  - NARROW: 1-10 bins, tight price range
  - SIXTYNINE: 69 bins, maximum allowed range

Strategy Distribution Patterns:
  - Spot Distribution: Uniform liquidity across all bins
  - Bid-Ask Distribution: U-shaped distribution (more liquidity at edges, based on research formula)

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
├── strategy_analyzer.py     - LP strategy simulation engine for Meteora DLMM (~250 lines)
├── models.py               - Position class and data models (~50 lines)
├── parsing_utils.py        - universal parsing utilities (~250 lines)
├── input/                  - SOL Decoder bot log files (automatically processes newest)
├── output/                 - analysis results
│   ├── detailed_reports/   - detailed per-position reports
│   └── final_analysis_report.csv - summary with strategy rankings
├── close_contexts_analysis.txt - exported close contexts for pattern analysis
├── price_cache/            - cached price data from Moralis API
├── CLAUDE_Session_History.md - complete development session archive
└── .env                    - API configuration (MORALIS_API_KEY)

File Handling Rules

Input: all *.log files starting with "app" in input/ directory
Cache: automatic Moralis API response caching (JSON files)
Reports: individual text reports + collective CSV

🏃‍♂️ Project Status
Last Update: 2025-06-22
Current Version: MVP v2.0
Working Features:

Position extraction from SOL Decoder logs ✅ (improved 33%)
Historical price data fetching from Moralis API ✅
2 LP strategy simulation (1-Sided Spot/Bid-Ask only) ✅
Comparative report generation ✅
PnL-based position filtering ✅
Debug system with configurable context export ✅
Close reason classification (TP/SL/LV/OOR/other) ✅
Business logic close reason detection (always active) ✅
Duplicate position prevention ✅
Position retry handling with data updates ✅
Strategy detection from logs ✅ (~90% accuracy)
Step size detection and processing (WIDE/SIXTYNINE/MEDIUM/NARROW) ✅
Research-based Bid-Ask distribution (U-shaped mathematical formula) ✅
Close timestamp extraction ✅
CSV append mode with deduplication ✅
Modular architecture with proper separation of concerns ✅
Step size integration with bin count adjustment ✅

Completed in v2.0:

Accurate Meteora DLMM simulation for 1-sided strategies 🆕
Research-based mathematical formulas for liquidity distribution 🆕
Step size parsing and automatic bin count adjustment 🆕
Removed risky 2-sided strategy simulations (placeholder only) 🆕
Enhanced strategy naming and result structure 🆕

Next Priority Tasks:

ML-driven TP/SL level optimization 📋
Post-exit analysis (forward-looking candle testing) 📋
Precise fee calculations per-candle 📋

Future Roadmap:

Pipeline Optimization:
  - Run orchestrator on existing data (skip re-extraction/re-fetching) 📋
  - Data gap filling and incremental updates 📋
  - Cross-log position tracking (open in one log, close in another) 📋

Analytics & Reporting Module:
  - Statistical analysis (averages, EMA, profit distributions) 📋
  - Chart generation and visualization 📋
  - Performance correlation with market trends (SOL-USDC, BTC-USDC) 📋

Telegram Integration:
  - Position open/close notifications 📋
  - SL/TP override commands (via n8n automation) 📋
  - Price alert system 📋

Advanced Features:
  - Market trend correlation analysis 📋
  - Real-time strategy recommendations 📋
  - Risk management automation 📋

📝 Session History

## Recent Milestones (Compressed)
**Note:** Complete session history available in `CLAUDE_Session_History.md`

**2025-06-18:** Implemented PnL filtering (-0.01 to +0.01 SOL threshold). Enhanced position parsing accuracy.

**2025-06-19:** Added comprehensive debug system with context export capabilities. Separated debug functionality into dedicated module.

**2025-06-20:** Moved close reason classification to core business logic (always active). Fixed duplicate position handling from bot retry attempts - 33% extraction improvement.

**2025-06-21:** Major refactoring - split oversized files into modular structure (models.py, parsing_utils.py). Enhanced strategy detection to ~90% accuracy with step size support.

**2025-06-22:** Integrated research-based mathematical formulas for accurate DLMM simulations. Implemented U-shaped Bid-Ask distribution, removed risky 2-sided strategies. **System Status: Production-ready v2.0** ✅

## Current Session (Detailed)
**2025-06-22: Wide vs 69 Bins & Anti-Sawtooth Analysis**

**Goal:** Analyze feasibility of Wide vs 69 bins comparison and Anti-Sawtooth impact  
**Achieved:**

- **Wide Multiple-Position Analysis:**
  - Confirmed Wide creates 2-4 positions for bin step 50-125, logged as single position by SOL Decoder
  - Identified implementation complexity: multi-position simulation logic, liquidity distribution speculation, complex bin step handling
  - **Decision:** NOT IMPLEMENTED due to disproportionate effort-to-benefit ratio (80% work for 20% value)
  - Alternative priorities identified: ML TP/SL optimization, post-exit analysis

- **Anti-Sawtooth Impact Assessment:**
  - Confirmed Anti-Sawtooth is position management strategy (frequent rebalancing within 3-5% ranges), not bin distribution method
  - **Decision:** NO IMPACT on existing simulations - current bin distribution logic (U-shaped/uniform) remains valid and accurate
  - Our simulations assume bot already chose optimal strategy, which aligns with Anti-Sawtooth being a management approach

- **Code Impact Verification:**
  - Verified current bin distribution logic unaffected by Wide/Anti-Sawtooth mechanisms
  - All existing simulations remain accurate and mathematically sound
  - No changes needed to strategy_analyzer.py core logic

**Technical Changes:**
- Added AIDEV-NOTE-CLAUDE comment in strategy_analyzer.py documenting rejection rationale for future reference
- Added "Rejected Features & Rationale" section to CLAUDE.md with detailed reasoning and dates
- Created CLAUDE_Session_History.md for complete historical session archive
- Restructured Session History into compressed milestones + detailed current session format

**Files Modified:**
- strategy_analyzer.py (documentation comment added)
- CLAUDE.md (new rejected features section, restructured session history)  
- CLAUDE_Session_History.md (new file, complete history archive)

**Issues:** All analysis completed, decisions documented for future reference ✅  
**Next Steps:** Focus on higher-ROI priorities: ML TP/SL optimization, post-exit analysis

**System Status:** v2.0 stable, ready for next development phase ✅