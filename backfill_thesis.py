#!/usr/bin/env python3
"""
Backfill Thesis Data Helper
Generates thesis data for existing positions that don't have it
"""

import os
import json
import sys
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime, timedelta

from src.alpaca.client import AlpacaClient
from src.utils.notes_manager import load_notes, save_notes, create_position_note


def backfill_thesis_data():
    """Use LLM to generate thesis data for existing positions"""

    # Load environment
    load_dotenv()

    # Initialize Alpaca client
    alpaca_api_key = os.getenv('ALPACA_API_KEY')
    alpaca_secret_key = os.getenv('ALPACA_SECRET_KEY')
    alpaca_env = os.getenv('ALPACA_ENV', 'paper')

    if not alpaca_api_key or not alpaca_secret_key:
        print("❌ Missing Alpaca API credentials")
        return

    alpaca_client = AlpacaClient(
        api_key=alpaca_api_key,
        secret_key=alpaca_secret_key,
        paper=(alpaca_env.lower() == 'paper')
    )

    # Initialize OpenAI client
    openai_api_key = os.getenv('OPENAI_API_KEY')
    if not openai_api_key:
        print("❌ Missing OpenAI API key")
        return

    openai_client = OpenAI(api_key=openai_api_key)
    model = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')

    # Get current positions
    print("Fetching current positions...")
    positions = alpaca_client.get_positions()
    orders = alpaca_client.get_orders(status='all')

    if not positions:
        print("✓ No positions to backfill")
        return

    # Load existing notes
    notes = load_notes()

    # Find positions without thesis data
    positions_to_backfill = []
    for position in positions:
        symbol = position['symbol']
        if symbol not in notes:
            positions_to_backfill.append(position)

    if not positions_to_backfill:
        print("✓ All positions already have thesis data")
        return

    print(f"\nFound {len(positions_to_backfill)} positions without thesis data:")
    for pos in positions_to_backfill:
        print(f"  - {pos['symbol']}: {pos['qty']} shares @ ${pos['avg_entry_price']:.2f}")

    print("\nGenerating thesis data using LLM...")

    # For each position, get thesis from LLM
    for position in positions_to_backfill:
        symbol = position['symbol']
        qty = position['qty']
        entry_price = position['avg_entry_price']
        current_price = position['current_price']

        # Find entry date from orders
        entry_date = None
        for order in orders:
            if order['symbol'] == symbol and order.get('status') == 'filled':
                filled_at = order.get('filled_at', order.get('submitted_at', ''))
                if filled_at:
                    try:
                        entry_date = filled_at.split('T')[0]
                        break
                    except:
                        pass

        if not entry_date:
            entry_date = datetime.now().strftime('%Y-%m-%d')

        print(f"\n{symbol}:")
        print(f"  Entry: ${entry_price:.2f} on {entry_date}")
        print(f"  Current: ${current_price:.2f}")

        # Build prompt for LLM
        prompt = f"""You are analyzing an existing stock position. Generate a realistic investment thesis for this position.

Position Details:
- Symbol: {symbol}
- Entry Price: ${entry_price:.2f}
- Entry Date: {entry_date}
- Current Price: ${current_price:.2f}
- Shares: {qty}

Please provide a complete investment thesis in JSON format:

{{
  "investment_thesis": "2-3 sentences explaining why this is a good investment opportunity",
  "target_price": <realistic target price above current price>,
  "stop_loss": <realistic stop loss below entry price>,
  "time_horizon_weeks": <number between 2-8>,
  "target_exit_date": "YYYY-MM-DD",
  "expected_catalyst": "Brief description of expected catalyst"
}}

Requirements:
- Target price must be > current price (${current_price:.2f})
- Stop loss must be < entry price (${entry_price:.2f})
- Target exit date must be within time_horizon_weeks from today
- Investment thesis should be realistic and market-aware

Respond with JSON only."""

        try:
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": "You are a professional equity analyst generating investment theses."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )

            thesis_data = json.loads(response.choices[0].message.content)

            # Create position note
            note = create_position_note(
                symbol=symbol,
                entry_price=entry_price,
                investment_thesis=thesis_data['investment_thesis'],
                target_price=thesis_data['target_price'],
                stop_loss=thesis_data['stop_loss'],
                time_horizon_weeks=thesis_data['time_horizon_weeks'],
                target_exit_date=thesis_data['target_exit_date'],
                expected_catalyst=thesis_data['expected_catalyst'],
                entry_date=entry_date
            )

            notes[symbol] = note

            print(f"  ✓ Generated thesis:")
            print(f"    Thesis: {thesis_data['investment_thesis'][:60]}...")
            print(f"    Target: ${thesis_data['target_price']:.2f}")
            print(f"    Stop: ${thesis_data['stop_loss']:.2f}")
            print(f"    Exit: {thesis_data['target_exit_date']}")

        except Exception as e:
            print(f"  ❌ Failed to generate thesis: {e}")
            continue

    # Save updated notes
    save_notes(notes)

    print(f"\n✅ Backfilled thesis data for {len(positions_to_backfill)} positions")
    print(f"Saved to logs/position_notes.json")


if __name__ == '__main__':
    backfill_thesis_data()
