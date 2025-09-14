# 4D TP/SL/TLS Optimization Module Specification

## 🔗 Background
This module extends the SOL Decoder LP Strategy Optimization Project with Trailing Stop Loss (TLS) functionality. For general project context, coding conventions, and architecture guidelines, see [CLAUDE.md](CLAUDE.md). For foundation TP/SL optimization context, see [tp_sl_optimizer_spec.md](tp_sl_optimizer_spec.md).

## 🤖 AI Assistant Instructions (Lex Specialis)

### **Critical Business Logic Priority**
1. **TLS activation logic:** TLS only activates when position reaches TLS_activation profit level
2. **TLS trailing mechanism:** Dynamic SL = max(original_SL, peak_PnL - TLS_trail)
3. **Parameter validation:** TP > TLS_activation, TLS_trail < TLS_activation (business sense constraints)
4. **4D data visualization:** Grid-based mini-heatmaps with shared color scale for comparability
5. **Baseline comparison:** Always compare TLS performance vs best non-TLS combination

### **Implementation Strategy**
- **Hybrid visualization approach:** Strategy overview scatter + grid mini-heatmaps + grouped ranking table
- **Progressive enhancement:** Extend existing TP/SL infrastructure rather than rebuild
- **Desktop-first:** Target minimum 14-inch laptop screens, no mobile optimization
- **Performance-conscious:** Smart combination filtering to reduce computational overhead

### **Code Integration Points**
```python
# REQUIRED EXTENSIONS from existing codebase:
from simulations.range_test_simulator import TpSlRangeSimulator  # Extend for TLS
from reporting.lp_position_valuator import simulate_position_exit  # Add TLS logic
from reporting.visualizations.interactive.range_test_charts import create_heatmap_grid  # Extend to 4D

# NEW INTEGRATION HOOKS:
# simulations/tls_range_simulator.py: New TLS-aware simulation engine
# reporting/visualizations/interactive/tls_4d_charts.py: 4D visualization components
# reporting/html_report_generator.py: Add 4D TLS optimization section
```

### **Module-Specific Anchor Comments**
```python
# AIDEV-TLS-CLAUDE: - Trailing Stop Loss business logic implementation
# AIDEV-4D-VIZ-CLAUDE: - 4-dimensional data visualization and filtering
# AIDEV-GRID-CLAUDE: - Mini-heatmap grid generation and layout
# AIDEV-BASELINE-CLAUDE: - TLS vs non-TLS performance comparison logic
```

### **Data Dependencies & Validation**
```python
# REQUIRED DATA STRUCTURES (extend existing):
TlsSimulationResult:
    position_id: str
    strategy_instance_id: str
    tp_level: float
    sl_level: float
    tls_activation: float
    tls_trail: float
    simulated_pnl: float
    exit_reason: str  # "TP", "SL", "TLS", "EOD"
    baseline_pnl: float  # Best non-TLS result for this position

# VALIDATION TARGETS:
# TLS logic accuracy: Positions should exit at exactly peak_PnL - trail when TLS triggers
# Grid visualization: All mini-heatmaps use shared color scale for comparability
# Performance: Process 1000 positions × 4D parameter grid <10min
# Baseline comparison: 100% accuracy in identifying best non-TLS performance
```

## 🎯 Core Objectives
**Primary Goal:** Provide comprehensive 4-dimensional optimization analysis for TP/SL/TLS parameters with intuitive visualization enabling identification of optimal parameter "islands"

**Success Criteria:**
- Enable visual identification of optimal parameter combinations across 4D space
- Provide clear comparison between TLS-enabled and baseline (non-TLS) performance
- Support rapid strategy comparison through overview visualizations
- Maintain sub-10-minute analysis time for typical datasets

**Business Context:**
- Trailing Stop Loss adds complexity but potential for risk reduction and profit optimization
- 4D parameter space requires sophisticated visualization to avoid overwhelming users
- Users need to quickly identify whether TLS provides meaningful benefit over simpler TP/SL approach

## 📋 Master Implementation Plan

## 📋 Phase 1: TLS Simulation Engine - Detailed Implementation Plan

### **Goal:** Extend existing simulation infrastructure with TLS business logic

**Target Completion Time:** 2-3 sessions

### **Prerequisites & Context Analysis**
**Required Modules for Context:**
- `simulations/range_test_simulator.py` - Base TP/SL simulation logic
- `reporting/lp_position_valuator.py` - Position valuation and exit logic  
- `core/models.py` - Position data model structure
- `reporting/config/portfolio_config.yaml` - Configuration structure
- `extraction/parsing_utils.py` - Position parsing and data preparation
- `reporting/strategy_instance_detector.py` - Strategy grouping logic

### **Implementation Tasks**

#### **Task 1.1: Configuration Extension** 
**File:** `reporting/config/portfolio_config.yaml`
**Action:** Add TLS configuration section
```yaml
# Add to existing portfolio_config.yaml file:
tls_range_testing:
  enable: true
  tls_activation_range: [3, 4, 5, 6, 7, 8]
  tls_trail_range: [1, 2, 3, 4, 5]
  inherit_tp_sl_ranges: true
  enable_smart_filtering: true
  max_combinations_per_position: 10000
  generate_baseline_comparison: true
```

#### **Task 1.2: Data Model Extension**
**File:** `core/models.py` 
**Action:** Extend TLS simulation result structure
```python
@dataclass
class TlsSimulationResult:
    position_id: str
    strategy_instance_id: str
    tp_level: float
    sl_level: float
    tls_activation: float
    tls_trail: float
    simulated_pnl: float
    exit_reason: str  # "TP", "SL", "TLS", "OOR", "END"
    strategy_best_non_tls_pnl: float
    
    def to_csv_row(self) -> Dict[str, Any]:
        """Convert to CSV-compatible dictionary"""
```

#### **Task 1.3: TLS Simulation Logic**
**File:** `simulations/tls_range_simulator.py` (NEW)
**Action:** Create TLS-aware simulation engine extending existing infrastructure

**Core Class Structure:**
```python
class TlsRangeSimulator:
    def __init__(self, enhanced_price_cache_manager, config):
        # Initialize with existing infrastructure
        
    def simulate_tls_for_position(self, position, tp, sl, tls_activation, tls_trail):
        """
        Core TLS simulation logic:
        1. Reuse existing OCHLV data fetching from EnhancedPriceCacheManager
        2. Reuse existing LP position valuation logic
        3. Add TLS activation and trailing logic
        4. Integrate existing OOR detection
        5. Return consistent exit_reason format
        """
        
    def generate_valid_combinations(self, tp_range, sl_range, tls_activation_range, tls_trail_range):
        """Smart filtering: TP > TLS_activation, TLS_trail < TLS_activation"""
        
    def calculate_strategy_baseline(self, strategy_positions, tp_sl_results):
        """Find best non-TLS performance per strategy"""
        
    def run_tls_analysis(self, positions_df):
        """Main analysis orchestrator"""
```

#### **Task 1.4: Integration with LP Position Valuator**
**File:** `reporting/lp_position_valuator.py`
**Action:** Extend existing position simulation with TLS logic
```python
def simulate_position_exit_with_tls(position_data, tp_level, sl_level, tls_activation, tls_trail):
    """
    Extend existing simulate_position_exit function:
    - Maintain existing TP/SL/OOR logic
    - Add TLS activation tracking
    - Add dynamic SL adjustment
    - Return TLS exit reason when appropriate
    """
```

#### **Task 1.5: Baseline Comparison System**
**File:** `simulations/baseline_comparator.py` (NEW)
**Action:** Create per-strategy baseline identification
```python
class StrategyBaselineComparator:
    def identify_best_non_tls_performance(self, strategy_positions, existing_tp_sl_results):
        """
        For each strategy:
        1. Find all TP/SL combinations from existing range testing
        2. Identify highest performing combination
        3. Return mapping: strategy_id -> best_non_tls_pnl
        """
        
    def calculate_tls_benefit(self, tls_result, baseline_pnl):
        """Calculate (tls_pnl - baseline_pnl) / baseline_pnl * 100"""
```

#### **Task 1.6: Data Pipeline Integration**  
**File:** `main.py`
**Action:** Add TLS analysis option to menu
```python
# Add menu option for TLS analysis
"6": "Run 4D TLS Optimization Analysis"
```

