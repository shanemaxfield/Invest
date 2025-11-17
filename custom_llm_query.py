#!/usr/bin/env python3
"""
Custom LLM Query Tool
Pull select data points from Alpaca and feed them into a custom LLM prompt
"""

import os
import json
import sys
from dotenv import load_dotenv
from src.alpaca.client import AlpacaClient
from openai import OpenAI

# Load environment
load_dotenv()

def get_alpaca_data():
    """Fetch data from Alpaca API"""
    api_key = os.getenv('ALPACA_API_KEY')
    secret_key = os.getenv('ALPACA_SECRET_KEY')
    env = os.getenv('ALPACA_ENV', 'paper')
    
    if not api_key or not secret_key:
        raise ValueError("Missing Alpaca API credentials")
    
    client = AlpacaClient(
        api_key=api_key,
        secret_key=secret_key,
        paper=(env.lower() == 'paper')
    )
    
    account = client.get_account()
    positions = client.get_positions()
    orders = client.get_orders(status='all')[:5]  # Last 5 orders
    
    return {
        'account': account,
        'positions': positions,
        'orders': orders
    }

def extract_data_points(data, selections):
    """
    Extract selected data points from Alpaca data
    
    Args:
        data: Full data from Alpaca
        selections: List of data point paths (e.g., ['account.cash', 'positions[0].symbol'])
    
    Returns:
        Dict with selected data points
    """
    extracted = {}
    
    for selection in selections:
        parts = selection.split('.')
        value = data
        
        try:
            for part in parts:
                if '[' in part and ']' in part:
                    # Handle array access like 'positions[0]'
                    key = part[:part.index('[')]
                    index = int(part[part.index('[')+1:part.index(']')])
                    value = value[key][index]
                else:
                    value = value[part]
            
            extracted[selection] = value
        except (KeyError, IndexError, TypeError) as e:
            extracted[selection] = f"Error: {e}"
    
    return extracted

def query_llm(data_points, custom_prompt, model="gpt-4-turbo-preview"):
    """
    Send data points and custom prompt to LLM
    
    Args:
        data_points: Dict of selected data points
        custom_prompt: Your custom prompt/question
        model: OpenAI model to use
    """
    openai_key = os.getenv('OPENAI_API_KEY')
    if not openai_key:
        raise ValueError("Missing OPENAI_API_KEY in .env file")
    
    client = OpenAI(api_key=openai_key)
    
    # Build the message
    data_str = json.dumps(data_points, indent=2)
    
    system_prompt = """You are a helpful financial analysis assistant. 
Analyze the provided data points and answer the user's question based on that data."""
    
    user_message = f"""Here are the selected data points from my portfolio:

{data_str}

---

{custom_prompt}"""
    
    print("=" * 60)
    print("SENDING TO LLM...")
    print("=" * 60)
    print(f"\nData Points:\n{data_str}\n")
    print(f"Your Prompt:\n{custom_prompt}\n")
    print("=" * 60)
    print("LLM RESPONSE:")
    print("=" * 60)
    
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        temperature=0.7
    )
    
    return response.choices[0].message.content

def main():
    """Main function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Query LLM with custom Alpaca data')
    parser.add_argument(
        '--prompt',
        type=str,
        help='Your custom prompt/question for the LLM'
    )
    parser.add_argument(
        '--data',
        nargs='+',
        help='Data points to extract (e.g., account.cash positions[0].symbol)',
        default=['account.portfolio_value', 'account.cash', 'positions']
    )
    parser.add_argument(
        '--model',
        type=str,
        default='gpt-4-turbo-preview',
        help='OpenAI model to use'
    )
    parser.add_argument(
        '--interactive',
        action='store_true',
        help='Interactive mode - enter prompt and data points'
    )
    
    args = parser.parse_args()
    
    # Fetch data from Alpaca
    print("Fetching data from Alpaca...")
    data = get_alpaca_data()
    print("✓ Data fetched\n")
    
    if args.interactive:
        # Interactive mode
        print("Available data structure:")
        print(json.dumps({
            'account': list(data['account'].keys()),
            'positions': f"Array of {len(data['positions'])} positions",
            'orders': f"Array of {len(data['orders'])} orders"
        }, indent=2))
        print("\nExample data point paths:")
        print("  - account.cash")
        print("  - account.portfolio_value")
        print("  - positions[0].symbol")
        print("  - positions[0].unrealized_pl")
        print("  - positions (all positions)")
        print()
        
        data_selections = input("Enter data points to extract (space-separated, or 'all' for everything): ").strip()
        if data_selections.lower() == 'all':
            data_points = data
        else:
            selections = data_selections.split()
            data_points = extract_data_points(data, selections)
        
        prompt = input("\nEnter your custom prompt/question: ").strip()
        if not prompt:
            print("No prompt provided, exiting")
            return
    else:
        # Command line mode
        if not args.prompt:
            print("Error: --prompt is required (or use --interactive)")
            parser.print_help()
            return
        
        data_points = extract_data_points(data, args.data)
        prompt = args.prompt
    
    # Query LLM
    try:
        response = query_llm(data_points, prompt, args.model)
        print(f"\n{response}\n")
        
        # Save to file
        output = {
            'data_points': data_points,
            'prompt': prompt,
            'response': response
        }
        os.makedirs('logs', exist_ok=True)
        with open('logs/custom_llm_query.json', 'w') as f:
            json.dump(output, f, indent=2)
        print("✓ Response saved to logs/custom_llm_query.json")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()

