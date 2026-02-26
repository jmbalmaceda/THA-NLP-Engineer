"""Interactive CLI entry point for the food ordering agent."""

from agent import FoodOrderAgent


def main() -> None:
    agent = FoodOrderAgent()
    print("Food ordering agent ready. Type 'quit' or 'exit' to leave.\n")

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("quit", "exit"):
            print("Goodbye!")
            break

        response = agent.send(user_input)
        print(f"\nAgent: {response['message']}\n")


if __name__ == "__main__":
    main()
