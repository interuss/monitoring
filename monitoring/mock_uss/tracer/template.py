import arrow

from monitoring.monitorlib import formatting


def _print_time_range(t0: str, t1: str) -> str:
    if not t0 and not t1:
        return ""
    now = arrow.utcnow()
    try:
        t0dt = arrow.get(t0) - now
        t1dt = arrow.get(t1) - now
        return " {} to {}".format(
            formatting.format_timedelta(t0dt), formatting.format_timedelta(t1dt)
        )
    except ValueError:
        return ""
