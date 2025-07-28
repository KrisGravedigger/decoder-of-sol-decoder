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
│   └── models.py               # Position class and other data models
├── data_fetching/              # NEW: All data fetching and orchestration logic
│   ├── __init__.py
│   ├── cache_orchestrator.py   # NEW: Manages OCHLV cache (menus, validation)
│   ├── enhanced_price_cache_manager.py # NEW: Core OCHLV+Volume cache logic
│   └── main_data_orchestrator.py # NEW: Manages main report data fetching
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
│   │   ├── interactive/          # NEW: Interactive chart modules
│   │   │   ├── __init__.py       # NEW: Re-exports all chart functions
│   │   │   ├── market_charts.py  # NEW: Correlation, EMA Trend charts
│   │   │   ├── portfolio_charts.py # NEW: KPI, Equity Curve, Drawdown, Cost charts
│   │   │   ├── simulation_charts.py# NEW: Weekend, Strategy Sim charts
│   │   │   └── strategy_charts.py  # NEW: Heatmap, AVG PnL charts
│   │   └── strategy_heatmap.py
│   ├── orchestrator.py         # Core logic engine for the reporting workflow
│   ├── analysis_runner.py      # Runs Spot vs. Bid-Ask simulation for all positions
│   ├── data_loader.py          # Position data loading and cleaning (no mapping logic)
│   ├── fee_simulator.py        # NEW: Simulates fee allocation for post-close periods
│   ├── html_report_generator.py # HTML report generation orchestrator
│   ├── infrastructure_cost_analyzer.py # Daily cost allocation and Moralis API
│   ├── lp_position_valuator.py # NEW: Calculates LP position value with IL formulas
│   ├── market_correlation_analyzer.py  # Analysis of portfolio vs market correlation
│   ├── metrics_calculator.py   # Financial metrics calculation
│   ├── post_close_analyzer.py  # NEW: Engine for "what-if" TP/SL analysis
│   ├── strategy_instance_detector.py # Groups positions into strategy instances
│   ├── text_reporter.py        # Text report generation
│   └── price_cache_manager.py  # Smart price caching with gap detection and API failure handling
├── simulations/                # "What-if" simulation engines
│   ├── spot_vs_bidask_simulator.py # Simulates Spot vs Bid-Ask strategies
│   └── weekend_simulator.py    # Simulates weekend parameter impact
├── tools/                      # Developer and utility tools
│   ├── __init__.py
│   ├── cache_debugger.py       # NEW: Debugging tools for the enhanced cache                # Developer and utility tools
│   ├── api_checker.py          # Checks Moralis API connectivity
│   ├── debug_analyzer.py       # Context analysis and export system
│   └── fix_column_names.py     # Column name standardization utility
└── utils/                      # NEW: Shared helper functions
    ├── __init__.py
    └── common.py               # NEW: Houses print_header, load_main_config, etc.

File Handling Rules

Input: Input: all *.log files starting with "app" in input/ directory; optional positions_to_skip.csv in root
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names

🏃‍♂️ Project Status
Last Update: 2025-07-17
Current Version: v4.4 - Strategy parsing & pipeline stabilization
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

- **Modular Chart Generation**: Decoupled the monolithic interactive chart module into four smaller, specialized modules (`portfolio`, `strategy`, `market`, `simulation`) for improved maintainability and adherence to the 600-line file limit. ✅

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

**Architecture Refactoring & Pragmatic Cache Management:**
- **Centralized Logic**: Refactored `main.py` by moving complex logic into dedicated modules (`data_fetching`, `tools`, `utils`), making it a clean entry point ✅
- **Circular Import Resolution**: Eliminated all circular import errors by creating a shared `utils.common` module for helper functions, stabilizing the architecture ✅
- **Pragmatic Cache Rule ("2-Day Rule")**: Implemented an automatic, time-based rule to stop fetching data for old, incomplete positions, preventing wasted API calls on unfixable data gaps ✅
- **Smart OCHLV Fetching**: OCHLV cache population now supports "Fill Gaps" and "Force Refetch" modes, giving the user full control while defaulting to the most efficient strategy ✅

