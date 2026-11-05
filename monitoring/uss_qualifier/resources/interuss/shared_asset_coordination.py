from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from math import isfinite
from threading import Lock
from time import monotonic
from typing import TYPE_CHECKING

from implicitdict import ImplicitDict

from monitoring.uss_qualifier.resources.resource import Resource

if TYPE_CHECKING:
    from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario


class SharedAssetType(StrEnum):
    DSSAvailability = "astm.f3548.v21.dss.uss_availability"
    """Exclusive control of USS availability states in the DSS pool."""

    MockUSSNotifications = "interuss.monitoring.mock_uss.notifications"
    """Exclusive use of mock_uss notifications and observed interactions."""


class SharedAssetIdentifier(str):
    """Identifier of a particular shared asset."""

    type: SharedAssetType
    """Type of shared asset."""

    instance: str | None = None
    """Identifier of specific instance of the shared asset type."""

    def __new__(
        cls,
        value: str | None = None,
        asset_type: SharedAssetType | None = None,
        instance: str | None = None,
    ):
        """Create a new SharedAssetIdentifier.

        Args:
            value: Full SharedAssetIdentifier representation: <type>[:<instance>]
        """
        if value:
            if asset_type or instance:
                raise ValueError(
                    "SharedAssetIdentifier may not be constructed with both a value and components"
                )
            parts = value.split(":")
            if len(parts) > 2:
                raise ValueError(
                    "Invalid SharedAssetIdentifier format; must be <type>[:<instance>]"
                )
            elif len(parts) == 2:
                asset_type = SharedAssetType(parts[0])
                instance = parts[1]
            else:
                asset_type = SharedAssetType(value)
        if asset_type is None:
            raise ValueError(
                "asset_type must be specified for SharedAssetIdentifier when value is not specified"
            )
        s = str(asset_type)
        if instance is not None:
            s += f":{instance}"
        str_value = str.__new__(cls, s)
        str_value.type = asset_type
        str_value.instance = instance
        return str_value


class SharedAssetAcquisitionError(Exception):
    """Ownership of the desired asset could not be acquired."""

    def __init__(self, msg):
        super().__init__(msg)


class SharedAssetLease(ABC):
    @abstractmethod
    def release(self) -> None:
        """Release asset explicitly (otherwise, the asset is released automatically at the end of
        scenario execution).

        The corresponding automatic release on the scenario's ExitStack becomes a no-op.
        """
        raise NotImplementedError()


class SharedAssetCoordinatorResource(Resource, ABC):
    """Resource that coordinates exclusive access to one or more shared assets, each potentially
    used by multiple test scenarios or other clients.

    Implementations may coordinate locally, through a remote service, or by some other means.
    Ownership is non-reentrant.  Acquisition automatically registers release with the scenario's
    ExitStack when that stack exits.

    Concrete coordinators should also inherit Resource[TheirSpecification] to declare their
    specification independently of this interface.
    """

    @abstractmethod
    def acquire(
        self, asset_id: SharedAssetIdentifier, scenario: GenericTestScenario
    ) -> SharedAssetLease:
        """Acquire ownership of the asset and register its automatic release on the scenario's ExitStack.

        To avoid deadlocks, acquire multiple assets in a consistent order across callers.

        Raises: SharedAssetAcquisitionError
        """
        raise NotImplementedError()


class TestRunSharedAssetCoordinatorSpecification(ImplicitDict):
    retry_interval_seconds: float
    """Delay between acquisition attempts; must be positive and finite."""

    max_wait_time_seconds: float
    """Maximum acquisition wait; zero permits only an immediate attempt."""


@dataclass
class _TestRunSharedAssetLease(SharedAssetLease):
    owner: GenericTestScenario
    asset_id: SharedAssetIdentifier
    release_action: Callable[[_TestRunSharedAssetLease], None]

    def release(self) -> None:
        self.release_action(self)


class TestRunSharedAssetCoordinatorResource(
    SharedAssetCoordinatorResource,
    Resource[TestRunSharedAssetCoordinatorSpecification],
):
    """Coordinate threads sharing this instance within one test run/process.

    Provide a single, common instance as a dependency of all participating scenarios.
    Separate coordinator instances or processes do not coordinate with each other.
    Each asset identifier has an independent lock, allowing unrelated shared assets to be used
    concurrently.
    """

    _retry_interval_seconds: float
    _max_wait_time_seconds: float
    _state_lock: Lock
    _leases: dict[SharedAssetIdentifier, _TestRunSharedAssetLease]

    def __init__(
        self,
        specification: TestRunSharedAssetCoordinatorSpecification,
        resource_origin: str,
    ):
        super().__init__(specification, resource_origin)
        if (
            not isfinite(specification.retry_interval_seconds)
            or specification.retry_interval_seconds <= 0
        ):
            raise ValueError("retry_interval_seconds must be positive and finite")
        if (
            not isfinite(specification.max_wait_time_seconds)
            or specification.max_wait_time_seconds < 0
        ):
            raise ValueError("max_wait_time_seconds must be nonnegative and finite")
        self._retry_interval_seconds = specification.retry_interval_seconds
        self._max_wait_time_seconds = specification.max_wait_time_seconds
        self._state_lock = Lock()
        self._leases = {}

    def acquire(
        self,
        asset_id: SharedAssetIdentifier,
        scenario: GenericTestScenario,
    ) -> SharedAssetLease:
        if not scenario.scenario_stack:
            raise TypeError(
                "Acquisition requires an ExitStack established for scenario"
            )

        lease = _TestRunSharedAssetLease(
            owner=scenario,
            asset_id=asset_id,
            release_action=self._release_if_current,
        )
        deadline = monotonic() + self._max_wait_time_seconds
        current_owner = self._try_acquire(asset_id, lease)
        while current_owner:
            remaining = deadline - monotonic()
            if remaining <= 0:
                raise SharedAssetAcquisitionError(
                    f"Unable to acquire shared resource {asset_id} from {current_owner.current_state_name()} after maximum wait time of {self._max_wait_time_seconds:g} seconds (requested by {scenario.current_state_name()})"
                )

            scenario.sleep(
                min(self._retry_interval_seconds, remaining),
                f"Required shared resource {asset_id} is being used by {current_owner.current_state_name()}; waiting for its release (requested by {scenario.current_state_name()})",
            )
            if monotonic() < deadline:
                current_owner = self._try_acquire(asset_id, lease)

        try:
            scenario.scenario_stack.callback(lease.release)
        except BaseException:
            lease.release()
            raise

        return lease

    def _try_acquire(
        self, asset_id: SharedAssetIdentifier, lease: _TestRunSharedAssetLease
    ) -> GenericTestScenario | None:
        """Attempt to acquire ownership of the specified asset_id returning None if successful or the current owner if unsuccessful."""
        with self._state_lock:
            if asset_id in self._leases:
                return self._leases[asset_id].owner
            self._leases[asset_id] = lease
            return None

    def _release_if_current(self, lease: _TestRunSharedAssetLease) -> None:
        with self._state_lock:
            if self._leases.get(lease.asset_id) is lease:
                del self._leases[lease.asset_id]
