import functools
import inspect
import os
from dataclasses import dataclass

import pytest

from monitoring.prober import utils

_test_results = dict()


def add_test_result(item, result):
    global _test_results
    _test_results[item] = result


def depends_on(*args):
    """Test decorator that skips a test if a dependent test didn't pass.

    :param args: List of test functions that must pass before the decorated
                 function will be executed.
    """

    def decorator_default_scope(func):
        prerequisites = args
        test_module = inspect.getmodule(inspect.stack()[1][0])

        @functools.wraps(func)
        def wrapper_default_scope(*args, **kwargs):
            global _test_results
            module_results = {
                k.name: _test_results[k]
                for k in _test_results
                if test_module and k.fspath == test_module.__file__
            }
            for prerequisite in prerequisites:
                if prerequisite.__name__ not in module_results:
                    pytest.fail(
                        f"Prerequisite test {prerequisite.__name__} did not exist when evaluating the dependent test {func.__name__}"
                    )
                if not module_results[prerequisite.__name__].passed:
                    pytest.skip("Prerequisite task did not pass")
            return func(*args, **kwargs)

        return wrapper_default_scope

    return decorator_default_scope


class VersionString(str):
    pass


def for_api_versions(*args):
    """Test decorator that checks if API version being tested applies to the test.

    A test function decorated with this decorator must include an argument that
    matches a fixture which takes on a VersionString value.  If that VersionString
    value matches any of the values specified in this decorator, the test will
    proceed normally.  If it does not match any of the values specified in this
    decorator, the test will be skipped.

    :param args: List of API versions for which the decorated test should be run.
    """

    def decorator_default_scope(func):
        acceptable_versions = args

        @functools.wraps(func)
        def wrapper_default_scope(*args, **kwargs):
            api_version = None
            for arg in args:
                if isinstance(arg, VersionString):
                    api_version = arg
                    break
            for key, value in kwargs.items():
                if isinstance(value, VersionString):
                    api_version = value
                    break

            if api_version is None:
                raise ValueError(
                    "A test with the @for_api_versions decorator must include, in its arguments, a fixture populated with a VersionString value (for instance: scd_api)"
                )
            if api_version in acceptable_versions:
                return func(*args, **kwargs)
            else:
                pytest.skip(f"Not applicable for API version {api_version}")

        return wrapper_default_scope

    return decorator_default_scope


ResourceType = int
resource_type_code_descriptions: dict[ResourceType, str] = {}


# Next code: 406
def register_resource_type(code: int, description: str) -> ResourceType:
    """Register that the specified code refers to the described resource.

    Args:
      code: A integer that is globally-unique among all register_resource_type
            calls in all prober tests, referring to this specific resource type.
      description: Description of the resource created from this type.

    Returns:
      ResourceType that can be used to create an ID with <IDFactory>.make_id,
      especially with the `ids` test fixture (see conftest.py).
    """
    test_filename = inspect.stack()[1].filename
    this_folder = os.path.dirname(os.path.abspath(__file__))
    test = os.path.relpath(test_filename, this_folder)
    full_description = f"{test}: {description}"
    if code in resource_type_code_descriptions:
        raise ValueError(
            f'Resource type code {code} is already in use as "{resource_type_code_descriptions[code]}" so it cannot be used for "{full_description}"'
        )
    resource_type_code_descriptions[code] = full_description
    return code


@dataclass(frozen=True)
class DecodedTestID:
    owner_name: str
    resource_type: ResourceType
    instance_index: int


class IDFactory:
    """Creates UUIDv4 (as described in RFC4122) formatted IDs encoding the kind of ID and owner.

    Format: 000HXXXX-YYYY-4LYY-8YYY-YYYYYYYY0000

    Note that a UUID V4 needs to conform to the following regexp, which is why we
    set the first digit of the fourth group to 8.

    ^[0-9a-fA-F]{8}\\-[0-9a-fA-F]{4}\\-4[0-9a-fA-F]{3}\\-[8-b][0-9a-fA-F]{3}\\-[0-9a-fA-F]{12}$

    XXXX encodes the kind of ID according to id_codes.
    YYYYYYYYYYYYYYYYY encodes the owner/creator of the resource having the ID and
    consists of 11 complete characters and 2 bits of a twelfth character,
    encoded as 6-bit groups.  Decoding marks the incomplete character with '?'.
    HL encodes an instance index from 0 to 255 in hexadecimal.  Index 0 produces
    the original ID format; other indices separate repeated invocations of a test.
    """

    owner_id: str
    _instance_index: int

    def __init__(self, test_owner: str, instance_index: int = 0):
        self.validate_instance_index(instance_index)
        self.owner_id = utils.encode_owner(test_owner)
        self._instance_index = instance_index

    @staticmethod
    def validate_instance_index(instance_index: int) -> None:
        if type(instance_index) is not int or not 0 <= instance_index <= 255:
            raise ValueError("instance_index must be an integer from 0 to 255")

    @property
    def instance_index(self) -> int:
        return self._instance_index

    def make_id(self, resource_type: ResourceType):
        """Make a test ID with the specified resource type code"""
        return f"000{self.instance_index >> 4:x}{utils.encode_resource_type_code(resource_type)}-{self.owner_id[0:4]}-4{self.instance_index & 0xF:x}{self.owner_id[4:6]}-8{self.owner_id[6:9]}-{self.owner_id[9:17]}0000"

    @classmethod
    def decode(cls, id: str) -> tuple[str, ResourceType]:
        """Decode an ID, retaining the original two-item return value."""
        decoded = cls.decode_details(id)
        return decoded.owner_name, decoded.resource_type

    @classmethod
    def decode_details(cls, id: str) -> DecodedTestID:
        """Decode the owner, resource type, and instance index of a test ID."""
        hex_digits = id.replace("-", "").lower()
        if len(hex_digits) != 32:
            raise ValueError(f"ID {id} has the wrong number of characters for a UUID")
        if any(c not in "0123456789abcdef" for c in hex_digits):
            raise ValueError(f"ID {id} contains non-hexadecimal characters")
        if hex_digits[0:3] != "000" or hex_digits[-4:] != "0000":
            raise ValueError(
                f"ID {id} does not have the leading and trailing zeros indicating a test ID"
            )
        if hex_digits[12] != "4" or hex_digits[16] != "8":
            raise ValueError(f"ID {id} is not formatted like a v4 test ID")
        x = hex_digits[4:8]
        y = hex_digits[8:12] + hex_digits[14:16] + hex_digits[17:28]
        resource_type_code = ResourceType(int(x, 16))
        owner_name = utils.decode_owner(y)
        return DecodedTestID(
            owner_name=owner_name,
            resource_type=resource_type_code,
            instance_index=int(hex_digits[3] + hex_digits[13], 16),
        )


check_scd_write_subscription_id = register_resource_type(
    344, "Subscription created by build/dev/check_scd_write.sh"
)
check_scd_write_constraint_id = register_resource_type(
    345, "Constraint reference created by build/dev/check_scd_write.sh"
)
check_scd_write_operational_intent_id = register_resource_type(
    346, "Operational intent reference created by build/dev/check_scd_write.sh"
)

unknown_resource_id = register_resource_type(
    404, "<Unknown resource ID / Unknown purpose>"
)
