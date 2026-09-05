from fastapi.testclient import TestClient

from app.main import create_app


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def test_register_user_api(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post(
            "/api/users/",
            json={
                "username": "alice",
                "password": "password123",
            },
        )

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["username"] == "alice"
    assert data["role"] == "user"
    assert data["submit_count"] == 0
    assert data["resolve_count"] == 0
    assert "password_hash" not in data


def test_login_and_logout_api(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/users/",
            json={
                "username": "alice",
                "password": "password123",
            },
        )

        login_response = client.post(
            "/api/auth/login",
            json={
                "username": "alice",
                "password": "password123",
            },
        )
        assert login_response.status_code == 200
        assert login_response.json()["msg"] == "login success"

        logout_response = client.post("/api/auth/logout")
        assert logout_response.status_code == 200
        assert logout_response.json()["msg"] == "logout success"


def test_login_rejects_wrong_password(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/users/",
            json={
                "username": "alice",
                "password": "password123",
            },
        )

        response = client.post(
            "/api/auth/login",
            json={
                "username": "alice",
                "password": "wrong-password",
            },
        )

    assert response.status_code == 401
    assert response.json()["msg"] == "invalid username or password"


def test_logout_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/auth/logout")

    assert response.status_code == 401
    assert response.json()["msg"] == "not logged in"


def test_user_can_query_self_after_login(tmp_path):
    with make_client(tmp_path) as client:
        register_response = client.post(
            "/api/users/",
            json={
                "username": "alice",
                "password": "password123",
            },
        )
        user_id = register_response.json()["data"]["user_id"]

        client.post(
            "/api/auth/login",
            json={
                "username": "alice",
                "password": "password123",
            },
        )

        response = client.get(f"/api/users/{user_id}")

    assert response.status_code == 200
    assert response.json()["data"]["username"] == "alice"


def test_user_cannot_query_other_user(tmp_path):
    with make_client(tmp_path) as client:
        alice = client.post(
            "/api/users/",
            json={
                "username": "alice",
                "password": "password123",
            },
        ).json()["data"]
        bob = client.post(
            "/api/users/",
            json={
                "username": "bobby",
                "password": "password123",
            },
        ).json()["data"]

        client.post(
            "/api/auth/login",
            json={
                "username": "alice",
                "password": "password123",
            },
        )

        response = client.get(f"/api/users/{bob['user_id']}")

    assert alice["user_id"] != bob["user_id"]
    assert response.status_code == 403
    assert response.json()["msg"] == "permission denied"


def test_get_user_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/users/1")

    assert response.status_code == 401
    assert response.json()["msg"] == "not logged in"