"""
Notes Manager - Layer 6 (Enhanced)
Handles loading, saving, and updating position notes with full thesis data
"""

import os
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

NOTES_FILE = 'logs/position_notes.json'
ARCHIVE_DIR = 'logs/archived_notes'


def load_notes() -> Dict[str, Dict]:
    """
    Load position notes from file

    Returns:
        Dict mapping symbol to thesis data
    """
    if not os.path.exists(NOTES_FILE):
        logger.info("No notes file found, starting with empty notes")
        return {}

    try:
        with open(NOTES_FILE, 'r') as f:
            notes = json.load(f)
        logger.info(f"Loaded notes for {len(notes)} positions")
        return notes
    except Exception as e:
        logger.error(f"Error loading notes: {e}")
        return {}


def save_notes(notes: Dict[str, Dict]) -> bool:
    """
    Save position notes to file

    Args:
        notes: Dict mapping symbol to thesis data

    Returns:
        True if successful
    """
    try:
        os.makedirs(os.path.dirname(NOTES_FILE), exist_ok=True)
        with open(NOTES_FILE, 'w') as f:
            json.dump(notes, f, indent=2)
        logger.info(f"Saved notes for {len(notes)} positions")
        return True
    except Exception as e:
        logger.error(f"Error saving notes: {e}")
        return False


def create_position_note(
    symbol: str,
    entry_price: float,
    investment_thesis: str,
    target_price: float,
    stop_loss: float,
    time_horizon_weeks: int,
    target_exit_date: str,
    expected_catalyst: str,
    entry_date: Optional[str] = None
) -> Dict:
    """
    Create a new position note with full thesis data

    Args:
        symbol: Stock symbol
        entry_price: Entry price
        investment_thesis: Investment thesis (2-3 sentences)
        target_price: Target price for exit
        stop_loss: Stop loss price
        time_horizon_weeks: Time horizon in weeks (2-8)
        target_exit_date: Target exit date (YYYY-MM-DD)
        expected_catalyst: Expected catalyst for price movement
        entry_date: Entry date (defaults to today)

    Returns:
        Position note dict
    """
    if entry_date is None:
        entry_date = datetime.now().strftime('%Y-%m-%d')

    note = {
        'entry_date': entry_date,
        'entry_price': round(entry_price, 2),
        'investment_thesis': investment_thesis.strip(),
        'target_price': round(target_price, 2),
        'stop_loss': round(stop_loss, 2),
        'time_horizon_weeks': time_horizon_weeks,
        'target_exit_date': target_exit_date,
        'expected_catalyst': expected_catalyst.strip(),
        'created_at': datetime.now().isoformat(),
        'review_history': []
    }

    logger.info(f"Created note for {symbol}: Target ${target_price}, Stop ${stop_loss}, Exit {target_exit_date}")

    return note


def add_review_entry(
    note: Dict,
    decision: str,
    reasoning: str
) -> Dict:
    """
    Add a review entry to position note

    Args:
        note: Position note dict
        decision: Decision made (HOLD, TRIM_25, TRIM_50, SELL_ALL)
        reasoning: Reasoning for decision

    Returns:
        Updated note dict
    """
    if 'review_history' not in note:
        note['review_history'] = []

    review_entry = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'decision': decision,
        'reasoning': reasoning.strip()
    }

    note['review_history'].append(review_entry)

    # Keep only last 30 reviews to avoid bloat
    if len(note['review_history']) > 30:
        note['review_history'] = note['review_history'][-30:]

    return note


def update_position_notes(
    existing_notes: Dict[str, Dict],
    new_positions: List[Dict],
    position_decisions: List[Dict],
    entry_prices: Dict[str, float]
) -> Dict[str, Dict]:
    """
    Update notes with new positions and decisions

    Args:
        existing_notes: Current notes
        new_positions: List of new positions from LLM
        position_decisions: List of position decisions from LLM
        entry_prices: Dict mapping symbol to entry price for new positions

    Returns:
        Updated notes dict
    """
    updated_notes = existing_notes.copy()

    # Add notes for new positions
    for new_pos in new_positions:
        symbol = new_pos['symbol']
        entry_price = entry_prices.get(symbol, 0.0)

        note = create_position_note(
            symbol=symbol,
            entry_price=entry_price,
            investment_thesis=new_pos['investment_thesis'],
            target_price=new_pos['target_price'],
            stop_loss=new_pos['stop_loss'],
            time_horizon_weeks=new_pos['time_horizon_weeks'],
            target_exit_date=new_pos['target_exit_date'],
            expected_catalyst=new_pos['expected_catalyst']
        )

        updated_notes[symbol] = note
        logger.info(f"Added thesis for new position: {symbol}")

    # Update review history for existing positions
    for decision in position_decisions:
        symbol = decision['symbol']
        action = decision['action']
        reasoning = decision.get('reasoning', 'No reasoning provided')

        if symbol in updated_notes:
            updated_notes[symbol] = add_review_entry(
                updated_notes[symbol],
                action,
                reasoning
            )

    return updated_notes


