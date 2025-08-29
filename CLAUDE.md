🌐 Language Policy
CRITICAL RULE: Regardless of conversation language, ALL code updates and CLAUDE.md modifications must be in English. This ensures consistency in codebase and documentation.

🎯 Project Objectives
Main Goals

✅ Bot Performance Analysis - Extract position data from SOL Decoder bot logs
✅ LP Strategy Optimization - Simulate alternative Meteora DLMM strategies for found positions
✅ Strategy Ranking - Identify best strategy combinations for different market conditions
✅ Analysis Automation - Complete pipeline from logs to comparative reports
✅ TP/SL Optimization - ML-ready optimization of take profit and stop loss levels with historical simulation
✅ Post-Exit Analysis - Forward-looking profitability analysis with "what-if" scenarios

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

```python
def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
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
```

Anchor Comments (AI Navigation Comments)
Format: # [TAG]-[AI_ID]: [comment content] (max 120 characters)
Available tags:

# AIDEV-NOTE-CLAUDE: - important performance/business logic information
# AIDEV-TODO-CLAUDE: - planned improvements/tasks
# AIDEV-QUESTION-CLAUDE: - doubts to discuss with human
# AIDEV-TPSL-CLAUDE: - TP/SL optimization specific notes
# AIDEV-VOLUME-CLAUDE: - Volume data collection and processing  
# AIDEV-FEES-CLAUDE: - Fee accumulation simulation logic
# AIDEV-PERF-CLAUDE: - Performance optimization for large-scale simulation
# AIDEV-INTEGRATE-CLAUDE: - Integration points with existing codebase

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
```python
# AIDEV-NOTE-CLAUDE: perf-critical; Moralis API cache mechanism - avoid duplicate requests
def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    # Implementation...

# AIDEV-TODO-CLAUDE: add pool_address format validation (ticket: SOL-123)  
def validate_meteora_pool_address(address: str) -> bool:
    # Current implementation...

# AIDEV-TPSL-CLAUDE: Fee accumulation affects SL triggering: position_value = price_value + fees
def calculate_position_exit(position: Position, tp_level: float, sl_level: float) -> ExitResult:
    # Exit calculation logic...
```

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
Discuss TP/SL optimization logic and mathematical frameworks
Extend OCHLV cache management and offline-first analysis patterns

⚠️ You can propose (but not implement)

Code refactoring - propose plan, wait for approval
API call optimizations - describe benefits, don't introduce automatically
Simulation algorithm improvements - discuss mathematics, don't change without permission
File structure changes - only with explicit permission
ML model architecture for TP/SL optimization - discuss approach, don't implement without specification
Advanced fee calculation improvements - describe benefits, don't introduce automatically
Post-close simulation enhancements - discuss mathematics, don't change without permission
Interactive tool UI/UX improvements - propose features, don't modify without approval

🚫 Absolute prohibitions

Don't assume LP strategy logic - Meteora DLMM parameters are specific, always ask
Don't implement Moralis API optimizations without consent (only propose)
Don't remove anchor comments without instructions
Don't change fee calculation logic - this is core business logic
Don't assume LP valuation mathematics - Meteora DLMM formulas are specific, always ask
Don't implement ML optimization algorithms without explicit specification
Don't change peak PnL extraction logic - this is validated business logic
Don't modify range testing simulation without understanding business impact

**Session History Management**
- **Maintain full history:** I will keep the detailed log of all recent sessions in this file.
- **Await archival command:** I will not compress or archive the session history. You, the user, will give the command to archive when a major milestone is complete.

📋 Change Implementation Process

First skeleton/plan of changes for discussion
After approval - complete code with precise "find and replace" instructions
Code changes: using "find and replace" method with exact location
New code: indicate exactly where to paste

📄 Refactoring (soft-stop at 600+ lines)

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

📝 Task Completion Reminders

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

## TP/SL Optimization & Analysis Terminology

