#!/usr/bin/env python3
"""
Preview Prompt Template
Shows what the formatted prompt would look like without needing OpenAI API key
"""

import os
import sys
from dotenv import load_dotenv
from src.utils.logger import setup_logging
from src.alpaca.client import AlpacaClient
from src.utils.position_history import build_position_history
from src.utils.template_formatter import format_portfolio_template
from src.llm.trading_advisor import TradingAdvisor
import logging

logger = logging.getLogger(__name__)


def main():
    """Preview the formatted prompt template"""
    print("=" * 60)
    print("PREVIEWING PORTFOLIO PROMPT TEMPLATE")
    print("=" * 60)
    print()
    
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
        return
    
    try:
        # Initialize client
        print("Fetching data from Alpaca...")
        client = AlpacaClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=(env.lower() == 'paper')
        )
        
        # Fetch data
        account = client.get_account()
        positions = client.get_positions()
        orders = client.get_orders(status='all')
        
        print(f"✓ Fetched {len(positions)} positions")
        print(f"✓ Fetched {len(orders)} orders")
        print()
        
        # Build position history
        print("Building position history...")
        positions_with_history = build_position_history(positions, orders)
        print(f"✓ Built history for {len(positions_with_history)} positions")
        print()
        
        # Format template
        print("Formatting template...")
        portfolio_template = format_portfolio_template(
            account, 
            positions_with_history
        )
        print("✓ Template formatted")
        print()
        
        # Get system and user prompts from the actual TradingAdvisor class
        # We need to create an instance, but we'll use a mock OpenAI client to avoid API calls
        # Actually, let's use a workaround - create a minimal class that inherits the methods
        # Or better yet, let's just import and call the methods directly using a mock
        
        # Create a mock OpenAI client class that won't actually initialize
        class MockOpenAI:
            def __init__(self, *args, **kwargs):
                pass  # Don't actually initialize anything
        
        # Temporarily replace OpenAI with our mock
        import src.llm.trading_advisor as ta_module
        original_openai = ta_module.OpenAI
        ta_module.OpenAI = MockOpenAI
        
        try:
            # Now we can create a TradingAdvisor instance without it trying to connect
            advisor = TradingAdvisor(api_key="dummy", model="gpt-4-turbo-preview")
            system_prompt = advisor._build_system_prompt()
            user_prompt = advisor._build_user_prompt(portfolio_template)
        finally:
            # Restore the original OpenAI class
            ta_module.OpenAI = original_openai
        
        # Display the full prompt
        print("=" * 60)
        print("SYSTEM PROMPT (ROLE & CONTEXT)")
        print("=" * 60)
        print()
        print(system_prompt)
        print()
        print("=" * 60)
        print("USER PROMPT (PORTFOLIO DATA)")
        print("=" * 60)
        print()
        print(user_prompt)
        print()
        print("=" * 60)
        
        # Save to files
        os.makedirs('logs', exist_ok=True)
        with open('logs/preview_prompt.txt', 'w') as f:
            f.write(portfolio_template)
        with open('logs/preview_full_prompt.txt', 'w') as f:
            f.write("=" * 60 + "\n")
            f.write("SYSTEM PROMPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(system_prompt)
            f.write("\n\n" + "=" * 60 + "\n")
            f.write("USER PROMPT\n")
            f.write("=" * 60 + "\n\n")
            f.write(user_prompt)
        print()
        print("✓ Template saved to logs/preview_prompt.txt")
        print("✓ Full prompt (system + user) saved to logs/preview_full_prompt.txt")
        print()
        
    except Exception as e:
        print(f"❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()

