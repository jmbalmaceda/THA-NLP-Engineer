# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A multi-turn agentic food ordering chatbot using **Mistral AI** and MCP (Model Context Protocol). The agent manages order lifecycle (add/modify/remove items, then submit) through natural conversation.

Full assignment spec: `description.md`.

## Setup & Running

```bash
# Create and activate virtualenv
python3 -m venv .venv && source .venv/bin/activate

# Install core dependencies
pip install -r requirements.txt

# Install voice dependencies (only needed for --voice flag)
pip install -r requirements-voice.txt

# Copy and fill in secrets
cp .env.example .env

# Run in text mode (default)
python main.py

# Run in voice mode
python main.py --voice
python main.py --voice --stt google --tts say

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_menu.py -v

# Seed MongoDB (only if MENU_SOURCE=mongodb)
python scripts/seed_mongodb.py
```

## Environment Variables (`.env`)

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `MISTRAL_API_KEY` | Yes | — | Mistral AI API key |
| `APPLICANT_EMAIL` | Yes | — | Sent as `X-Applicant-Email` header on MCP calls |
| `MISTRAL_MODEL` | No | `mistral-small-latest` | Mistral model ID |
| `MENU_SOURCE` | No | `static` | `static` or `mongodb` |
| `MONGODB_URI` | If MongoDB | `mongodb://localhost:27017` | MongoDB connection string |
| `MONGODB_DB` | No | `food_ordering` | MongoDB database name |
| `MONGODB_COLLECTION` | No | `menu` | MongoDB collection name |
| `STT_PROVIDER` | No | `whisper` | Voice STT backend: `whisper` or `google` |
| `TTS_PROVIDER` | No | `say` | Voice TTS backend: `say`, `pyttsx3`, or `edge` |
| `WHISPER_MODEL` | No | `base` | faster-whisper model size: `tiny`, `base`, `small`, `medium`, `large` |
| `SAY_VOICE` | No | system default | macOS voice name (e.g. `Samantha`) |
| `SAY_RATE` | No | system default | macOS say speaking rate in WPM |
| `EDGE_TTS_VOICE` | No | `en-US-JennyNeural` | Edge TTS BCP-47 voice name |

## Architecture

### Data flow per `send()` call

```
user message
  → append to history
  → Mistral call 1 (system prompt + full history + SUBMIT_ORDER_TOOL schema)
      → if tool_call returned:
          → MCPClient.submit_order() [asyncio.run wrapping async MCP SDK]
          → append tool result to history
          → Mistral call 2 (same history + tool result) → final text
      → else: use call-1 text as reply
  → ConversationLogger.log_turn() → conversation.log (JSON lines)
  → return {"message": str, "tool_calls": [...]}  # tool_calls only on submission
```

### Key design decisions

- **System prompt not in history** — injected fresh on every Mistral call but never appended to `self.history`. The system prompt embeds the full rendered menu text.
- **Synchronous surface, async internals** — `MCPClient.submit_order()` calls `asyncio.run()` around the async `mcp` SDK, keeping everything else synchronous and easy to test.
- **Menu loaded at import time** — `menu.py` calls `get_menu_provider().load()` at module level, populating the module-level `MENU` dict. Swapping sources requires a process restart.
- **MenuProvider Protocol** — `StaticMenuProvider` (default) and `MongoDBMenuProvider` both satisfy `MenuProvider`. Add new sources by implementing `load() -> dict[str, MenuItem]` and registering in `get_menu_provider()`.
- **Two-step confirmation gate** — The system prompt enforces: (1) build order, (2) show full summary + total + ask explicit confirmation, then and only then call `submit_order`. "That's all" closes step 1, it does not confirm.
- **Voice as a pure I/O layer** — `voice.py` sits entirely outside `agent.py`. `FoodOrderAgent.send()` works with plain strings; voice is handled by `main.py` wrapping STT before and TTS after each call. Adding or removing voice requires zero changes to agent logic.

### Module responsibilities

| File | Responsibility |
|---|---|
| `agent.py` | `FoodOrderAgent` — Mistral client, conversation history, tool-call loop |
| `menu.py` | Dataclasses (`MenuItem`, `OptionSpec`, `ExtraSpec`), `MenuProvider` Protocol, `calculate_price()`, `validate_item()`, `render_menu_text()` |
| `menu_mongodb.py` | `MongoDBMenuProvider` — fetches menu from MongoDB at call time |
| `mcp_client.py` | `MCPClient` (sync wrapper) + `SUBMIT_ORDER_TOOL` schema dict |
| `logger.py` | `ConversationLogger` — appends JSON lines to `conversation.log` |
| `voice.py` | STT/TTS Protocol + implementations (`WhisperSTT`, `GoogleSTT`, `MacSayTTS`, `Pyttsx3TTS`, `EdgeTTS`) + `get_stt_provider()` / `get_tts_provider()` factories |
| `main.py` | CLI entry point — text mode and voice mode (`--voice`, `--stt`, `--tts` flags) |
| `scripts/seed_mongodb.py` | Drops and recreates the MongoDB menu collection from `MENU` |

## MCP Integration

- **Server URL**: `https://webviews-git-moveo-food-nlp-assignment-moveo-ai.vercel.app/api/demo/mcp`
- **Transport**: Streamable HTTP (`mcp.client.streamable_http`)
- **Tool**: `submit_order(items, special_instructions?)`
- **Header**: `X-Applicant-Email` required on every request
- **Limit**: $50 order total (server-enforced)

## Testing

Tests use `unittest.mock` to patch `Mistral` and inject a mock `MCPClient`. No real API calls are made.

```python
# Pattern: inject mock_mcp, patch agent.Mistral, control chat.complete.return_value
agent._mistral_mock.chat.complete.side_effect = [first_response, second_response]
```

`test_menu.py` tests `calculate_price` and `validate_item` with no mocking needed.
