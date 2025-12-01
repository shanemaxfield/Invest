"""
Decision Context Builder - Layer 1
Pre-calculates all buy/sell options so LLM doesn't need to do math
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


def build_decision_context(
    account: Dict,
    positions: List[Dict],
    notes: Dict[str, Dict]
) -> Dict:
    """
    Build pre-calculated decision context for LLM

    Args:
        account: Account information from Alpaca
        positions: List of current positions
        notes: Position notes with thesis data

    Returns:
        Structured context with pre-calculated options
    """
    available_cash = account['cash']
    buying_power = account['buying_power']
    portfolio_value = account['portfolio_value']

    # Pre-calculate buy options (deployment levels)
    buy_options = {
        'DEPLOY_25_PERCENT': {
            'amount': round(available_cash * 0.25, 2),
            'description': f'Deploy ${available_cash * 0.25:,.2f} (25% of cash)'
        },
        'DEPLOY_50_PERCENT': {
            'amount': round(available_cash * 0.50, 2),
            'description': f'Deploy ${available_cash * 0.50:,.2f} (50% of cash)'
        },
        'DEPLOY_80_PERCENT': {
            'amount': round(available_cash * 0.80, 2),
            'description': f'Deploy ${available_cash * 0.80:,.2f} (80% of cash - MINIMUM REQUIRED)'
        },
        'DEPLOY_ALL_CASH': {
            'amount': round(available_cash, 2),
            'description': f'Deploy ${available_cash:,.2f} (100% of cash - RECOMMENDED)'
        },
        'HOLD_CASH': {
            'amount': 0.0,
            'description': 'Hold cash (NOT RECOMMENDED - only if market conditions are extremely unfavorable)'
        }
    }

    # Pre-calculate sell options for each position
    position_options = {}
    for position in positions:
        symbol = position['symbol']
        qty = position['qty']
        current_price = position['current_price']
        market_value = position['market_value']

        position_options[symbol] = {
            'HOLD': {
                'qty': 0,
                'value': 0.0,
                'description': 'Hold position (no action)'
            },
            'TRIM_25': {
                'qty': int(qty * 0.25),
                'value': round(market_value * 0.25, 2),
                'description': f'Sell {int(qty * 0.25)} shares (~${market_value * 0.25:,.2f})'
            },
            'TRIM_50': {
                'qty': int(qty * 0.50),
                'value': round(market_value * 0.50, 2),
                'description': f'Sell {int(qty * 0.50)} shares (~${market_value * 0.50:,.2f})'
            },
            'SELL_ALL': {
                'qty': int(qty),
                'value': round(market_value, 2),
                'description': f'Sell all {int(qty)} shares (~${market_value:,.2f})'
            }
        }

    context = {
        'timestamp': datetime.now().isoformat(),
        'account': {
            'available_cash': round(available_cash, 2),
            'buying_power': round(buying_power, 2),
            'portfolio_value': round(portfolio_value, 2),
            'equity': round(account['equity'], 2)
        },
        'buy_options': buy_options,
        'position_options': position_options,
        'positions_data': {},  # Will be enriched with notes and current data
        'summary': {
            'total_positions': len(positions),
            'total_market_value': round(sum(p['market_value'] for p in positions), 2),
            'cash_percentage': round((available_cash / portfolio_value * 100) if portfolio_value > 0 else 0, 2)
        }
    }

    # Enrich positions with current data and notes
    for position in positions:
        symbol = position['symbol']
        context['positions_data'][symbol] = {
            'current': {
                'qty': position['qty'],
                'current_price': position['current_price'],
                'market_value': position['market_value'],
                'avg_entry_price': position['avg_entry_price'],
                'unrealized_pl': position['unrealized_pl'],
                'unrealized_plpc': position['unrealized_plpc']
            },
            'notes': notes.get(symbol, None)  # May be None if no thesis data yet
        }

    logger.info(f"Built decision context: ${available_cash:,.2f} cash, {len(positions)} positions")

    return context


def calculate_shares_for_amount(amount: float, price: float) -> int:
    """
    Calculate number of shares that can be purchased with given amount

    Args:
        amount: Dollar amount to invest
        price: Price per share

    Returns:
        Number of shares (integer)
    """
    if price <= 0:
        return 0
    return int(amount / price)


def validate_deployment_amount(
    deployment_option: str,
    new_positions: List[Dict],
    buy_options: Dict
) -> Dict:
    """
    Validate that new positions match the deployment option

    Args:
        deployment_option: The deployment option chosen
        new_positions: List of new positions with allocation percentages
        buy_options: Pre-calculated buy options

    Returns:
        Dict with 'valid' boolean and 'details' dict
    """
    if deployment_option == 'HOLD_CASH':
        if new_positions:
            return {
                'valid': False,
                'reason': 'HOLD_CASH selected but new positions provided'
            }
        return {'valid': True, 'total_amount': 0.0}

    deployment_amount = buy_options[deployment_option]['amount']

    # Calculate total allocation percentage
    total_allocation_pct = sum(pos.get('allocation_percent', 0) for pos in new_positions)

    # Allow 1% tolerance for rounding
    if abs(total_allocation_pct - 100) > 1:
        return {
            'valid': False,
            'reason': f'Allocation percentages sum to {total_allocation_pct}%, must sum to 100%'
        }

    # Calculate individual amounts
    position_amounts = []
    for pos in new_positions:
        allocation = pos.get('allocation_percent', 0)
        amount = deployment_amount * (allocation / 100.0)
        position_amounts.append({
            'symbol': pos.get('symbol'),
            'allocation_percent': allocation,
            'amount': round(amount, 2)
        })

    return {
        'valid': True,
        'total_amount': deployment_amount,
        'positions': position_amounts
    }
