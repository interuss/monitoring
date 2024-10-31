# Get mock_uss interactions test step fragment
This step obtains interactions of interest from mock_uss.

## 🛑 Mock USS interactions logs retrievable check
The Mock USSes provide a GET endpoint to retrieve all the interactions that took place between them and other USSes
after a particular time.
If there is any error retrieving these interactions, this check will fail as per **[interuss.mock_uss.hosted_instance.ExposeInterface](../../../requirements/interuss/mock_uss/hosted_instance.md)**.
