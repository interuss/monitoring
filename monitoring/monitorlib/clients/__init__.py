from abc import ABC
from typing import List, Optional

from monitoring.monitorlib.fetch import Query
from monitoring.monitorlib.mock_uss_interface.interaction_log import Issue


class QueryHook(ABC):
    def on_query(
        self, query: Query, function, issues: Optional[List[Issue]] = None
    ) -> None:
        """Called whenever a client performs a query and this hook is included in query_hooks.

        Args:
            query: Query that was performed.
            function: The client function that performed the query.
        """
        raise NotImplementedError("QueryHook subclass did not implement on_query")


query_hooks: List[QueryHook] = []


def call_query_hooks(
    query: Query, function, issues: Optional[List[Issue]] = None
) -> None:
    for hook in query_hooks:
        hook.on_query(query=query, function=function, issues=issues)
