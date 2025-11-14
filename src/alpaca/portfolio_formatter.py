"""
Portfolio Data Formatter
Formats portfolio data into a strict format for LLM consumption
"""

import json
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class PortfolioFormatter:
    """Formats portfolio data into a structured format for LLM analysis"""

    @staticmethod
    def format_for_llm(account: Dict, positions: List[Dict]) -> Dict:
        """
        Format account and positions data into a strict JSON structure for LLM

        Args:
            account: Account information from Alpaca
            positions: List of positions from Alpaca

        Returns:
            Formatted dict ready for LLM consumption
        """
        # Calculate position percentages
        total_portfolio_value = account['portfolio_value']

        formatted_positions = []
        for pos in positions:
            position_percentage = (pos['market_value'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0

            formatted_positions.append({
                'symbol': pos['symbol'],
                'quantity': pos['qty'],
                'average_entry_price': round(pos['avg_entry_price'], 2),
                'current_price': round(pos['current_price'], 2),
                'market_value': round(pos['market_value'], 2),
                'cost_basis': round(pos['cost_basis'], 2),
                'unrealized_profit_loss': round(pos['unrealized_pl'], 2),
                'unrealized_profit_loss_percent': round(pos['unrealized_plpc'] * 100, 2),
                'portfolio_allocation_percent': round(position_percentage, 2),
                'position_side': pos['side']
            })

        # Calculate cash percentage
        cash_percentage = (account['cash'] / total_portfolio_value * 100) if total_portfolio_value > 0 else 0

        formatted_data = {
            'timestamp': datetime.now().isoformat(),
            'account_summary': {
                'total_portfolio_value': round(total_portfolio_value, 2),
                'cash_available': round(account['cash'], 2),
                'cash_percentage': round(cash_percentage, 2),
                'buying_power': round(account['buying_power'], 2),
                'equity': round(account['equity'], 2),
                'day_change': round(account['equity'] - account['last_equity'], 2),
                'day_change_percent': round(
                    ((account['equity'] - account['last_equity']) / account['last_equity'] * 100)
                    if account['last_equity'] > 0 else 0,
                    2
                ),
                'currency': account['currency'],
                'pattern_day_trader': account['pattern_day_trader'],
                'trading_restrictions': {
                    'trading_blocked': account['trading_blocked'],
                    'account_blocked': account['account_blocked']
                }
            },
            'positions': sorted(
                formatted_positions,
                key=lambda x: x['market_value'],
                reverse=True  # Sort by market value descending
            ),
            'summary_statistics': {
                'total_positions': len(formatted_positions),
                'total_invested': round(sum(p['cost_basis'] for p in positions), 2),
                'total_market_value': round(sum(p['market_value'] for p in positions), 2),
                'total_unrealized_pl': round(sum(p['unrealized_pl'] for p in positions), 2),
                'invested_percentage': round(
                    (sum(p['market_value'] for p in positions) / total_portfolio_value * 100)
                    if total_portfolio_value > 0 else 0,
                    2
                )
            }
        }

        logger.info(f"Formatted portfolio data: {len(formatted_positions)} positions, "
                   f"${total_portfolio_value:.2f} total value")

        return formatted_data

    @staticmethod
    def to_json_string(formatted_data: Dict, pretty: bool = True) -> str:
        """
        Convert formatted data to JSON string

        Args:
            formatted_data: The formatted portfolio data
            pretty: If True, return pretty-printed JSON

        Returns:
            JSON string
        """
        if pretty:
            return json.dumps(formatted_data, indent=2)
        return json.dumps(formatted_data)

    @staticmethod
    def create_llm_prompt_context(formatted_data: Dict) -> str:
        """
        Create a human-readable context string for the LLM prompt

        Args:
            formatted_data: The formatted portfolio data

        Returns:
            Formatted string for LLM context
        """
        account = formatted_data['account_summary']
        positions = formatted_data['positions']
        stats = formatted_data['summary_statistics']

        context = f"""PORTFOLIO ANALYSIS DATA
Generated at: {formatted_data['timestamp']}

=== ACCOUNT SUMMARY ===
Total Portfolio Value: ${account['total_portfolio_value']:,.2f}
Cash Available: ${account['cash_available']:,.2f} ({account['cash_percentage']:.1f}%)
Buying Power: ${account['buying_power']:,.2f}
Day Change: ${account['day_change']:,.2f} ({account['day_change_percent']:+.2f}%)

=== CURRENT POSITIONS ({stats['total_positions']} total) ===
"""

        if positions:
            for i, pos in enumerate(positions, 1):
                context += f"""
Position {i}: {pos['symbol']}
  Quantity: {pos['quantity']}
  Current Price: ${pos['current_price']:.2f}
  Market Value: ${pos['market_value']:,.2f} ({pos['portfolio_allocation_percent']:.1f}% of portfolio)
  Entry Price: ${pos['average_entry_price']:.2f}
  Cost Basis: ${pos['cost_basis']:,.2f}
  P/L: ${pos['unrealized_profit_loss']:,.2f} ({pos['unrealized_profit_loss_percent']:+.2f}%)
"""
        else:
            context += "\n  No positions currently held.\n"

        context += f"""
=== PORTFOLIO STATISTICS ===
Total Positions: {stats['total_positions']}
Total Invested: ${stats['total_invested']:,.2f}
Total Market Value: ${stats['total_market_value']:,.2f}
Total Unrealized P/L: ${stats['total_unrealized_pl']:,.2f}
Invested Percentage: {stats['invested_percentage']:.1f}%
Cash Percentage: {account['cash_percentage']:.1f}%
"""

        return context
