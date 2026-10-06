# Upcoming Release Notes

## About & Process

This file aggregates the changes and updates that will be included in the next release notes.

Its goal is to facilitate the process of writing release notes, as well as making it easier to use this repository from its `main` branch.

Pull requests that introduce major changes, especially breaking changes to configurations, or otherwise important new features, should update this file
with the details necessary for users to migrate and fully use any added functionality.

At the time of release, the content below the horizontal line in this file will be copied to the release notes and deleted from this file.

### Template & Examples

The release notes should contain at least the following sections:

#### Mandatory migration tasks

* Rename uss_qualifier ABCScenario in test configurations/suites to XYZScenario
    * Note that XYZScenario is currently skipped in most sample and development configurations.
* Rename uss_qualifier resource in test configurations/suites:
    * resources.a.b.ABCResource -> resources.x.y.XYResource

#### Optional migration tasks

* Rename uss_qualifier resource resources.x.y.z.SomeResource -> resources.SomeResource
    * For compatibility, the old name is currently an alias to the new name (this use produces a deprecation warning), but support for the old name will be removed in a future version.

#### Important information

* Feature X has changed behavior to Y

--------------------------------------------------------------------------------------------------------------------

# Release Notes for v0.37.0

## Mandatory migration tasks

* For any uss_qualifier test configurations using any of the test suites `suites.astm.utm.f3548_21`, `suites.faa.uft.message_signing`, `suites.uspace.flight_auth`, or `suites.uspace.required_services`, the following resources must be changed:
    * `priority_preemption_flights` was previously an optional `resources.flight_planning.FlightIntentsResource`.  If this resource was previously provided to one of the above test suites, a new resource named `priority_preemption_flights_provider` must be provided instead.  This new resource must be a `resources.ResourceProvidingResource[resources.flight_planning.FlightIntentsResource]`, and one suitable concrete implementation is a `resources.geospatial.TriangularCascadeSoutheastResource`.  See [f3548_self_contained](./monitoring/uss_qualifier/configurations/dev/f3548_self_contained.yaml) for an example.

## Optional migration tasks

## Important information