**TP/SL Optimizer (Phase 3B):**
- Post-close analysis engine with "what-if" simulation capabilities ✅
- LP position valuation with impermanent loss and fee calculations ✅
- Volume-proportional fee simulation based on historical position performance ✅
- Configurable scope filtering for targeted analysis ✅
- Robust handling of missing data for individual positions ✅
- Generation of text reports and statistical summaries for optimization analysis ✅
- Export of preliminary ML-ready datasets with post-close features ✅

**TP/SL Range Testing (Phase 4A):**
- **In-place Data Enrichment:** `strategy_instance_detector` now enriches the main `positions_to_analyze.csv` with a `strategy_instance_id`, creating a single source of truth for all analyses. ✅
- **Range Simulation Engine:** A new `TpSlRangeSimulator` tests a user-defined grid of TP/SL values against all historical positions. ✅
- **Per-Strategy Heatmaps:** The HTML report now includes interactive heatmaps showing PnL results for each major strategy instance, allowing for visual identification of optimal parameter regions. ✅
- **Optimal Settings Reporting:** The report includes summary tables that explicitly state the best-performing TP/SL combination found for each strategy. ✅
- **Detailed Data Export:** The simulation process generates detailed and aggregated result files (`range_test_detailed_results.csv`, `range_test_aggregated.csv`) for further analysis and as a foundation for Phase 4B. ✅

**Interactive "What-If" Tool (Phase 4B):**
- **Dynamic Frontend Analysis:** A new, purely client-side tool (HTML/JS) is integrated into the report, allowing for real-time exploration of simulation data without backend calls. ✅
- **Efficient Data Backend:** The tool is powered by a single, enriched JSON object created by merging three data artifacts (`range_test_results`, `positions`, `strategy_instances`) in the Python backend. ✅
- **Advanced Interactive Filtering:** Users can dynamically filter the "what-if" analysis by:
    - Date range (`open_timestamp`).
    - Minimum number of positions per strategy. ✅
- **Smart TP/SL Matching:** The tool uses a Euclidean distance algorithm to find the closest pre-calculated TP/SL result from the simulation grid, providing intuitive and accurate responses to user input. ✅
- **Real-Time UI Updates:** The results table, including PnL, win rate, and exit reason breakdowns, updates instantly as the user adjusts any filter. ✅

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
- **TP/SL Range Testing (Phase 4):** Implement a framework to simulate and test ranges of TP/SL values to find optimal combinations. 📋
- **Post-exit analysis**: forward-looking profitability analysis beyond historical close points ✅ COMPLETED IN PHASE 3B

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

ML & Advanced Analytics:
  - ML-driven TP/SL level optimization (Phase 5) 📋
  - Post-exit analysis (forward-looking candle testing) ✅ COMPLETED IN PHASE 3B
  - Precise fee calculations per-candle 📋

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

**2025-07-18: Market Trend Visualization & Report Simplification**

**Goal:** Enhance the market trend analysis section with a more intuitive visualization of the EMA-based trend logic, and simplify the report by removing redundant or less valuable charts.

**Achieved:**
- **Visual Trend Indicator Chart:** Implemented a new, interactive chart in the Market Correlation section that plots the SOL price against its 50-period EMA.
  - The EMA line is **dynamically colored** (green for uptrend, red for downtrend) to provide an intuitive, visual confirmation of the trend detection logic used in the analysis.
  - This makes it much easier to understand *why* certain days are classified as uptrend or downtrend.
- **Unified Trend Colors:** Standardized the color scheme across all three trend-based bar charts (`Avg Return`, `Win Rate`, `Days Count`) to consistently represent uptrends (green) and downtrends (red), improving readability and at-a-glance comprehension.
- **Simplified Weekend Analysis:** Streamlined the `Weekend Parameter Impact Comparison` chart by removing the 'Sharpe Ratio' metric. This focuses the analysis on the more direct impact on `Total PnL` and `Average ROI (%)`.
- **Report Decluttering:** Completely removed the 'Legacy Strategy Heatmap (Fallback)' section and its corresponding generation logic. This declutters the final report and eliminates a redundant visualization, making the primary `Strategy Performance Summary` the single source of truth.

