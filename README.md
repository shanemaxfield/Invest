# AI-Powered Alpaca Trading Bot

An automated trading system that uses AI (LLM) to analyze your portfolio and make trading decisions through the Alpaca API.

## Overview

This trading bot:
- Connects to Alpaca's trading API to access your portfolio
- Fetches account information and current positions
- Formats data into a structured format for AI analysis
- Uses an LLM (OpenAI GPT-4) to analyze the portfolio and recommend trades
- Executes trades based on the LLM's recommendations
- Runs on a schedule (default: 8pm MT daily)

## Features

- **Alpaca Integration**: Full integration with Alpaca's paper and live trading APIs
- **LLM-Driven Decisions**: Uses GPT-4 to analyze portfolios and suggest trades
- **Safety Controls**: Includes dry-run mode, position limits, and validation
- **Scheduling**: Automated daily runs at a specified time
- **Comprehensive Logging**: Detailed logs of all operations
- **Data Export**: Saves portfolio data and decisions to JSON files

## Project Structure

```
Invest/
├── src/
│   ├── alpaca/              # Alpaca API client and portfolio formatter
│   │   ├── client.py        # Main Alpaca API wrapper
│   │   └── portfolio_formatter.py  # Formats data for LLM
│   ├── llm/                 # LLM integration
│   │   └── trading_advisor.py      # AI trading advisor
│   ├── scheduler/           # Scheduling system
│   │   └── trading_scheduler.py    # Daily run scheduler
│   └── utils/               # Utilities
│       ├── logger.py        # Logging configuration
│       └── trade_executor.py       # Trade execution with safety checks
├── logs/                    # Log files and data exports
├── main.py                  # Main orchestrator
├── test_alpaca.py          # Alpaca API test script
├── setup.sh                # Setup script
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md              # This file
```

## Prerequisites

- Python 3.8 or higher
- Alpaca account (paper or live)
- OpenAI API account (for LLM features)

## Installation

### 1. Clone the repository

```bash
git clone <your-repo-url>
cd Invest
```

### 2. Run the setup script

```bash
./setup.sh
```

This will:
- Create a Python virtual environment
- Install all dependencies
- Create a `.env` file from the template
- Set up the logs directory

### 3. Configure your API keys

Edit the `.env` file and add your credentials:

```bash
# Alpaca API Credentials
ALPACA_API_KEY=your_api_key_here
ALPACA_SECRET_KEY=your_secret_key_here
ALPACA_ENV=paper  # Use 'paper' for testing, 'live' for real trading

# OpenAI API Key
OPENAI_API_KEY=your_openai_api_key_here
```

**Getting API Keys:**

