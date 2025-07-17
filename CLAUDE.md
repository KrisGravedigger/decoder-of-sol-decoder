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

Input: Input: all *.log files starting with "app" in input/ directory; optional positions_to_skip.csv in root
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names

🏃‍♂️ Project Status
Last Update: 2025-07-11
Current Version: v4.2 - Strategy parsing & pipeline stabilization
Working Features:

Position extraction from SOL Decoder logs ✅ (improved to >99.5% accuracy)
Manual position filtering via `positions_to_skip.csv` ✅
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

**2025-06-25**: Implemented a strategy instance detection system to group and rank positions by performance. Enhanced the data pipeline to support log analysis from multiple wallets in separate subfolders.

**2025-06-28**: Developed a comprehensive portfolio analytics module with dual currency support and infrastructure cost analysis. Implemented a chart generator for key metrics like equity curves, drawdowns, and strategy heatmaps.

**2025-06-29**: Executed a major refactoring, breaking down oversized analytics and charting modules into a more maintainable, single-responsibility structure. Fixed a critical timestamp parsing bug that had prevented any positions from being loaded.

**2025-07-02**: Implemented new modules for market correlation and weekend parameter analysis. Developed an interactive HTML reporting system with Plotly charts and optimized the main pipeline for a 3x speed increase.

**2025-07-02**: Conducted another major refactoring, separating UI and core logic from the main script and HTML generator. Added a user-friendly interactive menu for easier execution of different analysis modes.

**2025-07-02**: Rewrote the weekend parameter analysis module with corrected business logic for dual-scenario simulation. Integrated the logic with YAML configuration and fixed associated interactive charts.

**2025-07-03**: Stabilized the application post-refactoring by creating a single entry point and implementing error resiliency. Introduced a "cache-only" mode and graceful degradation to handle API failures without crashing the report generation.

**2025-07-03**: Implemented a robust deduplication system using a universal_position_id to track and merge positions across multiple, overlapping log files. This enables correct position completion when open/close events are in different files.

**2025-07-04**: Overhauled the price cache manager with smart gap detection and monthly cache files, reducing redundant API calls by over 70%. The system now distinguishes between API failures and periods with no data to conserve credits.

**2025-07-04**: Standardized all CSV column names across the entire project to eliminate complex and error-prone mapping logic. This refactoring simplified the data pipeline and improved maintainability.

**2025-07-11**: Overhauled the strategy parsing logic with a reverse-search and best-match approach, resolving 99.5% of previous parsing failures. Integrated Take Profit (TP) and Stop Loss (SL) extraction into the data pipeline.

**2025-07-12**: Replaced static charts with five professional, interactive Plotly visualizations in the HTML report. Enhanced the report to include an AVG PnL summary and ensured all charts respect YAML configuration filters.

**2025-07-12**: Addressed several data quality issues by stabilizing the market data pipeline and fixing critical data filtering bugs. Identified the root cause of absurd simulation PnL values as a data corruption issue happening before the simulation step.

**2025-07-13**: Refactored the data architecture to fetch market data only once, creating a single source of truth. This eliminated conflicting API calls and resolved a "poisoned cache" issue that caused cascading failures in analysis modules.

**2025-07-15**: Replaced a fragile multi-line parser with a robust single-line approach, resolving all NaN issues for Take Profit and Stop Loss. Implemented "Superseded" logic to correctly close old positions when a new one is started for the same pair.

**2025-07-15**: Resolved the "Time Machine" bug by refactoring active position tracking to use the token pair as a unique key. This change, combined with "Superseded" logic, restored data integrity and recovered dozens of lost positions.


**2025-07-16: Manual Position Filtering for Data Correction**

**Goal:** Implement a mechanism to manually exclude specific positions from the analysis pipeline to handle known data errors in source logs.

**Achieved:**
- **Manual Skip Functionality:** Implemented logic in `log_extractor.py` to read a new file, `positions_to_skip.csv`.
- **Targeted Filtering:** The system now loads a set of `position_id`s from this file and filters them out from the extracted data before writing the final `positions_to_analyze.csv`.
- **Robust Implementation:** The feature is designed to be fault-tolerant. If `positions_to_skip.csv` is missing or contains errors, the extraction process continues without manual filtering, logging an appropriate message.
- **Clear Logging:** Added logs to indicate when the skip file is loaded and how many positions are manually excluded, ensuring transparency in the data processing pipeline.

