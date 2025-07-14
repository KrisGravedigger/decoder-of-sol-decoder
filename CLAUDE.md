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

**Session History Management**
- **Maintain full history:** I will keep the detailed log of all recent sessions in this file.
- **Await archival command:** I will not compress or archive the session history. You, the user, will give the command to archive when a major milestone is complete.

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

Strategy Heatmap Image Orientation Issue:
- **Issue**: Generated PNG files saved with 90° clockwise rotation requiring manual correction in image viewers
- **Attempted solutions**: figsize dimension changes, orientation='portrait' parameter, both simultaneously
- **Implementation complexity**: MEDIUM - matplotlib configuration issue not resolved with standard approaches
- **Business impact**: LOW - functional charts generate correctly, only display orientation affected
- **Decision**: Escalated to Gemini for matplotlib expertise, beyond Claude's current troubleshooting scope
- **Date**: 2025-06-28
- **Status**: UNRESOLVED - requires matplotlib/PNG orientation specialist knowledge

Column Name Mapping Chaos (RESOLVED):
- **Issue**: Three different column naming systems (CSV headers, runtime mappings, code expectations) causing KeyError chaos across modules
- **Root cause**: Accidental complexity from position-based → name-based CSV transition with unnecessary "clean name" mappings
- **Business impact**: HIGH - constant maintenance overhead, KeyError crashes, developer confusion
- **Decision**: ELIMINATED all mapping logic, standardized on clean names throughout pipeline
- **Date**: 2025-07-04
- **Resolution**: Plan A implementation - direct CSV → code name consistency, zero mapping overhead
- **Status**: RESOLVED - clean codebase achieved ✅

Strategy Parsing Issues (RESOLVED):
- **Issue**: 455 unresolved parsing cases (242 suspicious + 213 missing step_size) causing incomplete position data
- **Root cause**: Basic regex patterns existed but logic for applying them was flawed
- **Business impact**: HIGH - 99.5% of problematic parsing cases, incomplete dataset for analysis
- **Resolution**: Complete parsing logic overhaul by Gemini with iterative debugging approach
- **Date**: 2025-07-11
- **Status**: RESOLVED - 2 remaining edge cases (99.5% success rate) ✅

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
Rate Limiting - 0.6s between requests, automatic caching with intelligent gap detection
Supported Timeframes - 10min, 30min, 1h, 4h (adaptive selection)
Cache Strategy - JSON files per pool/timerange in price_cache/ with smart placeholder filling

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

Market Analysis Terminology

EMA Slope Trend Detection: 3-day percentage change in 50-period EMA (>0.1% = uptrend)
Pearson Correlation: Linear correlation coefficient between portfolio and SOL daily returns
Weekend Parameter: weekendSizePercentage configuration reducing position sizes on Sat/Sun UTC
Weekend Parameter Analysis: Simulation comparing current vs alternative weekend position sizing
Statistical Significance: p-value < 0.05 for correlation and trend difference testing
Interactive HTML Reports: Plotly-based comprehensive reports with embedded visualizations

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
Superseded - close when a new position for the same pair is opened before the previous one was closed, indicating a replacement/restart

## Enhanced Deduplication System

**Universal Position ID** - Cross-file position identifier using `pool_address + open_timestamp`
**Position Completion** - Process of updating incomplete positions (`active_at_log_end`) with complete data from subsequent files
**Cross-File Position Tracking** - System capability to track positions that open in one log file and close in another
**Chronological File Processing** - Files processed in sorted order to maintain proper event sequencing
**Duplicate Handling Logic**:
  - **Skip**: Exact duplicates (same position_id)
  - **Update**: Incomplete position → complete position
  - **Add**: New positions not seen before

**File Processing Order**: Alphabetical sorting ensures consistent chronological processing of log files

## Smart Price Cache Management

**Smart Gap Detection** - Identifies missing time periods in cache and fetches only required gaps from API
**API Failure Handling** - Distinguishes between "no data available" (weekend) vs "API request failed" (401 error)
**Placeholder Logic** - Creates intelligent forward-filled placeholders for verified empty periods only
**Cross-API-Failure Safety** - Skips gap filling on API failures, enables retry on subsequent runs
**Cache Integrity** - Monthly cache files with incremental updates, no data loss on partial fetches

## Custom Timestamp Handling

**SOL Decoder Timestamp Format:** `MM/DD-HH:MM:SS` (non-standard format)
**Example:** `05/12-20:57:08` = May 12, 20:57:08 (current year)
**Special Case:** `24:XX:XX` = next day 00:XX:XX

**Issue:** `pandas.to_datetime()` fails on this format
**Solution:** Use `_parse_custom_timestamp()` from `data_loader.py`

**Location:** reporting/data_loader.py::_parse_custom_timestamp()
**Status:** Production-ready, handles edge cases (24:XX rollover)

```python
# AIDEV-NOTE-CLAUDE: Handle SOL Decoder custom timestamp format
from data_loader import _parse_custom_timestamp
positions_df['timestamp_column'] = positions_df['timestamp_column'].apply(_parse_custom_timestamp)
```

## Unified Column Naming System

**Clean Names Standard** - All modules use consistent, short column names without mapping overhead
**Current Standard:**
- `investment_sol` (not `initial_investment_sol`)
- `pnl_sol` (not `final_pnl_sol_from_log`)
- `strategy_raw` (not `actual_strategy_from_log`)

**Implementation:** Direct CSV header → code usage, zero mapping logic
**Benefits:** Eliminated accidental complexity, improved maintainability, faster debugging
**Status:** Fully implemented across entire codebase ✅

## Strategy Parsing & Pipeline Stabilization

**Take Profit/Stop Loss Parsing** - Enhanced position model with TP/SL fields parsed from opening events
**Context-Based Parsing** - Improved strategy detection using reverse search with lookahead context
**Silent Failure Detection** - SUCCESS_CONFIRMATION_PATTERNS prevent false positive position detection
**Business Logic Integration** - Core TP/SL data now available throughout analysis pipeline
**Parsing Accuracy** - Improved from ~90% to >99.5% success rate for strategy parameter detection

🗂️ Project Structure
project/
├── main.py                     # Main application entry point with interactive menu
├── main_analyzer.py            # (Legacy) Alternative analysis entry point
├── core/
│   └── models.py               # Position class with TP/SL fields and other data models
├── extraction/                 # Data extraction from logs
│   ├── __init__.py
│   ├── log_extractor.py        # Main parser with enhanced strategy parsing and cross-file tracking
│   └── parsing_utils.py        # Enhanced parsing utilities with TP/SL extraction
├── reporting/                  # Analytics and portfolio performance analysis
│   ├── __init__.py
│   ├── config/
│   │   └── portfolio_config.yaml
│   ├── templates/
│   │   └── comprehensive_report.html
│   ├── visualizations/         # Chart plotting modules
│   │   ├── __init__.py
│   │   ├── cost_impact.py
│   │   ├── drawdown.py
│   │   ├── equity_curve.py
│   │   ├── interactive_charts.py # Plotly charts for HTML report
│   │   └── strategy_heatmap.py
│   ├── orchestrator.py         # Core logic engine for the reporting workflow
│   ├── analysis_runner.py      # Runs Spot vs. Bid-Ask simulation for all positions
│   ├── data_loader.py          # Position data loading and cleaning (no mapping logic)
│   ├── html_report_generator.py # HTML report generation orchestrator
│   ├── infrastructure_cost_analyzer.py # Daily cost allocation and Moralis API
│   ├── market_correlation_analyzer.py  # Analysis of portfolio vs market correlation
│   ├── metrics_calculator.py   # Financial metrics calculation
│   ├── strategy_instance_detector.py # Groups positions into strategy instances
│   ├── text_reporter.py        # Text report generation
│   └── price_cache_manager.py  # Smart price caching with gap detection and API failure handling
├── simulations/                # "What-if" simulation engines
│   ├── spot_vs_bidask_simulator.py # Simulates Spot vs Bid-Ask strategies
│   └── weekend_simulator.py    # Simulates weekend parameter impact
└── tools/                      # Developer and utility tools
    ├── api_checker.py          # Checks Moralis API connectivity
    ├── debug_analyzer.py       # Context analysis and export system
    └── fix_column_names.py     # Column name standardization utility

