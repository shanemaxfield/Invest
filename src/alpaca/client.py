"""
Alpaca API Client
Handles all interactions with the Alpaca Trading API
"""

import os
import logging
from typing import Dict, List, Optional
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest

logger = logging.getLogger(__name__)


class AlpacaClient:
    """Wrapper for Alpaca Trading API"""

    def __init__(self, api_key: str, secret_key: str, paper: bool = True):
        """
        Initialize Alpaca client

        Args:
            api_key: Alpaca API key
            secret_key: Alpaca secret key
            paper: If True, use paper trading. If False, use live trading.
        """
        self.api_key = api_key
        self.secret_key = secret_key
        self.paper = paper

        # Initialize trading client
        self.trading_client = TradingClient(
            api_key=api_key,
            secret_key=secret_key,
            paper=paper
        )

        # Initialize data client (doesn't need paper parameter)
        self.data_client = StockHistoricalDataClient(
            api_key=api_key,
            secret_key=secret_key
        )

        logger.info(f"Alpaca client initialized ({'PAPER' if paper else 'LIVE'} trading)")

    def get_account(self) -> Dict:
        """
        Get account information

        Returns:
            Dict containing account details (cash, portfolio value, buying power, etc.)
        """
        try:
            account = self.trading_client.get_account()
            account_data = {
                'cash': float(account.cash),
                'portfolio_value': float(account.portfolio_value),
                'buying_power': float(account.buying_power),
                'equity': float(account.equity),
                'last_equity': float(account.last_equity),
                'currency': account.currency,
                'pattern_day_trader': account.pattern_day_trader,
                'trading_blocked': account.trading_blocked,
                'account_blocked': account.account_blocked,
            }
            logger.info(f"Retrieved account info: Portfolio value = ${account_data['portfolio_value']:.2f}")
            return account_data
        except Exception as e:
            logger.error(f"Error getting account info: {e}")
            raise

    def get_positions(self) -> List[Dict]:
        """
        Get all current positions

        Returns:
            List of dicts containing position information
        """
        try:
            positions = self.trading_client.get_all_positions()
            positions_data = []

            for position in positions:
                positions_data.append({
                    'symbol': position.symbol,
                    'qty': float(position.qty),
                    'avg_entry_price': float(position.avg_entry_price),
                    'current_price': float(position.current_price),
                    'market_value': float(position.market_value),
                    'cost_basis': float(position.cost_basis),
                    'unrealized_pl': float(position.unrealized_pl),
                    'unrealized_plpc': float(position.unrealized_plpc),
                    'side': position.side,
                })

            logger.info(f"Retrieved {len(positions_data)} positions")
            return positions_data
        except Exception as e:
            logger.error(f"Error getting positions: {e}")
            raise

    def get_latest_quote(self, symbol: str) -> Dict:
        """
        Get latest quote for a symbol

        Args:
            symbol: Stock symbol (e.g., 'AAPL')

        Returns:
            Dict with bid/ask prices
        """
        try:
            request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
            quote = self.data_client.get_stock_latest_quote(request)

            quote_data = {
                'symbol': symbol,
                'bid_price': float(quote[symbol].bid_price),
                'ask_price': float(quote[symbol].ask_price),
                'bid_size': quote[symbol].bid_size,
                'ask_size': quote[symbol].ask_size,
            }

            return quote_data
        except Exception as e:
            logger.error(f"Error getting quote for {symbol}: {e}")
            raise

    def place_market_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        time_in_force: str = "day"
    ) -> Dict:
        """
        Place a market order

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Quantity of shares
            side: 'buy' or 'sell'
            time_in_force: Order time in force ('day', 'gtc', 'ioc', 'fok')

        Returns:
            Dict with order information
        """
        try:
            # Convert side to enum
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL

            # Convert time_in_force to enum
            tif_map = {
                'day': TimeInForce.DAY,
                'gtc': TimeInForce.GTC,
                'ioc': TimeInForce.IOC,
                'fok': TimeInForce.FOK,
            }
            tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

            # Create market order request
            market_order_data = MarketOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif
            )

            # Submit order
            order = self.trading_client.submit_order(order_data=market_order_data)

            order_info = {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side.value,
                'type': order.type.value,
                'status': order.status.value,
                'submitted_at': str(order.submitted_at),
            }

            logger.info(f"Market order placed: {side.upper()} {qty} {symbol} - Order ID: {order.id}")
            return order_info

        except Exception as e:
            logger.error(f"Error placing market order for {symbol}: {e}")
            raise

    def place_limit_order(
        self,
        symbol: str,
        qty: float,
        side: str,
        limit_price: float,
        time_in_force: str = "day"
    ) -> Dict:
        """
        Place a limit order

        Args:
            symbol: Stock symbol (e.g., 'AAPL')
            qty: Quantity of shares
            side: 'buy' or 'sell'
            limit_price: Limit price for the order
            time_in_force: Order time in force ('day', 'gtc', 'ioc', 'fok')

        Returns:
            Dict with order information
        """
        try:
            # Convert side to enum
            order_side = OrderSide.BUY if side.lower() == 'buy' else OrderSide.SELL

            # Convert time_in_force to enum
            tif_map = {
                'day': TimeInForce.DAY,
                'gtc': TimeInForce.GTC,
                'ioc': TimeInForce.IOC,
                'fok': TimeInForce.FOK,
            }
            tif = tif_map.get(time_in_force.lower(), TimeInForce.DAY)

            # Create limit order request
            limit_order_data = LimitOrderRequest(
                symbol=symbol,
                qty=qty,
                side=order_side,
                time_in_force=tif,
                limit_price=limit_price
            )

            # Submit order
            order = self.trading_client.submit_order(order_data=limit_order_data)

            order_info = {
                'id': str(order.id),
                'symbol': order.symbol,
                'qty': float(order.qty),
                'side': order.side.value,
                'type': order.type.value,
                'limit_price': float(order.limit_price),
                'status': order.status.value,
                'submitted_at': str(order.submitted_at),
            }

            logger.info(f"Limit order placed: {side.upper()} {qty} {symbol} @ ${limit_price} - Order ID: {order.id}")
            return order_info

        except Exception as e:
            logger.error(f"Error placing limit order for {symbol}: {e}")
            raise

    def get_orders(self, status: str = "all") -> List[Dict]:
        """
        Get orders

        Args:
            status: Filter by status ('open', 'closed', 'all')

        Returns:
            List of order dicts
        """
        try:
            from alpaca.trading.enums import QueryOrderStatus

            status_map = {
                'open': QueryOrderStatus.OPEN,
                'closed': QueryOrderStatus.CLOSED,
                'all': QueryOrderStatus.ALL,
            }

            from alpaca.trading.requests import GetOrdersRequest
            request = GetOrdersRequest(
                status=status_map.get(status.lower(), QueryOrderStatus.ALL)
            )

            orders = self.trading_client.get_orders(filter=request)

            orders_data = []
            for order in orders:
                orders_data.append({
                    'id': str(order.id),
                    'symbol': order.symbol,
                    'qty': float(order.qty),
                    'side': order.side.value,
                    'type': order.type.value,
                    'status': order.status.value,
                    'submitted_at': str(order.submitted_at),
                })

            logger.info(f"Retrieved {len(orders_data)} orders (status: {status})")
            return orders_data

        except Exception as e:
            logger.error(f"Error getting orders: {e}")
            raise

    def cancel_all_orders(self) -> bool:
        """
        Cancel all open orders

        Returns:
            True if successful
        """
        try:
            self.trading_client.cancel_orders()
            logger.info("All open orders cancelled")
            return True
        except Exception as e:
            logger.error(f"Error cancelling orders: {e}")
            raise
