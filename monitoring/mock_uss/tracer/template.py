import datetime
from monitoring.monitorlib import formatting


def _print_time_range(t0: str, t1: str) -> str:
    if not t0 and not t1:
        return ""
    now = datetime.datetime.utcnow()
    if t0.endswith("Z"):
        t0 = t0[0:-1]
    if t1.endswith("Z"):
        t1 = t1[0:-1]
    try:
        t0dt = datetime.datetime.fromisoformat(t0) - now
        t1dt = datetime.datetime.fromisoformat(t1) - now
        return " {} to {}".format(
            formatting.format_timedelta(t0dt), formatting.format_timedelta(t1dt)
        )
    except ValueError as e:
        return ""
