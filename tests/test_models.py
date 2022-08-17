import pytest

from src.app import initiate_database
from src.models import Project


@pytest.mark.asyncio
async def test_base_model():
    await initiate_database()
    await Project(name="some1234").create()
    project = await Project.find_one(Project.name == "some1234")
    assert project.name == "some1234"

    project.name = "some2345"
    print("created_at ", project.created_at)
    print("updated_at ", project.updated_at)
    await project.save()

    project = await Project.find_one(Project.name == "some2345")
    assert project.name == "some2345"
    assert project.created_at != project.updated_at
