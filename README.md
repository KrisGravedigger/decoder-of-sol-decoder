# SOL Decoder Strategy Analyzer

A Python tool for analyzing SOL Decoder bot performance by extracting position data from bot logs and simulating alternative LP strategies on Meteora DEX using historical price data.

## Overview

This tool helps SOL Decoder bot users find optimal strategy combinations by:

1. **Extracting position data** from bot logs automatically
2. **Fetching historical price data** via Moralis API for each position
3. **Simulating alternative strategies** to find the best approach for each entry
4. **Generating comprehensive reports** comparing all strategy combinations

The tool analyzes different combinations of:
- **Distribution modes**: Spot vs Bid-Ask 
- **Entry types**: 1-Sided vs Wide

## ⚠️ Important: MVP Limitations & Proper Usage

**This is an MVP (Minimum Viable Product)** designed for relative comparison of strategies, not precise financial predictions.

### ✅ **What this tool IS good for:**
- **Ranking strategies** for each position (which performed best)
- **Identifying trends** across different market conditions
- **Comparing within pairs**: Spot vs Bid-Ask for same entry type
- **Data exploration** to guide further analysis
- **Relative performance** assessment between similar strategies

### ❌ **What this tool is NOT:**
- A precise financial forecasting tool
- Accurate for absolute PnL predictions  
- Reliable for cross-category comparisons (Wide vs 1-Sided)
- Suitable for high-stakes investment decisions

### 🔬 **Known Technical Limitations:**
- **Simplified IL calculations** for Wide strategies
- **Basic fee distribution model** (actual fees depend on volume, not just liquidity)
- **Static bin analysis** (doesn't account for price transitions over time)
- **Estimated fee budgets** based on actual bot PnL assumptions

### 📊 **Recommended Usage:**
1. Use for **strategy ranking** within each position
2. Look for **patterns** across multiple positions  
3. Focus on **relative differences** between strategies
4. Use results to **guide further research**, not as final decisions
5. Combine with other analysis methods for investment decisions

## Features

- 📊 **Automated Log Parsing**: Extracts position data from SOL Decoder bot logs
- 📈 **Meteora Integration**: Fetches historical price data for Meteora DLMM pools
- 🎯 **Strategy Optimization**: Compares all strategy combinations to find optimal settings
- 📋 **Comprehensive Reports**: Detailed analysis reports for each position and strategy
- 💾 **Smart Caching**: Caches price data to minimize API calls and speed up analysis
- 🔍 **Robust Validation**: Data validation and error handling for reliable results

## Requirements

- Python 3.11+ (recommended for maximum compatibility)
- Moralis API key (free tier available)
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

### 1. Prepare Your Data

Place your SOL Decoder bot log files in the `input/` directory. The tool automatically processes:
- Log files starting with "app" and containing ".log" in filename
- Standard SOL Decoder log format with timestamps and position events
- Position opening/closing events, PnL data, and strategy information

**Note**: The log structure is specific to SOL Decoder bot output. You need actual bot logs to use this tool effectively.

### 2. Run the Analysis

Execute the main analyzer:
```bash
python main_analyzer.py
```

The tool will:
1. Extract position data from SOL Decoder logs → `positions_to_analyze.csv`
2. Fetch Meteora pool price history for each position
3. Run strategy simulations for all combinations
4. Generate detailed reports in `detailed_reports/`
5. Create final summary with optimal strategies → `final_analysis_report.csv`

### 3. Review Results

- **Individual Reports**: Check `detailed_reports/` for position-specific analysis
- **Summary Report**: Review `final_analysis_report.csv` for comparative results
- **Logs**: Monitor console output for processing status and any issues

**Remember**: Focus on **relative rankings** and **trends** rather than absolute PnL values. Use results to identify which strategies tend to perform better in different market conditions.

## Output Files

| File | Description |
|------|-------------|
| `positions_to_analyze.csv` | Extracted position data from SOL Decoder logs |
| `final_analysis_report.csv` | Strategy comparison with optimal recommendations |
| `detailed_reports/*.txt` | Individual position analysis with all strategy results |
| `price_cache/` | Cached Meteora pool price data (auto-generated) |

## Project Structure

```
├── main_analyzer.py          # Main orchestration script
├── log_extractor.py          # SOL Decoder log parsing and position extraction
├── strategy_analyzer.py      # Strategy simulation engine for Meteora DLMM
├── input/                    # Place your SOL Decoder log files here
├── detailed_reports/         # Generated individual position reports
├── price_cache/             # Cached Meteora pool price data
├── .env                     # API configuration (create this)
└── requirements.txt         # Python dependencies
```

## Configuration

Key configuration variables in each module:

### Log Extractor (`log_extractor.py`)
- `LOG_DIR`: Input directory for log files (default: "input")
- `OUTPUT_CSV`: Output CSV filename (default: "positions_to_analyze.csv")

### Main Analyzer (`main_analyzer.py`)
- `POSITIONS_CSV`: Position data file (default: "positions_to_analyze.csv")
- `FINAL_REPORT_CSV`: Final report filename (default: "final_analysis_report.csv")
- `DETAILED_REPORTS_DIR`: Individual reports directory (default: "detailed_reports")
- `PRICE_CACHE_DIR`: Price cache directory (default: "price_cache")

### Strategy Analyzer (`strategy_analyzer.py`)
- `bin_step`: Price step between bins in basis points (default: 100)
- `num_bins`: Number of bins in liquidity distribution (default: 69)

## API Requirements

This tool requires a Moralis API key for fetching Solana/Meteora price data:

1. Sign up at [moralis.io](https://moralis.io)
2. Get your free API key from the dashboard  
3. Add it to your `.env` file as `MORALIS_API_KEY`

The tool automatically handles:
- Rate limiting (0.6s between requests)
- Response caching to minimize API usage
- Error handling for network issues

## Log Format Requirements

This tool is designed specifically for SOL Decoder bot logs. The bot generates logs with:

- Position opening events with strategy information
- Pool addresses for Meteora DLMM pairs
- Investment amounts and PnL calculations
- Timestamps in the format `v1.2.3-MM/DD-HH:MM:SS`

**Important**: You need actual SOL Decoder bot logs to use this analyzer. The log structure is specific to that bot's output format.

## Troubleshooting

### Common Issues

**No positions extracted:**
- Verify you're using actual SOL Decoder bot log files
- Check that files start with "app" and contain ".log"
- Ensure the bot logs contain position opening/closing events

**API errors:**
- Verify your Moralis API key is correct
- Check network connectivity
- Monitor rate limiting (tool includes automatic delays)

**Invalid dates:**
- The tool handles some date edge cases automatically
- Check that your SOL Decoder logs have valid timestamps

### Debug Mode

Enable debug logging by modifying the logging level:
```python
logging.basicConfig(level=logging.DEBUG, ...)
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License. Feel free to copy, modify, and use this code however you like.

## Disclaimer

**This tool is an MVP for educational and exploratory analysis only.** 

- The strategy simulations use simplified models and should not be considered precise financial predictions
- Results are intended for **relative comparison** and **trend identification** only
- Always conduct additional research and analysis before making investment decisions
- The tool works with past performance data, which does not guarantee future results
- SOL Decoder bot performance may vary significantly from these simplified simulations

**Use responsibly**: This tool helps identify patterns and potential strategies for further investigation, not as a definitive trading signal.

## Support

If you encounter issues or have questions:

1. Check the [Issues](https://github.com/yourusername/solana-lp-strategy-analyzer/issues) page
2. Create a new issue with detailed information about your problem
3. Include relevant log snippets and error messages

---

**Happy analyzing! 📊🚀**