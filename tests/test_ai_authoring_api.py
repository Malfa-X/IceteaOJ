from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def login_admin(client):
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admintestpassword"},
    )


def register_and_login_user(client, username: str = "alice"):
    client.post(
        "/api/users/",
        json={"username": username, "password": "password123"},
    )
    return client.post(
        "/api/auth/login",
        json={"username": username, "password": "password123"},
    )


def make_config_payload() -> dict:
    return {
        "provider_url": "mock://local",
        "model_name": "mock-problem-generator",
        "api_key": "secret-api-key",
        "input_price_per_1k": 0.001,
        "output_price_per_1k": 0.002,
    }


def make_authoring_payload() -> dict:
    return {
        "topic": "array basics",
        "difficulty": "easy",
        "requirements": "Generate a beginner friendly problem.",
        "testcase_count": 3,
    }


def test_admin_can_update_and_read_masked_ai_config(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)

        update_response = client.put("/api/ai/config", json=make_config_payload())
        assert update_response.status_code == 200
        assert update_response.json()["data"]["api_key"] == "********"

        get_response = client.get("/api/ai/config")

    assert get_response.status_code == 200
    data = get_response.json()["data"]
    assert data["provider_url"] == "mock://local"
    assert data["model_name"] == "mock-problem-generator"
    assert data["api_key"] == "********"
    assert "secret-api-key" not in get_response.text


def test_ai_config_requires_admin(tmp_path):
    with make_client(tmp_path) as client:
        assert client.get("/api/ai/config").status_code == 401

        register_and_login_user(client)

        get_response = client.get("/api/ai/config")
        update_response = client.put("/api/ai/config", json=make_config_payload())

    assert get_response.status_code == 403
    assert update_response.status_code == 403


def test_user_can_create_and_read_ai_problem_task(tmp_path):
    with make_client(tmp_path) as client:
        register_and_login_user(client)

        create_response = client.post(
            "/api/ai/tasks/",
            json=make_authoring_payload(),
        )
        assert create_response.status_code == 200
        task_id = create_response.json()["data"]["task_id"]

        detail_response = client.get(f"/api/ai/tasks/{task_id}")

    assert detail_response.status_code == 200
    data = detail_response.json()["data"]
    assert data["status"] == "success"
    assert data["progress"] == 100
    assert data["result"]["id"].startswith("AI_")
    assert len(data["result"]["testcases"]) == 3
    assert data["token_usage"]["input_tokens"] > 0


def test_ai_problem_task_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/ai/tasks/", json=make_authoring_payload())

    assert response.status_code == 401
    assert response.json()["msg"] == "not logged in"


def test_admin_can_apply_generated_problem_to_problem_repository(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        create_response = client.post(
            "/api/ai/tasks/",
            json=make_authoring_payload(),
        )
        task_id = create_response.json()["data"]["task_id"]
        generated_id = client.get(f"/api/ai/tasks/{task_id}").json()["data"]["result"]["id"]

        apply_response = client.post(f"/api/ai/tasks/{task_id}/apply")
        detail_response = client.get(f"/api/problems/{generated_id}")

    assert apply_response.status_code == 200
    assert apply_response.json()["data"] == {"id": generated_id}
    assert detail_response.status_code == 200
    assert detail_response.json()["data"]["id"] == generated_id


def test_non_admin_cannot_apply_generated_problem(tmp_path):
    with make_client(tmp_path) as client:
        register_and_login_user(client)
        create_response = client.post(
            "/api/ai/tasks/",
            json=make_authoring_payload(),
        )
        task_id = create_response.json()["data"]["task_id"]

        response = client.post(f"/api/ai/tasks/{task_id}/apply")

    assert response.status_code == 403
    assert response.json()["msg"] == "permission denied"


def test_user_can_cancel_pending_ai_problem_task(tmp_path):
    with make_client(tmp_path) as client:
        register_and_login_user(client)
        create_response = client.post(
            "/api/ai/tasks/",
            json=make_authoring_payload(),
        )
        task_id = create_response.json()["data"]["task_id"]

        response = client.put(f"/api/ai/tasks/{task_id}/cancel")

    assert response.status_code == 400
    assert response.json()["msg"] == "task already finished"
