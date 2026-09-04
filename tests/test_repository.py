import asyncio

import pytest

from app.models import Problem
from app.repository import (
    ProblemAlreadyExistsError,
    ProblemNotFoundError,
    ProblemRepository,
)


def make_problem(problem_id: str = "P1001") -> Problem:
    return Problem.model_validate(
        {
            "id": problem_id,
            "title": "A+B Problem",
            "description": "Calculate a + b.",
            "input_description": "Two integers a and b.",
            "output_description": "The sum of a and b.",
            "samples": [{"input": "1 2", "output": "3"}],
            "constraints": "|a|, |b| <= 10^9",
            "testcases": [{"input": "-1 2", "output": "1"}],
        }
    )


def test_repository_adds_and_gets_problem(tmp_path):
    async def run_test():
        repository = ProblemRepository(tmp_path / "problems")
        await repository.initialize()
        problem = make_problem()

        await repository.add_problem(problem)

        loaded_problem = await repository.get_problem("P1001")
        assert loaded_problem == problem

    asyncio.run(run_test())


def test_repository_lists_problem_summaries(tmp_path):
    async def run_test():
        repository = ProblemRepository(tmp_path / "problems")
        await repository.initialize()

        await repository.add_problem(make_problem("B1001"))
        await repository.add_problem(make_problem("A1001"))

        problems = await repository.list_problems()

        assert [problem.id for problem in problems] == ["A1001", "B1001"]
        assert [problem.title for problem in problems] == ["A+B Problem", "A+B Problem"]

    asyncio.run(run_test())


def test_repository_rejects_duplicate_problem(tmp_path):
    async def run_test():
        repository = ProblemRepository(tmp_path / "problems")
        await repository.initialize()
        problem = make_problem()

        await repository.add_problem(problem)

        with pytest.raises(ProblemAlreadyExistsError):
            await repository.add_problem(problem)

    asyncio.run(run_test())


def test_repository_updates_problem(tmp_path):
    async def run_test():
        repository = ProblemRepository(tmp_path / "problems")
        await repository.initialize()
        problem = make_problem()

        await repository.add_problem(problem)

        updated_problem = problem.model_copy(update={"title": "Updated A+B Problem"})
        await repository.update_problem("P1001", updated_problem)

        assert (await repository.get_problem("P1001")).title == "Updated A+B Problem"

    asyncio.run(run_test())


def test_repository_deletes_problem(tmp_path):
    async def run_test():
        repository = ProblemRepository(tmp_path / "problems")
        await repository.initialize()
        problem = make_problem()

        await repository.add_problem(problem)
        await repository.delete_problem("P1001")

        with pytest.raises(ProblemNotFoundError):
            await repository.get_problem("P1001")

    asyncio.run(run_test())
