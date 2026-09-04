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


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def test_submission_api_accepts_python_answer(tmp_path):
    with make_client(tmp_path) as client:
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
        client.post("/api/problems/", json=make_problem_payload())

        response = client.post(
            "/api/submissions/",
            json={
                "problem_id": "P1001",
                "language": "cpp",
                "code": "int main(){}",
            },
        )

    assert response.status_code == 404
    assert response.json()["msg"] == "language not found"


def test_submission_api_rejects_missing_submission(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/submissions/missing")

    assert response.status_code == 404
    assert response.json()["msg"] == "submission not found"