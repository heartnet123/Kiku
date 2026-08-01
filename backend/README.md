# Kiku backend

FastAPI responsibilities:

- app/api/v1/ — versioned HTTP routers
- app/schemas/ — request and response contracts
- app/services/ — application use cases
- app/domain/ — framework-independent models
- app/core/ — configuration and cross-cutting concerns

Run from backend:

    uv run fastapi dev app/main.py

Endpoints:

- GET /api/v1/health
- POST /api/v1/search
- GET /docs
