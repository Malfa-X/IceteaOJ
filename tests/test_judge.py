import shutil
import pytest
import asyncio

from app.judge import judge_submission, normalize_output
from app.models import (
    LanguageConfig,
    Problem,
    SubmissionCreate,
    TestCaseStatus,
)


def make_problem() -> Problem:
    return Problem.model_validate(
        {
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
    )


def python_language() -> LanguageConfig:
    return LanguageConfig(
        name="python",
        file_ext=".py",
        run_cmd="python {src}",
    )

def cpp_language() -> LanguageConfig:
    return LanguageConfig(
        name="cpp",
        file_ext=".cpp",
        compile_cmd="g++ {src} -o {exe}",
        run_cmd="{exe}",
    )

def test_normalize_output_ignores_trailing_space_and_newline():
    assert normalize_output("3   \n") == "3"
    assert normalize_output("1 2  \n3\n\n") == "1 2\n3"


def test_judge_python_accepted_answer():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="python",
        code="a, b = map(int, input().split())\nprint(a + b)",
    )

    result = asyncio.run(judge_submission(make_problem(), submission, python_language()))

    assert result.score == 20
    assert result.counts == 20
    assert [case.result for case in result.details] == [
        TestCaseStatus.AC,
        TestCaseStatus.AC,
    ]


def test_judge_python_wrong_answer():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="python",
        code="print(0)",
    )

    result = asyncio.run(judge_submission(make_problem(), submission, python_language()))

    assert result.score == 0
    assert [case.result for case in result.details] == [
        TestCaseStatus.WA,
        TestCaseStatus.WA,
    ]


def test_judge_python_runtime_error():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="python",
        code="raise RuntimeError('boom')",
    )

    result = asyncio.run(judge_submission(make_problem(), submission, python_language()))

    assert result.score == 0
    assert result.details[0].result == TestCaseStatus.RE


def test_judge_python_time_limit_exceeded():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="python",
        code="while True:\n    pass",
    )

    problem = make_problem().model_copy(update={"time_limit": 0.2})

    result = asyncio.run(judge_submission(problem, submission, python_language()))

    assert result.score == 0
    assert result.details[0].result == TestCaseStatus.TLE

@pytest.mark.skipif(shutil.which("g++") is None, reason="g++ is not installed")

def test_judge_cpp_accepted_answer():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="cpp",
        code="""
#include <iostream>
using namespace std;

int main() {
    long long a, b;
    cin >> a >> b;
    cout << a + b << endl;
    return 0;
}
""",
    )

    result = asyncio.run(judge_submission(make_problem(), submission, cpp_language()))

    assert result.compile_info is not None
    assert result.compile_info.result == "success"
    assert result.score == 20
    assert result.counts == 20
    assert [case.result for case in result.details] == [
        TestCaseStatus.AC,
        TestCaseStatus.AC,
    ]


def test_judge_cpp_compilation_error():
    submission = SubmissionCreate(
        problem_id="P1001",
        language="cpp",
        code="int main() { syntax error }",
    )

    result = asyncio.run(judge_submission(make_problem(), submission, cpp_language()))

    assert result.compile_info is not None
    assert result.compile_info.result == "error"
    assert result.score == 0
    assert result.details[0].result == TestCaseStatus.CE