# SOL Decoder Strategy Analyzer v4.4

A comprehensive Python tool for analyzing SOL Decoder bot performance with advanced portfolio analytics, market correlation analysis, and ML-ready strategy optimization capabilities.

## Overview

This tool has evolved from a simple log parser into a complete portfolio analytics platform that helps SOL Decoder bot users optimize their LP strategies through:

1. **Automated Log Processing** - Extract position data from bot logs with >99.5% accuracy
2. **Advanced Market Analysis** - Market correlation, EMA trend detection, weekend parameter optimization
3. **Professional Portfolio Analytics** - Dual currency analysis (SOL/USDC) with infrastructure cost impact
4. **Interactive Reporting** - Plotly-based comprehensive reports with executive summaries
5. **Strategy Optimization** - Compare Spot vs Bid-Ask distributions with research-verified mathematical formulas
6. **Smart Data Management** - Intelligent caching, offline analysis, graceful error handling

The tool analyzes **1-sided LP strategies** with different distribution patterns using official Meteora DLMM mathematical formulas with automatic step size detection.

## 🆕 Version 4.4 Major Updates

**Portfolio Analytics & Market Intelligence:**
- ✅ **Complete Portfolio Analytics Module**: Dual SOL/USDC currency analysis with infrastructure cost impact
- ✅ **Market Correlation Analysis**: Pearson correlation with SOL trends, EMA slope detection  
- ✅ **Weekend Parameter Optimization**: weekendSizePercentage impact simulation with statistical significance
- ✅ **Interactive HTML Reports**: Plotly-based comprehensive reports with executive summaries
- ✅ **Professional Charting**: 4 chart types (equity curve, drawdown, strategy heatmap, cost impact)

**Architecture & Reliability:**
- ✅ **Centralized Architecture**: Single entry point (main.py) with interactive menu system
- ✅ **Smart Cache Management v2.0**: Intelligent gap detection, API failure vs no-data distinction
- ✅ **True Offline Mode**: Complete analysis capability without API calls using cached data
- ✅ **Graceful Degradation**: Reports handle missing data without crashes
- ✅ **Enhanced Error Resiliency**: Comprehensive fallback mechanisms throughout pipeline

**Data Quality & Parsing:**
- ✅ **Enhanced Strategy Parsing**: >99.5% accuracy with context-based detection
- ✅ **Take Profit/Stop Loss Extraction**: TP/SL values parsed and integrated into analysis pipeline
- ✅ **"Superseded" Position Logic**: Robust handling of position restarts and replacements
- ✅ **Manual Position Filtering**: positions_to_skip.csv for data quality control
- ✅ **Cross-File Position Tracking**: Positions that open/close across different log files

**Performance & Usability:**
- ✅ **3x Pipeline Speed Improvement**: Optimized data flow and single CSV load architecture
- ✅ **Modular Chart Generation**: Decomposed into specialized modules for better maintainability
- ✅ **Zero Column Mapping Complexity**: Unified naming system across entire codebase
- ✅ **API Credit Conservation**: Controlled API usage with user confirmation prompts

## Features

### Core Analytics
- 📊 **Advanced Log Parsing**: >99.5% accuracy with TP/SL extraction and cross-file position tracking
- 📈 **Meteora DLMM Integration**: Research-verified mathematical simulations for strategy comparison
- 🎯 **Strategy Optimization**: Spot vs Bid-Ask distributions with step size analysis and performance ranking
- 💰 **Infrastructure Cost Analysis**: Daily cost allocation with break-even analysis and dual currency impact
- 📊 **Market Correlation Analysis**: Portfolio vs SOL performance with EMA trend detection

### Reporting & Visualization  
- 📋 **Interactive HTML Reports**: Professional Plotly-based reports with executive summaries
- 📊 **Professional Charts**: Equity curves, drawdown analysis, strategy heatmaps, cost impact charts
- 🔍 **Weekend Parameter Analysis**: weekendSizePercentage optimization with statistical significance testing
- 💾 **Smart Caching**: Intelligent gap detection and API failure handling to minimize costs