**Peak PnL Extraction** - Maximum profit/loss percentages reached during position lifetime, parsed from bot logs
**Post-Close Analysis** - Forward-looking "what-if" simulation using historical price data after position closure
**Range Testing** - Systematic testing of TP/SL parameter grids to identify optimal combinations
**Strategy Instance** - Grouped positions sharing identical parameters (strategy, step_size, investment_sol)
**Interactive What-If Tool** - Browser-based explorer for dynamic TP/SL scenario analysis
**LP Position Valuation** - Mathematical calculation of position value including impermanent loss
**Volume-Proportional Fees** - Fee simulation based on historical volume patterns
**Missed Opportunity Analysis** - Quantification of profit potential beyond actual close timing
**ML Dataset Export** - Structured feature set for machine learning model training

**OCHLV+Volume Data** - Open/Close/High/Low prices with trading volume for accurate simulations
**Offline-First Analysis** - Complete analysis capability using cached data without API dependency
**Euclidean Distance Matching** - Algorithm to find closest pre-calculated TP/SL combinations
**Time Decay Weighting** - Prioritizing recent performance in optimization calculations
**Expected Value (EV) Analysis** - Mathematical framework for viable Stop Loss floor determination

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
```
project/
├── main.py                     # Main application entry point with interactive menu
├── main_analyzer.py            # (Legacy) Alternative analysis entry point
├── core/
│   └── models.py               # Enhanced Position model with TP/SL and peak PnL fields
├── data_fetching/              # All data fetching and orchestration logic
│   ├── __init__.py
│   ├── cache_orchestrator.py   # Manages OCHLV cache (menus, validation)
│   ├── enhanced_price_cache_manager.py # Core OCHLV+Volume cache logic
│   └── main_data_orchestrator.py # Manages main report data fetching
├── extraction/                 # Data extraction from logs
│   ├── __init__.py
│   ├── log_extractor.py        # Main parser with enhanced strategy parsing and cross-file tracking
│   └── parsing_utils.py        # Enhanced parsing utilities with TP/SL and peak PnL extraction
├── reporting/                  # Analytics and portfolio performance analysis
│   ├── __init__.py
│   ├── config/
│   │   └── portfolio_config.yaml # Infrastructure costs, TP/SL ranges, analysis parameters
│   ├── templates/
│   │   └── comprehensive_report.html # Interactive HTML report with TP/SL tools
│   ├── visualizations/         # Chart plotting modules
│   │   ├── __init__.py
│   │   ├── cost_impact.py
│   │   ├── drawdown.py
│   │   ├── equity_curve.py
│   │   ├── interactive/          # Interactive chart modules
│   │   │   ├── __init__.py       # Re-exports all chart functions
│   │   │   ├── market_charts.py  # Correlation, EMA Trend charts
│   │   │   ├── portfolio_charts.py # KPI, Equity Curve, Drawdown, Cost charts
│   │   │   ├── simulation_charts.py# Weekend, Strategy Sim charts
│   │   │   └── strategy_charts.py  # Heatmap, AVG PnL charts
│   │   └── strategy_heatmap.py
│   ├── orchestrator.py         # Core logic engine for the reporting workflow
│   ├── analysis_runner.py      # Runs Spot vs. Bid-Ask simulation for all positions
│   ├── data_loader.py          # Position data loading and cleaning (no mapping logic)
│   ├── post_close_analyzer.py  # "What-if" TP/SL analysis engine
│   ├── fee_simulator.py        # Volume-proportional fee allocation
│   ├── lp_position_valuator.py # LP position value with IL formulas
│   ├── html_report_generator.py # HTML report generation orchestrator
│   ├── infrastructure_cost_analyzer.py # Daily cost allocation and Moralis API
│   ├── market_correlation_analyzer.py  # Analysis of portfolio vs market correlation
│   ├── metrics_calculator.py   # Financial metrics calculation
│   ├── strategy_instance_detector.py # Groups positions into strategy instances
│   ├── text_reporter.py        # Text report generation
│   ├── price_cache_manager.py  # Smart price caching with gap detection and API failure handling
│   └── enhanced_price_cache_manager.py # OCHLV+Volume cache with offline-first
├── simulations/                # "What-if" simulation engines
│   ├── spot_vs_bidask_simulator.py # Simulates Spot vs Bid-Ask strategies
│   ├── weekend_simulator.py    # Simulates weekend parameter impact
│   └── range_test_simulator.py # TP/SL range testing simulation engine
├── tools/                      # Developer and utility tools
│   ├── __init__.py
│   ├── cache_debugger.py       # OCHLV cache debugging and validation
│   ├── api_checker.py          # Checks Moralis API connectivity
│   ├── debug_analyzer.py       # Context analysis and export system
│   └── fix_column_names.py     # Column name standardization utility
└── utils/                      # Shared helper functions
    ├── __init__.py
    └── common.py               # Houses print_header, load_main_config, etc.
```

