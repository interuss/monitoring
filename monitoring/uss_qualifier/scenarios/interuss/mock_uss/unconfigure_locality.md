# Unconfigure mock_uss locality test scenario

This test scenario restores the locality setting for a collection of mock USS instances following a [ConfigureLocality test scenario](./configure_locality.md).

## Resources

No resources are needed because they are stored by the [ConfigureLocality test scenario](./configure_locality.md).

## Restore locality test case

### Set locality to old value test step

The most recent ConfigureLocality test scenario instances recorded the old locality values and mock_uss instances.  This test step consumes that information to restore localities to their old values.

#### Query ok check

If a mock USS instance doesn't respond properly to a request to change its locality, **[interuss.mock_uss.hosted_instance.ExposeInterface](../../../requirements/interuss/mock_uss/hosted_instance.md)** is not met.
