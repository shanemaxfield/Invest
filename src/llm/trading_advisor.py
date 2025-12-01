"""
LLM Trading Advisor
Integrates with OpenAI (or other LLMs) to make trading decisions
"""

import json
import logging
from typing import Dict, List, Optional
from openai import OpenAI

logger = logging.getLogger(__name__)


class TradingAdvisor:
    """LLM-based trading advisor that analyzes portfolio and suggests trades"""

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
        portfolio_template: str,
        custom_instructions: Optional[str] = None
    ) -> Dict:
        """
        Analyze portfolio and get trading decisions from LLM

        Args:
            portfolio_template: Formatted portfolio template string
            custom_instructions: Optional custom instructions to add to the prompt

        Returns:
            Dict containing trading decisions and reasoning
        """
        try:
            # Build the system prompt
            system_prompt = self._build_system_prompt()

            # Build the user prompt with portfolio data
            user_prompt = self._build_user_prompt(portfolio_template, custom_instructions)

            # Call the LLM (silently, output handled in main.py)
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

            return decisions

        except Exception as e:
            logger.error(f"Error getting trading decisions from LLM: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM"""
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

    def _build_user_prompt(
        self,
        portfolio_template: str,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build the user prompt with portfolio template"""

        prompt = f"""{portfolio_template}

"""

        if custom_instructions:
            prompt += f"""
ADDITIONAL INSTRUCTIONS:
{custom_instructions}

"""

        prompt += """
CRITICAL INSTRUCTIONS FOR THIS CHECK-IN:

STEP 1 - DEPLOY ALL CASH OR FREE UP CAPITAL (MANDATORY):
Look at "Available Cash" above. 
- IF CASH IS POSITIVE: You MUST deploy 100% of it. Calculate the exact dollar amount and create BUY actions that use ALL of it.
  - If you have $50,000 cash, you MUST buy $50,000 worth of stocks
  - Split across multiple positions if needed, but deploy EVERY DOLLAR
- IF CASH IS NEGATIVE: You have two options:
  1. Use "Buying Power" if it's positive to make BUY actions (using margin)
  2. SELL underperforming positions to free up cash, then immediately deploy that cash into new opportunities
- Your response MUST include actions - either BUY actions deploying cash/buying power, or SELL actions to free up capital followed by BUY actions
- Empty actions arrays are NOT acceptable - you must take action to win the competition

STEP 2 - Review Existing Positions:
- Check entry dates - DO NOT sell positions bought within last 3 days unless thesis fundamentally broken
- Evaluate P&L - hold winners, exit losers or positions that hit targets

STEP 3 - Execute:
Be aggressive. Deploy all cash. Make bold moves. Every dollar must work.
"""

        return prompt

    def validate_decisions(self, decisions: Dict) -> bool:
        """
        Validate that the LLM decisions are in the correct format

        Args:
            decisions: The decisions dict from the LLM

        Returns:
            True if valid, raises exception if not
        """
        required_keys = ['actions']

        for key in required_keys:
            if key not in decisions:
                raise ValueError(f"Missing required key in LLM response: {key}")

        # Validate actions
        if not isinstance(decisions['actions'], list):
            raise ValueError("'actions' must be a list")

        for i, action in enumerate(decisions['actions']):
            # Required fields for API communication
            required_action_keys = ['action_type', 'symbol']
            for key in required_action_keys:
                if key not in action:
                    raise ValueError(f"Action {i} missing required key: {key}")

            # Validate action type
            if action['action_type'] not in ['BUY', 'SELL', 'HOLD', 'REBALANCE']:
                raise ValueError(f"Invalid action_type: {action['action_type']}")

            # Validate order type if present
            if 'order_type' in action and action['order_type'] not in ['MARKET', 'LIMIT']:
                raise ValueError(f"Invalid order_type: {action['order_type']}")

            # Check for quantity on BUY/SELL actions
            if action['action_type'] in ['BUY', 'SELL']:
                if 'quantity' not in action or action['quantity'] <= 0:
                    raise ValueError(f"Action {i} ({action['action_type']}) must have positive quantity")

        logger.info("LLM decisions validated successfully")
        return True
    
    def extract_notes_updates(self, decisions: Dict, actions_taken: List[Dict]) -> Dict[str, str]:
        """
        Extract notes updates from LLM decisions, only for positions that changed
        
        Args:
            decisions: LLM decisions dict
            actions_taken: List of actions that were actually executed
        
        Returns:
            Dict mapping symbol to note text (only for changed positions)
        """
        notes_updates = {}
        
        # Get notes_updates from LLM response
        llm_notes = decisions.get('notes_updates', {})
        
        # Only include notes for symbols where we actually took action
        symbols_with_changes = set()
        for action in actions_taken:
            action_data = action.get('action', {})
            if action_data.get('action_type') in ['BUY', 'SELL']:
                symbols_with_changes.add(action_data.get('symbol'))
        
        # Filter notes to only include changed positions
        for symbol, note in llm_notes.items():
            if symbol in symbols_with_changes:
                # Validate note length (max 3 sentences)
                sentences = note.split('.')
                if len(sentences) > 3:
                    # Truncate to 3 sentences
                    note = '. '.join(sentences[:3]) + '.'
                notes_updates[symbol] = note.strip()
        
        if notes_updates:
            logger.info(f"Extracted notes updates for {len(notes_updates)} positions")
        
        return notes_updates
