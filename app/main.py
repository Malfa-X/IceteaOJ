from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.models import Problem, ProblemId
from app.repository import (
    ProblemAlreadyExistsError,
    ProblemNotFoundError,
    ProblemRepository,
    ProblemStorageError,
)


def api_response(code: int, msg: str, data: object | None = None) -> dict:
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }


def create_app(problems_dir: Path | None = None) -> FastAPI:
    repository = ProblemRepository(problems_dir or Path("data/problems"))

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await repository.initialize()
        yield

    app = FastAPI(
        title="IceteaOJ",
        version="0.1.0",
        lifespan=lifespan,
    )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_, __):
        return JSONResponse(
            status_code=400,
            content=api_response(400, "invalid request parameters"),
        )

    @app.exception_handler(ProblemAlreadyExistsError)
    async def problem_exists_handler(_, __):
        return JSONResponse(
            status_code=409,
            content=api_response(409, "problem id already exists"),
        )

    @app.exception_handler(ProblemNotFoundError)
    async def problem_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "problem not found"),
        )

    @app.exception_handler(ProblemStorageError)
    async def storage_error_handler(_, __):
        return JSONResponse(
            status_code=500,
            content=api_response(500, "problem storage error"),
        )

    @app.get("/api/health")
    async def health_check() -> dict:
        return api_response(200, "success", {"status": "ok"})

    @app.get("/api/problems/")
    async def list_problems() -> dict:
        problems = await repository.list_problems()
        data = [problem.model_dump(mode="json") for problem in problems]
        return api_response(200, "success", data)

    @app.post("/api/problems/")
    async def add_problem(problem: Problem) -> dict:
        await repository.add_problem(problem)
        return api_response(200, "add success", {"id": problem.id})

    @app.get("/api/problems/{problem_id}")
    async def get_problem(problem_id: Annotated[ProblemId, ApiPath()]) -> dict:
        problem = await repository.get_problem(problem_id)
        return api_response(200, "success", problem.model_dump(mode="json"))

    @app.put("/api/problems/{problem_id}")
    async def update_problem(
        problem_id: Annotated[ProblemId, ApiPath()],
        problem: Problem,
    ):
        if problem_id != problem.id:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "path id and body id must match"),
            )

        await repository.update_problem(problem_id, problem)
        return api_response(200, "update success", {"id": problem.id})

    @app.delete("/api/problems/{problem_id}")
    async def delete_problem(problem_id: Annotated[ProblemId, ApiPath()]) -> dict:
        await repository.delete_problem(problem_id)
        return api_response(200, "delete success", {"id": problem_id})

    return app


app = create_app()

