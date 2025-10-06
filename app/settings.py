from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="/opt/multibot/.env",  # на сервере. локально можно ".env"
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

settings = Settings()
ADMIN_IDS = {int(x.strip()) for x in settings.GA_ADMIN_IDS.split(",") if x.strip()}
