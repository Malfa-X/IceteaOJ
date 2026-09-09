import asyncio

import pytest

from app.ai_authoring import (
    AiProblemTaskNotFoundError,
    AiProblemTaskRepository,
    call_ollama_provider,
    call_openai_compatible_provider,
)
from app.models import (
    AiModelConfig,
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


def test_ollama_provider_parses_problem_and_token_usage(monkeypatch):
    repository = AiProblemTaskRepository()
    task = asyncio.run(repository.create_task("user-1", make_ai_request()))
    config = AiModelConfig(
        provider_url="http://127.0.0.1:11434/api/chat",
        model_name="qwen2.5:7b",
        api_key="local-ollama-no-key",
        input_price_per_1k=0,
        output_price_per_1k=0,
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "message": {"content": make_problem().model_dump_json()},
                "prompt_eval_count": 12,
                "eval_count": 34,
            }

    def fake_post(url, json, timeout):
        assert url == "http://127.0.0.1:11434/api/chat"
        assert json["model"] == "qwen2.5:7b"
        assert json["stream"] is False
        return FakeResponse()

    monkeypatch.setattr("app.ai_authoring.requests.post", fake_post)

    problem, usage = call_ollama_provider(task, config)

    assert problem.id == "AI1001"
    assert usage.input_tokens == 12
    assert usage.output_tokens == 34
    assert usage.total_cost == 0


def test_openai_compatible_provider_uses_bearer_token_and_usage(monkeypatch):
    repository = AiProblemTaskRepository()
    task = asyncio.run(repository.create_task("user-1", make_ai_request()))
    config = AiModelConfig(
        provider_url="https://ddpro.ai/v1/chat/completions",
        model_name="qwen2.5:7b",
        api_key="sk-123456789",
        input_price_per_1k=0.001,
        output_price_per_1k=0.002,
    )

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {"message": {"content": make_problem().model_dump_json()}},
                ],
                "usage": {
                    "prompt_tokens": 100,
                    "completion_tokens": 200,
                },
            }

    def fake_post(url, json, headers, timeout):
        assert url == "https://ddpro.ai/v1/chat/completions"
        assert json["model"] == "qwen2.5:7b"
        assert headers["Authorization"] == "Bearer sk-123456789"
        return FakeResponse()

    monkeypatch.setattr("app.ai_authoring.requests.post", fake_post)

    problem, usage = call_openai_compatible_provider(task, config)

    assert problem.id == "AI1001"
    assert usage.input_tokens == 100
    assert usage.output_tokens == 200
    assert usage.total_cost == 0.0005
