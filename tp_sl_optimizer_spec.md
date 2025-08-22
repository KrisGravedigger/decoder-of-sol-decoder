# TP/SL Optimizer Module Specification

## 🔗 Background
This module is part of the SOL Decoder LP Strategy Optimization Project. For general project context, coding conventions, and architecture guidelines, see [CLAUDE.md](CLAUDE.md).

## 🤖 AI Assistant Instructions (Lex Specialis)

### **Critical Business Logic Priority**
1. **Fee accumulation buffer for SL:** Position value = price value + accumulated fees
2. **Volume-proportional fee simulation:** Fee generation depends on volume per candle
3. **Distance-based fee multipliers:** Bid-ask strategies have variable fee rates based on price distance
4. **Post-close data extension:** Simulate "what-if" scenarios using actual historical price data

### **Implementation Strategy**
- **Stage-gate approach:** Each phase must be fully functional before proceeding
- **Data validation first:** Validate fee simulation against known position outcomes before optimization
- **Performance monitoring:** Track computational cost at each stage (target: <5min for full dataset)
- **Backward compatibility:** Never break existing pipeline during development

### **Code Integration Points**
```python
# REQUIRED IMPORTS from existing codebase:
from extraction.log_extractor import load_positions_data
from reporting.price_cache_manager import PriceCacheManager
from reporting.data_loader import load_and_prepare_positions
from simulations.spot_vs_bidask_simulator import calculate_fees_estimate

# INTEGRATION HOOKS in existing files:
# main.py: Add TP/SL optimization menu option
# reporting/orchestrator.py: Import optimization results for portfolio reports
# reporting/html_report_generator.py: Add optimization recommendations section
```

### **Module-Specific Anchor Comments**
```python
# AIDEV-TPSL-CLAUDE: - TP/SL optimization specific notes
# AIDEV-VOLUME-CLAUDE: - Volume data collection and processing  
# AIDEV-FEES-CLAUDE: - Fee accumulation simulation logic
# AIDEV-PERF-CLAUDE: - Performance optimization for large-scale simulation
# AIDEV-INTEGRATE-CLAUDE: - Integration points with existing codebase
```

### **Data Dependencies & Validation**
```python
# REQUIRED DATA STRUCTURES (extend existing):
Position.volume_history: List[float]  # Per-candle volume data
Position.fee_accumulation: List[float]  # Simulated fees over time
Position.post_close_prices: List[float]  # Price data after position close

# VALIDATION TARGETS:
# Fee simulation accuracy: <10% variance vs. actual position fees
# Performance: Process 1000 positions × 100 candles × 10 parameter combinations <5min
# Data completeness: >95% positions have sufficient post-close data
```

## 🎯 Core Objectives
**Primary Goal:** Determine statistically optimal Take Profit and Stop Loss levels through historical simulation

**Success Criteria:**
- Provide evidence-based TP/SL recommendations with quantified impact on portfolio PnL
- Enable user-defined parameter range testing with clear performance comparisons
- Integrate seamlessly with existing portfolio analytics pipeline

**Business Context:**
- LP strategies generate profit through fees, not directional price movement
- SL triggering must account for accumulated fees as buffer (position value = price value + fees)
- TP optimization seeks balance between frequent small wins vs. rare large wins

## 📋 Master Implementation Plan:

### **Phase 1: Data Infrastructure** ✅ *COMPLETED*
**Goal:** Establish robust OCHLV+Volume data collection
- [x] Redesign price cache for raw OCHLV+Volume storage
- [x] Implement volume data collection from Moralis API
- [x] Create local processing layer for multiple data consumption patterns
- [x] Validate volume data accuracy against known LP positions

**Phase Questions:**
- How to handle weekends/holidays with zero volume in cache? -> **Answered: API returns no data, our system caches this empty result.**
- What's the optimal timeframe granularity (1min, 5min, 15min)? -> **Answered: Implemented adaptive granularity (10m/30m/1h/4h) based on position duration.**
- Should we implement immediate migration of existing cache or parallel system? -> **Answered: Implemented a parallel system (`price_cache/raw/`) to avoid breaking the existing pipeline.**

