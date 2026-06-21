from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Google OAuth
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str = "http://localhost:8000/auth/callback"

    # Research APIs
    tavily_api_key: str

    # AWS Bedrock
    aws_access_key_id: str
    aws_secret_access_key: str
    aws_region: str = "eu-north-1"
    bedrock_model: str = "eu.anthropic.claude-haiku-4-5-20251001-v1:0"

    # LangSmith tracing
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "meetiq"

    # App
    secret_key: str
    frontend_url: str = "http://localhost:5173"

    # Guardrail tuning
    tavily_max_searches: int = 5
    scraper_timeout_s: int = 5
    tavily_timeout_s: int = 10
    research_timeout_s: int = 60
    cb_fail_threshold: int = 3       # circuit breaker: open after N failures
    cb_recovery_s: int = 300         # circuit breaker: recover after N seconds
    rate_limit_per_min: int = 10

    # Logging
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


# Single instance imported everywhere
# Usage: from meetiq.config.settings import settings
settings = Settings()
