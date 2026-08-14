from datetime import UTC, datetime
from typing import Any

from loguru import logger

from monitoring.benchmarker.configurations.actions.action import BenchmarkActionName
from monitoring.benchmarker.configurations.actions.astm import (
    SubscriptionCreationMode,
    SubscriptionDeletionMode,
)
from monitoring.benchmarker.configurations.actions.f3411 import (
    CreateSubscription,
    DeleteSubscription,
    F3411ActionSpecification,
)
from monitoring.monitorlib.fetch import rid as fetch_rid
from monitoring.monitorlib.mutate import rid as mutate_rid
from monitoring.monitorlib.rid import RIDVersion
from monitoring.monitorlib.testing import make_fake_url
from monitoring.uss_qualifier.resources.astm.f3411.dss import (
    DSSInstance,
    DSSInstanceResource,
    DSSInstancesResource,
)
from monitoring.uss_qualifier.resources.definitions import ResourceID


def get_dss_instances(resource_pool: dict[ResourceID, Any]) -> list[DSSInstance]:
    """Retrieve all F3411 DSS instances from the resource pool."""
    dss_instances: list[DSSInstance] = []
    for res in resource_pool.values():
        if isinstance(res, DSSInstanceResource):
            dss_instances.append(res.dss_instance)
        elif isinstance(res, DSSInstancesResource):
            dss_instances.extend(res.dss_instances)
    return dss_instances


def select_dss_instance(
    dss_instances: list[DSSInstance], rid_version: RIDVersion | None = None
) -> DSSInstance:
    """Select a DSS instance matching the rid_version (or the first available)."""
    if not dss_instances:
        raise ValueError("No ASTM F3411 DSS instances found in resource pool")
    if rid_version is not None:
        matching = [dss for dss in dss_instances if dss.rid_version == rid_version]
        if not matching:
            raise ValueError(
                f"No ASTM F3411 DSS instances found in resource pool matching RID version '{rid_version}'"
            )
        return matching[0]
    return dss_instances[0]


def create_subscription(
    spec: CreateSubscription,
    resource_pool: dict[ResourceID, Any],
) -> None:
    dss_instances = get_dss_instances(resource_pool)
    sub = spec.subscription
    dss_instance = select_dss_instance(dss_instances, sub.rid_version)

    if spec.mode == SubscriptionCreationMode.GetDeleteCreate:
        logger.info(
            f"F3411 Action: Checking if subscription '{sub.subscription_id}' exists before creating..."
        )
        fetched_sub = fetch_rid.subscription(
            subscription_id=sub.subscription_id,
            rid_version=sub.rid_version,
            session=dss_instance.client,
            participant_id=dss_instance.participant_id,
        )
        if fetched_sub.status_code == 200 and fetched_sub.subscription:
            logger.info(
                f"F3411 Action: Existing subscription '{sub.subscription_id}' found (version {fetched_sub.subscription.version}); deleting it..."
            )
            del_result = mutate_rid.delete_subscription(
                subscription_id=sub.subscription_id,
                subscription_version=fetched_sub.subscription.version,
                rid_version=sub.rid_version,
                utm_client=dss_instance.client,
                participant_id=dss_instance.participant_id,
            )
            if not del_result.success:
                raise RuntimeError(
                    f"Failed to delete existing subscription '{sub.subscription_id}' during GetDeleteCreate: {del_result.errors}"
                )
        elif fetched_sub.status_code == 404:
            logger.info(
                f"F3411 Action: Subscription '{sub.subscription_id}' does not exist; proceeding to create."
            )
        else:
            raise RuntimeError(
                f"Failed to query subscription '{sub.subscription_id}' during GetDeleteCreate: {fetched_sub.errors}"
            )

        logger.info(f"F3411 Action: Creating subscription '{sub.subscription_id}'...")
        uss_base_url = make_fake_url()
        t0 = datetime.now(UTC)
        create_result = mutate_rid.upsert_subscription(
            area_vertices=sub.area.to_vertices(),
            alt_lo=sub.min_alt.to_w84_m(),
            alt_hi=sub.max_alt.to_w84_m(),
            start_time=t0,
            end_time=t0 + sub.duration.timedelta,
            uss_base_url=uss_base_url,
            subscription_id=sub.subscription_id,
            rid_version=sub.rid_version,
            utm_client=dss_instance.client,
            participant_id=dss_instance.participant_id,
        )
        if not create_result.success:
            raise RuntimeError(
                f"Failed to create subscription '{sub.subscription_id}': {create_result.errors}"
            )
        logger.info(
            f"F3411 Action: Successfully created subscription '{sub.subscription_id}'."
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
        raise ValueError("No ASTM F3411 DSS instances found in resource pool")

    if spec.mode == SubscriptionDeletionMode.GetDeleteIfExist:
        logger.info(
            f"F3411 Action: Checking if subscription '{spec.subscription_id}' exists before deleting..."
        )
        checked_versions: set[RIDVersion] = set()
        deleted = False
        for dss_instance in dss_instances:
            if dss_instance.rid_version in checked_versions:
                continue
            checked_versions.add(dss_instance.rid_version)

            fetched_sub = fetch_rid.subscription(
                subscription_id=spec.subscription_id,
                rid_version=dss_instance.rid_version,
                session=dss_instance.client,
                participant_id=dss_instance.participant_id,
            )
            if fetched_sub.status_code == 200 and fetched_sub.subscription:
                logger.info(
                    f"F3411 Action: Existing subscription '{spec.subscription_id}' found (version {fetched_sub.subscription.version}); deleting it..."
                )
                del_result = mutate_rid.delete_subscription(
                    subscription_id=spec.subscription_id,
                    subscription_version=fetched_sub.subscription.version,
                    rid_version=dss_instance.rid_version,
                    utm_client=dss_instance.client,
                    participant_id=dss_instance.participant_id,
                )
                if not del_result.success:
                    raise RuntimeError(
                        f"Failed to delete subscription '{spec.subscription_id}': {del_result.errors}"
                    )
                logger.info(
                    f"F3411 Action: Successfully deleted subscription '{spec.subscription_id}'."
                )
                deleted = True
                break
            elif fetched_sub.status_code == 404:
                continue
            else:
                raise RuntimeError(
                    f"Failed to query subscription '{spec.subscription_id}' during GetDeleteIfExist: {fetched_sub.errors}"
                )

        if not deleted:
            logger.info(
                f"F3411 Action: Subscription '{spec.subscription_id}' did not exist; nothing to delete."
            )
    else:
        raise NotImplementedError(
            f"Unsupported subscription deletion mode '{spec.mode}'"
        )


def run_f3411_action(
    action_name: BenchmarkActionName,
    f3411_spec: F3411ActionSpecification,
    resource_pool: dict[ResourceID, Any],
) -> None:
    action_performed = False
    if (
        "create_subscription" in f3411_spec
        and f3411_spec.create_subscription is not None
    ):
        logger.info(f"Action '{action_name}': Creating F3411 subscription...")
        create_subscription(f3411_spec.create_subscription, resource_pool)
        action_performed = True
    if (
        "delete_subscription" in f3411_spec
        and f3411_spec.delete_subscription is not None
    ):
        logger.info(f"Action '{action_name}': Deleting F3411 subscription...")
        delete_subscription(f3411_spec.delete_subscription, resource_pool)
        action_performed = True
    if not action_performed:
        raise ValueError(
            f"Action '{action_name}' F3411ActionSpecification did not specify any supported action"
        )
