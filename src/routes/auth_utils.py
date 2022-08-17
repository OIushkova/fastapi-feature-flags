from enum import Enum

from fastapi import HTTPException, Depends
from fastapi.security import HTTPAuthorizationCredentials
from starlette.requests import Request


class TokenTypes(Enum):
    BEARER = "bearer"
    BASIC = "basic"


def get_auth_credentials(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        raise HTTPException(status_code=401)

    scheme, _, credentials = auth_header.partition(" ")
    if not scheme or not credentials:
        raise HTTPException(status_code=401)

    return HTTPAuthorizationCredentials(scheme=scheme, credentials=credentials)


def get_environment_api_key(
    auth_cred: HTTPAuthorizationCredentials = Depends(get_auth_credentials),
):
    if auth_cred.scheme.lower() == TokenTypes.BEARER.value:
        return auth_cred.credentials
