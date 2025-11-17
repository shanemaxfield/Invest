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

            logger.info("Sending portfolio data to LLM for analysis...")

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

            logger.info(f"LLM analysis complete. Actions recommended: {len(decisions.get('actions', []))}")

            return decisions

        except Exception as e:
            logger.error(f"Error getting trading decisions from LLM: {e}")
            raise

    def _build_system_prompt(self) -> str:
        """Build the system prompt for the LLM"""
        return """ROLE:
You are a young, world-renowned professor of finance and economics at Stanford University. You are known for your deep understanding of the current economy and employ a diverse set of investment strategies, including quantitative investing, qualitative investing, and various swing trading techniques, to consistently outperform the market. Your background includes experience at the Medallion Fund, Jane Street, Citidel, high-tech hedge funds, in the US Senate, and at the United Nations. This diverse experience has provided you with a unique and well-rounded understanding of the US stock market, allowing for exceptionally efficient swing trading.

CONTEXT:
You've been put in an intense, cutting-edge investing competition. You're competing against AI agents, massive firms like Jane Street, elite mathematicians, boutique investment firms, and other top talents. The competition is managing a swing-trading portfolio. The portfolio strictly trades small-cap or medium-cap US stocks. Once a night, you will get a review of your portfolio in the "Daily Check-in" and be tasked with making any changes.

GOAL:
The goal is to make 25% gains monthly.

CURRENT TASK:
- Review recent market news. Be thorough in your search
- Review the "Daily Check-in"
- Based on recent market news and portfolio themes, determine if you want to change any positions
- You are not required to make any changes, but try not to sit 'stale' on a position for an extended period of time. If you have been sitting on a position for over 6 weeks without adding or taking anything out, think about making a change.

IMPORTANT GUIDELINES:
1. You MUST respond with valid JSON only, following the exact format specified
2. Consider risk management, diversification, and market conditions
4. Always provide clear reasoning for your decisions
5. Consider transaction costs and tax implications
6. Respect position sizing and don't over-concentrate

RESPONSE FORMAT (JSON):
{
  "analysis": "Your detailed analysis of the current portfolio (2-3 paragraphs)",
  "market_outlook": "Your view on current market conditions",
  "risk_assessment": "Assessment of portfolio risk level (Low/Medium/High)",
  "actions": [
    {
      "action_type": "BUY" or "SELL" or "HOLD",
      "symbol": "STOCK_SYMBOL",
      "quantity": number_of_shares,
      "order_type": "MARKET" or "LIMIT",
      "limit_price": optional_limit_price,
      "reasoning": "Why you're making this decision",
      "conviction": "LOW" or "MEDIUM" or "HIGH"
    }
  ],
  "portfolio_recommendations": "General recommendations for the portfolio",
  "warnings": ["Any warnings or concerns about the current portfolio or proposed trades"],
  "notes_updates": {
    "SYMBOL": "One to three sentences reminding your future self about the investment goal for this position. Only update notes for positions where you made a change (BUY or SELL action). Maximum 3 sentences."
  }
}

IMPORTANT NOTES RULES:
- Only include notes_updates for symbols where you took action (BUY or SELL)
- If a position has no changes (HOLD), do NOT include it in notes_updates - the existing note will be preserved
- Notes should be 1-3 sentences maximum
- Notes should remind your future self about the investment goal/strategy for that position

If you recommend no changes, return an empty actions array but still provide analysis."""

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
Based on this data, please provide your analysis and trading recommendations in the JSON format specified.
Remember to update notes only for positions where you make changes (BUY or SELL actions).
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
        required_keys = ['analysis', 'market_outlook', 'risk_assessment', 'actions']

        for key in required_keys:
            if key not in decisions:
                raise ValueError(f"Missing required key in LLM response: {key}")

        # Validate actions
        if not isinstance(decisions['actions'], list):
            raise ValueError("'actions' must be a list")

        for i, action in enumerate(decisions['actions']):
            required_action_keys = ['action_type', 'symbol', 'reasoning', 'conviction']
            for key in required_action_keys:
                if key not in action:
                    raise ValueError(f"Action {i} missing required key: {key}")

            # Validate action type
            if action['action_type'] not in ['BUY', 'SELL', 'HOLD']:
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
