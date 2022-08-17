from fastapi import APIRouter
from fastapi.responses import Response

router = APIRouter()


@router.get("")
async def health():
    return Response("Healthy")
