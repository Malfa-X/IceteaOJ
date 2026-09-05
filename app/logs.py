import asyncio
from datetime import datetime
from app.models import AccessLog, SubmissionLog

class SubmissionLogNotFoundError(Exception):
    pass


class SubmissionLogRepository:
    def __init__(self):
        self._logs: dict[str, SubmissionLog] = {}
        self._lock = asyncio.Lock()

    async def save_log(self, log: SubmissionLog) -> None:
        async with self._lock:
            self._logs[log.submission_id] = log

    async def get_log(self, submission_id: str) -> SubmissionLog:
        async with self._lock:
            if submission_id not in self._logs:
                raise SubmissionLogNotFoundError(submission_id)

            return self._logs[submission_id]

class AccessLogRepository:
    def __init__(self):
        self._logs: list[AccessLog] = []
        self._lock = asyncio.Lock()

    async def record(
        self,
        user_id: str,
        problem_id: str,
        status: str,
    ) -> None:
        async with self._lock:
            self._logs.append(
                AccessLog(
                    user_id=user_id,
                    problem_id=problem_id,
                    time=datetime.now().strftime("%Y-%m-%d"),
                    status=status,
                )
            )

    async def list_logs(
        self,
        user_id: str | None = None,
        problem_id: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> list[AccessLog]:
        async with self._lock:
            logs = list(self._logs)

            if user_id is not None:
                logs = [log for log in logs if log.user_id == user_id]

            if problem_id is not None:
                logs = [log for log in logs if log.problem_id == problem_id]

            if page is not None and page_size is not None:
                start = (page - 1) * page_size
                end = start + page_size
                logs = logs[start:end]

            return logs