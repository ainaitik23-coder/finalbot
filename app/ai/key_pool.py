"""
Rotates across every (key, model) combination you configure, in this fixed
nested order:

  for each Gemini key (in .env order):
      for each Gemini model (GEMINI_MODELS order, in constants.py)
  for each Groq key (in .env order):
      for each Groq model (GROQ_MODELS order, in constants.py)

So with keys [k1, k2] and models [m1, m2, m3], the order is:
  k1+m1 -> k1+m2 -> k1+m3 -> k2+m1 -> k2+m2 -> k2+m3

If a (key, model) combo hits its rate limit (HTTP 429), only that specific
combo goes on cooldown - the same key immediately tries its next model
before the pool ever moves on to a different key (Gemini/Groq quotas are
often per model, not just per key, so a key exhausted on one model can
often still serve a different model). Conversation history/memory is
completely untouched by any of this.

Add/remove keys any time in .env (GEMINI_API_KEYS / GROQ_API_KEYS,
comma-separated) or change the model lists in constants.py - no other code
changes needed, and there's no hard limit on how many keys or models you list.
"""
import logging
import time
from dataclasses import dataclass

from app.config import settings
from app.utils.constants import (
    PROVIDER_GEMINI,
    PROVIDER_GROQ,
    GEMINI_MODELS,
    GROQ_MODELS,
)

logger = logging.getLogger("key_pool")

# Free-tier quotas on Gemini/Groq are typically daily - cool a (key, model)
# combo down for 24h after it 429s, then let the pool try it again automatically.
COOLDOWN_SECONDS = 24 * 60 * 60


@dataclass
class KeySlot:
    provider: str
    key: str
    model: str
    exhausted_until: float = 0.0

    def is_available(self) -> bool:
        return time.time() >= self.exhausted_until

    def mark_exhausted(self, cooldown: int = COOLDOWN_SECONDS) -> None:
        self.exhausted_until = time.time() + cooldown


class KeyPool:
    def __init__(self):
        self._slots: list[KeySlot] = []
        self._cursor = 0
        self._build()

    def _build(self) -> None:
        self._slots = []
        for k in settings.gemini_keys_list:
            for m in GEMINI_MODELS:
                self._slots.append(KeySlot(provider=PROVIDER_GEMINI, key=k, model=m))
        for k in settings.groq_keys_list:
            for m in GROQ_MODELS:
                self._slots.append(KeySlot(provider=PROVIDER_GROQ, key=k, model=m))
        logger.info(
            f"Key pool built: {len(settings.gemini_keys_list)} Gemini key(s) x "
            f"{len(GEMINI_MODELS)} model(s), {len(settings.groq_keys_list)} Groq "
            f"key(s) x {len(GROQ_MODELS)} model(s) = {len(self._slots)} total slots"
        )

    def slot_count(self) -> int:
        return len(self._slots)

    def next_slot(self) -> KeySlot | None:
        """
        Returns the next available (key, model) slot, walking the fixed
        nested order starting from the current cursor, and advances the
        cursor past it. Returns None if every combo is currently on cooldown.
        """
        n = len(self._slots)
        if n == 0:
            return None
        for i in range(n):
            idx = (self._cursor + i) % n
            slot = self._slots[idx]
            if slot.is_available():
                self._cursor = (idx + 1) % n
                return slot
        return None

    def mark_exhausted(self, provider: str, key: str, model: str) -> None:
        for slot in self._slots:
            if slot.provider == provider and slot.key == key and slot.model == model:
                slot.mark_exhausted()
                logger.warning(
                    f"Combo exhausted, cooling down: {provider}/{model} ...{key[-4:]}"
                )
                return

    def all_exhausted(self) -> bool:
        return all(not s.is_available() for s in self._slots) if self._slots else True


key_pool = KeyPool()
