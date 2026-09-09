import asyncio
import json
import os
import tempfile
from pathlib import Path

from pydantic import ValidationError

from app.models import Problem, ProblemSummary


class ProblemNotFoundError(Exception):
    pass


class ProblemAlreadyExistsError(Exception):
    pass


class ProblemStorageError(Exception):
    pass


class ProblemRepository:
    def __init__(self, problems_dir: Path):
        self.problems_dir = problems_dir
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        await asyncio.to_thread(self.problems_dir.mkdir, parents=True, exist_ok=True)

    def _problem_path(self, problem_id: str) -> Path:
        """根据题目ID构造路径"""
        problem_path = (self.problems_dir / f"{problem_id}.json").resolve()
        problems_root = self.problems_dir.resolve()

        if problem_path.parent != problems_root:
            raise ProblemStorageError("invalid problem path")

        return problem_path

    @staticmethod
    def _read_problem_file(problem_path: Path) -> Problem:
        """读取题目JSON文件并检查是否符合要求，返回内容"""
        try:
            content = problem_path.read_text(encoding="utf-8")
            return Problem.model_validate_json(content)
        except (OSError, ValueError, ValidationError) as error:
            raise ProblemStorageError("failed to read problem file") from error

    @staticmethod
    def _write_problem_file(problem_path: Path, problem: Problem) -> None:
        """写入JSON文件"""
        payload = json.dumps(
            problem.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
        )

        temp_name = None
        try:
            with tempfile.NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=problem_path.parent,
                prefix=f".{problem_path.stem}.",
                suffix=".tmp",
                delete=False,
            ) as temp_file:
                temp_file.write(payload)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())
                temp_name = temp_file.name

            os.replace(temp_name, problem_path)
        except OSError as error:
            if temp_name is not None:
                Path(temp_name).unlink(missing_ok=True)
            raise ProblemStorageError("failed to write problem file") from error

    def _list_problems_sync(self) -> list[ProblemSummary]:
        """真正执行从存储层获取题目列表"""
        summaries = []

        for problem_path in self.problems_dir.glob("*.json"):
            problem = self._read_problem_file(problem_path)
            summaries.append(ProblemSummary(id=problem.id, title=problem.title))

        return sorted(summaries, key=lambda problem: problem.id)

    async def list_problems(self) -> list[ProblemSummary]:
        """将上一个函数异步封装，被main.py调用"""
        async with self._lock:
            return await asyncio.to_thread(self._list_problems_sync)

    async def get_problem(self, problem_id: str) -> Problem:
        """查询详情，用到获取路径和读"""
        async with self._lock:
            problem_path = self._problem_path(problem_id)

            if not await asyncio.to_thread(problem_path.is_file):
                raise ProblemNotFoundError(problem_id)

            return await asyncio.to_thread(self._read_problem_file, problem_path)

    async def add_problem(self, problem: Problem) -> None:
        """添加题目，用到获取路径和写"""
        async with self._lock:
            problem_path = self._problem_path(problem.id)

            if await asyncio.to_thread(problem_path.exists):
                raise ProblemAlreadyExistsError(problem.id)

            await asyncio.to_thread(self._write_problem_file, problem_path, problem)

    async def update_problem(self, problem_id: str, problem: Problem) -> None:
        async with self._lock:
            problem_path = self._problem_path(problem_id)

            if not await asyncio.to_thread(problem_path.is_file):
                raise ProblemNotFoundError(problem_id)

            await asyncio.to_thread(self._write_problem_file, problem_path, problem)

    async def update_log_visibility(
        self,
        problem_id: str,
        public_cases: bool,
    ) -> Problem:
        async with self._lock:
            problem_path = self._problem_path(problem_id)

            if not await asyncio.to_thread(problem_path.is_file):
                raise ProblemNotFoundError(problem_id)

            problem = await asyncio.to_thread(self._read_problem_file, problem_path)
            updated_problem = problem.model_copy(update={"public_cases": public_cases})
            await asyncio.to_thread(self._write_problem_file, problem_path, updated_problem)

            return updated_problem

    async def delete_problem(self, problem_id: str) -> None:
        async with self._lock:
            problem_path = self._problem_path(problem_id)

            if not await asyncio.to_thread(problem_path.is_file):
                raise ProblemNotFoundError(problem_id)

            try:
                await asyncio.to_thread(problem_path.unlink)
            except OSError as error:
                raise ProblemStorageError("failed to delete problem file") from error

