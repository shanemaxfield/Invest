"""
Decision Validator - Layer 4
Validates LLM responses for correctness and safety
"""

import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

VALID_POSITION_ACTIONS = ['HOLD', 'TRIM_25', 'TRIM_50', 'SELL_ALL']
VALID_DEPLOYMENT_OPTIONS = ['DEPLOY_25_PERCENT', 'DEPLOY_50_PERCENT', 'DEPLOY_80_PERCENT', 'DEPLOY_ALL_CASH', 'HOLD_CASH']


def validate_decisions(
    decisions: Dict,
    context: Dict,
    existing_positions: List[str]
) -> Dict:
    """
    Validate LLM decisions for correctness

    Args:
        decisions: LLM decision response
        context: Decision context with pre-calculated options
        existing_positions: List of existing position symbols

    Returns:
        Dict with 'valid' boolean and 'errors' list
    """
    errors = []

    # Check required top-level keys
    if 'position_decisions' not in decisions:
        errors.append("Missing required key: 'position_decisions'")
    if 'cash_deployment' not in decisions:
        errors.append("Missing required key: 'cash_deployment'")

    if errors:
        return {'valid': False, 'errors': errors}

    # Validate position decisions
    position_errors = _validate_position_decisions(
        decisions.get('position_decisions', []),
        context,
        existing_positions
    )
    errors.extend(position_errors)

    # Validate cash deployment
    deployment_errors = _validate_cash_deployment(
        decisions.get('cash_deployment', {}),
        context
    )
    errors.extend(deployment_errors)

    # Check minimum cash deployment (80% rule)
    deployment_option = decisions.get('cash_deployment', {}).get('deployment_option')
    if deployment_option == 'HOLD_CASH':
        errors.append("HOLD_CASH is not allowed - must deploy at least 80% of available cash")
    elif deployment_option in ['DEPLOY_25_PERCENT', 'DEPLOY_50_PERCENT']:
        errors.append(f"{deployment_option} is below 80% minimum - must use DEPLOY_80_PERCENT or DEPLOY_ALL_CASH")

    if errors:
        return {'valid': False, 'errors': errors}

    return {'valid': True, 'errors': []}


def _validate_position_decisions(
    position_decisions: List[Dict],
    context: Dict,
    existing_positions: List[str]
) -> List[str]:
    """Validate position decisions"""
    errors = []

    if not isinstance(position_decisions, list):
        errors.append("'position_decisions' must be a list")
        return errors

    for i, decision in enumerate(position_decisions):
        # Check required fields
        if 'symbol' not in decision:
            errors.append(f"Position decision {i}: Missing 'symbol'")
            continue
        if 'action' not in decision:
            errors.append(f"Position decision {i}: Missing 'action'")
            continue

        symbol = decision['symbol']
        action = decision['action']

        # Validate symbol exists in portfolio
        if symbol not in existing_positions:
            errors.append(f"Position decision {i}: Symbol '{symbol}' not in current positions")

        # Validate action is from allowed set
        if action not in VALID_POSITION_ACTIONS:
            errors.append(f"Position decision {i} ({symbol}): Invalid action '{action}'. Must be one of {VALID_POSITION_ACTIONS}")

        # Check reasoning is provided
        if 'reasoning' not in decision or not decision['reasoning']:
            errors.append(f"Position decision {i} ({symbol}): Missing 'reasoning'")

    return errors


