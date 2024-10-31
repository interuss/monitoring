# ASTM NetRID DSS: Endpoint encryption test scenario

## Overview

Ensures that a DSS only exposes its endpoints via HTTPS.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

### test_search_area

[`VerticesResource`](../../../../../resources/vertices.py) to be used in this scenario for a search query.

## Connect to HTTP port test case

Tries to connect to the http port (80) of the DSS instance, and expects either a refusal of the connection,
or a redirection to the https port (443).

Note: this test case will be skipped if the DSS instance is configured to use HTTP.

### Attempt GET on root path via HTTP test step

This test step attempts an HTTP GET request on the root path of the DSS instance, using plain HTTP,
and expects either a connection refusal or a redirection to the equivalent HTTPS URL.

#### 🛑 Connection fails or response redirects to HTTPS endpoint check

If the DSS instance accepts the connection on the HTTP port and does not immediately redirect to the HTTPS port
upon reception of an HTTP request, it is in violation of **[astm.f3411.v19.DSS0020](../../../../../requirements/astm/f3411/v19.md)**.

### Attempt GET on a known valid path via HTTP test step

This test step attempts an HTTP GET request on a known valid path by searching for ISAs in the configured planning area.

#### 🛑 Connection fails or response redirects to HTTPS endpoint check

If the DSS instance accepts the connection on the HTTP port and does not immediately redirect to the HTTPS port
upon reception of an HTTP request, it is in violation of **[astm.f3411.v19.DSS0020](../../../../../requirements/astm/f3411/v19.md)**.

## Connect to HTTPS port test case

Try to connect to the DSS instance over HTTPS.

### Attempt to connect to the DSS instance on the HTTPS port test step

#### 🛑 A request can be sent over HTTPS check

If the DSS instance cannot be reached over HTTPS, it is in violation of **[astm.f3411.v19.DSS0020](../../../../../requirements/astm/f3411/v19.md)**.
