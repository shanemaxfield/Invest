"""
Trade Executor - Layer 5 (Rewritten)
Executes trades based on new decision format with safety limits
"""

import logging
from typing import Dict, List, Tuple
from src.alpaca.client import AlpacaClient

logger = logging.getLogger(__name__)

# Safety limits
MAX_POSITION_SIZE = 0.25  # 25% of portfolio max per position
MAX_SINGLE_TRADE = 10000  # $10k max per trade
MIN_CASH_RESERVE = 100    # Always keep $100 cash minimum


class TradeExecutor:
    """Executes trades with new decision format and safety checks"""

    def __init__(
        self,
        alpaca_client: AlpacaClient,
        dry_run: bool = True
    ):
        """
        Initialize trade executor

        Args:
            alpaca_client: Initialized Alpaca client
            dry_run: If True, simulate trades without executing
        """
        self.alpaca_client = alpaca_client
        self.dry_run = dry_run

        logger.info(f"Trade executor initialized (DRY RUN: {dry_run})")

    def execute_with_safety(
        self,
        automatic_actions: List[Dict],
        decisions: Dict,
        context: Dict
    ) -> Dict:
        """
        Execute automatic actions + LLM decisions with safety limits

        Args:
            automatic_actions: Automatic actions from rules engine
            decisions: LLM decisions (validated)
            context: Decision context with pre-calculated options

        Returns:
            Execution results dict
        """
        results = {
            'automatic_exits': [],
            'position_management': [],
            'new_positions': [],
            'failed': [],
            'dry_run': self.dry_run,
            'entry_prices': {},  # Track entry prices for new positions
            'sold_symbols': [],  # Track sold symbols for note archiving
            'sell_reasons': {}   # Track sell reasons
        }

        account = context['account']
        position_options = context['position_options']
        buy_options = context['buy_options']

        # Step 1: Execute automatic exits first
        logger.info(f"Executing {len(automatic_actions)} automatic exits...")
        for auto_action in automatic_actions:
            result = self._execute_automatic_exit(auto_action)
            results['automatic_exits'].append(result)
            if result['status'] == 'executed' or result['status'] == 'dry_run':
                results['sold_symbols'].append(auto_action['symbol'])
                results['sell_reasons'][auto_action['symbol']] = auto_action.get('trigger', 'AUTOMATIC_EXIT')

        # Step 2: Execute position management (trims, sells from LLM)
        position_decisions = decisions.get('position_decisions', [])
        logger.info(f"Executing {len(position_decisions)} position management decisions...")
        for decision in position_decisions:
            symbol = decision['symbol']
            action = decision['action']

            if action == 'HOLD':
                logger.info(f"{symbol}: HOLD - no action needed")
                continue

            # Get pre-calculated options
            options = position_options.get(symbol, {})
            option_data = options.get(action, {})

            if not option_data:
                logger.error(f"{symbol}: No option data for action {action}")
                results['failed'].append({
                    'symbol': symbol,
                    'action': action,
                    'error': f'No option data for action {action}'
                })
                continue

            qty = option_data['qty']

            result = self._execute_sell(symbol, qty, action, decision.get('reasoning', ''))
            results['position_management'].append(result)

            if result['status'] in ['executed', 'dry_run']:
                # Track partial or full sales
                if action == 'SELL_ALL':
                    results['sold_symbols'].append(symbol)
                    results['sell_reasons'][symbol] = 'LLM_DECISION'

        # Step 3: Execute new position buys
        cash_deployment = decisions.get('cash_deployment', {})
        deployment_option = cash_deployment.get('deployment_option')
        new_positions = cash_deployment.get('new_positions', [])

        if new_positions:
            deployment_amount = buy_options[deployment_option]['amount']
            logger.info(f"Deploying ${deployment_amount:,.2f} across {len(new_positions)} new positions...")

            for new_pos in new_positions:
                symbol = new_pos['symbol']
                allocation_pct = new_pos['allocation_percent']
                amount = deployment_amount * (allocation_pct / 100.0)

                # Apply safety limit
                max_position_value = account['portfolio_value'] * MAX_POSITION_SIZE
                if amount > max_position_value:
                    logger.warning(f"{symbol}: Amount ${amount:,.2f} exceeds max position size ${max_position_value:,.2f}, capping")
                    amount = max_position_value

                if amount > MAX_SINGLE_TRADE:
                    logger.warning(f"{symbol}: Amount ${amount:,.2f} exceeds max single trade ${MAX_SINGLE_TRADE:,.2f}, capping")
                    amount = MAX_SINGLE_TRADE

                result = self._execute_buy(symbol, amount, new_pos)
                results['new_positions'].append(result)

                # Track entry price for notes
                if result['status'] in ['executed', 'dry_run']:
                    results['entry_prices'][symbol] = result.get('entry_price', 0.0)

        return results

    def _execute_automatic_exit(self, auto_action: Dict) -> Dict:
        """Execute an automatic exit (stop loss or target reached)"""
        symbol = auto_action['symbol']
        qty = auto_action['qty']
        reason = auto_action['reason']

        logger.warning(f"AUTOMATIC EXIT: {symbol} - {reason}")

        if self.dry_run:
            return {
                'status': 'dry_run',
                'symbol': symbol,
                'action': 'SELL_ALL',
                'qty': qty,
                'reason': reason,
                'message': f'[DRY RUN] Would sell {qty} shares of {symbol}: {reason}'
            }

        try:
            # Execute market sell
            order = self.alpaca_client.place_market_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                time_in_force='day'
            )

            logger.info(f"Automatic exit executed: {symbol} - Order ID: {order['id']}")

            return {
                'status': 'executed',
                'symbol': symbol,
                'action': 'SELL_ALL',
                'qty': qty,
                'reason': reason,
                'order': order
            }

        except Exception as e:
            logger.error(f"Failed to execute automatic exit for {symbol}: {e}")
            return {
                'status': 'failed',
                'symbol': symbol,
                'action': 'SELL_ALL',
                'qty': qty,
                'reason': reason,
                'error': str(e)
            }

    def _execute_sell(self, symbol: str, qty: int, action: str, reasoning: str) -> Dict:
        """Execute a sell order (trim or sell all)"""
        if qty <= 0:
            return {
                'status': 'skipped',
                'symbol': symbol,
                'action': action,
                'qty': 0,
                'reason': 'Zero quantity'
            }

        logger.info(f"{symbol}: {action} - Selling {qty} shares - {reasoning}")

        if self.dry_run:
            return {
                'status': 'dry_run',
                'symbol': symbol,
                'action': action,
                'qty': qty,
                'reasoning': reasoning,
                'message': f'[DRY RUN] Would sell {qty} shares of {symbol}'
            }

        try:
            # Execute market sell
            order = self.alpaca_client.place_market_order(
                symbol=symbol,
                qty=qty,
                side='sell',
                time_in_force='day'
            )

            logger.info(f"Sell executed: {symbol} {qty} shares - Order ID: {order['id']}")

            return {
                'status': 'executed',
                'symbol': symbol,
                'action': action,
                'qty': qty,
                'reasoning': reasoning,
                'order': order
            }

        except Exception as e:
            logger.error(f"Failed to execute sell for {symbol}: {e}")
            return {
                'status': 'failed',
                'symbol': symbol,
                'action': action,
                'qty': qty,
                'reasoning': reasoning,
                'error': str(e)
            }

    def _execute_buy(self, symbol: str, amount: float, thesis_data: Dict) -> Dict:
        """Execute a buy order for a new position"""
        logger.info(f"{symbol}: Buying ${amount:,.2f} worth - {thesis_data.get('investment_thesis', '')[:50]}...")

        if self.dry_run:
            # For dry run, estimate shares (would need current price in real scenario)
            return {
                'status': 'dry_run',
                'symbol': symbol,
                'amount': amount,
                'thesis_data': thesis_data,
                'entry_price': 0.0,  # Would need to fetch current price
                'message': f'[DRY RUN] Would buy ${amount:,.2f} of {symbol}'
            }

        try:
            # Get current price
            quote = self.alpaca_client.get_latest_quote(symbol)
            current_price = quote['ask_price']

            # Calculate shares
            qty = int(amount / current_price)

            if qty <= 0:
                return {
                    'status': 'skipped',
                    'symbol': symbol,
                    'amount': amount,
                    'reason': f'Amount too small to buy even 1 share @ ${current_price:.2f}'
                }

            # Execute market buy
            order = self.alpaca_client.place_market_order(
                symbol=symbol,
                qty=qty,
                side='buy',
                time_in_force='day'
            )

            logger.info(f"Buy executed: {symbol} {qty} shares @ ~${current_price:.2f} - Order ID: {order['id']}")

            return {
                'status': 'executed',
                'symbol': symbol,
                'qty': qty,
                'amount': amount,
                'entry_price': current_price,
                'thesis_data': thesis_data,
                'order': order
            }

        except Exception as e:
            logger.error(f"Failed to execute buy for {symbol}: {e}")
            return {
                'status': 'failed',
                'symbol': symbol,
                'amount': amount,
                'thesis_data': thesis_data,
                'error': str(e)
            }


