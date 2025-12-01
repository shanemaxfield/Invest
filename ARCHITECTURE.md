# 6-Layer Autonomous Trading System Architecture

## Overview

This system implements a 6-layer architecture that eliminates LLM math errors and provides perfect memory between trading sessions.

## The 6 Layers

### Layer 0: Data Fetching
- Fetches account, positions, and order data from Alpaca
- Loads position notes (investment theses) from disk

### Layer 1: Decision Context Builder (`src/utils/decision_context_builder.py`)
**Purpose**: Pre-calculate ALL buy/sell options so LLM doesn't need to do math

**What it does**:
- Calculates exact dollar amounts for buy options (25%, 50%, 80%, 100% of cash)
- Calculates exact share quantities for sell options (HOLD, TRIM_25, TRIM_50, SELL_ALL)
- Returns structured context with all options pre-computed

**Why**: LLM simply picks from options - no calculation errors possible

### Layer 2: Rules Engine (`src/utils/rules_engine.py`)
**Purpose**: Automatic exits based on stop loss and target prices

**What it does**:
- Checks if current price <= stop_loss → automatic SELL_ALL (bypasses LLM)
- Checks if current price >= target_price → automatic SELL_ALL (bypasses LLM)
- Flags positions needing review (time horizon expired, near stop loss)
- Returns automatic actions + flagged positions

**Why**: Critical exits happen automatically - no LLM decision needed

### Layer 3: LLM Trading Advisor (`src/llm/trading_advisor.py`)
**Purpose**: Make decisions with perfect memory and constrained choices

**What it does**:
- Injects original investment thesis for EACH position into prompt
- Shows LLM its own reasoning from when it bought the position
- Provides pre-calculated options (LLM just picks, doesn't calculate)
- Enforces minimum 80% cash deployment
- New response format with thesis data for all new positions

**Why**: LLM sees its past decisions and reasons about them

### Layer 4: Decision Validator (`src/utils/decision_validator.py`)
**Purpose**: Validate LLM responses before execution

**What it does**:
- Validates response structure (all required fields present)
- Validates actions are from allowed set
- Validates new position allocations sum to 100%
- Validates target_price > stop_loss for new positions
- Validates symbols, time horizons, dates

**Why**: Catch errors before executing trades

### Layer 5: Trade Executor (`src/utils/trade_executor.py`)
**Purpose**: Execute trades with safety limits

**What it does**:
1. Execute automatic exits first (from rules engine)
2. Execute position management (trims, sells from LLM)
3. Execute new position buys (using pre-calculated amounts)
4. Apply safety limits:
   - MAX_POSITION_SIZE = 25% of portfolio
   - MAX_SINGLE_TRADE = $10,000
   - MIN_CASH_RESERVE = $100

**Why**: Defense in depth - safety limits prevent catastrophic errors

### Layer 6: Memory Manager (`src/utils/notes_manager.py`)
**Purpose**: Maintain perfect memory between runs

**What it does**:
- Saves complete thesis data for new positions
- Updates review history for all positions (even HOLD decisions)
- Archives notes for exited positions (preserves history)
- Loads notes at startup so LLM sees past decisions

**Why**: LLM never forgets why it bought a position

## Position Notes Structure

```json
{
  "NVDA": {
    "entry_date": "2025-11-28",
    "entry_price": 145.50,
    "investment_thesis": "Playing AI GPU demand into Q4 earnings. Expecting datacenter beat.",
    "target_price": 165.00,
    "stop_loss": 138.00,
    "time_horizon_weeks": 3,
    "target_exit_date": "2025-12-19",
    "expected_catalyst": "Q4 earnings 2025-12-15",
    "created_at": "2025-11-28T20:00:00",
    "review_history": [
      {
        "date": "2025-11-29",
        "decision": "HOLD",
        "reasoning": "Thesis intact, approaching catalyst"
      }
    ]
  }
}
```

## LLM Response Format

```json
{
  "position_decisions": [
    {
      "symbol": "NVDA",
      "action": "HOLD | TRIM_25 | TRIM_50 | SELL_ALL",
      "reasoning": "Brief explanation based on original thesis"
    }
  ],
  "cash_deployment": {
    "deployment_option": "DEPLOY_80_PERCENT | DEPLOY_ALL_CASH",
    "new_positions": [
      {
        "symbol": "AAPL",
        "allocation_percent": 50,
        "investment_thesis": "2-3 sentences explaining the play",
        "target_price": 150.00,
        "stop_loss": 135.00,
        "time_horizon_weeks": 4,
        "target_exit_date": "2025-12-15",
        "expected_catalyst": "Q4 earnings on 2025-12-15"
      }
    ]
  }
}
```

## Flow Diagram

```
1. Fetch Data (account, positions, notes)
   ↓
2. Layer 1: Pre-calculate all buy/sell options
   ↓
3. Layer 2: Apply rules engine (automatic exits)
   ↓
4. Layer 3: Get LLM decisions (with memory injection)
   ↓
5. Layer 4: Validate decisions
   ↓
6. Layer 5: Execute with safety limits
   ↓
7. Layer 6: Update memory (save notes)
```

## Key Features

### ✅ No Math Errors
- LLM picks from pre-calculated options
- All dollar amounts and share quantities calculated by code
- LLM never does arithmetic

### ✅ Perfect Memory
- Every position has investment thesis
- LLM sees its own past reasoning
- Review history tracks all decisions

### ✅ Automatic Safety
- Stop losses trigger automatically
- Target prices trigger automatically
- Safety limits prevent oversized positions

### ✅ Minimum Cash Deployment
- LLM must deploy ≥80% of cash
- Can't hold cash idle
- Aggressive capital deployment

## Usage

### First Time Setup (Backfill Existing Positions)

If you have existing positions without thesis data:

```bash
python backfill_thesis.py
```

This will use the LLM to generate thesis data for all existing positions.

### Run Trading Cycle

```bash
# Dry run (recommended first)
python main.py --mode once

# Live trading
python main.py --mode once --live

# Scheduled daily runs
python main.py --mode schedule --live
```

### Check Logs

```bash
# View position notes
cat logs/position_notes.json

# View latest context
cat logs/latest_context.json

# View LLM decisions
cat logs/latest_llm_decisions.json

# View execution results
cat logs/latest_execution_results.json

# View archived notes
ls logs/archived_notes/
```

## Safety Features

1. **Dry Run by Default**: Must explicitly pass `--live` flag
2. **Position Size Limits**: Max 25% portfolio per position
3. **Trade Size Limits**: Max $10k per trade
4. **Cash Reserve**: Always keep $100 minimum
5. **Validation Layer**: Catches errors before execution
6. **Automatic Exits**: Stop losses and targets bypass LLM

## Monitoring

The system logs all actions to `logs/trading.log` and saves:
- Decision context: `logs/latest_context.json`
- LLM decisions: `logs/latest_llm_decisions.json`
- Execution results: `logs/latest_execution_results.json`
- Position notes: `logs/position_notes.json`
- Archived notes: `logs/archived_notes/`

## Troubleshooting

### "Missing thesis data" warnings
Run `python backfill_thesis.py` to generate thesis for existing positions

### Validation errors
Check `logs/latest_llm_decisions.json` - LLM may have returned invalid format

### No trades executed
Check dry_run flag - remove it or add `--live` to execute real trades

### Stop losses not triggering
Verify position notes have `stop_loss` and `target_price` fields