**Files Modified:**
- `reporting/visualizations/interactive_charts.py`
- `reporting/html_report_generator.py`
- `reporting/templates/comprehensive_report.html`

**System Status:** Report visualizations are enhanced and simplified. All changes are stable. ✅

**2025-07-19: Refactoring of Interactive Chart Module**

**Goal:** To refactor the oversized `interactive_charts.py` file (over 800 lines) into smaller, thematic modules to improve maintainability, and to remove obsolete chart functions, adhering to the project's 600-line file limit convention.

**Achieved:**
- **Decomposition:** The monolithic `interactive_charts.py` was successfully decomposed into four new, specialized modules: `portfolio_charts.py`, `strategy_charts.py`, `market_charts.py`, and `simulation_charts.py`.
- **New Structure:** A new directory `reporting/visualizations/interactive/` was created to house the new modules, improving project organization.
- **Simplified Interface:** An `__init__.py` file was added to the new directory to re-export all chart functions, ensuring that the consuming `html_report_generator.py` only required a minimal import path change and no changes to its function calls.
- **Code Pruning:** Two obsolete and unused functions (`create_equity_curve_chart`, `create_strategy_heatmap_chart`) were identified and completely removed, reducing dead code.
- **Pipeline Consistency:** All related files (`html_report_generator.py`, `comprehensive_report.html`) were updated to reflect the new structure and removal of old functions.

**Business Impact:**
- **Improved Maintainability:** Developers can now quickly locate and modify a specific chart's logic without navigating a massive file.
- **Enhanced Readability:** The smaller, focused modules are easier to understand and debug.
- **Adherence to Conventions:** The project now complies with the established 600-line file limit rule, ensuring long-term code health.

**Files Modified/Created/Deleted:**
- **Deleted:** `reporting/visualizations/interactive_charts.py`
- **Created:** `reporting/visualizations/interactive/` (and all 5 files within)
- **Modified:** `reporting/html_report_generator.py`, `reporting/templates/comprehensive_report.html`, `CLAUDE.md`

**System Status:** Refactoring is complete. The new modular chart generation system is stable and operational. ✅

**2025-07-17: Critical Data Fix: Resolving Gaps in SOL/USDC Market Price Data**

**Goal:** To diagnose and permanently fix missing data points for SOL/USDC market prices (specifically for July 5th, 8th, and 9th), which were causing a flat line in the EMA trend chart and visual gaps in other analytics.

**Diagnosis and Resolution Steps:**

1.  **Symptom & Initial Feature (Cache Repair Mechanism):** The initial symptom was incomplete charts. The first step was to build a "cache repair" mechanism, assuming the cache had stored empty data from a previous API failure. This involved:
    *   Implementing a `force_refetch` flag in `price_cache_manager.py` to ignore existing placeholders.
    *   Adding a user-facing sub-menu in `main.py` under "Step 3: Fetch/Update Data", giving the user full control to trigger a standard fetch, a full force refetch, or a targeted refetch for SOL/USDC data only.
    *   Propagating the `force_refetch` flag through `analysis_runner.py` and `infrastructure_cost_analyzer.py` to ensure it reaches the cache manager.

2.  **Root Cause Identification:** When the new `force_refetch` mode still failed to retrieve data, it became clear the problem wasn't the cache, but the API query itself. Using a diagnostic script (`tools/debug_sol_price_fetcher.py`) and user-provided documentation, we identified the root cause: the system was querying the wrong asset address for market-wide SOL/USDC prices. It was using a specific, low-liquidity pool address instead of a canonical, high-liquidity pair address recognized by the API.

3.  **Verification & Final Fix:** The diagnostic script confirmed that the Raydium USDC/SOL pair address (`83v8iPyZihDEjDdY8RdZddyZNyUtXngz69Lgo9Kt5d6d`) returned a complete dataset. The final fix was to update `infrastructure_cost_analyzer.py` to use this correct, hardcoded pair address for all SOL/USDC price history requests.

