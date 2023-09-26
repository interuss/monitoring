import datetime
from typing import Dict, List, Optional

import s2sphere
import yaml
from yaml.representer import Representer

from implicitdict import ImplicitDict
from monitoring.monitorlib import fetch, infrastructure, scd
from monitoring.monitorlib.geo import Polygon
from monitoring.monitorlib.geotemporal import Volume4D


class FetchedEntityReferences(fetch.Query):
    """Wrapper to interpret a DSS Entity query as a set of Entity references."""

    entity_type: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def error(self) -> Optional[str]:
        # Handle any errors
        if self.status_code != 200:
            return "Failed to search {} in DSS ({})".format(
                self.entity_type, self.status_code
            )
        if self.json_result is None:
            return "DSS response to search {} was not valid JSON".format(
                self.entity_type
            )
        for entity_ref in self.json_result.get(self.entity_type, []):
            if "id" not in entity_ref:
                return "DSS response to search {} included entry without id".format(
                    self.entity_type
                )
            if "manager" not in entity_ref:
                return "DSS response to search {} included {} without manager".format(
                    self.entity_type, entity_ref["id"]
                )
            if "uss_base_url" not in entity_ref:
                return (
                    "DSS response to search {} included {} without uss_base_url".format(
                        self.entity_type, entity_ref["id"]
                    )
                )
        return None

    @property
    def references_by_id(self) -> Dict:
        if self.json_result is None:
            return {}
        return {e["id"]: e for e in self.json_result.get(self.entity_type, [])}

    def has_different_content_than(self, other):
        if not isinstance(other, FetchedEntityReferences):
            return True
        if self.error != other.error:
            return True
        if self.success:
            my_refs = self.references_by_id
            other_refs = other.references_by_id
            for id in other_refs:
                if id not in my_refs:
                    return True
            for id, r in my_refs.items():
                if id not in other_refs or r != other_refs[id]:
                    return True
        return False


yaml.add_representer(FetchedEntityReferences, Representer.represent_dict)


def _entity_references(
    dss_resource_name: str,
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    alt_min_m: float = 0,
    alt_max_m: float = 3048,
) -> FetchedEntityReferences:
    # Query DSS for Entities in 4D volume of interest
    request_body = {
        "area_of_interest": Volume4D.from_values(
            start_time,
            end_time,
            alt_min_m,
            alt_max_m,
            polygon=Polygon.from_latlng_rect(latlngrect=area),
        ).to_f3548v21()
    }
    url = "/dss/v1/{}/query".format(dss_resource_name)
    scope = scd.SCOPE_CP if "constraint" in dss_resource_name else scd.SCOPE_SC
    entity_references = FetchedEntityReferences(
        fetch.query_and_describe(
            utm_client, "POST", url, json=request_body, scope=scope
        )
    )
    entity_references.entity_type = dss_resource_name
    return entity_references


def operational_intent_references(
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    alt_min_m: float = 0,
    alt_max_m: float = 3048,
) -> FetchedEntityReferences:
    return _entity_references(
        "operational_intent_references",
        utm_client,
        area,
        start_time,
        end_time,
        alt_min_m,
        alt_max_m,
    )


class FetchedEntity(fetch.Query):
    id_requested: Optional[str] = None
    entity_type: Optional[str] = None

    @property
    def success(self) -> bool:
        return self.error is None

    @property
    def reference(self) -> Optional[Dict]:
        if self.json_result is None:
            return None
        return self.json_result.get(self.entity_type, {}).get("reference", None)

    @property
    def details(self) -> Optional[Dict]:
        if self.json_result is None:
            return None
        return self.json_result.get(self.entity_type, {}).get("details", None)

    @property
    def error(self) -> Optional[str]:
        prefix = "USS query for {} {} ".format(self.entity_type, self.id_requested)

        if self.status_code != 200:
            msg = prefix + "indicated failure ({})".format(self.status_code)
            if "failure" in self.response:
                msg += ": " + self.response["failure"]
            return msg
        if self.json_result is None:
            return prefix + "did not return valid JSON"
        if self.entity_type not in self.json_result:
            return prefix + "did not contain {} field".format(self.entity_type)
        if self.reference is None:
            return prefix + "did not contain reference field"
        if self.details is None:
            return prefix + "did not contain details field"
        return None

    def has_different_content_than(self, other):
        if not isinstance(other, FetchedEntity):
            return True
        if self.success != other.success:
            return True
        if self.success:
            if self.reference != other.reference or self.details != other.details:
                return True
            return False
        else:
            return self.error != other.error


yaml.add_representer(FetchedEntity, Representer.represent_dict)


def _full_entity(
    uss_resource_name: str,
    uss_base_url: str,
    entity_id: str,
    utm_client: infrastructure.UTMClientSession,
) -> FetchedEntity:
    uss_entity_url = uss_base_url + "/uss/v1/{}s/{}".format(
        uss_resource_name, entity_id
    )

    # Query the USS for Entity details
    scope = scd.SCOPE_CP if "constraint" in uss_resource_name else scd.SCOPE_SC
    entity = FetchedEntity(
        fetch.query_and_describe(utm_client, "GET", uss_entity_url, scope=scope)
    )
    entity.id_requested = entity_id
    entity.entity_type = uss_resource_name
    return entity


