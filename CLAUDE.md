# CLAUDE.md - SOL Decoder Strategy Analyzer

## 🌐 Language Policy
**CRITICAL RULE**: Regardless of conversation language, ALL code updates and CLAUDE.md modifications must be in English. This ensures consistency in codebase and documentation.

## 🎯 Project Objectives
### Main Goals
- [ ] **Bot Performance Analysis** - Extract position data from SOL Decoder bot logs
- [ ] **LP Strategy Optimization** - Simulate alternative Meteora DLMM strategies for found positions  
- [ ] **Strategy Ranking** - Identify best strategy combinations for different market conditions
- [ ] **Analysis Automation** - Complete pipeline from logs to comparative reports
- [ ] **TP/SL Optimization** - ML-driven optimization of take profit and stop loss levels
- [ ] **Post-Exit Analysis** - Forward-looking profitability analysis beyond historical close points

### Project Success Criteria
**MVP (current)**: Tool generates relative strategy rankings for each position with accuracy sufficient for trend and pattern identification.

**Long-term**: System provides reliable strategic recommendations with precise financial simulations and ML-optimized TP/SL levels.

## 📋 Coding Conventions

### Structure and Organization
- **Maximum file length:** 600 lines of code
- **When file exceeds 600 lines:** time for refactoring (split into modules)
- **Naming:** snake_case for functions/variables, PascalCase for classes

### Documentation
- **Docstrings:** Mandatory for all functions and classes
- **Docstring format:** Google style with complete parameter and return value descriptions
- **Example:**
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

### Anchor Comments (AI Navigation Comments)
**Format:** `# [TAG]-[AI_ID]: [comment content] (max 120 characters)`

**Available tags:**
- `# AIDEV-NOTE-CLAUDE:` - important performance/business logic information
- `# AIDEV-TODO-CLAUDE:` - planned improvements/tasks  
- `# AIDEV-QUESTION-CLAUDE:` - doubts to discuss with human
- `# AIDEV-NOTE-GEMINI:` - information added by Gemini
- `# AIDEV-TODO-GEMINI:` - tasks planned by Gemini

**Anchor comment usage rules:**
- **Before scanning files:** always locate existing `AIDEV-*` anchors first
- **When modifying code:** update related anchors
- **DO NOT remove `AIDEV-NOTE`** without explicit human instruction
- **Add anchors when code is:**
  - too long or complex
  - very important
  - confusing or potentially buggy
  - performance-critical

**Usage examples:**
```python
# AIDEV-NOTE-CLAUDE: perf-critical; Moralis API cache mechanism - avoid duplicate requests
def fetch_price_history(pool_address: str, start_dt: datetime, end_dt: datetime) -> List[Dict]:
    # Implementation...

# AIDEV-TODO-CLAUDE: add pool_address format validation (ticket: SOL-123)  
def validate_meteora_pool_address(address: str) -> bool:
    # Current implementation...

# AIDEV-QUESTION-CLAUDE: should timeframe selection be adaptive or fixed? 
# Context: current 10min/30min/1h/4h may not cover all use cases
def calculate_optimal_timeframe(duration_hours: float) -> str:
    # Timeframe selection logic...
```

### Refactoring Rules at 600+ Lines
- **Extract business logic** to separate modules (parsers/, analyzers/, utils/)
- **Create utils.py** for helper functions (timestamp parsing, validation)
- **Separate layers** (data extraction, price fetching, strategy simulation, reporting)
- **Add AIDEV-NOTE** about refactoring reason

## 🚦 Rules for Claude

