import datetime
import enum

import arrow
from termcolor import colored


class Change(enum.Enum):
    NOCHANGE = 0
    ADDED = 1
    CHANGED = 2
    REMOVED = 3

    @classmethod
    def color_of(cls, change) -> str:
        if change == Change.NOCHANGE:
            return "grey"
        elif change == Change.ADDED:
            return "green"
        elif change == Change.CHANGED:
            return "yellow"
        elif change == Change.REMOVED:
            return "red"
        raise ValueError("Invalid Change type")


def _update_overall(overall: Change, field: Change):
    if overall == Change.CHANGED:
        return Change.CHANGED
    if overall == Change.NOCHANGE:
        return field
    if overall == Change.ADDED:
        if field == Change.ADDED or field == Change.NOCHANGE:
            return Change.ADDED
        else:
            return Change.CHANGED
    if overall == Change.REMOVED:
        if field == Change.REMOVED or field == Change.NOCHANGE:
            return Change.REMOVED
        else:
            return Change.CHANGED
    raise ValueError("Unexpected change configuration")


def dict_changes(a: dict, b: dict) -> tuple[dict, dict, Change]:
    values = {}
    changes = {}
    overall = Change.NOCHANGE

    for k, v1 in b.items():
        v0 = a.get(k, {})
        if isinstance(v1, dict):
            field_values, field_changes, change = dict_changes(v0, v1)
            if len(field_values) >= 2:
                values[k] = field_values
                changes[k] = field_changes
                changes[k]["__self__"] = change
            elif len(field_values) == 1:
                field_k = next(iter(field_values.keys()))
                k = k + "." + field_k
                values[k] = field_values[field_k]
                changes[k] = field_changes[field_k]
        else:
            if v0 == v1:
                change = Change.NOCHANGE
            else:
                values[k] = v1
                if k not in a:
                    change = Change.ADDED
                else:
                    change = Change.CHANGED
                changes[k] = change
        overall = _update_overall(overall, change)

    for k, v0 in a.items():
        if k not in b:
            if isinstance(v0, dict):
                values[k], changes[k], change = dict_changes(v0, {})
            else:
                values[k] = v0
                change = Change.REMOVED
                changes[k] = change
            overall = _update_overall(overall, change)

    return values, changes, overall


def diff_lines(values: dict, changes: dict) -> list[str]:
    lines = []
    for k, v in values.items():
        c = changes[k]
        if isinstance(v, dict):
            if "__self__" in c:
                lines.append(colored(k, Change.color_of(c["__self__"])) + ":")
            else:
                lines.append(k + ":")
            lines.extend("  " + line for line in diff_lines(v, c))
        else:
            if c == Change.ADDED:
                lines.append(colored(f"{k}: {v}", "green"))
            elif c == Change.CHANGED:
                lines.append(k + ": " + colored(str(v), "yellow"))
            elif c == Change.REMOVED:
                lines.append(colored(f"{k}: {v}", "red"))
    return lines


def format_timedelta(td: datetime.timedelta) -> str:
    """Produce a human-readable string describing a timedelta.
    Args:
      td: datetime.timedelta to format.
    Return:
      Formatted timedelta that looks like HH:MM:SS or XXXdHH:MM:SS where XXX is
      number of days, with or without a leading negative sign.
    """
    seconds = int(td.total_seconds())
    if seconds < 0:
        seconds = -seconds
        sign = "-"
    else:
        sign = ""
    periods = (("%d", 60 * 60 * 24), ("%02d", 60 * 60), ("%02d", 60), ("%02d", 1))
    has_days = seconds >= periods[0][1]

    segments = []
    for format_string, period_seconds in periods:
        period_value, seconds = divmod(seconds, period_seconds)
        segments.append(format_string % period_value)

    if has_days:
        return sign + "{:s}d{:s}:{:s}:{:s}".format(*segments)
    else:
        return sign + "{:s}:{:s}:{:s}".format(*segments[1:])


def make_datetime(t) -> datetime.datetime:
    if isinstance(t, str):
        return arrow.get(t).datetime
    elif isinstance(t, datetime.datetime):
        return arrow.get(t).datetime
    else:
        raise ValueError(f"Could not convert {str(type(t))} to datetime")


def limit_resolution(value: float, resolution: float) -> float:
    """Change resolution of a value"""
    return round(value / resolution) * resolution


def format_duration_shorthand(duration: float | datetime.timedelta) -> str:
    """Produce a smart shorthand string describing a duration.

    Has a maximum of two significant units, and tenths of a second only for values <10s.
    Examples:
      - 3.8s (<10s)
      - 48s (>=10s and <60s)
      - 1m3s (60s <= d < 3600s)
      - 12m42s
      - 1h5m (3600s <= d < 86400s)
      - 4h (if minutes == 0)
      - 6m (if seconds == 0)
      - 1d6h
      - 3w4d
    """
    if isinstance(duration, datetime.timedelta):
        seconds = duration.total_seconds()
    else:
        seconds = float(duration)

    if seconds < 0:
        return f"-{format_duration_shorthand(-seconds)}"

    if seconds < 10.0:
        rounded = round(seconds, 1)
        if rounded >= 10.0:
            return "10s"
        return f"{rounded:.1f}s"

    if seconds < 60.0:
        rounded = round(seconds)
        if rounded >= 60:
            return "1m"
        return f"{rounded}s"

    if seconds < 3600.0:
        total_sec = round(seconds)
        mins = total_sec // 60
        secs = total_sec % 60
        if mins >= 60:
            return "1h"
        if secs == 0:
            return f"{mins}m"
        return f"{mins}m{secs}s"

    if seconds < 86400.0:
        total_min = round(seconds / 60.0)
        hours = total_min // 60
        mins = total_min % 60
        if hours >= 24:
            return "1d"
        if mins == 0:
            return f"{hours}h"
        return f"{hours}h{mins}m"

    if seconds < 604800.0:
        total_hours = round(seconds / 3600.0)
        days = total_hours // 24
        hours = total_hours % 24
        if days >= 7:
            return "1w"
        if hours == 0:
            return f"{days}d"
        return f"{days}d{hours}h"

    total_days = round(seconds / 86400.0)
    weeks = total_days // 7
    days = total_days % 7
    if days == 0:
        return f"{weeks}w"
    return f"{weeks}w{days}d"
