"""Shared constants across the app."""

GRAPH_API_VERSION = "v21.0"
GRAPH_API_BASE = f"https://graph.facebook.com/{GRAPH_API_VERSION}"

PROVIDER_GEMINI = "gemini"
PROVIDER_GROQ = "groq"

# Tried in this order per key - if a (key, model) combo hits its rate limit,
# the next model in the list is tried with the SAME key before moving to the
# next key (since Gemini/Groq quotas are often per model, not just per key).
GEMINI_MODELS = [
    "gemini-3.6-flash",
    "gemini-3-flash-preview",
    "gemini-3.5-flash",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
]
GROQ_MODELS = ["qwen/qwen3.8-27b", "qwen/qwen3.6-27b"]

IG_MESSAGING_FIELD = "messaging"

MAX_REPLY_CHARS = 1000  # Instagram DM practical limit safety margin
