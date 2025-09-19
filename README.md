# SOL Decoder Strategy Analyzer v6.0

A comprehensive Python tool for analyzing SOL Decoder bot performance with **complete TP/SL and TSL optimization capabilities**, advanced portfolio analytics, and ML-ready strategy optimization.

## Overview

This tool has evolved into a **complete portfolio analytics and optimization platform** that helps SOL Decoder bot users maximize their LP strategy performance through:

1. **Automated Log Processing** - Extract position data from bot logs with >99.5% accuracy
2. **Advanced Market Analysis** - Market correlation, EMA trend detection, weekend parameter optimization
3. **Professional Portfolio Analytics** - Dual currency analysis (SOL/USDC) with infrastructure cost impact
4. **Interactive Reporting** - Plotly-based comprehensive reports with executive summaries
5. **Strategy Optimization** - Compare Spot vs Bid-Ask distributions with research-verified mathematical formulas
6. **🆕 Complete TP/SL Optimization** - Historical simulation, range testing, and interactive "what-if" analysis
7. **🆕 Post-Exit Analysis** - Forward-looking profitability analysis with missed opportunity quantification
8. **Smart Data Management** - Offline-first analysis, intelligent caching, graceful error handling

The tool analyzes **1-sided LP strategies** with different distribution patterns using official Meteora DLMM mathematical formulas with automatic step size detection.

## 🆕 Version 6.0 Major Updates

**Advanced 4D TLS (Trailing Stop Loss) Optimization:**
- ✅ **4D Grid Visualization**: Sophisticated mini-heatmaps with global color scaling and interactive filters to explore TP/SL/TLS Activation/TLS Trail parameters.
- ✅ **Parameter Grouping & Ranking**: A smart clustering algorithm that identifies robust, high-performing parameter "islands" and presents them in an intuitive, expandable table.
- ✅ **Baseline Comparison**: Clear, quantitative comparison of TLS-enabled strategies against the best non-TLS performance.

## Features

### Core Analytics
- 📊 **Advanced Log Parsing**: >99.5% accuracy with TP/SL extraction and peak PnL analysis
- 📈 **Meteora DLMM Integration**: Research-verified mathematical simulations for strategy comparison
- 🎯 **Strategy Optimization**: Spot vs Bid-Ask distributions with step size analysis and performance ranking
- 💰 **Infrastructure Cost Analysis**: Daily cost allocation with break-even analysis and dual currency impact
- 📊 **Market Correlation Analysis**: Portfolio vs SOL performance with EMA trend detection

### TP/SL Optimization Engine
- 🔬 **Historical Simulation**: Test thousands of TP/SL combinations against actual position data
- 🎯 **Interactive What-If Tool**: Dynamic browser-based exploration with real-time results
- 📊 **Visual Heatmaps**: Per-strategy optimization matrices showing profit potential
- 🧮 **Mathematical Precision**: LP position valuation with impermanent loss calculations
- 💡 **Actionable Insights**: Direct recommendations for optimal parameters per strategy
- 🤖 **ML-Ready Export**: Structured datasets for machine learning model development

### Reporting & Visualization  
- 📋 **Interactive HTML Reports**: Professional Plotly-based reports with embedded optimization tools
- 📊 **Professional Charts**: Equity curves, drawdown analysis, strategy heatmaps, cost impact charts
- 🔍 **Weekend Parameter Analysis**: weekendSizePercentage optimization with statistical significance testing
- 💾 **Smart Caching**: Offline-first analysis with intelligent gap detection and API failure handling

### Architecture & Reliability
- 🗃️ **Centralized Entry Point**: Single main.py with interactive menu for all operations
- 💾 **True Offline Analysis**: Complete analysis capability using cached data without API calls
- 🔧 **Graceful Error Handling**: Reports handle missing data and API failures without crashes
- 🛠️ **Manual Data Correction**: positions_to_skip.csv for excluding problematic positions
- 📄 **Cross-File Position Tracking**: Handles positions that span multiple log files

## Requirements

- Python 3.11+ (recommended for maximum compatibility)
- Moralis API key (free tier available - used only for initial data fetching)
- SOL Decoder bot log files

## Installation

