#!/usr/bin/env python3
"""
Test Trading Script
Test placing trades through the Alpaca API (paper trading only)
"""

import os
import sys
from dotenv import load_dotenv
from src.alpaca.client import AlpacaClient
import json

# Load environment
load_dotenv()

def get_account_info(client):
    """Get and display account info"""
    account = client.get_account()
    print("\n" + "=" * 60)
    print("ACCOUNT INFORMATION")
    print("=" * 60)
    print(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
    print(f"Cash Available: ${account['cash']:,.2f}")
    print(f"Buying Power: ${account['buying_power']:,.2f}")
    print(f"Trading Blocked: {account['trading_blocked']}")
    print("=" * 60 + "\n")
    return account

def get_positions(client):
    """Get and display current positions"""
    positions = client.get_positions()
    print("CURRENT POSITIONS:")
    print("-" * 60)
    if positions:
        for pos in positions:
            pl_sign = '+' if pos['unrealized_pl'] >= 0 else ''
            print(f"  {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
            print(f"    P/L: {pl_sign}${pos['unrealized_pl']:,.2f} ({pl_sign}{pos['unrealized_plpc']*100:.2f}%)")
    else:
        print("  No positions")
    print()
    return positions

def get_quote(client, symbol):
    """Get current quote for a symbol"""
    try:
        quote = client.get_latest_quote(symbol)
        print(f"\nCurrent Quote for {symbol}:")
        print(f"  Bid: ${quote['bid_price']:.2f} (size: {quote['bid_size']})")
        print(f"  Ask: ${quote['ask_price']:.2f} (size: {quote['ask_size']})")
        return quote
    except Exception as e:
        print(f"  Error getting quote: {e}")
        return None

def place_market_order_test(client, symbol, qty, side):
    """Test placing a market order"""
    print(f"\n{'='*60}")
    print(f"PLACING MARKET ORDER")
    print(f"{'='*60}")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {qty}")
    print(f"Order Type: MARKET")
    print(f"{'='*60}\n")
    
    try:
        result = client.place_market_order(
            symbol=symbol,
            qty=qty,
            side=side,
            time_in_force="day"
        )
        
        print("✓ ORDER PLACED SUCCESSFULLY!")
        print("\nOrder Details:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def place_limit_order_test(client, symbol, qty, side, limit_price):
    """Test placing a limit order"""
    print(f"\n{'='*60}")
    print(f"PLACING LIMIT ORDER")
    print(f"{'='*60}")
    print(f"Symbol: {symbol}")
    print(f"Side: {side.upper()}")
    print(f"Quantity: {qty}")
    print(f"Limit Price: ${limit_price:.2f}")
    print(f"Order Type: LIMIT")
    print(f"{'='*60}\n")
    
    try:
        result = client.place_limit_order(
            symbol=symbol,
            qty=qty,
            side=side,
            limit_price=limit_price,
            time_in_force="day"
        )
        
        print("✓ ORDER PLACED SUCCESSFULLY!")
        print("\nOrder Details:")
        print(json.dumps(result, indent=2))
        return result
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return None

def interactive_mode(client):
    """Interactive mode for testing trades"""
    account = get_account_info(client)
    positions = get_positions(client)
    
    print("=" * 60)
    print("INTERACTIVE TRADE TESTING")
    print("=" * 60)
    print("\nOptions:")
    print("  1. Place a MARKET BUY order")
    print("  2. Place a MARKET SELL order")
    print("  3. Place a LIMIT BUY order")
    print("  4. Place a LIMIT SELL order")
    print("  5. Get quote for a symbol")
    print("  6. View account info")
    print("  7. View positions")
    print("  0. Exit")
    
    while True:
        choice = input("\nSelect an option (0-7): ").strip()
        
        if choice == '0':
            print("Exiting...")
            break
        elif choice == '1':
            symbol = input("Enter symbol to BUY: ").strip().upper()
            qty = float(input("Enter quantity: "))
            get_quote(client, symbol)
            confirm = input(f"\nPlace MARKET BUY order for {qty} shares of {symbol}? (yes/no): ")
            if confirm.lower() == 'yes':
                place_market_order_test(client, symbol, qty, 'buy')
            else:
                print("Cancelled")
        elif choice == '2':
            if not positions:
                print("No positions to sell")
                continue
            print("\nYour positions:")
            for i, pos in enumerate(positions):
                print(f"  {i+1}. {pos['symbol']}: {pos['qty']} shares")
            try:
                idx = int(input("Select position number: ")) - 1
                pos = positions[idx]
                qty = float(input(f"Enter quantity to sell (max {pos['qty']}): "))
                if qty > pos['qty']:
                    print("Quantity exceeds position size")
                    continue
                confirm = input(f"\nPlace MARKET SELL order for {qty} shares of {pos['symbol']}? (yes/no): ")
                if confirm.lower() == 'yes':
                    place_market_order_test(client, pos['symbol'], qty, 'sell')
                else:
                    print("Cancelled")
            except (ValueError, IndexError):
                print("Invalid selection")
        elif choice == '3':
            symbol = input("Enter symbol to BUY: ").strip().upper()
            qty = float(input("Enter quantity: "))
            limit_price = float(input("Enter limit price: $"))
            get_quote(client, symbol)
            confirm = input(f"\nPlace LIMIT BUY order for {qty} shares of {symbol} @ ${limit_price:.2f}? (yes/no): ")
            if confirm.lower() == 'yes':
                place_limit_order_test(client, symbol, qty, 'buy', limit_price)
            else:
                print("Cancelled")
        elif choice == '4':
            if not positions:
                print("No positions to sell")
                continue
            print("\nYour positions:")
            for i, pos in enumerate(positions):
                print(f"  {i+1}. {pos['symbol']}: {pos['qty']} shares @ ${pos['current_price']:.2f}")
            try:
                idx = int(input("Select position number: ")) - 1
                pos = positions[idx]
                qty = float(input(f"Enter quantity to sell (max {pos['qty']}): "))
                if qty > pos['qty']:
                    print("Quantity exceeds position size")
                    continue
                limit_price = float(input("Enter limit price: $"))
                confirm = input(f"\nPlace LIMIT SELL order for {qty} shares of {pos['symbol']} @ ${limit_price:.2f}? (yes/no): ")
                if confirm.lower() == 'yes':
                    place_limit_order_test(client, pos['symbol'], qty, 'sell', limit_price)
                else:
                    print("Cancelled")
            except (ValueError, IndexError):
                print("Invalid selection")
        elif choice == '5':
            symbol = input("Enter symbol: ").strip().upper()
            get_quote(client, symbol)
        elif choice == '6':
            get_account_info(client)
        elif choice == '7':
            get_positions(client)
        else:
            print("Invalid option")

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Alpaca trading API')
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode (recommended)'
    )
    parser.add_argument(
        '--market-buy',
        nargs=2,
        metavar=('SYMBOL', 'QTY'),
        help='Place market buy order (e.g., --market-buy AAPL 1)'
    )
    parser.add_argument(
        '--market-sell',
        nargs=2,
        metavar=('SYMBOL', 'QTY'),
        help='Place market sell order (e.g., --market-sell TSLA 1)'
    )
    parser.add_argument(
        '--limit-buy',
        nargs=3,
        metavar=('SYMBOL', 'QTY', 'PRICE'),
        help='Place limit buy order (e.g., --limit-buy AAPL 1 150.00)'
    )
    parser.add_argument(
        '--limit-sell',
        nargs=3,
        metavar=('SYMBOL', 'QTY', 'PRICE'),
        help='Place limit sell order (e.g., --limit-sell TSLA 1 400.00)'
    )
    
    args = parser.parse_args()
    
    # Check environment
    env = os.getenv('ALPACA_ENV', 'paper')
    if env.lower() != 'paper':
        print("⚠️  WARNING: You are NOT in paper trading mode!")
        confirm = input("Continue anyway? (yes/no): ")
        if confirm.lower() != 'yes':
            print("Exiting...")
            return
    
    # Get credentials
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    
    if not api_key or not secret_key:
        print("❌ Missing Alpaca API credentials in .env file")
        return
    
    # Initialize client
    client = AlpacaClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=(env.lower() == 'paper')
    )
    
    print(f"\n{'='*60}")
    print(f"ALPACA TRADING API TEST")
    print(f"{'='*60}")
    print(f"Environment: {env.upper()} trading")
    print(f"{'='*60}\n")
    
    # Interactive mode
    if args.interactive or (not args.market_buy and not args.market_sell and not args.limit_buy and not args.limit_sell):
        interactive_mode(client)
        return
    
    # Command line mode
    account = get_account_info(client)
    
    if args.market_buy:
        symbol, qty = args.market_buy
        place_market_order_test(client, symbol.upper(), float(qty), 'buy')
    
    if args.market_sell:
        symbol, qty = args.market_sell
        place_market_order_test(client, symbol.upper(), float(qty), 'sell')
    
    if args.limit_buy:
        symbol, qty, price = args.limit_buy
        place_limit_order_test(client, symbol.upper(), float(qty), 'buy', float(price))
    
    if args.limit_sell:
        symbol, qty, price = args.limit_sell
        place_limit_order_test(client, symbol.upper(), float(qty), 'sell', float(price))

if __name__ == '__main__':
    main()