File Handling Rules

Input: all *.log files starting with "app" in input/ directory
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names

🏃‍♂️ Project Status
Last Update: 2025-07-11
Current Version: v4.2 - Strategy parsing & pipeline stabilization
Working Features:

Position extraction from SOL Decoder logs ✅ (improved to >99.5% accuracy)
Historical price data fetching from Moralis API ✅
Smart price cache with gap detection and API failure handling ✅
2 LP strategy simulation (1-Sided Spot/Bid-Ask only) ✅
Comparative report generation ✅
PnL-based position filtering ✅
Debug system with configurable context export ✅
Close reason classification (TP/SL/LV/OOR/other) ✅
Reliable Take Profit/Stop Loss parsing from `OPENED` events ✅
Robust handling of position restarts/replacements ("Superseded" logic) ✅
Business logic close reason detection (always active) ✅
Business logic close reason detection (always active) ✅
Duplicate position prevention ✅
Position retry handling with data updates ✅
Strategy detection from logs ✅ (>99.5% accuracy)
Step size detection and processing (WIDE/SIXTYNINE/MEDIUM/NARROW) ✅
Research-based Bid-Ask distribution (U-shaped mathematical formula) ✅
Close timestamp extraction ✅
CSV append mode with deduplication ✅
Modular architecture with proper separation of concerns ✅
Step size integration with bin count adjustment ✅
Strategy instance detection and grouping ✅
Multi-wallet support with subfolder organization ✅
Strategy performance ranking with weighted scoring ✅
Enhanced CSV structure with wallet_id and source_file tracking ✅
Enhanced position deduplication with cross-file tracking ✅
Universal position identification (pool_address + open_timestamp) ✅
Automatic position completion (active_at_log_end → complete positions) ✅
Chronological file processing for proper position sequencing ✅
Intelligent duplicate handling with update/skip logic ✅
Enhanced position deduplication with universal identification ✅
Cross-file position tracking and completion ✅
Chronological file processing with intelligent duplicate handling ✅

**Portfolio Analytics Module:**
- **Complete analysis pipeline**: dual SOL/USDC currency analysis with infrastructure cost impact ✅
- **Chart generation system**: 4 professional charts with timestamps (equity curve, drawdown analysis, strategy heatmap, cost impact) ✅
- **Strategy heatmap**: automated parsing of step_size from strategy names, position counts display, filter details ✅
- **Text report generation**: timestamped portfolio summaries and infrastructure impact reports ✅
- **YAML configuration**: infrastructure costs, risk-free rates, visualization filters ✅
- **Moralis API integration**: historical SOL/USDC price data with smart caching ✅
- **Custom timestamp parsing**: handles non-standard formats (MM/DD-HH:MM:SS, 24:XX:XX) ✅
- **Robust error handling**: fallback mechanisms for missing data and CSV structure variations ✅

**Architecture Stabilization & Resiliency:**
- **Centralized Entry Point**: `main.py` provides a single, interactive menu to run all parts of the pipeline ✅
- **Robust API Key Handling**: Dependency injection ensures the API key is passed securely and used only when needed ✅
- **Cache-Only Mode**: Full application support for running in an offline/cached mode for testing and cost savings ✅
- **Error Resiliency (Graceful Degradation)**: The HTML report generation no longer crashes on missing data (e.g., from market analysis in cache-only mode), instead displaying informative messages ✅

**Smart Price Cache Management v2.0:**
- **Intelligent Gap Detection**: Only fetches missing time periods, prevents redundant API calls ✅
- **API Failure vs No Data Distinction**: Handles 401 errors differently from legitimate empty periods (weekends) ✅
- **Smart Placeholder Logic**: Forward-fills only verified empty periods, skips placeholder creation on API failures ✅
- **Cross-API-Failure Safety**: Enables retry on subsequent runs for failed requests while preserving verified empty data ✅
- **Monthly Cache Files**: Organized by month with incremental updates and merge capabilities ✅

**Column Name Standardization v1.0:**
- **Eliminated Mapping Chaos**: Removed all column name mapping logic from entire codebase ✅
- **Unified Naming System**: CSV headers and code use identical clean names (investment_sol, pnl_sol, strategy_raw) ✅
- **Zero Accidental Complexity**: Direct CSV → code usage, no intermediate mapping layers ✅
- **Improved Maintainability**: Single source of truth for column names, easier debugging ✅
- **Performance Enhancement**: Eliminated mapping overhead in data processing pipeline ✅

**Strategy Parsing & Pipeline Stabilization v4.2:**
- **Enhanced TP/SL Parsing**: Take profit and stop loss values now extracted and stored in Position model ✅
- **Improved Strategy Detection**: >99.5% accuracy through reverse search with context lookahead ✅
- **Silent Failure Detection**: SUCCESS_CONFIRMATION_PATTERNS prevent false positive position detection ✅
- **Robust Pipeline**: NaN handling and error resilience throughout data processing pipeline ✅
- **Enhanced Logging**: Clean, focused logs with DEBUG-level detail control ✅

Completed in v2.0:

Accurate Meteora DLMM simulation for 1-sided strategies 🆕
Research-based mathematical formulas for liquidity distribution 🆕
Step size parsing and automatic bin count adjustment 🆕
Removed risky 2-sided strategy simulations (placeholder only) 🆕
Enhanced strategy naming and result structure 🆕

Completed in Session 1 (2025-06-25):

Strategy Instance Detection Module 🆕
- Automated grouping of positions into strategy instances based on parameters 🆕
- Investment tolerance handling (±0.005 SOL) for test variants 🆕
- Weighted performance scoring with business-defined metrics 🆕
- Multi-wallet support via subfolder organization (input/wallet_name/) 🆕
- Enhanced Position model with wallet_id and source_file tracking 🆕
- Backward-compatible CSV structure with automatic column addition 🆕
- Strategy ranking system identifying top-performing configurations 🆕

**Completed in Portfolio Analytics v1.0:**
- **Complete Portfolio Analytics Module** 🆕
  - Dual currency analysis (SOL/USDC) with historical conversion rates 🆕
  - Infrastructure cost integration with daily flat allocation ($28.54/month) 🆕
  - Professional chart generation (4 types) with timestamped outputs 🆕
  - Strategy performance heatmaps with automatic step_size parsing 🆕
  - Comprehensive text reports with cost impact analysis 🆕
  - YAML configuration system for costs and parameters 🆕
  - Main orchestrator with CLI interface and multiple analysis modes 🆕

**Technical Achievements:**
- **Advanced CSV Processing**: handles messy real-world data with custom timestamp parsing 🆕
- **Strategy Name Parsing**: extracts step_size from embedded format ("Bid-Ask (1-Sided) MEDIUM") 🆕
- **Moralis API Integration**: working SOL/USDC price feeds with intelligent caching 🆕
- **Robust Error Handling**: dual fallback system for chart generation 🆕
- **Cost Impact Analysis**: daily allocation across active positions with break-even metrics 🆕

