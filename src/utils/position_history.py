"""
Position History Builder
Builds transaction history from positions and orders
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Competition start date (hardcoded for now)
COMPETITION_START_DATE = datetime(2025, 11, 16)  # Tomorrow


def calculate_days_since_start() -> int:
    """
    Calculate days since competition start
    
    Returns:
        Number of days
    """
    today = datetime.now().date()
    start = COMPETITION_START_DATE.date()
    days = (today - start).days + 1  # +1 to include today
    return max(1, days)  # At least day 1


def build_position_history(positions: List[Dict], orders: List[Dict]) -> Dict[str, Dict]:
    """
    Build transaction history for each position
    
    Args:
        positions: List of current positions
        orders: List of all orders
    
    Returns:
        Dict mapping symbol to position data with history
    """
    # Create a dict of positions by symbol
    positions_dict = {pos['symbol']: pos for pos in positions}
    
    # Group orders by symbol
    orders_by_symbol = {}
    for order in orders:
        symbol = order['symbol']
        if symbol not in orders_by_symbol:
            orders_by_symbol[symbol] = []
        orders_by_symbol[symbol].append(order)
    
    # Build history for each position
    result = {}
    for symbol, position in positions_dict.items():
        symbol_orders = orders_by_symbol.get(symbol, [])
        
        # Filter to filled orders and sort by date
        filled_orders = [
            o for o in symbol_orders 
            if o.get('status') == 'filled' and o.get('filled_at')
        ]
        filled_orders.sort(key=lambda x: x.get('filled_at', x.get('submitted_at', '')))
        
        # Build history array
        history = []
        for order in filled_orders:
            action = "Bought" if order['side'] == 'buy' else "Sold"
            qty = order.get('filled_qty', order.get('qty', 0))
            price = order.get('filled_avg_price', order.get('avg_fill_price', 0))
            value = qty * price if price > 0 else 0
            date = order.get('filled_at', order.get('submitted_at', ''))
            
            # Format date to ISO format (YYYY-MM-DD)
            if date:
                try:
                    # Parse datetime string and extract date
                    if 'T' in str(date):
                        date_str = str(date).split('T')[0]
                    else:
                        date_str = str(date).split()[0]
                except:
                    date_str = str(date)
            else:
                date_str = "Unknown"
            
            history.append({
                'action': action,
                'qty': qty,
                'price': price,
                'value': value,
                'date': date_str
            })
        
        result[symbol] = {
            'current': {
                'qty': position['qty'],
                'market_value': position['market_value'],
                'current_price': position['current_price']
            },
            'history': history
        }
    
    return result