**Key Outcomes:**
- The SOL/USDC market data pipeline is now robust and fetches complete, accurate historical data, resolving the core issue of missing data points.
- The EMA Trend indicator chart now displays correctly without flat-lining.
- The project now has a powerful, user-controlled cache repair mechanism to handle potential future API data inconsistencies without code changes.

**Files Modified:**
- `main.py` (added data fetching sub-menu and logic for `refetch_mode`)
- `price_cache_manager.py` (implemented core `force_refetch` logic)
- `reporting/analysis_runner.py` (updated to accept and pass the `force_refetch` flag)
- `reporting/infrastructure_cost_analyzer.py` (updated to use the correct SOL/USDC pair address and pass the `force_refetch` flag; removed rogue `basicConfig` call)

**System Status:** The market data pipeline is now stable, and the data integrity issue is fully resolved. ✅


**2025-07-22: TP/SL Optimizer Phase 1 Implementation (80% Complete)**

**Goal:** Implement Phase 1 of TP/SL Optimizer Module - Data Infrastructure with OCHLV+Volume support and offline-first approach.

**Achieved:**
- **EnhancedPriceCacheManager Implementation:** Created new cache manager extending existing PriceCacheManager with volume data support, raw OCHLV cache structure (`price_cache/raw/YYYY-MM/`), and interactive API fallback with user control.
- **Main Menu Integration:** Added comprehensive cache validation menu (option 6) with 5 specialized functions for cache management, validation, volume analysis, and debugging.
- **Cross-Month Data Handling:** Successfully implemented cross-month position support for positions spanning multiple months (June→July 2025), resolving initial single-month limitation.
- **Cache Architecture:** Established parallel cache system with raw OCHLV+Volume data alongside existing processed cache, maintaining full backward compatibility.
- **Volume Data Collection:** Successfully tested with 18 positions, collecting OCHLV+Volume data from Moralis API with proper rate limiting and monthly organization.
- **Time Coverage Tolerance:** Implemented candle alignment tolerance (1-hour) to handle real-world timing discrepancies between position start/end and API candle boundaries.

**Critical Issues Identified & Partially Resolved:**
- **Cache Detection Inconsistency:** Different functions (validation vs fetch) use different algorithms for cache checking, leading to conflicting results where validation shows "Complete" but cache-only mode fetches from API.
- **Function Synchronization:** Successfully updated `fetch_ochlv_data()` to use same cache loading logic as validation functions, but synchronization still incomplete across all code paths.
- **Cross-Month Boundary Handling:** Initially positions spanning months only checked first month cache - resolved by implementing `_load_raw_cache_for_period()` with proper month spanning.

**Current Status:**
- **Data Collection:** ✅ Working (18/18 positions successfully cached)
- **Volume Extraction:** ✅ Working (all positions return volume arrays)
- **Cache Structure:** ✅ Working (proper raw cache organization)
- **Cache-Only Mode:** 🔄 Partially working (~50% positions still prompt for API despite having cache)

**Technical Achievements:**
- Maintained API rate limiting (0.6s between requests) and existing PriceCacheManager compatibility
- Interactive Polish prompts for cache-only mode with user control over API usage
- Comprehensive debugging system with cache location analysis and validation reporting
- Enhanced timeframe determination using existing project algorithms

**Files Modified:**
- **Created:** `reporting/enhanced_price_cache_manager.py` (main new functionality)
- **Modified:** `main.py` (added cache validation menu and 5 new functions)
- **Integration:** `reporting/analysis_runner.py` (added use_cache_only parameter)

**Next Session Priority:** Resolve cache detection synchronization to ensure cache-only mode works 100% consistently for all positions. Issue appears to be in `_fetch_missing_data_cross_month()` function implementation or cache checking algorithm differences between validation and fetch operations.

**Business Impact:** Phase 1 data infrastructure is functionally complete and ready for Phase 2 (Post-Position Analysis) once cache synchronization issues are resolved. The offline-first approach and volume data collection successfully established foundation for ML-driven TP/SL optimization.

**2025-07-23: Architecture Refactoring & Pragmatic Cache Management**

**Goal:** To resolve critical architectural issues (circular imports), clean up the main entry point, and implement a pragmatic, cost-effective caching system for the OCHLV+Volume data required by the TP/SL Optimizer.

