import pytest
from pydantic import ValidationError

from app.models import Problem


def make_problem_payload() -> dict:
    return {
        "id": "P1001",
        "title": "A+B Problem",
        "description": "Calculate a + b.",
        "input_description": "Two integers a and b.",
        "output_description": "The sum of a and b.",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "|a|, |b| <= 10^9",
        "testcases": [{"input": "-1 2", "output": "1"}],
    }


def test_problem_uses_default_optional_fields():
    problem = Problem.model_validate(make_problem_payload())

    assert problem.hint == ""
    assert problem.source == ""
    assert problem.tags == []
    assert problem.time_limit == 3.0
    assert problem.memory_limit == 128
    assert problem.author == ""
    assert problem.difficulty == ""


def test_problem_rejects_missing_required_field():
    payload = make_problem_payload()
    del payload["testcases"]

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)


def test_problem_rejects_extra_field():
    payload = make_problem_payload()
    payload["unexpected"] = "value"

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)


def test_problem_rejects_bad_problem_id():
    payload = make_problem_payload()
    payload["id"] = "../P1001"

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)


def test_problem_rejects_empty_cases():
    payload = make_problem_payload()
    payload["samples"] = []

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)


def test_problem_rejects_non_positive_limits():
    payload = make_problem_payload()
    payload["time_limit"] = 0

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)

    payload = make_problem_payload()
    payload["memory_limit"] = 0

    with pytest.raises(ValidationError):
        Problem.model_validate(payload)

