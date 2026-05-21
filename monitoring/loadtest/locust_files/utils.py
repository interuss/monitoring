import datetime

from monitoring.monitorlib import rid_v1


def format_time(time: datetime.datetime) -> str:
    return time.astimezone(datetime.UTC).strftime(rid_v1.DATE_FORMAT)
