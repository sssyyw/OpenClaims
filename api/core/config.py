import os

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "postgresql+asyncpg://localhost:5432/claims_intelligence"
    anthropic_api_key: str = os.environ.get("ANTHROPIC_API_KEY", "")
    openai_api_key: str = os.environ.get("OPENAI_API_KEY", "")

    # Embedding config
    embedding_model: str = "text-embedding-3-large"
    embedding_dimensions: int = 1536  # text-embedding-3-large supports native dim reduction

    # LLM config
    llm_model: str = "claude-sonnet-4-20250514"
    llm_max_concurrent: int = 5
    llm_timeout_seconds: int = 30

    # Retrieval config
    retrieval_top_k: int = 10

    model_config = {"env_prefix": "CI_", "env_file": ".env"}


settings = Settings()
