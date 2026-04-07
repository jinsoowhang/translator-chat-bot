"""Settings loader — combines .env secrets with config.yaml language rules."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Secrets and server config loaded from environment / .env."""

    whapi_token: str
    whapi_base_url: str = "https://gate.whapi.cloud"
    webhook_secret: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


class LanguagePair(BaseModel):
    source: list[str]
    target: str


class BotConfig(BaseModel):
    """Language routing rules loaded from config.yaml."""

    language_pairs: list[LanguagePair]
    bot_name: str
    claude_model: str
    language_labels: dict[str, str] = Field(default_factory=dict)

    def target_for(self, source_lang: str) -> str | None:
        """Given a detected source language code, return the target language code."""
        code = source_lang.lower()
        for pair in self.language_pairs:
            if code in (s.lower() for s in pair.source):
                return pair.target
        return None

    def label(self, lang_code: str) -> str:
        return self.language_labels.get(lang_code.lower(), lang_code.upper())


def load_bot_config(path: str | Path = "config.yaml") -> BotConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return BotConfig(**data)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


@lru_cache(maxsize=1)
def get_bot_config() -> BotConfig:
    return load_bot_config()