### **Phase 2: Integration & Offline-First Analysis** ✅ *COMPLETED*
**Goal:** Complete Phase 1 integration with offline-first analysis pipeline
- [x] Extend PriceCacheManager with offline processed cache support
- [x] Implement interactive gap handling for incomplete data
- [x] Add config-driven data source preferences
- [x] Create smart menu labels showing online/offline mode
- [x] Add offline cache management options analogous to raw cache

**Implementation Decisions:** 
- **Architecture:** Extend existing PriceCacheManager (Option B) rather than direct OCHLV consumption
- **Cache Strategy:** offline_processed/ → raw/ → processed/ → API fallback chain
- **Gap Handling:** Interactive user choice with "apply to all" memory
- **Config Control:** prefer_offline_cache parameter in portfolio_config.yaml
- **Data Generation:** On-demand offline cache generation from raw OCHLV data

### **Phase 3A: Log-Based Peak PnL Extraction** ✅ *COMPLETED*
**Goal:**  Extract maximum profit/loss percentages from bot logs during position lifetime

- [x] Extend Position model with peak PnL fields (max_profit_during_position, max_loss_during_position, total_fees_collected)
- [x] Implement peak PnL extraction functions in parsing_utils.py
- [x] Add selective extraction logic based on close_reason (TP/SL/other)
- [x] Integrate with log_extractor.py for real-time extraction
- [x] Add tp_sl_analysis configuration section to portfolio_config.yaml
- [x] Create backfill utility for existing positions
- [x] Resolve LogParser config loading issues

**Implementation Details:**
- **Pattern Matching:** "SOL (Return: +X.XX%)" regex extraction with significance threshold filtering
- **Fee Calculation:** "Claimed: X SOL" + ("Y SOL (Fees Tokens Included)" - "Initial Z SOL")
- **Selective Logic:** TP positions extract max_loss only, SL positions extract max_profit only, others extract both
- **Performance:** Optimized search between open_line_index and close_line_index only
- **Configuration:** significance_threshold: 0.5% default, fully configurable via YAML

### **Phase 3B: Post-Close Analysis & Simulation** ✅ *COMPLETED*
**Goal:** Extend positions with post-close price data and simulate alternative TP/SL scenarios

- [x] Extend EnhancedPriceCacheManager for post-close data fetching
- [x] Implement volume-proportional fee allocation for simulation periods
- [x] Add LP position valuation using mathematical formulas
- [x] Create "what-if" simulation engine for alternative exit timing
- [x] Generate ML-ready dataset with missed opportunity metrics
- [x] Integrate with main menu for analysis execution

### **Phase 4: TP/SL Range Testing** 📋 NEXT IMPLEMENTATION

**Goal:** Create a framework to test a user-defined grid of Take Profit (TP) and Stop Loss (SL) values, aggregating the results to identify the most optimal combinations for each identified strategy instance.

This phase is divided into two parts:
- **Phase 4A (Current Implementation):** Backend simulation and static reporting with per-strategy heatmaps.
- **Phase 4B: Interactive "What-If" Tool** ✅ **COMPLETE**
    - **Summary:** Implemented a fully interactive, client-side tool within the HTML report. It is powered by a pre-calculated, enriched JSON data object.
    - **Key Features:**
        - Dynamic filtering by date range and minimum positions per strategy.
        - Smart TP/SL matching using Euclidean distance.
        - Real-time updates of a comprehensive results table.

---
#### **Phase 4A: Static Reporting & Per-Strategy Analysis** ✅ **COMPLETE**

**Core Data Flow:** The key architectural decision is to enrich the primary data file in-place, ensuring a single source of truth for all subsequent analyses.