**Achieved:**
- **Major Code Refactoring:** Decomposed the oversized `main.py` by moving all orchestration and debugging logic into new, dedicated modules: `data_fetching/cache_orchestrator.py`, `data_fetching/main_data_orchestrator.py`, and `tools/cache_debugger.py`.
- **Created Shared Utilities Module:** Established a new `utils/common.py` module for shared helper functions (`print_header`, `load_main_config`), completely resolving all circular import errors and solidifying the project's architecture.
- **Implemented "Pragmatic Cache Rule":** Instead of a complex state management system, a simple and effective "2-Day Rule" was implemented. The system now automatically avoids trying to "fix" incomplete cache data for any position that was closed more than two days ago, preventing wasted API credits on permanent data gaps.
- **Developed Smart Fetching Modes:** The OCHLV cache orchestrator now provides two modes: "Fill Gaps Only" (the default, which skips complete and old-incomplete positions) and "Force Refetch All", giving the user full control over the data fetching process.
- **Unified Cache Validation:** The logic for validating cache completeness is now consistent across all analysis and debugging functions, eliminating user confusion.

**2025-07-24: TP/SL Optimizer Phase 2 Implementation - Integration & Offline-First Analysis**
**Goal:**  Complete the integration of the new OCHLV+Volume cache system with the existing analysis pipeline to enable fully offline analysis after initial data fetching.
**Achieved:**
- **3-Tier Cache System Implementation:** Successfully deployed offline_processed/ cache layer that converts raw OCHLV data to simple price format compatible with existing simulations. Cache priority chain: offline_processed/ → raw/ generation → processed/ → API fallback.
- **Config-Driven Offline-First Behavior:** Added comprehensive data_source section to portfolio_config.yaml controlling prefer_offline_cache, interactive_gap_handling, and auto_generate_offline preferences.
- **Interactive Gap Resolution:** Implemented sophisticated 6-option user choice system for incomplete data (partial/fallback/skip data + "apply to all" variants) with session memory to handle real-world data gaps gracefully.
- **Smart Menu Enhancement:** Added dynamic mode indicators showing (Online/Offline/Hybrid) in main menu based on config preferences and API key availability, improving user experience and system transparency.
- **Enhanced Cache Management:** Extended cache management menu (option 6) with offline cache refresh and validation options, providing users with full control analogous to existing raw cache management.
- **Pure Offline Validation:** Confirmed that Steps 4-5 (simulations + reports) run completely offline after Step 3 data fetching, eliminating API dependency for analysis iterations.
- **Zero Breaking Changes:** Maintained complete backward compatibility - all existing functionality preserved while adding new offline-first capabilities.

**Technical Architecture:**

Extended PriceCacheManager with config integration, interactive gap handling methods, and offline cache generation logic
Updated AnalysisRunner and PortfolioAnalysisOrchestrator constructors to accept and pass config parameters
Enhanced main.py with smart labeling logic and offline cache management menu options
Implemented comprehensive error handling and user guidance for offline operational scenarios

**Business Impact:**
API Cost Control: Users can now run unlimited analysis iterations after initial data collection without ongoing API credit consumption
System Reliability: Complete offline capability ensures continuous analysis even during API outages or rate limiting
Enhanced User Experience: Interactive gap handling provides users with full control over data quality vs analysis coverage trade-offs
ML Foundation: Robust offline data infrastructure established for future ML-driven TP/SL optimization with guaranteed data availability

**Files Modified:**
reporting/config/portfolio_config.yaml (added data_source section)
reporting/price_cache_manager.py (major extensions for offline cache logic)
reporting/analysis_runner.py (config integration)
reporting/orchestrator.py (config parameter passing)
main.py (smart menu labels and cache management)

**System Status:** Phase 2 complete. The TP/SL Optimizer now provides robust offline-first analysis capabilities. Foundation established for Phase 3 - Post-Position Analysis. ✅

