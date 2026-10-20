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

    # Qdrant vector store
    qdrant_url: str = "http://localhost:6333"
    qdrant_collection: str = "documents"

    # File storage
    upload_dir: str = "uploads"
    max_file_size_mb: int = 10
    allowed_extensions: str = ".txt,.pdf"

    # Generation provider (Gemini)
    gemini_model: str = "gemini-3.8-flash"
    gemini_api_key: str = ""

    # Anonymous sessions and cookies
    session_cookie_name: str = "docuchat_session"
    session_lifetime_days: int = 30
    session_cookie_secure: bool = False
    session_cookie_httponly: bool = True
    session_cookie_samesite: str = "lax"

    # CORS (comma-separated origins; must be explicit when
    # credentials are used)
    cors_origins: str = "http://localhost,http://localhost:8000"

    # Optional Langfuse observability (disabled by
    # default; the RAG pipeline must work without it)
    langfuse_enabled: bool = False
    langfuse_public_key: str = ""
    langfuse_secret_key: str = ""
    langfuse_host: str = "https://cloud.langfuse.com"



settings = Settings()
