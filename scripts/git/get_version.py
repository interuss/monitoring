#!/usr/bin/env python3
"""
scripts/git/get_version.py
InterUSS monitoring version representation utility.

This CLI combines and standardizes all repository Git inspection, PEP 440 version derivation,
and upstream organization discovery into a single Standard-Library-only tool.
"""

import argparse
import os
import re
import subprocess
import sys

# Base repository root determination relative to the scripts/git directory.
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))


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
    """
    Determines the organization/owner of the upstream repository.
    Checks 'origin', 'interuss', tracking upstream branch, or defaults to 'unknown'.
    """
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


def get_commit_hash(with_status: bool = True) -> str:
    """
    Returns the current short commit hash, optionally suffixed with '-dirty' or '-localcommit'.
    """
    res = run_git_cmd(["rev-parse", "--short", "HEAD"])
    commit = res.stdout.strip()

    if not with_status:
        return commit

    status_res = run_git_cmd(["status", "--porcelain"], check=False)
    if status_res.stdout.strip():
        return f"{commit}-dirty"

    cherry_res = run_git_cmd(["cherry"], check=False)
    if cherry_res.returncode == 0 and cherry_res.stdout.strip():
        return f"{commit}-localcommit"

    return commit


def get_git_tag_metadata(namespace: str, component: str) -> tuple[str, bool, str, bool]:
    """
    Interrogates Git for component tags, exact boundary matches, commit hash, and workspace state.
    """
    tag_match_pattern = f"{namespace}/{component}/*"

    # 1. Resolve Baseline Tag (--abbrev=0 isolates tag boundary without distance markers)
    baseline_res = run_git_cmd(
        ["describe", "--tags", "--abbrev=0", f"--match={tag_match_pattern}"],
        check=False,
    )
    if baseline_res.returncode == 0 and baseline_res.stdout.strip():
        baseline_tag = baseline_res.stdout.strip()
    else:
        baseline_tag = f"{namespace}/{component}/v0.0.0"

    # 2. Determine Exact-Match Tag Boundary
    exact_res = run_git_cmd(
        ["describe", "--tags", f"--match={tag_match_pattern}", "--exact-match"],
        check=False,
    )
    is_exact_tag_boundary = exact_res.returncode == 0

    # 3. Retrieve Commit-Hash & Workspace Dirtiness
    hash_res = run_git_cmd(["rev-parse", "--short", "HEAD"])
    commit_hash = hash_res.stdout.strip()

    status_res = run_git_cmd(["status", "--porcelain"], check=False)
    is_dirty = bool(status_res.stdout.strip())

    return baseline_tag, is_exact_tag_boundary, commit_hash, is_dirty


def derive_pep440_version(namespace: str, component: str) -> str:
    """
    Validates Git tag and metadata against strict InterUSS SemVer and Pre-Release conventions,
    generating a canonical PEP 440 version string.
    """
    baseline_tag, is_exact_tag_boundary, commit_hash, is_dirty = get_git_tag_metadata(
        namespace, component
    )

    strict_tag_regex = re.compile(
        rf"^{re.escape(namespace)}/{re.escape(component)}/v(?P<semver>\d+\.\d+\.\d+)(?P<rc_segment>-rc\d+)?$"
    )
    malformed_prerelease_regex = re.compile(
        rf"^{re.escape(namespace)}/{re.escape(component)}/v\d+\.\d+\.\d+-(.*)$"
    )

    malformed_match = malformed_prerelease_regex.match(baseline_tag)
    strict_match = strict_tag_regex.match(baseline_tag)

    if malformed_match and not strict_match:
        invalid_suffix = malformed_match.group(1)
        raise ValueError(
            f"Strict Validation Failure: Tag '{baseline_tag}' contains a non-conforming pre-release "
            f"or release-candidate identifier ('-{invalid_suffix}'). InterUSS pre-release tags "
            f"must strictly utilize the lowercase, hyphen-prefixed '-rc[N]' convention (e.g., '-rc1'). "
            "Case-insensitivity, arbitrary alpha-segments, or alternative delimiters are prohibited."
        )

    if not strict_match:
        raise ValueError(
            f"Strict Validation Failure: Tag '{baseline_tag}' violates InterUSS repository SemVer conventions. "
            f"Expected Pattern: '{namespace}/{component}/vX.Y.Z[-rcN]'."
        )

    semver = strict_match.group("semver")
    rc_segment = strict_match.group("rc_segment")

    # Map pre-release: '0.31.0' + '-rc2' -> '0.31.0rc2'
    pep440_base = semver
    if rc_segment:
        pep440_base = f"{semver}{rc_segment.lstrip('-')}"

    # If this is not an exact match on the release tag, or if workspace is dirty, append local version
    metadata_segments = []
    if not is_exact_tag_boundary:
        metadata_segments.append(f"g{commit_hash.lstrip('g')}")
    if is_dirty:
        metadata_segments.append("dirty")

    if metadata_segments:
        return f"{pep440_base}+{'.'.join(metadata_segments)}"

    return pep440_base


