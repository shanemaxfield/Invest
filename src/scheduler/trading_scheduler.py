"""
Trading Scheduler
Schedules daily trading runs at specified time
"""

import schedule
import time
import logging
from datetime import datetime
import pytz

logger = logging.getLogger(__name__)


class TradingScheduler:
    """Schedules and runs trading operations"""

    def __init__(
        self,
        trading_function,
        hour: int = 20,
        minute: int = 0,
        timezone: str = "America/Denver"
    ):
        """
        Initialize the scheduler

        Args:
            trading_function: Function to call when scheduled time is reached
            hour: Hour to run (24-hour format, 0-23)
            minute: Minute to run (0-59)
            timezone: Timezone string (e.g., 'America/Denver' for MT)
        """
        self.trading_function = trading_function
        self.hour = hour
        self.minute = minute
        self.timezone = pytz.timezone(timezone)
        self.is_running = False

        logger.info(f"Scheduler initialized: {hour:02d}:{minute:02d} {timezone}")

    def schedule_daily_run(self):
        """Schedule the daily trading run"""
        time_str = f"{self.hour:02d}:{self.minute:02d}"

        schedule.every().day.at(time_str).do(self._run_with_timezone_check)

        logger.info(f"Daily run scheduled for {time_str} {self.timezone}")

    def _run_with_timezone_check(self):
        """Wrapper to run trading function with timezone awareness"""
        now = datetime.now(self.timezone)
        logger.info(f"Scheduled run triggered at {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")

        try:
            self.trading_function()
        except Exception as e:
            logger.error(f"Error during scheduled trading run: {e}", exc_info=True)

    def run_now(self):
        """Manually trigger a trading run immediately"""
        logger.info("Manual trading run triggered")
        try:
            self.trading_function()
        except Exception as e:
            logger.error(f"Error during manual trading run: {e}", exc_info=True)

    def start(self, run_immediately: bool = False):
        """
        Start the scheduler

        Args:
            run_immediately: If True, run the trading function immediately before starting scheduler
        """
        if self.is_running:
            logger.warning("Scheduler is already running")
            return

        self.is_running = True

        if run_immediately:
            logger.info("Running trading function immediately before starting scheduler...")
            self.run_now()

        logger.info("Starting scheduler... Press Ctrl+C to stop")

        try:
            while self.is_running:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        except KeyboardInterrupt:
            logger.info("Scheduler stopped by user")
            self.is_running = False

    def stop(self):
        """Stop the scheduler"""
        logger.info("Stopping scheduler...")
        self.is_running = False

    def get_next_run_time(self) -> str:
        """
        Get the next scheduled run time

        Returns:
            String representation of next run time
        """
        next_run = schedule.next_run()
        if next_run:
            # Convert to target timezone
            local_time = next_run.replace(tzinfo=pytz.UTC).astimezone(self.timezone)
            return local_time.strftime('%Y-%m-%d %H:%M:%S %Z')
        return "No runs scheduled"