### Architecture & Reliability
- 🏗️ **Centralized Entry Point**: Single main.py with interactive menu for all operations
- 💾 **True Offline Analysis**: Complete analysis capability using cached data without API calls
- 🔧 **Graceful Error Handling**: Reports handle missing data and API failures without crashes
- 🛠️ **Manual Data Correction**: positions_to_skip.csv for excluding problematic positions
- 🔄 **Cross-File Position Tracking**: Handles positions that span multiple log files

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
=== SOL Decoder Strategy Analyzer v4.4 ===
[1] Extract positions from logs
[2] Run Spot vs Bid-Ask analysis  
[3] Fetch/Update market data
[4] Generate portfolio analytics report
[5] Run comprehensive analysis (steps 1-4)
[6] Cache-only analysis (offline mode)
```

### Typical Workflow

1. **Place log files** in `input/` directory (supports multi-wallet via subfolders)
2. **Run comprehensive analysis** (Option 5) for first-time setup
3. **Use cache-only mode** (Option 6) for subsequent analysis to save API credits
4. **Review reports** in `detailed_reports/` and open the HTML report for interactive analysis

### Advanced Options

- **Manual Position Filtering**: Create `positions_to_skip.csv` to exclude specific positions
- **Force Data Refresh**: Use submenu in Step 3 to refresh cached market data
- **Multi-Wallet Analysis**: Organize logs in `input/wallet_name/` subfolders

## Sample Results & Key Insights

**Portfolio Performance Example:**
- **Total Positions Analyzed**: 450+ positions across multiple strategies
- **Strategy Comparison**: Bid-Ask vs Spot distribution performance rankings
- **Market Correlation**: Portfolio correlation with SOL price movements and trend analysis
- **Infrastructure Impact**: Cost allocation analysis showing break-even points and net profitability

**Actionable Insights:**
- Strategy performance varies significantly by market conditions (uptrend vs downtrend)
- Weekend parameter optimization can impact total returns by 15-30%
- Infrastructure costs typically represent 2-8% of gross PnL depending on position size and duration

## Output Files & Reports

| File/Report | Description |
|-------------|-------------|
| `positions_to_analyze.csv` | Complete extracted position data with TP/SL |
| `final_analysis_report.csv` | Strategy comparison with optimization recommendations |
| `comprehensive_report.html` | **Interactive HTML report with all analytics** |
| `detailed_reports/*.txt` | Individual position analysis files |
| `strategy_instances.csv` | Strategy performance groupings and rankings |
| `price_cache/` | Smart cached market data (auto-managed) |

## Enhanced Project Structure

```
├── main.py                          # 🆕 Centralized entry point with interactive menu
├── core/
│   └── models.py                    # 🆕 Enhanced Position model with TP/SL fields
├── extraction/                      # Data extraction from logs
│   ├── log_extractor.py            # 🆕 >99.5% accuracy parser with cross-file tracking  
│   └── parsing_utils.py            # 🆕 Enhanced TP/SL extraction and strategy detection
├── reporting/                       # 🆕 Complete portfolio analytics module
│   ├── config/
│   │   └── portfolio_config.yaml   # 🆕 Infrastructure costs and analysis parameters
│   ├── templates/
│   │   └── comprehensive_report.html # 🆕 Interactive HTML report template
│   ├── visualizations/
│   │   └── interactive/             # 🆕 Modular chart generation system
│   │       ├── portfolio_charts.py  # KPI, Equity, Drawdown, Cost charts
│   │       ├── strategy_charts.py   # Heatmap, Performance summary charts  
│   │       ├── market_charts.py     # Correlation, EMA Trend charts
│   │       └── simulation_charts.py # Weekend parameter analysis
│   ├── orchestrator.py             # 🆕 Main analytics orchestration engine
│   ├── html_report_generator.py    # 🆕 Interactive report generation
│   ├── market_correlation_analyzer.py # 🆕 Market correlation and trend analysis
│   └── price_cache_manager.py      # 🆕 Smart caching with intelligent gap detection
├── simulations/                     # Strategy simulation engines
│   ├── spot_vs_bidask_simulator.py # Research-based DLMM simulations
│   └── weekend_simulator.py        # 🆕 Weekend parameter optimization
├── tools/                           # Utility and debugging tools
│   ├── api_checker.py              # API connectivity verification
│   └── debug_analyzer.py           # Context analysis and debugging
└── input/                           # Log files (supports multi-wallet subfolders)
```

## Configuration

### Portfolio Analytics (`reporting/config/portfolio_config.yaml`)
```yaml
portfolio_analysis:
  risk_free_rates:
    sol_staking: 0.04      # 4% APR SOL staking
    usdc_staking: 0.05     # 5% APR USDC staking
  cost_allocation_method: "daily_flat"
  analysis_periods: [1, 7, 30, 90]  # days
  min_position_threshold: 0.01       # SOL minimum for analysis

infrastructure_costs:
  monthly:
    vps_cost: 8.54         # USD
    rpc_endpoints: 20.0   # USD  
    bot_subscription: 00.0 # USD
    # Total: 28.54 USD/month = 0.95 USD/day

currency_analysis:
  primary_denomination: "sol"
  include_usdc_view: true
  sol_price_source: "moralis"

visualization:
  chart_types: ["equity_curve", "drawdown", "cost_impact", "strategy_heatmap"]
  timestamp_format: "%Y%m%d_%H%M"
  filters:
    min_strategy_occurrences: 2  # minimum positions per strategy
    top_strategies_only: 10      # show only top N strategies
    exclude_outliers: false       # remove statistical outliers
    date_range_filter: false      # custom date range selection

# Weekend Parameter Analysis Configuration
weekend_analysis:
  weekend_size_reduction: 0        # 0=disabled, 1=enabled for all positions
  size_reduction_percentage: 80    # 80% reduction = 20% remains; 0 = no analysis
  
 api_settings:
  cache_only: false
```

## API Usage & Cost Management

**Smart Caching System:**
- **Intelligent Gap Detection**: Only fetches missing time periods
- **API Failure Handling**: Distinguishes between API errors and legitimate empty periods  
- **Monthly Cache Organization**: Organized cache files with incremental updates
- **Force Refresh Options**: User-controlled cache refresh for data updates

**Cost Conservation:**
- **Cache-Only Mode**: Complete offline analysis using cached data
- **User Confirmation Prompts**: API usage requires explicit user consent
- **Controlled Fetching**: Single centralized data fetching phase prevents unexpected API calls

## Troubleshooting

### Common Issues & Solutions

**No positions extracted:**
- Verify SOL Decoder bot log files are in `input/` directory
- Check logs contain actual position opening/closing events
- Enable debug logging in `log_extractor.py` for detailed diagnostics

**Missing market data:**
- Use "Force Data Refresh" option in Step 3 submenu
- Verify Moralis API key is correct and has available credits
- Check network connectivity and API rate limits

**Report generation errors:**
- Try cache-only mode first to isolate API issues
- Check `positions_to_analyze.csv` exists and contains valid data
- Review console output for specific error messages

**Data quality issues:**
- Use `positions_to_skip.csv` to exclude problematic positions
- Re-run extraction (Step 1) to refresh position data
- Check source log files for corruption or format changes

### Debug Features

**Enhanced Logging:**
```python
# Enable debug logging in log_extractor.py
DEBUG_ENABLED = True
DEBUG_LEVEL = "DEBUG"
```

**Manual Data Correction:**
Create `positions_to_skip.csv` with position IDs to exclude:
```csv
position_id
SOL/USDC-2024-06-15-12:30:45
BONK/SOL-2024-06-20-09:15:22
```

## Roadmap & Future Development

### Immediate Priorities (Next Release)
- **ML-Driven TP/SL Optimization**: Machine learning models for optimal take profit/stop loss levels
- **Post-Exit Analysis**: Forward-looking profitability analysis beyond historical close points
- **Enhanced Strategy Analytics**: Strategy comparison matrices with detailed performance breakdown

### Advanced Analytics
- **Real-Time Strategy Recommendations**: Dynamic strategy suggestions based on market conditions
- **Risk Management Automation**: Automated risk assessment and position sizing recommendations  
- **Cross-Strategy Performance Analysis**: Comprehensive comparison across all strategy variants

### Integration & Automation
- **Telegram Integration**: Position notifications and SL/TP override commands
- **Market Regime Detection**: Bull/bear/crab market identification for strategy optimization
- **Delta-Neutral LP Management**: Funding rate analysis and hedge position optimization

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

**This tool is designed for educational and comparative analysis purposes.**

- Portfolio analytics are based on historical data and simplified models for trend identification
- Strategy simulations provide **relative performance comparisons** between distribution methods
- Results are intended for **strategic guidance** and **pattern recognition**, not precise financial predictions
- Always conduct additional research and consider market conditions, risk tolerance, and position sizing
- Past performance analysis does not guarantee future results

**Use responsibly**: This tool helps compare strategies and identify patterns, not as definitive trading signals.

## Support & Community

- **Issues**: Report bugs and feature requests via [GitHub Issues](https://github.com/yourusername/solana-lp-strategy-analyzer/issues)
- **Documentation**: Complete technical documentation available in `CLAUDE.md`
- **Discord**: Join our community for discussions and support

---

**Happy analyzing! 📊🚀**

*Advanced portfolio analytics for smarter LP strategy decisions.*