**File:** `reporting/orchestrator.py`
**Action:** Integrate TLS analysis into reporting pipeline
```python
def run_tls_optimization_analysis():
    """
    Orchestrate TLS analysis:
    1. Load existing positions and TP/SL results
    2. Run TLS simulation
    3. Generate baseline comparisons
    4. Export results for visualization
    """
```

### **Validation & Testing Strategy**

#### **Unit Tests:**
- TLS activation logic (should activate at exact percentage)
- Dynamic SL calculation (max of original SL and trail)
- Exit reason accuracy (TP vs SL vs TLS vs OOR vs END)
- Parameter validation (invalid combinations rejected)

#### **Integration Tests:**
- Compatibility with existing Position model
- Correct baseline identification per strategy
- Performance under load (500 positions × 200 combinations)
- Data export format consistency

#### **Business Logic Tests:**
```python
# Test scenarios:
test_tls_activation_behavior()  # TLS activates at 5%, position reaches 6%
test_tls_trailing_behavior()   # Peak 8%, trail 3%, exits at 5%
test_tls_vs_sl_priority()      # TLS exit vs original SL
test_baseline_comparison()     # Correct best non-TLS identification
```

### **Success Criteria:**
- [ ] TLS simulation produces logically consistent exit behavior
- [ ] All invalid parameter combinations filtered correctly  
- [ ] Baseline comparison identifies best non-TLS per strategy with 100% accuracy
- [ ] Performance target: <10 minutes for 500 positions × 200 combinations
- [ ] Exit reasons maintain compatibility: TP, SL, TLS, OOR, END
- [ ] Integration with existing data pipeline works seamlessly

### **Risk Mitigation:**
- **Performance Risk:** Implement circuit breaker at 10,000 combinations per position
- **Logic Risk:** Extensive unit testing of TLS state transitions
- **Integration Risk:** Reuse existing infrastructure where possible
- **Data Risk:** Validate baseline comparison against known results

### **Deliverables:**
1. Working TLS simulation engine
2. Configuration integration in YAML
3. Data model extensions
4. Baseline comparison system
5. Unit and integration tests
6. Performance validation results

## 🔮 Future Implementation Phases

### **Phase 6: TLS Log Extraction & Live Data Integration** 🔲 *FUTURE REQUIREMENT*
**Goal:** Extract actual TLS closures from SOL Decoder logs and integrate with historical analysis

**Trigger:** When SOL Decoder bot starts generating positions with TLS and closing them via TLS mechanism

**Required Components:**
- Extend `extraction/parsing_utils.py` with TLS close reason regex patterns
- Update close reason classification in `log_extractor.py` 
- Modify existing reports to include TLS as separate close reason category
- Validate TLS simulation accuracy against real TLS closures
- Update portfolio analytics to account for TLS close behavior

**Business Impact:**
- Enable validation of TLS simulation accuracy vs real bot behavior
- Provide complete close reason analytics including TLS category
- Support optimization based on actual TLS performance data

**Implementation Notes:**
- Wait for real TLS positions to appear in logs before implementing
- Use actual TLS close patterns to refine simulation logic
- May require regex pattern development based on bot output format

---

## 🚀 Phase 1 Implementation Prompt

**Use this prompt when starting Phase 1 implementation:**

```
You are implementing Phase 1 of the 4D TP/SL/TLS Optimization Module for the SOL Decoder LP Strategy Optimization Project.

CRITICAL CONTEXT - READ FIRST:
- Review CLAUDE.md for general project guidelines and coding conventions
- Review tp_sl_optimizer_spec.md for existing TP/SL infrastructure context
- Review tls_4d_optimization_spec.md for complete module specification
- Current implementation target: Phase 1 - TLS Simulation Engine

MAIN HYPOTHESIS TO VALIDATE:
TLS will likely worsen performance of current optimal TP/SL combinations, but will enable safe exploration of higher TP levels. Goal: discover higher TP opportunities made viable by TLS protection.

BUSINESS LOGIC PRIORITIES:
1. TLS activation: Only activates when position reaches tls_activation profit level
2. Dynamic SL: max(original_SL, peak_PnL - tls_trail) when TLS active
3. Exit priorities: TP → SL/TLS → OOR (reuse existing) → END
4. Baseline comparison: Compare best TLS vs best non-TLS PER STRATEGY
5. Parameter validation: TP > TLS_activation, TLS_trail < TLS_activation

REQUIRED MODULES FOR CONTEXT:
- simulations/range_test_simulator.py (base simulation logic)
- reporting/lp_position_valuator.py (position valuation)
- core/models.py (data structures)
- reporting/config/portfolio_config.yaml (configuration)
- extraction/parsing_utils.py (data parsing)
- reporting/strategy_instance_detector.py (strategy grouping)

KEY INTEGRATION POINTS:
- Extend existing range testing infrastructure (don't rebuild)
- Reuse EnhancedPriceCacheManager for OCHLV data
- Maintain exit_reason compatibility: TP, SL, TLS, OOR, END
- Generate strategy_best_non_tls_pnl for baseline comparison

IMPLEMENTATION TASKS:
1. Add tls_range_testing config section to portfolio_config.yaml
2. Create TlsSimulationResult data model in core/models.py
3. Implement TlsRangeSimulator in simulations/tls_range_simulator.py
4. Extend lp_position_valuator.py with TLS exit logic
5. Create baseline comparison system
6. Integrate with main menu and orchestrator

VALIDATION TARGETS:
- TLS logic accuracy: Exact activation and trailing behavior
- Parameter validation: Invalid combinations rejected
- Performance: <10min for 500 positions × 200 combinations
- Baseline accuracy: 100% correct best non-TLS identification per strategy
- Exit reason compatibility maintained

CRITICAL TECHNICAL REQUIREMENTS:
- max_combinations_per_position: 10000 (performance circuit breaker)
- Smart filtering: Skip TP <= TLS_activation combinations
- Reuse existing OOR detection logic
- Per-strategy baseline comparison (not per-position)

Start with Task 1.1 (Configuration Extension) and proceed systematically through all tasks. Validate each component before proceeding to next.
```

**Technical Requirements:**
```python
# AIDEV-TLS-CLAUDE: Core TLS simulation logic
def simulate_position_with_tls(position_data, tp_level, sl_level, tls_activation, tls_trail):
    """
    Simulate position with Trailing Stop Loss logic.
    
    Business Logic:
    - TLS activates only when position reaches tls_activation profit level
    - Once active, dynamic SL = max(original_SL, peak_PnL - tls_trail)
    - Exit on first condition: TP reached, SL/TLS triggered, or end of data
    """
    peak_pnl = 0.0
    tls_activated = False
    dynamic_sl = -sl_level
    
    for candle in position_data:
        current_pnl = calculate_lp_pnl(candle)
        
        # Update peak and check TLS activation
        if current_pnl > peak_pnl:
            peak_pnl = current_pnl
            
        if not tls_activated and peak_pnl >= tls_activation:
            tls_activated = True
            
        # Update dynamic SL if TLS is active
        if tls_activated:
            trailing_sl = peak_pnl - tls_trail
            dynamic_sl = max(dynamic_sl, trailing_sl)
        
        # Check exit conditions
        if current_pnl >= tp_level:
            return current_pnl, "TP"
        if current_pnl <= dynamic_sl:
            return current_pnl, "TLS" if tls_activated and current_pnl > -sl_level else "SL"
    
    return current_pnl, "EOD"
```

**Smart Filtering Logic:**
```python
# AIDEV-4D-VIZ-CLAUDE: Reduce computational overhead through business logic constraints
def generate_valid_combinations(tp_range, sl_range, tls_activation_range, tls_trail_range):
    """
    Generate only valid TLS parameter combinations based on business logic:
    - TP > TLS_activation (must be able to reach activation level)
    - TLS_trail < TLS_activation (trail distance should be reasonable)
    - TLS_activation >= 3% (minimum meaningful activation level)
    """
    valid_combinations = []
    for tp in tp_range:
        for sl in sl_range:
            for tls_act in tls_activation_range:
                for tls_trail in tls_trail_range:
                    if tp > tls_act and tls_trail < tls_act and tls_act >= 3:
                        valid_combinations.append((tp, sl, tls_act, tls_trail))
    return valid_combinations
```

