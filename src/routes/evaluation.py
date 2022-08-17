from enum import Enum
from typing import Dict, Set

from fastapi import APIRouter, Depends, HTTPException

from src.models import Environment, FlagEvaluationResult, FlagRule
from src.routes.auth_utils import get_environment_api_key

router = APIRouter()


async def _get_environment(environment_id: str) -> Environment:
    env = await Environment.find_one(Environment.id == environment_id)
    if env is None:
        raise HTTPException(status_code=404)
    return env


class Scopes(Enum):
    SERVER_SIDE = "SERVER_SIDE"
    CLIENT_SIDE = "CLIENT_SIDE"


class _PermissionsValidator:
    def __init__(self, scopes: Set[Scopes]):
        self.scopes = scopes

    def __call__(
        self,
        environment: Environment = Depends(_get_environment),
        api_key=Depends(get_environment_api_key),
    ):
        if Scopes.SERVER_SIDE in self.scopes and api_key in environment.server_side_keys:
            return
        if Scopes.CLIENT_SIDE in self.scopes and api_key in environment.client_side_keys:
            return
        raise HTTPException(status_code=401)


server_side_only = _PermissionsValidator({Scopes.SERVER_SIDE})
server_or_client_side = _PermissionsValidator({Scopes.SERVER_SIDE, Scopes.CLIENT_SIDE})


@router.get(
    "/{environment_id}/get_rules",
    response_model=Dict[str, FlagRule],
    dependencies=[Depends(server_side_only)],
)
async def get_rules(environment: Environment = Depends(_get_environment)):
    return await environment.get_all_rules()


@router.post(
    "/{environment_id}",
    response_model=Dict[str, FlagEvaluationResult],
    dependencies=[Depends(server_or_client_side)],
)
async def evaluate_flags(
    environment: Environment = Depends(_get_environment),
    body: dict = None,
):
    return await environment.evaluate_flags(body)


@router.post(
    "/{environment_id}/{flag_name}",
    response_model=FlagEvaluationResult,
    dependencies=[Depends(server_or_client_side)],
)
async def evaluate_flag(
    flag_name: str,
    environment: Environment = Depends(_get_environment),
    body: dict = None,
):
    res = await environment.evaluate_flag(flag_name, body)
    if not res:
        raise HTTPException(status_code=404, detail="Flag not found")

    return res
