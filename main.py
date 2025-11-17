#!/usr/bin/env python3
"""
Main Trading Bot
Orchestrates the entire trading process: data fetching, LLM analysis, and trade execution
"""

import os
import sys
import logging
from dotenv import load_dotenv

from src.utils.logger import setup_logging
from src.alpaca.client import AlpacaClient
from src.alpaca.portfolio_formatter import PortfolioFormatter
from src.llm.trading_advisor import TradingAdvisor
from src.utils.trade_executor import TradeExecutor
from src.scheduler.trading_scheduler import TradingScheduler
from src.utils.position_history import build_position_history
from src.utils.template_formatter import format_portfolio_template
from src.utils.notes_manager import load_notes, save_notes, update_notes

logger = logging.getLogger(__name__)


class TradingBot:
    """Main trading bot orchestrator"""

    def __init__(self, dry_run: bool = True):
        """
        Initialize the trading bot

        Args:
            dry_run: If True, simulate trades without executing
        """
        # Load environment variables
        load_dotenv()

        # Setup logging
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        setup_logging(log_level=log_level)

        logger.info("=" * 60)
        logger.info("Trading Bot Initializing...")
        logger.info("=" * 60)

        # Initialize Alpaca client
        alpaca_api_key = os.getenv('ALPACA_API_KEY')
        alpaca_secret_key = os.getenv('ALPACA_SECRET_KEY')
        alpaca_env = os.getenv('ALPACA_ENV', 'paper')

        if not alpaca_api_key or not alpaca_secret_key:
            raise ValueError("Missing Alpaca API credentials in .env file")

        self.alpaca_client = AlpacaClient(
            api_key=alpaca_api_key,
            secret_key=alpaca_secret_key,
            paper=(alpaca_env.lower() == 'paper')
        )

        # Initialize LLM advisor
        openai_api_key = os.getenv('OPENAI_API_KEY')
        if not openai_api_key:
            logger.warning("No OpenAI API key found - LLM analysis will not work")
            self.llm_advisor = None
        else:
            llm_model = os.getenv('LLM_MODEL', 'gpt-4-turbo-preview')
            self.llm_advisor = TradingAdvisor(
                api_key=openai_api_key,
                model=llm_model
            )

        # Initialize formatter and executor
        self.formatter = PortfolioFormatter()
        self.trade_executor = TradeExecutor(
            alpaca_client=self.alpaca_client,
            dry_run=dry_run
        )

        logger.info("Trading Bot initialized successfully")
        logger.info(f"Mode: {'DRY RUN' if dry_run else 'LIVE TRADING'}")

    def run_trading_cycle(self):
        """Execute a complete trading cycle"""
        logger.info("=" * 60)
        logger.info("Starting Trading Cycle")
        logger.info("=" * 60)

        try:
            # Step 1: Fetch portfolio data
            logger.info("Step 1: Fetching portfolio data from Alpaca...")
            account = self.alpaca_client.get_account()
            positions = self.alpaca_client.get_positions()
            orders = self.alpaca_client.get_orders(status='all')

            # Step 2: Build position history and format template
            logger.info("Step 2: Building position history and formatting template...")
            positions_with_history = build_position_history(positions, orders)
            notes = load_notes()
            portfolio_template = format_portfolio_template(account, positions_with_history, notes)

            # Log portfolio summary
            logger.info(f"Portfolio Value: ${account['portfolio_value']:,.2f}")
            logger.info(f"Cash Available: ${account['cash']:,.2f}")
            logger.info(f"Positions: {len(positions)}")

            # Save template to file for review
            import json
            os.makedirs('logs', exist_ok=True)
            with open('logs/latest_portfolio_template.txt', 'w') as f:
                f.write(portfolio_template)
            logger.info("Portfolio template saved to logs/latest_portfolio_template.txt")

            # Step 3: Get LLM decisions
            if self.llm_advisor:
                logger.info("Step 3: Requesting trading decisions from LLM...")
                decisions = self.llm_advisor.get_trading_decisions(portfolio_template)

                # Validate decisions
                self.llm_advisor.validate_decisions(decisions)

                # Save LLM decisions to file
                with open('logs/latest_llm_decisions.json', 'w') as f:
                    json.dump(decisions, f, indent=2)
                logger.info("LLM decisions saved to logs/latest_llm_decisions.json")

                # Log LLM analysis
                logger.info("=" * 60)
                logger.info("LLM ANALYSIS")
                logger.info("=" * 60)
                logger.info(f"Market Outlook: {decisions.get('market_outlook', 'N/A')}")
                logger.info(f"Risk Assessment: {decisions.get('risk_assessment', 'N/A')}")
                logger.info(f"Recommended Actions: {len(decisions.get('actions', []))}")

                # Step 4: Execute trades
                logger.info("Step 4: Executing trading decisions...")
                execution_results = self.trade_executor.execute_decisions(decisions, account)

                # Step 5: Update notes for positions that changed
                logger.info("Step 5: Updating position notes...")
                executed_actions = execution_results.get('executed', [])
                notes_updates = self.llm_advisor.extract_notes_updates(decisions, executed_actions)
                if notes_updates:
                    updated_notes = update_notes(notes, notes_updates)
                    save_notes(updated_notes)
                    logger.info(f"Updated notes for {len(notes_updates)} positions")
                else:
                    logger.info("No notes updates needed (no positions changed)")

                # Save execution results
                with open('logs/latest_execution_results.json', 'w') as f:
                    json.dump(execution_results, f, indent=2)

                # Log execution summary
                logger.info("=" * 60)
                logger.info("EXECUTION SUMMARY")
                logger.info("=" * 60)
                logger.info(f"Executed: {len(execution_results['executed'])}")
                logger.info(f"Skipped: {len(execution_results['skipped'])}")
                logger.info(f"Failed: {len(execution_results['failed'])}")

                if execution_results['executed']:
                    logger.info("Executed trades:")
                    for exec_trade in execution_results['executed']:
                        action = exec_trade['action']
                        logger.info(f"  - {action['action_type']} {action.get('quantity', 0)} "
                                  f"{action['symbol']} (Conviction: {action.get('conviction', 'N/A')})")

            else:
                logger.warning("Skipping LLM analysis - no API key configured")

            logger.info("=" * 60)
            logger.info("Trading Cycle Complete")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error during trading cycle: {e}", exc_info=True)
            raise

    def start_scheduler(self, run_immediately: bool = False):
        """
        Start the scheduled trading runs

        Args:
            run_immediately: If True, run a trading cycle immediately before starting scheduler
        """
        hour = int(os.getenv('SCHEDULED_HOUR', '20'))
        minute = int(os.getenv('SCHEDULED_MINUTE', '0'))
        timezone = os.getenv('TIMEZONE', 'America/Denver')

        scheduler = TradingScheduler(
            trading_function=self.run_trading_cycle,
            hour=hour,
            minute=minute,
            timezone=timezone
        )

        scheduler.schedule_daily_run()
        logger.info(f"Next scheduled run: {scheduler.get_next_run_time()}")

        scheduler.start(run_immediately=run_immediately)


def main():
    """Main entry point"""
    import argparse

    parser = argparse.ArgumentParser(description='AI-Powered Trading Bot')
    parser.add_argument(
        '--mode',
        choices=['once', 'schedule'],
        default='once',
        help='Run once or start scheduler (default: once)'
    )
    parser.add_argument(
        '--live',
        action='store_true',
        help='Execute real trades (default: dry run)'
    )
    parser.add_argument(
        '--run-immediately',
        action='store_true',
        help='When using schedule mode, run immediately before starting scheduler'
    )

    args = parser.parse_args()

    # Initialize bot
    dry_run = not args.live
    bot = TradingBot(dry_run=dry_run)

    if args.mode == 'once':
        # Run once and exit
        bot.run_trading_cycle()
    else:
        # Start scheduler
        bot.start_scheduler(run_immediately=args.run_immediately)


if __name__ == '__main__':
    main()