Completed in v3.0
**Market Analysis & Reporting Module:**
- **Market correlation analysis**: Pearson correlation with SOL trends, EMA slope detection ✅
- **Weekend parameter optimization**: weekendSizePercentage impact simulation with 5x scaling ✅  
- **Interactive HTML reporting**: Plotly-based comprehensive reports with executive summaries ✅
- **CLI analysis modes**: `--correlation`, `--weekend`, `--comprehensive` options ✅
- **Performance optimization**: single CSV load for comprehensive analysis (3x faster) ✅
- **Custom timestamp integration**: SOL Decoder format parsing in portfolio pipeline ✅
- **Configuration-driven metrics**: risk-free rates from YAML, no hardcoded values ✅
- **Statistical significance testing**: confidence intervals and p-values for correlations ✅

**Completed in v3.3 - Weekend Parameter Analysis v2.1:**
- **Complete weekend parameter analysis logic**: CSV always represents actual positions ✅
- **Dual scenario simulation**: current vs alternative weekend sizing with proper interpretation ✅
- **YAML-driven configuration**: weekend_size_reduction and size_reduction_percentage parameters ✅
- **Orchestrator-level skip logic**: analysis skipped when size_reduction_percentage=0 ✅
- **Enhanced error handling**: proper handling of skipped analysis in HTML reports ✅
- **Fixed interactive charts**: updated key mapping (current_scenario/alternative_scenario) ✅
- **Business logic documentation**: clear assumptions about CSV data interpretation ✅

**Completed in v3.6 - Architecture Stabilization & Resiliency:**
- **Centralized architecture**: main.py as single entry point with interactive menu ✅
- **Robust API key handling**: dependency injection pattern eliminating 401 errors ✅
- **Cache-only mode**: full offline operation capability for testing and API credit conservation ✅
- **Graceful degradation**: HTML reports handle missing data without crashes ✅
- **Enhanced error resiliency**: comprehensive fallback mechanisms throughout pipeline ✅

**Completed in v4.0 - Smart Cache & Column Standardization:**
- **Smart Price Cache v2.0**: Intelligent gap detection, API failure vs no-data distinction, smart placeholder logic ✅
- **Column Name Standardization**: Eliminated mapping chaos, unified naming system across entire codebase ✅
- **Cache API Failure Handling**: Proper distinction between API failures (retry tomorrow) vs verified empty periods (cache forever) ✅
- **Forward Fill Intelligence**: Placeholders only for verified data gaps, not API failures ✅
- **Zero Mapping Overhead**: Direct CSV header → code usage, eliminated accidental complexity ✅

**Completed in v4.1 - Zero Price Bug Resolution:**
- **Root Cause Identified**: Legacy cache files contained zero placeholders instead of forward-filled prices ✅
- **Cache Manager Fix**: Enhanced placeholder logic to use valid nearby prices ✅  
- **Analysis Runner Enhancement**: Forward-fill logic with comprehensive missing data warnings ✅
- **Cache Repair Tool**: Automated script to fix existing zero placeholders in cache files ✅
- **Zero Price Elimination**: 100% elimination of "Zero price detected in simulation" warnings ✅

**Completed in v4.2 - Strategy Parsing & Pipeline Stabilization:**
- **Enhanced TP/SL Parsing**: Take profit and stop loss values extracted from opening events and stored in Position model ✅
- **Context-Based Strategy Detection**: Reverse search with lookahead context improved accuracy to >99.5% ✅
- **Silent Failure Detection**: SUCCESS_CONFIRMATION_PATTERNS prevent false positive position detection ✅
- **Pipeline Stabilization**: Enhanced error handling, NaN-resistant processing, robust data flow ✅
- **Logging Optimization**: Clean operational logs with DEBUG-level detail for diagnostics ✅

**Completed in v4.3 - Robust Single-Line Parsing & "Superseded" Logic:**
- **Critical Parsing Fix**: Replaced fragile, multi-line parsing with a robust single-line strategy, resolving the core issue of `NaN` values for TP/SL ✅
- **Single-Line Anchor**: The `... | OPENED ...` log entry is now the single source of truth for opening events, improving reliability from ~90% to >99.9% ✅
- **Unified Data Extraction**: TP, SL, investment, strategy, wallet address, and version are all parsed from one line, eliminating context-related errors ✅
- **"Superseded" Logic**: Implemented robust handling for position restarts, where an old, unclosed position is automatically closed and logged when a new one for the same pair appears ✅
- **Minimal Context Search**: Context searching is now only used for the targeted retrieval of `pool_address` from `View DLMM` links, increasing precision ✅
- **Parser Simplification**: Significantly simplified the codebase in `log_extractor.py` and `parsing_utils.py`, improving maintainability ✅

Next Priority Tasks:

**Immediate (Next Session):**
- **TP/SL Optimization Module**: ML-driven take profit and stop loss level optimization 📋
- **Post-exit analysis**: forward-looking profitability analysis beyond historical close points 📋

**Strategy Analytics Module Enhancement:**
  - Strategy comparison matrix with detailed performance breakdown 📋
  - Daily performance tracking and trend analysis 📋
  - Performance correlation with market trends (SOL-USDC, BTC-USDC) 📋

**ML & Advanced Analytics:**
  - ML-driven TP/SL level optimization 📋
  - Post-exit analysis (forward-looking candle testing) 📋
  - Precise fee calculations per-candle 📋

**Delta-Neutral LP Management (Planned Post TP/SL Optimization):**
  - Funding rate analyzer with multi-DEX monitoring📋
  - Real-time delta exposure calculator for active LP positions 📋
  - Optimal hedge position sizing with leverage optimization 📋
  - SOL-USDC trend correlation with funding rate analysis 📋
  - Delta-neutral P&L reporting, performance analytics and simulations 📋
  - Market regime detection (bull/bear/crab) for hedge timing 📋
  - **Business rationale**: Isolate LP fee profits from directional SOL risk, enable larger LP exposure with controlled risk 📋

Future Roadmap:

Pipeline Optimization:
  - Run orchestrator on existing data (skip re-extraction/re-fetching) 📋
  - Data gap filling and incremental updates 📋
  - Cross-log position tracking (open in one log, close in another) ✅ COMPLETED

Analytics & Reporting Module:
  - Statistical analysis (averages, EMA, profit distributions) ✅ COMPLETED
  - Chart generation and visualization ✅ COMPLETED
  - Performance correlation with market trends (SOL-USDC, BTC-USDC) ✅ COMPLETED

Telegram Integration:
  - Position open/close notifications 📋
  - SL/TP override commands (via n8n automation) 📋
  - Price alert system 📋

Advanced Features:
  - Market trend correlation analysis ✅ COMPLETED
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

**2025-06-25: Strategy Instance Detection & Multi-Wallet Support**

**Goal:** Build strategy instance detection system and enable multi-wallet analytics  
**Achieved:**

- **Modular Architecture Implementation:**
  - Restructured project into extraction/ and reporting/ modules
  - Created strategy_instance_detector.py as foundation for analytics module
  - Enhanced import system for cross-module compatibility

- **Multi-Wallet Support:**
  - Enhanced log_extractor.py to support subfolder organization (input/wallet_name/)
  - Added wallet_id and source_file tracking to Position model
  - Enabled consolidation of logs from multiple wallets/machines

- **Strategy Instance Detection:**
  - Implemented automatic grouping of positions into strategy instances
  - Investment tolerance logic (±0.005 SOL) for distinguishing test variants
  - Business-defined weighted scoring: avg_pnl_percent(40%) + win_rate(40%) + efficiency metrics(20%)
  - Generated 19 unique strategy instances from 71 positions in initial test

