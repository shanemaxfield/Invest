# Quick Start Guide - 6-Layer Autonomous Trading System

## 🎯 What Was Built

A complete 6-layer autonomous trading system that:
- ✅ **Eliminates LLM math errors** (all calculations done by code)
- ✅ **Provides perfect memory** (LLM sees its own investment thesis for each position)
- ✅ **Automatic safety exits** (stop losses and targets trigger without LLM)
- ✅ **Enforces capital deployment** (minimum 80% cash deployment)
- ✅ **Multi-layer validation** (catches errors before execution)

## 🚀 Getting Started (5 Steps)

### Step 1: Install Dependencies

```bash
cd /home/user/Invest
pip install -r requirements.txt
```

### Step 2: Configure Environment

Ensure your `.env` file has:
```bash
ALPACA_API_KEY=your_alpaca_key
ALPACA_SECRET_KEY=your_alpaca_secret
ALPACA_ENV=paper
OPENAI_API_KEY=your_openai_key
LLM_MODEL=gpt-4-turbo-preview
```

### Step 3: Backfill Existing Positions

If you have existing positions, generate thesis data for them:

```bash
python backfill_thesis.py
```

This creates investment theses for all current positions so the LLM has memory from the start.

### Step 4: Test in Dry-Run Mode

```bash
python main.py --mode once
```

This runs a complete trading cycle without executing real trades. Review:
- `logs/latest_context.json` - Pre-calculated options
- `logs/latest_llm_decisions.json` - LLM decisions
- `logs/latest_execution_results.json` - What would have executed

### Step 5: Go Live

When ready:

```bash
# Single run (live trading)
python main.py --mode once --live

# Scheduled nightly runs (live trading)
python main.py --mode schedule --live
```

## 📁 What Gets Created

After running, you'll have:

### Position Notes (`logs/position_notes.json`)
Contains investment thesis for each position:
```json
{
  "NVDA": {
    "entry_date": "2025-11-28",
    "entry_price": 145.50,
    "investment_thesis": "Playing AI GPU demand into Q4 earnings",
    "target_price": 165.00,
    "stop_loss": 138.00,
    "time_horizon_weeks": 3,
    "target_exit_date": "2025-12-19",
    "expected_catalyst": "Q4 earnings on 2025-12-15",
    "review_history": [...]
  }
}
```

### Archived Notes (`logs/archived_notes/`)
When positions are sold, notes are archived (not deleted) with timestamp and reason.

### Decision Logs
- `logs/latest_context.json` - Pre-calculated buy/sell options
- `logs/latest_llm_decisions.json` - LLM's decisions
- `logs/latest_execution_results.json` - Execution results
- `logs/trading.log` - Application logs

## 🔍 How It Works

```
1. Load position notes (investment theses)
2. Pre-calculate ALL buy/sell options (no LLM math)
3. Check automatic exits (stop loss, target price)
4. Get LLM decisions WITH memory injection
5. Validate decisions (multi-layer checks)
6. Execute trades with safety limits
7. Update position notes (save memory)
```

## 🛡️ Safety Features

- **Dry run by default** - Must use `--live` flag
- **Position limits** - Max 25% portfolio per position
- **Trade limits** - Max $10,000 per trade
- **Cash reserve** - Always keep $100 minimum
- **Automatic exits** - Stop losses bypass LLM
- **Validation** - Catches errors before execution

## 📊 Example LLM Decision

The LLM now responds in this format (NO math needed):

```json
{
  "position_decisions": [
    {
      "symbol": "NVDA",
      "action": "HOLD",
      "reasoning": "Thesis intact, approaching Q4 earnings catalyst"
    }
  ],
  "cash_deployment": {
    "deployment_option": "DEPLOY_ALL_CASH",
    "new_positions": [
      {
        "symbol": "AAPL",
        "allocation_percent": 100,
        "investment_thesis": "iPhone 16 demand strong into holidays",
        "target_price": 200.00,
        "stop_loss": 175.00,
        "time_horizon_weeks": 4,
        "target_exit_date": "2025-12-30",
        "expected_catalyst": "Holiday sales report"
      }
    ]
  }
}
```

## 🧪 Testing

Run unit tests:
```bash
python test_architecture.py
```

This verifies all 6 layers work correctly.

## 📚 Documentation

- **ARCHITECTURE.md** - Detailed architecture explanation
- **IMPLEMENTATION_COMPLETE.md** - Complete implementation summary
- **QUICKSTART.md** - This file

## 🔧 Troubleshooting

### "No module named 'alpaca'" error
Run: `pip install -r requirements.txt`

### "Missing thesis data" warnings
Run: `python backfill_thesis.py`

### Validation errors
Check `logs/latest_llm_decisions.json` - LLM may have returned invalid format

### No trades executed
Verify you're using `--live` flag for real trading

## 💡 Key Concepts

### Pre-Calculated Options
The system calculates exact dollar amounts and share quantities BEFORE the LLM runs. The LLM simply picks from these options:

**Buy Options:**
- DEPLOY_80_PERCENT: $4,000 (minimum required)
- DEPLOY_ALL_CASH: $5,000 (recommended)

**Sell Options for NVDA:**
- HOLD: No action
- TRIM_25: Sell 25 shares (~$3,687)
- TRIM_50: Sell 50 shares (~$7,375)
- SELL_ALL: Sell 100 shares (~$14,750)

### Memory Injection
For each position, the LLM sees:
- Original entry date and price
- Investment thesis it wrote when buying
- Target price and stop loss
- Expected catalyst
- Days held and days remaining
- All past review decisions

### Automatic Exits
The rules engine checks BEFORE the LLM runs:
- If price <= stop_loss → automatic SELL_ALL
- If price >= target_price → automatic SELL_ALL

These trades execute WITHOUT LLM decision.

## ✅ Success Checklist

Before going live:
- [ ] Dependencies installed
- [ ] Environment configured
- [ ] Existing positions backfilled
- [ ] Dry run successful
- [ ] Reviewed LLM prompt (thesis injection working)
- [ ] Reviewed LLM decisions (new format correct)
- [ ] Reviewed execution results (trades look correct)

## 🎯 What's Different From Before

**Before:**
- LLM calculated dollar amounts → frequent math errors
- No memory of investment theses
- All decisions went through LLM
- Minimal validation
- Could hold cash idle

**After:**
- LLM picks from pre-calculated options → zero math errors
- Perfect memory of all investment theses
- Automatic exits for critical triggers
- Multi-layer validation
- Minimum 80% cash deployment enforced

## 📞 Need Help?

1. Check `logs/trading.log` for detailed logs
2. Review `ARCHITECTURE.md` for deep dive
3. Check `IMPLEMENTATION_COMPLETE.md` for complete documentation

---

**Ready to start? Run:** `python main.py --mode once` (dry run)
