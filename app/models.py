from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints


ProblemId = Annotated[
    str,
    StringConstraints(
        strip_whitespace=True,
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9_-]+$",
    ),
]


class TestCase(BaseModel):
    model_config = ConfigDict(extra="forbid")

    input: str
    output: str


class Problem(BaseModel):
    """题目"""
    model_config = ConfigDict(extra="forbid")

    id: ProblemId
    title: str = Field(min_length=1)
    description: str = Field(min_length=1)
    input_description: str = Field(min_length=1)
    output_description: str = Field(min_length=1)
    samples: list[TestCase] = Field(min_length=1)
    constraints: str = Field(min_length=1)
    testcases: list[TestCase] = Field(min_length=1)

    hint: str = ""
    source: str = ""
    tags: list[str] = Field(default_factory=list)
    time_limit: float = Field(default=3.0, gt=0)
    memory_limit: int = Field(default=128, gt=0)
    author: str = ""
    difficulty: str = ""
    public_cases: bool = False


class ProblemSummary(BaseModel):
    id: str
    title: str

class SubmissionStatus(StrEnum):
    """提交状态"""
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class TestCaseStatus(StrEnum):
    """提交代码测试后测试点状态"""
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    RE = "RE"
    CE = "CE"
    UNK = "UNK"


class SubmissionCreate(BaseModel):
    """提交请求"""
    model_config = ConfigDict(extra="forbid")

    problem_id: ProblemId
    language: str = Field(min_length=1)
    code: str = Field(min_length=1)


class CompileInfo(BaseModel):
    result: str
    message: str = ""


class RunInfo(BaseModel):
    result: str
    message: str = ""


class TestCaseResult(BaseModel):
    """单个测试点结果"""
    id: int
    result: TestCaseStatus
    time: float = Field(default=0.0, ge=0)
    memory: int = Field(default=0, ge=0)


class JudgeResult(BaseModel):
    """题目判断结果"""
    score: int = Field(ge=0)
    counts: int = Field(ge=0)
    compile_info: CompileInfo | None = None
    run_info: RunInfo | None = None
    error_info: str = ""
    details: list[TestCaseResult] = Field(default_factory=list)

class SubmissionLog(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    problem_id: ProblemId
    user_id: str
    details: list[TestCaseResult] = Field(default_factory=list)
    score: int = Field(ge=0)
    counts: int = Field(ge=0)

class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    user_id: str = "anonymous"
    problem_id: ProblemId
    language: str
    code: str
    status: SubmissionStatus = SubmissionStatus.PENDING
    score: int | None = None
    counts: int | None = None
    compile_info: CompileInfo | None = None
    run_info: RunInfo | None = None
    error_info: str | None = None

class LanguageConfig(BaseModel):
    """语言配置模型，里面有默认TL和ML"""
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    file_ext: str = Field(min_length=1)
    compile_cmd: str = ""
    run_cmd: str = Field(min_length=1)
    time_limit: float = Field(default=3.0, gt=0)
    memory_limit: int = Field(default=128, gt=0)

class UserRole(StrEnum):
    USER = "user"
    ADMIN = "admin"
    BANNED = "banned"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6)


class UserLogin(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=40)
    password: str = Field(min_length=6)


class UserRoleUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: UserRole


class User(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    username: str
    password_hash: str
    join_time: str
    role: UserRole = UserRole.USER
    submit_count: int = 0
    resolve_count: int = 0


class UserPublic(BaseModel):
    user_id: str
    username: str
    join_time: str
    role: UserRole
    submit_count: int
    resolve_count: int

class LogVisibilityUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    public_cases: bool = False


class AccessLog(BaseModel):
    user_id: str
    problem_id: ProblemId
    action: str = "view_logs"
    time: str
    status: str


class AiProblemTaskStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AiModelConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_url: str = Field(min_length=1)
    model_name: str = Field(min_length=1)
    api_key: str = Field(min_length=1)
    input_price_per_1k: float = Field(default=0.0, ge=0)
    output_price_per_1k: float = Field(default=0.0, ge=0)


class AiModelConfigPublic(BaseModel):
    provider_url: str
    model_name: str
    api_key: str
    input_price_per_1k: float
    output_price_per_1k: float


class AiProblemRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    topic: str = Field(min_length=1)
    difficulty: str = Field(min_length=1)
    requirements: str = ""
    testcase_count: int = Field(default=5, ge=1, le=20)


class AiTokenUsage(BaseModel):
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    input_cost: float = Field(default=0.0, ge=0)
    output_cost: float = Field(default=0.0, ge=0)
    total_cost: float = Field(default=0.0, ge=0)
    currency: str = "USD"
    pricing_note: str = ""


class AiProblemTask(BaseModel):
    model_config = ConfigDict(extra="forbid")

    task_id: str
    user_id: str
    request: AiProblemRequest
    status: AiProblemTaskStatus = AiProblemTaskStatus.PENDING
    progress: int = Field(default=0, ge=0, le=100)
    message: str = ""
    result: Problem | None = None
    token_usage: AiTokenUsage = Field(default_factory=AiTokenUsage)
    error_info: str = ""
    created_at: str
    updated_at: str
