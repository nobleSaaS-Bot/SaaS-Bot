from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    APP_NAME: str = "SaaS Bot Platform"
    DEBUG: bool = False
    SECRET_KEY: str = "change-me-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24

    DATABASE_URL: str = "postgresql://user:password@localhost:5432/saasbot"

    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    TELEGRAM_BOT_TOKEN: str = ""
    TELEGRAM_WEBHOOK_SECRET: str = ""

    STRIPE_SECRET_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    TELEBIRR_APP_ID: str = ""
    TELEBIRR_APP_KEY: str = ""
    TELEBIRR_PUBLIC_KEY: str = ""
    TELEBIRR_SHORT_CODE: str = ""
    TELEBIRR_NOTIFY_URL: str = ""

    MPESA_CONSUMER_KEY: str = ""
    MPESA_CONSUMER_SECRET: str = ""
    MPESA_SHORTCODE: str = ""
    MPESA_PASSKEY: str = ""
    MPESA_CALLBACK_URL: str = ""

    OPENAI_API_KEY: str = ""

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
