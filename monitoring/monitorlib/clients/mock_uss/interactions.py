from datetime import datetime
from enum import Enum
from typing import List

import yaml
from implicitdict import ImplicitDict
from yaml.representer import Representer

from monitoring.monitorlib.fetch import Query


class QueryDirection(str, Enum):
    Incoming = "Incoming"
    """The query originated from a remote client and was handled by the system reporting the interaction."""

    Outgoing = "Outgoing"
    """The system reporting the interaction initiated the query to a remote server."""


class Interaction(ImplicitDict):
    query: Query
    direction: QueryDirection

    def interaction_time(self) -> datetime:
        """
        Returns the time the interaction occurred: this returns min(received_at, initiated_at)
        or whichever of the two is defined.

        Raises ValueError if neither received_at nor initiated_at is defined.
        """
        if "received_at" in self.query.request and "initiated_at" in self.query.request:
            return min(
                self.query.request.received_at.datetime,
                self.query.request.initiated_at.datetime,
            )
        elif "received_at" in self.query.request:
            return self.query.request.received_at.datetime
        elif "initiated_at" in self.query.request:
            return self.query.request.initiated_at.datetime
        else:
            raise ValueError(
                f"There is no received_at or initiated_at field in the interaction {self}"
            )


yaml.add_representer(Interaction, Representer.represent_dict)


class ListLogsResponse(ImplicitDict):
    interactions: List[Interaction]
