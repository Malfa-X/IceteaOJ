import asyncio
import contextlib
import subprocess
import sys
import threading
import time
from pathlib import Path
from tempfile import TemporaryDirectory

import psutil

from app.models import (
    CompileInfo,
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
        exe_path = Path(temp_dir) / executable_name("main")
        source_path.write_text(submission.code, encoding="utf-8")

        if language.compile_cmd:
            compile_result = await compile_source(
                compile_cmd=language.compile_cmd,
                source_path=source_path,
                exe_path=exe_path,
                time_limit=max(language.time_limit, 10.0),
            )
            if compile_result.result != "success":
                return JudgeResult(
                    score=0,
                    counts=counts,
                    compile_info=compile_result,
                    run_info=RunInfo(result="not_started", message="compile failed"),
                    error_info=compile_result.message,
                    details=[
                        TestCaseResult(
                            id=index,
                            result=TestCaseStatus.CE,
                        )
                        for index in range(1, len(problem.testcases) + 1)
                    ],
                )
        else:
            compile_result = None

        for index, testcase in enumerate(problem.testcases, start=1):
            case_result = await run_single_case(
                source_path=source_path,
                exe_path=exe_path,
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
        compile_info=compile_result,
        run_info=RunInfo(
            result="finished",
            message=f"{len(problem.testcases)} test cases finished",
        ),
        details=details,
    )

async def run_single_case(
    source_path: Path,
    exe_path: Path,
    run_cmd: str,
    testcase_input: str,
    expected_output: str,
    time_limit: float,
    memory_limit: int,
    case_id: int,
) -> TestCaseResult:
    command = build_command(run_cmd, source_path, exe_path)

    def run_sync() -> TestCaseResult:
        start_time = time.perf_counter()
        memory_state = {"result": None, "memory": 0, "stop": False}

        try:
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

            memory_thread = threading.Thread(
                target=monitor_memory_sync,
                args=(process, memory_limit, memory_state),
                daemon=True,
            )
            memory_thread.start()

            try:
                stdout, stderr = process.communicate(
                    testcase_input.encode(),
                    timeout=time_limit,
                )
            except subprocess.TimeoutExpired:
                kill_process_tree(process)
                process.wait()
                elapsed_time = time.perf_counter() - start_time
                return TestCaseResult(
                    id=case_id,
                    result=TestCaseStatus.TLE,
                    time=elapsed_time,
                    memory=0,
                )
            finally:
                memory_state["stop"] = True
                memory_thread.join(timeout=0.2)

            elapsed_time = time.perf_counter() - start_time

            if memory_state["result"] == TestCaseStatus.MLE:
                return TestCaseResult(
                    id=case_id,
                    result=TestCaseStatus.MLE,
                    time=elapsed_time,
                    memory=memory_state["memory"],
                )

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

        except OSError:
            elapsed_time = time.perf_counter() - start_time
            return TestCaseResult(
                id=case_id,
                result=TestCaseStatus.UNK,
                time=elapsed_time,
                memory=0,
            )

    return await asyncio.to_thread(run_sync)

async def compile_source(
    compile_cmd: str,
    source_path: Path,
    exe_path: Path,
    time_limit: float,
) -> CompileInfo:
    command = build_command(compile_cmd, source_path, exe_path)

    def compile_sync() -> CompileInfo:
        try:
            completed = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=time_limit,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return CompileInfo(result="error", message="compile timeout")
        except OSError as error:
            return CompileInfo(result="error", message=str(error))

        if completed.returncode == 0:
            return CompileInfo(result="success", message="")

        return CompileInfo(
            result="error",
            message=completed.stderr.decode(errors="replace")[:2000],
        )

    return await asyncio.to_thread(compile_sync)


def executable_name(name: str) -> str:
    if sys.platform.startswith("win"):
        return f"{name}.exe"

    return name

def build_command(run_cmd: str, source_path: Path, exe_path: Path) -> list[str]:
    command_text = run_cmd.format(src=str(source_path), exe=str(exe_path))
    return command_text.split()

async def monitor_memory(process, memory_limit: int, state: dict) -> None:
    try:
        parent = psutil.Process(process.pid)

        while process.returncode is None:
            processes = [parent] + parent.children(recursive=True)
            memory = 0

            for child in processes:
                with contextlib.suppress(psutil.Error):
                    memory += child.memory_info().rss

            memory_mb = memory / 1024 / 1024
            state["memory"] = max(state.get("memory", 0), int(memory_mb))

            if memory_mb > memory_limit:
                state["result"] = TestCaseStatus.MLE
                kill_process_tree(process)
                return

            await asyncio.sleep(0.02)
    except psutil.Error:
        return


def kill_process_tree(process) -> None:
    with contextlib.suppress(psutil.Error):
        parent = psutil.Process(process.pid)
        for child in parent.children(recursive=True):
            child.kill()
        parent.kill()

    with contextlib.suppress(ProcessLookupError):
        process.kill()


def monitor_memory_sync(process, memory_limit: int, state: dict) -> None:
    try:
        parent = psutil.Process(process.pid)

        while process.poll() is None and not state["stop"]:
            processes = [parent] + parent.children(recursive=True)
            memory = 0

            for child in processes:
                with contextlib.suppress(psutil.Error):
                    memory += child.memory_info().rss

            memory_mb = memory / 1024 / 1024
            state["memory"] = max(state.get("memory", 0), int(memory_mb))

            if memory_mb > memory_limit:
                state["result"] = TestCaseStatus.MLE
                kill_process_tree(process)
                return

            time.sleep(0.02)
    except psutil.Error:
        return
