"""
Template Formatter
Formats portfolio data into the custom LLM prompt template
"""

import logging
from typing import Dict, List
from src.utils.position_history import calculate_days_since_start
from src.utils.notes_manager import get_note

logger = logging.getLogger(__name__)


def format_portfolio_template(
    account: Dict,
    positions_with_history: Dict[str, Dict],
    notes: Dict[str, str],
    starting_value: float = 1000.0
) -> str:
    """
    Format portfolio data into the custom template format
    
    Args:
        account: Account information
        positions_with_history: Dict of positions with history (from build_position_history)
        notes: Dict of position notes
        starting_value: Starting portfolio value (default $1000)
    
    Returns:
        Formatted template string
    """
    day_number = calculate_days_since_start()
    current_value = account['portfolio_value']
    
    # Build header with "Your Daily Check-in:" section
    template = f"""Your Daily Check-in:
This is day '{day_number}' of the competition. The portfolio started with ${starting_value:.2f}. It's currently trading at '${current_value:.2f}'. Below is an in depth look into your portfolio:

"""
    
    # Format each position
    for symbol, pos_data in positions_with_history.items():
        template += f"{symbol}\n"
        template += "History:\n"
        
        history = pos_data.get('history', [])
        if history:
            # First transaction (initial buy)
            first = history[0]
            template += f"- {first['action']} '{first['qty']:.0f}' shares on '{first['date']}' for '${first['value']:.2f}'.\n"
            
            # Subsequent transactions
            for trans in history[1:]:
                action = trans['action']
                if action == "Bought":
                    action_text = "Added"
                elif action == "Sold":
                    action_text = "Sold"
                else:
                    action_text = action
                
                template += f"- {action_text} '{trans['qty']:.0f}' shares for '${trans['value']:.2f}' on '{trans['date']}'.\n"
        else:
            template += "- No transaction history available.\n"
        
        # Current holdings
        current = pos_data.get('current', {})
        template += "Currently:\n"
        template += f"- Hold '{current.get('qty', 0):.0f}' shares valued at '${current.get('market_value', 0):.2f}'.\n"
        
        # Previous notes
        note_text = get_note(symbol, notes)
        template += "Previous Notes:\n"
        template += f"{note_text}\n"
        template += "\n"
    
    return template