### 🎯 You can do without asking
- **Add anchor comments** with CLAUDE tag
- **Discuss LP strategy business logic** (but don't implement without specification)
- **Implement according to specification** when simulation parameters are clearly defined

### ⚠️ You can propose (but not implement)
- **Code refactoring** - propose plan, wait for approval
- **API call optimizations** - describe benefits, don't introduce automatically
- **Simulation algorithm improvements** - discuss mathematics, don't change without permission
- **File structure changes** - only with explicit permission

### 🚫 Absolute prohibitions
- **Don't assume LP strategy logic** - Meteora DLMM parameters are specific, always ask
- **Don't implement Moralis API optimizations** without consent (only propose)
- **Don't remove anchor comments** without instructions
- **Don't change fee calculation logic** - this is core business logic

### 📋 Change Implementation Process
1. **First skeleton/plan** of changes for discussion
2. **After approval** - complete code with precise "find and replace" instructions
3. **Code changes:** using "find and replace" method with exact location
4. **New code:** indicate exactly where to paste

### 🔄 Refactoring (soft-stop at 600+ lines)
- **Suggest refactoring** but allow continuation without it
- **When refactoring:** check function by function that all functionalities are preserved
- **Format:** "I suggest refactoring, but can continue without it if you prefer"

### 📏 File Length Monitoring
- **At 600+ lines:** gently suggest refactoring with each modification
- **Don't block work** if you decide to continue

## 📚 Domain Dictionary

### Data Sources & APIs
- **Primary Price API** - Moralis API (Solana gateway)
- **Rate Limiting** - 0.6s between requests, automatic caching
- **Supported Timeframes** - 10min, 30min, 1h, 4h (adaptive selection)
- **Cache Strategy** - JSON files per pool/timerange in price_cache/

### Meteora DLMM Terminology
- **DLMM** - Decentralized Liquidity Market Maker (Meteora protocol)
- **Bin** - discrete price range in liquidity pool
- **Bin Step** - price spacing between bins (in basis points)
- **Active Bin** - bin containing current market price
- **Price Factor** - price multiplier between bins (1 + bin_step/10000)

### SOL Decoder Bot Terminology  
- **LP Strategy** - liquidity provision strategy (Spot/Bid-Ask × 1-Sided/Wide)
- **Bid-Ask Distribution** - progressive liquidity distribution (more at edges)
- **Spot Distribution** - uniform liquidity distribution
- **1-Sided Entry** - entry with SOL only
- **Wide Entry** - entry with 50/50 SOL/Token split

### Financial Metrics
- **IL (Impermanent Loss)** - loss due to relative price changes of assets
- **PnL from Fees** - profit from trading fees
- **Take Profit (TP)** - automatic close when profit target reached
- **Stop Loss (SL)** - automatic close when loss threshold exceeded
- **Post-Exit Analysis** - forward-looking profitability analysis beyond historical close
- **ML-Optimized Levels** - TP/SL levels determined by machine learning algorithms

## 🗂️ Project Structure
- **main_analyzer.py** - main orchestrator (extraction → analysis → reporting)
- **log_extractor.py** - SOL Decoder bot log parser, extracts position data
- **strategy_analyzer.py** - LP strategy simulation engine for Meteora DLMM
- **input/** - SOL Decoder bot log files (automatically processes newest)
  - **archive/** - processed logs (automatic archiving) [TODO]
- **output/** - analysis results
  - **detailed_reports/** - detailed per-position reports  
  - **final_analysis_report.csv** - summary with strategy rankings
- **price_cache/** - cached price data from Moralis API
- **.env** - API configuration (MORALIS_API_KEY)

### File Handling Rules
- **Input:** all *.log files starting with "app" in input/ directory
- **Cache:** automatic Moralis API response caching (JSON files)
- **Reports:** individual text reports + collective CSV

## 🏃‍♂️ Project Status
**Last Update:** [PLACEHOLDER - will be updated regularly]
**Current Version:** MVP v1.0
**Working Features:** 
- Position extraction from SOL Decoder logs ✅
- Historical price data fetching from Moralis API ✅
- 4 LP strategy simulation (Spot/Bid-Ask × 1-Sided/Wide) ✅
- Comparative report generation ✅

**In Progress:**
- Fee calculation accuracy improvements 🔄
- TP/SL optimization research 🔄

**Next:**
- Financial simulation accuracy improvements 📋
- ML-driven TP/SL level optimization 📋
- Post-exit analysis (forward-looking candle testing) 📋
- Precise fee calculations per-candle 📋

## 📝 Session History
### 2025-06-13: Position Exit Date Accuracy
- **Goal:** Fixes in position exit date determination  
- **Achieved:** 100% completed - parser correctly identifies close events
- **Issues:** - 
- **Next Steps:** Create filter to skip positions without significant PnL

### 2025-06-17: CLAUDE.md Setup & Roadmap
- **Goal:** Create project bible and define development priorities
- **Achieved:** CLAUDE.md template customization, roadmap clarification
- **Issues:** -
- **Next Steps:** Begin accuracy improvements and TP/SL optimization research