def get_git_version(namespace: str, component: str, long_format: bool = False) -> str:
    """
    Derives the version string conforming to the legacy version.sh format.
    """
    tag_match_pattern = f"{namespace}/{component}/*"
    describe_res = run_git_cmd(
        ["describe", "--abbrev=1", "--tags", f"--match={tag_match_pattern}"],
        check=False,
    )
    commit = run_git_cmd(["rev-parse", "--short", "HEAD"]).stdout.strip()
    status_res = run_git_cmd(["status", "--porcelain"], check=False)
    dirty_suffix = "-dirty" if status_res.stdout.strip() else ""

    if describe_res.returncode != 0 or not describe_res.stdout.strip():
        last_version = f"v0.0.0-{commit}"
    else:
        full_tag = describe_res.stdout.strip()
        last_version = full_tag.split("/")[-1]
        if "-" in last_version:
            # Commits added on top of tag
            base_part = last_version.split("-")[0]
            last_version = f"{base_part}-{commit}"

    version_str = f"{last_version}{dirty_suffix}"
    if long_format:
        return f"{namespace}/{component}/{version_str}"
    return version_str


def main() -> None:
    parser = argparse.ArgumentParser(
        description="InterUSS monitoring version representation utility."
    )
    parser.add_argument(
        "--format",
        choices=[
            "pep440",
            "imagetag",
            "owner",
            "commit",
        ],
        default="pep440",
        help=(
            "Explicit output format.\n"
            "  pep440: Canonical PEP440 version (e.g., '0.31.0', '0.31.0rc1', '0.31.0+gd56bb4d.dirty'); fails for malformed pre-releases (-RC, -1.2, etc.).\n"
            "  imagetag: docker image tag version (e.g., 'v0.31.0', 'v0.31.0-d56bb4d417-dirty').\n"
            "  owner: Repository organization name (e.g., 'interuss', 'Orbitalize').\n"
            "  commit: Current commit hash with status suffix (e.g., 'd56bb4d-dirty', 'd56bb4d-localcommit')."
        ),
    )

    args = parser.parse_args()

    if args.format == "owner":
        print(get_upstream_owner())
        sys.exit(0)

    elif args.format == "commit":
        print(get_commit_hash(with_status=True))
        sys.exit(0)

    component = "monitoring"
    owner = get_upstream_owner()

    if args.format == "imagetag":
        print(get_git_version(owner, component, long_format=False))
        sys.exit(0)

    elif args.format == "pep440":
        try:
            pep440_version = derive_pep440_version(owner, component)
            print(pep440_version)
            sys.exit(0)
        except ValueError as e:
            print(f"[InterUSS Version Validation ERROR] {e}", file=sys.stderr)
            sys.exit(1)

    else:
        raise ValueError(f"Invalid requested format '{args.format}'")


if __name__ == "__main__":
    main()
