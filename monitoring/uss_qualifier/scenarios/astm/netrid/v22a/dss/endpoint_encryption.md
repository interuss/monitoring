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

### Attempt to connect to the DSS instance on the HTTP port test step

#### 🛑 Connection to HTTP port fails or redirects to HTTPS port check

If the DSS instance accepts the connection on the HTTP port and does not immediately redirect to the HTTPS port
upon reception of an HTTP request, it is in violation of **[astm.f3411.v22a.DSS0020](../../../../../requirements/astm/f3411/v22a.md)**.

## Connect to HTTPS port test case

Try to connect to the DSS instance over HTTPS.

### Attempt to connect to the DSS instance on the HTTPS port test step

#### 🛑 A request can be sent over HTTPS check

If the DSS instance cannot be reached over HTTPS, it is in violation of **[astm.f3411.v22a.DSS0020](../../../../../requirements/astm/f3411/v22a.md)**.
