from __future__ import annotations

import os
import traceback
from dataclasses import dataclass

from loguru import logger

import monitoring


@dataclass
class CallSite:
    func: str
    file: str
    line: int | None

    def __init__(self, func: str, file: str, line: int | None = None):
        """Define a site that may call a deprecated function.

        Args:
            func: Name of the calling function.  May include traceback shorthands like <dictcomp>.
            file: Filename starting with the `monitoring` folder.  Example: monitoring/monitorlib/deprecation.py
            line: Line in file where call site is located, if this should be checked to match.
        """
        self.func = func
        self.file = file
        self.line = line

    @staticmethod
    def from_frame_summary(stack: list[traceback.FrameSummary]) -> CallSite:
        monitoring_path = os.path.dirname(monitoring.__file__)

        i = -1
        func_name = stack[i].name
        while stack[i].name.startswith("<"):
            i -= 1
            func_name = stack[i].name
            if i == 0:
                break

        if stack[i].filename.startswith(monitoring_path):
            filename = os.path.join(
                "monitoring", stack[-1].filename[len(monitoring_path) + 1 :]
            )
        else:
            filename = stack[-1].filename
        return CallSite(func=func_name, file=filename, line=stack[-1].lineno)


class DeprecatedUsageError(RuntimeError):
    pass


def assert_deprecated(legacy_callers: list[CallSite] | None = None) -> None:
    """Assert that the function calling this function is deprecated.

    If the calling function is not explicitly listed in legacy_callers, then a DeprecatedUsageError will be thrown.
    Generally, the deprecated function should not be used in new development.  However, if it must be used in new
    development, or if the calling function location has been refactored, the legacy_callers of the deprecated function
    can be updated to include the call site to be allowed.

    If legacy_callers is not specified, a warning will be logged for all usage of the deprecated function

    Args:
        legacy_callers: List of CallSites that may call the deprecated function.  If omitted, a warning will be logged
            for all usages of the deprecated function rather than raising an exception.

    Raises:
        * DeprecatedUsageError if the calling function is not an explicitly-identified legacy caller.
    """
    stack = traceback.extract_stack()

    deprecated_site = CallSite.from_frame_summary(stack[0:-1])
    site = CallSite.from_frame_summary(stack[0:-2])
    msg = f"`{site.func}` in {site.file} (line {site.line}) called deprecated function `{deprecated_site.func}` in {deprecated_site.file} (line {deprecated_site.line}).  New use of deprecated functionality is generally not allowed."

    if legacy_callers is not None:
        base_dir = os.path.abspath(
            os.path.join(os.path.dirname(monitoring.__file__), "..")
        )
        for legacy_caller in legacy_callers:
            # Make sure the assert_deprecated assertion is valid
            if not os.path.exists(os.path.join(base_dir, legacy_caller.file)):
                raise ValueError(
                    f"assert_deprecated specified legacy_caller file {legacy_caller.file}, but that file does not exist."
                )

            # See if the calling site is a legacy caller
            if (
                site.file == legacy_caller.file
                and site.func == legacy_caller.func
                and (legacy_caller.line is None or site.line == legacy_caller.line)
            ):
                # Calling site is specified as a legacy caller so do nothing
                return

        # Calling site is not specified as a legacy caller
        msg += "  If this usage is important or is merely a refactoring, the legacy_callers of the deprecated function may be updated."
        raise DeprecatedUsageError(msg)
    else:
        logger.warning(msg)
