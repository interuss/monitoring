import functools
import inspect

import pytest

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
