import os
from dataclasses import dataclass
from datetime import timedelta

from monitoring.monitorlib.fetch import QueryType
from monitoring.monitorlib.inspection import import_submodules
from monitoring.monitorlib.versioning import get_code_version
from monitoring.uss_qualifier import action_generators, scenarios, suites
from monitoring.uss_qualifier.configurations.configuration import (
    TimingReportConfiguration,
)
from monitoring.uss_qualifier.reports import jinja_env
from monitoring.uss_qualifier.reports.report import TestRunReport, TestSuiteActionReport
from monitoring.uss_qualifier.reports.tested_requirements.summaries import (
    compute_test_run_information,
)


class _GenerationError(RuntimeError):
    def __init__(self, msg: str):
        super().__init__(msg)


def generate_timing_report(
    report: TestRunReport, config: TimingReportConfiguration, output_path: str
) -> None:
    import_submodules(scenarios)
    import_submodules(suites)
    import_submodules(action_generators)

    test_run = compute_test_run_information(report)

    os.makedirs(output_path, exist_ok=True)
    index_file = os.path.join(output_path, "index.html")

    try:
        if report.report.start_time is None:
            raise _GenerationError("start_time is missing")
        if report.report.end_time is None:
            raise _GenerationError("end_time is missing")
        duration = report.report.end_time.datetime - report.report.start_time.datetime
        scenario_summaries, query_summaries = _summarize(report.report)
        scenario_breakdown = _make_scenario_breakdown(
            report, scenario_summaries, config
        )
        query_breakdown = _make_query_breakdown(query_summaries, config)
        servers = _list_servers(query_summaries)
    except _GenerationError as e:
        template = jinja_env.get_template("timing/cannot_generate.html")
        with open(index_file, "w") as f:
            f.write(template.render(non_generation_reason=str(e)))
        return

    template = jinja_env.get_template("timing/report.html")

    with open(index_file, "w") as f:
        f.write(
            template.render(
                report=report,
                test_run=test_run,
                duration=duration,
                codebase_version=get_code_version(),
                scenario_breakdown=scenario_breakdown,
                servers=servers,
                query_breakdown=query_breakdown,
                round=round,
                len=len,
                sum=_sum,
                format_time=_format_time,
            )
        )


def _format_time(dt: timedelta) -> str:
    hours = int(dt.seconds / 3600)
    minutes = int((dt.seconds % 3600) / 60)
    seconds = dt.total_seconds() % 60
    if dt > timedelta(hours=24):
        return f"{dt.days}d{hours}h{minutes}m"
    elif dt > timedelta(hours=1):
        return f"{hours}h{minutes}m{seconds:.0f}s"
    elif dt > timedelta(minutes=1):
        return f"{minutes}m{seconds:.0f}s"
    elif dt > timedelta(seconds=10):
        return f"{seconds:.1f}s"
    elif dt > timedelta(seconds=1):
        return f"{seconds:.2f}s"
    else:
        return f"{seconds:.3f}s"


def _sum(items):
    """This sum function works with a list of timedeltas (or any type defining self-addition), unlike the built-in sum."""
    result = None
    for v in items:
        if result is None:
            result = v
        else:
            result = result + v
    return result


def _add_dicts(d1: dict, d2: dict, result: dict) -> None:
    """Creates a merged dict with unique elements of d1 and d2, and the sum of values for keys shared by d1 and d2."""
    for k, v in d1.items():
        if k in d2:
            result[k] = v + d2[k]
        else:
            result[k] = v
    for k, v in d2.items():
        if k not in d1:
            result[k] = v


@dataclass
class _ScenarioSummary:
    instances: int
    total_time: timedelta
    query_time: timedelta
    delay_time: timedelta

    def __add__(self, other):
        if isinstance(other, _ScenarioSummary):
            return _ScenarioSummary(
                instances=self.instances + other.instances,
                total_time=self.total_time + other.total_time,
                query_time=self.query_time + other.query_time,
                delay_time=self.delay_time + other.delay_time,
            )
        else:
            raise TypeError(f"Cannot add _ScenarioSummary to {type(other)}")


class _ScenarioSummaryCollection(dict[str, _ScenarioSummary]):
    def __add__(self, other):
        if isinstance(other, _ScenarioSummaryCollection):
            result = _ScenarioSummaryCollection()
            _add_dicts(self, other, result)
            return result
        else:
            raise TypeError(f"Cannot add _ScenarioSummaryCollection to {type(other)}")


@dataclass
class _QuerySummary:
    times_per_server: dict[str, list[timedelta]]

    def __add__(self, other):
        if isinstance(other, _QuerySummary):
            times_per_server = {}
            _add_dicts(self.times_per_server, other.times_per_server, times_per_server)
            return _QuerySummary(
                times_per_server=times_per_server,
            )
        else:
            raise TypeError(f"Cannot add _QuerySummary to {type(other)}")


class _QuerySummaryCollection(dict[QueryType, _QuerySummary]):
    def __add__(self, other):
        if isinstance(other, _QuerySummaryCollection):
            result = _QuerySummaryCollection()
            _add_dicts(self, other, result)
            return result
        else:
            raise TypeError(f"Cannot add _QuerySummaryCollection to {type(other)}")


