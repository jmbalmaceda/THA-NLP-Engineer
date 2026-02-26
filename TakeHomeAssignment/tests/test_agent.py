"""Tests for agent.py — FoodOrderAgent send() behaviour."""

import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent))


# ---------------------------------------------------------------------------
# Helpers to build fake Mistral response objects
# ---------------------------------------------------------------------------

def _make_text_message(text: str, role: str = "assistant"):
    msg = MagicMock()
    msg.role = role
    msg.content = text
    msg.tool_calls = None
    return msg


def _make_tool_call_message(tool_name: str, arguments: dict, call_id: str = "tc_001"):
    tc_func = MagicMock()
    tc_func.name = tool_name
    tc_func.arguments = json.dumps(arguments)

    tc = MagicMock()
    tc.id = call_id
    tc.function = tc_func

    msg = MagicMock()
    msg.role = "assistant"
    msg.content = None
    msg.tool_calls = [tc]
    return msg


def _make_response(message):
    choice = MagicMock()
    choice.message = message
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_mcp():
    mcp = MagicMock()
    mcp.submit_order.return_value = {
        "success": True,
        "order_id": "ORD-TEST",
        "total": 8.50,
        "estimated_time": "15-20 minutes",
    }
    return mcp


@pytest.fixture
def agent(mock_mcp):
    """FoodOrderAgent with mocked Mistral client and MCPClient."""
    with patch.dict(
        "os.environ",
        {"MISTRAL_API_KEY": "test-key", "APPLICANT_EMAIL": "test@example.com"},
    ):
        with patch("agent.Mistral") as MockMistral:
            mock_mistral_instance = MagicMock()
            MockMistral.return_value = mock_mistral_instance

            from agent import FoodOrderAgent

            a = FoodOrderAgent(mcp_client=mock_mcp)
            a._mistral_mock = mock_mistral_instance
            return a


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSendSimpleMessage:
    def test_returns_message_key(self, agent):
        text_msg = _make_text_message("Hello, what can I get you?")
        agent._mistral_mock.chat.complete.return_value = _make_response(text_msg)

        result = agent.send("Hi")

        assert "message" in result
        assert result["message"] == "Hello, what can I get you?"

    def test_no_tool_calls_key_when_no_tool_called(self, agent):
        text_msg = _make_text_message("Sure, one burger!")
        agent._mistral_mock.chat.complete.return_value = _make_response(text_msg)

        result = agent.send("I want a burger")

        assert "tool_calls" not in result


class TestSubmitOrderToolCall:
    def test_send_triggers_submit_order(self, agent, mock_mcp):
        order_args = {
            "items": [{"item_id": "classic_burger", "quantity": 1, "options": {"size": "regular"}}]
        }
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Order submitted! Order #ORD-TEST.")

        # First call returns tool_call, second returns final text
        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        result = agent.send("Yes, submit it")

        assert "tool_calls" in result
        assert len(result["tool_calls"]) == 1
        assert result["tool_calls"][0]["name"] == "submit_order"
        assert result["tool_calls"][0]["result"]["success"] is True
        mock_mcp.submit_order.assert_called_once()

    def test_tool_call_result_structure(self, agent, mock_mcp):
        order_args = {
            "items": [{"item_id": "fries", "quantity": 2, "options": {"size": "large"}}],
            "special_instructions": "Extra crispy",
        }
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Done!")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        result = agent.send("Submit")

        tc = result["tool_calls"][0]
        assert tc["name"] == "submit_order"
        assert "arguments" in tc
        assert "result" in tc
        assert isinstance(tc["arguments"], dict)
        assert isinstance(tc["result"], dict)


class TestMCPFailure:
    def test_handles_mcp_exception(self, agent, mock_mcp):
        mock_mcp.submit_order.side_effect = RuntimeError("Connection refused")

        order_args = {"items": [{"item_id": "soda", "quantity": 1}]}
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Sorry, there was an error submitting your order.")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        result = agent.send("Yes")

        assert "tool_calls" in result
        tc = result["tool_calls"][0]
        assert tc["result"]["success"] is False
        assert "Connection refused" in tc["result"]["error"]

    def test_handles_mcp_failure_response(self, agent, mock_mcp):
        mock_mcp.submit_order.return_value = {
            "success": False,
            "error": "Order total ($55.00) exceeds $50 limit.",
        }

        order_args = {"items": [{"item_id": "margherita", "quantity": 5}]}
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Sorry, your order exceeds the $50 limit.")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        result = agent.send("Submit")

        assert result["tool_calls"][0]["result"]["success"] is False


class TestConversationHistory:
    def test_history_grows_with_each_send(self, agent):
        text_msg1 = _make_text_message("Got it!")
        text_msg2 = _make_text_message("Added!")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(text_msg1),
            _make_response(text_msg2),
        ]

        assert len(agent.history) == 0
        agent.send("Hello")
        # After first send: 1 user + 1 assistant = 2
        assert len(agent.history) == 2

        agent.send("I want fries")
        # After second send: 2 user + 2 assistant = 4
        assert len(agent.history) == 4

    def test_history_includes_tool_messages(self, agent, mock_mcp):
        order_args = {"items": [{"item_id": "soda", "quantity": 1}]}
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Order submitted!")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        agent.send("Yes, submit")

        # user + assistant(tool_call) + tool_result + assistant(final)
        assert len(agent.history) == 4
        roles = [m["role"] for m in agent.history]
        assert roles == ["user", "assistant", "tool", "assistant"]


class TestResponseFormat:
    def test_response_format_no_tool_calls(self, agent):
        text_msg = _make_text_message("What size burger?")
        agent._mistral_mock.chat.complete.return_value = _make_response(text_msg)

        result = agent.send("I want a burger")

        assert set(result.keys()) == {"message"}
        assert isinstance(result["message"], str)

    def test_response_format_with_tool_calls(self, agent, mock_mcp):
        order_args = {"items": [{"item_id": "classic_burger", "quantity": 1}]}
        tool_msg = _make_tool_call_message("submit_order", order_args)
        final_msg = _make_text_message("Your order is confirmed!")

        agent._mistral_mock.chat.complete.side_effect = [
            _make_response(tool_msg),
            _make_response(final_msg),
        ]

        result = agent.send("Submit")

        assert "message" in result
        assert "tool_calls" in result
        assert isinstance(result["message"], str)
        assert isinstance(result["tool_calls"], list)

        tc = result["tool_calls"][0]
        assert "name" in tc
        assert "arguments" in tc
        assert "result" in tc
