## Build an Agentic Food Ordering Chatbot

### Overview

Build a conversational agent that takes food orders through natural language dialogue. The agent must handle the full order lifecycle — adding items, modifying them, removing them, and submitting the final order via a provided MCP tool.

---

### Menu Schema

Your agent should parse this menu and use it to validate orders and calculate totals.

``` yaml
menu:
  # ----- BURGERS -----
  - id: classic_burger
    name: Classic Burger
    base_price: 8.50
    options:
      size:
        type: single_choice
        required: true
        choices: [regular, large]
        default: regular
        price_modifier:
          regular: 0
          large: 2.00
      patty:
        type: single_choice
        required: false
        choices: [beef, chicken, veggie]
        default: beef
    extras:
      type: multi_choice
      choices:
        - id: cheese
          price: 1.00
        - id: bacon
          price: 1.50
        - id: avocado
          price: 2.00
        - id: extra_patty
          price: 3.00

  - id: spicy_burger
    name: Spicy Jalapeño Burger
    base_price: 9.50
    options:
      size:
        type: single_choice
        required: true
        choices: [regular, large]
        default: regular
        price_modifier:
          regular: 0
          large: 2.00
      spice_level:
        type: single_choice
        required: false
        choices: [mild, medium, hot, extra_hot]
        default: medium
    extras:
      type: multi_choice
      choices:
        - id: cheese
          price: 1.00
        - id: bacon
          price: 1.50
        - id: jalapeños
          price: 0.75

  # ----- PIZZAS -----
  - id: margherita
    name: Margherita Pizza
    base_price: 12.00
    options:
      size:
        type: single_choice
        required: true
        choices: [small, medium, large]
        default: medium
        price_modifier:
          small: -2.00
          medium: 0
          large: 4.00
      crust:
        type: single_choice
        required: false
        choices: [thin, regular, thick]
        default: regular
    extras:
      type: multi_choice
      choices:
        - id: extra_cheese
          price: 2.00
        - id: olives
          price: 1.50
        - id: mushrooms
          price: 1.50
        - id: pepperoni
          price: 2.00

  # ----- SIDES -----
  - id: fries
    name: French Fries
    base_price: 3.50
    options:
      size:
        type: single_choice
        required: true
        choices: [small, medium, large]
        default: medium
        price_modifier:
          small: -1.00
          medium: 0
          large: 1.50
    extras:
      type: multi_choice
      choices:
        - id: truffle_oil
          price: 2.00
        - id: parmesan
          price: 1.00
        - id: cheese_sauce
          price: 1.50

  - id: onion_rings
    name: Onion Rings
    base_price: 4.50
    options:
      size:
        type: single_choice
        required: true
        choices: [small, medium, large]
        default: medium
        price_modifier:
          small: -1.00
          medium: 0
          large: 1.50
    extras:
      type: multi_choice
      choices:
        - id: ranch_dip
          price: 0.75
        - id: spicy_mayo
          price: 0.75

  # ----- DRINKS -----
  - id: soda
    name: Soft Drink
    base_price: 2.00
    options:
      size:
        type: single_choice
        required: true
        choices: [small, medium, large]
        default: medium
        price_modifier:
          small: -0.50
          medium: 0
          large: 0.75
      flavor:
        type: single_choice
        required: true
        choices: [cola, diet_cola, lemon_lime, orange]
        default: cola

  - id: milkshake
    name: Milkshake
    base_price: 5.50
    options:
      size:
        type: single_choice
        required: true
        choices: [regular, large]
        default: regular
        price_modifier:
          regular: 0
          large: 2.00
      flavor:
        type: single_choice
        required: true
        choices: [vanilla, chocolate, strawberry, oreo]
    extras:
      type: multi_choice
      choices:
        - id: whipped_cream
          price: 0.50
        - id: cherry_on_top
          price: 0.25

```

### MCP Tool

We provide an MCP server with a single tool: `submit_order`. Your agent must connect to this server and call the tool when the user confirms their order.

**Server URL** (Streamable HTTP transport):

```
https://webviews-git-moveo-food-nlp-assignment-moveo-ai.vercel.app/api/demo/mcp
```

⚠️ IMPORTANT: You must include the header X-Applicant-Email with your email (the one listed in your CV) in all requests to the MCP server. The tool will not work without this header.

**Tool: `submit_order`**

**Input Schema:**

``` json
{
  "name": "submit_order",
  "description": "Submit the final food order",
  "inputSchema": {
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
              "description": "Menu item ID (e.g., classic_burger, margherita, fries)"
            },
            "quantity": {
              "type": "integer",
              "description": "Number of this item",
              "default": 1
            },
            "options": {
              "type": "object",
              "description": "Item options (e.g., size, patty, crust, flavor)"
            },
            "extras": {
              "type": "array",
              "description": "List of extra IDs for this item",
              "items": { "type": "string" }
            }
          },
          "required": ["item_id", "quantity"]
        }
      },
      "special_instructions": {
        "type": "string",
        "description": "Any special instructions for the order"
      }
    },
    "required": ["items"]
  }
}

```

Example Input:

``` json
{
  "items": [
    {
      "item_id": "classic_burger",
      "quantity": 1,
      "options": {"size": "large", "patty": "beef"},
      "extras": ["cheese", "bacon"]
    }
  ],
  "special_instructions": "No onions please"
}
```

Example Output (success):

``` json
{
  "success": true,
  "order_id": "ORD-12345",
  "total": 13.00,
  "estimated_time": "15-20 minutes"
}
```

Example Output (failure):

``` json
{
  "success": false,
  "error": "Order total ($52.00) exceeds $50 limit."
}
```

The server may return failures for various reasons (e.g., order exceeds limit, kitchen busy, internal errors, etc.).

---

### Example Conversations

**Example 1: Simple order with modification**

```
User: I'd like a large classic burger with cheese and bacon
Agent: Large Classic Burger with cheese and bacon. Anything else?
User: Actually, remove the bacon
Agent: Updated: Large Classic Burger with cheese. Anything else?
User: That's it
Agent: Your order: Large Classic Burger with cheese — $11.50. Ready to submit?
User: Yes
Agent: Order submitted! Order #ORD-48271. Estimated time: 15-20 minutes.

```

**Example 2: Multiple items**

```
User: I want a medium margherita with olives, large fries with parmesan, and a cola
Agent: Medium Margherita Pizza with olives, Large French Fries with parmesan, and Medium Cola. Anything else?
User: Make the cola large
Agent: Updated: Large Cola. Your total is $20.25. Ready to submit?
User: Submit
Agent: Order submitted! Order #ORD-55102.
```

### Requirements

| # | Requirement |
| --- | --- |
| 1 | Parse the menu schema and use it to validate orders |
| 2 | Support **adding**, **modifying**, and **removing** items |
| 3 | Confirm the order with the user before submission |
| 4 | Call `submit_order` via MCP and handle the response |
| 5 | Log each conversation turn in a structured format |
| 6 | Provide two entry points (see below) |
| 7 | Document setup and design decisions in the README |

---

### Agent Interface

Your agent must be usable in two ways:

**1. Interactive mode**

``` bash
python main.py
```

**2. Programmatic API**

``` python
from agent import FoodOrderAgent

agent = FoodOrderAgent()

response = agent.send("I want a large burger with cheese")
response = agent.send("Actually make it regular")
response = agent.send("Submit")
response = agent.send("Yes")
```

### Code Structure:

```
your-repo/
├── agent.py          # Must export FoodOrderAgent class
├── main.py           # Interactive entry point
├── ...
```

**Required method:**

| Method | Description |
| --- | --- |
| `send(message: str) -> dict` | Process user message, return response (see format below) |

**Response format:**

The `send()` method must return a dict with the following structure:

```python
{
  "message": str,         # Required: the agent's response to the user
  "tool_calls": [         # Optional: list of tool calls made this turn
    {
      "name": str,        # Tool name (e.g., "submit_order")
      "arguments": dict,  # Arguments passed to the tool
      "result": dict      # Result returned by the tool
    }
  ]
}
```

**Examples:**

*User adds an item (no tool calls):*

```python
agent.send("I want a large burger with cheese")
# Returns:
{
  "message": "Large Classic Burger with cheese. Anything else?"
}
```

```python

```

*User modifies the order (no tool calls):*

```python
agent.send("Actually make it regular")
# Returns:
{
  "message": "Updated: Regular Classic Burger with cheese. Anything else?"
}
```

*User confirms and order is submitted (tool call):*

```python
agent.send("Yes")
# Returns:
{
  "message": "Order submitted! Order #ORD-12345. Estimated time: 15-20 minutes.",
  "tool_calls": [
    {
      "name": "submit_order",
      "arguments": {
        "items": [
          {
            "item_id": "classic_burger",
            "quantity": 1,
            "options": {"size": "regular"},
            "extras": ["cheese"]
          }
        ],
        "special_instructions": null
      },
      "result": {
        "success": true,
        "order_id": "ORD-12345",
        "total": 9.50,
        "estimated_time": "15-20 minutes"
      }
    }
  ]
}
```

*Order submission fails (tool call with failure):*

```python
agent.send("Yes")
# Returns:
{
  "message": "Sorry, the order couldn't be submitted — the kitchen is busy. Would you like me to try again?",
  "tool_calls": [
    {
      "name": "submit_order",
      "arguments": {
        "items": [...]
      },
      "result": {
        "success": false,
        "error": "Kitchen is currently busy. Please try again."
      }
    }
  ]
}
```

---

### Deliverables

Item	Format
Source code	Public GitHub repo with the above specs
README	Setup, usage, design decisions

### Technical Notes

- **LLM**: Use any provider you prefer. [Mistral's free tier](https://console.mistral.ai/) is a zero-cost option if needed.
- **Coding tools**: You are allowed (and encouraged) to use LLM-powered coding assistants to help you with this assignment.
- In case of voice agent (bonus — optional), [Elevenlabs](https://elevenlabs.io/pricing) offers also zero-cost option for TTS/STT
- **MCP**: Implement a client to connect to the server — see [modelcontextprotocol.io](https://modelcontextprotocol.io/)
- **Language**: Python 3.10+