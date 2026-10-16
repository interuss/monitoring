## Overview

In order to execute a test scenario, it is normally necessary to provide configuration-specific resources that the scenario depends on.  This could include, for example:

* The set of NetRID Service Providers under test in a particular environment
* Flight data to be injected into the NetRID service providers, reflective of the jurisdiction in which the test is being conducted
* Performance evaluation criteria defining what additional latency or other factors may be introduced by the test apparatus

These things are provided to the test scenarios as resources via a named dependency injection framework described below.

## Resource types

A resource provider to a test scenario is an instance of a particular kind of resource.  This kind of resource is the "resource type", and resource types are implemented as subclasses of [the abstract `Resource` class](resource.py).  Therefore, a resource available to a test scenario will always be an instance of a subclass of `Resource`.

### Creating a new resource type

A new resource type is simply a Python subclass of [the abstract `Resource` class](resource.py).  It should be placed in the appropriate sub-module of the [`resources` module](.).  A requirement for any resource type is that the resource type must be constructable from 1) a specification for the resource and 2) any required dependencies (which must also be resources).

Note that resources which use content from external (not included in the configuration itself) files should specify an [ExternalFile](./files.py) in their specification and use the loading routines in [files.py](files.py).

## Using resources in a test scenario

A test scenario requiring a resource should declare a named dependency on a resource of a particular type.  For example, the ASTM NetRID Nominal Behavior test scenario may declare that it has a `service_providers` dependency which must be satisfied with a `netrid.NetRIDServiceProviders` resource type.  The test scenario's configuration must specify the resource from the global resource pool (by specifying the globally-unique ID of the resource) that should be used to satisfy the test scenario's `service_providers` dependency.

## Declaring resources

Resources for a given test configuration are all declared in a single global resource collection, and then the resources generated from that collection are placed in a single global resource pool.  A resource from that pool may be referenced using its globally-unique (within the test configuration) identifier.  To declare a resource, a [`ResourceDeclaration`](resource.py) must be added to the test configuration's [`ResourceCollection`](resource.py).

1. A particular instance of test resource must have a name that is unique in the full pool of resources in the test configuration.
    * Example: `netrid.service_providers`, which would provide access to the RID injection API for each ASTM NetRID Service Provider under test.
    * Example: `netrid.flight_data.nominal_flights`, which would provide flight data for nominal flights which could be injected into Service Providers under test.
2. Every type of test resource must define a "resource specification", which is a serializable data type that fully defines how to create an instance of that resource type.
3. Every type of test resource must define how to create an instance of the test resource from an instance of the resource specification.

Dependency resource IDs may be suffixed with `?` to indicate that the dependency is optional.  Explicit constructor parameters must have a default value to accept optional dependencies.  Dependencies accepted through `**kwargs` are treated as having an implicit default of `None`.  Missing optional dependencies are omitted from the constructor call, so they do not appear in the `kwargs` dictionary.


## Resource-providing resources

A `ResourceProvidingResource[SpecificationType, ResourceType]` provides resources of `ResourceType` according to a desired key, such as an index.  This is useful when a test scenario needs multiple related instances of a resource (e.g., spatially separated flights derived from a single base flight).

To use a `ResourceProvidingResource`:

1. Declare it like any other resource, with the dependencies its implementation requires.
2. Call `provide_resource_for` with the supported keys (e.g., `provide_resource_for(index=0)`).

## Selecting a single provided resource

Use `resources.resource.SingularResource[ResourceType]` to place one indexed provider result in the resource pool:

```yaml
conflicting_flights:
  resource_type: resources.resource.SingularResource[resources.flight_planning.FlightIntentsResource]
  dependencies:
    provider: conflicting_flights_provider
  specification:
    index: 0
```

The pool contains the actual resource returned by `provider.provide_resource_for(index=0)` rather than the SingularResource itself, so consumers can depend directly on `FlightIntentsResource`.  The selected resource retains its own origin and generic type metadata.  Providers must support an integer `index` key and return the declared resource type.

## Resolving into pools

Resource construction calls `resolve_resource()` after assigning generic type bindings.  The default implementation returns `self`; selectors may override it to return the resource to expose to consumers.  Resolution happens once during construction, and the result is reused by downstream dependencies.