def _validate_cash_deployment(
    cash_deployment: Dict,
    context: Dict
) -> List[str]:
    """Validate cash deployment section"""
    errors = []

    if not isinstance(cash_deployment, dict):
        errors.append("'cash_deployment' must be a dict")
        return errors

    # Check deployment_option
    if 'deployment_option' not in cash_deployment:
        errors.append("cash_deployment: Missing 'deployment_option'")
        return errors

    deployment_option = cash_deployment['deployment_option']
    if deployment_option not in VALID_DEPLOYMENT_OPTIONS:
        errors.append(f"cash_deployment: Invalid deployment_option '{deployment_option}'. Must be one of {VALID_DEPLOYMENT_OPTIONS}")
        return errors

    # Check new_positions
    new_positions = cash_deployment.get('new_positions', [])

    # If HOLD_CASH, should have no new positions
    if deployment_option == 'HOLD_CASH':
        if new_positions:
            errors.append("cash_deployment: HOLD_CASH selected but new_positions provided")
        return errors

    # If deploying cash, must have new positions
    if deployment_option != 'HOLD_CASH' and not new_positions:
        errors.append(f"cash_deployment: {deployment_option} selected but no new_positions provided")
        return errors

    # Validate each new position
    total_allocation = 0
    for i, position in enumerate(new_positions):
        position_errors = _validate_new_position(i, position)
        errors.extend(position_errors)

        # Sum allocations
        total_allocation += position.get('allocation_percent', 0)

    # Check allocations sum to 100% (±1% tolerance)
    if new_positions and abs(total_allocation - 100) > 1:
        errors.append(f"cash_deployment: Allocation percentages sum to {total_allocation}%, must sum to 100%")

    return errors


def _validate_new_position(index: int, position: Dict) -> List[str]:
    """Validate a single new position"""
    errors = []

    required_fields = [
        'symbol',
        'allocation_percent',
        'investment_thesis',
        'target_price',
        'stop_loss',
        'time_horizon_weeks',
        'target_exit_date',
        'expected_catalyst'
    ]

    # Check all required fields present
    for field in required_fields:
        if field not in position:
            errors.append(f"New position {index}: Missing required field '{field}'")

    # If missing fields, return early
    if errors:
        return errors

    symbol = position['symbol']

    # Validate allocation_percent
    allocation = position.get('allocation_percent', 0)
    if not isinstance(allocation, (int, float)) or allocation <= 0 or allocation > 100:
        errors.append(f"New position {index} ({symbol}): allocation_percent must be between 0 and 100")

    # Validate target_price > stop_loss
    target_price = position.get('target_price')
    stop_loss = position.get('stop_loss')
    if target_price and stop_loss:
        if target_price <= stop_loss:
            errors.append(f"New position {index} ({symbol}): target_price (${target_price}) must be > stop_loss (${stop_loss})")

    # Validate time_horizon_weeks
    time_horizon = position.get('time_horizon_weeks')
    if not isinstance(time_horizon, (int, float)) or time_horizon < 2 or time_horizon > 8:
        errors.append(f"New position {index} ({symbol}): time_horizon_weeks must be between 2 and 8")

    # Validate target_exit_date format
    target_exit_date = position.get('target_exit_date')
    if target_exit_date:
        try:
            datetime.strptime(target_exit_date, '%Y-%m-%d')
        except (ValueError, TypeError):
            errors.append(f"New position {index} ({symbol}): target_exit_date must be in YYYY-MM-DD format")

    # Validate investment_thesis has content
    thesis = position.get('investment_thesis', '').strip()
    if len(thesis) < 10:
        errors.append(f"New position {index} ({symbol}): investment_thesis must be at least 10 characters")

    # Validate expected_catalyst has content
    catalyst = position.get('expected_catalyst', '').strip()
    if len(catalyst) < 5:
        errors.append(f"New position {index} ({symbol}): expected_catalyst must be at least 5 characters")

    return errors


def validate_symbol(symbol: str) -> bool:
    """
    Basic symbol validation (format check)

    Args:
        symbol: Stock ticker symbol

    Returns:
        True if valid format
    """
    # Basic checks: uppercase letters, 1-5 characters
    if not symbol:
        return False
    if not symbol.isalpha():
        return False
    if len(symbol) < 1 or len(symbol) > 5:
        return False

    return True


def format_validation_errors(validation_result: Dict) -> str:
    """
    Format validation errors for display

    Args:
        validation_result: Result from validate_decisions

    Returns:
        Formatted error string
    """
    if validation_result.get('valid'):
        return "✓ All validations passed"

    errors = validation_result.get('errors', [])
    error_text = f"❌ Validation failed with {len(errors)} error(s):\n"
    for i, error in enumerate(errors, 1):
        error_text += f"  {i}. {error}\n"

    return error_text
