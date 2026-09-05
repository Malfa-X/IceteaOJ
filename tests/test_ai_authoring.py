import asyncio

import pytest

from app.ai_authoring import AiProblemTaskNotFoundError, AiProblemTaskRepository
from app.models import (
    AiProblemRequest,
    AiProblemTaskStatus,
    AiTokenUsage,
    Problem,
)


def make_ai_request() -> AiProblemRequest:
    return AiProblemRequest(
        topic="loop and arithmetic",
        difficulty="easy",
        requirements="Generate an A+B style problem.",
        testcase_count=2,
    )


def make_problem() -> Problem:
    return Problem(
        id="AI1001",
        title="Generated A+B",
        description="Calculate the sum of two integers.",
        input_description="Two integers a and b.",
        output_description="The sum of a and b.",
        samples=[{"input": "1 2", "output": "3"}],
        constraints="|a|, |b| <= 10^9",
        testcases=[
            {"input": "1 2", "output": "3"},
            {"input": "-1 4", "output": "3"},
        ],
        difficulty="easy",
        tags=["generated"],
    )


def test_ai_task_repository_creates_pending_task():
    repository = AiProblemTaskRepository()

    task = asyncio.run(repository.create_task("user-1", make_ai_request()))

    assert task.task_id
    assert task.user_id == "user-1"
    assert task.status == AiProblemTaskStatus.PENDING
    assert task.progress == 0
    assert task.result is None


def test_ai_task_repository_updates_progress():
    repository = AiProblemTaskRepository()
    task = asyncio.run(repository.create_task("user-1", make_ai_request()))

    updated = asyncio.run(
        repository.update_progress(
            task.task_id,
            AiProblemTaskStatus.RUNNING,
            30,
            "building prompt",
        )
    )

    assert updated.status == AiProblemTaskStatus.RUNNING
    assert updated.progress == 30
    assert updated.message == "building prompt"


def test_ai_task_repository_finishes_task_with_problem_and_usage():
    repository = AiProblemTaskRepository()
    task = asyncio.run(repository.create_task("user-1", make_ai_request()))
    usage = AiTokenUsage(
        input_tokens=100,
        output_tokens=200,
        input_cost=0.001,
        output_cost=0.004,
        total_cost=0.005,
        pricing_note="mock pricing",
    )

    finished = asyncio.run(
        repository.finish_task(
            task.task_id,
            make_problem(),
            usage,
        )
    )

    assert finished.status == AiProblemTaskStatus.SUCCESS
    assert finished.progress == 100
    assert finished.result is not None
    assert finished.result.id == "AI1001"
    assert finished.token_usage.total_cost == 0.005


def test_ai_task_repository_cancels_task():
    repository = AiProblemTaskRepository()
    task = asyncio.run(repository.create_task("user-1", make_ai_request()))

    cancelled = asyncio.run(repository.cancel_task(task.task_id))

    assert cancelled.status == AiProblemTaskStatus.CANCELLED
    assert asyncio.run(repository.is_cancelled(task.task_id)) is True


def test_ai_task_repository_rejects_missing_task():
    repository = AiProblemTaskRepository()

    with pytest.raises(AiProblemTaskNotFoundError):
        asyncio.run(repository.get_task("missing"))
