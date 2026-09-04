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

