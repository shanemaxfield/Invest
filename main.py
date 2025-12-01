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

        # Setup logging - suppress console output, only log to file
        # We'll use print() for the three main sections instead
        log_level = os.getenv('LOG_LEVEL', 'INFO')
        # Set up logging to file only, not console
        import logging
        from logging.handlers import RotatingFileHandler
        os.makedirs('logs', exist_ok=True)
        file_handler = RotatingFileHandler('logs/trading.log', maxBytes=10*1024*1024, backupCount=5)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))
        root_logger.handlers.clear()
        root_logger.addHandler(file_handler)
        # Suppress external library noise
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('openai').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)

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

        # Logging suppressed for cleaner output - check logs/trading.log for details

    def run_trading_cycle(self):
        """Execute a complete trading cycle"""
        import json
        
        try:
            # Step 1: Fetch portfolio data
            account = self.alpaca_client.get_account()
            positions = self.alpaca_client.get_positions()
            orders = self.alpaca_client.get_orders(status='all')

            # Step 2: Build position history and format template
            positions_with_history = build_position_history(positions, orders)
            portfolio_template = format_portfolio_template(account, positions_with_history)

            # Save template to file for review
            os.makedirs('logs', exist_ok=True)
            with open('logs/latest_portfolio_template.txt', 'w') as f:
                f.write(portfolio_template)

            # Step 3: Get LLM decisions
            if self.llm_advisor:
                # Build full prompt for display
                system_prompt = self.llm_advisor._build_system_prompt()
                user_prompt = self.llm_advisor._build_user_prompt(portfolio_template)
                full_prompt = f"{system_prompt}\n\n{user_prompt}"
                
                # Display full prompt
                print("\n" + "=" * 80)
                print("FULL PROMPT SENT TO LLM")
                print("=" * 80)
                print(full_prompt)
                print("=" * 80 + "\n")
                
                decisions = self.llm_advisor.get_trading_decisions(portfolio_template)

                # Validate decisions
                self.llm_advisor.validate_decisions(decisions)

                # Save LLM decisions to file
                with open('logs/latest_llm_decisions.json', 'w') as f:
                    json.dump(decisions, f, indent=2)

                # Display LLM response
                print("\n" + "=" * 80)
                print("LLM RESPONSE")
                print("=" * 80)
                print(json.dumps(decisions, indent=2))
                print("=" * 80 + "\n")

                # Step 4: Execute trades
                execution_results = self.trade_executor.execute_decisions(decisions, account)


                # Save execution results
                with open('logs/latest_execution_results.json', 'w') as f:
                    json.dump(execution_results, f, indent=2)

                # Display execution summary
                print("\n" + "=" * 80)
                print("EXECUTION SUMMARY")
                print("=" * 80)
                print(f"Executed: {len(execution_results['executed'])}")
                print(f"Skipped: {len(execution_results['skipped'])}")
                print(f"Failed: {len(execution_results['failed'])}")
                
                if execution_results['executed']:
                    print("\nExecuted trades:")
                    for exec_trade in execution_results['executed']:
                        action = exec_trade['action']
                        result = exec_trade.get('result', {})
                        order_id = result.get('id', 'N/A')
                        print(f"  - {action['action_type']} {action.get('quantity', 0)} "
                              f"{action['symbol']} (Conviction: {action.get('conviction', 'N/A')})")
                        print(f"    Order ID: {order_id}")
                        if 'reasoning' in action:
                            print(f"    Reasoning: {action['reasoning']}")
                
                if execution_results['skipped']:
                    print("\nSkipped trades:")
                    for skip in execution_results['skipped']:
                        action = skip['action']
                        reason = skip.get('reason', 'Unknown')
                        print(f"  - {action.get('action_type', 'N/A')} {action.get('symbol', 'N/A')}: {reason}")
                
                if execution_results['failed']:
                    print("\nFailed trades:")
                    for fail in execution_results['failed']:
                        action = fail['action']
                        error = fail.get('error', 'Unknown error')
                        print(f"  - {action.get('action_type', 'N/A')} {action.get('symbol', 'N/A')}: {error}")
                
                print("=" * 80 + "\n")

            else:
                print("⚠️  Skipping LLM analysis - no API key configured")

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