File Handling Rules

Input: all *.log files starting with "app" in input/ directory; optional positions_to_skip.csv in root
Cache: automatic Moralis API response caching (JSON files) with smart gap detection
Reports: individual text reports + collective CSV with clean column names

🏃‍♂️ Project Status
Last Update: 2025-08-25
Current Version: v5.0 - Complete TP/SL Optimization Module
Working Features:

**Core Data Pipeline:**
- Position extraction from SOL Decoder logs ✅ (improved to >99.5% accuracy)
- Manual position filtering via `positions_to_skip.csv` ✅
- Historical price data fetching from Moralis API ✅
- Smart price cache with gap detection and API failure handling ✅
- 2 LP strategy simulation (1-Sided Spot/Bid-Ask only) ✅
- Comparative report generation ✅
- PnL-based position filtering ✅
- Debug system with configurable context export ✅
- Close reason classification (TP/SL/LV/OOR/other) ✅
- Reliable Take Profit/Stop Loss parsing from `OPENED` events ✅
- Robust handling of position restarts/replacements ("Superseded" logic) ✅
- Business logic close reason detection (always active) ✅
- Duplicate position prevention ✅
- Position retry handling with data updates ✅
- Strategy detection from logs ✅ (>99.5% accuracy)
- Step size detection and processing (WIDE/SIXTYNINE/MEDIUM/NARROW) ✅
- Research-based Bid-Ask distribution (U-shaped mathematical formula) ✅
- Close timestamp extraction ✅
- CSV append mode with deduplication ✅
- Modular architecture with proper separation of concerns ✅
- Step size integration with bin count adjustment ✅
- Strategy instance detection and grouping ✅
- Multi-wallet support with subfolder organization ✅
- Strategy performance ranking with weighted scoring ✅
- Enhanced CSV structure with wallet_id and source_file tracking ✅
- Enhanced position deduplication with cross-file tracking ✅
- Universal position identification (pool_address + open_timestamp) ✅
- Automatic position completion (active_at_log_end → complete positions) ✅
- Chronological file processing for proper position sequencing ✅
- Intelligent duplicate handling with update/skip logic ✅

**Portfolio Analytics Module:**
- Complete analysis pipeline: dual SOL/USDC currency analysis with infrastructure cost impact ✅
- Chart generation system: 4 professional charts with timestamps (equity curve, drawdown analysis, strategy heatmap, cost impact) ✅
- Strategy heatmap: automated parsing of step_size from strategy names, position counts display, filter details ✅
- Text report generation: timestamped portfolio summaries and infrastructure impact reports ✅
- YAML configuration: infrastructure costs, risk-free rates, visualization filters ✅
- Moralis API integration: historical SOL/USDC price data with smart caching ✅
- Custom timestamp parsing: handles non-standard formats (MM/DD-HH:MM:SS, 24:XX:XX) ✅
- Robust error handling: fallback mechanisms for missing data and CSV structure variations ✅

