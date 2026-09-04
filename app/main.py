from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Path as ApiPath
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.judge import judge_submission
from app.languages import LanguageAlreadyExistsError, LanguageNotFoundError, LanguageRegistry
from app.models import Problem, ProblemId, SubmissionCreate, SubmissionStatus, LanguageConfig
from app.submission_repository import SubmissionNotFoundError, SubmissionRepository
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
    language_registry = LanguageRegistry()
    submission_repository = SubmissionRepository()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await repository.initialize()
        yield

    async def run_judge_task(submission_id: str, submission_create: SubmissionCreate):
        try:
            problem = await repository.get_problem(submission_create.problem_id)
            language = language_registry.get_language(submission_create.language)
            result = await judge_submission(problem, submission_create, language)

            await submission_repository.finish_submission(
                submission_id=submission_id,
                status=SubmissionStatus.SUCCESS,
                score=result.score,
                counts=result.counts,
                compile_info=result.compile_info,
                run_info=result.run_info,
                error_info=result.error_info,
            )
        except Exception as error:
            await submission_repository.finish_submission(
                submission_id=submission_id,
                status=SubmissionStatus.ERROR,
                error_info="judge task failed",
            )

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

    @app.exception_handler(LanguageNotFoundError)
    async def language_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "language not found"),
        )

    @app.exception_handler(SubmissionNotFoundError)
    async def submission_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "submission not found"),
        )

    @app.exception_handler(LanguageAlreadyExistsError)
    async def language_exists_handler(_, __):
        return JSONResponse(
            status_code=409,
            content=api_response(409, "language already exists"),
        )

    @app.get("/api/health")
    async def health_check() -> dict:
        return api_response(200, "success", {"status": "ok"})

    @app.get("/api/problems/")
    async def list_problems() -> dict:
        problems = await repository.list_problems()
        data = [problem.model_dump(mode="json") for problem in problems]
        return api_response(200, "success", data)

    @app.get("/api/submissions/{submission_id}")
    async def get_submission(submission_id: str) -> dict:
        submission = await submission_repository.get_submission(submission_id)

        if submission.status == SubmissionStatus.PENDING:
            data = {
                "submission_id": submission.submission_id,
                "status": submission.status,
            }
        else:
            data = {
                "submission_id": submission.submission_id,
                "status": submission.status,
                "score": submission.score,
                "counts": submission.counts,
                "compile_info": (
                    submission.compile_info.model_dump(mode="json")
                    if submission.compile_info is not None
                    else None
                ),
                "run_info": (
                    submission.run_info.model_dump(mode="json")
                    if submission.run_info is not None
                    else None
                ),
                "error_info": submission.error_info,
            }

        return api_response(200, "success", data)

    @app.get("/api/languages/")
    async def list_languages() -> dict:
        return api_response(
            200,
            "success",
            {
                "name": language_registry.list_languages(),
            },
        )

    @app.post("/api/languages/")
    async def add_language(language: LanguageConfig) -> dict:
        language_registry.register_language(language)
        return api_response(
            200,
            "language registered",
            {
                "name": language.name,
            },
        )

    @app.post("/api/problems/")
    async def add_problem(problem: Problem) -> dict:
        await repository.add_problem(problem)
        return api_response(200, "add success", {"id": problem.id})

    @app.post("/api/submissions/")
    async def add_submission(
        submission_create: SubmissionCreate,
        background_tasks: BackgroundTasks,
    ) -> dict:
        await repository.get_problem(submission_create.problem_id)
        language_registry.get_language(submission_create.language)

        submission = await submission_repository.create_submission(
            problem_id=submission_create.problem_id,
            language=submission_create.language,
            code=submission_create.code,
        )

        background_tasks.add_task(
            run_judge_task,
            submission.submission_id,
            submission_create,
        )

        return api_response(
            200,
            "success",
            {
                "submission_id": submission.submission_id,
                "status": submission.status,
            },
        )

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

