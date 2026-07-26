from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    app_name: str = "Research Alignment Agent"
    app_version: str = "1.0.0"
    debug: bool = False

    port: int = 8000

    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash-lite"
    gemini_embedding_model: str = "gemini-embedding-2"

    firebase_credentials_path: str = ""
    firebase_project_id: str = ""
    firebase_api_key: str = ""

    database_url: str = "sqlite:///./research_agent.db"
    chroma_db_path: str = ""
    chroma_collection: str = "research_papers_v12"

    cors_origins: list[str] = ["*"]

    upload_dir: str = "uploads"
    max_upload_size_mb: int = 20

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
