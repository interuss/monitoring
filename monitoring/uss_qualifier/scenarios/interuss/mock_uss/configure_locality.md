# Configure mock_uss locality test scenario

This test scenario instructs a collection of mock USS instances to use a specified locality.  The old locality is recorded so that the [UnconfigureLocality test scenario](./unconfigure_locality.md) can set the locality values back to what they were before.

This scenario should not generally be used directly; instead, the [WithLocality action generator](../../../action_generators/interuss/mock_uss/with_locality.py) should be used to temporarily change the locality of mock_uss instances when appropriate.

## Resources

### mock_uss_instances

The means to communicate with the mock USS instances that will have their localities set.

### locality

The locality to set all mock USS instances to.

## Set locality test case

### Get current locality value test step

#### Query ok check

If a mock USS instance doesn't respond properly to a request to get its current locality, **[interuss.mock_uss.hosted_instance.ExposeInterface](../../../requirements/interuss/mock_uss/hosted_instance.md)** is not met.

### Set locality to desired value test step

#### Query ok check

If a mock USS instance doesn't respond properly to a request to change its locality, **[interuss.mock_uss.hosted_instance.ExposeInterface](../../../requirements/interuss/mock_uss/hosted_instance.md)** is not met.

## Cleanup

### Restore locality check

If uss_qualifier cannot restore a mock_uss instance's locality to its old value when rolling back incomplete locality changes, **[interuss.mock_uss.hosted_instance.ExposeInterface](../../../requirements/interuss/mock_uss/hosted_instance.md)** is not met.