**Step 0: Data Linkage & Enrichment (Crucial Prerequisite)**
- **File to Modify:** `reporting/strategy_instance_detector.py`
- **Workflow Change:** This module becomes a mandatory data preparation step in the main pipeline.
- **Logic:**
    1. Reads the base `positions_to_analyze.csv` file.
    2. Performs its strategy instance detection as usual.
    3. **Enriches** the loaded DataFrame by adding a new `strategy_instance_id` column.
    4. **Overwrites** the original `positions_to_analyze.csv` file with this new, enriched version. All subsequent steps will naturally use this complete data file.

**Step 1: Configuration (`portfolio_config.yaml`)**
- A new `range_testing` section will be added to allow users to define the simulation parameters.
```yaml
# PHASE 4: TP/SL Range Testing Configuration
range_testing:
  enable: true  # Master switch to run this analysis

  # Define TP levels to test (in percentage)
  tp_levels: [2, 4, 6, 8, 10, 15] 

  # Define SL levels to test (in percentage, positive value)
  sl_levels: [2, 3, 4, 5, 7, 10]

  # Metric for heatmap color and ranking
  primary_ranking_metric: "total_pnl"

**Step 2: Simulation Engine**
New File: simulations/range_test_simulator.py
New Class: TpSlRangeSimulator
Input: The enriched positions_to_analyze.csv (from Step 0).
Core Logic:
For each position, it will reuse the logic from PostCloseAnalyzer to generate a post-close value timeline once.
It will then iterate through the configured TP/SL grid. For each pair, it will scan the timeline to find the simulated exit point (TP, SL, or end of simulation).
Outputs:
range_test_detailed_results.csv: A large file with results for every combination (position_id, strategy_instance_id, tp_level, sl_level, simulated_pnl). This will be the foundation for Phase 4B.
range_test_aggregated.csv: Aggregated results, grouped by strategy_instance_id, tp_level, and sl_level.

**Step 3: Reporting & Visualization**
New File: reporting/visualizations/interactive/range_test_charts.py
New Section in HTML Report: "TP/SL Range Test Analysis"
Components:
Per-Strategy Heatmaps: A series of interactive Plotly heatmaps, one for each major strategy instance.
X-axis: SL levels, Y-axis: TP levels, Color: primary_ranking_metric.
Tooltips will show detailed stats (Total PnL, Avg PnL, Win Rate).
Optimal Settings Table: A summary table showing the best-performing TP/SL combination found for each strategy instance.

#### **Phase 4B: Interactive "What-If" Tool** ✅ **COMPLETE**

**Implementation Summary:**
- **Backend Data Enrichment:** Modified `html_report_generator.py` to merge simulation results with position timestamps and strategy instance data
- **Frontend Interactive Tool:** Created a fully client-side JavaScript tool with:
  - Dynamic TP/SL input fields with real-time updates
  - Date range filtering with clear buttons
  - Minimum positions per strategy filter
  - Euclidean distance algorithm to find closest TP/SL combinations
  - Aggregated results table with exit reason breakdown
  - Color-coded PnL values for visual feedback

**Technical Achievements:**
- Zero additional API calls - all computation happens in the browser
- Efficient data merging using pandas for enriched JSON generation
- Responsive UI with grid layout that adapts to screen size
- Robust error handling for edge cases (no data, invalid filters)
- Performance optimized for datasets with thousands of simulation results

**Business Value:**
- Users can instantly explore "what-if" scenarios without re-running simulations
- Date filtering enables analysis of specific time periods or market conditions
- Strategy count filter ensures statistical significance
- Exit breakdown provides insights into why positions closed
- Results help identify optimal TP/SL parameters for different market regimes

### **Phase 5: Optimization Engine** 📋 *NEXT IMPLEMENTATION*
**Goal:** Implement a prescriptive analytics engine to identify statistically optimal TP/SL parameters per strategy, based on historical simulation data, and present actionable recommendations.

**Core Logic & Requirements:**

**1. Net Effect Strategy Analysis**
- **Challenge:** A change in TP/SL parameters affects positions within a strategy differently.
- **Implementation:** For each proposed TP/SL change, categorize every position's outcome relative to its baseline performance:
    - **Type A (Improved):** New PnL > Baseline PnL (e.g., SL hit at -8% instead of -9%).
    - **Type B (Neutral):** New PnL = Baseline PnL (e.g., position hit TP, unaffected by SL change).
    - **Type C (Degraded):** New PnL < Baseline PnL (e.g., a winning position is now closed by the tighter SL).
- **Calculation:** The system must compute the `net_pnl_impact` by summing the improvements and degradations across all positions within a strategy for a given TP/SL combination.

**2. Expected Value (EV) Based SL Floor Analysis**
- **Concept:** Determine a rational Stop Loss floor using a sound risk/reward mathematical framework based on Expected Value.
- **Mathematical Foundation:** A strategy is profitable if its Expected Value is positive. The breakeven point is found where the historical win rate (`P_win`) equals the required win rate based on the risk parameters.
- **Formula:** `P_win > SL_Level / (TP_Level + SL_Level)`
- **Implementation:** The system will calculate the historical win rate for each TP/SL combo from the simulation data. It will then compare this to the required win rate calculated from the formula. An SL is considered "viable" if `Historical P_win > Required P_win`. The "SL floor" is the point at which this condition is no longer met.

**3. Time Decay Weighting System**
- **Requirement:** Prioritize recent performance in all calculations.
- **Logic:** Implement a configurable, time-weighted system for all PnL and win-rate calculations.
    - `last_7_days_weight`: 1.0 (100%)
    - `decay_period_weeks`: 4
    - `minimum_weight`: 0.5 (50%)
- **Functionality:** All analysis must be switchable between `time-weighted` and `equal-weighted` modes.

**4. Statistical Significance**
- **Requirement:** Avoid overfitting on small data samples.
- **Implementation:** Add a `min_positions_for_optimization` parameter to the config. The engine will skip analysis and not provide recommendations for any strategy instance with fewer positions than this threshold.

**5. Deliverables & Visualizations**
- **New Module:** `optimization/tp_sl_optimizer.py`
- **New HTML Report Section:** "TP/SL Optimization Recommendations"
- **A. Strategy Performance Matrix:** Interactive table showing the `net_pnl_impact` for each TP/SL combination, highlighting the optimal choice per strategy.
- **B. Win Rate vs. Required Win Rate Chart:** An X-Y chart for a selected strategy.
    - X-axis: SL Level.
    - Y-axis: Win Rate (%).
    - Lines: One line for "Historical Win Rate" at different SL levels, and multiple lines for "Required Win Rate" for various TP levels (e.g., TP=2%, TP=4%). Intersections show viability points.
- **C. Dynamic SL Floor Table:** A summary table showing the deepest viable SL for each TP level based on the EV analysis.

**Configuration (`portfolio_config.yaml`):**
```yaml
# PHASE 5: TP/SL Optimization Engine
optimization_engine:
  enable: true
  min_positions_for_optimization: 30 # Min positions for a strategy to be analyzed

  # Time decay settings for weighting recent performance
  time_weighting:
    enable: true
    last_n_days_full_weight: 7
    decay_period_weeks: 4
    minimum_weight: 0.5

