from abc import ABC
from typing import List

from monitoring.monitorlib.fetch import Query


class QueryHook(ABC):
    def on_query(self, query: Query) -> None:
        """Called whenever a client performs a query and this hook is included in query_hooks.

        Args:
            query: Query that was performed.
        """
        raise NotImplementedError("QueryHook subclass did not implement on_query")


query_hooks: List[QueryHook] = []


def call_query_hooks(query: Query) -> None:
    for hook in query_hooks:
        hook.on_query(query=query)
