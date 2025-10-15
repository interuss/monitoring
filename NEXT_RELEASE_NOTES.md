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

# Release Notes for v0.21.0

## Mandatory migration tasks

## Optional migration tasks

## Important information
