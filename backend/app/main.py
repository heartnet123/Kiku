from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings, validate_runtime_settings
from app.core.rate_limit import check_rate_limit

validate_runtime_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    docs_url="/docs" if settings.enable_openapi else None,
    redoc_url="/redoc" if settings.enable_openapi else None,
    openapi_url="/openapi.json" if settings.enable_openapi else None,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

@app.middleware("http")
async def add_api_hardening_headers(request: Request, call_next):
    retry_after = check_rate_limit(request)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Try again later."},
            headers={"Retry-After": str(retry_after)},
        )
    response = await call_next(request)
    if not response.headers.get("X-Content-Type-Options"):
        response.headers["X-Content-Type-Options"] = "nosniff"
    if not response.headers.get("X-Frame-Options"):
        response.headers["X-Frame-Options"] = "DENY"
    if not response.headers.get("Referrer-Policy"):
        response.headers["Referrer-Policy"] = "no-referrer"
    if not response.headers.get("Permissions-Policy"):
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    if request.url.path.startswith(settings.api_prefix):
        if not response.headers.get("Cache-Control"):
            response.headers["Cache-Control"] = "no-store"
        vary = response.headers.get("Vary", "")
        if "Origin" not in vary:
            response.headers["Vary"] = f"{vary}, Origin" if vary else "Origin"
    return response


app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/", include_in_schema=False)
async def root() -> dict[str, str]:
    return {"status": "ok", "service": settings.app_name}
