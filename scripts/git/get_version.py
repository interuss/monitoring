#!/usr/bin/env python3
"""
InterUSS monitoring version representation utility.

This CLI combines and standardizes all repository Git inspection, PEP 440 version derivation,
and upstream organization discovery into a single Standard-Library-only tool.
"""

import argparse
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Any

# Base repository root determination relative to the scripts/git directory.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
VERSION_FILE_PATH = os.path.join(BASE_DIR, "monitoring", "_version.py")


@dataclass
class GitInfo:
    upstream_owner: str
    """Organization/owner of the upstream repository."""

    component: str
    """Component identifier ("monitoring" for this repository)."""

    baseline_tag: str
    """Tag content without status information.  E.g., interuss/monitoring/v0.0.0"""

    is_exact_tag_boundary: bool
    """True when the current state lies exactly on a valid tag (and therefore is suitable for release)."""

    full_commit_hash: str
    """Full SHAA-1 commit hash."""

    short_commit_hash: str
    """Current commit hash in short form."""

    is_dirty: bool
    """True when there are uncommitted changes."""

    is_localcommit: bool
    """True when the most recent commit is local-only."""


def run_git_cmd(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """Executes a Git command rooted in the repository workspace."""
    return subprocess.run(
        ["git"] + args,
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=check,
    )


def get_upstream_owner() -> str:
    """Determines the organization/owner of the upstream repository."""
    backup_repo = "https://github.com/unknown/_"
    try:
        upstream_branch = run_git_cmd(
            ["rev-parse", "--abbrev-ref", "@{upstream}"], check=False
        )
        if upstream_branch.returncode == 0 and upstream_branch.stdout.strip():
            backup_repo = f"https://github.com/{upstream_branch.stdout.strip()}"
    except Exception:
        pass

    upstream_repo = ""
    for remote in ["origin", "interuss"]:
        res = run_git_cmd(["remote", "get-url", remote], check=False)
        if res.returncode == 0 and res.stdout.strip():
            upstream_repo = res.stdout.strip()
            break

    if not upstream_repo:
        upstream_repo = backup_repo

    # Normalize SSH/HTTPS URL formats to extract owner:
    # 1. git@github.com:interuss/monitoring.git
    # 2. git@github.com/interuss/monitoring.git
    # 3. https://github.com/interuss/monitoring.git
    # 4. ssh://git@github.com/interuss/monitoring.git
    normalized = upstream_repo.replace(":", "/")
    if "github.com/" in normalized:
        after_gh = normalized.split("github.com/")[-1]
        owner = after_gh.split("/")[0]
        if owner and owner != "unknown":
            return owner

    # Fallback pattern extraction if not github.com explicitly
    parts = [
        p for p in re.split(r"[/:\\]", upstream_repo) if p and not p.endswith(".git")
    ]
    if len(parts) >= 2:
        return parts[-2]

    return "unknown"


def get_git_info(component: str) -> GitInfo:
    """Interrogates git for information relevant to versioning."""

    kwargs: dict[str, Any] = {"component": component}

    upstream_owner = get_upstream_owner()
    kwargs["upstream_owner"] = upstream_owner

    tag_match_pattern = f"{upstream_owner}/{component}/*"

    # Resolve baseline tag (--abbrev=0 isolates tag boundary without distance markers)
    baseline_res = run_git_cmd(
        ["describe", "--tags", "--abbrev=0", f"--match={tag_match_pattern}"],
        check=False,
    )
    if baseline_res.returncode == 0 and baseline_res.stdout.strip():
        kwargs["baseline_tag"] = baseline_res.stdout.strip()
    else:
        kwargs["baseline_tag"] = f"{upstream_owner}/{component}/v0.0.0"

    # Determine exact-match tag boundary
    exact_res = run_git_cmd(
        ["describe", "--tags", f"--match={tag_match_pattern}", "--exact-match"],
        check=False,
    )
    kwargs["is_exact_tag_boundary"] = exact_res.returncode == 0

    # Retrieve the full commit hash
    full_hash_res = run_git_cmd(["rev-parse", "HEAD"])
    kwargs["full_commit_hash"] = full_hash_res.stdout.strip()

    # Retrieve short commit hash
    short_hash_res = run_git_cmd(["rev-parse", "--short", "HEAD"])
    kwargs["short_commit_hash"] = short_hash_res.stdout.strip()

    # Retrieve workspace dirtiness
    status_res = run_git_cmd(["status", "--porcelain"], check=False)
    kwargs["is_dirty"] = bool(status_res.stdout.strip())

    # Retrieve whether commit is local-only
    cherry_res = run_git_cmd(["cherry"], check=False)
    kwargs["is_localcommit"] = cherry_res.returncode == 0 and cherry_res.stdout.strip()

    return GitInfo(**kwargs)


def derive_pep440_version(info: GitInfo) -> str:
    """
    Validates Git tag and metadata against strict InterUSS SemVer and Pre-Release conventions,
    generating a canonical PEP 440 version string.
    """

    env_version = os.environ.get("MONITORING_VERSION")
    if env_version:
        return env_version

    strict_tag_regex = re.compile(
        rf"^{re.escape(info.upstream_owner)}/{re.escape(info.component)}/v(?P<semver>\d+\.\d+\.\d+)(?P<rc_segment>-rc\d+)?$"
    )
    malformed_prerelease_regex = re.compile(
        rf"^{re.escape(info.upstream_owner)}/{re.escape(info.component)}/v\d+\.\d+\.\d+-(.*)$"
    )

    malformed_match = malformed_prerelease_regex.match(info.baseline_tag)
    strict_match = strict_tag_regex.match(info.baseline_tag)

    if malformed_match and not strict_match:
        invalid_suffix = malformed_match.group(1)
        raise ValueError(
            f"Strict Validation Failure: Tag '{info.baseline_tag}' contains a non-conforming pre-release "
            f"or release-candidate identifier ('-{invalid_suffix}'). InterUSS pre-release tags "
            f"must strictly utilize the lowercase, hyphen-prefixed '-rc[N]' convention (e.g., '-rc1'). "
            "Case-insensitivity, arbitrary alpha-segments, or alternative delimiters are prohibited."
        )

    if not strict_match:
        raise ValueError(
            f"Strict Validation Failure: Tag '{info.baseline_tag}' violates InterUSS repository SemVer conventions. "
            f"Expected Pattern: '{info.upstream_owner}/{info.component}/vX.Y.Z[-rcN]'."
        )

    semver = strict_match.group("semver")
    rc_segment = strict_match.group("rc_segment")

    # Map pre-release: '0.31.0' + '-rc2' -> '0.31.0rc2'
    pep440_base = semver
    if rc_segment:
        pep440_base = f"{semver}{rc_segment.lstrip('-')}"

    # If this is not an exact match on the release tag, or if workspace is dirty, append local version
    metadata_segments = []
    if not info.is_exact_tag_boundary:
        metadata_segments.append(info.short_commit_hash)
    if info.is_dirty or info.is_localcommit:
        metadata_segments.append(
            ("dirty" if info.is_dirty else "")
            + ("localcommit" if info.is_localcommit else "")
        )

    if metadata_segments:
        return f"{pep440_base}+{'.'.join(metadata_segments)}"
    else:
        return pep440_base


def compute_image_tag(info: GitInfo) -> str:
    """Computes the semantic version string with which a docker image should be tagged."""

    tag = info.baseline_tag.split("/")[-1]

    build_parts = []
    if not info.is_exact_tag_boundary:
        build_parts.append(info.short_commit_hash)
    if info.is_dirty or info.is_localcommit:
        build_parts.append(
            ("dirty" if info.is_dirty else "")
            + ("localcommit" if info.is_localcommit else "")
        )
    if build_parts:
        tag += "+" + ".".join(build_parts)
    return tag


def get_pep440_version(
    component: str = "monitoring",
) -> str:
    """
    Returns the PEP 440 version string, checking in order:
    1. MONITORING_VERSION environment variable override.
    2. Git metadata via get_git_info and derive_pep440_version.
    3. Existing version file (if Git is unavailable, e.g. in an extracted sdist).
    4. PKG-INFO metadata (if present).
    5. Fallback '0.0.0'.
    """
    env_version = os.environ.get("MONITORING_VERSION")
    if env_version:
        return env_version

    try:
        info = get_git_info(component)
        return derive_pep440_version(info)
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        pass

    if os.path.exists(VERSION_FILE_PATH):
        try:
            with open(VERSION_FILE_PATH) as f:
                for line in f:
                    if line.startswith("__version__ = "):
                        return line.split('"')[1]
        except Exception:
            pass

    pkg_info_file = os.path.join(BASE_DIR, "PKG-INFO")
    if os.path.exists(pkg_info_file):
        try:
            with open(pkg_info_file) as f:
                for line in f:
                    if line.startswith("Version: "):
                        return line.split("Version: ", 1)[1].strip()
        except Exception:
            pass

    return "0.0.0"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="InterUSS monitoring version representation utility."
    )
    parser.add_argument(
        "--format",
        choices=[
            "pep440",
            "imagetag",
            "commitsha1",
        ],
        default="pep440",
        help=(
            "Explicit output format.\n"
            "  pep440: Canonical PEP440 version (e.g., '0.31.0', '0.31.0rc1', '0.31.0+gd56bb4d.dirty'); fails for malformed pre-releases (-RC, -1.2, etc.).\n"
            "  imagetag: docker image tag version (e.g., 'v0.31.0', 'v0.31.0-d56bb4d417-dirty').\n"
            "  commitsha1: Current commit full hash abbreviation without any status suffix (e.g., 'd56bb4d417242e0c29bd6b64837aa8bf5adad487')."
        ),
    )

    args = parser.parse_args()

    if args.format == "commitsha1":
        info = get_git_info("monitoring")
        print(info.full_commit_hash)

    elif args.format == "imagetag":
        info = get_git_info("monitoring")
        print(compute_image_tag(info))

    elif args.format == "pep440":
        print(get_pep440_version())

    else:
        raise ValueError(f"Invalid requested format '{args.format}'")


if __name__ == "__main__":
    main()
