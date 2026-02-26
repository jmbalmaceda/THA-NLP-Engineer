"""Structured JSON conversation logger."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path


class ConversationLogger:
    def __init__(self, log_file: str = "conversation.log"):
        self.log_file = Path(log_file)
        # Also set up standard Python logging for errors/warnings
        logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
        self._logger = logging.getLogger(__name__)

    def log_turn(
        self,
        turn: int,
        role: str,
        content: str,
        tool_calls: list | None = None,
    ) -> None:
        """Write a structured JSON log line for a conversation turn."""
        entry: dict = {
            "turn": turn,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "role": role,
            "content": content,
        }
        if tool_calls:
            entry["tool_calls"] = tool_calls

        try:
            with self.log_file.open("a", encoding="utf-8") as f:
                f.write(json.dumps(entry) + "\n")
        except OSError as e:
            self._logger.error("Failed to write conversation log: %s", e)
