from enum import Enum
from typing import List

from implicitdict import ImplicitDict
import yaml
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


yaml.add_representer(Interaction, Representer.represent_dict)


class ListLogsResponse(ImplicitDict):
    interactions: List[Interaction]