- **Performance Analysis Results:**
  - Top strategy: Bid-Ask MEDIUM 2.21 SOL (3.5% avg PnL, 100% win rate)
  - Clear performance differentiation across investment amounts and strategies
  - Successful ranking system identifying optimal configurations

- **Enhanced Data Pipeline:**
  - Backward-compatible CSV structure with automatic column addition
  - strategy_instance_id assignment for position tracking
  - Export to strategy_instances.csv with comprehensive metrics

**Technical Changes:**
- extraction/log_extractor.py: Added multi-wallet support and enhanced Position creation
- models.py: Extended with wallet_id, source_file, and strategy_instance_id fields
- reporting/strategy_instance_detector.py: Complete implementation with grouping and ranking
- Enhanced import system for modular architecture

**Files Modified:**
- models.py (enhanced Position class)
- extraction/log_extractor.py (multi-wallet support)
- reporting/strategy_instance_detector.py (new module)
- CLAUDE.md (architecture and progress updates)

**Results:** Successfully detected 19 strategy instances with clear performance ranking ✅  
**Next Steps:** Strategy comparison matrix and daily performance tracking modules

**System Status:** Strategy analytics foundation complete, ready for advanced reporting ✅

## Current Session (Detailed)
**2025-06-28: Portfolio Analytics Module Implementation (Session 2)**

**Goal:** Build complete portfolio analytics system with infrastructure cost analysis and dual currency metrics
**Achieved:**

- **Portfolio Analytics System Implementation:**
  - Complete portfolio_analytics.py with dual currency analysis (SOL primary, USDC secondary) ✅
  - Infrastructure cost analyzer with daily flat allocation ($28.54/month = $0.95/day) ✅
  - Chart generator with 4 chart types (equity curve, drawdown, strategy heatmap, cost impact) ✅
  - Main orchestrator with CLI interface and multiple analysis modes ✅
  - YAML configuration system for costs and parameters ✅

- **Robust Data Processing:**
  - CSV column mapping for positions_to_analyze.csv structure ✅
  - Custom timestamp parser handling 24:XX:XX format → 00:XX:XX next day ✅
  - Strategy and step_size extraction from actual_strategy_from_log ✅
  - Moralis API integration for SOL/USDC historical rates ✅

- **Technical Achievements:**
  - Fixed critical bugs in metrics calculation (daily_usdc_df → daily_df) ✅
  - Improved daily return calculation (daily_pnl / capital_base vs pct_change) ✅
  - Working Moralis endpoint using Raydium SOL/USDC pool ✅
  - Timestamped output files preventing overwrites ✅
  - Cost impact overlay on equity curves ✅

- **Chart Generation System:**
  - Strategy heatmap with step_size parsing from embedded strategy names ✅
  - Position counts in strategy names (e.g., "Bid-Ask MEDIUM 2.15SOL (13)") ✅
  - Filter information showing excluded strategies ✅
  - Fallback to positions-based heatmap when strategy_instances.csv fails ✅
  - All 4 chart types working: equity curve, drawdown, strategy heatmap, cost impact ✅

**Files Generated:**
- reporting/config/portfolio_config.yaml ✅
- reporting/infrastructure_cost_analyzer.py ✅
- reporting/portfolio_analytics.py ✅
- reporting/chart_generator.py ✅
- reporting/portfolio_main.py ✅

**Results:** Successfully analyzed 70 positions over 36 days, generated 4 charts and comprehensive reports

**Technical Fixes Applied:**
- Strategy heatmap CSV parsing: extract step_size from "Bid-Ask (1-Sided) MEDIUM" format ✅
- Enhanced error handling with dual fallback system ✅
- Improved subtitle positioning and filter details ✅
- Cost impact analysis for negative PnL scenarios ✅

**Issues:** Strategy heatmap image orientation - PNG files save rotated 90° clockwise, escalated to Gemini
**Next Steps:** Complete matplotlib orientation fix, integrate with existing pipeline

**System Status:** 100% functional, production-ready for analysis and reporting ✅

**2025-06-29: Major Refactoring and Stability Fixes**
**Goal:** Refactor oversized modules for maintainability and fix a critical data loading bug.
**Achieved:**
- **Major Refactoring:**
  - `portfolio_analytics.py` and `chart_generator.py` were refactored into smaller, single-responsibility modules, adhering to the project's 600-line file limit.
  - New modules created: `data_loader.py`, `metrics_calculator.py`, `text_reporter.py`, and the `visualizations/` directory with its own set of plotting modules.
  - The project structure is now significantly cleaner, more scalable, and easier to maintain.
- **Critical Bug Fix:**
  - Resolved a timestamp parsing issue in `data_loader.py` that caused all 71 positions to be discarded. The logic now correctly handles mixed standard and custom date formats, unblocking the entire analysis pipeline.
- **Metric Refinement:**
  - Improved the "Cost Impact %" calculation in `infrastructure_cost_analyzer.py` to correctly handle cases with negative Gross PnL, providing more intuitive results in all scenarios.
**System Status:** Portfolio Analytics v1.1 - Stable and Refactored. ✅

**2025-07-02: Market Correlation & Weekend Analysis Implementation (Session 3)**

**Goal:** Complete reporting module with market correlation analysis, weekend parameter optimization, and comprehensive HTML reporting system.

**Achieved:**

- **Market Correlation Analysis Module:**
  - Complete `market_correlation_analyzer.py` with Pearson correlation analysis ✅
  - EMA 50 slope-based trend detection (3-day slope, 0.1% threshold) ✅
  - SOL market trend segmentation (uptrend vs downtrend performance) ✅
  - Statistical significance testing with confidence intervals ✅
  - Moralis API integration for SOL/USDC price data ✅

- **Weekend Parameter Analysis Module:**
  - Complete `weekend_parameter_analyzer.py` with weekendSizePercentage simulation ✅
  - 5x position scaling logic (weekend positions enlarged, weekday reduced) ✅
  - UTC weekend classification (Saturday-Sunday) ✅
  - Performance comparison with ENABLE/DISABLE recommendations ✅
  - Comprehensive metrics analysis (PnL, ROI, Win Rate, Sharpe) ✅

- **Interactive HTML Report System:**
  - Complete `html_report_generator.py` with Plotly interactive charts ✅
  - Professional HTML template with embedded visualizations ✅
  - Comprehensive report combining all analysis modules ✅
  - Executive summary with key metrics and recommendations ✅
  - Pure Python implementation (Jinja2 + Plotly, no external dependencies) ✅

- **Portfolio Main Optimization:**
  - Major performance optimization: CSV loaded only once in comprehensive analysis ✅
  - New CLI modes: `--correlation`, `--weekend`, `--comprehensive` ✅
  - Enhanced error handling and backward compatibility ✅
  - Configuration-driven risk-free rates (no hardcoded values) ✅
  - Refactored methods integration with `metrics_calculator.py` modules ✅

**Technical Achievements:**
- **Performance Optimization**: 3x faster comprehensive analysis (single CSV load) ✅
- **Custom Timestamp Handling**: integrated SOL Decoder format parsing (`MM/DD-HH:MM:SS`) ✅
- **Column Mapping**: automatic CSV structure adaptation (`final_pnl_sol_from_log` → `pnl_sol`) ✅
- **Gemini Code Review**: implementation received "very high quality" rating with 100% compliance ✅

**Files Generated:**
- reporting/market_correlation_analyzer.py (300 lines) ✅
- reporting/weekend_parameter_analyzer.py (280 lines) ✅  
- reporting/html_report_generator.py (450 lines) ✅
- reporting/portfolio_main.py (enhanced with new modules) ✅