**Configuration Extension:**
```yaml
# PHASE 1: 4D TLS Range Testing Configuration
tls_range_testing:
  enable: true
  
  # TLS parameter ranges
  tls_activation_range: [3, 4, 5, 6, 7, 8]  # Activation at X% profit
  tls_trail_range: [1, 2, 3, 4, 5]          # Trail X% below peak
  
  # Existing TP/SL ranges (inherit from range_testing section)
  inherit_tp_sl_ranges: true
  
  # Performance optimization
  enable_smart_filtering: true               # Skip invalid combinations
  max_combinations_per_position: 1000       # Performance circuit breaker
  
  # Baseline comparison
  generate_baseline_comparison: true         # Always compare vs best non-TLS
```

**Success Metrics:**
- [ ] TLS logic correctly implemented with activation and trailing behavior
- [ ] Parameter validation prevents invalid combinations (TP <= TLS_activation)
- [ ] Baseline comparison accurately identifies best non-TLS performance
- [ ] Performance under 10 minutes for 500 positions × 200 valid combinations
- [ ] Integration with existing Position model and data pipeline

## 📋 Phase 2: Strategy Overview Visualization - Detailed Implementation Plan

### **Goal:** Create strategy comparison interface enabling rapid identification of high-performing strategies

**Target Completion Time:** 1-2 sessions

### **Prerequisites & Context Analysis**
**Required Modules for Context:**
- `simulations/tls_range_simulator.py` - TLS simulation results (Phase 1 output)
- `reporting/visualizations/interactive/range_test_charts.py` - Existing chart infrastructure
- `reporting/html_report_generator.py` - HTML report integration
- `simulations/baseline_comparator.py` - Baseline comparison data
- `reporting/strategy_instance_detector.py` - Strategy grouping and naming
- `reporting/config/portfolio_config.yaml` - Visualization configuration

### **Implementation Tasks**

#### **Task 2.1: Strategy Scatter Plot Visualization**
**File:** `reporting/visualizations/interactive/tls_strategy_charts.py` (NEW)
**Action:** Create strategy overview scatter plot with performance clouds

**Core Visualization Requirements:**
```python
def create_strategy_overview_scatter(tls_results_df, baseline_data):
    """
    Strategy Overview Scatter Plot:
    
    Layout:
    - X-axis: Strategy names (categorical, rotated labels for readability)
    - Y-axis: PnL percentages (continuous scale)
    - Points: Individual TLS combination results (small semi-transparent dots)
    - Highlights: 
      * Green dot: Best TLS result per strategy (larger, fully opaque)
      * Yellow dot: Best non-TLS result per strategy (medium, fully opaque)
    
    Interactive Features:
    - Clickable strategy names trigger filtering for detailed grid view
    - Hover tooltips: Strategy name, TP/SL/TLS parameters, PnL value
    - Performance density visualization (point clustering indicates optimization "hotspots")
    
    Visual Design:
    - Color intensity based on result frequency in top 10% performers
    - Point size scaling: individual results (3px), best TLS (8px), best non-TLS (6px)
    - Strategy name rotation: 45 degrees for readability with many strategies
    """
    
    # Data preparation
    strategy_groups = tls_results_df.groupby('strategy_instance_id')
    scatter_data = []
    
    for strategy_id, group in strategy_groups:
        # Individual combination points
        for _, row in group.iterrows():
            scatter_data.append({
                'strategy': strategy_id,
                'pnl': row['simulated_pnl'],
                'tp': row['tp_level'],
                'sl': row['sl_level'],
                'tls_act': row['tls_activation'],
                'tls_trail': row['tls_trail'],
                'point_type': 'individual'
            })
        
        # Best TLS result (green highlight)
        best_tls = group.loc[group['simulated_pnl'].idxmax()]
        scatter_data.append({
            'strategy': strategy_id,
            'pnl': best_tls['simulated_pnl'],
            'tp': best_tls['tp_level'],
            'sl': best_tls['sl_level'],
            'tls_act': best_tls['tls_activation'],
            'tls_trail': best_tls['tls_trail'],
            'point_type': 'best_tls'
        })
        
        # Best non-TLS result (yellow highlight)
        baseline_pnl = baseline_data.get(strategy_id, 0)
        scatter_data.append({
            'strategy': strategy_id,
            'pnl': baseline_pnl,
            'point_type': 'best_non_tls'
        })
    
    return create_plotly_scatter(scatter_data)
```

#### **Task 2.2: Global Top Combinations Table**
**File:** `reporting/visualizations/interactive/tls_strategy_charts.py`
**Action:** Create comprehensive ranking table with strategy navigation

```python
def create_global_top_combinations_table(tls_results_df, baseline_data, top_count=10):
    """
    Global Top 10 Combinations Table:
    
    Columns:
    - Rank: 1-10 numeric ranking
    - Strategy: Clickable strategy name (triggers grid filter)
    - TP: Take profit percentage
    - SL: Stop loss percentage
    - TLS Act: TLS activation percentage
    - TLS Trail: TLS trail percentage
    - TLS PnL: Performance with TLS
    - Baseline PnL: Best non-TLS performance for this strategy
    - TLS Benefit: Percentage improvement ((tls_pnl - baseline_pnl) / baseline_pnl * 100)
    
    Features:
    - Color-coded TLS Benefit: Green (positive), Red (negative), Gray (neutral ±1%)
    - Clickable strategy names set filter for detailed 4D grid view
    - Sort by TLS PnL descending (fixed, no user sorting needed)
    - Responsive table design with proper column sizing
    """
    
    # Calculate TLS benefit for all combinations
    enriched_results = []
    for _, row in tls_results_df.iterrows():
        strategy_baseline = baseline_data.get(row['strategy_instance_id'], 0)
        tls_benefit = ((row['simulated_pnl'] - strategy_baseline) / strategy_baseline * 100) if strategy_baseline > 0 else 0
        
        enriched_results.append({
            'strategy_instance_id': row['strategy_instance_id'],
            'tp_level': row['tp_level'],
            'sl_level': row['sl_level'],
            'tls_activation': row['tls_activation'],
            'tls_trail': row['tls_trail'],
            'tls_pnl': row['simulated_pnl'],
            'baseline_pnl': strategy_baseline,
            'tls_benefit': tls_benefit
        })
    
    # Sort by TLS PnL and take top N
    top_combinations = sorted(enriched_results, key=lambda x: x['tls_pnl'], reverse=True)[:top_count]
    
    return create_interactive_table(top_combinations)
```

#### **Task 2.3: Strategy Performance Summary Statistics**
**File:** `reporting/visualizations/interactive/tls_strategy_charts.py`
**Action:** Generate strategy-level performance insights

```python
def create_strategy_performance_summary(tls_results_df, baseline_data):
    """
    Strategy Performance Summary:
    
    Metrics per strategy:
    - Best TLS Performance: Highest PnL with TLS enabled
    - Best Baseline Performance: Best non-TLS performance
    - TLS Advantage: Percentage improvement of best TLS vs baseline
    - Optimization Potential: Range between worst and best TLS results
    - Parameter Sensitivity: Standard deviation of TLS results
    
    Output format: Dictionary for integration with HTML template
    """
    
    summary_stats = {}
    
    for strategy_id in tls_results_df['strategy_instance_id'].unique():
        strategy_data = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_id]
        baseline_pnl = baseline_data.get(strategy_id, 0)
        
        best_tls_pnl = strategy_data['simulated_pnl'].max()
        worst_tls_pnl = strategy_data['simulated_pnl'].min()
        avg_tls_pnl = strategy_data['simulated_pnl'].mean()
        std_tls_pnl = strategy_data['simulated_pnl'].std()
        
        tls_advantage = ((best_tls_pnl - baseline_pnl) / baseline_pnl * 100) if baseline_pnl > 0 else 0
        optimization_potential = best_tls_pnl - worst_tls_pnl
        
        summary_stats[strategy_id] = {
            'best_tls_pnl': best_tls_pnl,
            'baseline_pnl': baseline_pnl,
            'tls_advantage': tls_advantage,
            'optimization_potential': optimization_potential,
            'parameter_sensitivity': std_tls_pnl,
            'avg_performance': avg_tls_pnl,
            'total_combinations': len(strategy_data)
        }
    
    return summary_stats
```

