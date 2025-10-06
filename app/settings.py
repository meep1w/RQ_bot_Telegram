from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    GA_BOT_TOKEN: str
    GA_ADMIN_IDS: str  # comma-separated
    GROUP_ID: int

    WEB_BASE: str
    WEBHOOK_SECRET_SALT: str

    DATABASE_URL: str
    ENV: str = "dev"

    @field_validator("GA_ADMIN_IDS")
    @classmethod
    def parse_admins(cls, v: str):
        # keep raw; split where needed
        return v

settings = Settings()

ADMIN_IDS = {int(x.strip()) for x in settings.GA_ADMIN_IDS.split(',') if x.strip()}