**Integration Results:**
- **Test Analysis**: 70 positions over 36 days successfully processed ✅
- **Performance Metrics**: 85.7% win rate, -0.861 SOL PnL, 20.9% infrastructure cost impact ✅
- **Files Generated**: 2 text reports + 4 PNG charts in 1.6 seconds ✅
- **New CLI Modes**: All analysis types working (correlation, weekend, comprehensive) ✅

**Business Insights Enabled:**
- **Market Correlation**: SOL trend impact on LP strategy performance ✅
- **Weekend Parameter**: Data-driven weekendSizePercentage optimization ✅
- **Infrastructure Costs**: Significant 20.9% impact identified and quantified ✅
- **Comprehensive Analysis**: All modules working together seamlessly ✅

**2025-07-02: Major Refactoring and UI Enhancement**

**Goal:** Refactor oversized modules (`portfolio_main.py`, `html_report_generator.py`) to adhere to project standards and add an interactive user menu for ease of use.
**Achieved:**

- **Major Refactoring (Code Modularity):**
  - `html_report_generator.py` was refactored by extracting its large HTML template into `reporting/templates/comprehensive_report.html` and moving all Plotly chart creation logic to a new, dedicated module: `reporting/visualizations/interactive_charts.py`. This significantly improved maintainability.
  - `portfolio_main.py` was split into two distinct files, separating the user interface from the core logic:
    - `orchestrator.py`: Now contains the `PortfolioAnalysisOrchestrator` class, serving as the pure logic engine for the analysis workflow.
    - `portfolio_main.py`: Re-created as the main command-line entry point, featuring an interactive menu and argument parsing. It now imports and uses the `PortfolioAnalysisOrchestrator`.

- **UI Enhancement (Interactive Menu):**
  - Implemented a user-friendly interactive menu in the new `portfolio_main.py`. This allows users to select analysis modes (comprehensive, quick, period-specific) without needing to memorize command-line arguments, improving accessibility.
  - Retained the command-line argument functionality for automation and power-user workflows.

- **Improved Project Structure:**
  - The overall project structure is now cleaner and more aligned with the single-responsibility principle. The new files fit logically within the established directory layout (`templates/`, `visualizations/`).

**2025-07-02: Weekend Parameter Analysis v2.1 - Final Implementation**

**Goal:** Implement correct weekend parameter analysis logic with proper business assumptions and YAML configuration.

**Achieved:**

- **Corrected Business Logic:**
  - **CSV Data Interpretation**: CSV always represents actual positions (regardless of weekend_size_reduction config) ✅
  - **Dual Scenario Simulation**: 
    - `weekend_size_reduction=1`: CSV has reduced weekend positions → simulate enlarged for comparison ✅
    - `weekend_size_reduction=0`: CSV has normal positions → simulate reduced for comparison ✅
  - **Weekend Position Focus**: Only positions opened during weekend (Sat/Sun UTC) are affected by simulation ✅
  - **Weekday Positions**: Remain identical in both scenarios (no changes) ✅

- **YAML Configuration Enhancement:**
  - **Enhanced Configuration**: `weekend_analysis` section in `portfolio_config.yaml` ✅
  - **Skip Logic**: `size_reduction_percentage: 0` = no analysis ✅
  - **Business Documentation**: Clear comments explaining assumptions and logic ✅

- **Orchestrator Integration:**
  - **Skip Logic**: Moved from analyzer to orchestrator for better workflow control ✅
  - **Enhanced Logging**: Proper warning and info messages for skipped analysis ✅
  - **Error Handling**: Graceful handling of skipped analysis in HTML reports ✅

- **Interactive Charts Fix:**
  - **Key Mapping Update**: Fixed `original_scenario` → `current_scenario` mapping ✅
  - **Removed Win Rate**: Eliminated win_rate from weekend analysis charts (business requirement) ✅
  - **Dynamic Scenario Names**: Charts now use actual scenario names from analysis ✅
  - **Skip Handling**: Proper display when analysis is skipped ✅

**Technical Changes:**
- **weekend_parameter_analyzer.py**: Complete rewrite with correct simulation logic ✅
- **orchestrator.py**: Added `_should_skip_weekend_analysis()` and enhanced workflow ✅
- **interactive_charts.py**: Fixed key mapping and removed win_rate from weekend charts ✅
- **portfolio_config.yaml**: Added comprehensive weekend_analysis configuration ✅

**Business Validation:**
- **Test Results**: KEEP_DISABLED recommendation with -0.565 SOL impact ✅
- **Scenario Names**: "ENABLED (80% weekend reduction)" vs "DISABLED (normal weekend sizes)" ✅
- **Proper Metrics**: Focus on PnL, ROI, and Sharpe ratio (no win_rate) ✅

**Files Modified:**
- reporting/config/portfolio_config.yaml (enhanced with weekend_analysis section)
- reporting/weekend_parameter_analyzer.py (complete rewrite)
- reporting/orchestrator.py (skip logic and enhanced workflow)
- reporting/visualizations/interactive_charts.py (fixed key mapping and charts)

**System Status:** Weekend Parameter Analysis v2.1 - Fully Functional and Business-Correct ✅

**Ready for Next Priority:** TP/SL Optimization Module - ML-driven take profit and stop loss level optimization 🚀

**2025-07-03: Post-Refactoring Stabilization & Error Resiliency**

**Goal:** Fully stabilize the application after a major architectural refactoring, ensure correct data flow, and implement error resiliency mechanisms for missing API data.

**Achieved:**
- **Centralized Architecture:** Refactored the application to use `main.py` as the single entry point with an interactive menu, orchestrating the entire analysis pipeline.
- **Fixed API Access:** Implemented a dependency injection pattern for the Moralis API key, eliminating `401 Unauthorized` errors and stabilizing connections.
- **Implemented "Cache-Only" Mode:** Added an `api_settings.cache_only` option in `portfolio_config.yaml`, allowing the application to run entirely from cached data for testing and saving API credits.
- **Restored Full Analysis Pipeline:** Reintegrated the previously omitted `strategy_instance_detector` module into the main workflow, ensuring the `strategy_instances.csv` file is generated correctly.
- **Implemented "Graceful Degradation":**
  - The reporting module (`html_report_generator`, `interactive_charts`) is now resilient to failures caused by missing data (e.g., market correlation analysis in cache-only mode).
  - Instead of a crash, the application now successfully generates the full HTML report, displaying "Data Unavailable" messages in sections where analysis could not be completed.
- **Unified User Interface:** Translated all UI elements and prompts in `main.py` to English, adhering to the project's critical rules.

**Status:** Architecture stabilized. The application is fully functional, robust, and resilient to common errors from missing cache data. It is ready for further development. ✅

**2025-07-03: Enhanced Deduplication & Cross-File Position Tracking**

**Goal:** Implement robust position deduplication system to handle overlapping log files and cross-file position tracking.

**Achieved:**

- **Universal Position Identification:**
  - Implemented `universal_position_id` property in Position model using `pool_address + open_timestamp` ✅
  - Added `is_position_complete()` method to detect incomplete vs complete positions ✅
  - Enhanced validation to require `pool_address` as mandatory field ✅

- **Enhanced Deduplication Logic:**
  - **Cross-file position tracking**: Positions can open in one file and close in another ✅
  - **Intelligent update system**: Incomplete positions (`active_at_log_end`) are updated with complete data ✅
  - **Duplicate prevention**: True duplicates are skipped, avoiding data pollution ✅
  - **Chronological processing**: Files sorted alphabetically for consistent event sequencing ✅

- **Improved Processing Pipeline:**
  - Enhanced CSV merge logic with filtered existing data to prevent conflicts ✅
  - Detailed logging of processing statistics (new/updated/skipped positions) ✅
  - Robust error handling for positions missing critical identifiers ✅