#### **Task 2.4: Interactive Navigation System**
**File:** `reporting/templates/comprehensive_report.html`
**Action:** Add JavaScript for strategy filtering and navigation

```javascript
// Strategy Overview Navigation System
function initializeStrategyOverview() {
    // Strategy name click handlers
    document.querySelectorAll('.strategy-name-clickable').forEach(element => {
        element.addEventListener('click', function(e) {
            const strategyId = e.target.getAttribute('data-strategy-id');
            filterGridByStrategy(strategyId);
            scrollToGridSection();
            highlightSelectedStrategy(strategyId);
        });
    });
    
    // Global top combinations table strategy links
    document.querySelectorAll('.top-combo-strategy-link').forEach(element => {
        element.addEventListener('click', function(e) {
            e.preventDefault();
            const strategyId = e.target.getAttribute('data-strategy-id');
            filterGridByStrategy(strategyId);
            scrollToGridSection();
            updateFilterIndicator(strategyId);
        });
    });
}

function filterGridByStrategy(strategyId) {
    // Update strategy filter dropdown in grid section
    const strategySelect = document.getElementById('strategyFilter');
    if (strategySelect) {
        strategySelect.value = strategyId;
        strategySelect.dispatchEvent(new Event('change'));
    }
}

function highlightSelectedStrategy(strategyId) {
    // Visual feedback in scatter plot
    document.querySelectorAll('.strategy-highlight').forEach(el => {
        el.classList.remove('selected');
    });
    
    const selectedElement = document.querySelector(`[data-strategy-id="${strategyId}"]`);
    if (selectedElement) {
        selectedElement.classList.add('selected');
    }
}

function scrollToGridSection() {
    // Smooth scroll to 4D grid section
    const gridSection = document.getElementById('tls-4d-grid-section');
    if (gridSection) {
        gridSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
}
```

#### **Task 2.5: HTML Template Integration**
**File:** `reporting/templates/comprehensive_report.html`
**Action:** Add Strategy Overview section to TLS analysis

```html
<!-- Strategy Overview Section (add to TLS analysis section) -->
<div class="tls-strategy-overview">
    <h3>📊 Strategy Performance Overview</h3>
    <div class="overview-description">
        <p>Compare TLS performance across all strategies. Click strategy names to filter the detailed grid below.</p>
    </div>
    
    <!-- Strategy Scatter Plot -->
    <div class="chart-container">
        <div id="strategy-overview-scatter" style="height: 500px;"></div>
        <div class="chart-legend">
            <span class="legend-item">
                <span class="legend-dot green"></span> Best TLS Result
            </span>
            <span class="legend-item">
                <span class="legend-dot yellow"></span> Best Non-TLS Result
            </span>
            <span class="legend-item">
                <span class="legend-dot gray"></span> Individual Combinations
            </span>
        </div>
    </div>
    
    <!-- Global Top Combinations Table -->
    <div class="top-combinations-section">
        <h4>🏆 Top 10 TLS Combinations (All Strategies)</h4>
        <div id="global-top-combinations-table"></div>
    </div>
    
    <!-- Strategy Performance Summary -->
    <div class="performance-summary-section">
        <h4>📈 Strategy Performance Summary</h4>
        <div id="strategy-performance-summary"></div>
    </div>
</div>
```

#### **Task 2.6: Chart Generation Integration**
**File:** `reporting/html_report_generator.py`
**Action:** Integrate strategy overview charts into report generation

```python
def generate_tls_strategy_overview_charts(self, tls_data, baseline_data):
    """
    Generate strategy overview visualization components:
    1. Strategy scatter plot with performance clouds
    2. Global top combinations table
    3. Strategy performance summary statistics
    """
    
    from reporting.visualizations.interactive.tls_strategy_charts import (
        create_strategy_overview_scatter,
        create_global_top_combinations_table,
        create_strategy_performance_summary
    )
    
    # Generate scatter plot
    scatter_chart = create_strategy_overview_scatter(tls_data, baseline_data)
    
    # Generate top combinations table
    top_combinations_table = create_global_top_combinations_table(tls_data, baseline_data)
    
    # Generate performance summary
    performance_summary = create_strategy_performance_summary(tls_data, baseline_data)
    
    return {
        'strategy_scatter_chart': scatter_chart,
        'top_combinations_table': top_combinations_table,
        'performance_summary': performance_summary
    }
```

### **Validation & Testing Strategy**

#### **Visual Validation Tests:**
- Strategy scatter plot displays all data points correctly
- Green/yellow highlights clearly distinguish best results
- Clickable elements respond appropriately
- Performance clouds show meaningful clustering patterns

#### **Interactive Function Tests:**
- Strategy name clicks correctly filter grid section
- Top combinations table navigation works seamlessly
- Scroll behavior is smooth and targets correct sections
- Filter indicators update properly

#### **Data Accuracy Tests:**
```python
# Test scenarios:
test_scatter_plot_data_accuracy()      # All TLS results represented
test_highlight_point_identification()  # Best results correctly highlighted  
test_baseline_comparison_accuracy()    # Yellow dots match actual baseline
test_top_combinations_ranking()        # Top 10 correctly sorted by PnL
test_tls_benefit_calculation()         # TLS benefit percentages accurate
test_strategy_navigation_flow()        # Click → filter → scroll flow works
```

### **Success Criteria:**
- [ ] Strategy scatter plot enables rapid visual comparison of strategy performance
- [ ] Clickable navigation seamlessly connects overview to detailed analysis
- [ ] Top combinations table provides actionable insights with clear TLS benefits
- [ ] Performance summary quantifies optimization opportunities per strategy
- [ ] Interactive elements respond smoothly without performance degradation
- [ ] Visual design supports identification of high-performing strategy clusters

### **Risk Mitigation:**
- **Performance Risk:** Optimize scatter plot rendering for large datasets (>1000 points)
- **Usability Risk:** Ensure strategy names remain readable with rotation and truncation
- **Navigation Risk:** Provide clear visual feedback for selected strategies
- **Data Risk:** Validate baseline comparison accuracy against Phase 1 results

### **Deliverables:**
1. Complete strategy overview visualization module
2. Interactive navigation system with filtering
3. Global top combinations ranking table
4. Strategy performance summary statistics
5. HTML template integration
6. JavaScript interaction handlers

---

## 🚀 Phase 2 Implementation Prompt

**Use this prompt when starting Phase 2 implementation:**

```
You are implementing Phase 2 of the 4D TP/SL/TLS Optimization Module for the SOL Decoder LP Strategy Optimization Project.

CONTEXT FROM PHASE 1 SUCCESS:
- TLS simulation engine fully operational (simulations/tls_range_simulator.py)
- Baseline comparison system working (simulations/baseline_comparator.py)
- TLS analysis integrated into main menu (position 7)
- Comprehensive report integration completed
- Data models and configuration established

PHASE 2 OBJECTIVE:
Create strategy comparison interface enabling rapid identification of high-performing strategies through visual overview and clickable navigation.

CRITICAL REQUIREMENTS:
1. Strategy scatter plot: X-axis strategy names, Y-axis PnL, points for all combinations
2. Dual highlights: Green dot (best TLS), Yellow dot (best non-TLS baseline) per strategy
3. Clickable navigation: Strategy names filter 4D grid view (seamless connection)
4. Global top 10 table: Best TLS combinations across all strategies with benefit calculation
5. Performance summary: Per-strategy statistics and optimization insights

REQUIRED MODULES FOR CONTEXT:
- simulations/tls_range_simulator.py (TLS simulation results)
- simulations/baseline_comparator.py (baseline comparison data)
- reporting/visualizations/interactive/range_test_charts.py (chart infrastructure)
- reporting/html_report_generator.py (report integration)
- reporting/templates/comprehensive_report.html (template structure)
- reporting/strategy_instance_detector.py (strategy naming)

IMPLEMENTATION TASKS:
1. Create tls_strategy_charts.py with scatter plot and table generation
2. Add strategy overview section to HTML template
3. Implement JavaScript navigation for strategy filtering
4. Integrate chart generation into html_report_generator.py
5. Add performance summary statistics calculation
6. Test interactive navigation flow (click → filter → scroll)

KEY DESIGN SPECIFICATIONS:
- Point sizes: Individual (3px), Best TLS (8px), Best non-TLS (6px)
- Color scheme: Green (best TLS), Yellow (best baseline), Gray (individual)
- Strategy name rotation: 45 degrees for readability
- TLS benefit calculation: (tls_pnl - baseline_pnl) / baseline_pnl * 100
- Table sorting: Fixed by TLS PnL descending (no user sorting)

VALIDATION TARGETS:
- Visual clarity: Strategy performance differences easily identifiable
- Navigation accuracy: Clicks correctly filter and scroll to grid section
- Data integrity: All baseline comparisons match Phase 1 calculations
- Performance: Smooth rendering with large datasets (1000+ combinations)
- User experience: Intuitive workflow from overview to detailed analysis

Start with Task 2.1 (Strategy Scatter Plot) and proceed systematically. Focus on creating clear visual hierarchy and seamless navigation flow.
```

