import statistics
from operator import attrgetter
from typing import List, Tuple, Dict

from monitoring.monitorlib import fetch


def compute_percentiles(values: List[float], percentiles: List[int]) -> List[float]:
    """
    Compute percentiles of durations.
    :param values: list of durations for which to compute the percentiles
    :param percentiles: percentiles to return (1 to 98 included)
    :return: a list with the corresponding percentiles
    """
    if len(values) == 0:
        return [0 for p in percentiles]
    elif len(values) == 1:
        return [values[0] for p in percentiles]
    else:
        calc_percentiles = statistics.quantiles(data=values, n=100)
        return [calc_percentiles[p - 1] for p in percentiles]


def compute_query_durations_percentiles(
    min_session_length_sec: int, all_queries: List[fetch.Query]
) -> Tuple[float, float, float, float]:
    """
    Compute the 95th and 99th percentiles of the query durations provided for both initial and subsequent queries.
    Initial and subsequent queries are identified through 1. their URL and 2. the time elapsed between the queries.
    :param min_session_length_sec: cut-off duration from last query to discriminate between initial and subsequent queries.
    :param all_queries:
    :return: tuple of percentiles: (init_95th, init_99th, subsequent_95th, subsequent_99th)
    """

    # classify queries by their URL
    queries_by_url: Dict[str, List[fetch.Query]] = dict()
    for query in all_queries:
        if query.request.url not in queries_by_url:
            queries_by_url[query.request.url] = list()
        queries_by_url[query.request.url] += query

    # split queries between init and subsequent
    init_durations: List[float] = list()  # list of initial queries duration
    subsequent_durations: List[float] = list()  # list of subsequent queries duration

    for queries in queries_by_url.values():
        queries.sort(key=attrgetter("request.initiated_at"))  # sort queries by time

        for idx, query in enumerate(queries):
            if query.request.initiated_at is None:
                # ignore query if it does not have time
                continue

            query_time = query.request.initiated_at.datetime
            prev_query_time = queries[idx - 1].request.initiated_at.datetime
            if (
                idx == 0
                or (query_time - prev_query_time).total_seconds()
                > min_session_length_sec
            ):
                init_durations += query.response.elapsed_s
            else:
                subsequent_durations += query.response.elapsed_s

    # compute percentiles
    [init_95th_percentile, init_99th_percentile] = compute_percentiles(
        init_durations, [95, 99]
    )
    [subsequent_95th_percentile, subsequent_99th_percentile] = compute_percentiles(
        subsequent_durations, [95, 99]
    )
    return (
        init_95th_percentile,
        init_99th_percentile,
        subsequent_95th_percentile,
        subsequent_99th_percentile,
    )
