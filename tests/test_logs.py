import asyncio
import pytest
from app.logs import (
    AccessLogRepository,
    SubmissionLogNotFoundError,
    SubmissionLogRepository,
)
from app.models import SubmissionLog, TestCaseResult, TestCaseStatus


def make_log() -> SubmissionLog:
    return SubmissionLog(
        submission_id="1",
        problem_id="P1001",
        user_id="alice",
        details=[
            TestCaseResult(id=1, result=TestCaseStatus.AC, time=0.01, memory=10),
            TestCaseResult(id=2, result=TestCaseStatus.WA, time=0.02, memory=11),
        ],
        score=10,
        counts=20,
    )


def test_repository_saves_and_gets_submission_log():
    async def run_test():
        repository = SubmissionLogRepository()
        log = make_log()

        await repository.save_log(log)

        loaded_log = await repository.get_log("1")
        assert loaded_log == log

    asyncio.run(run_test())


def test_repository_overwrites_submission_log():
    async def run_test():
        repository = SubmissionLogRepository()

        await repository.save_log(make_log())
        updated_log = make_log().model_copy(update={"score": 20})
        await repository.save_log(updated_log)

        loaded_log = await repository.get_log("1")
        assert loaded_log.score == 20

    asyncio.run(run_test())


def test_repository_rejects_missing_submission_log():
    async def run_test():
        repository = SubmissionLogRepository()

        with pytest.raises(SubmissionLogNotFoundError):
            await repository.get_log("missing")

    asyncio.run(run_test())

def test_access_log_repository_records_and_filters_logs():
    async def run_test():
        repository = AccessLogRepository()

        await repository.record(user_id="alice", problem_id="P1001", status="200")
        await repository.record(user_id="bob", problem_id="P1002", status="403")

        alice_logs = await repository.list_logs(user_id="alice")
        assert len(alice_logs) == 1
        assert alice_logs[0].problem_id == "P1001"
        assert alice_logs[0].action == "view_logs"
        assert alice_logs[0].status == "200"

        p1002_logs = await repository.list_logs(problem_id="P1002")
        assert len(p1002_logs) == 1
        assert p1002_logs[0].user_id == "bob"

    asyncio.run(run_test())