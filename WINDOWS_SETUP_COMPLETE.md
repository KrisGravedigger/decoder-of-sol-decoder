# Windows Setup Guide for SOL Decoder Strategy Analyzer

## ✅ Installation Complete!

All required libraries have been successfully installed for Windows. The application is now ready to run.

## 📦 Installed Libraries

The following Python packages have been installed via pip:

### Core Data Analysis
- **pandas** (>=1.5.0, <3.0.0) - Data manipulation and analysis
- **numpy** (>=1.21.0) - Numerical computing
- **scipy** (>=1.9.0) - Scientific computing

### Data Visualization
- **plotly** (>=5.0.0) - Interactive charts and plots
- **matplotlib** (>=3.5.0) - Static plotting
- **seaborn** (>=0.11.0) - Statistical visualization

### Web & API
- **requests** (>=2.28.0, <3.0.0) - HTTP requests for API calls

### Configuration & Environment
- **python-dotenv** (>=0.19.0, <2.0.0) - Environment variable management
- **PyYAML** (>=6.0) - YAML configuration file handling

### User Interface & Utilities
- **tqdm** (>=4.64.0) - Progress bars
- **Jinja2** (>=3.0.0) - HTML template engine for reports

## 🔧 Configuration Files Created

1. **requirements.txt** - Complete list of all dependencies
2. **.env** - Environment configuration (set to offline mode by default)
3. **.env.template** - Template for environment configuration

## 🚀 How to Run the Application

```powershell
# Navigate to the project directory
cd "c:\Users\krzys\Desktop\Decoder of SOL Decoder v3"

# Run the main application
python main.py
```

The application will display an interactive menu with the following options:

1. **Data Preparation** - Extract and process log files
2. **Data Fetching** - Fetch market data (requires API key)
3. **Reporting** - Generate analysis reports
4. **Full Standard Pipeline** - Complete automated analysis
5. **Full Optimization Pipeline** - Advanced optimization analysis
6. **TP/SL Range Testing** - Take Profit/Stop Loss optimization
7. **TLS Analysis** - Trailing Stop Loss analysis
8. **Cache Management** - Data cache debugging tools
0. **Exit** - Close the application

## 🔑 API Configuration (Optional)

To enable online data fetching:

1. Open the `.env` file
2. Replace `MORALIS_API_KEY=` with your actual Moralis API key
3. Set `CACHE_ONLY=false` if you want to enable online mode

The application can run in offline mode using cached data without an API key.

## 🐛 Troubleshooting

If you encounter any import errors:

```powershell
# Verify all packages are installed correctly
python -c "import pandas, numpy, plotly, matplotlib, seaborn, requests, dotenv, yaml, scipy, tqdm, jinja2; print('All packages OK!')"

# Reinstall requirements if needed
pip install -r requirements.txt --force-reinstall
```

## 📁 Project Structure

The project uses the following structure:
- `main.py` - Main application entry point
- `core/` - Core data models
- `extraction/` - Log file processing
- `reporting/` - Analysis and report generation
- `simulations/` - Strategy simulation engines
- `data_fetching/` - Market data management
- `tools/` - Debugging and utility tools
- `utils/` - Common utilities

## ✅ Windows-Specific Notes

- PowerShell is used as the shell environment
- All Python packages are compatible with Windows
- File paths use Windows backslash format
- The application handles Windows-specific path separators automatically

Your SOL Decoder Strategy Analyzer is now fully configured and ready for use on Windows!