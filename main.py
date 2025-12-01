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
from src.utils.trade_executor import TradeExecutor, format_execution_summary
from src.scheduler.trading_scheduler import TradingScheduler
from src.utils.position_history import build_position_history
from src.utils.template_formatter import format_portfolio_template
# New 6-layer architecture imports
from src.utils.decision_context_builder import build_decision_context
from src.utils.rules_engine import apply_rules_engine
from src.utils.decision_validator import validate_decisions, format_validation_errors
from src.utils.notes_manager import load_notes, save_notes, update_position_notes, remove_sold_positions

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
        """Execute a complete trading cycle with 6-layer architecture"""
        import json

        try:
            # ===================================================================
            # LAYER 0: Fetch Data
            # ===================================================================
            logger.info("Starting 6-layer autonomous trading cycle...")

            account = self.alpaca_client.get_account()
            positions = self.alpaca_client.get_positions()
            orders = self.alpaca_client.get_orders(status='all')
            notes = load_notes()

            # ===================================================================
            # LAYER 1: Build Decision Context (Pre-calculate all options)
            # ===================================================================
            logger.info("Layer 1: Building decision context with pre-calculated options...")
            context = build_decision_context(account, positions, notes)

            # Save context to file for review
            os.makedirs('logs', exist_ok=True)
            with open('logs/latest_context.json', 'w') as f:
                json.dump(context, f, indent=2)

            # ===================================================================
            # LAYER 2: Apply Rules Engine (Automatic exits)
            # ===================================================================
            logger.info("Layer 2: Applying rules engine for automatic exits...")
            automatic_actions, flagged_positions = apply_rules_engine(positions, notes, context)

            # ===================================================================
            # LAYER 3: Get LLM Decisions (With memory injection)
            # ===================================================================
            if not self.llm_advisor:
                print("⚠️  Skipping LLM analysis - no API key configured")
                return

            logger.info("Layer 3: Getting LLM decisions with memory injection...")

            # Get decisions from LLM
            decisions = self.llm_advisor.get_trading_decisions(
                context,
                automatic_actions,
                flagged_positions,
                positions
            )

            # Save LLM decisions to file
            with open('logs/latest_llm_decisions.json', 'w') as f:
                json.dump(decisions, f, indent=2)

            # Display LLM response
            print("\n" + "=" * 80)
            print("LLM DECISIONS")
            print("=" * 80)
            print(json.dumps(decisions, indent=2))
            print("=" * 80 + "\n")

            # ===================================================================
            # LAYER 4: Validate Decisions
            # ===================================================================
            logger.info("Layer 4: Validating LLM decisions...")

            existing_symbols = [p['symbol'] for p in positions]
            validation_result = validate_decisions(decisions, context, existing_symbols)

            if not validation_result['valid']:
                error_msg = format_validation_errors(validation_result)
                print("\n" + "=" * 80)
                print("VALIDATION FAILED")
                print("=" * 80)
                print(error_msg)
                print("=" * 80 + "\n")
                raise ValueError(f"LLM decisions failed validation: {validation_result['errors']}")

            print("✓ Validation passed\n")

            # ===================================================================
            # LAYER 5: Execute with Safety Limits
            # ===================================================================
            logger.info("Layer 5: Executing trades with safety limits...")

            execution_results = self.trade_executor.execute_with_safety(
                automatic_actions,
                decisions,
                context
            )

            # Save execution results
            with open('logs/latest_execution_results.json', 'w') as f:
                json.dump(execution_results, f, indent=2)

            # Display execution summary
            summary = format_execution_summary(execution_results)
            print(summary)

            # ===================================================================
            # LAYER 6: Update Memory
            # ===================================================================
            logger.info("Layer 6: Updating position memory...")

            # Update notes with new positions and review decisions
            new_positions = decisions.get('cash_deployment', {}).get('new_positions', [])
            position_decisions = decisions.get('position_decisions', [])
            entry_prices = execution_results.get('entry_prices', {})

            notes = update_position_notes(
                notes,
                new_positions,
                position_decisions,
                entry_prices
            )

            # Remove notes for sold positions (after archiving)
            sold_symbols = execution_results.get('sold_symbols', [])
            sell_reasons = execution_results.get('sell_reasons', {})

            notes = remove_sold_positions(notes, sold_symbols, sell_reasons)

            # Save updated notes
            save_notes(notes)

            logger.info("Trading cycle completed successfully")
            print("\n✅ Trading cycle completed successfully\n")

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
