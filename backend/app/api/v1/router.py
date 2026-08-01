from fastapi import APIRouter

from app.api.v1.routes import auth_routes, feedback, health, members, search, sources

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_routes.router)
api_router.include_router(search.router)
api_router.include_router(members.router)
api_router.include_router(sources.router)
api_router.include_router(feedback.router)
