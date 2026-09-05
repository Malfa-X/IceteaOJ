import asyncio

from app.models import SubmissionLog


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