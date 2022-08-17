from fastapi import APIRouter

from src.routes.admin import projects, environments

admin_router = APIRouter()

admin_router.include_router(projects.router, prefix="/projects")
admin_router.include_router(environments.router, prefix="")
