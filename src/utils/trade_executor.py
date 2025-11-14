"""
Trade Executor
Executes trades based on LLM decisions with safety checks
"""

import logging
from typing import Dict, List
from src.alpaca.client import AlpacaClient

logger = logging.getLogger(__name__)


class TradeExecutor:
    """Executes trades with safety checks and validation"""

    def __init__(
        self,
        alpaca_client: AlpacaClient,
        dry_run: bool = True,
        max_position_pct: float = 20.0,
        max_trade_value: float = 10000.0
    ):
        """
        Initialize trade executor

        Args:
            alpaca_client: Initialized Alpaca client
            dry_run: If True, simulate trades without executing
            max_position_pct: Maximum percentage of portfolio for a single position
            max_trade_value: Maximum dollar value for a single trade
        """
        self.alpaca_client = alpaca_client
        self.dry_run = dry_run
        self.max_position_pct = max_position_pct
        self.max_trade_value = max_trade_value

        logger.info(f"Trade executor initialized (DRY RUN: {dry_run})")

    def execute_decisions(self, decisions: Dict, account: Dict) -> Dict:
        """
        Execute trading decisions from LLM

        Args:
            decisions: Trading decisions from LLM
            account: Account information for safety checks

        Returns:
            Dict with execution results
        """
        actions = decisions.get('actions', [])
        results = {
            'executed': [],
            'skipped': [],
            'failed': [],
            'dry_run': self.dry_run
        }

        if not actions:
            logger.info("No actions to execute")
            return results

        logger.info(f"Processing {len(actions)} actions...")

        for action in actions:
            try:
                # Skip HOLD actions
                if action['action_type'] == 'HOLD':
                    logger.info(f"HOLD action for {action['symbol']} - skipping")
                    results['skipped'].append({
                        'action': action,
                        'reason': 'HOLD action'
                    })
                    continue

                # Validate and execute the action
                validation_result = self._validate_action(action, account)

                if not validation_result['valid']:
                    logger.warning(f"Action validation failed: {validation_result['reason']}")
                    results['skipped'].append({
                        'action': action,
                        'reason': validation_result['reason']
                    })
                    continue

                # Execute the trade
                execution_result = self._execute_action(action)
                results['executed'].append({
                    'action': action,
                    'result': execution_result
                })

            except Exception as e:
                logger.error(f"Error executing action {action}: {e}")
                results['failed'].append({
                    'action': action,
                    'error': str(e)
                })

        # Log summary
        logger.info(f"Execution complete: {len(results['executed'])} executed, "
                   f"{len(results['skipped'])} skipped, {len(results['failed'])} failed")

        return results

    def _validate_action(self, action: Dict, account: Dict) -> Dict:
        """
        Validate a trading action against safety rules

        Args:
            action: The action to validate
            account: Account information

        Returns:
            Dict with 'valid' boolean and 'reason' string
        """
        action_type = action['action_type']
        symbol = action['symbol']
        quantity = action.get('quantity', 0)

        # Basic validation
        if action_type not in ['BUY', 'SELL']:
            return {'valid': False, 'reason': f"Invalid action type: {action_type}"}

        if quantity <= 0:
            return {'valid': False, 'reason': f"Invalid quantity: {quantity}"}

        # For BUY orders, check buying power and position limits
        if action_type == 'BUY':
            # Estimate trade value (use limit price if available, otherwise we can't validate precisely)
            if action.get('order_type') == 'LIMIT' and 'limit_price' in action:
                estimated_value = quantity * action['limit_price']
            else:
                # For market orders, we'd need current price - skip value check
                logger.warning(f"Cannot validate trade value for market order on {symbol} without current price")
                estimated_value = 0

            if estimated_value > 0:
                # Check max trade value
                if estimated_value > self.max_trade_value:
                    return {
                        'valid': False,
                        'reason': f"Trade value ${estimated_value:.2f} exceeds max ${self.max_trade_value:.2f}"
                    }

                # Check max position percentage
                max_position_value = account['portfolio_value'] * (self.max_position_pct / 100)
                if estimated_value > max_position_value:
                    return {
                        'valid': False,
                        'reason': f"Trade would exceed max position size ({self.max_position_pct}% of portfolio)"
                    }

                # Check buying power
                if estimated_value > account['buying_power']:
                    return {
                        'valid': False,
                        'reason': f"Insufficient buying power: ${account['buying_power']:.2f} available"
                    }

        # For SELL orders, verify we have the position
        if action_type == 'SELL':
            try:
                positions = self.alpaca_client.get_positions()
                position = next((p for p in positions if p['symbol'] == symbol), None)

                if not position:
                    return {'valid': False, 'reason': f"No position found for {symbol}"}

                if quantity > position['qty']:
                    return {
                        'valid': False,
                        'reason': f"Insufficient shares: trying to sell {quantity}, have {position['qty']}"
                    }
            except Exception as e:
                logger.error(f"Error checking position for {symbol}: {e}")
                return {'valid': False, 'reason': f"Error verifying position: {e}"}

        return {'valid': True, 'reason': 'Validation passed'}

    def _execute_action(self, action: Dict) -> Dict:
        """
        Execute a single trading action

        Args:
            action: The action to execute

        Returns:
            Dict with execution result
        """
        action_type = action['action_type']
        symbol = action['symbol']
        quantity = action['quantity']
        order_type = action.get('order_type', 'MARKET')

        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {action_type} {quantity} {symbol} ({order_type})")
            return {
                'status': 'dry_run',
                'action': action_type,
                'symbol': symbol,
                'quantity': quantity,
                'order_type': order_type
            }

        # Real execution
        try:
            if order_type == 'LIMIT':
                limit_price = action.get('limit_price')
                if not limit_price:
                    raise ValueError(f"Limit order for {symbol} missing limit_price")

                side = 'buy' if action_type == 'BUY' else 'sell'
                result = self.alpaca_client.place_limit_order(
                    symbol=symbol,
                    qty=quantity,
                    side=side,
                    limit_price=limit_price,
                    time_in_force='day'
                )

                logger.info(f"LIMIT order executed: {action_type} {quantity} {symbol} @ ${limit_price}")
                return result

            else:  # MARKET order
                side = 'buy' if action_type == 'BUY' else 'sell'
                result = self.alpaca_client.place_market_order(
                    symbol=symbol,
                    qty=quantity,
                    side=side,
                    time_in_force='day'
                )

                logger.info(f"MARKET order executed: {action_type} {quantity} {symbol}")
                return result

        except Exception as e:
            logger.error(f"Error executing {action_type} order for {symbol}: {e}")
            raise