1. Clone this repository:
```bash
git clone https://github.com/yourusername/solana-lp-strategy-analyzer.git
cd solana-lp-strategy-analyzer
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the project root:
```env
MORALIS_API_KEY=your_moralis_api_key_here
```

## Usage

### Interactive Menu System

Run the main application:
```bash
python main.py
```

The interactive menu provides access to all functionality:

```
=== SOL Decoder Strategy Analyzer v5.0 ===
[1] Extract positions from logs
[2] Run Spot vs Bid-Ask analysis  
[3] Fetch/Update market data
[4] Generate portfolio analytics report
[5] Run comprehensive analysis (steps 1-4)
[6] Cache-only analysis (offline mode)
[7] 🆕 TP/SL Post-Close Analysis
[8] 🆕 TP/SL Range Testing & Optimization
```

### Typical Workflow

1. **Place log files** in `input/` directory (supports multi-wallet via subfolders)
2. **Run comprehensive analysis** (Option 5) for first-time setup
3. **Run TP/SL optimization** (Option 8) for parameter recommendations
4. **Use cache-only mode** (Option 6) for subsequent analysis to save API credits
5. **Review reports** in `detailed_reports/` and open the HTML report for interactive analysis

### Advanced TP/SL Optimization

- **Configure ranges** in `reporting/config/portfolio_config.yaml`:
```yaml
range_testing:
  tp_levels: [2, 4, 6, 8, 10, 15]
  sl_levels: [2, 3, 4, 5, 7, 10]
