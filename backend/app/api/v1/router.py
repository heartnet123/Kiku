from fastapi import APIRouter

from app.api.v1.routes import auth_routes, chat, feedback, health, members, search, sources, workspaces

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth_routes.router)
api_router.include_router(search.router)
api_router.include_router(search.top_level_router)
api_router.include_router(members.router)
api_router.include_router(workspaces.router)
api_router.include_router(sources.router)
api_router.include_router(feedback.router)
api_router.include_router(chat.router)