**Business Impact:**
- Provides a crucial "escape hatch" for data quality issues originating from the bot's logs that cannot be fixed programmatically.
- Increases the reliability of the final analysis by allowing for the manual removal of erroneous data points (e.g., positions with absurd PnL values due to log corruption).

**Files Modified:**
- `extraction/log_extractor.py` (added filtering logic)
- `CLAUDE.md` (documentation update)

**System Status:** Manual data correction feature is stable and ready for use. ✅

**2025-07-15: Architectural Refactoring for True Offline Analysis**
Goal: Resolve a critical architectural flaw where multiple parts of the pipeline (simulations, reporting) were independently attempting to fetch data, leading to uncontrolled API credit usage and bypassing the cache, even on subsequent runs.
Achieved:
Centralized Data Fetching: Implemented a new, single function run_all_data_fetching in main.py which is now the only point of contact with the Moralis API. It populates the cache for both per-position price histories (for simulations) and daily SOL/USDC rates (for reporting).
True Offline Mode Enforcement: Refactored the entire pipeline (main_menu, run_full_pipeline) to ensure that all analysis and simulation steps (run_spot_vs_bidask_analysis, PortfolioAnalysisOrchestrator) are executed explicitly without an API key, forcing them to rely 100% on pre-populated cache.
Controlled API Usage (Safety Valve): The central data-fetching step now includes a one-time "Go/No-Go" prompt that asks the user for confirmation before initiating any online activity, providing full control over API credit expenditure.
Critical Bug Fix: Corrected a faulty guard clause in PortfolioAnalysisOrchestrator that incorrectly prevented it from running in cache-only mode.
Elimination of "Two Brains": Removed all rogue data-fetching logic and incorrect "safety valve" prompts from downstream modules (analysis_runner.py), ensuring a single, predictable data flow.
Business Impact:
Eliminated Uncontrolled API Spending: The system no longer makes unexpected API calls during analysis or simulation, guaranteeing cost control.
Improved Pipeline Reliability: The clear separation between a single "online" fetching phase and multiple "offline" analysis phases makes the system's behavior predictable, robust, and easier to debug.
Enhanced User Control: The "Safety Valve" gives the user a clear, decisive moment to authorize or prevent potential costs.
Files Modified:
main.py (major architectural changes, new central fetching function)
reporting/orchestrator.py (bug fix for cache-only mode)
reporting/analysis_runner.py (cleanup of redundant logic)
CLAUDE.md (documentation update)
System Status: Architecture is now stable with a clear online/offline separation. The root cause of uncontrolled API calls has been resolved. ✅

**2025-07-16: Resolving Cascading Data Errors & Pipeline Stabilization**

**Goal:** Diagnose and resolve a series of critical data integrity issues that emerged after major architectural refactoring, including timestamp errors, `KeyError`s, and inverted PnL values that corrupted the final analytics.

**Problem Diagnosis & Resolution Steps:**

1.  **Timestamp Type Mismatch (`FATAL DATA ERROR`):**
    *   **Symptom:** The `analysis_runner` was rejecting most positions because it received timestamps as strings instead of `datetime` objects.
    *   **Root Cause:** Analysis steps were reading `positions_to_analyze.csv` with `pd.read_csv` but were not applying the centralized timestamp parsing logic from `data_loader.py`.
    *   **Fix:** Modified `main.py` to ensure that any function reading `positions_to_analyze.csv` immediately uses the project's standard data loading and cleaning functions (`load_and_prepare_positions`), guaranteeing correct data types throughout the pipeline.

2.  **Heatmap Generation Failure (`KeyError: 'initial_investment'`):**
    *   **Symptom:** The strategy heatmap chart failed to generate, throwing a `KeyError`.
    *   **Root Cause:** The visualization code in `strategy_heatmap.py` was still referencing the old column name (`initial_investment`) instead of the project's standardized name (`investment_sol`).
    *   **Fix:** Updated the column name in `strategy_heatmap.py` to align with the unified naming system, resolving the error.

