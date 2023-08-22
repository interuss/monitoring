# Diagnostic capability to monitor interactions in interoperability ecosystems

## Description
This diagnostic capability monitors UTM traffic in a specified area.  This
includes, when requested, remote ID Identification Service Areas, strategic
deconfliction Operational Intents, and Constraints.  This tool records data in a
way not allowed in a standards-compliant production system, so should not be run
on a production system.

## Polling
Polling periodically queries the DSS regarding the objects of interest and notes
when they appear, change, or disappear.  The primary advantage to this mode is
that it operates as a client only and does not require routing to support an
externally-accessible server.  One disadvantage is that fast changes are not
detected.  For instance, if an ISA was added and then deleted all within a
single polling period, this tool would not create an record of that ISA.

## Subscribe
The Subscribe capability emplaces Subscriptions in the DSS and listens for
incoming notifications of changes from other USSs.  The two primary advantages
to this capability are that no ongoing polling is necessary and details of
Entities are delivered automatically -- the only outgoing requests happen at
initialization and shutdown.  The disadvantages include requiring an external
route to the mock_uss instance, probably with TLS unless the TLS check is
disabled in the DSS, and that information logging is dependent on USSs behaving
correctly and sending notifications upon DSS prompting.

### External route
One important argument when using the subscribe capability is
`MOCK_USS_BASE_URL`.  This should be the URL at which the mock_uss container can
be reached externally.  Note that this URL will probably need to use https with
non-local systems (to satisfy DSS validation), but the tracer container only
serves via http.  This means a user will need to provide their own TLS
termination for the external endpoint and forward traffic to the tracer
container in order to use the tracer subscribe capability.

## Log viewer
Visit /tracer/logs to see a list of log entries recorded by tracer while the
current session has been running.

## Invocation
From the repository root:

```shell script
./monitoring/mock_uss/run_locally_tracer.sh
```

See that script for parameters that can be adjusted for a deployed system.
