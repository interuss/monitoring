import os
import subprocess

from loguru import logger

from monitoring.benchmarker.configurations.actions.action import (
    RunCommandActionSpecification,
)
from monitoring.monitorlib.versioning import get_repo_root


def run_command(cmd_spec: RunCommandActionSpecification) -> None:
    repo_root = get_repo_root()
    cwd = cmd_spec.path.replace("$REPO_ROOT", repo_root)
    env = os.environ.copy()
    if "env" in cmd_spec and cmd_spec.env:
        for k, v in cmd_spec.env.items():
            env[k] = str(v)

    logger.info(f"Action: Running command `{cmd_spec.command}` in {cwd}")

    # Merge the streams so both are logged live without one filling a pipe while
    # we wait for the other.  Keep the output for the failure traceback as well.
    output: list[str] = []
    with subprocess.Popen(
        cmd_spec.command,
        shell=True,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        errors="replace",
    ) as process:
        assert process.stdout is not None
        for line in process.stdout:
            output.append(line)
            logger.info("Command output: {}", line.rstrip("\r\n"))
        returncode = process.wait()

    if returncode:
        combined_output = "".join(output)
        error = subprocess.CalledProcessError(
            returncode, cmd_spec.command, output=combined_output
        )
        error.add_note(
            f"Working directory: {cwd}\n"
            f"Combined stdout/stderr:\n{combined_output or '(no output)'}"
        )
        raise error
