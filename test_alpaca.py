#!/usr/bin/env python3
"""
Alpaca API Test Script
Tests connectivity and basic functionality of the Alpaca API
"""

import os
import sys
from dotenv import load_dotenv
from src.utils.logger import setup_logging
from src.alpaca.client import AlpacaClient
from src.alpaca.portfolio_formatter import PortfolioFormatter
import logging

logger = logging.getLogger(__name__)


def test_connection():
    """Test basic connection to Alpaca API"""
    print("\n" + "=" * 60)
    print("ALPACA API CONNECTION TEST")
    print("=" * 60)

    # Load environment
    load_dotenv()
    setup_logging(log_level='INFO')

    # Get credentials
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    env = os.getenv('ALPACA_ENV', 'paper')

    if not api_key or not secret_key:
        print("❌ ERROR: Missing Alpaca API credentials")
        print("Please set ALPACA_API_KEY and ALPACA_SECRET_KEY in .env file")
        return False

    print(f"\n✓ Credentials found")
    print(f"✓ Environment: {env.upper()}")

    # Initialize client
    try:
        client = AlpacaClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=(env.lower() == 'paper')
        )
        print("✓ Alpaca client initialized")
    except Exception as e:
        print(f"❌ ERROR initializing client: {e}")
        return False

    # Test 1: Get account info
    print("\n" + "-" * 60)
    print("TEST 1: Fetch Account Information")
    print("-" * 60)
    try:
        account = client.get_account()
        print("✓ Account data retrieved successfully")
        print(f"\n  Portfolio Value: ${account['portfolio_value']:,.2f}")
        print(f"  Cash: ${account['cash']:,.2f}")
        print(f"  Buying Power: ${account['buying_power']:,.2f}")
        print(f"  Equity: ${account['equity']:,.2f}")
        print(f"  Pattern Day Trader: {account['pattern_day_trader']}")
        print(f"  Trading Blocked: {account['trading_blocked']}")
    except Exception as e:
        print(f"❌ ERROR getting account: {e}")
        return False

    # Test 2: Get positions
    print("\n" + "-" * 60)
    print("TEST 2: Fetch Current Positions")
    print("-" * 60)
    try:
        positions = client.get_positions()
        print(f"✓ Positions retrieved: {len(positions)} positions found")

        if positions:
            print("\n  Current positions:")
            for pos in positions:
                pl_sign = '+' if pos['unrealized_pl'] >= 0 else ''
                print(f"    - {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
                print(f"      Market Value: ${pos['market_value']:,.2f}")
                print(f"      P/L: {pl_sign}${pos['unrealized_pl']:,.2f} ({pl_sign}{pos['unrealized_plpc']*100:.2f}%)")
        else:
            print("  No positions currently held")
    except Exception as e:
        print(f"❌ ERROR getting positions: {e}")
        return False

    # Test 3: Get orders
    print("\n" + "-" * 60)
    print("TEST 3: Fetch Recent Orders")
    print("-" * 60)
    try:
        orders = client.get_orders(status='all')
        print(f"✓ Orders retrieved: {len(orders)} orders found")

        if orders:
            # Show last 5 orders
            recent_orders = orders[:5]
            print(f"\n  Last {len(recent_orders)} orders:")
            for order in recent_orders:
                print(f"    - {order['side'].upper()} {order['qty']} {order['symbol']}")
                print(f"      Status: {order['status']} | Type: {order['type']}")
                print(f"      Submitted: {order['submitted_at']}")
        else:
            print("  No orders found")
    except Exception as e:
        print(f"❌ ERROR getting orders: {e}")
        return False

    # Test 4: Test data formatting
    print("\n" + "-" * 60)
    print("TEST 4: Portfolio Data Formatting")
    print("-" * 60)
    try:
        formatter = PortfolioFormatter()
        formatted_data = formatter.format_for_llm(account, positions)
        print("✓ Portfolio data formatted successfully")

        print("\n  Formatted summary:")
        print(f"    Total Positions: {formatted_data['summary_statistics']['total_positions']}")
        print(f"    Total Invested: ${formatted_data['summary_statistics']['total_invested']:,.2f}")
        print(f"    Cash %: {formatted_data['account_summary']['cash_percentage']:.1f}%")

        # Test JSON conversion
        json_str = formatter.to_json_string(formatted_data, pretty=False)
        print(f"✓ JSON conversion successful ({len(json_str)} chars)")

        # Test context string creation
        context = formatter.create_llm_prompt_context(formatted_data)
        print(f"✓ LLM context created ({len(context)} chars)")

    except Exception as e:
        print(f"❌ ERROR formatting data: {e}")
        return False

    # Test 5: Test quote fetching (if we have a position)
    if positions and len(positions) > 0:
        print("\n" + "-" * 60)
        print("TEST 5: Fetch Latest Quote")
        print("-" * 60)
        test_symbol = positions[0]['symbol']
        try:
            quote = client.get_latest_quote(test_symbol)
            print(f"✓ Quote retrieved for {test_symbol}")
            print(f"\n  Bid: ${quote['bid_price']:.2f} (size: {quote['bid_size']})")
            print(f"  Ask: ${quote['ask_price']:.2f} (size: {quote['ask_size']})")
        except Exception as e:
            print(f"⚠ WARNING: Could not fetch quote for {test_symbol}: {e}")

    # All tests passed
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nYour Alpaca API connection is working correctly.")
    print("You can now run the main trading bot with: python main.py")
    print("\n")

    return True


if __name__ == '__main__':
    success = test_connection()
    sys.exit(0 if success else 1)
