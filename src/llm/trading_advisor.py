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
        portfolio_data: Dict,
        custom_instructions: Optional[str] = None
    ) -> Dict:
        """
        Analyze portfolio and get trading decisions from LLM

        Args:
            portfolio_data: Formatted portfolio data
            custom_instructions: Optional custom instructions to add to the prompt

        Returns:
            Dict containing trading decisions and reasoning
        """
        try:
            # Build the system prompt
            system_prompt = self._build_system_prompt()

            # Build the user prompt with portfolio data
            user_prompt = self._build_user_prompt(portfolio_data, custom_instructions)

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
        return """You are an expert financial trading advisor AI. Your role is to analyze portfolio data and make informed trading decisions.

IMPORTANT GUIDELINES:
1. You MUST respond with valid JSON only, following the exact format specified
2. Consider risk management, diversification, and market conditions
3. Be conservative - only suggest trades when you have strong conviction
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
  "warnings": ["Any warnings or concerns about the current portfolio or proposed trades"]
}

If you recommend no changes, return an empty actions array but still provide analysis."""

    def _build_user_prompt(
        self,
        portfolio_data: Dict,
        custom_instructions: Optional[str] = None
    ) -> str:
        """Build the user prompt with portfolio data"""

        prompt = f"""Please analyze the following portfolio and provide trading recommendations.

PORTFOLIO DATA:
{json.dumps(portfolio_data, indent=2)}

"""

        if custom_instructions:
            prompt += f"""
ADDITIONAL INSTRUCTIONS:
{custom_instructions}

"""

        prompt += """
Based on this data, please provide your analysis and trading recommendations in the JSON format specified.
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
