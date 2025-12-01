"""
Rules Engine - Layer 2
Automatic exits based on stop loss and target prices
"""

import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


def apply_rules_engine(
    positions: List[Dict],
    notes: Dict[str, Dict],
    context: Dict
) -> Tuple[List[Dict], List[str]]:
    """
    Apply automatic exit rules and flag positions for LLM review

    Args:
        positions: List of current positions
        notes: Position notes with thesis data
        context: Decision context from builder

    Returns:
        Tuple of (automatic_actions, flagged_positions)
        - automatic_actions: List of automatic SELL_ALL actions
        - flagged_positions: List of symbols flagged for review
    """
    automatic_actions = []
    flagged_positions = []

    today = datetime.now().date()

    for position in positions:
        symbol = position['symbol']
        current_price = position['current_price']
        qty = position['qty']

        # Get thesis data from notes
        position_notes = notes.get(symbol)

        # Skip positions without thesis data (can't apply rules)
        if not position_notes:
            logger.warning(f"{symbol}: No thesis data found, skipping rules engine")
            flagged_positions.append(symbol)
            continue

        stop_loss = position_notes.get('stop_loss')
        target_price = position_notes.get('target_price')
        target_exit_date = position_notes.get('target_exit_date')
        entry_date_str = position_notes.get('entry_date')

        # Check STOP LOSS trigger (automatic SELL_ALL)
        if stop_loss and current_price <= stop_loss:
            logger.warning(f"{symbol}: STOP LOSS TRIGGERED - Price ${current_price:.2f} <= Stop ${stop_loss:.2f}")
            automatic_actions.append({
                'symbol': symbol,
                'action': 'SELL_ALL',
                'qty': int(qty),
                'reason': f'AUTOMATIC: Stop loss triggered (${current_price:.2f} <= ${stop_loss:.2f})',
                'trigger': 'STOP_LOSS'
            })
            continue  # Don't send to LLM, automatic exit

        # Check TARGET PRICE reached (automatic SELL_ALL)
        if target_price and current_price >= target_price:
            logger.info(f"{symbol}: TARGET PRICE REACHED - Price ${current_price:.2f} >= Target ${target_price:.2f}")
            automatic_actions.append({
                'symbol': symbol,
                'action': 'SELL_ALL',
                'qty': int(qty),
                'reason': f'AUTOMATIC: Target price reached (${current_price:.2f} >= ${target_price:.2f})',
                'trigger': 'TARGET_REACHED'
            })
            continue  # Don't send to LLM, automatic exit

        # Flag positions needing review (not automatic exit, but LLM should pay attention)

        # Check if time horizon expired
        if target_exit_date:
            try:
                exit_date = datetime.strptime(target_exit_date, '%Y-%m-%d').date()
                if today >= exit_date:
                    logger.info(f"{symbol}: Time horizon expired (target exit: {target_exit_date})")
                    flagged_positions.append(symbol)
                    continue
            except ValueError:
                logger.error(f"{symbol}: Invalid target_exit_date format: {target_exit_date}")

        # Check if near stop loss (within 5%)
        if stop_loss:
            distance_to_stop = ((current_price - stop_loss) / stop_loss) * 100
            if distance_to_stop < 5:
                logger.info(f"{symbol}: NEAR STOP LOSS - Only {distance_to_stop:.1f}% away")
                flagged_positions.append(symbol)
                continue

        # Check if near target (within 5%)
        if target_price:
            distance_to_target = ((target_price - current_price) / current_price) * 100
            if distance_to_target < 5:
                logger.info(f"{symbol}: NEAR TARGET - Only {distance_to_target:.1f}% away")
                flagged_positions.append(symbol)
                continue

    # Log summary
    if automatic_actions:
        logger.warning(f"Rules engine triggered {len(automatic_actions)} automatic exits")
        for action in automatic_actions:
            logger.warning(f"  - {action['symbol']}: {action['trigger']} - {action['reason']}")

    if flagged_positions:
        logger.info(f"Flagged {len(flagged_positions)} positions for LLM review: {', '.join(flagged_positions)}")

    return automatic_actions, flagged_positions


def get_status_summary(
    symbol: str,
    position: Dict,
    notes: Dict,
    is_flagged: bool = False
) -> str:
    """
    Get status summary for a position

    Args:
        symbol: Stock symbol
        position: Position data
        notes: Position notes
        is_flagged: Whether position is flagged for review

    Returns:
        Status summary string
    """
    if not notes:
        return "⚠️ No thesis data available"

    current_price = position['current_price']
    stop_loss = notes.get('stop_loss')
    target_price = notes.get('target_price')

    # Check if price is within expected range
    if stop_loss and target_price:
        if stop_loss < current_price < target_price:
            status = "✓ Thesis intact (price between stop and target)"
        elif current_price <= stop_loss:
            status = "⚠️ BELOW STOP LOSS"
        elif current_price >= target_price:
            status = "✓ ABOVE TARGET PRICE"
        else:
            status = "→ In range"
    else:
        status = "→ Monitoring"

    # Add flagged indicator
    if is_flagged:
        status += " [NEEDS REVIEW]"

    return status


def calculate_days_remaining(target_exit_date: str) -> int:
    """
    Calculate days remaining until target exit date

    Args:
        target_exit_date: Target exit date string (YYYY-MM-DD)

    Returns:
        Number of days remaining (negative if past)
    """
    try:
        exit_date = datetime.strptime(target_exit_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        delta = (exit_date - today).days
        return delta
    except (ValueError, TypeError):
        return 0


def calculate_days_held(entry_date: str) -> int:
    """
    Calculate days held since entry

    Args:
        entry_date: Entry date string (YYYY-MM-DD)

    Returns:
        Number of days held
    """
    try:
        entry = datetime.strptime(entry_date, '%Y-%m-%d').date()
        today = datetime.now().date()
        delta = (today - entry).days
        return delta
    except (ValueError, TypeError):
        return 0
