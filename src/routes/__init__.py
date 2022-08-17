from fastapi import FastAPI

from src.routes import health
from src.routes.admin import admin_router
from src.routes.evaluation import router as evaluation_router


def init_routes(app: FastAPI):
    app.include_router(health.router, prefix="/health_check")
    app.include_router(admin_router, prefix="/admin")
    app.include_router(evaluation_router, prefix="")
