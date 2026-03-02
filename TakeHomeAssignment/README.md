# Food Ordering Chatbot

An agentic, multi-turn conversational food ordering assistant built with Python, Mistral AI, and MCP (Model Context Protocol).

## Features

- Natural language order management — add, modify, and remove items across multiple turns
- Full menu validation (options, extras, prices) before any order is accepted
- Order confirmation flow with itemised total before submission
- Order submission via MCP Streamable HTTP (`submit_order` tool)
- Pluggable menu source — hardcoded (default) or MongoDB
- Structured JSON conversation logging to `conversation.log`
- **Voice mode** — speak your order and hear responses (optional, `--voice` flag)

## Setup

### 1. Clone and create a virtual environment

```bash
git clone <repo-url>
cd TakeHomeAssignment

python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Optional: install voice mode dependencies (--voice flag)
pip install -r requirements-voice.txt
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```
MISTRAL_API_KEY=your_mistral_api_key_here
APPLICANT_EMAIL=your_email@example.com
MISTRAL_MODEL=mistral-small-latest

# Menu source: 'static' (default) or 'mongodb'
MENU_SOURCE=static

# Required only when MENU_SOURCE=mongodb
MONGODB_URI=mongodb://localhost:27017
MONGODB_DB=food_ordering
MONGODB_COLLECTION=menu
```

- **`MISTRAL_API_KEY`** — get a free key at [console.mistral.ai](https://console.mistral.ai/)
- **`APPLICANT_EMAIL`** — sent as `X-Applicant-Email` header on every MCP request (required by the server)
- **`MISTRAL_MODEL`** — optional; defaults to `mistral-small-latest`
- **`MENU_SOURCE`** — optional; defaults to `static`

### 3. Run

```bash
# Text mode (default)
python main.py

# Voice mode — speak your order, hear responses
python main.py --voice                        # default providers: whisper STT + macOS say TTS
python main.py --voice --stt google           # Google STT (cloud, no key needed)
python main.py --voice --stt google --tts edge  # Google STT + Microsoft Edge TTS

# Run tests
python -m pytest tests/ -v
```

## Usage

### Text mode

```
$ python main.py
Food ordering agent ready [text mode]. Type 'quit' or 'exit' to leave.

You: I'd like a large classic burger with cheese and bacon
Agent: Large Classic Burger with cheese and bacon — $12.00. Anything else?

You: Remove the bacon
Agent: Updated: Large Classic Burger with cheese — $10.50. Anything else?

You: That's it
Agent: Your order:
  • Large Classic Burger with cheese — $10.50
Total: $10.50. Ready to submit?

You: Yes
Agent: Order submitted! Order #ORD-48271. Estimated time: 15-20 minutes.
```

### Programmatic API

```python
from agent import FoodOrderAgent

agent = FoodOrderAgent()

response = agent.send("I want a large burger with cheese")
print(response["message"])

response = agent.send("Yes, submit it")
print(response["message"])
print(response["tool_calls"])  # present only when submit_order was called
```

**`send()` return format:**

```python
# Normal turn (no submission)
{"message": "Large Classic Burger with cheese. Anything else?"}

# Order submitted
{
  "message": "Order submitted! Order #ORD-12345. Estimated time: 15-20 minutes.",
  "tool_calls": [
    {
      "name": "submit_order",
      "arguments": {
        "items": [{"item_id": "classic_burger", "quantity": 1, "options": {"size": "large"}, "extras": ["cheese"]}]
      },
      "result": {"success": true, "order_id": "ORD-12345", "total": 10.50, "estimated_time": "15-20 minutes"}
    }
  ]
}
```

## Project Structure

```
├── agent.py              # FoodOrderAgent — Mistral AI + tool-use loop
├── menu.py               # Menu dataclasses, Provider protocol, price calculation, validation
├── menu_mongodb.py       # MongoDB-backed menu provider
├── mcp_client.py         # Sync MCP client wrapper (submit_order + tool schema)
├── logger.py             # Structured JSON conversation logger
├── voice.py              # Voice I/O — STT and TTS providers (whisper, google, say, edge…)
├── main.py               # CLI entry point (text + voice modes)
├── requirements.txt
├── requirements-voice.txt  # Optional voice mode dependencies
├── .env.example
├── scripts/
│   └── seed_mongodb.py   # Seed the MongoDB menu collection
└── tests/
    ├── test_menu.py
    ├── test_agent.py
    └── test_mcp_client.py
