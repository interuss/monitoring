import os
import subprocess
from typing import Optional


_commit_hash: Optional[str] = None
_code_version: Optional[str] = None


def get_commit_hash() -> str:
    global _commit_hash
    if _commit_hash is None:
        _commit_hash = _retrieve_commit_hash()
    return _commit_hash


def _retrieve_commit_hash() -> str:
    env_hash = os.environ.get("GIT_COMMIT_HASH", "")
    if env_hash:
        return env_hash

    process = subprocess.Popen(
        ["git", "rev-parse", "--short", "HEAD"],
        stdout=subprocess.PIPE,
        universal_newlines=True,
    )
    commit, _ = process.communicate()
    if process.returncode != 0:
        return "unknown"
    commit = commit.strip()
    if "not a git repository" in commit:
        return "unknown"
    return commit


def get_code_version() -> str:
    global _code_version
    if _code_version is None:
        _code_version = _retrieve_code_version()
    return _code_version


def _retrieve_code_version() -> str:
    env_version = os.environ.get("MONITORING_VERSION", "")
    if env_version:
        return env_version
    env_version = os.environ.get("CODE_VERSION", "")
    if env_version:
        return env_version

    commit = get_commit_hash()

    process = subprocess.Popen(
        ["git", "status", "-s"], stdout=subprocess.PIPE, universal_newlines=True
    )
    status, _ = process.communicate()
    if process.returncode != 0:
        return commit + "-unknown"
    elif status:
        return commit + "-dirty"
    return commit