def archive_position_note(symbol: str, note: Dict, reason: str = "SOLD") -> bool:
    """
    Archive a position note when position is exited

    Args:
        symbol: Stock symbol
        note: Position note to archive
        reason: Reason for archiving (SOLD, STOP_LOSS, TARGET_REACHED, etc.)

    Returns:
        True if successful
    """
    try:
        # Create archive directory if it doesn't exist
        os.makedirs(ARCHIVE_DIR, exist_ok=True)

        # Create archive filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        archive_filename = f"{symbol}_{timestamp}_{reason}.json"
        archive_path = os.path.join(ARCHIVE_DIR, archive_filename)

        # Add archive metadata
        archived_note = note.copy()
        archived_note['archived_at'] = datetime.now().isoformat()
        archived_note['archive_reason'] = reason

        # Save to archive
        with open(archive_path, 'w') as f:
            json.dump(archived_note, f, indent=2)

        logger.info(f"Archived note for {symbol}: {archive_filename}")
        return True

    except Exception as e:
        logger.error(f"Error archiving note for {symbol}: {e}")
        return False


def remove_sold_positions(
    notes: Dict[str, Dict],
    sold_symbols: List[str],
    reasons: Dict[str, str]
) -> Dict[str, Dict]:
    """
    Remove notes for sold positions (after archiving)

    Args:
        notes: Current notes
        sold_symbols: List of symbols that were sold
        reasons: Dict mapping symbol to sell reason

    Returns:
        Updated notes dict
    """
    updated_notes = notes.copy()

    for symbol in sold_symbols:
        if symbol in updated_notes:
            # Archive the note first
            reason = reasons.get(symbol, "SOLD")
            archive_position_note(symbol, updated_notes[symbol], reason)

            # Remove from active notes
            del updated_notes[symbol]
            logger.info(f"Removed note for sold position: {symbol}")

    return updated_notes


def get_note(symbol: str, notes: Dict[str, Dict]) -> Optional[Dict]:
    """
    Get note for a symbol

    Args:
        symbol: Stock symbol
        notes: Notes dict

    Returns:
        Note dict or None if not found
    """
    return notes.get(symbol)


def format_note_for_display(symbol: str, note: Dict, current_price: float) -> str:
    """
    Format a position note for display in LLM prompt

    Args:
        symbol: Stock symbol
        note: Position note
        current_price: Current price

    Returns:
        Formatted string
    """
    entry_date = note.get('entry_date', 'Unknown')
    entry_price = note.get('entry_price', 0.0)
    thesis = note.get('investment_thesis', 'No thesis available')
    target = note.get('target_price', 0.0)
    stop = note.get('stop_loss', 0.0)
    time_horizon = note.get('time_horizon_weeks', 0)
    target_exit = note.get('target_exit_date', 'Unknown')
    catalyst = note.get('expected_catalyst', 'Unknown')

    # Calculate days held
    try:
        entry_dt = datetime.strptime(entry_date, '%Y-%m-%d')
        days_held = (datetime.now() - entry_dt).days
    except:
        days_held = 0

    # Calculate days remaining
    try:
        exit_dt = datetime.strptime(target_exit, '%Y-%m-%d')
        days_remaining = (exit_dt - datetime.now()).days
    except:
        days_remaining = 0

    # Calculate P&L
    if entry_price > 0:
        pnl_pct = ((current_price - entry_price) / entry_price) * 100
        pnl_sign = '+' if pnl_pct >= 0 else ''
    else:
        pnl_pct = 0
        pnl_sign = ''

    formatted = f"""
  Entry: ${entry_price:.2f} on {entry_date} ({days_held} days ago)
  P&L: {pnl_sign}{pnl_pct:.2f}%

  YOUR ORIGINAL INVESTMENT THESIS:
    "{thesis}"
    Target Price: ${target:.2f}
    Stop Loss: ${stop:.2f}
    Time Horizon: {time_horizon} weeks (exit by {target_exit})
    Expected Catalyst: {catalyst}
    Days Remaining: {days_remaining} days
"""

    return formatted


def get_recent_reviews(note: Dict, count: int = 3) -> List[Dict]:
    """
    Get most recent review entries

    Args:
        note: Position note
        count: Number of recent reviews to return

    Returns:
        List of recent review entries
    """
    review_history = note.get('review_history', [])
    return review_history[-count:] if review_history else []
