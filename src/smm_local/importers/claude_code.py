"""Claude Code transcript JSONL to visible conversation messages."""

from pathlib import Path
from typing import Any, Iterable


class ClaudeCodeAdapter:
    name = "claude-code"

    def discover(self, root: Path) -> Iterable[Path]:
        return root.rglob("*.jsonl")

    def normalize(self, item: dict[str, Any], byte_offset: int) -> dict[str, Any] | None:
        kind = item.get("type")
        if kind not in {"user", "assistant"} or any(item.get(flag) is True for flag in ("isSidechain", "isMeta", "isCompactSummary")):
            return None
        message = item.get("message")
        if not isinstance(message, dict) or message.get("role") != kind:
            return None
        content = message.get("content")
        if isinstance(content, str):
            text = content
        elif isinstance(content, list):
            text = "\n".join(
                part["text"] for part in content
                if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str)
            )
        else:
            return None
        if not text.strip():
            return None
        return {
            "kind": "message", "session_id": item.get("sessionId"), "cwd": item.get("cwd"),
            "key": str(item.get("uuid") or f"offset:{byte_offset}"), "position": byte_offset,
            "role": kind, "text": text, "timestamp": item.get("timestamp"),
        }
