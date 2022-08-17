from typing import List

from fastapi import APIRouter, HTTPException, Depends
from pymongo.errors import WriteError

from src.common.logger import get_logger
from src.models import Project, Flag, Environment, FlagRule

router = APIRouter()
logger = get_logger(__name__)


PROJECT_RETURN_FIELDS = {
    "response_model_include": {
        "id",
        "name",
        "environment_ids",
        "flags",
        "created_at",
        "updated_at",
    },
    "response_model_by_alias": False,
}


async def _get_project(project_name: str) -> Project:
    project = await Project.find_one(Project.name == project_name)
    if project is None:
        raise HTTPException(status_code=404)
    return project


@router.get("", response_model=List[Project], **PROJECT_RETURN_FIELDS)
async def list_projects(page_size: int = 100, page_start: int = 0):
    return await Project.all(limit=page_size, skip=page_start).sort(Project.name).to_list()


@router.post("", response_model=Project, status_code=201, **PROJECT_RETURN_FIELDS)
async def create_project(project: Project):
    return await project.create()


@router.get("/{project_name}", response_model=Project, **PROJECT_RETURN_FIELDS)
async def get_project(project: Project = Depends(_get_project)):
    return project


@router.delete("/{project_name}", status_code=204)
async def delete_project(project: Project = Depends(_get_project)):
    await project.delete()


# todo add permission validation
@router.post(
    "/{project_name}",
    response_model=Environment,
    status_code=201,
    response_model_include={
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    },
    response_model_by_alias=False,
)
async def create_environment(environment: Environment, project: Project = Depends(_get_project)):
    await project.add_environment(environment)
    return environment


@router.post("/{project_name}/flags", response_model=Flag, status_code=201)
async def add_flag(flag: Flag, project: Project = Depends(_get_project)):
    try:
        return await project.add_flag(flag)
    except WriteError as e:
        logger.info(f"Fail to add flag: {e}")
        raise HTTPException(status_code=400, detail="Flag name already exists")


@router.patch("/{project_name}/flags/{flag_name}", response_model=Flag, status_code=201)
async def patch_flag(
    flag_name: str, flag_updatable: FlagRule, project: Project = Depends(_get_project)
):
    try:
        return await project.update_flag(flag_name, flag_updatable)
    except WriteError as e:
        logger.info(f"Fail to patch flag: {e}")
        raise HTTPException(status_code=400)


@router.delete("/{project_name}/flags/{flag_name}", status_code=204)
async def remove_flag(flag_name: str, project: Project = Depends(_get_project)):
    try:
        await project.remove_flag(flag_name)
    except WriteError as e:
        logger.info(f"Fail to remove flag: {e}")
        raise HTTPException(status_code=400)