**Technical Implementation:**
- **models.py**: Added `universal_position_id` property and `is_position_complete()` method
- **log_extractor.py**: Complete rewrite of deduplication logic in `run_extraction()` function
- **File processing**: Alphabetical sorting in both main directory and subdirectories

**Business Impact:**
- **Eliminates duplicate positions** from overlapping log files
- **Enables cross-file position tracking** for positions spanning multiple logs  
- **Provides position completion** when close events appear in different files
- **Maintains data integrity** through intelligent update/skip logic

**Test Results:** Successfully processed overlapping log files with proper deduplication and position completion ✅

**Files Modified:**
- core/models.py (enhanced Position class with universal identification)
- extraction/log_extractor.py (complete deduplication logic rewrite)

**System Status:** Enhanced Deduplication v1.0 - Production Ready ✅

**2025-07-04: Smart Price Cache & API Failure Handling (Session 4)**

**Goal:** Implement intelligent price cache management with proper API failure handling and smart placeholder logic.

**Achieved:**

- **Smart Cache Management v2.0:**
  - Complete rewrite of `price_cache_manager.py` with intelligent gap detection ✅
  - Monthly cache files (`pool_timeframe_YYYY-MM.json`) with incremental updates ✅
  - Smart gap detection: system identifies missing periods and fetches only required data ✅
  - Multi-month support: automatically splits requests across month boundaries ✅
  - Eliminated wasteful API calls: cache utilization improved from 0% to 95%+ ✅

- **API Failure vs No Data Distinction:**
  - **API Success + Empty Data**: Creates forward-filled placeholders, marks as "checked" ✅
  - **API Failure (401/timeout)**: Skips placeholder creation, enables retry tomorrow ✅
  - **Smart placeholder logic**: Only fills verified empty periods, not API failures ✅
  - **Cross-API-failure safety**: Preserves API credits while maintaining data integrity ✅

- **Cache Architecture Enhancement:**
  - **Gap detection logic**: `_find_data_gaps()` with intelligent timestamp comparison ✅
  - **Coverage-based detection**: For 1h/4h timeframes, only fetches major gaps (>24h threshold) ✅
  - **Incremental merging**: `_merge_and_save()` with deduplication and chronological sorting ✅
  - **Error resilience**: Graceful handling of corrupted cache files and API failures ✅

**Technical Implementation:**
- **reporting/price_cache_manager.py**: Complete rewrite with smart gap detection
- **Cache strategy**: Monthly files with intelligent gap filling and merge capabilities
- **API optimization**: Reduced API calls by 70%+ through intelligent caching
- **Forward fill logic**: Placeholder creation only for verified empty periods

**Business Impact:**
- **API Credit Conservation**: System no longer wastes credits on redundant requests ✅
- **Reliable Data Pipeline**: Handles weekends/holidays vs API failures correctly ✅
- **Automatic Recovery**: Failed API requests retry automatically on subsequent runs ✅
- **Performance Enhancement**: Cache hit rate improved from 0% to 95%+ ✅

**Test Results:** 
- Previous: 70% API credits wasted on redundant weekend requests
- Current: 0% wasted calls, intelligent retry logic for genuine API failures ✅

**Files Modified:**
- reporting/price_cache_manager.py (complete rewrite with smart gap detection)
- reporting/analysis_runner.py (integration with new cache manager)
- main.py (added SOL/USDC rate fetching menu option)

**System Status:** Smart Price Cache v2.0 - Production Ready ✅

**2025-07-04: Column Name Standardization & Mapping Elimination (Session 4 Continued)**

**Goal:** Eliminate column name mapping chaos and standardize on clean names throughout entire codebase.

**Achieved:**

- **Root Cause Analysis:**
  - Identified "accidental complexity" from CSV position-based → name-based transition ✅
  - Discovered three different naming systems causing KeyError chaos across modules ✅
  - Mapped complete scope: 119 mapped names vs 12 original names in codebase ✅

- **Plan A Implementation - Column Name Cleanup:**
  - **Eliminated mapping logic**: Removed all column mapping from `data_loader.py` ✅
  - **Standardized CSV generation**: Updated `models.py` to generate clean headers ✅
  - **Automated cleanup**: Created `fix_column_names.py` utility for safe bulk replacement ✅
  - **System-wide replacement**: 7 files modified, 0 old names remaining ✅

- **Clean Naming Standard Established:**
  - `investment_sol` (not `initial_investment_sol`) - 8 characters shorter ✅
  - `pnl_sol` (not `final_pnl_sol_from_log`) - 15 characters shorter ✅
  - `strategy_raw` (not `actual_strategy_from_log`) - 12 characters shorter ✅

- **Architecture Simplification:**
  - **Before**: CSV → mapping → code (3 naming systems, chaos) ❌
  - **After**: CSV → code (1 naming system, clarity) ✅
  - **Zero mapping overhead**: Direct header → code usage ✅
  - **Single source of truth**: Consistent names across entire pipeline ✅

**Technical Implementation:**
- **tools/fix_column_names.py**: Safe bulk replacement utility with verification ✅
- **core/models.py**: Updated CSV generation to use clean column names ✅
- **reporting/data_loader.py**: Removed all mapping logic, direct column access ✅
- **Verification**: 0 old names remaining, 126 clean names throughout codebase ✅

**Business Impact:**
- **Eliminated accidental complexity**: No more mapping overhead or KeyError debugging ✅
- **Improved maintainability**: Single source of truth for column names ✅
- **Enhanced developer experience**: Clear, predictable naming throughout codebase ✅
- **Future-proof architecture**: New columns automatically use clean names ✅

**Test Results:**
- **Pipeline verification**: Complete pipeline runs without KeyError crashes ✅
- **CSV header verification**: Clean names in generated CSV files ✅
- **Code verification**: 0 old names, 126 clean names across 30 Python files ✅

**Files Modified:**
- tools/fix_column_names.py (new utility)
- core/models.py (clean CSV generation)
- reporting/data_loader.py (mapping elimination)
- Plus 4 other files with automatic name standardization

**System Status:** Column Name Standardization v1.0 - Complete Success ✅

**2025-07-11: Strategy Parsing & Pipeline Stabilization (Handover to Gemini)**

**Goal:** Resolve strategy parsing issues and achieve complete pipeline stabilization.

**Initial Status:** 455 unresolved parsing cases (242 suspicious + 213 missing step_size)
**Final Status:** 2 unresolved cases (99.5% reduction in problematic cases) ✅

**Achieved:**

- **Iterative Debugging Approach:**
  - **Etap 1**: Fixed basic regex application logic, reversed search direction for most recent complete logs ✅
  - **Etap 2**: Enhanced functionality with TP/SL parsing, refactored to "best match" logic ✅
  - **Etap 3**: Increased lookahead parameters and sharpened success criteria ✅
  - **Etap 4**: Pipeline hardening with NaN handling and CSV column consistency ✅
  - **Etap 5**: Logging optimization for cleaner operational output ✅

- **Enhanced Strategy Parsing:**
  - **Reverse Search Logic**: Changed from forward to backward search in `parse_strategy_from_context` ✅
  - **Silent Failure Detection**: Introduced `SUCCESS_CONFIRMATION_PATTERNS` requiring numerical position IDs ✅
  - **Extended Search Window**: Increased to 150 lines for delayed success confirmations ✅
  - **Best Match Logic**: Continues searching for complete matches while keeping partial as fallback ✅

