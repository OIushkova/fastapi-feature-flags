import asyncio
from datetime import datetime

import pytest
from asgi_lifespan import LifespanManager
from httpx import AsyncClient
from testcontainers.compose import DockerCompose
from testcontainers.core.waiting_utils import wait_container_is_ready

from src.app import app
from src.common.db import get_mongo_client
from src.models import Project, Environment, ApiKey
from src.settings import settings

_testcontainers = DockerCompose(
    ".",
    compose_file_name="docker-compose.yml",
    pull=True,
)


def pytest_configure(config):
    if settings.RUN_TESTCONTAINERS:
        print(f"{datetime.utcnow()}: Start infra")
        _testcontainers.start()

        @wait_container_is_ready()
        def _connect():
            from pymongo import MongoClient

            return MongoClient(settings.MONGODB_CONNECTION_URL)

        print(f"{datetime.utcnow()}: Infra started")


def pytest_unconfigure(config):
    if settings.RUN_TESTCONTAINERS and settings.STOP_TESTCONTAINERS:
        print(f"{datetime.utcnow()}: Stop infra")
        _testcontainers.stop()
        print(f"{datetime.utcnow()}: Finish stopping infra")


@pytest.fixture(scope="session")
async def client():
    async with LifespanManager(app, startup_timeout=30):
        async with AsyncClient(app=app, base_url="http://test") as client:
            yield client


@pytest.fixture(autouse=True)
async def cleanup():
    db = get_mongo_client().get_default_database()
    collections = await db.list_collection_names()
    _clear_all_collections(db, collections)
    yield
    _clear_all_collections(db, collections)


def _clear_all_collections(db, collections):
    for collection in collections:
        db[collection].delete_many({})


@pytest.fixture(scope="session", autouse=True)
def event_loop():
    yield asyncio.get_event_loop()


@pytest.fixture
def environment_factory():
    async def _factory(**kwargs) -> Environment:
        if "name" not in kwargs.keys():
            kwargs["name"] = "default_env"
        return await Environment(**kwargs).create()

    return _factory


@pytest.fixture
def project_factory():
    async def _factory(**kwargs) -> Project:
        environments = kwargs.pop("environments") if "environments" in kwargs else []
        if "name" not in kwargs.keys():
            kwargs["name"] = "default_project"
        project = await Project(**kwargs).create()
        for env in environments:
            await project.add_environment(env)
            await env.create_api_key(ApiKey(name="client_side_key"))
            await env.create_api_key(ApiKey(name="server_side_key"), server_side=True)

        return project

    return _factory
