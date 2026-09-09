from fastapi.testclient import TestClient

from app.main import create_app


def make_problem_payload() -> dict:
    return {
        "id": "P1001",
        "title": "A+B Problem",
        "description": "Calculate a + b.",
        "input_description": "Two integers a and b.",
        "output_description": "The sum of a and b.",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "|a|, |b| <= 10^9",
        "testcases": [
            {"input": "1 2", "output": "3"},
            {"input": "-2 5", "output": "3"},
        ],
        "time_limit": 1.0,
        "memory_limit": 128,
    }

def login_admin(client):
    return client.post(
        "/api/auth/login",
        json={"username": "admin", "password": "admintestpassword"},
    )

def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def test_submission_api_accepts_python_answer(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        )

        assert submit_response.status_code == 200
        submit_data = submit_response.json()["data"]
        assert submit_data["status"] == "pending"

        detail_response = client.get(f"/api/submissions/{submit_data['submission_id']}")

        assert detail_response.status_code == 200
        detail_data = detail_response.json()["data"]
        assert detail_data["status"] == "success"
        assert detail_data["score"] == 20
        assert detail_data["counts"] == 20


def test_submission_api_reports_wrong_answer(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )

        submission_id = submit_response.json()["data"]["submission_id"]
        detail_response = client.get(f"/api/submissions/{submission_id}")

        assert detail_response.status_code == 200
        detail_data = detail_response.json()["data"]
        assert detail_data["status"] == "success"
        assert detail_data["score"] == 0
        assert detail_data["counts"] == 20


def test_submission_api_rejects_missing_problem(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "missing",
                "language": "python",
                "code": "print(1)",
            },
        )

    assert response.status_code == 404
    assert response.json()["msg"] == "problem not found"


def test_submission_api_rejects_missing_language(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "rust",
                "code": "int main(){}",
            },
        )

    assert response.status_code == 404
    assert response.json()["msg"] == "language not found"


def test_submission_api_rejects_missing_submission(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/missing")

    assert response.status_code == 404
    assert response.json()["msg"] == "submission not found"

def test_submission_list_api_filters_by_problem_id(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        first = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        ).json()["data"]

        second = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        ).json()["data"]

        response = client.get("/api/submissions/?problem_id=P1001")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert [item["submission_id"] for item in data["submissions"]] == [
        second["submission_id"],
        first["submission_id"],
    ]


def test_submission_list_api_filters_by_status(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        )

        response = client.get("/api/submissions/?problem_id=P1001&status=success")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert all(item["status"] == "success" for item in data["submissions"])


