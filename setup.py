#!/usr/bin/env python3
"""Build configuration for interuss_monitoring."""

import os
import sys

from setuptools import setup

REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_GIT = os.path.join(REPO_ROOT, "scripts", "git")

sys.path.insert(0, SCRIPTS_GIT)
from write_version_file import (  # noqa: E402  # pyright: ignore[reportMissingImports]
    write_version_file,
)

write_version_file()

setup()