def format_execution_summary(results: Dict) -> str:
    """
    Format execution results for display

    Args:
        results: Execution results dict

    Returns:
        Formatted summary string
    """
    summary = "\n" + "=" * 80 + "\n"
    summary += "EXECUTION SUMMARY\n"
    summary += "=" * 80 + "\n"

    if results['dry_run']:
        summary += "🔵 DRY RUN MODE - No real trades executed\n\n"

    # Automatic exits
    auto_exits = results.get('automatic_exits', [])
    if auto_exits:
        summary += f"🔴 AUTOMATIC EXITS ({len(auto_exits)}):\n"
        for exit_result in auto_exits:
            status = exit_result['status']
            symbol = exit_result['symbol']
            reason = exit_result['reason']
            summary += f"  {'✓' if status != 'failed' else '✗'} {symbol}: {reason}\n"
        summary += "\n"

    # Position management
    pos_mgmt = results.get('position_management', [])
    if pos_mgmt:
        summary += f"📊 POSITION MANAGEMENT ({len(pos_mgmt)}):\n"
        for mgmt_result in pos_mgmt:
            status = mgmt_result['status']
            if status == 'skipped':
                continue
            symbol = mgmt_result['symbol']
            action = mgmt_result['action']
            qty = mgmt_result.get('qty', 0)
            reasoning = mgmt_result.get('reasoning', '')[:60]
            summary += f"  {'✓' if status != 'failed' else '✗'} {symbol} {action}: {qty} shares\n"
            summary += f"     Reasoning: {reasoning}\n"
        summary += "\n"

    # New positions
    new_positions = results.get('new_positions', [])
    if new_positions:
        summary += f"🟢 NEW POSITIONS ({len(new_positions)}):\n"
        for new_result in new_positions:
            status = new_result['status']
            if status == 'skipped':
                continue
            symbol = new_result['symbol']
            amount = new_result.get('amount', 0)
            qty = new_result.get('qty', 0)
            thesis = new_result.get('thesis_data', {}).get('investment_thesis', '')[:60]
            summary += f"  {'✓' if status != 'failed' else '✗'} {symbol}: ${amount:,.2f} ({qty} shares)\n"
            summary += f"     Thesis: {thesis}\n"
        summary += "\n"

    # Failed
    failed = results.get('failed', [])
    if failed:
        summary += f"❌ FAILED ({len(failed)}):\n"
        for fail in failed:
            symbol = fail.get('symbol', 'Unknown')
            error = fail.get('error', 'Unknown error')
            summary += f"  ✗ {symbol}: {error}\n"
        summary += "\n"

    summary += "=" * 80 + "\n"

    return summary
