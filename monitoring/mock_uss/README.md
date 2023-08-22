## Summary

`mock_uss` contains mock implementations of a number of USS services.  It
provides a development-level web server that responds to requests to the USS
endpoints defined in the relevant ASTM standards in a standards-compliant
manner, as well as
[automated testing interaction interfaces](https://github.com/interuss/automated_testing_interfaces)
defined by InterUSS, and ad-hoc interfaces accessible to other monitoring
tools.

## Functionality sets

The same mock_uss binary can be configured to behave as one of many different
types of USSs by enabling and configuring different sets of functionality.
The available functionality sets are:

* [`atproxy_client`](atproxy_client): [atproxy](../atproxy) client/backend
* [`geoawareness`](geoawareness): Geo-awareness provider
* [`msgsigning`](msgsigning): [IETF HTTP Message Signatures](https://datatracker.ietf.org/doc/draft-ietf-httpbis-message-signatures/)
* [`riddp`](riddp): Remote ID Display Provider
* [`ridsp`](ridsp): Remote ID Service Provider
* [`scdsc`](scdsc): ASTM F3548 strategic coordinator
* [`tracer`](tracer): Interoperability ecosystem tracer logger


## Local deployment

A set of mock_uss instances intended to enable many uss_qualifier tests can be deployed locally as described in [uss_qualifier local testing](../uss_qualifier/local_testing.md).
