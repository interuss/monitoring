import statistics
from operator import attrgetter
from typing import List, Tuple, Dict

from . import Query


def classify_query_by_url(queries: List[Query]) -> Dict[str, List[Query]]:
    queries_by_url: Dict[str, List[Query]] = dict()
    for query in queries:
        if query.request.url not in queries_by_url:
            queries_by_url[query.request.url] = list()
        queries_by_url[query.request.url].append(query)
    return queries_by_url


def get_init_subsequent_queries_durations(
    min_session_length_sec: int, queries_by_url: Dict[str, List[Query]]
) -> Tuple[List[float], List[float]]:
    """
    Get the initial and subsequent durations of the provided queries.
    Initial and subsequent queries are identified through 1. their URL and 2. the time elapsed between the queries.
    :param min_session_length_sec: cut-off duration from last query to discriminate between initial and subsequent queries.
    :param queries_by_url:
    :return: list of durations of respectively initial and subsequent queries
    """

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
                init_durations.append(query.response.elapsed_s)
            else:
                subsequent_durations.append(query.response.elapsed_s)

    return init_durations, subsequent_durations


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
