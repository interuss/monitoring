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

# Release Notes for v0.36.0

## Mandatory migration tasks

## Optional migration tasks

* Added `allow_duplicate_positions` flag (defaulting to `False`) to `generate_aircraft_states` and `AdjacentCircularFlightsSimulatorConfiguration`. Currently, duplicate positions may be generated (e.g. if the configured flight duration is longer than the path's unique loop length). With this flag set to `False` (the new default), the simulator will now detect duplicate positions and raise a `ValueError`. To allow duplicate positions as before, set `allow_duplicate_positions: true` in your circular flight simulation configurations.

## Important information