def _summarize(
    report: TestSuiteActionReport,
) -> tuple[_ScenarioSummaryCollection, _QuerySummaryCollection]:
    if "test_scenario" in report and report.test_scenario:
        scenario = report.test_scenario
        if "start_time" not in scenario or not scenario.start_time:
            raise _GenerationError(
                f"test scenario {scenario.scenario_type} is missing start_time"
            )
        if "end_time" not in scenario or not scenario.end_time:
            raise _GenerationError(
                f"test scenario {scenario.scenario_type} started at {scenario.start_time} is missing end_time"
            )
        query_time = timedelta(seconds=0)
        query_summaries = _QuerySummaryCollection()
        if "cases" in scenario and scenario.cases:
            for case in scenario.cases:
                if "steps" in case and case.steps:
                    for step in case.steps:
                        if "queries" in step and step.queries:
                            for query in step.queries:
                                dt = (
                                    query.response.reported.datetime
                                    - query.request.timestamp
                                )
                                if dt == 0:
                                    dt = timedelta(seconds=0)
                                query_time += dt
                                query_type = query.query_type or QueryType.Unknown
                                if query_type not in query_summaries:
                                    query_summaries[query_type] = _QuerySummary(
                                        times_per_server={}
                                    )
                                server = query.request.url_hostname
                                if (
                                    server
                                    not in query_summaries[query_type].times_per_server
                                ):
                                    query_summaries[query_type].times_per_server[
                                        server
                                    ] = []
                                query_summaries[query_type].times_per_server[
                                    server
                                ].append(dt)
        delay_time = timedelta(seconds=0)
        # TODO: populate delay_time
        scenario_summaries = _ScenarioSummaryCollection(
            {
                scenario.scenario_type: _ScenarioSummary(
                    instances=1,
                    total_time=scenario.end_time.datetime
                    - scenario.start_time.datetime,
                    query_time=query_time,
                    delay_time=delay_time,
                )
            }
        )
        return scenario_summaries, query_summaries

    elif "test_suite" in report and report.test_suite:
        actions = report.test_suite.actions
    elif "action_generator" in report and report.action_generator:
        actions = report.action_generator.actions
    elif "skipped_action" in report and report.skipped_action:
        return _ScenarioSummaryCollection(), _QuerySummaryCollection()
    else:
        raise _GenerationError(
            f"test action started at {report.start_time} does not have action content"
        )

    summaries = _ScenarioSummaryCollection()
    queries = _QuerySummaryCollection()
    for action in actions:
        ds, dq = _summarize(action)
        summaries = summaries + ds
        queries = queries + dq
    return summaries, queries


@dataclass
class _ScenarioBreakdownRow:
    scenario: str
    total_time: timedelta
    average_time: timedelta
    query_fraction: float
    delay_fraction: float


def _truncate(items, value_of, fraction):
    result = []
    items_list = list(items)
    if not items_list:
        return result

    total_value = value_of(items_list[0])
    for item in items_list[1:]:
        total_value += value_of(item)
    threshold_value = fraction * total_value

    result.append(items_list[0])
    running_value = value_of(items_list[0])
    if running_value < threshold_value:
        for item in items_list[1:]:
            running_value = running_value + value_of(item)
            result.append(item)
            if running_value >= threshold_value:
                break
    return result


def _make_scenario_breakdown(
    report: TestRunReport,
    summaries: _ScenarioSummaryCollection,
    config: TimingReportConfiguration,
) -> list[_ScenarioBreakdownRow]:
    rows = []
    for scenario_type, summary in summaries.items():
        rows.append(
            _ScenarioBreakdownRow(
                scenario=scenario_type,
                total_time=summary.total_time,
                average_time=summary.total_time / summary.instances,
                query_fraction=summary.query_time.total_seconds()
                / summary.total_time.total_seconds(),
                delay_fraction=summary.delay_time.total_seconds()
                / summary.total_time.total_seconds(),
            )
        )
    if report.report.end_time and report.report.start_time:
        scenario_time = _sum(
            summary.total_time for summary in summaries.values()
        ) or timedelta(seconds=0)
        overhead = (
            report.report.end_time.datetime - report.report.start_time.datetime
        ) - scenario_time
        rows.append(
            _ScenarioBreakdownRow(
                scenario="Non-scenario overhead",
                total_time=overhead,
                average_time=overhead,
                query_fraction=0,
                delay_fraction=0,
            )
        )
    rows.sort(key=lambda row: row.total_time, reverse=True)
    rows = _truncate(
        rows, lambda row: row.total_time, config.percentage_of_time_to_break_down / 100
    )
    return rows


@dataclass
class _QueryBreakdownRow:
    query_type: QueryType
    times_per_server: dict[str, list[timedelta]]

    @property
    def total_time(self) -> timedelta:
        total = timedelta(seconds=0)
        for dts in self.times_per_server.values():
            server_dts = _sum(dts) or timedelta(seconds=0)
            total += server_dts
        return total

    @property
    def average_time(self) -> timedelta:
        total = timedelta(seconds=0)
        n = 0
        for dts in self.times_per_server.values():
            server_dts = _sum(dts) or timedelta(seconds=0)
            total += server_dts
            n += len(dts)
        return total / n


def _make_query_breakdown(
    summaries: _QuerySummaryCollection, config: TimingReportConfiguration
) -> list[_QueryBreakdownRow]:
    rows = []
    for query_type, summary in summaries.items():
        rows.append(
            _QueryBreakdownRow(
                query_type=query_type, times_per_server=summary.times_per_server
            )
        )
    rows.sort(key=lambda row: row.total_time, reverse=True)
    rows = _truncate(
        rows, lambda row: row.total_time, config.percentage_of_time_to_break_down / 100
    )
    return rows


def _list_servers(summaries: _QuerySummaryCollection) -> list[str]:
    server_set = set()
    for summary in summaries.values():
        for server in summary.times_per_server.keys():
            server_set.add(server)
    servers = list(server_set)
    servers.sort()
    return servers