```

## Menu

| Item | Base Price | Key Options |
|------|-----------|-------------|
| Classic Burger | $8.50 | size (regular/large), patty |
| Spicy Jalapeño Burger | $9.50 | size, spice level |
| Margherita Pizza | $12.00 | size (small/medium/large), crust |
| French Fries | $3.50 | size |
| Onion Rings | $4.50 | size |
| Soft Drink | $2.00 | size, flavor |
| Milkshake | $5.50 | size, flavor (required) |

Order total is capped at **$50** (enforced by the MCP server).

## Menu Sources

The menu source is selected via the `MENU_SOURCE` environment variable.

### Static (default)

The menu is defined as Python dataclasses in `menu.py`. No external dependencies required.

### MongoDB

Set `MENU_SOURCE=mongodb` and configure the connection variables, then seed the collection:

```bash
python scripts/seed_mongodb.py
```

The seed script reads `MENU` directly from `menu.py` and inserts one document per item, so it stays in sync with the static definition automatically.

To add a new menu source, implement a class with a `load() -> dict[str, MenuItem]` method and register it in `get_menu_provider()` in `menu.py`.

## Voice Mode

Run with `--voice` to interact through microphone and speakers instead of keyboard.

```
$ python main.py --voice --stt google
Food ordering agent ready [voice mode]. Type 'quit' or 'exit' to leave.

Press Enter to record (or type 'quit'):    ← press Enter to start
Recording… press Enter to stop.           ← speak your order
                                           ← press Enter to stop
Transcribing…
You said: I'd like a large classic burger with cheese
Agent: Large Classic Burger with cheese — $10.50. Anything else?  ← spoken aloud
```

### STT providers

| Name | `--stt` value | How it works | Deps |
|---|---|---|---|
| faster-whisper | `whisper` (default) | Local inference, no internet needed | `faster-whisper sounddevice soundfile` |
| Google Web Speech | `google` | Cloud API, no key required | `SpeechRecognition sounddevice soundfile` |

### TTS providers

| Name | `--tts` value | How it works | Deps |
|---|---|---|---|
| macOS say | `say` (default) | Built-in macOS `say` command | none |
| pyttsx3 | `pyttsx3` | Offline, cross-platform | `pyttsx3` |
| Microsoft Edge | `edge` | Cloud neural voices, high quality | `edge-tts` |

Providers can also be set via environment variables (`STT_PROVIDER`, `TTS_PROVIDER`) so no CLI flag is needed. See `.env.example` for all voice-related variables.

## Design Decisions

### Mistral AI for LLM
Mistral's free tier (`mistral-small-latest`) handles multi-turn dialogue and tool calling well without additional cost. The tool-use loop is two-stage: a first call that may return a `submit_order` tool call, and a second call (after the MCP result is appended to history) to produce the final user-facing message.

### MCP via Streamable HTTP
The `mcp` Python SDK's `streamablehttp_client` is async-only. `MCPClient` wraps it with `asyncio.run()` so the rest of the codebase stays synchronous and straightforward to test.

### Menu Provider pattern
The menu is loaded through a `MenuProvider` Protocol, allowing the data source to be swapped via `MENU_SOURCE` without changing any consumer code. `StaticMenuProvider` serves the hardcoded dataclasses; `MongoDBMenuProvider` fetches from a collection at startup. The `SUBMIT_ORDER_TOOL` schema lives in `mcp_client.py` alongside the client that implements it.

### Stateful conversation history
`FoodOrderAgent` maintains a `history` list in Mistral's message format. The system prompt (injected on every call but not stored in history) includes the full menu, rules, and pricing logic — letting the LLM handle order state tracking naturally through conversation context.

### Confirmation gate
The system prompt defines a strict two-step flow: first build the order, then show a full summary with the total and ask for explicit confirmation before calling `submit_order`. Phrases like "that's all" or "no" to "anything else?" close step one but do not trigger submission.