**Architecture Stabilization & Resiliency:**
- Centralized Entry Point: `main.py` provides a single, interactive menu to run all parts of the pipeline ✅
- Robust API Key Handling: Dependency injection ensures the API key is passed securely and used only when needed ✅
- Cache-Only Mode: Full application support for running in an offline/cached mode for testing and cost savings ✅
- Error Resiliency (Graceful Degradation): The HTML report generation no longer crashes on missing data (e.g., from market analysis in cache-only mode), instead displaying informative messages ✅
- Modular Chart Generation: Decoupled the monolithic interactive chart module into four smaller, specialized modules (`portfolio`, `strategy`, `market`, `simulation`) for improved maintainability and adherence to the 600-line file limit. ✅

**Smart Price Cache Management v2.0:**
- Intelligent Gap Detection: Only fetches missing time periods, prevents redundant API calls ✅
- API Failure vs No Data Distinction: Handles 401 errors differently from legitimate empty periods (weekends) ✅
- Smart Placeholder Logic: Forward-fills only verified empty periods, skips placeholder creation on API failures ✅
- Cross-API-Failure Safety: Enables retry on subsequent runs for failed requests while preserving verified empty data ✅
- Monthly Cache Files: Organized by month with incremental updates and merge capabilities ✅

**Column Name Standardization v1.0:**
- Eliminated Mapping Chaos: Removed all column name mapping logic from entire codebase ✅
- Unified Naming System: CSV headers and code use identical clean names (investment_sol, pnl_sol, strategy_raw) ✅
- Zero Accidental Complexity: Direct CSV → code usage, no intermediate mapping layers ✅
- Improved Maintainability: Single source of truth for column names, easier debugging ✅
- Performance Enhancement: Eliminated mapping overhead in data processing pipeline ✅

**Strategy Parsing & Pipeline Stabilization v4.2:**
- Enhanced TP/SL Parsing: Take profit and stop loss values now extracted and stored in Position model ✅
- Improved Strategy Detection: >99.5% accuracy through reverse search with context lookahead ✅
- Silent Failure Detection: SUCCESS_CONFIRMATION_PATTERNS prevent false positive position detection ✅
- Robust Pipeline: NaN handling and error resilience throughout data processing pipeline ✅
- Enhanced Logging: Clean, focused logs with DEBUG-level detail control ✅

**Architecture Refactoring & Pragmatic Cache Management:**
- Centralized Logic: Refactored `main.py` by moving complex logic into dedicated modules (`data_fetching`, `tools`, `utils`), making it a clean entry point ✅
- Circular Import Resolution: Eliminated all circular import errors by creating a shared `utils.common` module for helper functions, stabilizing the architecture ✅
- Pragmatic Cache Rule ("2-Day Rule"): Implemented an automatic, time-based rule to stop fetching data for old, incomplete positions, preventing wasted API calls on unfixable data gaps ✅
- Smart OCHLV Fetching: OCHLV cache population now supports "Fill Gaps" and "Force Refetch" modes, giving the user full control while defaulting to the most efficient strategy ✅

**TP/SL Optimization Module (Complete):**
- **Peak PnL extraction from logs** ✅ (max profit/loss during position lifetime)
- **Post-close "what-if" analysis** ✅ (forward-looking simulation beyond actual close)
- **LP position valuation with impermanent loss** ✅ (mathematical accuracy for price fluctuations)
- **Volume-proportional fee simulation** ✅ (realistic fee allocation for extended periods)
- **OCHLV+Volume data infrastructure** ✅ (offline-first cache with monthly organization)
- **TP/SL range testing simulation** ✅ (grid-based parameter optimization)
- **Interactive what-if tool** ✅ (browser-based dynamic exploration)
- **Per-strategy optimization heatmaps** ✅ (visual identification of optimal parameters)
- **ML-ready dataset export** ✅ (structured features for model training)
- **Missed opportunity quantification** ✅ (profit potential analysis)

Next Priority Tasks:

