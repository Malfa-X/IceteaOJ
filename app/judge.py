import asyncio
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from app.models import (
    JudgeResult,
    LanguageConfig,
    Problem,
    RunInfo,
    SubmissionCreate,
    TestCaseResult,
    TestCaseStatus,
)


def normalize_output(output: str) -> str:
    return "\n".join(line.rstrip() for line in output.rstrip().splitlines())


async def judge_submission(
    problem: Problem,
    submission: SubmissionCreate,
    language: LanguageConfig,
) -> JudgeResult:
    details = []
    score = 0
    counts = len(problem.testcases) * 10

    with TemporaryDirectory() as temp_dir:
        source_path = Path(temp_dir) / f"main{language.file_ext}"
        source_path.write_text(submission.code, encoding="utf-8")

        for index, testcase in enumerate(problem.testcases, start=1):
            case_result = await run_single_case(
                source_path=source_path,
                run_cmd=language.run_cmd,
                testcase_input=testcase.input,
                expected_output=testcase.output,
                time_limit=problem.time_limit or language.time_limit,
                memory_limit=problem.memory_limit or language.memory_limit,
                case_id=index,
            )
            details.append(case_result)

            if case_result.result == TestCaseStatus.AC:
                score += 10

    return JudgeResult(
        score=score,
        counts=counts,
        run_info=RunInfo(
            result="finished",
            message=f"{len(problem.testcases)} test cases finished",
        ),
        details=details,
    )


async def run_single_case(
    source_path: Path,
    run_cmd: str,
    testcase_input: str,
    expected_output: str,
    time_limit: float,
    memory_limit: int,
    case_id: int,
) -> TestCaseResult:
    command = build_command(run_cmd, source_path)
    start_time = time.perf_counter()

    try:
        process = await asyncio.create_subprocess_exec(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await asyncio.wait_for(
            process.communicate(testcase_input.encode()),
            timeout=time_limit,
        )

        elapsed_time = time.perf_counter() - start_time

        if process.returncode != 0:
            return TestCaseResult(
                id=case_id,
                result=TestCaseStatus.RE,
                time=elapsed_time,
                memory=0,
            )

        actual_output = normalize_output(stdout.decode(errors="replace"))
        normalized_expected = normalize_output(expected_output)

        if actual_output == normalized_expected:
            result = TestCaseStatus.AC
        else:
            result = TestCaseStatus.WA

        return TestCaseResult(
            id=case_id,
            result=result,
            time=elapsed_time,
            memory=0,
        )

    except asyncio.TimeoutError:
        process.kill()
        await process.wait()

        elapsed_time = time.perf_counter() - start_time
        return TestCaseResult(
            id=case_id,
            result=TestCaseStatus.TLE,
            time=elapsed_time,
            memory=0,
        )
    except OSError:
        elapsed_time = time.perf_counter() - start_time
        return TestCaseResult(
            id=case_id,
            result=TestCaseStatus.UNK,
            time=elapsed_time,
            memory=0,
        )


def build_command(run_cmd: str, source_path: Path) -> list[str]:
    command_text = run_cmd.format(src=str(source_path))
    return command_text.split()