### 🔧 Current Phase Status: Phase 4 Complete

**Completed Objectives:**
✅ **Phase 4A - Static Range Testing:** Successfully implemented grid-based TP/SL simulation with heatmap visualizations
✅ **Phase 4B - Interactive Tool:** Fully functional browser-based "what-if" explorer with advanced filtering
✅ **Data Pipeline:** Enriched simulation results with timestamps and strategy metadata for comprehensive analysis
✅ **User Experience:** Real-time updates, intuitive controls, and actionable insights
✅ **Performance:** Client-side computation ensures instant results without server load
✅ **Post-Close Analysis Engine:** Successfully implemented a "what-if" simulation engine to analyze positions after their actual close time.
✅ **LP Valuation:** Integrated mathematical formulas for impermanent loss to accurately value LP positions as prices fluctuate.
✅ **Fee Simulation:** Implemented a volume-proportional fee simulator that uses a position's historical performance to project future fee income.
✅ **Missed Opportunity Metrics:** The system now quantifies missed profit potential and optimal exit timing, providing actionable business insights.
✅ **ML Dataset Generation:** The pipeline can now generate and export a preliminary feature set for the machine learning phase (Phase 4/5).
✅ **Workflow Integration:** The new functionality is fully integrated into the main menu and operates on a stable, debugged architecture.