**Phase 5: ML-Driven Optimization Engine:**
- Implement prescriptive analytics engine for optimal TP/SL parameter identification 📋
- Expected Value (EV) based SL floor analysis with mathematical framework 📋
- Time decay weighting system prioritizing recent performance 📋
- Statistical significance validation to avoid overfitting 📋
- Net effect strategy analysis for parameter change impact 📋

**Advanced Analytics & Integration:**
- Real-time strategy recommendations based on market conditions 📋
- Risk management automation with position sizing recommendations 📋
- Market regime detection (bull/bear/crab) for parameter adaptation 📋
- Cross-strategy performance analysis and correlation studies 📋

**Delta-Neutral LP Management (Post TP/SL Optimization):**
- Funding rate analyzer with multi-DEX monitoring 📋
- Real-time delta exposure calculator for active LP positions 📋
- Optimal hedge position sizing with leverage optimization 📋
- SOL-USDC trend correlation with funding rate analysis 📋
- Delta-neutral P&L reporting, performance analytics and simulations 📋
- Market regime detection (bull/bear/crab) for hedge timing 📋

Future Roadmap:

**Telegram Integration:**
- Position open/close notifications 📋
- SL/TP override commands (via n8n automation) 📋
- Price alert system 📋

**Advanced Features:**
- Real-time strategy recommendations 📋
- Risk management automation 📋

📝 Session History

## Recent Milestones (Last 10 Major Updates)

**2025-08-25: Critical Log Parser Debugging & Regex Pattern Fix**

Major Parser Issue Resolved: Fixed critical regex patterns causing 0 position detection in SOL Decoder v0.13.36 logs
Root Cause Analysis: Bot format changed to bidask: null | OPENED instead of expected bidask: 123 | OPENED, plus [LOG] prefix requirement
Silent Failure Detection Fix: Modified success confirmation patterns to accept OPENED line itself as validation, reducing false negatives from 94.4% to 0%
Emoji Close Pattern Support: Updated close event regex to handle 🟨Closed TOKEN-SOL format with emoji prefixes
Parsing Success Rate: Improved from 0/18 positions to 18/18 positions detected, with 8 positions above 0.01 SOL threshold
Cross-File Position Tracking: Successfully handling position opens/closes across multiple log files with superseded logic
Data Quality Improvement: From 0 usable positions to 55/63 expected positions (87% capture rate) in August 1-20 period

**Identified Remaining Issues:**

Missing 8 Positions: 8/63 expected positions not captured, requires diagnostic analysis
Peak PnL Scaling Error: max_profit_during_position and max_loss_during_position values ~10x too high
Strategy End Date Complexity: Need to remove strategy end dates from reports to simplify presentation

**Technical Implementation:**

