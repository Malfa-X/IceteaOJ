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


class ProblemSummary(BaseModel):
    id: str
    title: str

class SubmissionStatus(StrEnum):
    PENDING = "pending"
    SUCCESS = "success"
    ERROR = "error"


class TestCaseStatus(StrEnum):
    AC = "AC"
    WA = "WA"
    TLE = "TLE"
    MLE = "MLE"
    RE = "RE"
    CE = "CE"
    UNK = "UNK"


class SubmissionCreate(BaseModel):
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
    id: int
    result: TestCaseStatus
    time: float = Field(default=0.0, ge=0)
    memory: int = Field(default=0, ge=0)


class JudgeResult(BaseModel):
    score: int = Field(ge=0)
    counts: int = Field(ge=0)
    compile_info: CompileInfo | None = None
    run_info: RunInfo | None = None
    error_info: str = ""
    details: list[TestCaseResult] = Field(default_factory=list)


class Submission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    submission_id: str
    problem_id: ProblemId
    language: str
    code: str
    status: SubmissionStatus = SubmissionStatus.PENDING
    score: int | None = None
    counts: int | None = None
    compile_info: CompileInfo | None = None
    run_info: RunInfo | None = None
    error_info: str | None = None