from fastapi.testclient import TestClient

from app.main import create_app


def make_problem_payload(problem_id: str = "sum_2") -> dict:
    return {
        "id": problem_id,
        "title": "Two Sum",
        "description": "Calculate a + b.",
        "input_description": "Two integers a and b.",
        "output_description": "The sum of a and b.",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "|a|, |b| <= 10^9",
        "testcases": [{"input": "-1 2", "output": "1"}],
    }


def make_client(tmp_path):
    return TestClient(create_app(tmp_path / "problems"))


def test_health_check(tmp_path):
    with make_client(tmp_path) as client:
        response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "code": 200,
        "msg": "success",
        "data": {"status": "ok"},
    }


def test_problem_crud_flow(tmp_path):
    with make_client(tmp_path) as client:
        add_response = client.post("/api/problems/", json=make_problem_payload())
        assert add_response.status_code == 200
        assert add_response.json() == {
            "code": 200,
            "msg": "add success",
            "data": {"id": "sum_2"},
        }

        list_response = client.get("/api/problems/")
        assert list_response.status_code == 200
        assert list_response.json()["data"] == [{"id": "sum_2", "title": "Two Sum"}]

        detail_response = client.get("/api/problems/sum_2")
        detail = detail_response.json()["data"]
        assert detail["id"] == "sum_2"
        assert detail["hint"] == ""
        assert detail["tags"] == []
        assert detail["time_limit"] == 3.0
        assert detail["memory_limit"] == 128

        updated_payload = make_problem_payload()
        updated_payload["title"] = "Updated Two Sum"
        update_response = client.put("/api/problems/sum_2", json=updated_payload)
        assert update_response.status_code == 200
        assert update_response.json()["msg"] == "update success"
        assert client.get("/api/problems/sum_2").json()["data"]["title"] == "Updated Two Sum"

        delete_response = client.delete("/api/problems/sum_2")
        assert delete_response.status_code == 200
        assert delete_response.json() == {
            "code": 200,
            "msg": "delete success",
            "data": {"id": "sum_2"},
        }
        assert client.get("/api/problems/sum_2").status_code == 404


def test_problem_api_errors(tmp_path):
    with make_client(tmp_path) as client:
        response = client.post("/api/problems/", json=make_problem_payload())
        assert response.status_code == 200

        duplicate_response = client.post("/api/problems/", json=make_problem_payload())
        assert duplicate_response.status_code == 409
        assert duplicate_response.json()["code"] == 409

        invalid_payload = make_problem_payload()
        del invalid_payload["testcases"]
        invalid_response = client.post("/api/problems/", json=invalid_payload)
        assert invalid_response.status_code == 400
        assert invalid_response.json()["code"] == 400

        mismatch_response = client.put(
            "/api/problems/sum_2",
            json=make_problem_payload("another_id"),
        )
        assert mismatch_response.status_code == 400

        missing_response = client.delete("/api/problems/missing")
        assert missing_response.status_code == 404

