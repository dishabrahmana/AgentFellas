from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Telegram
    telegram_bot_token: str = Field(validation_alias="TELEGRAM_BOT_TOKEN")
    telegram_user_id: str = Field(validation_alias="TELEGRAM_USER_ID")

    # DeepSeek
    deepseek_api_key: str = Field(validation_alias="DEEPSEEK_API_KEY")
    deepseek_api_url: str = "https://api.deepseek.com/v1"

    # Gemini (optional fallback)
    gemini_api_key: str | None = None

    # Database
    database_url: str = "sqlite+aiosqlite:///data/worktracker.db"

    # Logging
    log_level: str = "INFO"
    log_dir: str = "./logs"

    # Gmail (optional)
    gmail_credentials_file: str | None = None

    # Device
    device_token: str | None = None

    # Timezone
    tz: str = "Asia/Jakarta"

    # Admin IDs
    admin_ids: str | None = None

    @property
    def admin_id_list(self) -> list[int]:
        if not self.admin_ids:
            return []
        return [int(x.strip()) for x in self.admin_ids.split(",") if x.strip()]

    @field_validator("log_dir")
    @classmethod
    def resolve_log_dir(cls, v: str) -> Path:
        p = Path(v)
        p.mkdir(parents=True, exist_ok=True)
        return p

    @field_validator("database_url")
    @classmethod
    def ensure_db_dir(cls, v: str) -> str:
        if v.startswith("sqlite"):
            path_part = v.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
            if path_part:
                Path(path_part).parent.mkdir(parents=True, exist_ok=True)
        return v


settings = Settings()
