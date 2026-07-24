import os
import subprocess

from loguru import logger

from monitoring.benchmarker.configurations.actions import RunCommandActionSpecification
from monitoring.monitorlib.versioning import get_repo_root


def run_command(cmd_spec: RunCommandActionSpecification) -> None:
    repo_root = get_repo_root()
    cwd = cmd_spec.path.replace("$REPO_ROOT", repo_root)
    env = os.environ.copy()
    if "env" in cmd_spec and cmd_spec.env:
        for k, v in cmd_spec.env.items():
            env[k] = str(v)

    logger.info(f"Action: Running command `{cmd_spec.command}` in {cwd}")

    subprocess.run(cmd_spec.command, shell=True, cwd=cwd, env=env, check=True)
