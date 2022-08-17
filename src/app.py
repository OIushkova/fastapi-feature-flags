from beanie import init_beanie
from fastapi import FastAPI

from src.common.db import get_mongo_client
from src import models
from src.routes import init_routes


def get_app() -> FastAPI:
    _app = FastAPI()
    init_routes(_app)
    return _app


app = get_app()


@app.on_event("startup")
async def start_database():
    await initiate_database()


async def initiate_database():
    await init_beanie(
        database=get_mongo_client().get_default_database(),
        document_models=[models.Project, models.Environment],
    )