**2025-07-26: TP/SL Optimizer Phase 3A Implementation & Debug**
**Goal:** Implement log-based peak PnL extraction as foundation for TP/SL optimization analysis.
**Achieved:**
**Position Model Extension:** Added 3 new fields to Position class:
- max_profit_during_position - Maximum % profit during position lifetime
- max_loss_during_position - Maximum % loss during position lifetime
- total_fees_collected - Total fees collected in SOL
**Peak PnL Extraction Logic:** Implemented extract_peak_pnl_from_logs() and extract_total_fees_from_logs() functions in parsing_utils.py with regex pattern matching for "SOL (Return: X%)" and fee calculation formulas
**Selective Analysis Logic:** Smart extraction based on close_reason - TP positions extract max_loss only, SL positions extract max_profit only, others extract both
Configuration Integration: Added tp_sl_analysis section to portfolio_config.yaml with configurable significance_threshold and scope filters for future Phase 3B
**Parser Integration:** Modified log_extractor.py to automatically extract peak PnL during position closing with config-driven thresholds
**Backfill Utility:** Created tools/backfill_peak_pnl.py for one-time processing of existing positions in CSV
**Debug Resolution:** Fixed LogParser AttributeError by implementing missing _load_config() method using proven pattern from orchestrator.py

**Technical Implementation:**
CSV structure extended with 3 new columns while maintaining backwards compatibility
Configuration-driven significance threshold (0.5% default) eliminates hardcoded values
Fee extraction uses formula: "Claimed: X SOL" + ("Y SOL (Fees Tokens Included)" - "Initial Z SOL")
Performance optimized: searches only between open_line_index and close_line_index
Optional fields ensure no breaking changes to existing pipeline

**Business Impact:**
Establishes solid foundation for ML-driven TP/SL optimization in Phase 3B
Provides real historical peak PnL data for "what-if" analysis scenarios
Enables identification of positions that could benefit from different TP/SL levels
Cost-efficient one-time log parsing avoids repeated scanning for analysis

**Files Modified:**
core/models.py (Position class extension)
extraction/parsing_utils.py (peak PnL extraction functions)
extraction/log_extractor.py (parser integration and config loading)
reporting/config/portfolio_config.yaml (tp_sl_analysis configuration)

**Files Created:**
tools/backfill_peak_pnl.py (utility for existing positions)

**System Status:** Phase 3A complete and stable. Peak PnL extraction working correctly with configurable parameters. Foundation established for Phase 3B - Post-Close Analysis. ✅
2025-07-26: Mathematical Foundation Research
**Goal:** Establish mathematical framework for LP position valuation in Phase 3B implementation.
Achieved:

**LP Position Valuation Framework:** Comprehensive research into liquidity provider position mathematics including constant product formulas, impermanent loss calculations, and concentrated liquidity valuation
Mathematical Formulas: Documented precise formulas for calculating LP position value changes when asset prices fluctuate, including square root payoff profiles and risk calculations
Concentrated Liquidity Mathematics: Specific formulas for Uniswap V3-style concentrated liquidity and bin-based systems like Meteora DLMM
SOL-Based Examples: Practical calculation examples for SOL-USDC positions with real-world scenarios
Fee Allocation Algorithms: Volume-proportional fee distribution formulas for post-close simulation
Implementation Guidance: Technical considerations for accurate LP position tracking in trading bot systems

**Business Impact:**
Provides mathematical foundation for accurate post-close "what-if" simulations
Enables precise calculation of missed opportunities in TP/SL timing
Supports development of ML features for optimal exit timing prediction
Establishes framework for risk-adjusted position valuation

**Research Output:** Comprehensive mathematical framework document with derivations, examples, and implementation considerations ready for Phase 3B development.
**System Status:** Mathematical foundation complete. Ready for Phase 3B implementation of post-close analysis with accurate LP position valuation. ✅

**2025-07-26: TP/SL Optimizer Phase 3B Implementation & Debug**

**Goal:** Implement the post-close analysis engine to simulate alternative TP/SL scenarios and quantify missed opportunities, serving as the foundation for ML-driven optimization.

