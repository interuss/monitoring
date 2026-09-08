import json
from datetime import UTC, datetime
from typing import Any

from loguru import logger
from uas_standards.astm.f3548.v21.api import EntityID, Subscription
from uas_standards.astm.f3548.v21.constants import Scope

from monitoring.benchmarker.configurations.actions.action import BenchmarkActionName
from monitoring.benchmarker.configurations.actions.astm import (
    SubscriptionCreationMode,
    SubscriptionDeletionMode,
)
from monitoring.benchmarker.configurations.actions.f3548 import (
    CreateSubscription,
    DeleteSubscription,
    F3548ActionSpecification,
)
from monitoring.monitorlib.inspection import calling_function_name
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3548.v21.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID


def get_dss_instances(resource_pool: dict[ResourceID, Any]) -> list[DSSInstance]:
    """Retrieve all F3548 DSS instances from the resource pool."""
    scopes_required = {
        Scope.StrategicCoordination.value: "managing subscriptions for strategic conflict detection",
    }
    dss_instances: list[DSSInstance] = []
    for res in resource_pool.values():
        if isinstance(res, DSSInstanceResource):
            dss_instances.append(res.get_instance(scopes_required))
        elif isinstance(res, DSSInstancesResource):
            for dss_instance_res in res.dss_instances:
                dss_instances.append(dss_instance_res.get_instance(scopes_required))
    return dss_instances


def _remove_operational_intent(
    op_intent_id: EntityID, dss_instance: DSSInstance
) -> None:
    oi_ref, _ = dss_instance.get_op_intent_reference(op_intent_id)
    if not oi_ref.ovn:
        raise RuntimeError(
            f"When attempting to remove operational intent '{op_intent_id}', fetching the operational intent reference did not return an OVN"
        )
    dss_instance.delete_op_intent(oi_ref.id, oi_ref.ovn)


def _remove_subscription(subscription: Subscription, dss_instance: DSSInstance) -> None:
    if subscription.dependent_operational_intents:
        n_oi_refs = len(subscription.dependent_operational_intents)
        logger.warning(
            f"Subscription '{subscription.id}' has {n_oi_refs} dependent operational intents; attempting to remove operational intents {', '.join(subscription.dependent_operational_intents)}"
        )
        for op_intent_id in subscription.dependent_operational_intents:
            _remove_operational_intent(op_intent_id, dss_instance)
        logger.info(
            f"Removed {n_oi_refs} operational intent references dependent on subscription '{subscription.id}'"
        )

    del_result = dss_instance.delete_subscription(
        sub_id=subscription.id,
        sub_version=subscription.version,
    )
    if not del_result.success:
        logger.error(
            f"Subscription deletion error:\n{json.dumps(del_result, indent=2)}"
        )
        raise RuntimeError(
            f"Failed to delete existing subscription '{subscription.id}' during {calling_function_name(levels=1)}: {del_result.errors}"
        )


