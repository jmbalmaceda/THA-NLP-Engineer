"""Tests for mcp_client.py — order submission via MCP."""

import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_client import MCPClient

SERVER_URL = "https://example.com/mcp"
EMAIL = "test@example.com"


def _make_mcp_result(payload: dict):
    """Build a mock MCP call_tool result with a JSON text content block."""
    content_block = MagicMock()
    content_block.text = json.dumps(payload)
    result = MagicMock()
    result.content = [content_block]
    return result


@pytest.fixture
def client():
    return MCPClient(server_url=SERVER_URL, applicant_email=EMAIL)


class TestSubmitOrder:
    def test_submit_order_success(self, client):
        success_payload = {
            "success": True,
            "order_id": "ORD-99999",
            "total": 10.50,
            "estimated_time": "15-20 minutes",
        }
        mock_result = _make_mcp_result(success_payload)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_http_ctx = AsyncMock()
        mock_http_ctx.__aenter__ = AsyncMock(
            return_value=(AsyncMock(), AsyncMock(), None)
        )
        mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("mcp_client.streamablehttp_client", return_value=mock_http_ctx),
            patch("mcp_client.ClientSession", return_value=mock_session),
        ):
            result = client.submit_order(
                items=[{"item_id": "classic_burger", "quantity": 1}]
            )

        assert result["success"] is True
        assert result["order_id"] == "ORD-99999"
        assert result["total"] == 10.50

    def test_submit_order_failure(self, client):
        failure_payload = {
            "success": False,
            "error": "Order total ($52.00) exceeds $50 limit.",
        }
        mock_result = _make_mcp_result(failure_payload)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_http_ctx = AsyncMock()
        mock_http_ctx.__aenter__ = AsyncMock(
            return_value=(AsyncMock(), AsyncMock(), None)
        )
        mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("mcp_client.streamablehttp_client", return_value=mock_http_ctx),
            patch("mcp_client.ClientSession", return_value=mock_session),
        ):
            result = client.submit_order(
                items=[{"item_id": "classic_burger", "quantity": 10}]
            )

        assert result["success"] is False
        assert "exceeds" in result["error"]

    def test_submit_order_sends_correct_headers(self, client):
        """Verify the X-Applicant-Email header is passed to streamablehttp_client."""
        success_payload = {"success": True, "order_id": "ORD-1"}
        mock_result = _make_mcp_result(success_payload)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        captured_kwargs: dict = {}

        def fake_streamablehttp_client(url, **kwargs):
            captured_kwargs.update({"url": url, **kwargs})
            ctx = AsyncMock()
            ctx.__aenter__ = AsyncMock(return_value=(AsyncMock(), AsyncMock(), None))
            ctx.__aexit__ = AsyncMock(return_value=False)
            return ctx

        with (
            patch("mcp_client.streamablehttp_client", side_effect=fake_streamablehttp_client),
            patch("mcp_client.ClientSession", return_value=mock_session),
        ):
            client.submit_order(items=[{"item_id": "fries", "quantity": 1}])

        assert captured_kwargs.get("headers", {}).get("X-Applicant-Email") == EMAIL

    def test_submit_order_with_special_instructions(self, client):
        success_payload = {"success": True, "order_id": "ORD-2"}
        mock_result = _make_mcp_result(success_payload)

        mock_session = AsyncMock()
        mock_session.initialize = AsyncMock()
        mock_session.call_tool = AsyncMock(return_value=mock_result)
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)

        mock_http_ctx = AsyncMock()
        mock_http_ctx.__aenter__ = AsyncMock(
            return_value=(AsyncMock(), AsyncMock(), None)
        )
        mock_http_ctx.__aexit__ = AsyncMock(return_value=False)

        with (
            patch("mcp_client.streamablehttp_client", return_value=mock_http_ctx),
            patch("mcp_client.ClientSession", return_value=mock_session),
        ):
            client.submit_order(
                items=[{"item_id": "fries", "quantity": 1}],
                special_instructions="No salt",
            )

        call_args = mock_session.call_tool.call_args
        arguments = call_args[0][1]
        assert arguments.get("special_instructions") == "No salt"
