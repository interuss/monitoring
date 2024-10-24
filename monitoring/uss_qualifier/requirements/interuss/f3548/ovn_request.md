# OVN Request Optional Extension to ASTM F3548-21 Requirements
This optional extension not part of the original F3548 standard API allows a USS to request a specific OVN when creating
or updating an operational intent.

## DSS requirements
### <tt>ImplementAPI</tt>
If a DSS has support for the optional extension, it must implement the endpoints `createOperationalIntentReference` and
`updateOperationalIntentReference` with the support for the optional field `requested_ovn_suffix` as defined in the API,
accept requests in the data format prescribed in the API, and respond in the data format prescribed in the API.
If there is a problem using the API such as a connection error, invalid response code, or invalid data, the DSS will
have failed to meet this requirement.
