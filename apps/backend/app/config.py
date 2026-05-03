from pydantic_settings import BaseSettings
from typing import List
import os


class Settings(BaseSettings):
    APP_NAME: str = "SaaS Bot Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/saasbot"

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000", "*"]

    # Telegram
    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    # The public base URL of this API — used to build webhook URLs for Telegram.
    # In production set this to e.g. https://api.yourdomain.com
    # In Replit dev it's auto-derived from REPLIT_DOMAINS if not set explicitly.
    API_BASE_URL: str = ""

    # Optional explicit Fernet key (base64url-encoded 32-byte key).
    # If not set, the key is derived from SECRET_KEY via SHA-256.
    ENCRYPTION_KEY: str = ""

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Telebirr
    TELEBIRR_APP_ID: str = ""
    TELEBIRR_APP_KEY: str = ""
    TELEBIRR_PUBLIC_KEY: str = ""
    TELEBIRR_SHORT_CODE: str = ""
    TELEBIRR_NOTIFY_URL: str = ""

    # M-Pesa
    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_CALLBACK_URL: str = ""

    # OpenAI
    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True

    @property
    def resolved_api_base_url(self) -> str:
        """Return API_BASE_URL, falling back to the Replit dev domain."""
        if self.API_BASE_URL:
            return self.API_BASE_URL.rstrip("/")
        replit_domains = os.environ.get("REPLIT_DOMAINS", "")
        if replit_domains:
            primary = replit_domains.split(",")[0].strip()
            return f"https://{primary}"
        return "http://localhost:8080"


settings = Settings()