**Technical Achievements:**
- Resolved all circular dependency issues, stabilizing the application's architecture.
- Implemented robust, graceful handling of incomplete data (e.g., missing fees/volume).
- Created a complete, end-to-end user workflow from analysis execution to report generation.

**Ready for Next Phase:**
- All TP/SL range testing functionality is complete and operational
- Foundation established for Phase 5 - ML-driven optimization
- Historical simulation data ready for machine learning model training



# Peak PnL extraction with business logic
if position.close_reason == 'TP':
    # We know max profit (final PnL), extract max_loss only
    position.max_profit_during_position = position.final_pnl
elif position.close_reason == 'SL':  
    # We know max loss (final PnL), extract max_profit only
    position.max_loss_during_position = position.final_pnl
else:  # 'LV', 'OOR', 'other'
    # Extract both max profit and max loss from logs
Configuration Structure
yamltp_sl_analysis:
  enable_custom_params: false
  
  # Time horizon controls (for Phase 3B)
  post_close_multiplier: 1.0           # 1x = position duration length
  min_post_close_hours: 2              # Minimum post-close analysis period
  max_post_close_hours: 48             # Maximum 2 days
  
  # Analysis scope filters
  scope_filters:
    enable_date_filter: false
    analysis_date_from: null            # Optional "YYYY-MM-DD" start date
    last_n_days: null                   # Alternative: analyze last N days only
    
    # Position quality filters
    min_position_duration_hours: 1      # Skip very short positions
    min_position_value_sol: 0.1         # Skip tiny positions  
    exclude_active_positions: true      # Skip active_at_log_end positions
    
    # Close reason filters
    include_close_reasons: ["TP", "SL", "LV", "OOR", "other"]
    
  # Peak PnL extraction settings
  significance_threshold: 0.5           # Minimum absolute % to consider significant
  min_samples_for_confidence: 5        # Minimum PnL readings for high confidence

### **Technical Specifications**
```
price_cache/
├── raw/                    # NEW: Raw OCHLV+Volume data
│   ├── 2024-06/           # Monthly organization
│   │   ├── pool_123...json # Per-pool raw data: {"timestamp": "2024-06-15T10:30:00Z", "open": 150.25, "close": 151.10, "high": 151.50, "low": 149.80, "volume": 25400.50}
│   └── 2024-07/
└── processed/             # Current processed cache (maintain during transition)
    ├── positions/
    └── daily_rates/
```

### **Critical Implementation Requirements**
```python
# AIDEV-VOLUME-CLAUDE: Volume data structure specification
# Expected API response format from Moralis:
{
    "timestamp": "2024-06-15T10:30:00Z",
    "open": 150.25,
    "close": 151.10,
    "high": 151.50,
    "low": 149.80,
    "volume": 25400.50  # CRITICAL: This field required for fee simulation
}

# AIDEV-INTEGRATE-CLAUDE: Extend existing PriceCacheManager
class EnhancedPriceCacheManager(PriceCacheManager):
    def fetch_ochlv_data(self, pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]
    def get_volume_for_position(self, position: Position) -> List[float]
    def validate_volume_completeness(self, position: Position) -> bool
```

### **Success Metrics for Phase 1**
- [ ] Volume data successfully collected for 100% of existing positions
- [ ] Raw cache system operational without breaking existing functionality  
- [ ] Data validation shows <10% variance between simulated and actual fee accumulation
- [ ] Performance acceptable: process 50 positions in <30 seconds for volume collection
- [ ] Integration: EnhancedPriceCacheManager works with existing analysis_runner.py calls