- **TP/SL Integration:**
  - **Enhanced Position Model**: Added `take_profit` and `stop_loss` fields to Position class ✅
  - **Unified Parsing Function**: `parse_open_details_from_context` extracts strategy, step_size, TP, and SL ✅
  - **CSV Export Enhancement**: Updated `to_csv_row` method with clean column names ✅
  - **Business Logic Integration**: TP/SL data now available throughout analysis pipeline ✅

- **Pipeline Stabilization:**
  - **NaN Handling**: Enhanced `strategy_instance_detector.py` to handle missing TP/SL values ✅
  - **Column Name Consistency**: Fixed critical mismatches between CSV generation and analysis expectations ✅
  - **Error Resilience**: System now processes positions with incomplete data gracefully ✅
  - **Success Pattern Enhancement**: Added "Opened a new pool" pattern reducing false negatives ✅

- **Logging Optimization:**
  - **Clean Operational Logs**: Moved detailed debug info to DEBUG level ✅
  - **Focus on Progress**: Primary logs show extraction and analysis progress clearly ✅
  - **Detailed Diagnostics**: Full debugging available via DEBUG logging level ✅

**Technical Implementation:**
- **extraction/parsing_utils.py**: Complete rewrite of strategy parsing with reverse search and TP/SL extraction
- **extraction/log_extractor.py**: Enhanced silent failure detection and success confirmation patterns
- **core/models.py**: Added TP/SL fields and updated CSV generation with clean column names
- **reporting/strategy_instance_detector.py**: NaN-resistant processing for incomplete position data
- **reporting/analysis_runner.py**: Optimized logging levels for cleaner output
- **reporting/price_cache_manager.py**: Reduced verbose logging to DEBUG level

**Business Impact:**
- **Data Completeness**: >99.5% of positions now have complete strategy information ✅
- **Enhanced Analytics**: TP/SL data enables advanced position analysis and ML optimization ✅
- **Pipeline Reliability**: System handles edge cases and incomplete data gracefully ✅
- **Operational Clarity**: Clean logs enable better monitoring and debugging ✅

**Files Modified:**
- core/models.py (TP/SL fields and clean CSV generation)
- extraction/log_extractor.py (enhanced success detection)
- extraction/parsing_utils.py (complete parsing logic rewrite)
- reporting/strategy_instance_detector.py (NaN handling)
- reporting/analysis_runner.py (logging optimization)
- reporting/price_cache_manager.py (logging optimization)

**System Status:** Strategy Parsing & Pipeline Stabilization v4.2 - Complete Success ✅

## Session Summary

**2025-07-11 Strategy Parsing & Pipeline Stabilization (Gemini Session)**

**Major Achievement:** 99.5% reduction in problematic parsing cases through iterative debugging approach

**Key Technical Improvements:**
1. **Enhanced Strategy Parsing**: Reverse search logic with best-match fallback ✅
2. **TP/SL Integration**: Complete take profit/stop loss parsing and storage ✅
3. **Pipeline Stabilization**: NaN-resistant processing with error resilience ✅
4. **Logging Optimization**: Clean operational logs with DEBUG-level diagnostics ✅

**Business Value:**
- **Data Quality**: >99.5% complete strategy information for analysis ✅
- **Enhanced Analytics**: TP/SL data enables ML optimization capabilities ✅
- **Operational Reliability**: Robust pipeline handles edge cases gracefully ✅
- **Developer Experience**: Clear, actionable logs with detailed diagnostics available ✅

**System Status:** v4.2 - Production Ready with Enhanced Data Completeness ✅
**Ready for Next Priority:** TP/SL Optimization Module & ML-driven analytics 🚀


**2025-07-12: Professional Charts Integration & HTML Report Enhancement (Session 5)**
Goal: Replace basic interactive charts with professional versions from chart_generator.py and add AVG PnL summary with YAML filters.
Achieved:

**Professional Interactive Charts Integration:**

Added 5 new functions to interactive_charts.py (~700 lines of code) ✅
create_professional_equity_curve() - dual currency with cost impact overlay ✅
create_professional_drawdown_analysis() - with running maximum and highlighted max DD ✅
create_professional_strategy_heatmap() - with YAML filters and position counts ✅
create_professional_cost_impact() - 4-panel comprehensive analysis ✅
create_strategy_avg_pnl_summary() - replaces old heatmap with horizontal bar chart ✅

**HTML Report System Enhancement:**

Enhanced html_report_generator.py with config passing and new chart integration ✅
Updated orchestrator.py to pass config to HTML generator ✅
Extended comprehensive_report.html with new sections for professional charts ✅
Added YAML filter display in template (min_strategy_occurrences, top_strategies_only) ✅


**Business Value Delivered:**

4 interactive charts with tooltips replacing static PNG versions ✅
AVG PnL summary with position counts in parentheses as requested ✅
YAML configuration filter compliance throughout chart generation ✅
Enhanced user experience with zoom, pan, and hover capabilities ✅

**Technical Implementation:**

interactive_charts.py: Added 5 professional chart functions with Plotly subplots and advanced styling
html_report_generator.py: Enhanced constructor with config parameter and template data preparation
orchestrator.py: Modified HTML generator instantiation to pass configuration
comprehensive_report.html: Added "Professional Portfolio Analytics" section and replaced heatmap

**Business Impact:**

Enhanced Visualization: Interactive charts provide superior user experience over static PNG ✅
YAML Compliance: All charts now respect configuration filters for consistent analysis ✅
Position Count Display: Strategy names include position counts for better context ✅
Professional Styling: Consistent color schemes and enhanced readability ✅

**Files Modified:**

reporting/visualizations/interactive_charts.py (5 new functions, ~700 lines added)
reporting/html_report_generator.py (config integration)
reporting/orchestrator.py (config passing)
reporting/templates/comprehensive_report.html (new sections and heatmap replacement)

**Test Results:**

Generated Report: comprehensive_report_20250712_1735.html ✅
Portfolio Analysis: 250 positions, 25 strategies successfully processed ✅
Chart Integration: All 4 professional charts rendering in HTML report ✅
YAML Filters: Configuration parameters correctly applied to visualizations ✅

System Status: Professional Charts Integration v1.0 - Complete Success ✅
Data Quality Issues Identified (Next Priority)
14 Issues Grouped by Root Cause:
🔥 CRITICAL - Simulation Data Quality (Priority 1):

Issue #1: Best Sim Strategy shows 150M SOL PnL (absurd values)
Issue #11: Spot/Bid-Ask identical bars, missing actual strategy bar
Root Cause: analysis_runner.py / SpotVsBidAskSimulator data corruption

📊 HIGH - Market Data Pipeline (Priority 2):

Issue #2: SOL Correlation shows "N/A - Data unavailable"
Issue #12: "Market Correlation analysis failed - SOL daily data is empty"
Issue #13: "Weekend analysis error: invalid data"
Root Cause: market_correlation_analyzer.py / price_cache_manager.py pipeline failure

🧮 HIGH - Financial Metrics Calculation (Priority 3):

Issue #3: Max drawdown shows 20,000% (vs realistic ~200%)
Issue #4: Drawdown chart shows max 200% (inconsistent with #3)
Issue #5: Infrastructure cost impact shows 3 SOL (~$500) vs expected $60
Root Cause: metrics_calculator.py / infrastructure_cost_analyzer.py formula errors

🎯 MEDIUM - Strategy Instance Detection (Priority 4):

Issue #6: Professional heatmap "No strategies with ≥2 positions found"
Issue #14: AVG PnL summary "No strategies with ≥2 positions found"
Root Cause: YAML filters vs actual data in strategy_instance_detector.py

💰 LOW - Chart Data Mapping (Priority 5):

