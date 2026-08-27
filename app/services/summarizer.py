"""
Optional: summarizes older parts of a long conversation so context doesn't
grow unbounded. Not called automatically - wire it in conversation.py if/when
a thread gets long (e.g. > MAX_HISTORY_MESSAGES * 3).
"""
from app.ai.gemini import call_gemini

SUMMARY_SYSTEM_PROMPT = (
    "Summarize the following conversation between a user and an assistant in "
    "3-4 short bullet points, focused on facts and preferences worth remembering. "
    "Be concise. Output plain text only."
)


async def summarize_history(history: list[dict]) -> str:
    convo_text = "\n".join(f"{h['role']}: {h['content']}" for h in history)
    summary = await call_gemini(SUMMARY_SYSTEM_PROMPT, [], convo_text)
    return summary
