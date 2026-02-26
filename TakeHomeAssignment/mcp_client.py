"""Synchronous MCP client wrapper for the food ordering submit_order tool."""

import asyncio
import json

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

SUBMIT_ORDER_TOOL = {
    "type": "function",
    "function": {
        "name": "submit_order",
        "description": (
            "Submit the confirmed food order to the kitchen. "
            "Call ONLY after the user has explicitly confirmed the order."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "List of order items",
                    "items": {
                        "type": "object",
                        "properties": {
                            "item_id": {
                                "type": "string",
                                "description": "Menu item ID (e.g., classic_burger, margherita)",
                            },
                            "quantity": {
                                "type": "integer",
                                "description": "Number of this item",
                            },
                            "options": {
                                "type": "object",
                                "description": "Item options (e.g., size, patty, crust, flavor)",
                            },
                            "extras": {
                                "type": "array",
                                "description": "List of extra IDs for this item",
                                "items": {"type": "string"},
                            },
                        },
                        "required": ["item_id", "quantity"],
                    },
                },
                "special_instructions": {
                    "type": "string",
                    "description": "Any special instructions for the order",
                },
            },
            "required": ["items"],
        },
    },
}


class MCPClient:
    def __init__(self, server_url: str, applicant_email: str):
        self.server_url = server_url
        self.applicant_email = applicant_email

    def submit_order(
        self,
        items: list[dict],
        special_instructions: str | None = None,
    ) -> dict:
        """Submit the order synchronously. Runs the async implementation internally."""
        return asyncio.run(self._submit_order_async(items, special_instructions))

    async def _submit_order_async(
        self,
        items: list[dict],
        special_instructions: str | None = None,
    ) -> dict:
        headers = {"X-Applicant-Email": self.applicant_email}
        arguments: dict = {"items": items}
        if special_instructions is not None:
            arguments["special_instructions"] = special_instructions

        async with streamablehttp_client(self.server_url, headers=headers) as (
            read,
            write,
            _,
        ):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool("submit_order", arguments)

                # Parse the text content from the result
                if result.content and len(result.content) > 0:
                    raw = result.content[0].text
                    try:
                        return json.loads(raw)
                    except (json.JSONDecodeError, AttributeError):
                        return {"success": False, "error": str(raw)}

                return {"success": False, "error": "Empty response from MCP server"}
