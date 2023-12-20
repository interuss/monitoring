import traceback


def stacktrace_string(e: Exception) -> str:
    """Return a multi-line string containing a stacktrace for the specified exception."""
    return "".join(traceback.format_exception(e))