**Visualization Specifications:**
```python
# AIDEV-4D-VIZ-CLAUDE: Strategy overview scatter plot
def create_strategy_overview_scatter(tls_results_df):
    """
    X-axis: Strategy names
    Y-axis: PnL percentages
    Points: Individual combination results (small dots)
    Highlight: Top result per strategy (larger green dot)
    
    Features:
    - Clickable strategy names set filter for detailed view
    - Color intensity based on combination frequency in top 10%
    - Tooltip showing TP/SL/TLS parameters on hover
    """
    
def create_global_top_combinations_table(tls_results_df):
    """
    Columns: Rank, Strategy, TP, SL, TLS_Act, TLS_Trail, PnL, Baseline_PnL, TLS_Benefit
    Features:
    - Clickable strategy names for filtering
    - Color-coded TLS_Benefit (green positive, red negative)
    - Sortable by any column
    """
```

**Interactive Features:**
- Strategy name clicks automatically filter grid view
- Global top 10 table shows best combinations across all strategies
- TLS benefit calculation: `(tls_pnl - baseline_pnl) / baseline_pnl * 100`
- Visual density indicators showing parameter "hotspots"

### **Phase 3: 4D Grid Visualization** 🔲 *PLANNED*
**Goal:** Implement sophisticated grid-based mini-heatmaps with advanced filtering and shared scaling

**Core Components:**
- Grid layout organizing TLS combinations logically
- Shared color scale across all mini-heatmaps
- Advanced filtering with 0.25% granularity
- TLS combination performance indicators

**Grid Organization Strategy:**
```python
# AIDEV-GRID-CLAUDE: Organize TLS combinations in logical grid
def organize_tls_grid_layout(tls_activation_range, tls_trail_range):
    """
    Grid Layout Strategy:
    - Rows: TLS_activation levels (3%, 4%, 5%, 6%, 7%, 8%)
    - Columns: TLS_trail levels (1%, 2%, 3%, 4%, 5%)
    - Each cell: TP×SL heatmap for that TLS combination
    - Header coloring: Average performance indicator for that TLS combo
    """
    
def calculate_shared_color_scale(all_results):
    """
    Critical: All mini-heatmaps must use identical color scaling
    - Min value: Global minimum PnL across all combinations
    - Max value: Global maximum PnL across all combinations
    - Scale: Red (poor) → Yellow (medium) → Green (excellent)
    """
```

**Advanced Filtering:**
```python
# AIDEV-4D-VIZ-CLAUDE: Enhanced filtering capabilities
filter_options = {
    "min_performance": {"min": 0, "max": 20, "step": 0.25, "default": 0},
    "min_win_rate": {"min": 30, "max": 95, "step": 5, "default": 0},
    "strategy_filter": {"type": "dropdown", "source": "strategy_names"},
    "highlight_outliers": {"type": "checkbox", "default": False}
}
```

**Performance Optimization:**
- Client-side filtering for instant response
- Lazy loading of mini-heatmaps for large datasets
- Progressive enhancement from basic to advanced views

### **Phase 4: Grouped Ranking Table** 🔲 *PLANNED*
**Goal:** Implement sophisticated grouping and ranking system for 4D parameter combinations

**Core Components:**
- Multi-dimensional similarity grouping
- Expandable group display with sub-combinations
- TLS effectiveness metrics
- Baseline comparison integration

**Grouping Algorithm:**
```python
# AIDEV-BASELINE-CLAUDE: 4D combination grouping logic
def group_similar_4d_combinations(results_df, tolerance_config):
    """
    Grouping Logic:
    - Euclidean distance in 4D parameter space
    - Configurable tolerance per dimension (TP, SL, TLS_Act, TLS_Trail)
    - Representative = highest performing member of group
    
    Group Metrics:
    - avg_pnl: Average PnL across group members
    - tls_effectiveness: % of group where TLS > baseline
    - stability: Consistency of results within group
    """
    
def calculate_tls_effectiveness(group_results):
    """
    TLS Effectiveness Metrics:
    - improvement_rate: % of positions where TLS > baseline
    - avg_improvement: Average % improvement when TLS helps
    - risk_reduction: Average loss reduction when TLS prevents deeper losses
    """
```

**Table Features:**
- Expand/collapse groups to see all similar combinations
- Sort by any metric (PnL, TLS effectiveness, group size)
- Color-coded baseline comparison (green = TLS better, red = TLS worse)
- Confidence indicators based on group size and consistency

### **Phase 5: Integration & Reporting** 🔲 *PLANNED*
**Goal:** Integrate 4D TLS analysis into main reporting pipeline with actionable insights

**Core Components:**
- HTML report section integration
- Executive summary with key recommendations
- Strategy-specific TLS recommendations
- Performance vs complexity trade-off analysis

**Report Integration:**
```python
# AIDEV-INTEGRATE-CLAUDE: Main report integration
def generate_tls_optimization_section(html_report):
    """
    Report Sections:
    1. Executive Summary: Overall TLS effectiveness across portfolio
    2. Strategy Overview: Which strategies benefit most from TLS
    3. Interactive 4D Explorer: Full grid and table interface
    4. Recommendations: Specific parameter suggestions per strategy
    5. Complexity Analysis: TLS benefits vs added parameter complexity
    """
```

**Key Insights Generation:**
- Identify strategies where TLS provides consistent benefit
- Flag strategies where TLS adds complexity without benefit
- Recommend optimal TLS parameters per strategy with confidence levels
- Quantify overall portfolio impact of TLS adoption

## 🏗️ Current Foundation Status

**Inherited Infrastructure (Ready to Extend):**
✅ **Position Data Model:** Core position structure with TP/SL parsing
✅ **Price Cache System:** OCHLV+Volume data infrastructure
✅ **LP Position Valuator:** Mathematical framework for position simulation
✅ **Range Test Simulator:** 2D TP/SL grid testing foundation
✅ **Interactive Visualization:** HTML report integration and chart infrastructure
✅ **Strategy Instance Detection:** Grouping and identification system

**Ready for TLS Extension:**
- Simulation engine can be extended with TLS logic
- Visualization infrastructure supports additional dimensions
- Data pipeline handles complex parameter combinations
- Report generation supports new analysis sections

## ⚠️ Implementation Considerations

### **Technical Challenges**
- **4D Visualization Complexity:** Grid layout may become overwhelming with large parameter sets
- **Performance Scaling:** 4D combinations create exponential computational growth
- **Memory Management:** Large result sets may require pagination or streaming
- **Color Scale Consistency:** Shared scaling critical for meaningful comparison

### **Business Logic Risks**
- **TLS Effectiveness Validation:** Need to verify TLS logic against real trading scenarios
- **Parameter Interdependencies:** Complex relationships between TP/SL/TLS parameters
- **Overfitting Risk:** Optimization may find parameters that don't generalize
- **Complexity vs Benefit:** TLS may add operational complexity without sufficient benefit

### **User Experience Challenges**
- **Information Overload:** 4D analysis may overwhelm users with choices
- **Learning Curve:** Complex interface requires user education
- **Desktop-Only Limitation:** Mobile users excluded from analysis
- **Performance Expectations:** Users expect fast response despite computational complexity

### **Data Quality Dependencies**
- **Historical Coverage:** TLS simulation requires sufficient post-close price data
- **Volume Data Completeness:** Fee simulation accuracy depends on volume data quality
- **Position Diversity:** Results need sufficient position variety for statistical significance

