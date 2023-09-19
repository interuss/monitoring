import inspect
import os
import subprocess
from typing import Optional

import monitoring


_commit_hash: Optional[str] = None
_code_version: Optional[str] = None
_github_base_url: Optional[str] = None
_repo_root: Optional[str] = None


def repo_url_of(abspath: str) -> str:
    relpath = os.path.relpath(abspath, start=get_repo_root())
    version = get_commit_hash()
    if version == "unknown":
        version = "main"
    return f"{get_github_base_url()}/blob/{version}/{relpath}"


def get_repo_root() -> str:
    global _repo_root
    if _repo_root is None:
        _repo_root = _retrieve_repo_root()
    return _repo_root


def _retrieve_repo_root() -> str:
    return os.path.split(os.path.split(inspect.getfile(monitoring))[0])[0]


def get_github_base_url() -> str:
    global _github_base_url
    if _github_base_url is None:
        _github_base_url = _retrieve_github_base_url()
    return _github_base_url


def _retrieve_github_base_url() -> str:
    base_url = os.environ.get("MONITORING_GITHUB_ROOT", "")
    if not base_url:
        base_url = "https://github.com/interuss/monitoring"
    return base_url


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
        ["git", "rev-parse", "HEAD"],
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
    if len(commit) > 7:
        commit = commit[0:7]

    process = subprocess.Popen(
        ["git", "status", "-s"], stdout=subprocess.PIPE, universal_newlines=True
    )
    status, _ = process.communicate()
    if process.returncode != 0:
        return commit + "-unknown"
    elif status:
        return commit + "-dirty"
    return commit
