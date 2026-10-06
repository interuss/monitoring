import datetime
import glob
import json
import os
import re
from collections.abc import Iterator

import yaml
from implicitdict import ImplicitDict
from loguru import logger

from monitoring.mock_uss.tracer.log_types import TracerLogEntry
from monitoring.monitorlib import infrastructure


class Logger:
    def __init__(
        self,
        log_path: str,
        kml_session: infrastructure.KMLGenerationSession | None = None,
    ):
        self.log_path = log_path
        os.makedirs(self.log_path, exist_ok=True)
        self.kml_session = kml_session

    def log_same(self, t0: datetime.datetime, t1: datetime.datetime, code: str) -> None:
        with open(
            os.path.join(self.log_path, "000000_nochange_queries.yaml"), "a"
        ) as f:
            body = {"t0": t0.isoformat(), "t1": t1.isoformat(), "code": code}
            f.write(yaml.dump(body, explicit_start=True))

    def log_new(self, content: TracerLogEntry) -> str:
        n = len(os.listdir(self.log_path))
        basename = "{:06d}_{}_{}".format(
            n, datetime.datetime.now().strftime("%H%M%S_%f"), content.prefix_code()
        )
        logname = f"{basename}.yaml"
        fullname = os.path.join(self.log_path, logname)

        dump = json.loads(json.dumps(content))
        dump["object_type"] = type(content).__name__
        with open(fullname, "w") as f:
            f.write(yaml.dump(dump, indent=2))

        if self.kml_session:
            kml_server_filename = os.path.join(self.kml_session.kml_folder, logname)
            try:
                with open(fullname) as f:
                    resp = self.kml_session.post(
                        "/realtime_kml",
                        data={"path": self.kml_session.kml_folder},
                        files=[("files[]", f)],
                    )
                resp.raise_for_status()
                kml_path = os.path.join(self.log_path, "kml")
                os.makedirs(kml_path, exist_ok=True)
                with open(os.path.join(kml_path, f"{basename}.kml"), "w") as f:
                    f.write(resp.content.decode("utf-8"))
            except OSError as e:
                print(f"Error posting {kml_server_filename} to KML server: {e}")

        return logname


class DummyLogger(Logger):
    def __init__(self):
        pass

    def log_same(self, t0: datetime.datetime, t1: datetime.datetime, code: str) -> None:
        pass

    def log_new(self, content: TracerLogEntry) -> str:
        return "dummy"


def load_logs(
    log_folder: str,
    acceptable_types: set[type[TracerLogEntry]] | None = None,
    ignored_types: set[type[TracerLogEntry]] | None = None,
) -> Iterator[tuple[str, TracerLogEntry]]:
    """Iterate through parsed TracerLogEntry files in a folder.

    Args:
        log_folder: Path to folder containing tracer YAML log files.
        acceptable_types: If specified, only parse and yield log entries of these types,
            raising NotImplementedError if an unignored log entry type is not in this set.
        ignored_types: If specified, silently skip log entries of these types without
            reading or parsing the file.
    """
    if not os.path.isdir(log_folder):
        raise ValueError(f"Log folder '{log_folder}' is not a directory")

    log_files = glob.glob(os.path.join(log_folder, "*.yaml"))
    log_files.sort()
    for log_file in log_files:
        logger.debug(f"Processing {log_file}")

        if "nochange_queries" in log_file:
            continue  # This is a known case where we don't want to print a warning

        filename = os.path.split(log_file)[-1]
        m = re.match(r"^(\d{6})_(\d\d)(\d\d)(\d\d)_(\d{6})_([^.]+)\.yaml$", filename)
        if not m:
            logger.warning(f"File name {filename} does not match log entry format")
            continue

        prefix_code = m.group(6)
        log_entry_type = TracerLogEntry.entry_type_from_prefix(prefix_code)
        if not log_entry_type:
            logger.warning(
                f"Cannot determine log entry type from prefix_code `{prefix_code}` in {filename}"
            )
            continue

        if ignored_types is not None and log_entry_type in ignored_types:
            continue

        if acceptable_types is not None and log_entry_type not in acceptable_types:
            raise NotImplementedError(
                f"Unhandled TracerLogEntry type {log_entry_type.__name__} in {log_file}"
            )

        with open(log_file) as f:
            try:
                content = yaml.load(f, Loader=yaml.CLoader)
                log_entry = ImplicitDict.parse(content, log_entry_type)
            except (ValueError, TypeError, KeyError, yaml.YAMLError) as e:
                logger.warning(f"Skipping {filename} because of parse error: {e}")
                continue

        yield filename, log_entry
