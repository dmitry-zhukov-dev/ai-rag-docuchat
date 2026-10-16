from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    """Small, dependency-free application settings for the initial skeleton."""

    app_name: str = os.getenv("APP_NAME", "DocuChat")
    app_description: str = os.getenv(
        "APP_DESCRIPTION",
        "Chat with your own documents",
    )
    app_version: str = os.getenv("APP_VERSION", "0.1.0")


settings = Settings()
