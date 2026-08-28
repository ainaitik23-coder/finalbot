"""
Central app configuration. Loads from .env via pydantic-settings.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Meta / Instagram
    IG_VERIFY_TOKEN: str
    IG_PAGE_ACCESS_TOKEN: str
    IG_APP_SECRET: str

    # LLM provider - comma-separated, as many as you want.
    GEMINI_API_KEYS: str = ""
    GROQ_API_KEYS: str = ""
    # App behavior
    DATABASE_URL: str = "sqlite+aiosqlite:///./memory/chat.db"
    LOG_LEVEL: str = "INFO"
    MAX_HISTORY_MESSAGES: int = 20

    PRIMARY_USER_ID: str = ""

    @property
    def gemini_keys_list(self) -> list[str]:
        return [k.strip() for k in self.GEMINI_API_KEYS.split(",") if k.strip()]


settings = Settings()
