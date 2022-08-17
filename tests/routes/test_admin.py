import asyncio

import pytest

from src.models import Environment


@pytest.mark.asyncio
async def test_project_api(client):
    response = await client.get("/admin/projects")

    assert response.status_code == 200
    assert response.json() == []

    project_name = "NewProject"
    response = await client.post("/admin/projects", json={"name": project_name})

    assert response.status_code == 201
    assert set(response.json().keys()) == {
        "id",
        "name",
        "environment_ids",
        "flags",
        "created_at",
        "updated_at",
    }
    assert response.json()["name"] == project_name

    response = await client.get(f"/admin/projects/{project_name}")

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "name",
        "environment_ids",
        "flags",
        "created_at",
        "updated_at",
    }
    assert response.json()["name"] == project_name

    response = await client.delete(f"/admin/projects/{project_name}")

    assert response.status_code == 204

    response = await client.get(f"/admin/projects/{project_name}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_environment_api(client):
    project_name = "NewProject"
    await client.post("/admin/projects", json={"name": project_name})

    response = await client.post(f"/admin/projects/{project_name}", json={"name": "local"})

    assert response.status_code == 201
    assert set(response.json().keys()) == {
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    }
    assert response.json()["name"] == "local"

    env_id = response.json()["id"]

    response = await client.get(f"/admin/{env_id}")

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    }

    response = await client.patch(f"/admin/{env_id}", json={"name": "local2"})

    assert response.status_code == 200
    assert set(response.json().keys()) == {
        "id",
        "name",
        "flags",
        "created_at",
        "updated_at",
    }
    assert response.json()["name"] == "local2"

    response = await client.patch(f"/admin/{env_id}")

    assert response.status_code == 400
    assert response.json()["detail"] == "Name for update is missing"

    response = await client.patch(f"/admin/{env_id}", json={"name": "aa"})

    assert response.status_code == 400
    assert (
        response.json()["detail"]
        == "1 validation error for Environment\nname\n  ensure this value has at least 3 characters "
        "(type=value_error.any_str.min_length; limit_value=3)"
    )


@pytest.mark.asyncio
async def test_flags_api(client, project_factory, environment_factory):
    env1 = Environment(name="env1")
    env2 = Environment(name="env2")
    env3 = await environment_factory()
    project = await project_factory(environments=[env1, env2])

    flag_name = "flag1"

    response = await client.post(
        f"/admin/projects/{project.name}/flags",
        json={"name": flag_name, "default": True},
    )
    assert response.status_code == 201
    assert response.json() == {"name": flag_name, "rules": None, "default": "True"}

    # override
    response = await client.post(f"/admin/projects/{project.name}/flags", json={"name": flag_name})
    assert response.status_code == 201
    assert response.json() == {"name": flag_name, "rules": None, "default": "False"}

    await asyncio.gather(*[i._sync() for i in (project, env1, env2, env3)])

    assert project.flags == {flag_name: {"rules": None, "default": "False"}}
    assert env1.flags == project.flags
    assert env2.flags == project.flags
    assert not env3.flags

    response = await client.post(f"/admin/projects/{project.name}/flags", json={"name": "flag2"})
    assert response.status_code == 201

    await asyncio.gather(*[i._sync() for i in (project, env1, env2)])

    assert project.flags == {
        flag_name: {"rules": None, "default": "False"},
        "flag2": {"rules": None, "default": "False"},
    }
    assert env1.flags == project.flags
    assert env2.flags == project.flags

    response = await client.patch(
        f"/admin/projects/{project.name}/flags/flag2", json={"default": "True"}
    )
    assert response.status_code == 201

    response = await client.patch(
        f"/admin/{env1.id}/flags/{flag_name}",
        json={"default": "True", "rules": {"==": [1, 1]}},
    )
    assert response.status_code == 201

    await asyncio.gather(*[i._sync() for i in (project, env1, env2)])

    assert project.flags == {
        flag_name: {"rules": None, "default": "False"},
        "flag2": {"rules": None, "default": "True"},
    }
    assert env1.flags == {
        flag_name: {"rules": {"==": [1, 1]}, "default": "True"},
        "flag2": {"rules": None, "default": "False"},
    }
    assert env2.flags == {
        flag_name: {"rules": None, "default": "False"},
        "flag2": {"rules": None, "default": "False"},
    }

    response = await client.delete(f"/admin/projects/{project.name}/flags/{flag_name}")
    assert response.status_code == 204

    await asyncio.gather(*[i._sync() for i in (project, env1, env2)])

    assert project.flags == {"flag2": {"rules": None, "default": "True"}}
    assert env1.flags == {"flag2": {"rules": None, "default": "False"}}
    assert env2.flags == {"flag2": {"rules": None, "default": "False"}}


@pytest.mark.asyncio
async def test_keys_api(client, environment_factory):
    env = await environment_factory()

    response = await client.post(
        f"/admin/{env.id}/server_side_key", json={"name": "server_side_key 1"}
    )
    assert response.status_code == 201
    server_side_key_1 = response.json()
    assert server_side_key_1["name"] == "server_side_key 1"

    response = await client.post(
        f"/admin/{env.id}/server_side_key", json={"name": "server_side_key 2"}
    )
    assert response.status_code == 201
    server_side_key_2 = response.json()
    assert server_side_key_2["name"] == "server_side_key 2"

    response = await client.post(
        f"/admin/{env.id}/client_side_key", json={"name": "client_side_key 1"}
    )
    assert response.status_code == 201
    client_side_key_1 = response.json()
    assert client_side_key_1["name"] == "client_side_key 1"

    await env._sync()

    assert len(env.server_side_keys) == 2
    assert len(env.client_side_keys) == 1
    assert env.server_side_keys[server_side_key_1["key"]].name == server_side_key_1["name"]
    assert env.server_side_keys[server_side_key_2["key"]].name == server_side_key_2["name"]

    response = await client.delete(f"/admin/{env.id}/server_side_key/{server_side_key_2['key']}")
    assert response.status_code == 204

    await env._sync()

    assert len(env.server_side_keys) == 1
    assert len(env.client_side_keys) == 1
