#!/usr/bin/env python3

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import pytest

# Ensure repository root is in sys.path so scripts.git is importable without PYTHONPATH=.
_repo_root = str(Path(__file__).resolve().parents[2])
if _repo_root not in sys.path:
    sys.path.insert(0, _repo_root)

from scripts.git.get_version import (  # noqa: E402
    compute_image_tag,
    derive_pep440_version,
    get_git_info,
    get_pep440_version,
    get_upstream_owner,
    main,
    run_git_cmd,
)

type CommandResult = tuple[int, str] | Exception
type CommandMap = dict[tuple[str, ...], CommandResult]


# ==============================================================================
# Git Environment Representation
# ==============================================================================


@dataclass(frozen=True)
class GitEnvironment:
    """Represents a hypothetical Git repository environment for testing."""

    name: str
    description: str
    origin_url: str | None = "https://github.com/interuss/monitoring.git"
    interuss_url: str | None = None
    upstream_branch: str | None = None
    upstream_branch_raises: bool = False
    baseline_tag: str | None = "interuss/monitoring/v0.31.0"
    is_exact_tag_boundary: bool = True
    has_uncommitted_changes: bool = False
    has_local_commits: bool = False
    full_commit_hash: str = "abcdef0123456789abcdef0123456789abcdef01"
    git_available: bool = True

    @property
    def short_commit_hash(self) -> str:
        return self.full_commit_hash[0:7]

    @property
    def command_map(self) -> CommandMap:
        """Constructs the command response map corresponding to this environment."""
        if not self.git_available:
            error = subprocess.SubprocessError("git: command not found")
            return {
                ("rev-parse", "--abbrev-ref", "@{upstream}"): error,
                ("remote", "get-url", "origin"): error,
                ("remote", "get-url", "interuss"): error,
                ("describe",): error,
                ("rev-parse", "HEAD"): error,
                ("rev-parse", "--short", "HEAD"): error,
                ("status", "--porcelain"): error,
                ("cherry",): error,
            }

        cmd_map: CommandMap = {}

        # 1. Upstream branch resolution (rev-parse --abbrev-ref @{upstream})
        if self.upstream_branch_raises:
            cmd_map[("rev-parse", "--abbrev-ref", "@{upstream}")] = (
                subprocess.SubprocessError("upstream branch query error")
            )
        elif self.upstream_branch:
            cmd_map[("rev-parse", "--abbrev-ref", "@{upstream}")] = (
                0,
                f"{self.upstream_branch}\n",
            )
        else:
            cmd_map[("rev-parse", "--abbrev-ref", "@{upstream}")] = (
                128,
                "fatal: no upstream configured for branch\n",
            )

        # 2. Remote URLs (origin and interuss)
        if self.origin_url:
            cmd_map[("remote", "get-url", "origin")] = (
                0,
                f"{self.origin_url}\n",
            )
        else:
            cmd_map[("remote", "get-url", "origin")] = (
                2,
                "error: No such remote 'origin'\n",
            )

        if self.interuss_url:
            cmd_map[("remote", "get-url", "interuss")] = (
                0,
                f"{self.interuss_url}\n",
            )
        else:
            cmd_map[("remote", "get-url", "interuss")] = (
                2,
                "error: No such remote 'interuss'\n",
            )

        # 3. Git tag description (baseline tag and exact match)
        if self.baseline_tag is not None:
            cmd_map[("describe", "--tags", "--abbrev=0")] = (
                0,
                f"{self.baseline_tag}\n",
            )
            if self.is_exact_tag_boundary:
                cmd_map[("describe", "--tags", "--exact-match")] = (
                    0,
                    f"{self.baseline_tag}\n",
                )
            else:
                cmd_map[("describe", "--tags", "--exact-match")] = (
                    128,
                    "fatal: no tag exactly matches\n",
                )
        else:
            cmd_map[("describe", "--tags", "--abbrev=0")] = (
                128,
                "fatal: No names found, cannot describe anything.\n",
            )
            cmd_map[("describe", "--tags", "--exact-match")] = (
                128,
                "fatal: no tag exactly matches\n",
            )

        # 4. Commit hashes
        cmd_map[("rev-parse", "HEAD")] = (0, f"{self.full_commit_hash}\n")
        cmd_map[("rev-parse", "--short", "HEAD")] = (
            0,
            f"{self.short_commit_hash}\n",
        )

        # 5. Workspace uncommitted changes (dirty state)
        if self.has_uncommitted_changes:
            cmd_map[("status", "--porcelain")] = (
                0,
                " M scripts/git/get_version.py\n",
            )
        else:
            cmd_map[("status", "--porcelain")] = (0, "")

        # 6. Local-only unpushed commits (cherry)
        if self.has_local_commits:
            cmd_map[("cherry",)] = (0, f"+ {self.full_commit_hash}\n")
        else:
            cmd_map[("cherry",)] = (0, "")

        return cmd_map


