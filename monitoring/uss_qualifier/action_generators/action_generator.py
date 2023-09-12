from __future__ import annotations
from abc import ABC, abstractmethod
import inspect
from typing import Generic, Dict, Optional, TypeVar

from implicitdict import ImplicitDict
from monitoring import uss_qualifier as uss_qualifier_module
from monitoring.monitorlib.inspection import (
    import_submodules,
    get_module_object_by_name,
)
from monitoring.uss_qualifier.action_generators.definitions import (
    ActionGeneratorSpecificationType,
    ActionGeneratorDefinition,
)
from monitoring.uss_qualifier.reports.report import TestSuiteActionReport
from monitoring.uss_qualifier.resources.definitions import ResourceID
from monitoring.uss_qualifier.resources.resource import ResourceType


class ActionGenerator(ABC, Generic[ActionGeneratorSpecificationType]):
    definition: ActionGeneratorDefinition

    @abstractmethod
    def __init__(
        self,
        specification: ActionGeneratorSpecificationType,
        resources: Dict[ResourceID, ResourceType],
    ):
        """Create an instance of the action generator.

        Concrete subclasses of ActionGenerator must implement their constructor according to this specification.

        :param specification: A serializable (subclass of implicitdict.ImplicitDict) specification for how to create the action generator.  This parameter may be omitted if not needed.
        :param resources: All of the resources available in the test suite in which the action generator is run.
        """
        raise NotImplementedError(
            "A concrete action generator type must implement __init__ method"
        )

    @abstractmethod
    def run_next_action(self) -> Optional[TestSuiteActionReport]:
        """Run the next action from the generator, or else return None if there are no more actions"""
        raise NotImplementedError(
            "A concrete action generator must implement `actions` method"
        )

    @staticmethod
    def make_from_definition(
        definition: ActionGeneratorDefinition, resources: Dict[ResourceID, ResourceType]
    ) -> ActionGeneratorType:
        from monitoring.uss_qualifier import (
            action_generators as action_generators_module,
        )

        import_submodules(action_generators_module)
        action_generator_type = get_module_object_by_name(
            parent_module=uss_qualifier_module,
            object_name=definition.generator_type,
        )
        if not issubclass(action_generator_type, ActionGenerator):
            raise NotImplementedError(
                "Action generator type {} is not a subclass of the ActionGenerator base class".format(
                    action_generator_type.__name__
                )
            )
        constructor_signature = inspect.signature(action_generator_type.__init__)
        specification_type = None
        constructor_args = {}
        for arg_name, arg in constructor_signature.parameters.items():
            if arg_name == "specification":
                specification_type = arg.annotation
                break
        if specification_type is not None:
            constructor_args["specification"] = ImplicitDict.parse(
                definition.specification, specification_type
            )
        constructor_args["resources"] = resources
        generator = action_generator_type(**constructor_args)
        generator.definition = definition
        return generator


ActionGeneratorType = TypeVar("ActionGeneratorType", bound=ActionGenerator)