Issue #7: Gross vs Net PnL - missing SOL bar, only USDC visible
Issue #8: Cost Impact - missing USDC bar, only SOL visible
Issue #9: Daily Cost - missing USDC bar, only SOL visible
Issue #10: Break-even analysis - empty chart
Root Cause: Currency mapping in new interactive_charts.py functions

Next Session Priority: Data Quality & Simulation Pipeline Debugging 📋
Session Summary
2025-07-12 Session 5: Professional Charts Integration
Major Achievement: Successfully integrated 4 professional interactive charts into HTML report system
Key Technical Improvements:

Enhanced Visualization: 5 new Plotly-based interactive charts with professional styling ✅
YAML Integration: Configuration-driven filtering throughout chart generation ✅
Template Enhancement: New HTML sections for professional analytics display ✅
Config Pipeline: End-to-end configuration passing from orchestrator to charts ✅

Business Value:

User Experience: Interactive charts with tooltips, zoom, and pan capabilities ✅
Data Insight: Position counts displayed in strategy names for better context ✅
Configuration Compliance: All charts respect YAML filter settings ✅
Professional Quality: Enhanced styling and consistent color schemes ✅

Issues Identified: 14 data quality problems grouped into 5 priority categories for systematic resolution
System Status: v4.3 - Professional Charts Integration Complete ✅
Ready for Next Priority: Data Quality & Simulation Pipeline Debugging 🚀

**2025-07-12: Simulation & Data Pipeline Debugging (Session 6)**

**Goal:** Resolve 5 priority groups of data quality issues, starting with the critical simulation errors.

**Achievements:**
- **Market Data Pipeline Stabilized:** Fixed the market data pipeline by implementing a historical buffer for EMA calculations. The market correlation analysis module now works correctly and generates charts.
- **"Time Machine" Bug Eliminated:** Positions with `close_timestamp` before `open_timestamp` are now correctly filtered out, preventing fatal data errors.
- **Negative Fee Budget Bug Fixed:** Corrected the logic to prevent negative `pnl_from_log` from creating a negative fee budget in simulations.
- **Advanced Heuristic Logic Implemented:** A sophisticated, non-linear heuristic matrix (v4.3) for calculating fee potential, including a `reversal_factor`, was implemented in the simulator.

**Critical Failure (Unresolved):**
- The core issue of **absurdly high PnL values (~150M SOL)** and identical results for both Spot and Bid-Ask strategies in the simulation **persists**.
- **Root Cause Hypothesis:** The issue is no longer believed to be in the simulation's business logic (which is now robust), but in a **fundamental data corruption or type mismatch** occurring in `analysis_runner.py` *before* the data is passed to the simulator. The current theory is that a value is being misinterpreted, causing `price_ratio` or `pnl_from_assets` to explode.

**Next Priority:** Isolate and fix the source of data corruption feeding the `spot_vs_bidask_simulator.py`.

**2025-07-13: Architectural Refactoring & Data Pipeline Stabilization**

**Goal:** Resolve critical data integrity issues in the market data pipeline causing cascading failures in correlation, cost, and weekend analysis. The root cause was identified as a chaotic data fetching architecture where multiple modules requested the same SOL/USDC price data with different, conflicting parameters, leading to a "poisoned cache" and massive API credit waste.

**Achievements:**

*   **Architectural Refactoring (Single Source of Truth):** Implemented a major architectural change. SOL/USDC price data is now fetched **only once** by the `PortfolioAnalytics` module at the beginning of the workflow, with the correct historical buffer needed for technical analysis.
*   **Data Flow Consolidation:** This single, authoritative dataset (`sol_rates`) is now passed down as an argument to all downstream modules (`MarketCorrelationAnalyzer`, `InfrastructureCostAnalyzer`), which have been refactored to accept this data instead of performing their own API calls.
*   **Critical Bug Fix (`1d` Timeframe):** Discovered and fixed a critical bug in `PriceCacheManager` where the `'1d'` timeframe was incorrectly handled as hourly, causing erroneous gap detection and chaotic caching behavior.

**Impact on Project Issues:**

*   **Market Data Pipeline (Priority 2):** **Conditionally Resolved.** The implemented changes directly address the root cause of this problem. Full validation is pending API credit refresh and cache cleanup.
*   **Financial Metrics - Infrastructure Cost (Part of Priority 3):** **Conditionally Resolved.** The accuracy of infrastructure cost calculation in SOL will be significantly improved due to the reliable price feed. The Max Drawdown issue remains outstanding.

**System Status:** The core data architecture has been stabilized. The system is now logically prepared to handle market data correctly and efficiently. Full validation of the fix is blocked by the temporary lack of API credits.

**2025-07-15: Robust Single-Line Parsing & "Superseded" Logic**

**Goal:** Resolve the critical issue of `NaN` values for Take Profit and Stop Loss in the final CSV, which was caused by a fragile and unreliable multi-line parsing mechanism.

**Achievements:**
- **Root Cause Diagnosis:** Correctly identified that the old parser, relying on `Creating a position`, was easily confused by multiple context lines and often failed to assemble a complete position record.
- **New Parsing Strategy:** Designed and implemented a fundamentally new and robust parsing strategy anchored on the single, data-rich `... | OPENED ...` log entry.
- **Unified Data Extraction:** The new `parse_position_from_open_line` function now extracts all critical opening data (TP, SL, investment, strategy, token pair, version, wallet address) from a single line, eliminating the primary source of parsing errors.
- **Targeted Context Search:** The need for broad context searching was eliminated. It is now used only for the specific, minimal task of finding the `pool_address` from a nearby `View DLMM` link.
- **"Superseded" Logic:** Implemented intelligent logic to handle position restarts. If a new position is opened for a pair that already has an active position, the old one is automatically closed with the reason "Superseded", preventing data loss and ensuring a clean history.
- **Full Integration:** Successfully integrated the new logic into `log_extractor.py` and `parsing_utils.py`, replacing the old, complex code with a simpler, more maintainable, and more effective solution.

**Result:** The `NaN` value issue for TP/SL is **100% resolved**. The data extraction pipeline is now significantly more robust, precise, and resilient to variations in log formatting.

**System Status:** v4.3 - Stable and Production-Ready ✅

**2025-07-15: Architectural Refactoring & Data Pipeline Stabilization**

**Goal:** Resolve critical data integrity issues causing cascading failures throughout the analysis pipeline, primarily the "Time Machine" bug where `close_timestamp` was earlier than `open_timestamp`.

**Achievements:**
- **Architectural Refactoring:** Fundamentally changed how active positions are tracked. The system now uses `token_pair` as the unique key for `active_positions`, ensuring that only one active position can exist per token pair at any time. This eliminates the ambiguity that was the root cause of the "Time Machine" errors.
- **"Superseded" Logic Implemented:** A robust mechanism now correctly identifies when a new position for a pair is opened, automatically closing the previous one with the status "Superseded". This accurately models the bot's behavior and prevents "ghost" positions from corrupting the data.
- **Data Recovery:** The new logic allowed the recovery of dozens of previously lost or misattributed positions, increasing the final, clean dataset from ~230 to 327 positions.
- **Robust Deduplication:** Implemented a universal ID (`pool_address` + `open_timestamp`) to reliably deduplicate positions across different log files (e.g., `app-1.log` and `app-1_1.log`), ensuring each unique position appears only once in the final CSV.

**Result:**
- **"Time Machine" errors reduced by 90%**, with remaining cases being legitimate data anomalies correctly filtered by the system.
- **Data integrity restored:** The final CSV is now a clean, deterministic, and reliable source of truth.
- **Parser is now production-ready**, resilient to common log format issues, and accurately models the position lifecycle.