def operational_intent(
    uss_base_url: str, entity_id: str, utm_client: infrastructure.UTMClientSession
) -> FetchedEntity:
    return _full_entity("operational_intent", uss_base_url, entity_id, utm_client)


class FetchedEntities(ImplicitDict):
    dss_query: FetchedEntityReferences
    uss_queries: Dict[str, FetchedEntity]
    cached_uss_queries: Dict[str, FetchedEntity]

    @property
    def success(self) -> bool:
        return not self.error

    @property
    def error(self) -> Optional[str]:
        dss_error = self.dss_query.error
        if dss_error is not None:
            return dss_error
        return None

    @property
    def entities_by_id(self) -> Dict[str, FetchedEntity]:
        entities = self.cached_entities_by_id.copy()
        for k, v in self.new_entities_by_id.items():
            entities[k] = v
        return entities

    @property
    def new_entities_by_id(self) -> Dict[str, FetchedEntity]:
        return self.uss_queries

    @property
    def cached_entities_by_id(self) -> Dict[str, FetchedEntity]:
        return self.cached_uss_queries

    def has_different_content_than(self, other):
        if not isinstance(other, FetchedEntities):
            return True
        if self.success != other.success:
            return True
        if self.dss_query.has_different_content_than(other.dss_query):
            return True

        my_entities = self.entities_by_id
        other_entities = other.entities_by_id
        for id, entity in my_entities.items():
            if id not in other_entities or entity.has_different_content_than(
                other_entities[id]
            ):
                return True
        for id in other_entities:
            if id not in my_entities:
                return True


yaml.add_representer(FetchedEntities, Representer.represent_dict)


class CachedEntity(ImplicitDict):
    reference: dict
    uss_query: FetchedEntity

    @property
    def uss_success(self) -> bool:
        return self.fetched_entity.success

    @property
    def reference(self) -> Dict:
        return self.reference

    @property
    def fetched_entity(self) -> FetchedEntity:
        return self.uss_query


def _entities(
    dss_resource_name: str,
    uss_resource_name: str,
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    alt_min_m: float = 0,
    alt_max_m: float = 3048,
    entity_cache: Optional[Dict[str, CachedEntity]] = None,
) -> FetchedEntities:
    fetched_references = _entity_references(
        dss_resource_name, utm_client, area, start_time, end_time, alt_min_m, alt_max_m
    )

    uss_queries: Dict[str, FetchedEntity] = {}
    cached_queries: Dict[str, FetchedEntity] = {}
    if fetched_references.success:
        if entity_cache is None:
            entity_cache = {}
        for entity_id, entity_ref in fetched_references.references_by_id.items():
            if (
                entity_id in entity_cache
                and entity_cache[entity_id].reference == entity_ref
                and entity_cache[entity_id].uss_success
            ):
                # Entity reference data in DSS is identical to the cached reference; do
                # not re-retrieve Entity details from USS
                cached_queries[entity_id] = entity_cache[entity_id].fetched_entity
                continue

            fetched_entity = _full_entity(
                uss_resource_name, entity_ref["uss_base_url"], entity_id, utm_client
            )
            uss_queries[entity_id] = fetched_entity
            entity_cache[entity_id] = CachedEntity(
                reference=entity_ref, uss_query=fetched_entity
            )

    return FetchedEntities(
        dss_query=fetched_references,
        uss_queries=uss_queries,
        cached_uss_queries=cached_queries,
    )


def operations(
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    alt_min_m: float = 0,
    alt_max_m: float = 3048,
    operation_cache: Optional[Dict[str, FetchedEntity]] = None,
) -> FetchedEntities:
    return _entities(
        "operational_intent_references",
        "operational_intent",
        utm_client,
        area,
        start_time,
        end_time,
        alt_min_m,
        alt_max_m,
        operation_cache,
    )


def constraints(
    utm_client: infrastructure.UTMClientSession,
    area: s2sphere.LatLngRect,
    start_time: datetime.datetime,
    end_time: datetime.datetime,
    alt_min_m: float = 0,
    alt_max_m: float = 3048,
    constraint_cache: Optional[Dict[str, FetchedEntity]] = None,
) -> FetchedEntities:
    return _entities(
        "constraint_references",
        "constraint",
        utm_client,
        area,
        start_time,
        end_time,
        alt_min_m,
        alt_max_m,
        constraint_cache,
    )


class FetchedSubscription(fetch.Query):
    @property
    def success(self) -> bool:
        return not self.errors

    @property
    def errors(self) -> List[str]:
        if self.status_code == 404:
            return []
        if self.status_code != 200:
            return ["Request to get Subscription failed ({})".format(self.status_code)]
        if self.json_result is None:
            return ["Request to get Subscription did not return valid JSON"]
        if not self._subscription.valid:
            return ["Invalid Subscription data"]
        return []

    @property
    def _subscription(self) -> scd.Subscription:
        return scd.Subscription(self.json_result.get("subscription", {}))

    @property
    def subscription(self) -> Optional[scd.Subscription]:
        if not self.success or self.status_code == 404:
            return None
        else:
            return self._subscription


yaml.add_representer(FetchedSubscription, Representer.represent_dict)


def subscription(
    utm_client: infrastructure.UTMClientSession, subscription_id: str
) -> FetchedSubscription:
    url = "/dss/v1/subscriptions/{}".format(subscription_id)
    result = fetch.query_and_describe(utm_client, "GET", url, scope=scd.SCOPE_SC)
    return FetchedSubscription(result)
