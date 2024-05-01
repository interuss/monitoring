# No OIR in workspace test step fragment

## ⚠️ Any existing operational intent reference has been removed check

If, after cleanup, one or more operational intent reference are still present at the DSS, this scenario cannot proceed.

This scenario is able to remove any operational intent reference that belongs to the configured credentials, but it cannot remove references
that belong to other credentials.

A regular failure of this check indicates that other scenarios might not properly clean up their resources, or that the _Prepare Flight Planners_
scenario should be moved in front of the present one.

If this check fails, the rest of the scenario is entirely skipped.