- **Alpaca**: Sign up at [alpaca.markets](https://alpaca.markets) and get your API keys from the dashboard
  - Paper trading: https://app.alpaca.markets/paper/dashboard/overview
  - Live trading: https://app.alpaca.markets/live/dashboard/overview
- **OpenAI**: Get your API key from [platform.openai.com/api-keys](https://platform.openai.com/api-keys)

## Usage

### Test Alpaca Connection

Before running the bot, test your Alpaca API connection:

```bash
python test_alpaca.py
```

This will verify:
- API credentials are working
- Account information can be retrieved
- Portfolio positions can be fetched
- Data formatting works correctly

### Running the Bot

#### Run Once (Immediate)

Execute a single trading cycle immediately:

```bash
# Dry run (no actual trades)
python main.py --mode once

# Live trading (CAREFUL!)
python main.py --mode once --live
```

#### Scheduled Mode

Start the scheduler for daily automated runs:

```bash
# Start scheduler (dry run)
python main.py --mode schedule

# Start scheduler and run immediately
python main.py --mode schedule --run-immediately

# Start scheduler with live trading (CAREFUL!)
python main.py --mode schedule --live
```

### Command Line Options

- `--mode`: `once` (run immediately) or `schedule` (daily scheduled runs)
- `--live`: Enable live trading (default: dry run)
- `--run-immediately`: When using schedule mode, run once immediately before starting scheduler

## How It Works

### Trading Cycle

Each trading cycle consists of 4 steps:

1. **Fetch Portfolio Data**
   - Retrieves account information (cash, portfolio value, buying power)
   - Gets current positions with P/L data
   - Fetches recent orders

2. **Format Data for LLM**
   - Converts raw API data into a structured JSON format
   - Calculates percentages, allocations, and statistics
   - Creates human-readable context for the LLM

3. **Get LLM Decisions**
   - Sends formatted portfolio data to OpenAI GPT-4
   - LLM analyzes the portfolio and market conditions
   - Returns structured trading recommendations with reasoning

4. **Execute Trades**
   - Validates each recommendation against safety rules
   - Executes approved trades (market or limit orders)
   - Logs all results and saves to files

### Safety Features

The bot includes multiple safety mechanisms:

- **Dry Run Mode**: Test without executing real trades (default)
- **Position Limits**: Maximum position size as % of portfolio (default: 20%)
- **Trade Value Limits**: Maximum dollar amount per trade (default: $10,000)
- **Buying Power Checks**: Ensures sufficient funds before buying
- **Position Verification**: Verifies you own shares before selling
- **Validation**: Strict validation of LLM outputs
- **Paper Trading**: Use Alpaca's paper trading environment for testing

### LLM Prompt System

The LLM receives:
- Complete portfolio snapshot with all positions
- Account balances and buying power
- Performance metrics (P/L, allocations, etc.)
- Custom instructions (optional)

The LLM returns:
- Detailed analysis of the portfolio
- Market outlook and risk assessment
- Specific trading actions (BUY/SELL/HOLD)
- Reasoning and conviction levels for each trade
- Warnings and recommendations

## Configuration

### Environment Variables (.env)

```bash
# Alpaca Configuration
ALPACA_API_KEY=your_key
ALPACA_SECRET_KEY=your_secret
ALPACA_ENV=paper  # 'paper' or 'live'

# LLM Configuration
OPENAI_API_KEY=your_key
LLM_MODEL=gpt-4-turbo-preview

# Scheduler Configuration
SCHEDULED_HOUR=20  # 8 PM
SCHEDULED_MINUTE=0
TIMEZONE=America/Denver  # Mountain Time

# Logging
LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR, CRITICAL
```

### Customizing Safety Limits

Edit `main.py` to modify safety limits:

```python
self.trade_executor = TradeExecutor(
    alpaca_client=self.alpaca_client,
    dry_run=dry_run,
    max_position_pct=20.0,    # Max 20% per position
    max_trade_value=10000.0   # Max $10k per trade
)
```

### Customizing LLM Behavior

The LLM system prompt can be modified in `src/llm/trading_advisor.py`:

```python
def _build_system_prompt(self) -> str:
    return """Your custom instructions here..."""
```

## Output Files

The bot saves data to the `logs/` directory:

- `trading.log` - Complete log of all operations
- `latest_portfolio_data.json` - Most recent portfolio snapshot
- `latest_llm_decisions.json` - Most recent LLM analysis and decisions
- `latest_execution_results.json` - Results of trade execution

## Important Notes

### Paper Trading First

**Always start with paper trading!** Set `ALPACA_ENV=paper` in your `.env` file and test thoroughly before considering live trading.

### Dry Run Mode

The default mode is dry run, which simulates trades without executing them. This is perfect for:
- Testing your setup
- Validating LLM decisions
- Understanding the bot's behavior

### Live Trading Warnings

**Live trading involves real money and real risk!**

- Only use the `--live` flag when you're absolutely ready
- Start with very small amounts
- Monitor the bot closely
- Understand that you can lose money
- The bot's decisions are AI-generated and not financial advice

### Market Hours

Alpaca trading is only available during market hours:
- Regular: 9:30 AM - 4:00 PM ET (Monday-Friday)
- Extended: 4:00 AM - 8:00 PM ET (varies by account type)

Schedule your bot to run during market hours, or use limit orders for after-hours execution.

## Troubleshooting

### "Missing Alpaca API credentials"

Make sure your `.env` file exists and contains valid `ALPACA_API_KEY` and `ALPACA_SECRET_KEY`.

### "Error getting account info"

- Verify your API keys are correct
- Check if you're using the right environment (paper vs live)
- Ensure your internet connection is working

### "No OpenAI API key found"

Add your `OPENAI_API_KEY` to the `.env` file. Without it, the LLM features won't work.

### Import errors

Make sure you've installed all dependencies:
```bash
pip install -r requirements.txt
```

## Development

### Running Tests

```bash
# Test Alpaca connectivity
python test_alpaca.py

# Test a single trading cycle (dry run)
python main.py --mode once
```

### Adding New Features

The modular structure makes it easy to extend:

- Add new data sources in `src/alpaca/`
- Modify LLM behavior in `src/llm/`
- Add trading strategies in `src/utils/`
- Customize scheduling in `src/scheduler/`

## License

This project is for educational and personal use only. Not financial advice.

## Disclaimer

**This bot is provided as-is for educational purposes.**

- Not financial advice
- No guarantees of profitability
- You are responsible for all trading decisions
- Past performance does not guarantee future results
- Use at your own risk

Always consult with a qualified financial advisor before making investment decisions.
