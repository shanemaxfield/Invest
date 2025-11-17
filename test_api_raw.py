#!/usr/bin/env python3
"""
Quick script to see raw API responses from Alpaca
"""

import os
import json
from dotenv import load_dotenv
from src.alpaca.client import AlpacaClient

# Load environment
load_dotenv()

# Get credentials
api_key = os.getenv('ALPACA_API_KEY')
secret_key = os.getenv('ALPACA_SECRET_KEY')
env = os.getenv('ALPACA_ENV', 'paper')

if not api_key or not secret_key:
    print("❌ Missing API credentials in .env file")
    exit(1)

# Initialize client
client = AlpacaClient(
    api_key=api_key,
    secret_key=secret_key,
    paper=(env.lower() == 'paper')
)

print("=" * 60)
print("RAW ALPACA API RESPONSES")
print("=" * 60)

# Get account info
print("\n1. ACCOUNT INFO:")
print("-" * 60)
account = client.get_account()
print(json.dumps(account, indent=2))

# Get positions
print("\n\n2. POSITIONS:")
print("-" * 60)
positions = client.get_positions()
print(json.dumps(positions, indent=2))

# Get orders
print("\n\n3. RECENT ORDERS:")
print("-" * 60)
orders = client.get_orders(status='all')
print(json.dumps(orders[:5], indent=2))  # Show last 5 orders

# Get quote for a position if available
if positions:
    print("\n\n4. LATEST QUOTE (for first position):")
    print("-" * 60)
    symbol = positions[0]['symbol']
    quote = client.get_latest_quote(symbol)
    print(json.dumps(quote, indent=2))

print("\n" + "=" * 60)