def create_git_environment(
    name: str = "custom_env",
    description: str = "Custom test environment",
    *,
    origin_url: str | None = "https://github.com/interuss/monitoring.git",
    interuss_url: str | None = None,
    upstream_branch: str | None = None,
    upstream_branch_raises: bool = False,
    baseline_tag: str | None = "interuss/monitoring/v0.31.0",
    is_exact_tag_boundary: bool = True,
    has_uncommitted_changes: bool = False,
    has_local_commits: bool = False,
    full_commit_hash: str = "abcdef0123456789abcdef0123456789abcdef01",
    git_available: bool = True,
) -> GitEnvironment:
    """Factory function producing a GitEnvironment based on repository characteristics."""
    return GitEnvironment(
        name=name,
        description=description,
        origin_url=origin_url,
        interuss_url=interuss_url,
        upstream_branch=upstream_branch,
        upstream_branch_raises=upstream_branch_raises,
        baseline_tag=baseline_tag,
        is_exact_tag_boundary=is_exact_tag_boundary,
        has_uncommitted_changes=has_uncommitted_changes,
        has_local_commits=has_local_commits,
        full_commit_hash=full_commit_hash,
        git_available=git_available,
    )


# ==============================================================================
# Specific Named Environments
# ==============================================================================

NOMINAL_RELEASE_ENV = GitEnvironment(
    name="nominal_release",
    description="Clean production release build checked out exactly on an official release tag",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

PRERELEASE_ENV = GitEnvironment(
    name="prerelease",
    description="Clean build checked out exactly on an official pre-release candidate tag",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0-rc1",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

COMMITS_AHEAD_CLEAN_ENV = GitEnvironment(
    name="commits_ahead_clean",
    description="Clean working directory with commits pushed ahead of the latest tag",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0",
    is_exact_tag_boundary=False,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

WIP_DEVELOPER_ENV = GitEnvironment(
    name="wip_developer",
    description="Active developer fork environment with local unpushed commits and uncommitted changes",
    origin_url="git@github.com:devuser/monitoring.git",
    interuss_url="https://github.com/interuss/monitoring.git",
    baseline_tag="devuser/monitoring/v0.31.0",
    is_exact_tag_boundary=False,
    has_uncommitted_changes=True,
    has_local_commits=True,
)

DIRTY_ONLY_ENV = GitEnvironment(
    name="dirty_only",
    description="Workspace directly on a release tag but with uncommitted local edits",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=True,
    has_local_commits=False,
)

LOCAL_COMMIT_ONLY_ENV = GitEnvironment(
    name="local_commit_only",
    description="Workspace with unpushed commits ahead of tag, but clean working tree",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0",
    is_exact_tag_boundary=False,
    has_uncommitted_changes=False,
    has_local_commits=True,
)

INTERUSS_REMOTE_FALLBACK_ENV = GitEnvironment(
    name="interuss_remote_fallback",
    description="Environment where origin remote is missing, falling back to interuss remote",
    origin_url=None,
    interuss_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

UPSTREAM_TRACKING_BRANCH_ENV = GitEnvironment(
    name="upstream_tracking_branch",
    description="Environment with no remotes, falling back to upstream tracking branch @{upstream}",
    origin_url=None,
    interuss_url=None,
    upstream_branch="upstream-org/main",
    baseline_tag="upstream-org/monitoring/v0.31.0",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

UPSTREAM_BRANCH_ERROR_ENV = GitEnvironment(
    name="upstream_branch_error",
    description="Environment where git rev-parse @{upstream} raises an error and no remotes exist",
    origin_url=None,
    interuss_url=None,
    upstream_branch_raises=True,
    baseline_tag=None,
    is_exact_tag_boundary=False,
)

NO_TAGS_ENV = GitEnvironment(
    name="no_tags",
    description="Initial repository state without any matching tags created yet",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag=None,
    is_exact_tag_boundary=False,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

NON_GITHUB_REMOTE_ENV = GitEnvironment(
    name="non_github_remote",
    description="Repository with a GitLab/custom non-GitHub remote URL",
    origin_url="https://gitlab.com/custom-org/monitoring.git",
    baseline_tag="custom-org/monitoring/v1.0.0",
    is_exact_tag_boundary=True,
    has_uncommitted_changes=False,
    has_local_commits=False,
)

MALFORMED_PRERELEASE_TAG_ENV = GitEnvironment(
    name="malformed_prerelease_tag",
    description="Repository where tag has an invalid pre-release identifier (-alpha1 instead of -rcN)",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/v0.31.0-alpha1",
    is_exact_tag_boundary=True,
)

NON_SEMVER_TAG_ENV = GitEnvironment(
    name="non_semver_tag",
    description="Repository where tag does not conform to SemVer pattern",
    origin_url="https://github.com/interuss/monitoring.git",
    baseline_tag="interuss/monitoring/release-2026",
    is_exact_tag_boundary=True,
)

GIT_UNAVAILABLE_ENV = GitEnvironment(
    name="git_unavailable",
    description="Environment where git binary is missing or directory is not a git repo",
    git_available=False,
)


# ==============================================================================
# Mock Execution Engine & Fixtures
# ==============================================================================


def _matches_pattern(args: list[str], pattern: tuple[str, ...]) -> bool:
    """Matches git command arguments against a pattern tuple."""
    if tuple(args) == pattern:
        return True
    if len(args) >= len(pattern) and tuple(args[: len(pattern)]) == pattern:
        return True
    if "describe" in pattern:
        if "--exact-match" in pattern:
            return "describe" in args and "--exact-match" in args
        if "--abbrev=0" in pattern:
            return "describe" in args and "--abbrev=0" in args
        return args[0] == "describe"
    return False


def make_mock_run_git_cmd(
    command_map: CommandMap,
) -> Callable[[list[str], bool], subprocess.CompletedProcess[str]]:
    """Builds a mock run_git_cmd function from a command map."""

    def fake_run_git_cmd(
        args: list[str], check: bool = True
    ) -> subprocess.CompletedProcess[str]:
        for pattern, result in command_map.items():
            if _matches_pattern(args, pattern):
                if isinstance(result, Exception):
                    raise result
                rc, stdout = result
                if check and rc != 0:
                    raise subprocess.CalledProcessError(
                        rc, ["git"] + args, output=stdout
                    )
                return subprocess.CompletedProcess(
                    args=["git"] + args,
                    returncode=rc,
                    stdout=stdout,
                    stderr="",
                )
        if check:
            raise subprocess.CalledProcessError(1, ["git"] + args, output="")
        return subprocess.CompletedProcess(
            args=["git"] + args,
            returncode=1,
            stdout="",
            stderr=f"unmapped git command: {args}",
        )

    return fake_run_git_cmd


@pytest.fixture
def apply_git_env(
    monkeypatch: pytest.MonkeyPatch,
) -> Callable[[GitEnvironment], GitEnvironment]:
    """Applies a GitEnvironment to scripts.git.get_version.run_git_cmd for the test duration."""
    # Ensure MONITORING_VERSION is clear by default
    monkeypatch.delenv("MONITORING_VERSION", raising=False)

    def _apply(env: GitEnvironment) -> GitEnvironment:
        fake_run = make_mock_run_git_cmd(env.command_map)
        monkeypatch.setattr("scripts.git.get_version.run_git_cmd", fake_run)
        return env

    return _apply


# ==============================================================================
# Suite A: Tool Output in Clean Release Environments
# ==============================================================================


def test_nominal_release_environment(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies tool outputs in a clean release environment checked out on a tag."""
    env = apply_git_env(NOMINAL_RELEASE_ENV)

    assert get_upstream_owner() == "interuss"

    info = get_git_info("monitoring")
    assert info.upstream_owner == "interuss"
    assert info.component == "monitoring"
    assert info.baseline_tag == "interuss/monitoring/v0.31.0"
    assert info.is_exact_tag_boundary is True
    assert info.is_dirty is False
    assert info.is_localcommit is False
    assert info.full_commit_hash == env.full_commit_hash
    assert info.short_commit_hash == env.short_commit_hash

    # PEP 440 version is canonical and tag-only without metadata
    assert derive_pep440_version(info) == "0.31.0"
    assert get_pep440_version() == "0.31.0"

    # Image tag matches exact tag
    assert compute_image_tag(info) == "v0.31.0"

    # Invariant check: CLI invocation outputs
    monkeypatch.setattr("sys.argv", ["get_version.py", "--format", "commitsha1"])
    main()
    assert capsys.readouterr().out.strip() == env.full_commit_hash

    monkeypatch.setattr("sys.argv", ["get_version.py", "--format", "imagetag"])
    main()
    assert capsys.readouterr().out.strip() == "v0.31.0"

    monkeypatch.setattr("sys.argv", ["get_version.py", "--format", "pep440"])
    main()
    assert capsys.readouterr().out.strip() == "0.31.0"


def test_prerelease_environment(apply_git_env) -> None:
    """Verifies that official -rcN pre-releases translate into canonical PEP 440 rc versions."""
    apply_git_env(PRERELEASE_ENV)

    info = get_git_info("monitoring")
    assert get_pep440_version() == "0.31.0rc1"
    assert compute_image_tag(info) == "v0.31.0-rc1"


# ==============================================================================
# Suite B: Tool Output in Development and WIP Environments
# ==============================================================================


def test_commits_ahead_clean_environment(apply_git_env) -> None:
    """Verifies that commits ahead of a release tag append the short commit hash."""
    env = apply_git_env(COMMITS_AHEAD_CLEAN_ENV)

    info = get_git_info("monitoring")
    assert info.is_exact_tag_boundary is False
    assert info.is_dirty is False
    assert info.is_localcommit is False

    assert get_pep440_version() == f"0.31.0+{env.short_commit_hash}"
    assert compute_image_tag(info) == f"v0.31.0-{env.short_commit_hash}"


def test_wip_developer_environment(apply_git_env) -> None:
    """Verifies that an active fork developer environment tags dirty and localcommit status."""
    env = apply_git_env(WIP_DEVELOPER_ENV)

    assert get_upstream_owner() == "devuser"

    info = get_git_info("monitoring")
    assert info.upstream_owner == "devuser"
    assert info.is_exact_tag_boundary is False
    assert info.is_dirty is True
    assert info.is_localcommit is True

    expected_pep440 = f"0.31.0+{env.short_commit_hash}.dirtylocalcommit"
    expected_imagetag = f"v0.31.0-{env.short_commit_hash}-dirty-localcommit"

    assert get_pep440_version() == expected_pep440
    assert compute_image_tag(info) == expected_imagetag


def test_dirty_only_environment(apply_git_env) -> None:
    """Verifies that uncommitted edits directly on a tag append dirty metadata."""
    apply_git_env(DIRTY_ONLY_ENV)

    info = get_git_info("monitoring")
    assert info.is_exact_tag_boundary is True
    assert info.is_dirty is True
    assert info.is_localcommit is False

    assert get_pep440_version() == "0.31.0+dirty"
    assert compute_image_tag(info) == "v0.31.0-dirty"


def test_local_commit_only_environment(apply_git_env) -> None:
    """Verifies that unpushed commits ahead of tag append commit hash and localcommit metadata."""
    env = apply_git_env(LOCAL_COMMIT_ONLY_ENV)

    info = get_git_info("monitoring")
    assert info.is_exact_tag_boundary is False
    assert info.is_dirty is False
    assert info.is_localcommit is True

    assert get_pep440_version() == f"0.31.0+{env.short_commit_hash}.localcommit"
    assert compute_image_tag(info) == f"v0.31.0-{env.short_commit_hash}-localcommit"


# ==============================================================================
# Suite C: Upstream Remote Resolution Branches
# ==============================================================================


def test_interuss_remote_fallback(apply_git_env) -> None:
    """Verifies fallback to interuss remote when origin remote is absent."""
    apply_git_env(INTERUSS_REMOTE_FALLBACK_ENV)
    assert get_upstream_owner() == "interuss"
    assert get_pep440_version() == "0.31.0"


def test_upstream_tracking_branch_fallback(apply_git_env) -> None:
    """Verifies fallback to git @{upstream} tracking branch when no remotes are present."""
    apply_git_env(UPSTREAM_TRACKING_BRANCH_ENV)
    assert get_upstream_owner() == "upstream-org"
    assert get_pep440_version() == "0.31.0"


def test_upstream_branch_error_fallback(apply_git_env) -> None:
    """Verifies graceful handling when @{upstream} query fails and remotes are absent."""
    apply_git_env(UPSTREAM_BRANCH_ERROR_ENV)
    assert get_upstream_owner() == "unknown"


def test_non_github_remote_url(apply_git_env) -> None:
    """Verifies owner extraction from non-GitHub (e.g. GitLab/internal) remote URLs."""
    apply_git_env(NON_GITHUB_REMOTE_ENV)
    assert get_upstream_owner() == "custom-org"
    assert get_pep440_version() == "1.0.0"


# ==============================================================================
# Suite D: Error Handling and Tag Validation
# ==============================================================================


def test_no_tags_environment(apply_git_env) -> None:
    """Verifies fallback to v0.0.0 when no matching tags exist in repository history."""
    env = apply_git_env(NO_TAGS_ENV)

    info = get_git_info("monitoring")
    assert info.baseline_tag == "interuss/monitoring/v0.0.0"
    assert info.is_exact_tag_boundary is False

    assert get_pep440_version() == f"0.0.0+{env.short_commit_hash}"
    assert compute_image_tag(info) == f"v0.0.0-{env.short_commit_hash}"


def test_malformed_prerelease_tag_fails_validation(apply_git_env) -> None:
    """Verifies strict InterUSS validation error on non-conforming pre-release suffix."""
    apply_git_env(MALFORMED_PRERELEASE_TAG_ENV)

    with pytest.raises(
        ValueError,
        match="Strict Validation Failure: Tag '.*' contains a non-conforming",
    ):
        get_pep440_version()


def test_non_semver_tag_fails_validation(apply_git_env) -> None:
    """Verifies strict InterUSS validation error on non-SemVer tag."""
    apply_git_env(NON_SEMVER_TAG_ENV)

    with pytest.raises(
        ValueError, match="violates InterUSS repository SemVer conventions"
    ):
        get_pep440_version()


# ==============================================================================
# Suite E: Fallback Chain When Git Is Unavailable
# ==============================================================================


def test_git_unavailable_with_monitoring_version_override(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that MONITORING_VERSION environment variable takes highest priority."""
    apply_git_env(GIT_UNAVAILABLE_ENV)
    monkeypatch.setenv("MONITORING_VERSION", "2.5.0")
    assert get_pep440_version() == "2.5.0"


def test_git_unavailable_fallback_to_version_file(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_pep440_version falls back to monitoring/_version.py when git is absent."""
    apply_git_env(GIT_UNAVAILABLE_ENV)

    fake_version_file = tmp_path / "_version.py"
    fake_version_file.write_text('__version__ = "0.28.4"\nversion = __version__\n')
    monkeypatch.setattr(
        "scripts.git.get_version.VERSION_FILE_PATH", str(fake_version_file)
    )

    assert get_pep440_version() == "0.28.4"


def test_git_unavailable_fallback_to_pkg_info(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_pep440_version falls back to PKG-INFO when _version.py is absent."""
    apply_git_env(GIT_UNAVAILABLE_ENV)

    # Point BASE_DIR to tmp_path with a PKG-INFO file and no _version.py
    monkeypatch.setattr(
        "scripts.git.get_version.VERSION_FILE_PATH",
        str(tmp_path / "nonexistent.py"),
    )
    monkeypatch.setattr("scripts.git.get_version.BASE_DIR", str(tmp_path))

    pkg_info = tmp_path / "PKG-INFO"
    pkg_info.write_text(
        "Metadata-Version: 2.1\nName: interuss_monitoring\nVersion: 0.19.2\n"
    )

    assert get_pep440_version() == "0.19.2"


def test_git_unavailable_ultimate_fallback(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that get_pep440_version returns 0.0.0 when no version sources are found."""
    apply_git_env(GIT_UNAVAILABLE_ENV)

    monkeypatch.setattr(
        "scripts.git.get_version.VERSION_FILE_PATH",
        str(tmp_path / "nonexistent.py"),
    )
    monkeypatch.setattr("scripts.git.get_version.BASE_DIR", str(tmp_path))

    assert get_pep440_version() == "0.0.0"


# ==============================================================================
# Suite F: Integration and CLI Invariants
# ==============================================================================


def test_real_run_git_cmd() -> None:
    """Verifies that unmocked run_git_cmd successfully executes the local git binary."""
    res = run_git_cmd(["--version"])
    assert res.returncode == 0
    assert "git version" in res.stdout


def test_main_invalid_format(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that an unsupported format option is rejected by the CLI parser."""
    apply_git_env(NOMINAL_RELEASE_ENV)
    monkeypatch.setattr("sys.argv", ["get_version.py", "--format", "invalid_format"])
    with pytest.raises(SystemExit) as exc_info:
        main()
    assert exc_info.value.code != 0


def test_derive_pep440_version_env_var_override(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that MONITORING_VERSION overrides derive_pep440_version directly."""
    apply_git_env(NOMINAL_RELEASE_ENV)
    monkeypatch.setenv("MONITORING_VERSION", "9.9.9")
    info = get_git_info("monitoring")
    assert derive_pep440_version(info) == "9.9.9"


def test_git_unavailable_corrupted_files_fall_through(
    apply_git_env: Callable[[GitEnvironment], GitEnvironment],
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies that unreadable version files or PKG-INFO gracefully fall through to 0.0.0."""
    apply_git_env(GIT_UNAVAILABLE_ENV)
    bad_version_dir = tmp_path / "_version_dir"
    bad_version_dir.mkdir()
    monkeypatch.setattr(
        "scripts.git.get_version.VERSION_FILE_PATH", str(bad_version_dir)
    )
    monkeypatch.setattr("scripts.git.get_version.BASE_DIR", str(tmp_path))
    (tmp_path / "PKG-INFO").mkdir()
    assert get_pep440_version() == "0.0.0"


def test_upstream_owner_unknown_when_url_parts_insufficient(apply_git_env) -> None:
    """Verifies fallback to 'unknown' when remote URL cannot be split into organization parts."""
    env = GitEnvironment(
        name="single_part_remote",
        description="Remote URL with single part",
        origin_url="unparseable",
        full_commit_hash="abcdef0123456789abcdef0123456789abcdef01",
    )
    apply_git_env(env)
    assert get_upstream_owner() == "unknown"
