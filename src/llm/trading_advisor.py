"""
LLM Trading Advisor - Layer 3 (Rewritten)
Integrates with OpenAI with enhanced memory injection and constrained choices
"""

import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI
from src.utils.rules_engine import get_status_summary, calculate_days_held, calculate_days_remaining
from datetime import datetime

logger = logging.getLogger(__name__)


class TradingAdvisor:
    """LLM-based trading advisor with memory injection and pre-calculated options"""

    def __init__(self, api_key: str, model: str = "gpt-4-turbo-preview"):
        """
        Initialize the trading advisor

        Args:
            api_key: OpenAI API key
            model: Model to use (default: gpt-4-turbo-preview)
        """
        self.client = OpenAI(api_key=api_key)
        self.model = model
        logger.info(f"Trading advisor initialized with model: {model}")

    def get_trading_decisions(
        self,
        context: Dict,
        automatic_actions: List[Dict],
        flagged_positions: List[str],
        positions: List[Dict]
    ) -> Dict:
        """
        Analyze portfolio and get trading decisions from LLM

        Args:
            context: Pre-calculated decision context
            automatic_actions: Automatic actions from rules engine
            flagged_positions: Positions flagged for review
            positions: Current positions data

        Returns:
            Dict containing trading decisions
        """
        try:
            # Build the system prompt
            system_prompt = self._build_system_prompt()

            # Build the user prompt with memory injection
            user_prompt = self._build_user_prompt(
                context,
                automatic_actions,
                flagged_positions,
                positions
            )

            # Call the LLM
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}  # Force JSON response
            )

            # Parse the response
            decision_text = response.choices[0].message.content
            decisions = json.loads(decision_text)

            logger.info("Successfully received LLM trading decisions")

            return decisions

        except Exception as e:
            logger.error(f"Error getting trading decisions from LLM: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM"""
        return """You are an elite equity research analyst at a top-tier investment fund specializing in ultra-aggressive swing trading.

CRITICAL RULES - READ CAREFULLY:

1. MATH IS HANDLED FOR YOU - DO NOT CALCULATE ANYTHING
   - All buy options are pre-calculated with exact dollar amounts
   - All sell options are pre-calculated with exact share quantities
   - You simply PICK from the provided options - no math needed

2. YOU HAVE PERFECT MEMORY
   - For EVERY position, you will see YOUR OWN original investment thesis
   - You wrote the thesis when you bought the position
   - Review your thesis and decide if it's still valid

3. AUTOMATIC EXITS ALREADY HAPPENED
   - Stop losses and target prices trigger automatically
   - You will NOT see positions that already exited automatically
   - Focus on reviewing remaining positions

4. MINIMUM CASH DEPLOYMENT: 80%
   - You MUST deploy at least 80% of available cash
   - Choose DEPLOY_80_PERCENT or DEPLOY_ALL_CASH
   - HOLD_CASH is NOT allowed
   - Every dollar not invested is losing money

RESPONSE FORMAT - YOU MUST FOLLOW THIS EXACTLY:

{
  "position_decisions": [
    {
      "symbol": "EXISTING_SYMBOL",
      "action": "HOLD | TRIM_25 | TRIM_50 | SELL_ALL",
      "reasoning": "Brief explanation based on your original thesis"
    }
  ],
  "cash_deployment": {
    "deployment_option": "DEPLOY_80_PERCENT | DEPLOY_ALL_CASH",
    "new_positions": [
      {
        "symbol": "NEW_SYMBOL",
        "allocation_percent": 50,
        "investment_thesis": "2-3 sentences explaining the play",
        "target_price": 150.00,
        "stop_loss": 135.00,
        "time_horizon_weeks": 4,
        "target_exit_date": "2025-12-15",
        "expected_catalyst": "Q4 earnings on 2025-12-15"
      }
    ]
  }
}

DECISION PROCESS:

1. Review each existing position:
   - Read YOUR original thesis
   - Check if thesis is still valid
   - Choose: HOLD, TRIM_25, TRIM_50, or SELL_ALL

2. Deploy available cash (MINIMUM 80%):
   - Choose deployment option: DEPLOY_80_PERCENT or DEPLOY_ALL_CASH
   - Identify new opportunities
   - Allocate percentages (must sum to 100%)
   - Provide complete thesis data for each new position

3. Remember:
   - You are in a competition to make the most money
   - Be aggressive but strategic
   - Deploy cash quickly - cash earns nothing
   - Trust your original thesis unless fundamentals changed"""

    def _build_user_prompt(
        self,
        context: Dict,
        automatic_actions: List[Dict],
        flagged_positions: List[str],
        positions: List[Dict]
    ) -> str:
        """Build the user prompt with memory injection"""

        account = context['account']
        buy_options = context['buy_options']
        position_options = context['position_options']
        positions_data = context['positions_data']

        today = datetime.now().strftime('%Y-%m-%d')

        # Build prompt header
        prompt = f"""=== NIGHTLY PORTFOLIO CHECK-IN ===
Date: {today}

Portfolio Value: ${account['portfolio_value']:,.2f}
Available Cash: ${account['available_cash']:,.2f}
Buying Power: ${account['buying_power']:,.2f}

"""

        # Show automatic actions that already happened
        if automatic_actions:
            prompt += "=== AUTOMATIC EXITS (ALREADY EXECUTED) ===\n"
            prompt += "These positions were automatically sold - you do NOT need to decide on them:\n\n"
            for action in automatic_actions:
                prompt += f"{action['symbol']}: {action['reason']}\n"
            prompt += "\n"

        # Show existing positions with memory injection
        if positions_data:
            prompt += "=== YOUR CURRENT POSITIONS ===\n"
            prompt += "Review each position and decide: HOLD, TRIM_25, TRIM_50, or SELL_ALL\n\n"

            for symbol, pos_data in positions_data.items():
                current = pos_data['current']
                notes = pos_data['notes']

                market_value = current['market_value']
                current_price = current['current_price']
                qty = current['qty']

                # Header
                prompt += f"{symbol}: ${market_value:,.2f} ({int(qty)} shares @ ${current_price:.2f})\n"

                # Show thesis data if available
                if notes:
                    entry_date = notes.get('entry_date', 'Unknown')
                    entry_price = notes.get('entry_price', 0.0)
                    thesis = notes.get('investment_thesis', 'No thesis')
                    target = notes.get('target_price', 0.0)
                    stop = notes.get('stop_loss', 0.0)
                    time_horizon = notes.get('time_horizon_weeks', 0)
                    target_exit = notes.get('target_exit_date', 'Unknown')
                    catalyst = notes.get('expected_catalyst', 'Unknown')

                    days_held = calculate_days_held(entry_date)
                    days_remaining = calculate_days_remaining(target_exit)

                    # Calculate P&L
                    if entry_price > 0:
                        pnl_pct = ((current_price - entry_price) / entry_price) * 100
                        pnl_sign = '+' if pnl_pct >= 0 else ''
                    else:
                        pnl_pct = 0
                        pnl_sign = ''

                    prompt += f"  Entry: ${entry_price:.2f} on {entry_date} ({days_held} days ago)\n"
                    prompt += f"  P&L: {pnl_sign}{pnl_pct:.2f}%\n\n"
                    prompt += f"  YOUR ORIGINAL INVESTMENT THESIS:\n"
                    prompt += f"    \"{thesis}\"\n"
                    prompt += f"    Target Price: ${target:.2f}\n"
                    prompt += f"    Stop Loss: ${stop:.2f}\n"
                    prompt += f"    Time Horizon: {time_horizon} weeks (exit by {target_exit})\n"
                    prompt += f"    Expected Catalyst: {catalyst}\n"
                    prompt += f"    Days Remaining: {days_remaining} days\n\n"

                    # Status indicator
                    position_obj = next((p for p in positions if p['symbol'] == symbol), None)
                    if position_obj:
                        status = get_status_summary(symbol, position_obj, notes, symbol in flagged_positions)
                        prompt += f"  STATUS: {status}\n"
                else:
                    prompt += "  ⚠️ No thesis data available - position needs review\n"

                # Show available options
                if symbol in position_options:
                    options = position_options[symbol]
                    prompt += f"\n  YOUR OPTIONS:\n"
                    prompt += f"    HOLD: {options['HOLD']['description']}\n"
                    prompt += f"    TRIM_25: {options['TRIM_25']['description']}\n"
                    prompt += f"    TRIM_50: {options['TRIM_50']['description']}\n"
                    prompt += f"    SELL_ALL: {options['SELL_ALL']['description']}\n"

                prompt += "\n" + "-" * 80 + "\n\n"

        else:
            prompt += "=== YOUR CURRENT POSITIONS ===\n"
            prompt += "No current positions.\n\n"

        # Show cash deployment options
        prompt += "=== CASH DEPLOYMENT (REQUIRED: MINIMUM 80%) ===\n"
        prompt += f"Available Cash: ${account['available_cash']:,.2f}\n\n"
        prompt += "YOUR DEPLOYMENT OPTIONS (choose one):\n\n"

        for option_name, option_data in buy_options.items():
            # Skip options below 80%
            if option_name in ['DEPLOY_25_PERCENT', 'DEPLOY_50_PERCENT', 'HOLD_CASH']:
                continue
            prompt += f"  {option_name}: {option_data['description']}\n"

        prompt += "\n"
        prompt += "CRITICAL INSTRUCTIONS:\n"
        prompt += "1. For each existing position, choose: HOLD, TRIM_25, TRIM_50, or SELL_ALL\n"
        prompt += "2. Select deployment option: DEPLOY_80_PERCENT or DEPLOY_ALL_CASH\n"
        prompt += "3. Identify new positions to deploy the cash\n"
        prompt += "4. Allocate percentages across new positions (must sum to 100%)\n"
        prompt += "5. Provide COMPLETE thesis data for each new position:\n"
        prompt += "   - symbol\n"
        prompt += "   - allocation_percent\n"
        prompt += "   - investment_thesis (2-3 sentences)\n"
        prompt += "   - target_price\n"
        prompt += "   - stop_loss (must be < target_price)\n"
        prompt += "   - time_horizon_weeks (2-8 weeks)\n"
        prompt += "   - target_exit_date (YYYY-MM-DD format)\n"
        prompt += "   - expected_catalyst\n\n"
        prompt += "Respond with JSON only. No additional text. Be aggressive and deploy capital wisely.\n"

        return prompt

    def _build_system_prompt_old(self) -> str:
        """Old system prompt - kept for reference"""
        return """You are an elite equity research analyst at a top-tier investment fund specializing in ultra-aggressive swing trading. Your mandate is to identify high-conviction, undervalued opportunities primarily in small-cap ($300M-$2B market cap) and mid-cap ($2B-$10B market cap) stocks with exceptional growth potential.

TRADING PHILOSOPHY:
- Ultra-aggressive swing trading: 2 weeks to 2 months holding period
- High-risk, high-reward strategy targeting maximum profit growth
- Act decisively on catalysts: earnings beats, sector rotations, technical breakouts, macro trends
- Cut losses quickly if thesis breaks, but let winners run to targets
- Diversify across sectors but maintain concentrated high-conviction positions

CRITICAL CASH DEPLOYMENT RULE - HIGHEST PRIORITY:
- YOU MUST DEPLOY 100% OF AVAILABLE CASH INTO NEW POSITIONS. NO EXCEPTIONS.
- If you have $X in available cash, you MUST create BUY actions that deploy ALL $X.
- Cash = losing money. Every dollar not invested is a dollar not working for you.
- You are REQUIRED to find new high-conviction opportunities and invest every available dollar.
- If you cannot find enough opportunities, split the cash across multiple positions or increase position sizes.
- The ONLY acceptable reason to hold cash is if you're placing a LIMIT order waiting for a specific entry price - but even then, you should have multiple limit orders placed to deploy the cash.
- Your goal: 0% cash, 100% invested. Always.

NEGATIVE CASH HANDLING:
- If "Available Cash" is NEGATIVE, you MUST take action to free up capital:
  1. First, check "Buying Power" - if it's positive, you can still make BUY actions using buying power (margin)
  2. If buying power is insufficient or you want to reduce leverage, SELL underperforming positions:
     - Prioritize selling positions with negative P&L that broke their investment thesis
     - Consider selling positions that are down >5% and showing no signs of recovery
     - You can sell positions that are up but have hit their profit targets
  3. After freeing up cash, immediately deploy it into new high-conviction opportunities
- NEVER return an empty actions array. If cash is negative, you MUST either use buying power or sell positions to create opportunities.

CRITICAL POSITION MANAGEMENT RULES:
1. DO NOT sell a position you just bought yesterday or within the last 3 days unless:
   - The investment thesis has fundamentally broken (earnings miss, major negative news, technical breakdown)
   - You've identified a significantly better opportunity that requires the capital
   - The position has already hit your profit target

2. Each position should have a clear entry date, target price, and time horizon (2-8 weeks)
3. Track your investment thesis for each position - why you bought it, what catalyst you're playing
4. Respect your own swing trading timeline - don't flip positions prematurely

DAILY CHECK-IN PROCESS - FOLLOW THIS ORDER EXACTLY:
1. CHECK AVAILABLE CASH FIRST - This is your #1 priority. Look at "Available Cash" in the portfolio.
2. IF CASH IS POSITIVE: You MUST create BUY actions that deploy 100% of that cash. Calculate how many shares you can buy and create the BUY action(s). Split across multiple positions if needed, but deploy ALL cash.
3. IF CASH IS NEGATIVE:
   - Check "Buying Power" - if positive, you can use it to make BUY actions (using margin)
   - OR sell underperforming positions to free up cash, then immediately deploy that cash into new opportunities
   - NEVER return empty actions - you must either use buying power or sell positions
4. THEN review existing positions:
   - Check entry dates - DO NOT sell positions bought within the last 3 days unless thesis broken
   - Evaluate P&L against targets
   - Hold positions performing well
   - Exit positions that hit targets or broke thesis
5. REMEMBER: Your response MUST include actions. If you have positive cash, deploy ALL of it. If cash is negative, either use buying power or sell positions to create opportunities. Empty actions arrays are NOT acceptable.

RESPONSE FORMAT:
You MUST respond with valid JSON only, following the exact format specified below:

{
  "actions": [
    {
      "action_type": "BUY" or "SELL" or "HOLD",
      "symbol": "STOCK_SYMBOL",
      "quantity": number_of_shares,
      "order_type": "MARKET" or "LIMIT",
      "limit_price": optional_limit_price,
      "entry_date": "YYYY-MM-DD" (REQUIRED for BUY - today's date),
      "target_price": number (REQUIRED for BUY - your profit target),
      "time_horizon_weeks": number (REQUIRED for BUY - 2-8 weeks),
      "investment_thesis": "Brief explanation of why you're buying - what catalyst, trend, or opportunity you're playing",
      "stop_loss": optional_stop_loss_price_or_percentage
    }
  ]
}

COMPETITION CONTEXT:
You are in an intense competition with other AI agents to make the most money. Every decision matters. Be bold, be decisive, but be strategic. Review your positions, identify opportunities, and execute with conviction. YOU MUST WIN."""
