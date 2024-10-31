import errno
import socket
from urllib.parse import urlparse

import requests
from future.backports.datetime import datetime

from monitoring.monitorlib import infrastructure
from monitoring.monitorlib.fetch import rid as fetch
from monitoring.uss_qualifier.resources import VerticesResource
from monitoring.uss_qualifier.resources.astm.f3411.dss import DSSInstanceResource
from monitoring.uss_qualifier.scenarios.scenario import GenericTestScenario
from monitoring.uss_qualifier.suites.suite import ExecutionContext


class EndpointEncryption(GenericTestScenario):
    """
    Ensures that the endpoints of a DSS are not accessible unencrypted:
     - HTTP access should be impossible or redirect to HTTPS
     - HTTPS access should be possible

    TODO: add a check for minimal cipher strength to a 128bit AES equivalent or more.
    """

    def __init__(
        self,
        dss: DSSInstanceResource,
        test_search_area: VerticesResource,
    ):
        super().__init__()
        self._dss = dss.dss_instance
        self._search_area = [
            v.as_s2sphere() for v in test_search_area.specification.vertices
        ]

        self._parsed_url = urlparse(self._dss.base_url)
        self._hostname = self._parsed_url.hostname

        self._http_base_url = f"http://{self._hostname}/{self._parsed_url.path}"

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        if self._hostname is None:
            self.record_note(
                "hostname",
                "Cannot check encryption requirement when DSS hostname is unspecified",
            )
            self.end_test_scenario()
            return

        if not self._dss.base_url.startswith("https://"):
            self.record_note(
                "encrypted_endpoints",
                "Cannot check encryption requirement when DSS endpoint is specified with an http:// base URL",
            )
            self.end_test_scenario()
            return

        self._case_http_unavailable_or_redirect()
        self._case_https_works()

        self.end_test_scenario()

    def _case_http_unavailable_or_redirect(self):
        self.begin_test_case("Connect to HTTP port")
        self.begin_test_step("Attempt GET on root path via HTTP")

        with self.check(
            "Connection to HTTP port fails or redirects to HTTPS port",
            self._dss.participant_id,
        ) as check:
            try:
                response = requests.get(
                    self._http_base_url,
                    timeout=10,
                    allow_redirects=False,
                )
                _check_is_redirect(self._parsed_url, check, response)
            except socket.error as e:
                if e.errno not in [errno.ECONNREFUSED, errno.ETIMEDOUT]:
                    check.record_failed(
                        "Connection to HTTP port failed for the unexpected reason",
                        details=f"Encountered socket error: {e}, while the expectation is to either run into a straight up connection refusal or a timeout.",
                    )

        self.begin_test_step("Attempt GET on a known valid path via HTTP")

        with self.check(
            "Connection to HTTP port fails or redirects to HTTPS port",
            self._dss.participant_id,
        ) as check:
            try:
                response = fetch.isas(
                    area=self._search_area,
                    start_time=datetime.now(),
                    end_time=datetime.now() + datetime.timedelta(days=1),
                    rid_version=self._dss.rid_version,
                    session=infrastructure.UTMClientSession(
                        self._http_base_url, self._dss.client.auth_adapter
                    ),
                    participant_id=self._dss.participant_id,
                )
                _check_is_redirect(self._parsed_url, check, response)
            except socket.error as e:
                if e.errno not in [errno.ECONNREFUSED, errno.ETIMEDOUT]:
                    check.record_failed(
                        "Connection to HTTP port failed for the unexpected reason",
                        details=f"Encountered socket error: {e}, while the expectation is to either run into a straight up connection refusal or a timeout.",
                    )

        self.end_test_step()
        self.end_test_case()

    def _case_https_works(self):
        parsed_url = urlparse(self._dss.base_url)
        hostname = parsed_url.hostname

        self.begin_test_case("Connect to HTTPS port")
        self.begin_test_step("Attempt GET on root path via HTTP test")

        if hostname is not None:
            with self.check(
                "Connection fails or response redirects to HTTPS endpoint",
                self._dss.participant_id,
            ) as check:
                try:
                    requests.get(
                        f"https://{hostname}/{parsed_url.path}",
                        timeout=10,
                        allow_redirects=False,
                    )
                    # We don't care about the response details, just that the connection was successful
                    # (a 404 would still indicate that HTTPS is working well)
                except requests.RequestException as e:
                    check.record_failed(
                        "Connection to HTTPS port failed",
                        details=f"Encountered exception while attempting HTTPS request: {e}",
                    )

        self.end_test_step()
        self.end_test_case()


def _check_is_redirect(parsed_url, check, response):
    # If we can connect, we want to check that we are being redirected:
    # (a 4XX response is already a form of communication that we don't want in cleartext)
    if response.status_code not in [301, 302, 307, 308]:
        check.record_failed(
            "Connection to HTTP port did not redirect",
            details=f"Was expecting a 301 or 308 response, but obtained status code: {response.status_code}",
        )
    if "Location" not in response.headers:
        check.record_failed(
            "Location header missing in redirect response",
            details="Was expecting a Location header in the response, but it was not present",
        )
    if response.headers.get("Location").startswith("http://"):
        check.record_failed(
            "Connection to HTTP port redirected to HTTP",
            details=f"Was expecting a redirection to an https:// URL. Location header: {response.headers.get('Location')}",
        )
    if not response.headers.get("Location").startswith(
        f"https://{parsed_url.hostname}/{parsed_url.path}"
    ):
        check.record_failed(
            "Redirect to unexpected destination",
            details=f"Was expecting a redirection to https://{parsed_url.hostname}/{parsed_url.path}, was {response.headers.get('Location')}",
        )
