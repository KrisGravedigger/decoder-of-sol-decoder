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
**Goal:** Implement parameter range simulation framework

- [ ] Build user-configurable TP/SL range testing interface
- [ ] Implement position-level "what-if" simulation logic
- [ ] Create portfolio-level aggregation and impact analysis
- [ ] Generate comparative performance reports

**Phase Questions:**
- Should we implement parallel processing for large simulation sets?
- How to handle positions that would never trigger with certain TP/SL levels?
- What statistical significance testing should we apply to results?

### **Phase 5: Optimization Engine** 📋 *PLANNED*
**Goal:** Identify statistically optimal parameter combinations
- [ ] Implement universal SL floor discovery algorithm
- [ ] Create TP efficiency analysis (frequency vs. magnitude trade-offs)
- [ ] Build recommendation engine with confidence intervals
- [ ] Integrate with existing portfolio analytics and reporting

**Phase Questions:**
- Should optimization be strategy-specific (bidask vs spot) or universal?
- How to weight different time periods (recent vs. historical performance)?
- What's the minimum sample size for statistically significant recommendations?


### 🔧 Current Phase Status: Phase 3B Complete

**Completed Objectives:**
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

- **Module Status:** Phase 3B - Complete ✅
- **Next Priority:** Phase 4 - TP/SL Range Testing
- **Estimated Complexity:** Medium (requires careful design of simulation logic and reporting)

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

## 📊 Current Status

### **Completed**
- [x] Phase 1: Data Infrastructure. The system can now reliably collect, store, and manage OCHLV+Volume data.
- [x] Phase 2: Post-Position Analysis.
- [x] Phase 3A: Log-Based Peak PnL Extraction. Real historical peak PnL data extracted from bot logs with configurable parameters.

### **In Progress**
Planning for Phase 3B: Post-Close Analysis with mathematical LP position valuation.

### **Ready for Implementation**

 Mathematical framework for LP position valuation (research complete)
 Volume-proportional fee allocation algorithms (formulas documented)
 Peak PnL baseline data (Phase 3A complete)
 Cache infrastructure for post-close data (Phase 2 architecture ready)

### **Blocked/Pending**
- [ ] Volume data API endpoint identification (Moralis documentation review needed)
- [ ] Cache migration strategy decision (parallel vs. sequential)

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