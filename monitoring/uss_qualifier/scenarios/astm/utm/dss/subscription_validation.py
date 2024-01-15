from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

import loguru
import s2sphere
from s2sphere import LatLngRect
from uas_standards.astm.f3548.v21.api import Subscription
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.monitorlib.geo import Polygon, Volume3D
from monitoring.monitorlib.geotemporal import Volume4D
from monitoring.monitorlib.mutate.scd import MutatedSubscription
from monitoring.prober.infrastructure import register_resource_type
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import DSSInstanceResource
from monitoring.uss_qualifier.resources.interuss.id_generator import IDGeneratorResource
from monitoring.uss_qualifier.resources.uss_area import (
    USSAreaResource,
    USSAreaSpecification,
)
from monitoring.uss_qualifier.scenarios.astm.utm.dss import test_step_fragments
from monitoring.uss_qualifier.scenarios.scenario import (
    TestScenario,
    PendingCheck,
)
from monitoring.uss_qualifier.suites.suite import ExecutionContext

_24H_MIN_TOLERANCE_S = 23 * 3600 + 59 * 60  # 23 hours and 59 minutes
_24H_MAX_TOLERANCE_S = 24 * 3600 + 1  # 24 hours sharp, plus a second


class SubscriptionValidation(TestScenario):
    """
    A scenario that verifies that the DSS properly validates and sets the proper limits on subscriptions.
    """

    SUB_TYPE = register_resource_type(378, "Subscription")

    # Base identifier for the subscriptions that will be created
    _sub_id: str

    _uss_area: USSAreaSpecification

    _uss_area_volume4d: Volume4D

    # Base parameters used for subscription creation variations
    _sub_generation_params: Dict[str, Any]

    def __init__(
        self,
        dss: DSSInstanceResource,
        id_generator: IDGeneratorResource,
        uss_area: USSAreaResource,
    ):
        """
        Args:
            dss: dss to test
            id_generator: will let us generate specific identifiers
            uss_area: An Area to use for the tests. It should be an area for which the DSS is responsible,
                 but has no other requirements.
        """
        super().__init__()
        scopes = {Scope.StrategicCoordination: "create and delete subscriptions"}
        # This is an UTMClientSession
        self._dss = dss.get_instance(scopes)
        self._pid = [self._dss.participant_id]
        self._sub_id = id_generator.id_factory.make_id(self.SUB_TYPE)
        self._uss_area = uss_area.specification

        # Keep the footprint, no altitudes
        self._uss_area_volume4d = Volume4D(
            volume=Volume3D(outline_polygon=Polygon(vertices=self._uss_area.footprint))
        )

        self._sub_generation_params = dict(
            subscription_id=self._sub_id,
            # One of these must be true for the subscription creation to be accepted
            notify_for_op_intents=True,
            notify_for_constraints=False,
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)
        self._setup_case()
        self.begin_test_case("Subscription Validation")

        self.begin_test_step("Subscription duration limitations")
        self._create_too_long_subscription()
        self.end_test_step()

        self.end_test_case()
        self.end_test_scenario()

    def _setup_case(self):
        self.begin_test_case("Setup")

        self._ensure_clean_workspace_step()

        self.end_test_case()

    def _ensure_clean_workspace_step(self):
        self.begin_test_step("Ensure clean workspace")
        # Start by dropping any active sub
        self._ensure_no_active_subs_exist()
        # Check for subscriptions that will collide with our IDs and drop them
        self._ensure_test_sub_ids_do_not_exist()
        self.end_test_step()

    def _ensure_test_sub_ids_do_not_exist(self):
        test_step_fragments.cleanup_sub(self, self._dss, self._sub_id)

    def _ensure_no_active_subs_exist(self):
        test_step_fragments.cleanup_active_subs(
            self,
            self._dss,
            self._uss_area_volume4d,
        )

    def _create_too_long_subscription(self):
        """Try to end up with a subscription that is too long on the DSS by:
        - trying to create such a subscription
        - trying to mutate an existing subscription to be too long
        """

        start_time = datetime.utcnow() - timedelta(minutes=1)
        invalid_duration = timedelta(hours=24, minutes=10)

        invalid_creation_params = self._uss_area.get_new_subscription_params(
            start_time=start_time,
            duration=invalid_duration,
            **self._sub_generation_params,
        )

        # Try a direct creation
        creation_attempt = self._dss.upsert_subscription(**invalid_creation_params)
        self.record_query(creation_attempt)

        with self.check("Don't create a too long subscription", self._pid) as check:
            if creation_attempt.response.status_code == 400:
                pass
            else:
                self._check_properly_truncated(check, creation_attempt)

        valid_duration = timedelta(hours=24)
        valid_creation_params = self._uss_area.get_new_subscription_params(
            start_time=start_time,
            duration=valid_duration,
            **self._sub_generation_params,
        )

        # Try mutating a valid subscription
        valid_creation = self._dss.upsert_subscription(**valid_creation_params)
        self.record_query(valid_creation)

        with self.check(
            "Accept a subscription of maximal duration", self._pid
        ) as check:
            if valid_creation.response.status_code != 200:
                check.record_failed(
                    summary="DSS failed to create a valid subscription",
                    details=f"{self._dss.participant_id} DSS instance has returned a non-200 response "
                    f"when creating a subscription with the maximally allowed duration of 24 hours.",
                    query_timestamps=[valid_creation.request.timestamp],
                )
                # We can end here if this fails and the severity did not cause an early abort
                return

        invalid_mutation_params = valid_creation_params.copy()
        invalid_mutation_params["end_time"] = (
            valid_creation_params["start_time"] + invalid_duration
        )

        mutation_attempt = self._dss.upsert_subscription(
            **invalid_mutation_params, version=valid_creation.subscription.version
        )
        self.record_query(mutation_attempt)

        with self.check(
            "Don't mutate a subscription to be too long", self._pid
        ) as check:
            if mutation_attempt.response.status_code == 400:
                pass
            else:
                self._check_properly_truncated(check, mutation_attempt)

    def _check_properly_truncated(
        self, check: PendingCheck, changed: MutatedSubscription
    ):
        duration = changed.subscription.duration
        # In case of success, we obtained the effectively created subscription:
        if _24H_MIN_TOLERANCE_S < duration.total_seconds() < _24H_MAX_TOLERANCE_S:
            # All is good
            pass
        else:
            check.record_failed(
                summary="DSS failed to reject or truncate subscription that exceeded 24 hours",
                details=f"{self._dss.participant_id} DSS instance has returned a non-properly truncated subscription "
                f"(duration: {duration}) "
                f"when the expectation was either to fail or to truncate at 24 hours.",
                query_timestamps=[changed.query.request.timestamp],
            )
            # If a subscription was created, we want to delete it before continuing:
            self.record_query(
                self._dss.delete_subscription(
                    sub_id=self._sub_id, sub_version=changed.subscription.version
                )
            )

    def cleanup(self):
        self.begin_cleanup()
        self._ensure_test_sub_ids_do_not_exist()
        self.end_cleanup()
