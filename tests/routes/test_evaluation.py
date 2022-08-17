import pytest

from src.models import Environment, Flag, FlagRule, ApiKey


@pytest.mark.asyncio
async def test_flags_api(client, project_factory):
    env1 = Environment(name="env1")
    env2 = Environment(name="env2")
    project = await project_factory(environments=[env1, env2])

    await project.add_flag(
        Flag(
            name="ready_to_eat",
            rules={
                "and": [
                    {"<": [{"var": "temp"}, 110]},
                    {"==": [{"var": "pie.filling"}, "apple"]},
                ]
            },
        )
    )

    await project.add_flag(
        Flag(
            name="simple",
            rules=1,
            default=0,
        )
    )

    await env2.update_flag(
        "ready_to_eat",
        FlagRule(
            rules={"==": [{"var": "pie.filling"}, "apple"]},
            default=True,
        ),
    )

    await env2.update_flag(
        "simple",
        FlagRule(
            rules=2,
            default=3,
        ),
    )

    env1_headers = {"Authorization": f"Bearer {next(iter(env1.server_side_keys))}"}
    env2_headers = {"Authorization": f"Bearer {next(iter(env2.server_side_keys))}"}

    response = await client.get(f"/{env1.id}/get_rules", headers=env1_headers)
    assert response.status_code == 200
    assert response.json() == {
        "ready_to_eat": {
            "rules": {
                "and": [
                    {"<": [{"var": "temp"}, 110]},
                    {"==": [{"var": "pie.filling"}, "apple"]},
                ]
            },
            "default": "False",
        },
        "simple": {"rules": "1", "default": "0"},
    }

    response = await client.post(f"/{env1.id}", json={}, headers=env1_headers)
    assert response.status_code == 200
    assert response.json() == {
        "ready_to_eat": {
            "value": "False",
            "status": "error",
            "reason": "Invalid context: key 'temp' not found",
        },
        "simple": {"value": "1", "status": "ok", "reason": ""},
    }

    response = await client.post(f"/{env2.id}", json={}, headers=env2_headers)
    assert response.status_code == 200
    assert response.json() == {
        "ready_to_eat": {
            "value": "True",
            "status": "error",
            "reason": "Invalid context: key 'pie' not found",
        },
        "simple": {"value": "2", "status": "ok", "reason": ""},
    }

    response = await client.post(
        f"/{env1.id}",
        json={"temp": 100, "pie": {"filling": "apple"}},
        headers=env1_headers,
    )
    assert response.status_code == 200
    assert response.json() == {
        "ready_to_eat": {"value": "True", "status": "ok", "reason": ""},
        "simple": {"value": "1", "status": "ok", "reason": ""},
    }

    response = await client.post(
        f"/{env2.id}", json={"pie": {"filling": "pineapple"}}, headers=env2_headers
    )
    assert response.status_code == 200
    assert response.json() == {
        "ready_to_eat": {"value": "False", "status": "ok", "reason": ""},
        "simple": {"value": "2", "status": "ok", "reason": ""},
    }

    response = await client.post(
        f"/{env2.id}/ready_to_eat",
        json={"pie": {"filling": "pineapple"}},
        headers=env2_headers,
    )
    assert response.status_code == 200
    assert response.json() == {"value": "False", "status": "ok", "reason": ""}


@pytest.mark.asyncio
async def test_evaluation_get_rules_permissions(client, environment_factory):
    env = await environment_factory()

    response = await client.get(f"/{env.id}/get_rules")
    assert response.status_code == 401

    await env.create_api_key(ApiKey(name="client_side_key"))
    await env._sync()

    response = await client.get(
        f"/{env.id}/get_rules",
        headers={"Authorization": f"Bearer {next(iter(env.client_side_keys))}"},
    )
    assert response.status_code == 401

    await env.create_api_key(ApiKey(name="server_side_key"), server_side=True)
    await env._sync()

    response = await client.get(
        f"/{env.id}/get_rules",
        headers={"Authorization": f"Bearer {next(iter(env.server_side_keys))}"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_evaluation_evaluate_permissions(client, environment_factory):
    env = await environment_factory()

    response = await client.post(f"/{env.id}")
    assert response.status_code == 401

    await env.create_api_key(ApiKey(name="client_side_key"))
    await env.create_api_key(ApiKey(name="server_side_key"), server_side=True)
    await env._sync()

    response = await client.post(
        f"/{env.id}",
        headers={"Authorization": f"Bearer {next(iter(env.client_side_keys))}"},
    )
    assert response.status_code == 200
    response = await client.post(
        f"/{env.id}",
        headers={"Authorization": f"Bearer {next(iter(env.server_side_keys))}"},
    )
    assert response.status_code == 200