## 📚 Architectural Decisions & Simplifications

### **Data Architecture Decisions**
- **Raw OCHLV Storage:** Prioritize flexibility over storage efficiency for future analysis needs.
- **Monthly Cache Organization:** Balance between file count and data access patterns.
- **Backward Compatibility:** Maintain dual cache system during transition to minimize risk.

### **Cache Management & State (Key Decisions from Phase 1)**
- **Pragmatic Time-Based Cache Expiry ("2-Day Rule"):** To prevent wasting API credits on permanent data gaps (e.g., due to low liquidity on old positions), the system will NOT attempt to fetch missing data for any position that was closed more than two days ago. This is a simple, automatic, and robust solution.
- **Rejected Complex Cache State Management:** We consciously decided against implementing a complex cache state system (e.g., using a `cache_state.json` file or marker files with `Complete`/`Partially Complete` statuses). The "2-Day Rule" was deemed a much simpler and more effective solution for the identified problem, avoiding unnecessary architectural complexity.
- **User-Controlled Fetching Modes:** The cache fetching orchestrator provides two clear modes: "Fill Gaps Only" (default, efficient mode that respects the 2-Day Rule) and "Force Refetch All" (for complete data refreshes), giving the user full control.

### **Fee Simulation Simplifications**
- **Proportional Volume Distribution:** Assume uniform volume distribution across position timeline
- **Distance Impact Factor:** Use simplified 2/3 range multiplier for bid-ask strategies
- **Market Regime Stability:** Assume current fee rate environment persists
- **Position Independence:** Ignore correlation effects between simultaneous positions

### **Performance Trade-offs**
- **User-Defined Ranges:** Accept computational cost for flexibility over preset optimization
- **Parallel Processing:** Defer until Phase 4 based on actual performance needs
- **Statistical Significance:** Focus on practical significance over academic statistical rigor

### **Conscious Omissions**
- **Real-time Fee Calculation:** Meteora's exact fee algorithm (use approximation)
- **Slippage Modeling:** Assume perfect execution at candle close prices
- **Capital Correlation:** Portfolio-level position interaction effects
- **Market Regime Detection:** Bull/bear market impact on optimal parameters

## ⚠️ Known Issues & Risks

### **Technical Risks**
- **API Rate Limits:** Volume data collection may require additional API credits ✅ Resolved: Offline-first approach implemented
- **Cache Migration Complexity:** Risk of data loss during cache architecture change ✅ Resolved: Parallel cache system successful
- **Performance Scaling:** Unknown computational requirements for large-scale simulation ✅ Resolved: Phase 3A meets performance targets

### **Phase 3B Technical Risks**

- **LP Valuation Accuracy:** Simplified fee model may not reflect Meteora DLMM reality accurately
- **Post-Close Data Coverage:** Historical price data may have gaps for older positions
- **Simulation Complexity:** Fee allocation and LP position valuation requires complex mathematics

### **Business Logic Risks**
- **Fee Simulation Accuracy:** Simplified fee model may not reflect reality accurately
- **Statistical Validity:** Limited historical data may not provide significant results
- **Parameter Correlation:** TP/SL optimization may have complex interdependencies
- **Statistical Validity:** Limited historical data may not provide significant results for ML optimization
- **Parameter Correlation:** TP/SL optimization may have complex interdependencies not captured in linear analysis
- **Market Condition Changes:** Historical patterns may not predict future performance

### **Data Quality Risks**
- **Volume Data Completeness:** Historical volume data may have gaps
- **Position Timeline Gaps:** Some positions may lack sufficient post-close data
- **Market Condition Changes:** Historical patterns may not predict future performance

## 🚀 Session Closure & Next Steps

### **What's Next**
*[Generated when closing current session]*

### **Proposed Prompt for New Instance**
*[Generated when transitioning to next phase or new session]*

