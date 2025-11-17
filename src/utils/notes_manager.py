"""
Notes Manager
Handles loading and saving position notes
"""

import os
import json
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

NOTES_FILE = 'logs/position_notes.json'


def load_notes() -> Dict[str, str]:
    """
    Load position notes from file
    
    Returns:
        Dict mapping symbol to note text
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


def save_notes(notes: Dict[str, str]) -> bool:
    """
    Save position notes to file
    
    Args:
        notes: Dict mapping symbol to note text
    
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


def update_notes(existing_notes: Dict[str, str], updates: Dict[str, str]) -> Dict[str, str]:
    """
    Merge note updates with existing notes
    
    Args:
        existing_notes: Current notes
        updates: New notes to add/update
    
    Returns:
        Updated notes dict
    """
    updated = existing_notes.copy()
    updated.update(updates)
    return updated


def get_note(symbol: str, notes: Dict[str, str]) -> str:
    """
    Get note for a symbol, or return default message
    
    Args:
        symbol: Stock symbol
        notes: Notes dict
    
    Returns:
        Note text or default message
    """
    return notes.get(symbol, "Insert previous notes")

