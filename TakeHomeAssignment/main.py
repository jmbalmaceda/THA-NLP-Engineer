"""Interactive CLI entry point for the food ordering agent.

Usage:
    python main.py                          # text mode (default)
    python main.py --voice                  # voice mode (default providers)
    python main.py --voice --stt whisper --tts say
    python main.py --voice --stt google  --tts edge
"""

import argparse

from agent import FoodOrderAgent


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Food ordering agent")
    parser.add_argument(
        "--voice",
        action="store_true",
        help="Enable voice mode: microphone input (STT) + spoken output (TTS)",
    )
    parser.add_argument(
        "--stt",
        metavar="PROVIDER",
        default=None,
        help="STT provider to use: whisper (default) | google  [overrides STT_PROVIDER env var]",
    )
    parser.add_argument(
        "--tts",
        metavar="PROVIDER",
        default=None,
        help="TTS provider to use: say (default) | pyttsx3 | edge  [overrides TTS_PROVIDER env var]",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()

    stt = tts = None
    if args.voice:
        from voice import get_stt_provider, get_tts_provider  # noqa: PLC0415
        stt = get_stt_provider(args.stt)
        tts = get_tts_provider(args.tts)

    agent = FoodOrderAgent()
    mode = "voice" if args.voice else "text"
    print(f"Food ordering agent ready [{mode} mode]. Type 'quit' or 'exit' to leave.\n")

    while True:
        try:
            if args.voice:
                cmd = input("Press Enter to record (or type 'quit'): ").strip().lower()
                if cmd in ("quit", "exit"):
                    print("Goodbye!")
                    break
                user_input = stt.listen().strip()
                if not user_input:
                    continue
            else:
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
        message = response["message"]
        print(f"\nAgent: {message}\n")

        if args.voice:
            tts.speak(message)


if __name__ == "__main__":
    main()
