import asyncio
from itertools import count

from app.models import (
    CompileInfo,
    RunInfo,
    Submission,
    SubmissionStatus,
)


class SubmissionNotFoundError(Exception):
    pass


class SubmissionRepository:
    def __init__(self):
        self._submissions: dict[str, Submission] = {}
        self._id_counter = count(1)
        self._lock = asyncio.Lock()

    async def create_submission(
        self,
        problem_id: str,
        language: str,
        code: str,
        user_id: str = "anonymous",
    ) -> Submission:
        async with self._lock:
            submission_id = str(next(self._id_counter))
            submission = Submission(
                submission_id=submission_id,
                user_id=user_id,
                problem_id=problem_id,
                language=language,
                code=code,
            )
            self._submissions[submission_id] = submission
            return submission

    async def get_submission(self, submission_id: str) -> Submission:
        async with self._lock:
            if submission_id not in self._submissions:
                raise SubmissionNotFoundError(submission_id)

            return self._submissions[submission_id]

    async def finish_submission(
        self,
        submission_id: str,
        status: SubmissionStatus,
        score: int | None = None,
        counts: int | None = None,
        compile_info: CompileInfo | None = None,
        run_info: RunInfo | None = None,
        error_info: str | None = None,
    ) -> None:
        async with self._lock:
            if submission_id not in self._submissions:
                raise SubmissionNotFoundError(submission_id)

            old_submission = self._submissions[submission_id]
            self._submissions[submission_id] = old_submission.model_copy(
                update={
                    "status": status,
                    "score": score,
                    "counts": counts,
                    "compile_info": compile_info,
                    "run_info": run_info,
                    "error_info": error_info,
                }
            )

    async def list_submissions(
        self,
        user_id: str | None = None,
        problem_id: str | None = None,
        status: SubmissionStatus | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> tuple[int, list[Submission]]:
        async with self._lock:
            submissions = list(self._submissions.values())

            if user_id is not None:
                submissions = [
                    submission
                    for submission in submissions
                    if submission.user_id == user_id
                ]

            if problem_id is not None:
                submissions = [
                    submission
                    for submission in submissions
                    if submission.problem_id == problem_id
                ]

            if status is not None:
                submissions = [
                    submission
                    for submission in submissions
                    if submission.status == status
                ]

            submissions = sorted(
                submissions,
                key=lambda submission: int(submission.submission_id),
                reverse=True,
            )

            total = len(submissions)

            if page is not None and page_size is not None:
                start = (page - 1) * page_size
                end = start + page_size
                submissions = submissions[start:end]

            return total, submissions