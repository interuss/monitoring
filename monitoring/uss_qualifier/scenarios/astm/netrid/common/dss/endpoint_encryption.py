import errno
import socket
from urllib.parse import urlparse

import requests
import uas_standards.astm.f3411.v19.api
import uas_standards.astm.f3411.v22a.api
from uas_standards.astm.f3411 import v19, v22a

from monitoring.monitorlib.rid import RIDVersion
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
    ):
        super().__init__()
        self._dss = dss.dss_instance

        if self._dss.rid_version == RIDVersion.f3411_19:
            op = v19.api.OPERATIONS[v19.api.OperationID.GetIdentificationServiceArea]
        elif self._dss.rid_version == RIDVersion.f3411_22a:
            op = v22a.api.OPERATIONS[v22a.api.OperationID.GetIdentificationServiceArea]
        else:
            raise NotImplementedError(
                f"Scenario does not support RID version {self._dss.rid_version}"
            )

        non_existing_id = "00000000-0000-0000-0000-000000000000"
        http_base_url = urlparse(self._dss.base_url)._replace(scheme="http")
        self._http_get_url = f"{http_base_url.geturl()}{op.path}".replace(
            "{id}", non_existing_id
        )
        self._https_get_url = f"{self._dss.base_url}{op.path}".replace(
            "{id}", non_existing_id
        )

    def run(self, context: ExecutionContext):
        self.begin_test_scenario(context)

        if not self._dss.base_url.startswith("https://"):
            self.record_note(
                "encrypted_endpoints",
                "Cannot check encryption requirement when DSS endpoint is specified with an http:// base URL",
            )
            self.end_test_scenario()
            return

        self.begin_test_case("Validate endpoint encryption")
        self._step_http_unavailable_or_redirect()
        self._step_https_works()
        self.end_test_case()

        self.end_test_scenario()

    def _step_http_unavailable_or_redirect(self):
        self.begin_test_step("Attempt GET on a known valid path via HTTP")

        with self.check(
            "HTTP GET fails or redirects to HTTPS",
            self._dss.participant_id,
        ) as check:
            try:
                response = requests.get(
                    self._http_get_url,
                    timeout=10,
                )
                if not response.url.startswith("https://"):
                    # response.url contains the url of the final request after all redirects have been followed, if any
                    check.record_failed(
                        "HTTP GET request did not redirect to HTTPS",
                        details=f"Made an http GET request and obtained status code {response.status_code} with response {str(response.content)} that was not redirected to https",
                    )

            except socket.error as e:
                if e.errno not in [errno.ECONNREFUSED, errno.ETIMEDOUT]:
                    check.record_failed(
                        "Connection to HTTP port failed for an unexpected reason",
                        details=f"Encountered socket error: {e}, while the expectation is to either run into a straight up connection refusal or a timeout.",
                    )

        self.end_test_step()

    def _step_https_works(self):
        self.begin_test_step("Attempt GET on a known valid path via HTTPS")

        with self.check(
            "HTTPS GET succeeds",
            self._dss.participant_id,
        ) as check:
            try:
                response = requests.get(
                    self._https_get_url,
                    timeout=10,
                )
                if not response.url.startswith("https://"):
                    # response.url contains the url of the final request after all redirects have been followed, if any
                    check.record_failed(
                        "HTTPS GET request redirected to HTTP",
                        details=f"Made an https GET request and obtained status code {response.status_code} with response {str(response.content)} that was redirected to http",
                    )
            except requests.RequestException as e:
                check.record_failed(
                    "Connection to HTTPS port failed",
                    details=f"Encountered exception while attempting HTTPS request: {e}",
                )

        self.end_test_step()
