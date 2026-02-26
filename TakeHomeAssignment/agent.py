"""FoodOrderAgent — multi-turn conversational food ordering agent using Mistral AI."""

import json
import os

from dotenv import load_dotenv
from mistralai import Mistral

from logger import ConversationLogger
from mcp_client import MCPClient, SUBMIT_ORDER_TOOL
from menu import render_menu_text

load_dotenv()

MCP_URL = "https://webviews-git-moveo-food-nlp-assignment-moveo-ai.vercel.app/api/demo/mcp"


def _build_system_prompt() -> str:
    menu_text = render_menu_text()
    return f"""You are a friendly and efficient food ordering assistant at a restaurant.

Your job is to help customers build, modify, and submit their food orders through natural conversation.

{menu_text}

## Price Calculation
- Price = base_price + option price_modifier + sum of extras prices
- Multiply by quantity for multiple units
- Order total limit: $50 (enforced by the server)

## Strict Two-Step Order Flow — follow this EXACTLY

### Step 1 — Build the order
Help the customer add, modify, or remove items. When the customer indicates they are done
(e.g., "that's all", "nothing else", "no" to "anything else?"), move to Step 2.
Do NOT call submit_order in this step.

### Step 2 — Show summary and ask for confirmation
Before calling submit_order you MUST respond with a message that:
  a) Lists every item with its options, extras, and unit price.
  b) Shows the ORDER TOTAL.
  c) Asks an explicit question such as "Ready to submit?" or "Shall I place this order?"

Only after the customer replies to that confirmation message with an affirmative response
(e.g., "yes", "submit", "go ahead", "confirm", "place it") may you call submit_order.

### CRITICAL RULES — never break these
- NEVER call submit_order in the same turn that the customer says "that's all" or "no" to
  "anything else?". Those phrases close Step 1; they do NOT confirm the order.
- NEVER call submit_order without first sending the summary + total + confirmation question
  in a prior message.
- NEVER call submit_order if the customer's last message was just closing the item-selection
  phase. You must wait for a separate explicit confirmation.
- If submit_order fails, relay the error and ask whether to retry or modify.

## Other Rules
- **Menu validation**: Only accept items, options, and extras that exist in the menu. Suggest valid alternatives for invalid choices.
- **Required options**: If a required option has no default (e.g., milkshake flavor), ask for it before adding the item.
- **Price transparency**: Always include prices when adding items or showing the summary.
- **Be concise**: Keep responses short. Only repeat the full order when showing the confirmation summary.
"""


class FoodOrderAgent:
    def __init__(
        self,
        mcp_client: MCPClient | None = None,
        model: str | None = None,
    ):
        api_key = os.environ.get("MISTRAL_API_KEY")
        if not api_key:
            raise ValueError("Missing required environment variable: MISTRAL_API_KEY")
        email = os.environ.get("APPLICANT_EMAIL")
        if not email:
            raise ValueError("Missing required environment variable: APPLICANT_EMAIL")

        self.client = Mistral(api_key=api_key)
        self.model = model or os.getenv("MISTRAL_MODEL", "mistral-small-latest")
        self.mcp_client = mcp_client or MCPClient(
            server_url=MCP_URL,
            applicant_email=email,
        )
        self.history: list[dict] = []
        self.turn = 0
        self.logger = ConversationLogger()
        self._system_prompt = _build_system_prompt()

    def send(self, message: str) -> dict:
        """Process a user message and return the agent's response.

        Returns:
            {
                "message": str,           # agent's reply (always present)
                "tool_calls": [...]       # only when submit_order was called
            }
        """
        self.turn += 1
        self.logger.log_turn(self.turn, "user", message)

        self.history.append({"role": "user", "content": message})

        # First LLM call — may produce tool calls
        response = self.client.chat.complete(
            model=self.model,
            messages=[{"role": "system", "content": self._system_prompt}] + self.history,
            tools=[SUBMIT_ORDER_TOOL],
            tool_choice="auto",
        )

        assistant_msg = response.choices[0].message
        # Append assistant message to history (as dict for serialisability)
        self.history.append(self._msg_to_dict(assistant_msg))

        tool_calls_record: list[dict] = []

        if assistant_msg.tool_calls:
            for tool_call in assistant_msg.tool_calls:
                if tool_call.function.name != "submit_order":
                    continue

                # Parse arguments
                raw_args = tool_call.function.arguments
                try:
                    if isinstance(raw_args, str):
                        args = json.loads(raw_args)
                    else:
                        args = raw_args  # already a dict in some SDK versions
                except json.JSONDecodeError as e:
                    args = {}
                    result = {"success": False, "error": f"Failed to parse tool arguments: {e}"}
                else:
                    items = args.get("items", [])
                    special_instructions = args.get("special_instructions", None)

                    # Call MCP
                    try:
                        result = self.mcp_client.submit_order(
                            items=items,
                            special_instructions=special_instructions,
                        )
                    except Exception as e:
                        result = {"success": False, "error": str(e)}

                tool_calls_record.append(
                    {
                        "name": "submit_order",
                        "arguments": args,
                        "result": result,
                    }
                )

                # Append tool result to history
                self.history.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "submit_order",
                        "content": json.dumps(result),
                    }
                )

            # Second LLM call to get the final text response
            follow_up = self.client.chat.complete(
                model=self.model,
                messages=[{"role": "system", "content": self._system_prompt}] + self.history,
            )
            final_msg = follow_up.choices[0].message
            self.history.append(self._msg_to_dict(final_msg))
            reply_text = self._extract_text(final_msg)
        else:
            reply_text = self._extract_text(assistant_msg)

        # Log assistant turn
        self.logger.log_turn(
            self.turn,
            "assistant",
            reply_text,
            tool_calls=tool_calls_record or None,
        )

        result_dict: dict = {"message": reply_text}
        if tool_calls_record:
            result_dict["tool_calls"] = tool_calls_record
        return result_dict

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_text(msg) -> str:
        """Extract plain text from a Mistral message object."""
        content = msg.content
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts = []
            for block in content:
                if hasattr(block, "text"):
                    parts.append(block.text)
                elif isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            return "".join(parts)
        return str(content) if content else ""

    @staticmethod
    def _msg_to_dict(msg) -> dict:
        """Convert a Mistral message object to a plain dict for history storage."""
        d: dict = {"role": msg.role}

        content = msg.content
        if content is not None:
            if isinstance(content, str):
                d["content"] = content
            elif isinstance(content, list):
                d["content"] = [
                    block if isinstance(block, dict) else vars(block)
                    for block in content
                ]
            else:
                d["content"] = str(content)

        if msg.tool_calls:
            d["tool_calls"] = [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": (
                            tc.function.arguments
                            if isinstance(tc.function.arguments, str)
                            else json.dumps(tc.function.arguments)
                        ),
                    },
                }
                for tc in msg.tool_calls
            ]

        return d