**Achieved:**
- **Full Module Implementation:** Created and integrated all core components for Phase 3B: `PostCloseAnalyzer`, `LPPositionValuator`, and `FeeSimulator`.
- **Architectural Stabilization:** Resolved all circular dependency and `NameError` issues by correctly implementing `if TYPE_CHECKING` blocks combined with forward-referencing type hints (`'Position'`), leading to a stable application architecture.
- **End-to-End Workflow:** Successfully implemented the full user-facing workflow in the main menu, including running the analysis, generating text reports, viewing statistics, and exporting a preliminary ML dataset.
- **Robust Data Handling:** The system now gracefully handles positions with missing fee or volume data by flagging them as unsuccessful analyses and continuing, rather than crashing the entire process.
- **Mathematical Logic Validation:** The simulation engine produces plausible business results (e.g., 14.8% average missed upside), indicating the impermanent loss and fee allocation formulas are working as intended.
- **Foundation for Phase 4:** The successful generation of `ml_dataset_tp_sl.csv` completes the data pipeline required to begin work on the machine learning optimization phase.

**Files Modified/Created:**
- `main.py` (added new menu and functions)
- `data_fetching/enhanced_price_cache_manager.py` (architectural fixes)
- **Created:** `reporting/post_close_analyzer.py`
- **Created:** `reporting/fee_simulator.py`
- **Created:** `reporting/lp_position_valuator.py`

**System Status:** Phase 3B is complete and stable. The application can now perform post-close "what-if" analysis, laying the groundwork for data-driven TP/SL optimization. ✅

**2025-07-27: TP/SL Range Testing (Phase 4A) Implementation**

**Goal:** Implement a framework to test a grid of TP/SL values and visualize the results to find optimal settings per strategy.

**Achieved:**
- **Robust Data Pipeline:** Implemented a critical architectural change where the `strategy_instance_detector.py` module now enriches the main `positions_to_analyze.csv` file in-place with a `strategy_instance_id`. This creates a single, reliable source of truth for all subsequent analyses and eliminates the need for intermediate files.
- **Simulation Engine:** Created a new `TpSlRangeSimulator` capable of running thousands of "what-if" scenarios based on user-defined TP/SL levels in the configuration.
- **Per-Strategy Visualization:** The main HTML report now features a new section with interactive Plotly heatmaps, generated for each major strategy. These heatmaps visually represent the most profitable TP/SL combinations.
- **Actionable Insights:** Added summary tables to the report, clearly listing the optimal TP/SL parameters found for each strategy, providing direct, actionable recommendations.
- **Foundation for Phase 4B:** The process now generates a detailed results file (`range_test_detailed_results.csv`), which will serve as the data backend for the future interactive "what-if" tool.

**System Status:** Phase 4A is complete and stable. The system can now perform large-scale TP/SL simulations and present the results in an intuitive, visual format. ✅

**2025-07-27: Interactive "What-If" Tool (Phase 4B) Implementation**

**Goal:** To build a fully interactive, client-side tool within the HTML report for dynamic exploration of the TP/SL simulation results.

**Achieved:**
- **Efficient Data Pipeline:** Implemented a robust data enrichment process in `html_report_generator.py` that merges three separate CSVs (`range_test_results`, `positions`, `strategy_instances`) into a single, comprehensive JSON object. This object serves as the complete backend for the interactive tool.
- **Dynamic Frontend Tool:** Developed a new section in the HTML report powered by JavaScript. The tool allows users to input custom TP/SL values and instantly see the aggregated impact on PnL, win rate, and trade outcomes per strategy.
- **Advanced Filtering Capabilities:** The tool includes real-time filters for date ranges and the minimum number of positions per strategy, allowing users to precisely scope their analysis.
- **Intelligent Parameter Matching:** Implemented a Euclidean distance algorithm in JavaScript to intelligently find the closest pre-calculated data point from the simulation grid, ensuring the "what-if" results are both fast and relevant.
- **Enhanced User Experience:** The results table updates instantly on any filter change, provides color-coded PnL feedback, and includes a breakdown of exit reasons (TP/SL/End of Sim) for a deeper understanding of the outcomes.

**System Status:** Phase 4B is complete and stable. The project now features a powerful, dynamic analysis tool that significantly enhances its business value and usability. ✅