# ASTM NetRID DSS: Endpoint encryption test scenario

## Overview

Ensures that a DSS only exposes its endpoints via HTTPS.

## Resources

### dss

[`DSSInstanceResource`](../../../../../resources/astm/f3411/dss.py) to be tested in this scenario.

## Validate endpoint encryption test case

Tries to connect to the http port (80) of the DSS instance, and expects either a refusal of the connection,
or a redirection to the https port (443).

Note that this test case will be skipped if the DSS instance is configured to use HTTP.
Note that the requests made in this case are made without any form of authentication, as the completion of any form
of communication over an unencrypted channel, even a 40X status response, is considered a failure.

### Attempt GET on a known valid path via HTTP test step
Attempts the operation `GetIdentificationServiceArea` on the DSS through HTTP with a non-existing ID.

#### 🛑 HTTP GET fails or redirects to HTTPS check
If the DSS instance serves the request through unencrypted HTTP, it is in violation of **[astm.f3411.v19.DSS0020](../../../../../requirements/astm/f3411/v19.md)**.
Only the last request after all redirections are followed is considered.

### Attempt GET on a known valid path via HTTPS test step
Attempts the operation `GetIdentificationServiceArea` on the DSS through HTTPS with a non-existing ID.

#### 🛑 HTTPS GET succeeds check
If the DSS instance does not serve the request through encrypted HTTPS, or redirects it to HTTP, it is in violation of **[astm.f3411.v19.DSS0020](../../../../../requirements/astm/f3411/v19.md)**.
Only the last request after all redirections are followed is considered.