## 🎯 Success Criteria & Validation

### **Phase 1 Validation**
- TLS simulation produces logically consistent results
- Parameter validation prevents all invalid combinations
- Performance meets <10-minute target for typical datasets
- Baseline comparison shows 100% accuracy

### **Phase 2 Validation**
- Strategy overview enables rapid identification of high performers
- Clickable navigation works seamlessly between overview and detail
- Top combinations table provides actionable insights
- Performance visualization shows meaningful patterns

### **Phase 3 Validation**
- Grid layout enables visual identification of parameter "islands"
- Shared color scaling allows meaningful comparison across mini-heatmaps
- Filtering provides smooth, responsive user experience
- TLS combination indicators clearly show relative performance

### **Phase 4 Validation**
- Grouping algorithm produces sensible, similar parameter clusters
- Ranking system prioritizes genuinely superior combinations
- TLS effectiveness metrics provide business-relevant insights
- Baseline comparison clearly shows when TLS adds value

### **Phase 5 Validation**
- Report integration provides clear, actionable recommendations
- Executive summary captures key insights for decision-making
- Strategy-specific guidance enables targeted parameter optimization
- Complexity analysis helps users understand cost/benefit trade-offs

## 📊 Current Implementation Status

### **Phase 1: TLS Simulation Engine** ✅ **COMPLETED** (2025-09-10)
**Achievement Summary:**
- Complete TLS simulation engine with dynamic trailing stop loss logic
- Smart parameter filtering (TP > TLS_activation, TLS_trail < TLS_activation)
- Per-strategy baseline comparison system using existing optimal TP/SL data
- Main menu integration (position 7) with reorganized menu structure
- Full data pipeline integration with comprehensive report generation
- Performance optimization with 10,000 combinations per position circuit breaker

**Technical Deliverables Completed:**
- `simulations/tls_range_simulator.py` - Core TLS simulation engine
- `reporting/lp_position_valuator.py` - Extended with TLS exit logic
- `simulations/baseline_comparator.py` - Per-strategy baseline identification
- `core/models.py` - TlsSimulationResult data model with CSV export
- `portfolio_config.yaml` - Complete TLS configuration section
- `main.py` - Menu reorganization and TLS analysis integration
- `comprehensive_report.html` - TLS section placeholder with BETA status

### **Phase 2: Strategy Overview Visualization** ✅ **COMPLETED** (2025-09-11/12)
**Achievement Summary:**
- Complete strategy visualization system with 4 interactive components
- Critical TLS logic bug fix: corrected dynamic SL calculation from peak-based to activation-based
- Parameter constraint optimization: removed restrictive limits to enable aggressive TLS testing
- Enhanced UI/UX with proper formatting and performance optimization
- Comprehensive mathematical validation across multiple market scenarios

**Technical Deliverables Completed:**
- `reporting/visualizations/interactive/tls_strategy_charts.py` - Complete strategy visualization suite
- **Strategy Performance Overview** - Scatter plot with grey bars for performance density
- **Top 10 TLS Combinations** - Global ranking table with deduplication and baseline comparison
- **Strategy Performance Summary** - Per-strategy metrics with TLS advantage calculation
- **TLS Parameter Distribution** - Analysis of parameter effectiveness across strategies
- **Critical Logic Fix** - `dynamic_sl = tls_activation - tls_trail` (fixed offset from activation)
- **Parameter Liberation** - Removed `tls_trail < tls_act` and `tls_act >= 3` constraints
- **UI Improvements** - Fixed formatting issues (+/-12.7% → -12.7%) and performance optimization

**Validation Results:**
- TLS logic verification: ✅ 10 differentiated market scenarios tested successfully
- Mathematical correctness: ✅ TLS 1/2 vs TLS 4/2 behavior properly differentiated
- Performance optimization: ✅ Grey bar visualization improves rendering while maintaining clarity
- User experience: ✅ Proper formatting and intuitive strategy comparison interface

## 📋 Phase 3: 4D Grid Visualization - Detailed Implementation Plan

### **Goal:** Implement sophisticated grid-based mini-heatmaps with global color scaling and advanced filtering

**Target Completion Time:** 2-3 sessions

### **Prerequisites & Context Analysis**
**Required Modules for Context:**
- `simulations/tls_range_simulator.py` - TLS simulation results data
- `reporting/visualizations/interactive/tls_strategy_charts.py` - Strategy overview navigation
- `reporting/visualizations/interactive/range_test_charts.py` - Existing heatmap infrastructure
- `reporting/html_report_generator.py` - Report integration pipeline
- `reporting/templates/comprehensive_report.html` - HTML template structure
- `reporting/config/portfolio_config.yaml` - TLS configuration with actual tested ranges

### **Implementation Tasks**

#### **Task 3.1: Dynamic TLS Range Detection**
**File:** `simulations/tls_range_simulator.py`
**Action:** Extract actual tested TLS ranges from simulation results

```python
def detect_tested_tls_ranges(tls_results_df):
    """
    Extract actual TLS ranges from simulation results to ensure grid matches data:
    
    Returns:
    - tls_activation_range: Sorted unique values from simulation results
    - tls_trail_range: Sorted unique values from simulation results
    
    Critical: Grid must display exactly what was tested, not config defaults
    """
    tls_activation_range = sorted(tls_results_df['tls_activation'].unique())
    tls_trail_range = sorted(tls_results_df['tls_trail'].unique())
    
    return tls_activation_range, tls_trail_range
```

#### **Task 3.2: Global Color Scale Calculator**
**File:** `reporting/visualizations/interactive/tls_4d_grid_charts.py` (NEW)
**Action:** Create shared color scaling system for all mini-heatmaps

```python
def calculate_global_color_scale(tls_results_df):
    """
    Calculate global min/max PnL values across all TLS combinations:
    
    Critical Requirements:
    - Single color scale used by ALL mini-heatmaps
    - Ensures visual comparability between different TLS combinations
    - Scale: Red (worst PnL) → Yellow (medium) → Green (best PnL)
    
    Returns:
    - global_min_pnl: Minimum PnL across all combinations
    - global_max_pnl: Maximum PnL across all combinations
    - color_scale_config: Plotly colorscale configuration
    """
    global_min_pnl = tls_results_df['simulated_pnl'].min()
    global_max_pnl = tls_results_df['simulated_pnl'].max()
    
    # Plotly colorscale with consistent red-yellow-green mapping
    color_scale = [
        [0.0, '#e74c3c'],    # Red for worst performance
        [0.5, '#f39c12'],    # Yellow for medium performance  
        [1.0, '#27ae60']     # Green for best performance
    ]
    
    return global_min_pnl, global_max_pnl, color_scale
```

#### **Task 3.3: Mini-Heatmap Generation Engine**
**File:** `reporting/visualizations/interactive/tls_4d_grid_charts.py`
**Action:** Create individual TP×SL heatmaps for each TLS combination

```python
def create_mini_heatmap(tls_activation, tls_trail, tls_results_df, global_color_scale):
    """
    Generate individual TP×SL heatmap for specific TLS combination:
    
    Layout:
    - X-axis: TP levels (from simulation data)
    - Y-axis: SL levels (from simulation data)  
    - Z-values: Average PnL for each TP×SL combination
    - Color scale: Global scale (shared across all mini-heatmaps)
    
    Header Styling:
    - Background color based on average performance of this TLS combination
    - Title format: "TLS(activation%, trail%)"
    - Performance indicator: Green (excellent), Yellow (good), Red (poor)
    
    Returns:
    - plotly_heatmap: Mini-heatmap chart object
    - avg_performance: Average PnL for header coloring
    """
    
    # Filter data for this specific TLS combination
    filtered_data = tls_results_df[
        (tls_results_df['tls_activation'] == tls_activation) & 
        (tls_results_df['tls_trail'] == tls_trail)
    ]
    
    if filtered_data.empty:
        return None, 0
    
    # Create TP×SL matrix
    tp_levels = sorted(filtered_data['tp_level'].unique())
    sl_levels = sorted(filtered_data['sl_level'].unique())
    
    # Build Z-matrix for heatmap
    z_matrix = []
    for sl in sl_levels:
        row = []
        for tp in tp_levels:
            cell_data = filtered_data[
                (filtered_data['tp_level'] == tp) & 
                (filtered_data['sl_level'] == sl)
            ]
            avg_pnl = cell_data['simulated_pnl'].mean() if not cell_data.empty else None
            row.append(avg_pnl)
        z_matrix.append(row)
    
    # Calculate average performance for header coloring
    avg_performance = filtered_data['simulated_pnl'].mean()
    
    # Create Plotly heatmap with global color scale
    heatmap = go.Heatmap(
        z=z_matrix,
        x=tp_levels,
        y=sl_levels,
        colorscale=global_color_scale['scale'],
        zmin=global_color_scale['min'],
        zmax=global_color_scale['max'],
        showscale=False,  # Only show scale once for entire grid
        hoverongaps=False,
        hovertemplate='TP: %{x}%<br>SL: %{y}%<br>PnL: %{z:.1f}%<extra></extra>'
    )
    
    return heatmap, avg_performance
```

