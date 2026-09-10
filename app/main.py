from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, Path as ApiPath, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.middleware.sessions import SessionMiddleware
from app.ai_authoring import (
    AiModelConfigNotFoundError,
    AiModelConfigRepository,
    AiProblemTaskNotFoundError,
    AiProblemTaskRepository,
    generate_problem_task,
)
from app.judge import judge_submission
from app.languages import LanguageAlreadyExistsError, LanguageNotFoundError, LanguageRegistry
from app.models import (
    AiModelConfig,
    AiProblemRequest,
    AiProblemTaskStatus,
    LanguageConfig,
    LogVisibilityUpdate,
    Problem,
    ProblemId,
    SubmissionCreate,
    SubmissionStatus,
    UserCreate,
    UserLogin,
    UserPublic,
    UserRole,
    UserRoleUpdate,
    SubmissionLog,
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
from app.logs import (
    AccessLogRepository,
    SubmissionLogNotFoundError,
    SubmissionLogRepository,
)

def api_response(code: int, msg: str, data: object | None = None) -> dict:
    """让所有接口返回统一格式"""
    return {
        "code": code,
        "msg": msg,
        "data": data,
    }


def create_app(problems_dir: Path | None = None) -> FastAPI:
    """创建整个FastAPI应用"""
    repository = ProblemRepository(problems_dir or Path("data/problems"))
    language_registry = LanguageRegistry()
    submission_repository = SubmissionRepository()
    user_repository = UserRepository()
    submission_log_repository = SubmissionLogRepository()
    access_log_repository = AccessLogRepository()
    user_repository = UserRepository()
    ai_config_repository = AiModelConfigRepository()
    ai_task_repository = AiProblemTaskRepository()

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        """应用启动时执行，初始化题目目录和默认用户（3个）"""
        await repository.initialize()
        await user_repository.initialize()
        yield

    async def run_judge_task(submission_id: str, submission_create: SubmissionCreate):
        """基于给出的submission后台判断题目"""
        try:
            problem = await repository.get_problem(submission_create.problem_id)
            language = language_registry.get_language(submission_create.language)
            result = await judge_submission(problem, submission_create, language)
            submission = await submission_repository.get_submission(submission_id)

            await submission_log_repository.save_log(
                SubmissionLog(
                    submission_id=submission_id,
                    problem_id=submission.problem_id,
                    user_id=submission.user_id,
                    details=result.details,
                    score=result.score,
                    counts=result.counts,
                )
            )

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
        """从请求session中找出当前登录用户，返回的user是从repository找的"""
        user_id = request.session.get("user_id")
        if user_id is None:
            return None

        return await user_repository.get_user(user_id)

    def require_permission_response() -> JSONResponse:
        """返回提醒403权限不足的信息"""
        return JSONResponse(
            status_code=403,
            content=api_response(403, "permission denied"),
        )

    def is_admin(user: UserPublic) -> bool:
        """判断当前登录用户是否为admin"""
        return user.role == UserRole.ADMIN

    def require_login_response() -> JSONResponse:
        """返回提醒401未登录的信息"""
        return JSONResponse(
            status_code=401,
            content=api_response(401, "not logged in"),
        )

    def submission_to_create(submission) -> SubmissionCreate:
        """基于submission创建新submission"""
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
        """负责判断subimssion list请求参数是否符合要求"""
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

    def validate_pagination_params(
        page: int | None,
        page_size: int | None,
    ) -> JSONResponse | None:
        """负责判断paginator的参数是否符合要求"""
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

    async def submission_to_summary(submission) -> dict:
        user = await user_repository.get_user(submission.user_id)

        item = {
            "submission_id": submission.submission_id,
            "status": submission.status,
            "user_id": submission.user_id,
            "username": user.username,
            "problem_id": submission.problem_id,
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

    @app.exception_handler(SubmissionLogNotFoundError)
    async def submission_log_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "submission log not found"),
        )

    @app.exception_handler(AiModelConfigNotFoundError)
    async def ai_model_config_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "AI model config not found"),
        )

    @app.exception_handler(AiProblemTaskNotFoundError)
    async def ai_problem_task_not_found_handler(_, __):
        return JSONResponse(
            status_code=404,
            content=api_response(404, "AI problem task not found"),
        )

    @app.get("/api/health") # 健康检查
    async def health_check() -> dict:
        return api_response(200, "success", {"status": "ok"})

    @app.get("/api/problems/") # 获得题目列表
    async def list_problems(request: Request):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        problems = await repository.list_problems()
        data = [problem.model_dump(mode="json") for problem in problems]
        return api_response(200, "success", data)

    @app.get("/api/submissions/") # 获得提交列表
    async def list_submissions(
        request: Request,
        user_id: str | None = None,
        problem_id: str | None = None,
        status: SubmissionStatus | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if user_id is not None and user_id != current_user.user_id and not is_admin(current_user):
            return require_permission_response()

        if user_id is None and not is_admin(current_user):
            user_id = current_user.user_id
        
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

        data = [
            await submission_to_summary(submission)
            for submission in submissions
        ]

        return api_response(
            200,
            "success",
            {
                "total": total,
                "submissions": data,
            },
        )

    @app.get("/api/submissions/{submission_id}/log") # 获得特定提交id的提交日志
    async def get_submission_log(request: Request, submission_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        submission = await submission_repository.get_submission(submission_id)
        problem = await repository.get_problem(submission.problem_id)

        allowed = (
            submission.user_id == current_user.user_id
            or is_admin(current_user)
            or problem.public_cases
        )

        if not allowed:
            await access_log_repository.record(
                user_id=current_user.user_id,
                problem_id=submission.problem_id,
                status="403",
            )
            return require_permission_response()

        log = await submission_log_repository.get_log(submission_id)

        await access_log_repository.record(
            user_id=current_user.user_id,
            problem_id=submission.problem_id,
            status="200",
        )

        return api_response(
            200,
            "success",
            {
                "details": [case.model_dump(mode="json") for case in log.details],
                "score": log.score,
                "counts": log.counts,
            },
        )

    @app.get("/api/submissions/{submission_id}") # 获得特定提交id的提交信息
    async def get_submission(request: Request, submission_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        submission = await submission_repository.get_submission(submission_id)

        if submission.user_id != current_user.user_id and not is_admin(current_user):
            return require_permission_response()
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

    @app.get("/api/languages/") # 获得支持的语言列表
    async def list_languages() -> dict:
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        return api_response(
            200,
            "success",
            {
                "name": language_registry.list_languages(),
            },
        )

    @app.get("/api/problems/{problem_id}") # 获得问题内容
    async def get_problem(request: Request, problem_id: Annotated[ProblemId, ApiPath()]):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        problem = await repository.get_problem(problem_id)
        return api_response(200, "success", problem.model_dump(mode="json"))

    @app.get("/api/users/") # 获得用户列表
    async def list_users(
        request: Request,
        page: int | None = None,
        page_size: int | None = None,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

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

        if page is None and page_size is not None:
            page = 1

        total, users = await user_repository.list_users(page=page, page_size=page_size)

        return api_response(
            200,
            "success",
            {
                "total": total,
                "users": [user.model_dump(mode="json") for user in users],
            },
        )

    @app.get("/api/users/{user_id}") # 获得用户信息
    async def get_user(request: Request, user_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if current_user.user_id != user_id and not is_admin(current_user):
            return require_permission_response()

        user = await user_repository.get_user(user_id)
        return api_response(200, "success", user.model_dump(mode="json"))

    @app.post("/api/languages/") # 添加支持编程语言
    async def add_language(request: Request, language: LanguageConfig):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        language_registry.register_language(language)
        return api_response(
            200,
            "language registered",
            {
                "name": language.name,
            },
        )

    @app.get("/api/logs/access/") # 获得访问评测日志本身的日志
    async def list_access_logs(
        request: Request,
        user_id: str | None = None,
        problem_id: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        error_response = validate_pagination_params(page=page, page_size=page_size)
        if error_response is not None:
            return error_response

        if page is None and page_size is not None:
            page = 1

        logs = await access_log_repository.list_logs(
            user_id=user_id,
            problem_id=problem_id,
            page=page,
            page_size=page_size,
        )

        return api_response(
            200,
            "success",
            [log.model_dump(mode="json") for log in logs],
        )

    @app.get("/api/ai/config") # 获得当前ai配置信息
    async def get_ai_config(request: Request):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        config = ai_config_repository.public_config()
        return api_response(200, "success", config.model_dump(mode="json"))

    @app.put("/api/ai/config") # 更新当前ai配置信息
    async def update_ai_config(request: Request, config: AiModelConfig):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        public_config = await ai_config_repository.set_config(config)
        return api_response(
            200,
            "AI model config updated",
            public_config.model_dump(mode="json"),
        )

    @app.post("/api/ai/tasks/") # 创建ai出题任务
    async def create_ai_problem_task(
        request: Request,
        authoring_request: AiProblemRequest,
        background_tasks: BackgroundTasks,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        task = await ai_task_repository.create_task(
            user_id=current_user.user_id,
            request=authoring_request,
        )

        background_tasks.add_task(
            generate_problem_task,
            task.task_id,
            ai_task_repository,
            ai_config_repository,
        )

        return api_response(
            200,
            "AI problem task created",
            task.model_dump(mode="json"),
        )

    @app.get("/api/ai/tasks/{task_id}") # 获得ai出题任务信息
    async def get_ai_problem_task(request: Request, task_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        task = await ai_task_repository.get_task(task_id)
        if task.user_id != current_user.user_id and not is_admin(current_user):
            return require_permission_response()

        return api_response(200, "success", task.model_dump(mode="json"))

    @app.put("/api/ai/tasks/{task_id}/cancel") # 取消ai出题任务
    async def cancel_ai_problem_task(request: Request, task_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        task = await ai_task_repository.get_task(task_id)
        if task.user_id != current_user.user_id and not is_admin(current_user):
            return require_permission_response()

        if task.status in {
            AiProblemTaskStatus.SUCCESS,
            AiProblemTaskStatus.FAILED,
            AiProblemTaskStatus.CANCELLED,
        }:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "task already finished"),
            )

        cancelled = await ai_task_repository.cancel_task(task_id)
        return api_response(
            200,
            "AI problem task cancelled",
            cancelled.model_dump(mode="json"),
        )

    @app.post("/api/ai/tasks/{task_id}/apply") # 将ai出的题加到data/problem即题目列表中
    async def apply_ai_problem_task(request: Request, task_id: str):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        task = await ai_task_repository.get_task(task_id)
        if task.status != AiProblemTaskStatus.SUCCESS or task.result is None:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "AI problem task is not ready"),
            )

        await repository.add_problem(task.result)
        return api_response(
            200,
            "AI problem applied",
            {"id": task.result.id},
        )

    @app.post("/api/problems/") # 添加题目
    async def add_problem(request: Request, problem: Problem):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        await repository.add_problem(problem)
        return api_response(200, "add success", {"id": problem.id})

    @app.put("/api/problems/{problem_id}") # 修改题目
    async def update_problem(
        request: Request,
        problem_id: Annotated[ProblemId, ApiPath()],
        problem: Problem,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if problem_id != problem.id:
            return JSONResponse(
                status_code=400,
                content=api_response(400, "path id and body id must match"),
            )

        await repository.update_problem(problem_id, problem)
        return api_response(200, "update success", {"id": problem.id})

    @app.post("/api/submissions/") # 创建提交
    async def add_submission(
        request: Request,
        submission_create: SubmissionCreate,
        background_tasks: BackgroundTasks,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        await repository.get_problem(submission_create.problem_id)
        language_registry.get_language(submission_create.language)
        submission = await submission_repository.create_submission(
            problem_id=submission_create.problem_id,
            language=submission_create.language,
            code=submission_create.code,
            user_id=current_user.user_id,
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

    @app.post("/api/users/") # 注册
    async def register_user(user_create: UserCreate) -> dict:
        user = await user_repository.create_user(user_create)
        return api_response(
            200,
            "register success",
            user.model_dump(mode="json"),
        )

    @app.post("/api/auth/login") # 登录
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

    @app.post("/api/auth/logout") # 登出
    async def logout(request: Request):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        request.session.clear()
        return api_response(200, "logout success", None)

    @app.put("/api/problems/{problem_id}/log_visibility") # 更新log的visibility
    async def update_problem_log_visibility(
        request: Request,
        problem_id: Annotated[ProblemId, ApiPath()],
        visibility: LogVisibilityUpdate,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        problem = await repository.update_log_visibility(
            problem_id,
            visibility.public_cases,
        )

        return api_response(
            200,
            "log visibility updated",
            {
                "problem_id": problem.id,
                "public_cases": problem.public_cases,
            },
        )

    @app.put("/api/submissions/{submission_id}/rejudge") # 重新测评特定提交
    async def rejudge_submission(
        request: Request,
        submission_id: str,
        background_tasks: BackgroundTasks,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()
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

    @app.put("/api/users/{user_id}/role") # 更新用户身份
    async def update_user_role(
        request: Request,
        user_id: str,
        role_update: UserRoleUpdate,
    ):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        user = await user_repository.update_role(user_id, role_update.role)

        return api_response(
            200,
            "role updated",
            {
                "user_id": user.user_id,
                "role": user.role,
            },
        )

    @app.delete("/api/problems/{problem_id}") # 删除问题
    async def delete_problem(request: Request, problem_id: Annotated[ProblemId, ApiPath()]):
        current_user = await get_current_user(request)
        if current_user is None:
            return require_login_response()

        if not is_admin(current_user):
            return require_permission_response()

        await repository.delete_problem(problem_id)
        return api_response(200, "delete success", {"id": problem_id})

    return app


app = create_app()