def test_submission_list_api_supports_pagination(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        for index in range(5):
            client.post(
                "/api/submissions/",
                json={
                    "problem_id": "P1001",
                    "language": "python",
                    "code": f"print({index})",
                },
            )

        response = client.get("/api/submissions/?problem_id=P1001&page=2&page_size=2")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 5
    assert len(data["submissions"]) == 2


def test_submission_list_api_rejects_missing_primary_filter(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/")

    assert response.status_code == 400
    assert response.json()["msg"] == "user_id or problem_id is required"


def test_submission_list_api_rejects_page_without_page_size(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/?problem_id=P1001&page=1")

    assert response.status_code == 400
    assert response.json()["msg"] == "page_size is required when page is set"

def test_submission_list_api_filters_by_problem_id(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        first = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        ).json()["data"]

        second = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        ).json()["data"]

        response = client.get("/api/submissions/?problem_id=P1001")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert [item["submission_id"] for item in data["submissions"]] == [
        second["submission_id"],
        first["submission_id"],
    ]


def test_submission_list_api_filters_by_status(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        )

        response = client.get("/api/submissions/?problem_id=P1001&status=success")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 2
    assert all(item["status"] == "success" for item in data["submissions"])


def test_submission_list_api_supports_pagination(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        for index in range(5):
            client.post(
                "/api/submissions/",
                json={
                    "problem_id": "P1001",
                    "language": "python",
                    "code": f"print({index})",
                },
            )

        response = client.get("/api/submissions/?problem_id=P1001&page=2&page_size=2")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 5
    assert len(data["submissions"]) == 2


def test_submission_list_api_rejects_missing_primary_filter(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/")

    assert response.status_code == 400
    assert response.json()["msg"] == "user_id or problem_id is required"


def test_submission_list_api_rejects_page_without_page_size(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/?problem_id=P1001&page=1")

    assert response.status_code == 400
    assert response.json()["msg"] == "page_size is required when page is set"

def test_rejudge_submission_api_resets_and_updates_result(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]

        before_rejudge = client.get(f"/api/submissions/{submission_id}").json()["data"]
        assert before_rejudge["score"] == 0

        rejudge_response = client.put(f"/api/submissions/{submission_id}/rejudge")
        assert rejudge_response.status_code == 200
        assert rejudge_response.json() == {
            "code": 200,
            "msg": "rejudge started",
            "data": {
                "submission_id": submission_id,
                "status": "pending",
            },
        }

        after_rejudge = client.get(f"/api/submissions/{submission_id}").json()["data"]
        assert after_rejudge["status"] == "success"
        assert after_rejudge["score"] == 0
        assert after_rejudge["counts"] == 20

def test_rejudge_submission_api_rejects_missing_submission(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.put("/api/submissions/missing/rejudge")

    assert response.status_code == 404
    assert response.json()["msg"] == "submission not found"

def test_submission_list_api_uses_first_page_when_only_page_size_is_set(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        for index in range(3):
            client.post(
                "/api/submissions/",
                json={
                    "problem_id": "P1001",
                    "language": "python",
                    "code": f"print({index})",
                },
            )

        response = client.get("/api/submissions/?problem_id=P1001&page_size=2")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["total"] == 3
    assert len(data["submissions"]) == 2
    assert [item["submission_id"] for item in data["submissions"]] == ["3", "2"]

def test_submission_list_api_rejects_invalid_pagination(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        page_response = client.get("/api/submissions/?problem_id=P1001&page=0&page_size=2")
        page_size_response = client.get(
            "/api/submissions/?problem_id=P1001&page=1&page_size=0"
        )

    assert page_response.status_code == 400
    assert page_response.json()["msg"] == "page must be positive"

    assert page_size_response.status_code == 400
    assert page_size_response.json()["msg"] == "page_size must be positive"

def test_submission_list_api_rejects_invalid_status(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/?problem_id=P1001&status=finished")

    assert response.status_code == 400
    assert response.json()["code"] == 400

def test_submission_list_api_does_not_return_code(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print('secret code')",
            },
        )

        response = client.get("/api/submissions/?problem_id=P1001")

    assert response.status_code == 200
    submission = response.json()["data"]["submissions"][0]
    assert "code" not in submission

def test_submission_log_api_returns_case_details(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())

        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "a, b = map(int, input().split())\nprint(a + b)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]

        response = client.get(f"/api/submissions/{submission_id}/log")

    assert response.status_code == 200
    data = response.json()["data"]
    assert data["score"] == 20
    assert data["counts"] == 20
    assert data["details"] == [
        {
            "id": 1,
            "result": "AC",
            "time": data["details"][0]["time"],
            "memory": data["details"][0]["memory"],
        },
        {
            "id": 2,
            "result": "AC",
            "time": data["details"][1]["time"],
            "memory": data["details"][1]["memory"],
        },
    ]


def test_submission_log_api_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/submissions/1/log")

    assert response.status_code == 401
    assert response.json()["msg"] == "not logged in"


def test_submission_log_api_rejects_missing_submission(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        response = client.get("/api/submissions/missing/log")

    assert response.status_code == 404
    assert response.json()["msg"] == "submission not found"


def test_submission_log_api_rejects_other_user(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/api/users/", json={"username": "bobby", "password": "password123"})

        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "alice123"},
        )
        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "bobby", "password": "password123"},
        )
        response = client.get(f"/api/submissions/{submission_id}/log")

    assert response.status_code == 403
    assert response.json()["msg"] == "permission denied"

def test_public_cases_allow_other_users_to_view_submission_log(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/api/users/", json={"username": "bobby", "password": "password123"})

        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())
        client.put("/api/problems/P1001/log_visibility", json={"public_cases": True})
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "alice123"},
        )
        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "bobby", "password": "password123"},
        )
        response = client.get(f"/api/submissions/{submission_id}/log")

    assert response.status_code == 200
    assert response.json()["data"]["score"] == 0


def test_admin_can_query_log_access_records(tmp_path):
    with make_client(tmp_path) as client:
        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "alice123"},
        )
        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]

        client.get(f"/api/submissions/{submission_id}/log")
        client.post("/api/auth/logout")

        login_admin(client)
        response = client.get("/api/logs/access/")

    assert response.status_code == 200
    logs = response.json()["data"]
    assert len(logs) == 1
    assert logs[0]["problem_id"] == "P1001"
    assert logs[0]["action"] == "view_logs"
    assert logs[0]["status"] == "200"

def test_denied_submission_log_access_is_audited(tmp_path):
    with make_client(tmp_path) as client:
        client.post("/api/users/", json={"username": "bobby", "password": "password123"})

        login_admin(client)
        client.post("/api/problems/", json=make_problem_payload())
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "alice123"},
        )
        submit_response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "python",
                "code": "print(0)",
            },
        )
        submission_id = submit_response.json()["data"]["submission_id"]
        client.post("/api/auth/logout")

        client.post(
            "/api/auth/login",
            json={"username": "bobby", "password": "password123"},
        )
        denied_response = client.get(f"/api/submissions/{submission_id}/log")
        client.post("/api/auth/logout")

        login_admin(client)
        audit_response = client.get("/api/logs/access/")

    assert denied_response.status_code == 403
    logs = audit_response.json()["data"]
    assert len(logs) == 1
    assert logs[0]["problem_id"] == "P1001"
    assert logs[0]["status"] == "403"

def test_access_log_api_requires_login(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/logs/access/")

    assert response.status_code == 401
    assert response.json()["msg"] == "not logged in"


def test_access_log_api_requires_admin(tmp_path):
    with make_client(tmp_path) as client:
        client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "alice123"},
        )

        response = client.get("/api/logs/access/")

    assert response.status_code == 403
    assert response.json()["msg"] == "permission denied"