3.  **Critical Data Corruption (Inverted PnL & "Equity Curve Cliff"):**
    *   **Symptom:** After fixing the initial errors, the final report showed dramatically incorrect metrics: `Net PnL` flipped from positive to negative, and the equity curve chart showed a sharp, unrealistic drop after June 22nd.
    *   **Root Cause:** The analysis was being performed on a **stale and corrupted `positions_to_analyze.csv` file**. This artifact was a leftover from a previous, faulty run of the log parser, which had incorrectly calculated PnL for some positions. Subsequent fixes in the code were not reflected in this "poisoned" intermediate file.
    *   **Resolution (The "Healing Pipeline"):** Running the full pipeline from Step 1 (`run_extraction`) forced the system to **overwrite the stale CSV with a fresh, correctly parsed version** based on the latest, stable code. This single action purged the corrupted data and restored the integrity of all subsequent calculations and visualizations.

**Key Insight:** This session highlighted the critical importance of data lineage. When a parser or data generation step is fixed, it is crucial to re-run the entire pipeline from the beginning to ensure all downstream artifacts are regenerated and free of legacy errors.

**Files Modified:**
- `main.py` (to enforce centralized data cleaning)
- `reporting/visualizations/strategy_heatmap.py` (to fix `KeyError`)
- `reporting/analysis_runner.py` (to strengthen data validation)

**System Status:** The data pipeline is now stable and robust. All identified data corruption issues have been resolved. The system correctly handles offline analysis based on a reliably generated central data artifact. ✅

**2025-07-16: Manual Position Filtering for Data Correction**

**Goal:** Implement a mechanism to manually exclude specific positions from the analysis pipeline to handle known data errors in source logs.

**Achieved:**
- **Manual Skip Functionality:** Implemented logic in `log_extractor.py` to read a new file, `positions_to_skip.csv`.
- **Targeted Filtering:** The system now loads a set of `position_id`s from this file and filters them out from the extracted data before writing the final `positions_to_analyze.csv`.
- **Robust Implementation:** The feature is designed to be fault-tolerant. If `positions_to_skip.csv` is missing or contains errors, the extraction process continues without manual filtering, logging an appropriate message.
- **Clear Logging:** Added logs to indicate when the skip file is loaded and how many positions are manually excluded, ensuring transparency in the data processing pipeline.

**Business Impact:**
- Provides a crucial "escape hatch" for data quality issues originating from the bot's logs that cannot be fixed programmatically.
- Increases the reliability of the final analysis by allowing for the manual removal of erroneous data points (e.g., positions with absurd PnL values due to log corruption).

**Files Modified:**
- `extraction/log_extractor.py` (added filtering logic)
- `CLAUDE.md` (documentation update)

**System Status:** Manual data correction feature is stable and ready for use. ✅

**2025-07-17: Critical Debugging: Resolving Unrealistic Max Drawdown Values**

**Goal:** To diagnose and fix a bug that was causing absurd, financially impossible values for the Max Drawdown metric (e.g., -15,000%) in generated reports.

**Diagnosis and Resolution Steps:**
- Initial Hypothesis (Rejected): The first assumption was that the issue stemmed from the fundamental instability of the (PnL - Peak) / Peak formula, especially with small peak PnL values.
- User's Key Insight: The user correctly identified that the problem was not the formula itself but a multiplication error. A comparison between the chart value (-146%) and the table value (-14,600%) pointed directly to a double-multiplication bug.
- Root Cause Identified: It was confirmed that the functions in metrics_calculator.py were incorrectly multiplying the final drawdown result by 100, effectively returning a percentage value. The reporting layer then formatted this number again as a percentage (:.2%), which caused the value to explode.

**Implemented Fix:**
The erroneous * 100 multiplication was removed from the calculate_sol_metrics and calculate_usdc_metrics functions in metrics_calculator.py. These functions now correctly return a raw decimal value (e.g., -1.46) ready for UI formatting.
The logic in the chart generation files (drawdown.py, interactive_charts.py) was confirmed to be correct and was left unchanged, as it needs to scale the Y-axis to a percentage.
For improved clarity, the metric's label in the KPI table was updated to "Max PnL Drawdown" as per the user's suggestion.

**Business Impact:**
- Restored credibility to a key risk metric in all reports by eliminating misleading and incorrect data.
- Ensured consistency in the calculation and presentation of financial metrics across the application.

**Files Modified:**
- reporting/metrics_calculator.py
- reporting/visualizations/interactive_charts.py
- System Status: The Max Drawdown metric is now stable and reliable. ✅