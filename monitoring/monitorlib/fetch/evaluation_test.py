from datetime import datetime

from implicitdict import StringBasedDateTime

from monitoring.monitorlib.fetch import (
    Query,
    RequestDescription,
    ResponseDescription,
    evaluation,
)


def _fq(ts: int, elapsed: float):
    """returns a fake query with the specified epoch timestamp as 'initiated_at'"""
    return Query(
        request=RequestDescription(
            method=None,
            url=None,
            initiated_at=StringBasedDateTime(datetime.fromtimestamp(ts)),
        ),
        response=ResponseDescription(elapsed_s=elapsed, reported=None),
    )


def test_get_init_subsequent_queries_durations():
    dummy_queries = [_fq(10, 2), _fq(12, 1), _fq(13, 0.9), _fq(14, 0.8)]
    query_dict = {"some-url": dummy_queries}
    (init_d, subseq_d) = evaluation.get_init_subsequent_queries_durations(5, query_dict)

    assert init_d == [2]
    assert subseq_d == [1, 0.9, 0.8]

    query_dict = {"some-url": dummy_queries, "another-url": dummy_queries}

    (init_d, subseq_d) = evaluation.get_init_subsequent_queries_durations(5, query_dict)
    assert init_d == [2, 2]
    assert subseq_d == [1, 0.9, 0.8, 1, 0.9, 0.8]
