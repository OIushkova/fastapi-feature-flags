from typing import Optional

from pydantic.error_wrappers import ValidationError as PydanticValidationError
from fastapi import APIRouter, HTTPException, Depends
from pymongo.errors import WriteError

from src.common.logger import get_logger
from src.models import Environment, FlagRule, Flag, ApiKey, ApiKeyValue

router = APIRouter()
logger = get_logger(__name__)


async def _get_environment(environment_id: str) -> Environment:
    env = await Environment.find_one(Environment.id == environment_id)
    if env is None:
        raise HTTPException(status_code=404)
    return env


# todo add permission validation
@router.get(
    "/{environment_id}",
    response_model=Environment,
    response_model_include={
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    },
    response_model_by_alias=False,
)
async def get_environment(environment: Environment = Depends(_get_environment)):
    return environment


@router.delete("/{environment_id}", status_code=204)
async def delete_environment(environment: Environment = Depends(_get_environment)):
    await environment.delete()


@router.patch(
    "/{environment_id}",
    response_model=Environment,
    response_model_include={
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    },
    response_model_by_alias=False,
)
async def update_environment(
    body: Optional[dict] = None, environment: Environment = Depends(_get_environment)
):
    if body and "name" in body.keys():
        try:
            environment.name = body["name"]
        except PydanticValidationError as e:
            raise HTTPException(status_code=400, detail=str(e))

        await environment.save()
        return environment

    raise HTTPException(status_code=400, detail="Name for update is missing")


@router.patch("/{environment_id}/flags/{flag_name}", response_model=Flag, status_code=201)
async def patch_flag(
    flag_name: str, flag: FlagRule, environment: Environment = Depends(_get_environment)
):
    try:
        return await environment.update_flag(flag_name, flag)
    except WriteError as e:
        logger.info(f"Fail to patch flag: {e}")
        raise HTTPException(status_code=400)


@router.post("/{environment_id}/server_side_key", response_model=ApiKey, status_code=201)
async def add_server_side_key(key: ApiKey, environment: Environment = Depends(_get_environment)):
    return await environment.create_api_key(key, server_side=True)


@router.post("/{environment_id}/client_side_key", response_model=ApiKey, status_code=201)
async def add_client_side_key(key: ApiKey, environment: Environment = Depends(_get_environment)):
    return await environment.create_api_key(key)


@router.delete("/{environment_id}/server_side_key/{key}", status_code=204)
async def delete_server_side_key(
    key: ApiKeyValue, environment: Environment = Depends(_get_environment)
):
    return await environment.delete_api_key(key, server_side=True)


@router.delete("/{environment_id}/client_side_key/{key}", status_code=204)
async def delete_client_side_key(
    key: ApiKeyValue, environment: Environment = Depends(_get_environment)
):
    return await environment.delete_api_key(key)
