from fastapi.testclient import TestClient

from app.main import create_app

def login_admin(client):
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admintestpassword"},
    )

def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def test_language_api_lists_default_languages(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/languages/")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {
            "name": ["cpp", "python"],
        },
    }


def test_language_api_registers_language(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.post(
            "/api/languages/",
            json={
                "name": "go",
                "file_ext": ".go",
                "compile_cmd": "go build -o {exe} {src}",
                "run_cmd": "{exe}",
            },
        )

        assert response.status_code == 200
        assert response.json() == {
            "code": 200,
            "msg": "language registered",
            "data": {"name": "go"},
        }

        list_response = client.get("/api/languages/")
        assert list_response.json()["data"]["name"] == ["cpp", "go", "python"]


def test_language_api_rejects_duplicate_language(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.post(
            "/api/languages/",
            json={
                "name": "python",
                "file_ext": ".py",
                "run_cmd": "python {src}",
            },
        )

    assert response.status_code == 409
    assert response.json()["msg"] == "language already exists"


def test_language_api_rejects_invalid_language_config(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.post(
            "/api/languages/",
            json={
                "name": "",
                "file_ext": ".py",
                "run_cmd": "python {src}",
            },
        )

    assert response.status_code == 400
    assert response.json()["code"] == 400