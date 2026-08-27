"""Loads and assembles the system prompt sent to the LLM."""
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent.parent / "prompts"


def _read(filename: str) -> str:
    path = PROMPTS_DIR / filename
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def build_system_prompt() -> str:
    """
    Combines base system rules + persona + safety notes into one system prompt.
    Edit prompts/persona.txt to control tone/personality - it's plain text,
    no code changes needed.
    """
    parts = [
        _read("system.txt"),
        _read("persona.txt"),
        _read("safety.txt"),
    ]
    return "\n\n".join(p for p in parts if p)


def get_fallback_message() -> str:
    return _read("fallback.txt") or "Sorry, thoda busy hoon abhi — thodi der me reply karta hoon!"