```
- **Interactive exploration** via the "What-If" tool in HTML reports
- **ML dataset export** for advanced optimization model development

## Sample Results & Key Insights

**TP/SL Optimization Example:**
- **Range Testing**: Analyzed 1000+ historical positions across 36 TP/SL combinations
- **Optimal Parameters**: Identified 6% TP / 10% SL as optimal for Bid-Ask Medium strategies
- **Missed Opportunities**: Quantified average 14.8% additional profit potential with optimized timing
- **Interactive Analysis**: Real-time filtering by date range and strategy performance

**Portfolio Performance Example:**
- **Total Positions Analyzed**: 450+ positions across multiple strategies
- **Strategy Comparison**: Bid-Ask vs Spot distribution performance rankings
- **Market Correlation**: Portfolio correlation with SOL price movements and trend analysis
- **Infrastructure Impact**: Cost allocation analysis showing break-even points and net profitability

**Actionable Insights:**
- Strategy performance varies significantly by market conditions (uptrend vs downtrend)
- Weekend parameter optimization can impact total returns by 15-30%
- Infrastructure costs typically represent 2-8% of gross PnL depending on position size and duration
- TP/SL optimization can improve portfolio performance by 20-40% through better exit timing

## Output Files & Reports

| File/Report | Description |
|-------------|-------------|
| `positions_to_analyze.csv` | Complete extracted position data with TP/SL and peak PnL |
| `final_analysis_report.csv` | Strategy comparison with optimization recommendations |
| `comprehensive_report.html` | **Interactive HTML report with TP/SL optimization tools** |
| `range_test_detailed_results.csv` | 🆕 Complete TP/SL simulation results |
| `ml_dataset_tp_sl.csv` | 🆕 ML-ready dataset with post-close features |
| `detailed_reports/*.txt` | Individual position analysis files |
| `strategy_instances.csv` | Strategy performance groupings and rankings |
| `price_cache/` | Smart cached market data (auto-managed) |

## Enhanced Project Structure

```
├── main.py                          # Centralized entry point with interactive menu
├── core/
│   └── models.py                    # Enhanced Position model with TP/SL and peak PnL fields
├── extraction/                      # Data extraction from logs
│   ├── log_extractor.py            # >99.5% accuracy parser with peak PnL extraction  
│   └── parsing_utils.py            # Enhanced TP/SL and peak PnL extraction utilities
├── reporting/                       # Complete portfolio analytics module
│   ├── config/
│   │   └── portfolio_config.yaml   # Infrastructure costs, TP/SL ranges, analysis parameters
│   ├── templates/
│   │   └── comprehensive_report.html # Interactive HTML report with TP/SL tools
│   ├── post_close_analyzer.py      # 🆕 "What-if" TP/SL analysis engine
│   ├── fee_simulator.py            # 🆕 Volume-proportional fee allocation
│   ├── lp_position_valuator.py     # 🆕 LP position value with IL formulas
│   ├── enhanced_price_cache_manager.py # 🆕 OCHLV+Volume cache with offline-first
│   └── visualizations/
│       └── interactive/             # Modular chart generation system
├── simulations/                     # Strategy simulation engines
│   ├── spot_vs_bidask_simulator.py # Research-based DLMM simulations
│   ├── weekend_simulator.py        # Weekend parameter optimization
│   └── range_test_simulator.py     # 🆕 TP/SL range testing simulation engine
├── data_fetching/                   # 🆕 All data fetching and orchestration logic
│   ├── cache_orchestrator.py       # 🆕 Manages OCHLV cache (menus, validation)
│   └── enhanced_price_cache_manager.py # 🆕 Core OCHLV+Volume cache logic
└── tools/                           # Utility and debugging tools
    ├── api_checker.py              # API connectivity verification
    └── cache_debugger.py           # 🆕 OCHLV cache debugging and validation
```

## Configuration

### TP/SL Optimization (`reporting/config/portfolio_config.yaml`)
```yaml
# TP/SL Range Testing Configuration
range_testing:
  enable: true
  tp_levels: [2, 4, 6, 8, 10, 15] 
  sl_levels: [2, 3, 4, 5, 7, 10]
  primary_ranking_metric: "total_pnl"

# Post-Close Analysis Settings
tp_sl_analysis:
  enable_custom_params: false
  post_close_multiplier: 1.0           # 1x = position duration length
  min_post_close_hours: 2              # Minimum post-close analysis period
  max_post_close_hours: 48             # Maximum 2 days
  significance_threshold: 0.5          # Minimum % for peak PnL detection

# Data Source Preferences (Offline-First)
data_source:
  prefer_offline_cache: true
  interactive_gap_handling: true
  auto_generate_offline: true
```

## Troubleshooting

### Common Issues & Solutions

**TP/SL optimization shows no results:**
- Verify positions have sufficient post-close price data
- Check TP/SL ranges in configuration match realistic values
- Ensure OCHLV cache is populated via Step 3 menu options

**Interactive "What-If" tool not working:**
- Re-run Step 8 to regenerate simulation results
- Check browser console for JavaScript errors
- Verify `range_test_detailed_results.csv` exists and contains data

**Missing market data:**
- Use "Force Data Refresh" option in Step 3 submenu
- Verify Moralis API key is correct and has available credits
- Try offline-first mode if API issues persist

## Roadmap & Future Development

### Immediate Priorities (Next Release)
- **🆕 Phase 5: ML-Driven Optimization**: Machine learning models for optimal TP/SL prediction
- **Enhanced Strategy Analytics**: Cross-strategy performance matrices with time-weighted analysis
- **Real-Time Recommendations**: Dynamic TP/SL suggestions based on current market conditions

### Advanced Analytics
- **Risk Management Automation**: Automated position sizing and risk assessment
- **Market Regime Detection**: Bull/bear/crab market identification for parameter adaptation
- **Delta-Neutral LP Management**: Funding rate analysis and hedge position optimization

### Integration & Automation
- **Telegram Integration**: Position notifications and TP/SL override commands
- **API Integration**: Direct bot parameter updates based on optimization results
- **Real-Time Monitoring**: Live position tracking with optimization alerts

## Contributing

We welcome contributions! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Follow the coding conventions in `CLAUDE.md`
4. Add comprehensive tests for new functionality
5. Commit changes (`git commit -m 'Add amazing feature'`)
6. Push to branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## License

This project is licensed under the MIT License. See `LICENSE` file for details.

## Disclaimer

**This tool provides advanced portfolio analytics and optimization recommendations.**

- TP/SL optimization is based on historical simulation and mathematical modeling for trend identification
- Strategy simulations provide **relative performance comparisons** and **optimization guidance**  
- Results are intended for **strategic decision-making** and **parameter optimization**, not precise financial predictions
- Always conduct additional research and consider current market conditions, risk tolerance, and position sizing
- Past performance optimization does not guarantee future results

**Use responsibly**: This tool helps optimize strategies and identify optimal parameters through rigorous historical analysis.

## Support & Community

- **Issues**: Report bugs and feature requests via [GitHub Issues](https://github.com/yourusername/solana-lp-strategy-analyzer/issues)
- **Documentation**: Complete technical documentation available in `CLAUDE.md`
- **Discord**: Join our community for discussions and support

---

**Happy optimizing! 📊🚀**

*Advanced TP/SL optimization for maximum LP strategy performance.*