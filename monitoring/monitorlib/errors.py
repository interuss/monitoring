import traceback


def stacktrace_string(e: Exception) -> str:
    """Return a multi-line string containing a stacktrace for the specified exception."""
    return "".join(traceback.format_exception(e))


def current_stack_string(exclude_levels: int = 1) -> str:
    """Return a multi-line string containing a trace of the current execution state."""
    stack = traceback.extract_stack()
    if exclude_levels > 0:
        stack = stack[0:-exclude_levels]
    return "".join(traceback.format_list(stack))