```
You are working on TP/SL Optimizer Module for SOL Decoder LP Strategy Optimization Project.

CRITICAL CONTEXT:
- Read CLAUDE.md for general project guidelines
- Read TP_SL_OPTIMIZER.md for module-specific requirements
- Current Phase: [X] - [Phase Name]
- Last session completed: [Specific achievements]

BUSINESS LOGIC PRIORITIES:
1. Fee accumulation affects SL triggering: position_value = price_value + accumulated_fees
2. Volume data drives fee simulation accuracy
3. Maintain backward compatibility with existing pipeline
4. Validate all simulation logic against known position outcomes

INTEGRATION REQUIREMENTS:
- Extend existing PriceCacheManager class
- Work with current Position model from core/models.py
- Integrate with analysis_runner.py workflow
- Add optimization results to portfolio reports

CURRENT TASK: [Specific next objective]

Key files to examine first:
- reporting/price_cache_manager.py (extend for volume data)
- core/models.py (Position class structure)
- simulations/spot_vs_bidask_simulator.py (existing fee calculation logic)

VALIDATION TARGET: [Specific success metric for current task]

Proceed with implementation, following stage-gate approach - validate each component before building next layer.
```

## 📝 Session History

### **2025-01-22: Module Specification & Planning**
- Created comprehensive specification document
- Defined 5-phase implementation plan
- Established architectural decisions and simplifications
- Identified key risks and mitigation strategies

### **2025-07-23: Phase 1 Implementation & Refactoring**
- Implemented `EnhancedPriceCacheManager` for OCHLV+Volume data.
- Created a robust, offline-first caching system with a parallel `raw/` cache directory.
- Refactored `main.py`, moving complex logic into dedicated `data_fetching` and `tools` modules to resolve circular dependencies and improve maintainability.
- Established a `utils/common.py` module for shared helper functions.
- Implemented a pragmatic "2-Day Rule" to automatically handle permanent data gaps without complex state management, saving API credits.
- Developed user-friendly menus for managing and debugging the new cache system.
- **Outcome: Phase 1 is complete and the system is architecturally sound for the next phase.**

### **2025-07-26: Phase 3A Completion Summary**

- Status: ✅ COMPLETE - Peak PnL extraction from logs operational
- Data Quality: >90% of positions have valid peak PnL data extracted
- Performance: Meets <30s target for 100 positions
- Configuration: Fully configurable via YAML with reasonable defaults
- Integration: Seamlessly integrated with existing pipeline, no breaking changes

**Transition to Phase 3B**0
- Ready for implementation: Post-close data extension and simulation engine
- Foundation established: Peak PnL baselines, mathematical frameworks, cache infrastructure
-Next session priority: Extend cache manager for post-close data and implement LP position valuation

- Module Status: Phase 3A - Complete ✅
- Next Priority: Phase 3B - Post-Close Analysis & Simulation Engine
- Estimated Complexity: Medium-High (mathematical precision required for LP valuation)

### **Phase 4 Critical Simulation Debug & Fix (2025-07-28)**

**Problem:** The simulation engine produced unrealistic results, with ~97% of all exits classified as 'Out of Range' (OOR) on the very first candle. This led to a cascade of failures: 0% win rates, identical PnL across all TP/SL tests (flat heatmaps), and a non-functional interactive analysis tool.

**Root Cause:**
1.  **Instantaneous OOR Logic:** The core simulator in `range_test_simulator.py` treated an OOR event as an immediate exit, preventing any TP or SL conditions from ever being tested.
2.  **Static OOR Parameters:** The simulator used a hardcoded 30-minute timeout for OOR, failing to account for dynamic, position-specific parameters available in the logs.
3.  **Client-Side Aggregation Bug:** The JavaScript in `comprehensive_report.html` incorrectly displayed data for only a single position instead of aggregating results for an entire strategy, causing the `exit_breakdown` table to show incorrect counts.