def create_subscription(
    spec: CreateSubscription,
    resource_pool: dict[ResourceID, Any],
) -> None:
    dss_instances = get_dss_instances(resource_pool)
    if not dss_instances:
        raise ValueError("No ASTM F3548 DSS instances found in resource pool")
    sub = spec.subscription
    dss_instance = dss_instances[0]

    if spec.mode == SubscriptionCreationMode.GetDeleteCreate:
        logger.info(
            f"F3548 Action: Checking if subscription '{sub.subscription_id}' exists before creating..."
        )
        fetched_sub = dss_instance.get_subscription(sub.subscription_id)
        if fetched_sub.status_code == 200 and fetched_sub.subscription is not None:
            logger.info(
                f"F3548 Action: Existing subscription '{sub.subscription_id}' found (version {fetched_sub.subscription.version}); deleting it..."
            )
            _remove_subscription(fetched_sub.subscription, dss_instance)
        elif fetched_sub.status_code == 404:
            logger.info(
                f"F3548 Action: Subscription '{sub.subscription_id}' does not exist; proceeding to create."
            )
        else:
            logger.error(
                f"Subscription query error:\n{json.dumps(fetched_sub, indent=2)}"
            )
            raise RuntimeError(
                f"Failed to query subscription '{sub.subscription_id}' during GetDeleteCreate: {fetched_sub.errors}"
            )

        logger.info(f"F3548 Action: Creating subscription '{sub.subscription_id}'...")
        uss_base_url = make_fake_url()
        t0 = datetime.now(UTC)
        notify_for_op_intents = (
            sub.notify_for_op_intents
            if "notify_for_op_intents" in sub and sub.notify_for_op_intents is not None
            else True
        )
        notify_for_constraints = (
            sub.notify_for_constraints
            if "notify_for_constraints" in sub
            and sub.notify_for_constraints is not None
            else False
        )
        create_result = dss_instance.upsert_subscription(
            area_vertices=sub.area.to_latlngrect(),
            start_time=t0,
            end_time=t0 + sub.duration.timedelta,
            base_url=uss_base_url,
            sub_id=sub.subscription_id,
            notify_for_op_intents=notify_for_op_intents,
            notify_for_constraints=notify_for_constraints,
            min_alt_m=sub.min_alt.to_w84_m(),
            max_alt_m=sub.max_alt.to_w84_m(),
        )
        if not create_result.success:
            logger.error(
                f"Subscription creation error:\n{json.dumps(create_result, indent=2)}"
            )
            raise RuntimeError(
                f"Failed to create subscription '{sub.subscription_id}': {create_result.errors}"
            )
        logger.info(
            f"F3548 Action: Successfully created subscription '{sub.subscription_id}'."
        )
    else:
        raise NotImplementedError(
            f"Unsupported subscription creation mode '{spec.mode}'"
        )


def delete_subscription(
    spec: DeleteSubscription,
    resource_pool: dict[ResourceID, Any],
) -> None:
    dss_instances = get_dss_instances(resource_pool)
    if not dss_instances:
        raise ValueError("No ASTM F3548 DSS instances found in resource pool")
    dss_instance = dss_instances[0]

    if spec.mode == SubscriptionDeletionMode.GetDeleteIfExist:
        logger.info(
            f"F3548 Action: Checking if subscription '{spec.subscription_id}' exists before deleting..."
        )
        fetched_sub = dss_instance.get_subscription(spec.subscription_id)
        if fetched_sub.status_code == 200 and fetched_sub.subscription is not None:
            logger.info(
                f"F3548 Action: Existing subscription '{spec.subscription_id}' found (version {fetched_sub.subscription.version}); deleting it..."
            )
            _remove_subscription(fetched_sub.subscription, dss_instance)
            logger.info(
                f"F3548 Action: Successfully deleted subscription '{spec.subscription_id}'."
            )
        elif fetched_sub.status_code == 404:
            logger.info(
                f"F3548 Action: Subscription '{spec.subscription_id}' did not exist; nothing to delete."
            )
        else:
            logger.error(
                f"Subscription query error:\n{json.dumps(fetched_sub, indent=2)}"
            )
            raise RuntimeError(
                f"Failed to query subscription '{spec.subscription_id}' during GetDeleteIfExist: {fetched_sub.errors}"
            )

    else:
        raise NotImplementedError(
            f"Unsupported subscription deletion mode '{spec.mode}'"
        )


def run_f3548_action(
    action_name: BenchmarkActionName,
    f3548_spec: F3548ActionSpecification,
    resource_pool: dict[ResourceID, Any],
) -> None:
    action_performed = False
    if (
        "create_subscription" in f3548_spec
        and f3548_spec.create_subscription is not None
    ):
        logger.info(f"Action '{action_name}': Creating F3548 subscription...")
        create_subscription(f3548_spec.create_subscription, resource_pool)
        action_performed = True
    if (
        "delete_subscription" in f3548_spec
        and f3548_spec.delete_subscription is not None
    ):
        logger.info(f"Action '{action_name}': Deleting F3548 subscription...")
        delete_subscription(f3548_spec.delete_subscription, resource_pool)
        action_performed = True
    if not action_performed:
        raise ValueError(
            f"Action '{action_name}' F3548ActionSpecification did not specify any supported action"
        )
