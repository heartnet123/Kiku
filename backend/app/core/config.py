from dataclasses import dataclass
import os
from dotenv import load_dotenv

# Automatically load environment variables from .env file
load_dotenv()


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("KIKU_APP_NAME", "Kiku API")
    api_prefix: str = "/api/v1"
    frontend_origin: str = os.getenv("KIKU_FRONTEND_ORIGIN", "http://localhost:5173")
    supabase_url: str = os.getenv("SUPABASE_URL", "")
    supabase_key: str = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_ANON_KEY", "")
    supabase_service_role_key: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")

    # Session cookies ride TLS whenever the frontend is served over HTTPS.
    cookie_secure: bool = (
        os.getenv("KIKU_COOKIE_SECURE") or ""
    ).strip().lower() in {"1", "true", "yes"} or os.getenv(
        "KIKU_FRONTEND_ORIGIN", "http://localhost:5173"
    ).startswith("https://")
    
    environment: str = os.getenv("KIKU_ENV", "development").strip().lower()
    enable_openapi: bool = (os.getenv("KIKU_ENABLE_OPENAPI") or "").strip().lower() in {"1", "true", "yes"} or environment != "production"
    
    # Opencode LLM Synthesis Configuration
    opencode_api_base_url: str = os.getenv("OPENCODE_API_BASE_URL", "https://opencode.ai/zen/v1")
    opencode_api_key: str = os.getenv("OPENCODE_API_KEY", "")
    opencode_llm_model: str = os.getenv("OPENCODE_LLM_MODEL", "deepseek-v4-flash-free")
    
    # OpenAI Embeddings Configuration
    openai_embedding_model: str = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", os.getenv("OPENCODE_API_KEY", ""))
    openai_api_base_url: str = os.getenv("OPENAI_API_BASE_URL", "https://api.openai.com/v1")


settings = Settings()


def validate_runtime_settings() -> None:
    if settings.environment == "production" and settings.frontend_origin.startswith("http://localhost"):
        raise RuntimeError("KIKU_FRONTEND_ORIGIN must be set to a production origin when KIKU_ENV=production.")