#### **Task 3.4: Grid Layout & Organization**
**File:** `reporting/visualizations/interactive/tls_4d_grid_charts.py`
**Action:** Organize mini-heatmaps in logical grid structure

```python
def create_4d_tls_grid(tls_results_df, strategy_filter=None):
    """
    Create complete 4D grid of mini-heatmaps:
    
    Grid Organization:
    - Rows: TLS_activation levels (ascending order)
    - Columns: TLS_trail levels (ascending order)
    - Each cell: TP×SL mini-heatmap for that TLS combination
    
    Header Coloring Logic:
    - Calculate average PnL for each TLS combination
    - Apply color coding: >10% = Green, 5-10% = Yellow, <5% = Red
    - Color intensity reflects relative performance within grid
    
    Features:
    - Strategy filtering: Show only selected strategy if filter applied
    - Global color scale: All mini-heatmaps use same scale for comparability
    - Missing data handling: Empty cells for untested combinations
    """
    
    # Apply strategy filter if specified
    if strategy_filter:
        filtered_df = tls_results_df[tls_results_df['strategy_instance_id'] == strategy_filter]
    else:
        filtered_df = tls_results_df
    
    # Detect actual TLS ranges from data
    tls_activation_range, tls_trail_range = detect_tested_tls_ranges(filtered_df)
    
    # Calculate global color scale
    global_min, global_max, color_scale = calculate_global_color_scale(filtered_df)
    global_color_config = {
        'scale': color_scale,
        'min': global_min,
        'max': global_max
    }
    
    # Generate grid of mini-heatmaps
    grid_data = []
    
    for activation in tls_activation_range:
        row_data = []
        for trail in tls_trail_range:
            heatmap, avg_performance = create_mini_heatmap(
                activation, trail, filtered_df, global_color_config
            )
            
            # Determine header color based on performance
            if avg_performance > 10:
                header_class = 'performance-excellent'
            elif avg_performance > 5:
                header_class = 'performance-good'
            else:
                header_class = 'performance-average'
            
            row_data.append({
                'tls_activation': activation,
                'tls_trail': trail,
                'heatmap': heatmap,
                'avg_performance': avg_performance,
                'header_class': header_class,
                'title': f'TLS({activation}%, {trail}%)'
            })
        
        grid_data.append(row_data)
    
    return {
        'grid_data': grid_data,
        'global_color_config': global_color_config,
        'tls_activation_range': tls_activation_range,
        'tls_trail_range': tls_trail_range
    }
```

#### **Task 3.5: Advanced Filtering System**
**File:** `reporting/visualizations/interactive/tls_4d_grid_charts.py`
**Action:** Implement sophisticated filtering with 0.25% granularity

```python
def create_grid_filter_controls():
    """
    Generate filtering interface for 4D grid:
    
    Filter Controls:
    - Min Performance: Range slider (0-20%, step 0.25%)
    - Strategy Filter: Dropdown with all available strategies + "All Strategies" option
    - Min Win Rate: Range slider (30-95%, step 5%) 
    - Show Only Improvements: Checkbox (TLS better than baseline)
    
    JavaScript Integration:
    - Real-time filtering without page reload
    - Visual feedback: Filtered cells fade out, active cells remain prominent
    - Filter state preservation: Maintain filters when navigating from Phase 2
    """
    
    filter_config = {
        'min_performance': {
            'type': 'range',
            'min': 0,
            'max': 20,
            'step': 0.25,
            'default': 0,
            'label': 'Min Performance (%)'
        },
        'strategy_filter': {
            'type': 'dropdown',
            'options': ['All Strategies'] + get_available_strategies(),
            'default': 'All Strategies',
            'label': 'Strategy'
        },
        'min_win_rate': {
            'type': 'range',
            'min': 30,
            'max': 95,
            'step': 5,
            'default': 30,
            'label': 'Min Win Rate (%)'
        },
        'show_only_improvements': {
            'type': 'checkbox',
            'default': False,
            'label': 'Show Only TLS Improvements'
        }
    }
    
    return filter_config

def apply_grid_filters(grid_data, filters):
    """
    Apply active filters to grid display:
    
    Filtering Logic:
    - Performance threshold: Hide cells below minimum
    - Strategy filter: Show only selected strategy data
    - Win rate filter: Hide cells with insufficient win rate
    - Improvement filter: Show only cells where TLS > baseline
    
    Visual Effects:
    - Filtered cells: opacity 0.3, pointer-events disabled
    - Active cells: opacity 1.0, full interactivity
    - Filter indicator: Show active filter count in UI
    """
    pass  # Implementation details for filtering logic
```

#### **Task 3.6: HTML Template Integration**
**File:** `reporting/templates/comprehensive_report.html`
**Action:** Add 4D grid section with filtering controls

```html
<!-- 4D TLS Grid Section (add to TLS analysis section) -->
<div class="tls-4d-grid-section" id="tls-4d-grid-section">
    <h3>🔢 4D TLS Parameter Grid Analysis</h3>
    <div class="grid-description">
        <p>Each mini-heatmap shows TP×SL performance for a specific TLS combination. 
           All heatmaps use the same color scale for direct comparison.</p>
    </div>
    
    <!-- Grid Filter Controls -->
    <div class="grid-filter-controls">
        <div class="filter-row">
            <label>Min Performance:</label>
            <input type="range" id="grid-min-performance" min="0" max="20" step="0.25" value="0">
            <span id="grid-performance-value">0%</span>
            
            <label>Strategy:</label>
            <select id="grid-strategy-filter">
                <option value="all">All Strategies</option>
                <!-- Strategy options populated dynamically -->
            </select>
            
            <label>Min Win Rate:</label>
            <input type="range" id="grid-min-winrate" min="30" max="95" step="5" value="30">
            <span id="grid-winrate-value">30%</span>
            
            <label><input type="checkbox" id="grid-show-improvements"> Show Only TLS Improvements</label>
        </div>
    </div>
    
    <!-- TLS Grid Container -->
    <div class="tls-grid-container">
        <div class="grid-header">
            <div class="grid-corner"></div>
            <!-- TLS Trail headers -->
            <div class="trail-headers" id="trail-headers">
                <!-- Populated dynamically -->
            </div>
        </div>
        
        <div class="grid-body" id="tls-grid-body">
            <!-- TLS Activation rows with mini-heatmaps -->
            <!-- Populated dynamically -->
        </div>
    </div>
    
    <!-- Global Color Scale Legend -->
    <div class="color-scale-legend">
        <h4>Performance Scale (Global)</h4>
        <div class="legend-gradient"></div>
        <div class="legend-labels">
            <span class="legend-min">Worst</span>
            <span class="legend-mid">Average</span>
            <span class="legend-max">Best</span>
        </div>
    </div>
</div>
```

#### **Task 3.7: JavaScript Interactive Controls**
**File:** `reporting/templates/comprehensive_report.html` (JavaScript section)
**Action:** Implement real-time filtering and grid interaction

