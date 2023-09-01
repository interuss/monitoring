from typing import Optional, List
import yaml
from yaml.representer import Representer
from implicitdict import ImplicitDict

from monitoring.monitorlib.fetch import Query


class Issue(ImplicitDict):
    requirement: Optional[str]  # Eg. data_validation, messagesigning
    description: str  # Eg. size of volumes <= 30
    details: Optional[str]  # Eg. Received volumes size = 100. Spec requires size = 30


yaml.add_representer(Issue, Representer.represent_dict)


class Interaction(ImplicitDict):
    query: Query
    reported_issues: Optional[List[Issue]]


yaml.add_representer(Interaction, Representer.represent_dict)


class ListLogsResponse(ImplicitDict):
    interactions: List[Interaction]

