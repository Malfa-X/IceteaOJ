import asyncio
import json
from datetime import datetime, timezone
from uuid import uuid4

import requests

from app.models import (
    AiModelConfig,
    AiModelConfigPublic,
    AiProblemRequest,
    AiProblemTask,
    AiProblemTaskStatus,
    AiTokenUsage,
    Problem,
)


class AiModelConfigNotFoundError(Exception):
    pass


class AiProblemTaskNotFoundError(Exception):
    pass


class AiModelConfigRepository:
    def __init__(self):
        self._config: AiModelConfig | None = AiModelConfig(
            provider_url="https://example.com/v1/chat/completions",
            model_name="your-model-name",
            api_key="your-api-key",
            input_price_per_1k=0.0,
            output_price_per_1k=0.0,
        )

    async def set_config(self, config: AiModelConfig) -> AiModelConfigPublic:
        self._config = config
        return self.public_config()

    async def get_config(self) -> AiModelConfig:
        if self._config is None:
            raise AiModelConfigNotFoundError()

        return self._config

    def public_config(self) -> AiModelConfigPublic:
        if self._config is None:
            raise AiModelConfigNotFoundError()

        return AiModelConfigPublic(
            provider_url=self._config.provider_url,
            model_name=self._config.model_name,
            api_key=mask_api_key(self._config.api_key),
            input_price_per_1k=self._config.input_price_per_1k,
            output_price_per_1k=self._config.output_price_per_1k,
        )


class AiProblemTaskRepository:
    def __init__(self):
        self._tasks: dict[str, AiProblemTask] = {}

    async def create_task(
        self,
        user_id: str,
        request: AiProblemRequest,
    ) -> AiProblemTask:
        now = current_time()
        task = AiProblemTask(
            task_id=uuid4().hex,
            user_id=user_id,
            request=request,
            created_at=now,
            updated_at=now,
        )
        self._tasks[task.task_id] = task
        return task

    async def get_task(self, task_id: str) -> AiProblemTask:
        if task_id not in self._tasks:
            raise AiProblemTaskNotFoundError(task_id)

        return self._tasks[task_id]

    async def update_progress(
        self,
        task_id: str,
        status: AiProblemTaskStatus,
        progress: int,
        message: str,
    ) -> AiProblemTask:
        task = await self.get_task(task_id)
        updated = task.model_copy(
            update={
                "status": status,
                "progress": progress,
                "message": message,
                "updated_at": current_time(),
            }
        )
        self._tasks[task_id] = updated
        return updated

    async def finish_task(
        self,
        task_id: str,
        result: Problem,
        token_usage: AiTokenUsage,
    ) -> AiProblemTask:
        task = await self.get_task(task_id)
        updated = task.model_copy(
            update={
                "status": AiProblemTaskStatus.SUCCESS,
                "progress": 100,
                "message": "problem generated",
                "result": result,
                "token_usage": token_usage,
                "updated_at": current_time(),
            }
        )
        self._tasks[task_id] = updated
        return updated

    async def fail_task(self, task_id: str, error_info: str) -> AiProblemTask:
        task = await self.get_task(task_id)
        updated = task.model_copy(
            update={
                "status": AiProblemTaskStatus.FAILED,
                "message": "problem generation failed",
                "error_info": error_info,
                "updated_at": current_time(),
            }
        )
        self._tasks[task_id] = updated
        return updated

    async def cancel_task(self, task_id: str) -> AiProblemTask:
        task = await self.get_task(task_id)
        updated = task.model_copy(
            update={
                "status": AiProblemTaskStatus.CANCELLED,
                "message": "problem generation cancelled",
                "updated_at": current_time(),
            }
        )
        self._tasks[task_id] = updated
        return updated

    async def is_cancelled(self, task_id: str) -> bool:
        task = await self.get_task(task_id)
        return task.status == AiProblemTaskStatus.CANCELLED


async def generate_problem_task(
    task_id: str,
    task_repository: AiProblemTaskRepository,
    config_repository: AiModelConfigRepository,
) -> None:
    try:
        task = await task_repository.get_task(task_id)
        config = await config_repository.get_config()

        progress_steps = [
            (10, "reading authoring requirements"),
            (30, "building generation prompt"),
            (55, "generating problem statement"),
            (75, "generating test cases"),
            (90, "calculating token usage and price"),
        ]

        for progress, message in progress_steps:
            if await task_repository.is_cancelled(task_id):
                return

            await task_repository.update_progress(
                task_id,
                AiProblemTaskStatus.RUNNING,
                progress,
                message,
            )
            await asyncio.sleep(0.01)

        if await task_repository.is_cancelled(task_id):
            return

        result, usage = await generate_problem(task, config)
        await task_repository.finish_task(task_id, result, usage)
    except Exception as error:
        await task_repository.fail_task(
            task_id,
            f"{type(error).__name__}: {error}",
        )


