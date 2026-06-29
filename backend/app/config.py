"""Application configuration, loaded from environment variables (.env).

Secrets (Claude API key, JWT secret, login password) live ONLY here on the
backend. They must never be committed or returned to the browser.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Auth (single account) ---
    app_username: str = "admin"
    app_password: str = "change-me"          # plain text in .env; hashed in memory at startup
    jwt_secret: str = "dev-insecure-change-me"
    jwt_expire_hours: int = 720              # 30 days; single-user convenience

    # --- Database ---
    database_url: str = "sqlite:///./data/app.db"

    # --- Claude API (used by seed generator + later tools) ---
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-4-6"

    # --- SRS defaults ---
    daily_new_cards: int = 20

    # --- CORS: dev frontend origins ---
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
