# Attempt to create OIR with invalid requested OVN suffix query test step fragment
This test step fragment validates that the DSS rejects invalid attempts to request an OVN suffix.

## 🛑 Attempt to create OIR with invalid requested OVN suffix query rejected check
If the DSS accepts the OVN suffix, or fails with an error other than an HTTP code 400, this check will fail as per **[interuss.f3548.ovn_request.ImplementAPI](../../../requirements/interuss/f3548/ovn_request.md)**.
