import asyncio

from app.models import SubmissionStatus
from app.submission_repository import SubmissionRepository


def test_repository_lists_submissions_by_newest_first():
    async def run_test():
        repository = SubmissionRepository()

        first = await repository.create_submission(
            problem_id="P1001",
            language="python",
            code="print(1)",
            user_id="alice",
        )
        second = await repository.create_submission(
            problem_id="P1002",
            language="python",
            code="print(2)",
            user_id="bob",
        )

        total, submissions = await repository.list_submissions()

        assert total == 2
        assert [submission.submission_id for submission in submissions] == [
            second.submission_id,
            first.submission_id,
        ]

    asyncio.run(run_test())


def test_repository_filters_submissions_by_user_problem_and_status():
    async def run_test():
        repository = SubmissionRepository()

        first = await repository.create_submission(
            problem_id="P1001",
            language="python",
            code="print(1)",
            user_id="alice",
        )
        second = await repository.create_submission(
            problem_id="P1001",
            language="python",
            code="print(2)",
            user_id="bob",
        )

        await repository.finish_submission(
            first.submission_id,
            status=SubmissionStatus.SUCCESS,
            score=10,
            counts=10,
        )

        total, submissions = await repository.list_submissions(
            user_id="alice",
            problem_id="P1001",
            status=SubmissionStatus.SUCCESS,
        )

        assert total == 1
        assert submissions[0].submission_id == first.submission_id

        total, submissions = await repository.list_submissions(
            user_id="bob",
            problem_id="P1001",
            status=SubmissionStatus.SUCCESS,
        )

        assert total == 0
        assert submissions == []

    asyncio.run(run_test())


def test_repository_paginates_submissions():
    async def run_test():
        repository = SubmissionRepository()

        for index in range(5):
            await repository.create_submission(
                problem_id="P1001",
                language="python",
                code=f"print({index})",
                user_id="alice",
            )

        total, submissions = await repository.list_submissions(page=2, page_size=2)

        assert total == 5
        assert [submission.submission_id for submission in submissions] == ["3", "2"]

    asyncio.run(run_test())