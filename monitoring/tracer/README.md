# Diagnostic tool to monitor DSS and USS interactions

## Description
This diagnostic tool monitors UTM traffic in a specified area.  This includes,
when requested, remote ID Identification Service Areas and Subscriptions, and
strategic deconfliction Operations, Constraints, and Subscriptions.  This tool
records data in a way not allowed in a standards-compliant production system, so
cannot be run on a compliant production system.

## Building the image
From the [`root folder of this repo`](../..) folder, first build the monitoring
image:

```shell script
./monitoring/build.sh
```

## Polling mode
Polling mode periodically queries the DSS regarding the objects of interest and
notes when they appear, change, or disappear.  The primary advantage to this
mode is that it operates as a client only and does not require routing to
support an externally-accessible server.  One disadvantage is that fast changes
are not detected.  For instance, if an ISA was added and then deleted all within
a single polling period, this tool would not create a record of that ISA.

### Invocation
```shell script
docker run --name tracer_run --rm -v `pwd`/logs:/logs interuss/dss/tracer \
    -w /app/monitoring/tracer python tracer_poll.py \
    --auth=<SPEC> \
    --dss=https://example.com \
    --area=34.1234,-123.4567,34.4567,-123.1234 \
    --output-folder=/logs \
    --rid-isa-poll-interval=15 \
    --scd-operation-poll-interval=15 \
    --scd-constraint-poll-interval=15
```

The auth SPEC defines how to obtain access tokens to access the DSS instances
and USSs in the network. See
[the auth spec documentation](../monitorlib/README.md#Auth_specs) for examples
and more information.

## Subscribe mode
Subscribe mode emplaces Subscriptions in the DSS and listens for incoming
notifications of changes from other USSs.  The two primary advantages to this
mode are that no ongoing polling is necessary and details of Entities are
delivered automatically -- the only outgoing requests happen at initialization
and shutdown.  The disadvantages include requiring an external route to this,
probably with TLS unless the TLS check is disabled in the DSS, and that
information logging is dependent on USSs behaving correctly and sending
notifications upon DSS prompting.

### Invocation
Make a copy of [`run_subscribe.sh`](run_subscribe.sh) and edit the arguments as
appropriate.  Then simply run your copy of that script (`./run_subscribe.sh`).
To stop this container gracefully (so that Subscriptions are removed):
`docker container kill --signal=INT tracer_subscribe`

### External route
One important argument in subscribe mode is `--base-url`.  This should be the
URL at which the tracer container can be reached externally.  Note that this URL
will probably need to use https (to satisfy DSS validation), but the tracer
container only serves via http.  This means a user will need to provide their
own TLS termination for the external endpoint and forward traffic to the tracer
container in order to use tracer in subscribe mode.

### Log viewer
While tracer is running in subscribe mode, visit /logs relative to the base URL
(e.g., https://example.com/logs) to see a list of log entries recorded by tracer
while the current session has been running.
