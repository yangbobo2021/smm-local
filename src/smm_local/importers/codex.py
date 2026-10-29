"""Codex rollout JSONL to stable session/message events."""

from pathlib import Path
from typing import Any, Iterable


def _text_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    chunks: list[str] = []
    for part in content:
        if isinstance(part, dict) and part.get("type") in {"input_text", "output_text", "text"}:
            value = part.get("text")
            if isinstance(value, str):
                chunks.append(value)
    return "\n".join(chunks)


def _injected_context(text: str) -> bool:
    return text.startswith(("# AGENTS.md instructions for ", "<environment_context>",
                            "<external_codex_apps_open_page>"))


class CodexAdapter:
    name = "codex"

    def discover(self, root: Path) -> Iterable[Path]:
        return root.rglob("*.jsonl")

    def normalize(self, item: dict[str, Any], byte_offset: int) -> dict[str, Any] | None:
        payload = item.get("payload")
        if not isinstance(payload, dict):
            return None
        if item.get("type") == "session_meta":
            return {"kind": "session", "session_id": payload.get("id") or payload.get("session_id"), "cwd": payload.get("cwd"), "timestamp": item.get("timestamp")}
        if item.get("type") == "response_item" and payload.get("type") == "message" and payload.get("role") in {"user", "assistant"}:
            text = _text_content(payload.get("content"))
            if text.strip() and not (payload["role"] == "user" and _injected_context(text)):
                return {"kind": "message", "key": str(payload.get("id") or f"offset:{byte_offset}"), "position": int(item.get("ordinal") or byte_offset), "role": payload["role"], "text": text, "timestamp": item.get("timestamp")}
        return None
