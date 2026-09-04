import pytest
from pydantic import ValidationError

from app.models import (
    Problem,
    JudgeResult,
    Submission,
    SubmissionCreate,
    SubmissionStatus,
    TestCaseResult,
    TestCaseStatus,
)

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

def test_submission_create_accepts_required_fields():
    submission = SubmissionCreate.model_validate(
        {
            "problem_id": "P1001",
            "language": "python",
            "code": "print(input())",
        }
    )

    assert submission.problem_id == "P1001"
    assert submission.language == "python"
    assert submission.code == "print(input())"


def test_submission_create_rejects_empty_code():
    with pytest.raises(ValidationError):
        SubmissionCreate.model_validate(
            {
                "problem_id": "P1001",
                "language": "python",
                "code": "",
            }
        )


def test_submission_defaults_to_pending():
    submission = Submission(
        submission_id="1",
        problem_id="P1001",
        language="python",
        code="print(1)",
    )

    assert submission.status == SubmissionStatus.PENDING
    assert submission.score is None
    assert submission.counts is None


def test_judge_result_contains_case_details():
    result = JudgeResult(
        score=10,
        counts=20,
        run_info={
            "result": "finished",
            "message": "2 test cases finished",
        },
        details=[
            TestCaseResult(
                id=1,
                result=TestCaseStatus.AC,
                time=0.01,
                memory=10,
            ),
            TestCaseResult(
                id=2,
                result=TestCaseStatus.WA,
                time=0.02,
                memory=11,
            ),
        ],
    )

    assert result.score == 10
    assert result.counts == 20
    assert result.details[0].result == TestCaseStatus.AC
    assert result.details[1].result == TestCaseStatus.WA