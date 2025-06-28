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

Strategy Heatmap Image Orientation Issue:
- **Issue**: Generated PNG files saved with 90° clockwise rotation requiring manual correction in image viewers
- **Attempted solutions**: figsize dimension changes, orientation='portrait' parameter, both simultaneously
- **Implementation complexity**: MEDIUM - matplotlib configuration issue not resolved with standard approaches
- **Business impact**: LOW - functional charts generate correctly, only display orientation affected
- **Decision**: Escalated to Gemini for matplotlib expertise, beyond Claude's current troubleshooting scope
- **Date**: 2025-06-28
- **Status**: UNRESOLVED - requires matplotlib/PNG orientation specialist knowledge

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
├── extraction/             - data extraction and processing
│   ├── __init__.py
│   ├── log_extractor.py   - main parser with debug controls and close reason classification (~430 lines)
│   └── extraction_utils.py - utilities for extraction module
├── **reporting/**              - **analytics and portfolio performance analysis**
│   ├── **__init__.py**
│   ├── **config/**
│   │   └── **portfolio_config.yaml** - **infrastructure costs, risk-free rates, filters** 🆕
│   ├── **output/** - **generated reports and charts directory** 🆕
│   │   ├── **charts/** - **timestamped PNG visualizations** 🆕
│   │   └── **portfolio analysis logs** 🆕
│   ├── **infrastructure_cost_analyzer.py** - **daily cost allocation and Moralis API (~400 lines)** 🆕
│   ├── **portfolio_analytics.py** - **dual currency analysis engine (~500 lines)** 🆕
│   ├── **chart_generator.py** - **4 chart types with strategy heatmap parsing (~600 lines)** 🆕
│   ├── **portfolio_main.py** - **CLI orchestrator with multiple analysis modes (~400 lines)** 🆕
│   ├── strategy_instance_detector.py - groups positions into strategy instances (~400 lines)
│   ├── strategy_comparison_matrix.py - strategy ranking and comparison (planned)
│   ├── daily_performance_tracker.py - performance tracking over time (planned)
│   ├── performance_visualizer.py - charts and visualization (planned)
│   └── reporting_utils.py - utilities for reporting module
├── main_analyzer.py        - main orchestrator (extraction → analysis → reporting)
├── strategy_analyzer.py    - LP strategy simulation engine for Meteora DLMM (~250 lines)
├── models.py              - Position class and data models (~50 lines)
├── parsing_utils.py       - universal parsing utilities (~250 lines)
├── debug_analyzer.py      - context analysis and export system (~200 lines)

File Handling Rules

Input: all *.log files starting with "app" in input/ directory
Cache: automatic Moralis API response caching (JSON files)
Reports: individual text reports + collective CSV

🏃‍♂️ Project Status
Last Update: 2025-06-28
Current Version: Portfolio Analytics v1.0 (Complete)
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
Strategy instance detection and grouping ✅
Multi-wallet support with subfolder organization ✅
Strategy performance ranking with weighted scoring ✅
Enhanced CSV structure with wallet_id and source_file tracking ✅

**Portfolio Analytics Module:**
- **Complete analysis pipeline**: dual SOL/USDC currency analysis with infrastructure cost impact ✅
- **Chart generation system**: 4 professional charts with timestamps (equity curve, drawdown analysis, strategy heatmap, cost impact) ✅
- **Strategy heatmap**: automated parsing of step_size from strategy names, position counts display, filter details ✅
- **Text report generation**: timestamped portfolio summaries and infrastructure impact reports ✅
- **YAML configuration**: infrastructure costs, risk-free rates, visualization filters ✅
- **Moralis API integration**: historical SOL/USDC price data with caching ✅
- **Custom timestamp parsing**: handles non-standard formats (MM/DD-HH:MM:SS, 24:XX:XX) ✅
- **Robust error handling**: fallback mechanisms for missing data and CSV structure variations ✅

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

Next Priority Tasks:

**Immediate (Next Session):**
- **Strategy Heatmap Orientation Fix**: resolve matplotlib PNG rotation issue (escalated to Gemini) 📋
- **Portfolio Analytics Integration**: connect with existing strategy_analyzer.py pipeline 📋

**Strategy Analytics Module Enhancement:**
  - Strategy comparison matrix with detailed performance breakdown 📋
  - Daily performance tracking and trend analysis 📋
  - Performance correlation with market trends (SOL-USDC, BTC-USDC) 📋

**ML & Advanced Analytics:**
  - ML-driven TP/SL level optimization 📋
  - Post-exit analysis (forward-looking candle testing) 📋
  - Precise fee calculations per-candle 📋

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