"""
Template Formatter
Formats portfolio data into the custom LLM prompt template
"""

import logging
from typing import Dict, List
from datetime import datetime, date

logger = logging.getLogger(__name__)


def format_portfolio_template(
    account: Dict,
    positions_with_history: Dict[str, Dict],
    starting_value: float = 1000.0
) -> str:
    """
    Format portfolio data into the custom template format
    
    Args:
        account: Account information
        positions_with_history: Dict of positions with history (from build_position_history)
        starting_value: Starting portfolio value (default $1000)
    
    Returns:
        Formatted template string
    """
    today = date.today()
    current_value = account['portfolio_value']
    available_cash = account['cash']
    buying_power = account['buying_power']
    
    # Build template header
    template = f"""Nightly Portfolio Check-In
Current Portfolio Value: ${current_value:,.2f}
Available Cash: ${available_cash:,.2f}
Buying Power: ${buying_power:,.2f}

Current Positions:
"""
    
    # Format each position with entry date and details
    for symbol, pos_data in positions_with_history.items():
        current = pos_data.get('current', {})
        market_value = current.get('market_value', 0)
        current_price = current.get('current_price', 0)
        qty = current.get('qty', 0)
        
        # Get entry date from history (first buy order)
        history = pos_data.get('history', [])
        entry_date = None
        entry_price = None
        
        for trans in history:
            if trans.get('action') == 'Bought':
                entry_date = trans.get('date')
                entry_price = trans.get('price', 0)
                break
        
        # Calculate days held
        days_held = None
        if entry_date:
            try:
                entry = datetime.strptime(entry_date, '%Y-%m-%d').date()
                days_held = (today - entry).days
            except:
                pass
        
        template += f"\n{symbol}:\n"
        template += f"  Current Value: ${market_value:,.2f} ({qty:.0f} shares @ ${current_price:.2f})\n"
        
        if entry_date and entry_price:
            template += f"  Entry Date: {entry_date} ({days_held} days ago)\n"
            template += f"  Entry Price: ${entry_price:.2f}\n"
            
            # Calculate P&L
            if current_price > 0 and entry_price > 0:
                pnl_pct = ((current_price - entry_price) / entry_price) * 100
                pnl_sign = "+" if pnl_pct >= 0 else ""
                template += f"  P&L: {pnl_sign}{pnl_pct:.2f}%\n"
        
        template += "\n"
    
    # If no positions
    if not positions_with_history:
        template += "No current positions.\n\n"
    
    template += f"Available Cash for New Positions: ${available_cash:,.2f}\n"
    
    return template

