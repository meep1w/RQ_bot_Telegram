import os
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", ".env"),
        env_file_encoding="utf-8",
    )
    GA_BOT_TOKEN: str
    GA_ADMIN_IDS: str
    GROUP_ID: int
    WEB_BASE: str
    WEBHOOK_SECRET_SALT: str
    DATABASE_URL: str
    ENV: str = "prod"
    USE_WEBHOOK: bool = True
    CERT_PATH: str = "/etc/ssl/certs/multibot.crt"

settings = Settings()
ADMIN_IDS = {int(x.strip()) for x in settings.GA_ADMIN_IDS.split(",") if x.strip()}