**Resolution Implemented:**
- **Dynamic OOR Parameter Parsing:** A new function, `extract_oor_parameters`, was implemented in `parsing_utils.py` to parse the OOR timeout (in minutes) and price threshold (in percent) directly from the log files for each position.
- **Stateful Simulation Engine:** The `_find_exit_in_timeline` method in `range_test_simulator.py` was completely refactored. It now correctly implements a stateful, time-based OOR check, allowing TP and SL conditions to be evaluated during the OOR timeout period.
- **Data Pipeline Integration:** The `Position` model (`core/models.py`) was extended to store the new dynamic OOR parameters, and `log_extractor.py` was updated to populate these fields.
- **Report Aggregation Fix:** The JavaScript function `updateWhatIfAnalysis` in the HTML template was rewritten to correctly filter for *all* positions matching the selected TP/SL combination and properly sum their PnL and exit reasons.

**Status:** The core simulation logic has been fixed. The system is now capable of realistically testing the TP/SL grid and generating meaningful, aggregated results.

### **Phase 4 Critical Simulation Debug & Fix (2025-08-22)**

**Problem:** The simulation engine produced unrealistic results, with ~97% of all exits classified as 'Out of Range' (OOR) on the very first candle. This led to a cascade of failures: 0% win rates, identical PnL across all TP/SL tests (flat heatmaps), and a non-functional interactive analysis tool.

**Root Cause:**
1.  **Instantaneous OOR Logic:** The core simulator in `range_test_simulator.py` treated an OOR event as an immediate exit, preventing any TP or SL conditions from ever being tested.
2.  **Static OOR Parameters:** The simulator used a hardcoded 30-minute timeout for OOR, failing to account for dynamic, position-specific parameters available in the logs.
3.  **Client-Side Aggregation Bug:** The JavaScript in `comprehensive_report.html` incorrectly displayed data for only a single position instead of aggregating results for an entire strategy, causing the `exit_breakdown` table to show incorrect counts.

**Resolution Implemented:**
- **Dynamic OOR Parameter Parsing:** A new function, `extract_oor_parameters`, was implemented in `parsing_utils.py` to parse the OOR timeout (in minutes) and price threshold (in percent) directly from the log files for each position.
- **Stateful Simulation Engine:** The `_find_exit_in_timeline` method in `range_test_simulator.py` was completely refactored. It now correctly implements a stateful, time-based OOR check, allowing TP and SL conditions to be evaluated during the OOR timeout period.
- **Data Pipeline Integration:** The `Position` model (`core/models.py`) was extended to store the new dynamic OOR parameters, and `log_extractor.py` was updated to populate these fields.
- **Report Aggregation Fix:** The JavaScript function `updateWhatIfAnalysis` in the HTML template was rewritten to correctly filter for *all* positions matching the selected TP/SL combination and properly sum their PnL and exit reasons.

**Status:** The core simulation logic has been fixed. The system is now capable of realistically testing the TP/SL grid and generating meaningful, aggregated results.

### **Phase 4B Interactive Tool Frontend Fix (2025-08-22)**

**Problem:** Despite a functional backend and correct data generation, the "Interactive TP/SL Explorer" (Phase 4B) in the HTML report remained empty and non-functional.

**Root Cause:**
A JavaScript syntax error was identified in `reporting/templates/comprehensive_report.html`. An extraneous closing curly brace `}` prematurely terminated the main `updateWhatIfAnalysis` function, rendering the table population logic unreachable. This "dead code" was a remnant of a previous, improperly resolved code merge, which also contained a non-functional, alternative implementation for rendering table rows.

**Resolution Implemented:**
- The JavaScript code within the HTML template was refactored to remove the erroneous curly brace and the entire block of unreachable, legacy code.
- This cleanup restored the correct structure of the `updateWhatIfAnalysis` function, allowing the existing, correct logic for rendering the results table to execute properly.

**Status:** The interactive "what-if" tool is now fully functional. The data pipeline from backend simulation to frontend visualization is complete and working as intended. Phase 4 is officially stable and complete.