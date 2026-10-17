from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Application metadata
    app_name: str = "DocuChat"
    app_description: str = "Chat with your own documents"
    app_version: str = "0.1.0"

    # PostgreSQL connection
    database_url: str = "postgresql+psycopg2://docuchat:docuchat@localhost:5433/docuchat"


settings = Settings()