async def generate_problem(
    task: AiProblemTask,
    config: AiModelConfig,
) -> tuple[Problem, AiTokenUsage]:
    return await asyncio.to_thread(call_openai_compatible_provider, task, config)


def call_openai_compatible_provider(
    task: AiProblemTask,
    config: AiModelConfig,
) -> tuple[Problem, AiTokenUsage]:
    payload = {
        "model": config.model_name,
        "messages": build_authoring_messages(task.request),
        "response_format": {"type": "json_object"},
        "temperature": 0.2,
    }
    headers = {
        "Authorization": f"Bearer {config.api_key}",
        "Content-Type": "application/json",
    }
    response = requests.post(
        config.provider_url,
        json=payload,
        headers=headers,
        timeout=120,
    )
    response.raise_for_status()

    payload = response.json()
    content = payload["choices"][0]["message"]["content"]
    problem = parse_problem_from_model_output(content, task, config)
    usage_payload = payload.get("usage") or {}
    usage = usage_from_counts(
        input_tokens=usage_payload.get("prompt_tokens", 0),
        output_tokens=usage_payload.get("completion_tokens", 0),
        config=config,
        pricing_note=(
            "External OpenAI-compatible API call; token counts from provider usage field. "
            "If the provider omits usage, counts fall back to 0."
        ),
    )
    return problem, usage


def build_authoring_messages(request: AiProblemRequest) -> list[dict[str, str]]:
    schema_hint = {
        "id": "AI_CUSTOM_ID",
        "title": "Problem title",
        "description": "Problem statement",
        "input_description": "Input format",
        "output_description": "Output format",
        "samples": [{"input": "1 2", "output": "3"}],
        "constraints": "Constraints",
        "testcases": [{"input": "1 2", "output": "3"}],
        "hint": "Solution hint",
        "source": "AI generated",
        "tags": ["ai-generated"],
        "time_limit": 1.0,
        "memory_limit": 128,
        "author": "AI",
        "difficulty": request.difficulty,
        "public_cases": False,
    }
    return [
        {
            "role": "system",
            "content": (
                "You generate programming contest problems for an online judge. "
                "Return only one valid JSON object. Do not use markdown. "
                "The JSON must match the given schema and include valid samples "
                "and testcases."
            ),
        },
        {
            "role": "user",
            "content": (
                f"Topic: {request.topic}\n"
                f"Difficulty: {request.difficulty}\n"
                f"Extra requirements: {request.requirements}\n"
                f"Testcase count: {request.testcase_count}\n"
                f"JSON schema example: {json.dumps(schema_hint, ensure_ascii=False)}"
            ),
        },
    ]


def parse_problem_from_model_output(
    content: str,
    task: AiProblemTask,
    config: AiModelConfig,
) -> Problem:
    data = json.loads(extract_json_object(content))
    if "problem" in data and isinstance(data["problem"], dict):
        data = data["problem"]

    data.setdefault("id", f"AI_{task.task_id[:8].upper()}")
    data.setdefault("source", f"AI generated by {config.model_name} via {config.provider_url}")
    data.setdefault("author", task.user_id)
    data.setdefault("difficulty", task.request.difficulty)
    data.setdefault("tags", ["ai-generated", task.request.topic, task.request.difficulty])
    data.setdefault("public_cases", False)
    return Problem.model_validate(data)


def extract_json_object(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = stripped.strip("`")
        if stripped.startswith("json"):
            stripped = stripped[4:].strip()

    start = stripped.find("{")
    end = stripped.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("model response does not contain a JSON object")

    return stripped[start : end + 1]


def usage_from_counts(
    input_tokens: int,
    output_tokens: int,
    config: AiModelConfig,
    pricing_note: str,
) -> AiTokenUsage:
    input_cost = input_tokens / 1000 * config.input_price_per_1k
    output_cost = output_tokens / 1000 * config.output_price_per_1k
    return AiTokenUsage(
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        input_cost=round(input_cost, 6),
        output_cost=round(output_cost, 6),
        total_cost=round(input_cost + output_cost, 6),
        pricing_note=pricing_note,
    )


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def mask_api_key(api_key: str) -> str:
    if not api_key:
        return ""

    return "********"


def current_time() -> str:
    return datetime.now(timezone.utc).isoformat()
