from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Path as ApiPath, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from app.judge import judge_submission
from app.languages import LanguageAlreadyExistsError, LanguageNotFoundError, LanguageRegistry
from app.models import (
    LanguageConfig,
    Problem,
    ProblemId,
    SubmissionCreate,
    SubmissionStatus,
    UserCreate,
    UserLogin,
    UserPublic,
)
from app.submission_repository import SubmissionNotFoundError, SubmissionRepository
from app.repository import (
    ProblemAlreadyExistsError,
    ProblemNotFoundError,
    ProblemRepository,
    ProblemStorageError,
)
from app.users import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserBannedError,
    UserNotFoundError,
    UserRepository,
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
    user_repository = UserRepository()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await repository.initialize()
        await user_repository.initialize()
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

    async def get_current_user(request: Request) -> UserPublic | None:
        user_id = request.session.get("user_id")
        if user_id is None:
            return None

        return await user_repository.get_user(user_id)


    def require_login_response() -> JSONResponse:
        return JSONResponse(
            status_code=401,
            content=api_response(401, "not logged in"),
        )

    def submission_to_create(submission) -> SubmissionCreate:
        return SubmissionCreate(
            problem_id=submission.problem_id,
            language=submission.language,
            code=submission.code,
        )

    def validate_submission_list_params(
        user_id: str | None,
        problem_id: str | None,
        page: int | None,
        page_size: int | None,
    ) -> JSONResponse | None:
        if user_id is None and problem_id is None:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "user_id or problem_id is required"),
            )

        if page is not None and page_size is None:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "page_size is required when page is set"),
            )

        if page is not None and page <= 0:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "page must be positive"),
            )

        if page_size is not None and page_size <= 0:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "page_size must be positive"),
            )

        return None

    def submission_to_summary(submission) -> dict:
        item = {
            "submission_id": submission.submission_id,
            "status": submission.status,
        }

        if submission.status == SubmissionStatus.SUCCESS:
            item["score"] = submission.score
            item["counts"] = submission.counts

        return item

    app = FastAPI(
        title="IceteaOJ",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        SessionMiddleware,
        secret_key="dev-secret-key-change-later",
        same_site="lax",
        https_only=False,
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

    @app.exception_handler(UserAlreadyExistsError)
    async def user_exists_handler(_, __):
        return JSONResponse(
            status_code=400,
            content=api_response(400, "username already exists"),
        )


    @app.exception_handler(UserNotFoundError)
    async def user_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "user not found"),
        )


    @app.exception_handler(InvalidCredentialsError)
    async def invalid_credentials_handler(_, __):
        return JSONResponse(
            status_code=401,
            content=api_response(401, "invalid username or password"),
        )


    @app.exception_handler(UserBannedError)
    async def user_banned_handler(_, __):
        return JSONResponse(
            status_code=403,
            content=api_response(403, "user is banned"),
        )

    @app.get("/api/health")
    async def health_check() -> dict:
        return api_response(200, "success", {"status": "ok"})

    @app.get("/api/problems/")
    async def list_problems() -> dict:
        problems = await repository.list_problems()
        data = [problem.model_dump(mode="json") for problem in problems]
        return api_response(200, "success", data)

    @app.get("/api/submissions/")
    async def list_submissions(
        user_id: str | None = None,
        problem_id: str | None = None,
        status: SubmissionStatus | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict:
        error_response = validate_submission_list_params(
            user_id=user_id,
            problem_id=problem_id,
            page=page,
            page_size=page_size,
        )
        if error_response is not None:
            return error_response

        if page is None and page_size is not None:
            page = 1

        total, submissions = await submission_repository.list_submissions(
            user_id=user_id,
            problem_id=problem_id,
            status=status,
            page=page,
            page_size=page_size,
        )

        data = [submission_to_summary(submission) for submission in submissions]

        return api_response(
            200,
            "success",
            {
                "total": total,
                "submissions": data,
            },
        )

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

    @app.get("/api/problems/{problem_id}")
    async def get_problem(problem_id: Annotated[ProblemId, ApiPath()]) -> dict:
        problem = await repository.get_problem(problem_id)
        return api_response(200, "success", problem.model_dump(mode="json"))

    @app.get("/api/users/{user_id}")
    async def get_user(request: Request, user_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if current_user.user_id != user_id:
            return JSONResponse(
                status_code=403,
                content=api_response(403, "permission denied"),
            )

        user = await user_repository.get_user(user_id)
        return api_response(200, "success", user.model_dump(mode="json"))

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

    @app.post("/api/users/")
    async def register_user(user_create: UserCreate) -> dict:
        user = await user_repository.create_user(user_create)
        return api_response(
            200,
            "register success",
            user.model_dump(mode="json"),
        )

    @app.post("/api/auth/login")
    async def login(request: Request, user_login: UserLogin) -> dict:
        user = await user_repository.authenticate(
            user_login.username,
            user_login.password,
        )
        request.session["user_id"] = user.user_id

        return api_response(
            200,
            "login success",
            {
                "user_id": user.user_id,
                "username": user.username,
                "role": user.role,
            },
        )

    @app.post("/api/auth/logout")
    async def logout(request: Request):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        request.session.clear()
        return api_response(200, "logout success", None)

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

    @app.put("/api/submissions/{submission_id}/rejudge")
    async def rejudge_submission(
        submission_id: str,
        background_tasks: BackgroundTasks,
    ) -> dict:
        submission = await submission_repository.reset_submission(submission_id)
        submission_create = submission_to_create(submission)

        background_tasks.add_task(
            run_judge_task,
            submission.submission_id,
            submission_create,
        )

        return api_response(
            200,
            "rejudge started",
            {
                "submission_id": submission.submission_id,
                "status": submission.status,
            },
        )

    @app.delete("/api/problems/{problem_id}")
    async def delete_problem(problem_id: Annotated[ProblemId, ApiPath()]) -> dict:
        await repository.delete_problem(problem_id)
        return api_response(200, "delete success", {"id": problem_id})

    return app


app = create_app()

