from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("KIKU_APP_NAME", "Kiku API")
    api_prefix: str = "/api/v1"
    frontend_origin: str = os.getenv("KIKU_FRONTEND_ORIGIN", "http://localhost:5173")


settings = Settings()