```javascript
// 4D Grid Interactive Controls
function initialize4DGrid() {
    // Grid filter event listeners
    document.getElementById('grid-min-performance').addEventListener('input', updateGridFilters);
    document.getElementById('grid-strategy-filter').addEventListener('change', updateGridFilters);
    document.getElementById('grid-min-winrate').addEventListener('input', updateGridFilters);
    document.getElementById('grid-show-improvements').addEventListener('change', updateGridFilters);
    
    // Strategy filter integration from Phase 2
    window.addEventListener('strategy-filter-changed', function(e) {
        const strategySelect = document.getElementById('grid-strategy-filter');
        strategySelect.value = e.detail.strategyId;
        updateGridFilters();
    });
}

function updateGridFilters() {
    const filters = {
        minPerformance: parseFloat(document.getElementById('grid-min-performance').value),
        strategy: document.getElementById('grid-strategy-filter').value,
        minWinRate: parseInt(document.getElementById('grid-min-winrate').value),
        showOnlyImprovements: document.getElementById('grid-show-improvements').checked
    };
    
    // Update filter value displays
    document.getElementById('grid-performance-value').textContent = filters.minPerformance + '%';
    document.getElementById('grid-winrate-value').textContent = filters.minWinRate + '%';
    
    // Apply filters to grid display
    applyFiltersToGrid(filters);
}

function applyFiltersToGrid(filters) {
    document.querySelectorAll('.mini-heatmap-cell').forEach(cell => {
        const cellData = JSON.parse(cell.getAttribute('data-cell-info'));
        
        // Check all filter conditions
        const passesFilters = (
            cellData.avgPerformance >= filters.minPerformance &&
            (filters.strategy === 'all' || cellData.strategy === filters.strategy) &&
            cellData.winRate >= filters.minWinRate &&
            (!filters.showOnlyImprovements || cellData.tlsAdvantage > 0)
        );
        
        // Apply visual filtering
        if (passesFilters) {
            cell.style.opacity = '1.0';
            cell.style.pointerEvents = 'auto';
        } else {
            cell.style.opacity = '0.3';
            cell.style.pointerEvents = 'none';
        }
    });
}
```

### **Validation & Testing Strategy**

#### **Visual Validation Tests:**
- Global color scale consistency across all mini-heatmaps
- Grid organization matches actual TLS ranges tested
- Header coloring accurately reflects average performance
- Filtering provides smooth, responsive visual feedback

#### **Data Integrity Tests:**
- TP×SL matrix accuracy within each mini-heatmap
- Color scale mapping corresponds to actual PnL values
- Strategy filtering shows correct subset without data loss
- Performance calculations match source simulation data

#### **Interactive Function Tests:**
```python
# Test scenarios:
test_global_color_scale_consistency()    # All heatmaps use same scale
test_strategy_filter_integration()       # Phase 2 → Phase 3 navigation
test_real_time_filtering_performance()   # <100ms response for filter changes
test_missing_data_handling()             # Empty cells display appropriately
test_grid_responsiveness()               # Layout adapts to different screen sizes
test_hover_tooltip_accuracy()           # Tooltips show correct TP/SL/PnL data
```

### **Success Criteria:**
- [ ] Grid layout clearly organizes TLS combinations with logical row/column structure
- [ ] Global color scale enables meaningful comparison between all mini-heatmaps
- [ ] Filtering system provides responsive, granular control (0.25% performance steps)
- [ ] Strategy filtering integration works seamlessly with Phase 2 navigation
- [ ] Visual identification of parameter "islands" possible through color patterns
- [ ] Performance remains smooth with large datasets (>1000 TLS combinations)

### **Risk Mitigation:**
- **Performance Risk:** Optimize mini-heatmap rendering for large grids (lazy loading if needed)
- **Usability Risk:** Ensure grid remains readable on 14" screens without excessive scrolling
- **Color Scale Risk:** Validate global scale provides sufficient contrast across performance ranges
- **Filter Risk:** Maintain filter state consistency during navigation between phases

### **Deliverables:**
1. Complete 4D grid visualization system with mini-heatmaps
2. Global color scaling engine ensuring visual comparability
3. Advanced filtering system with 0.25% granularity
4. HTML template integration with responsive grid layout
5. JavaScript interactive controls for real-time filtering
6. Strategy filter integration with Phase 2 navigation

---

## 🚀 Phase 3 Implementation Prompt

**Use this prompt when starting Phase 3 implementation:**

```
You are implementing Phase 3 of the 4D TP/SL/TLS Optimization Module for the SOL Decoder LP Strategy Optimization Project.

CONTEXT FROM PHASES 1 & 2 SUCCESS:
- Phase 1: Complete TLS simulation engine with verified mathematical logic
- Phase 2: Strategy overview visualization with corrected TLS logic and interactive navigation
- Available data: TLS simulation results with actual tested parameter ranges
- Integration points: Strategy filtering from Phase 2 overview to Phase 3 grid

PHASE 3 OBJECTIVE:
Create sophisticated grid-based mini-heatmaps enabling visual identification of optimal parameter "islands" across 4D TLS space.

CRITICAL REQUIREMENTS:
1. Grid organization: Rows = TLS_activation levels, Columns = TLS_trail levels (from actual data)
2. Mini-heatmaps: TP×SL performance for each TLS combination
3. Global color scale: Single scale across ALL mini-heatmaps for comparability
4. Header coloring: TLS combination performance indicator (Green/Yellow/Red)
5. Advanced filtering: Min performance (0.25% steps), strategy, win rate, improvements only
6. Phase 2 integration: Strategy clicks filter entire grid seamlessly

REQUIRED MODULES FOR CONTEXT:
- simulations/tls_range_simulator.py (TLS simulation data)
- reporting/visualizations/interactive/tls_strategy_charts.py (Phase 2 charts)
- reporting/visualizations/interactive/range_test_charts.py (existing heatmap infrastructure)
- reporting/html_report_generator.py (report integration)
- reporting/templates/comprehensive_report.html (template structure)

IMPLEMENTATION TASKS:
1. Create tls_4d_grid_charts.py with grid generation engine
2. Implement global color scale calculation across all combinations
3. Build mini-heatmap generation for each TLS combination
4. Add advanced filtering system (performance 0.25% steps, strategy, win rate)
5. Integrate with HTML template including responsive grid layout
6. Connect Phase 2 strategy navigation to grid filtering

KEY DESIGN SPECIFICATIONS:
- Grid layout: Detect actual TLS ranges from simulation data (not config defaults)
- Color scale: Red (worst) → Yellow (medium) → Green (best) applied globally
- Header colors: Based on average performance of each TLS combination
- Filtering: Real-time with visual feedback (opacity 0.3 for filtered cells)
- Integration: Strategy filter from Phase 2 sets grid strategy filter

VALIDATION TARGETS:
- Visual consistency: All mini-heatmaps comparable through shared color scale
- Performance identification: Clear visual "islands" of optimal parameters
- Interactive responsiveness: <100ms filter response time
- Data integrity: 100% accuracy between simulation data and grid display
- Navigation flow: Seamless Phase 2 → Phase 3 strategy filtering

USER REQUIREMENTS CONFIRMED:
- Grid organization: Rows = TLS_activation, Columns = TLS_trail ✅
- Color scale: Global only (no local scaling option) ✅  
- Filtering: Min performance 0.25% + strategy + win rate ✅
- Header styling: Performance-based coloring as in prototype ✅
- Layout: Desktop-first for 14" screens as in prototype ✅
- Integration: Strategy clicks filter entire grid ✅

Start with Task 3.1 (Dynamic TLS Range Detection) and proceed systematically. Focus on global color scale consistency and visual identification of parameter optimization patterns.
```

### **Phase 4: Grouped Ranking Table** 🔲 **PLANNED** 
**Target:** 4D parameter grouping with expandable interface and TLS effectiveness metrics

### **Phase 5: Integration & Reporting** 🔲 **PLANNED**
**Target:** Executive summary generation and final system integration

## 📚 Dependencies & Prerequisites

**Must Be Complete Before Starting:**
- TP/SL Range Testing Module (Phase 4A/4B) ✅ Complete
- OCHLV+Volume data infrastructure ✅ Complete
- Strategy instance detection system ✅ Complete
- HTML report generation framework ✅ Complete

**External Dependencies:**
- Plotly.js for interactive visualizations
- Pandas for data manipulation and grouping
- Existing portfolio configuration system

**Hardware Requirements:**
- Minimum 14-inch display (desktop-first approach)
- Sufficient memory for large result set manipulation
- Modern browser with JavaScript ES6+ support

---

*This specification will be updated as each phase is completed, incorporating lessons learned and refining subsequent phase requirements.*