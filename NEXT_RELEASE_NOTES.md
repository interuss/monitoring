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

# Release Notes for v0.20.0

## Mandatory migration tasks

### Update PlanningAreaResource

Resources of type `resources.PlanningAreaResource` now have their volume specified via a separate `resource.VolumeResource` resource, which needs to be passed as a dependency.

Previously, a planning area would be specified as:

```yaml
planning_area:
  $content_schema: monitoring/uss_qualifier/resources/definitions/ResourceDeclaration.json
  resource_type: resources.PlanningAreaResource
  specification:
    base_url: https://testdummy.interuss.org/interuss/monitoring/uss_qualifier/configurations/dev/f3548_self_contained/planning_area
    volume:
      outline_polygon:
        vertices:
          - lat: 37.1853
            lng: -80.6140
          - lat: 37.2148
            lng: -80.6140
          - lat: 37.2148
            lng: -80.5440
          - lat: 37.1853
            lng: -80.5440
      altitude_lower:
        value: 0
        reference: W84
        units: M
      altitude_upper:
        value: 3048
        reference: W84
        units: M
```

The volume needs to ve moved to a separate `VolumeResource`, and references in the `dependencies` of the existing `PlanningAreaResource`:

```yaml
# Add a new resource:
planning_area_volume:
  $content_schema: monitoring/uss_qualifier/resources/definitions/ResourceDeclaration.json
  resource_type: resources.VolumeResource
  specification:
    template:
      outline_polygon:
        vertices:
          - lat: 37.1853
            lng: -80.6140
          - lat: 37.2148
            lng: -80.6140
          - lat: 37.2148
            lng: -80.5440
          - lat: 37.1853
            lng: -80.5440
      altitude_lower:
          value: 0
          reference: W84
          units: M
      altitude_upper:
          value: 3048
          reference: W84
          units: M

# Add a dependencies section with a 'volume' to the existing resource.
planning_area:
  $content_schema: monitoring/uss_qualifier/resources/definitions/ResourceDeclaration.json
  resource_type: resources.PlanningAreaResource
  dependencies:
    volume: planning_area_volume
  specification:
    base_url: https://testdummy.interuss.org/interuss/monitoring/uss_qualifier/configurations/dev/f3548_self_contained/planning_area
```

## Optional migration tasks

## Important information

* The RID test data of the [U-Space test configuration](monitoring/uss_qualifier/configurations/dev/uspace.yaml) has been adjusted not to overlap. ([#1198](https://github.com/interuss/monitoring/pull/1198))