Updated Regex Pattern: v(?P<version>[\d.]+)-(?P<timestamp>\d{2}/\d{2}-\d{2}:\d{2}:\d{2})\s*\[LOG\]\s*(?P<strategy_type>bidask|spot|spot-onesided):\s*(?:null|\d+)\s*\|\s*OPENED\s*(?P<token_pair>[\w\s().-]+-SOL)
Enhanced Success Patterns: Added OPENED line validation and Checking open positions on meteora as success indicators
Improved Close Detection: Closed\s+([A-Za-z0-9\s\-_()]+-SOL)\s+\(Symbol: pattern for emoji-prefixed messages
CSV Field Handling: Fixed strategy_instance_id field conflicts in data export

**2025-07-26: TP/SL Optimizer Phase 3A & 3B Complete**
- **Peak PnL Extraction:** Enhanced Position model with max_profit/max_loss fields parsed from logs
- **Post-Close Analysis Engine:** "What-if" simulation with LP position valuation and fee allocation
- **Mathematical Framework:** Implemented impermanent loss formulas and volume-proportional fees
- **Offline-First Architecture:** Complete analysis capability using cached OCHLV+Volume data
- **ML Dataset Foundation:** Generated preliminary feature sets for optimization model training

**2025-07-27: TP/SL Range Testing (Phase 4A & 4B) Complete**
- **Grid Simulation Engine:** Systematic testing of TP/SL parameter combinations across all positions
- **Interactive What-If Tool:** Browser-based dynamic explorer with real-time filtering and matching
- **Per-Strategy Heatmaps:** Visual identification of optimal TP/SL regions per strategy instance
- **Data Pipeline Enhancement:** Single source of truth with strategy_instance_id enrichment
- **Actionable Insights:** Direct recommendations for optimal TP/SL parameters per strategy

**2025-07-24: TP/SL Optimizer Phase 2 Implementation - Integration & Offline-First Analysis**
- **3-Tier Cache System Implementation:** Successfully deployed offline_processed/ cache layer that converts raw OCHLV data to simple price format compatible with existing simulations
- **Config-Driven Offline-First Behavior:** Added comprehensive data_source section to portfolio_config.yaml controlling prefer_offline_cache, interactive_gap_handling preferences
- **Interactive Gap Resolution:** Implemented sophisticated 6-option user choice system for incomplete data with session memory
- **Smart Menu Enhancement:** Added dynamic mode indicators showing (Online/Offline/Hybrid) in main menu based on config preferences
- **Pure Offline Validation:** Confirmed that Steps 4-5 (simulations + reports) run completely offline after Step 3 data fetching

**2025-07-23: Architecture Refactoring & Pragmatic Cache Management**
- **Major Code Refactoring:** Decomposed the oversized `main.py` by moving all orchestration and debugging logic into new, dedicated modules
- **Created Shared Utilities Module:** Established a new `utils/common.py` module for shared helper functions, completely resolving all circular import errors
- **Implemented "Pragmatic Cache Rule":** Simple and effective "2-Day Rule" to automatically avoid wasted API credits on permanent data gaps
- **Developed Smart Fetching Modes:** The OCHLV cache orchestrator now provides two modes: "Fill Gaps Only" (default) and "Force Refetch All"

**2025-07-19: Refactoring of Interactive Chart Module**
- **Decomposition:** The monolithic `interactive_charts.py` file (800+ lines) was successfully decomposed into four specialized modules
- **New Structure:** Created `reporting/visualizations/interactive/` directory with `portfolio_charts.py`, `strategy_charts.py`, `market_charts.py`, and `simulation_charts.py`
- **Code Pruning:** Removed two obsolete and unused functions, reducing dead code
- **Pipeline Consistency:** All related files updated to reflect the new structure and removal of old functions

**2025-07-18: Market Trend Visualization & Report Simplification**
- **Visual Trend Indicator Chart:** Implemented new interactive chart plotting SOL price against its 50-period EMA with dynamic coloring (green for uptrend, red for downtrend)
- **Unified Trend Colors:** Standardized color scheme across all trend-based bar charts for improved readability
- **Simplified Weekend Analysis:** Streamlined the Weekend Parameter Impact chart by removing less relevant metrics
- **Report Decluttering:** Removed redundant Legacy Strategy Heatmap section, making the primary Strategy Performance Summary the single source of truth

**2025-07-17: Critical Debugging: Resolving Unrealistic Max Drawdown Values**
- **Root Cause Identified:** The functions in `metrics_calculator.py` were incorrectly multiplying the final drawdown result by 100, then the reporting layer formatted this as a percentage again
- **Implemented Fix:** Removed the erroneous `* 100` multiplication from `calculate_sol_metrics` and `calculate_usdc_metrics` functions
- **Business Impact:** Restored credibility to a key risk metric by eliminating misleading data (e.g., -14,600% instead of -146%)

**2025-07-16: Manual Position Filtering for Data Correction**
- **Manual Skip Functionality:** Implemented logic in `log_extractor.py` to read `positions_to_skip.csv` and filter out specified position IDs
- **Robust Implementation:** Feature is fault-tolerant - if skip file is missing, extraction continues without manual filtering
- **Business Impact:** Provides crucial "escape hatch" for data quality issues from bot logs that cannot be fixed programmatically

**2025-07-15: Critical Pipeline Fixes & "Superseded" Logic**
- **Robust Single-Line Parsing:** Replaced fragile multi-line parsing with robust single-line strategy, resolving NaN issues for TP/SL
- **"Superseded" Logic:** Implemented handling for position restarts where old unclosed positions are automatically closed when new ones start
- **Data Pipeline Stabilization:** Fixed "Time Machine" bug and active position tracking using token pair as unique key
- **Recovery Achievement:** Recovered dozens of lost positions and restored data integrity across the pipeline

**2025-07-04: Smart Cache & Column Standardization**
- **Smart Price Cache v2.0:** Intelligent gap detection, API failure vs no-data distinction, smart placeholder logic
- **Column Name Standardization:** Eliminated mapping chaos, unified naming system across entire codebase (investment_sol, pnl_sol, strategy_raw)
- **Zero Mapping Overhead:** Direct CSV header → code usage, eliminated accidental complexity
- **Cache API Failure Handling:** Proper distinction between API failures (retry tomorrow) vs verified empty periods (cache forever)

**System Status:** TP/SL Optimization Module complete through Phase 4. Foundation established for Phase 5 ML-driven recommendations. All major objectives achieved. ✅

**2025-08-28: Peak PnL Analysis Debugging & Code Cleanup**
Issue Resolution - Peak PnL Values Investigation:

**Initial Problem:** Peak PnL fields (max_profit_during_position, max_loss_during_position) showing values ~10x too high (e.g., -5.13 for 9% SL positions)
- Debugging Process: Implemented targeted debugging with TARGETED_DEBUG_ENABLED for position pos_08-18-07-32-07_2663390
- Root Cause Discovery: Values were mathematically correct - misunderstanding of units. Peak PnL shows percentages (-5.13%), not SOL amounts (-5.13 SOL)
- Validation: Debug trace confirmed regex correctly extracted -5.13% from log line: PnL: -0.46183 SOL (Return: -5.13%)
- Business Logic Confirmation: Position lost 5.13% at peak, then recovered to +6.03% profit at TP close - this is expected LP behavior

**Strategy Instance ID Simplification:**

- Implementation: Modified _generate_strategy_id() in strategy_instance_detector.py to remove last_use_date from ID format
- Result: Cleaner strategy IDs: Bid-Ask_TP6_SL9_2025-08-14_5c005f (vs previous with end dates)
- Data Preservation: last_use_date remains in CSV export, only removed from ID generation

**Debug Infrastructure Cleanup:**

- Targeted Debug Disabled: Set TARGETED_DEBUG_ENABLED = False and DETAILED_POSITION_LOGGING = False
- Log Noise Reduction: Moved validation diagnostics and superseded position warnings to DEBUG-only mode
- Enhanced Error Messages: Improved "Could not identify closed pair" warnings with file, timestamp, and content preview
- File Cleanup: Removed peak_pnl_debug.txt debug output file

**Incomplete - Skipped Positions Logging:**

- Requirement: Create skipped_positions.txt with validation errors including file names and timestamps
- Challenge: Positions with validation errors may not reach main validation loop in run() function
- Status: Needs further investigation into where validation errors are actually detected and filtered

**Technical Details:**

- Peak PnL Regex Pattern: SOL\s*\(Return:\s*([+-]?\d+\.?\d*)\s*%\) works correctly
- Function Location: extract_peak_pnl_from_logs() in extraction/parsing_utils.py
- Validation Location: Main validation loop in LogParser.run() around line 430
- Debug Files Generated: 18,239 samples processed for single position showing expected volatility range

**Code Quality Improvements:**

- Logging Standardization: Consistent DEBUG-level logging for non-critical diagnostics
- Error Message Enhancement: Added file context and timestamps to parsing error messages
- Debug Flag Consolidation: Centralized debug controls in log_extractor.py header constants