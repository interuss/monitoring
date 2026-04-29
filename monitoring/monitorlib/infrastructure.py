from __future__ import annotations

import asyncio
import datetime
import functools
import threading
import time
import urllib.parse
import weakref
from enum import Enum

import jwt
import requests
from aiohttp import ClientSession
from loguru import logger

ALL_SCOPES = [
    "utm.strategic_coordination",
]

EPOCH = datetime.datetime.fromtimestamp(0, datetime.UTC)
TOKEN_REFRESH_MARGIN = datetime.timedelta(seconds=15)
CLIENT_TIMEOUT = 10  # seconds
SOCKET_KEEP_ALIVE_LIMIT = 57  # seconds.


AuthSpec = str
"""Specification for means by which to obtain access tokens."""


class AuthAdapter:
    """Base class for an adapter that add JWTs to requests."""

    def __init__(self):
        self._tokens = {}

    def issue_token(self, intended_audience: str, scopes: list[str]) -> str:
        """Subclasses must return a bearer token for the given audience."""

        raise NotImplementedError()

    def get_headers(self, url: str, scopes: list[str] | None = None) -> dict[str, str]:
        if scopes is None:
            scopes = ALL_SCOPES
        scopes = [s.value if isinstance(s, Enum) else s for s in scopes]
        intended_audience = urllib.parse.urlparse(url).hostname

        if not intended_audience:
            return {}

        scope_string = " ".join(scopes)
        if intended_audience not in self._tokens:
            self._tokens[intended_audience] = {}
        if scope_string not in self._tokens[intended_audience]:
            token = self.issue_token(intended_audience, scopes)
        else:
            token = self._tokens[intended_audience][scope_string]
        payload = jwt.decode(token, options={"verify_signature": False})
        expires = EPOCH + datetime.timedelta(seconds=payload["exp"])
        if datetime.datetime.now(datetime.UTC) > expires - TOKEN_REFRESH_MARGIN:
            token = self.issue_token(intended_audience, scopes)
        self._tokens[intended_audience][scope_string] = token
        return {"Authorization": "Bearer " + token}

    def add_headers(self, request: requests.PreparedRequest, scopes: list[str]):
        if request.url:
            for k, v in self.get_headers(request.url, scopes).items():
                request.headers[k] = v

    def get_sub(self) -> str | None:
        """Retrieve `sub` claim from one of the existing tokens"""
        for _, tokens_by_scope in self._tokens.items():
            for token in tokens_by_scope.values():
                payload = jwt.decode(token, options={"verify_signature": False})
                if "sub" in payload:
                    return payload["sub"]
        return None


class UTMClientSession(requests.Session):
    """Requests session that enables easy access to ASTM-specified UTM endpoints.

    Automatically applies authorization according to the `auth_adapter` specified
    at construction, when present.

    If the URL starts with '/', then automatically prefix the URL with the
    `prefix_url` specified on construction (this is usually the base URL of the
    DSS).

    When possible, a UTMClientSession should be reused rather than creating a
    new one because an excessive number of UTMClientSessions can exhaust the
    number of connections allowed by the system (see #1407).
    """

    _next_session_id: int = 1
    _session_id: int
    _session_id_lock = threading.Lock()

    _closure_timer: threading.Timer | None = None
    _closure_lock: threading.Lock
    _last_used: float | None = None

    def __init__(
        self,
        prefix_url: str,
        auth_adapter: AuthAdapter | None = None,
        timeout_seconds: float | None = None,
    ):
        super().__init__()

        with UTMClientSession._session_id_lock:
            self._session_id = UTMClientSession._next_session_id
            UTMClientSession._next_session_id += 1

        self._prefix_url = prefix_url[0:-1] if prefix_url[-1] == "/" else prefix_url
        self.auth_adapter = auth_adapter
        self.default_scopes: list[str] | None = None
        self.timeout_seconds = timeout_seconds or CLIENT_TIMEOUT
        self._closure_lock = threading.Lock()

        UTMClientSession._start_closure_timer(weakref.ref(self))

    @staticmethod
    def _start_closure_timer(wref: weakref.ReferenceType[UTMClientSession]) -> None:
        def wrapper():
            weak_self_final = wref()
            if weak_self_final is not None:
                try:
                    weak_self_final.close_if_idle()
                finally:
                    UTMClientSession._start_closure_timer(wref)

        weak_self_initial = wref()
        if weak_self_initial:
            weak_self_initial._closure_timer = threading.Timer(
                weak_self_initial.seconds_until_idle(), wrapper
            )
            weak_self_initial._closure_timer.daemon = True
            weak_self_initial._closure_timer.start()

    def close_if_idle(self) -> None:
        with self._closure_lock:
            if (
                self._last_used
                and time.monotonic() - self._last_used > SOCKET_KEEP_ALIVE_LIMIT
            ):
                logger.debug(
                    "Closing idle UTMClientSession {} to {} with default scopes {} last used {} (now {})",
                    self._session_id,
                    self._prefix_url,
                    ", ".join(self.default_scopes) if self.default_scopes else "<none>",
                    self._last_used,
                    time.monotonic(),
                )
                self.close()
                self._last_used = None

    def seconds_until_idle(self) -> float:
        if self._last_used is None:
            return SOCKET_KEEP_ALIVE_LIMIT
        else:
            return max(
                0.0, SOCKET_KEEP_ALIVE_LIMIT - (time.monotonic() - self._last_used)
            )

    def __del__(self):
        if timer := self._closure_timer:
            timer.cancel()

    # Overrides method on requests.Session
    def prepare_request(self, request, **kwargs):
        # Automatically prefix any unprefixed URLs
        if request.url.startswith("/"):
            request.url = self._prefix_url + request.url

        return super().prepare_request(request, **kwargs)

    def adjust_request_kwargs(self, kwargs):
        if self.auth_adapter:
            scopes = None
            if "scopes" in kwargs:
                scopes = kwargs["scopes"]
                del kwargs["scopes"]
            if "scope" in kwargs:
                scopes = [kwargs["scope"]]
                del kwargs["scope"]
            if scopes is None:
                scopes = self.default_scopes

            def auth(
                prepared_request: requests.PreparedRequest,
            ) -> requests.PreparedRequest:
                if scopes and self.auth_adapter:
                    self.auth_adapter.add_headers(prepared_request, scopes)
                return prepared_request

            kwargs["auth"] = auth
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout_seconds
        return kwargs

    def request(self, method, url, *args, **kwargs):
        if "auth" not in kwargs:
            kwargs = self.adjust_request_kwargs(kwargs)

        with self._closure_lock:
            result = super().request(method, url, *args, **kwargs)
            self._last_used = time.monotonic()
            return result

    def get_prefix_url(self):
        return self._prefix_url

    def get(self, *args, **kwargs):
        return super().get(*args, **kwargs)

    def delete(self, *args, **kwargs):
        return super().delete(*args, **kwargs)


class AsyncUTMTestSession:
    """
    Requests Asyncio client session that provides additional functionality for running DSS concurrency tests:
      * Adds a prefix to URLs that start with a '/'.
      * Automatically applies authorization according to adapter, when present
    """

    def __init__(
        self,
        prefix_url: str,
        auth_adapter: AuthAdapter | None = None,
        timeout_seconds: float | None = None,
    ):
        self._client = None
        loop = asyncio.get_event_loop()
        loop.run_until_complete(self.build_session())

        self._prefix_url = prefix_url[0:-1] if prefix_url[-1] == "/" else prefix_url
        self.auth_adapter = auth_adapter
        self.default_scopes: list[str] | None = None
        self.timeout_seconds = timeout_seconds or CLIENT_TIMEOUT

    async def build_session(self):
        self._client = ClientSession()

    def close(self):
        if self._client:
            loop = asyncio.get_event_loop()
            loop.run_until_complete(self._client.close())

    def adjust_request_kwargs(self, url, method, kwargs):
        if self.auth_adapter:
            scopes = None
            if "scopes" in kwargs:
                scopes = kwargs["scopes"]
                del kwargs["scopes"]
            if "scope" in kwargs:
                scopes = [kwargs["scope"]]
                del kwargs["scope"]
            if scopes is None:
                scopes = self.default_scopes
            if not scopes:
                raise ValueError(
                    "All tests must specify auth scope for all session requests.  Either specify as an argument for each individual HTTP call, or decorate the test with @default_scope."
                )
            headers = {}
            for k, v in self.auth_adapter.get_headers(url, scopes).items():
                headers[k] = v
            kwargs["headers"] = headers
            if method == "PUT" and kwargs.get("data"):
                kwargs["json"] = kwargs["data"]
                del kwargs["data"]
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout_seconds
        return kwargs

    async def put(self, url, **kwargs):
        """Returns (status, headers, json)"""
        url = self._prefix_url + url
        if "auth" not in kwargs:
            kwargs = self.adjust_request_kwargs(url, "PUT", kwargs)

        if not self._client:
            raise ValueError("Client is not ready")

        async with self._client.put(url, **kwargs) as response:
            return (
                response.status,
                {k: v for k, v in response.headers.items()},
                await response.json(),
            )

    async def get(self, url, **kwargs):
        """Returns (status, headers, json)"""
        url = self._prefix_url + url
        if "auth" not in kwargs:
            kwargs = self.adjust_request_kwargs(url, "GET", kwargs)

        if not self._client:
            raise ValueError("Client is not ready")

        async with self._client.get(url, **kwargs) as response:
            return (
                response.status,
                {k: v for k, v in response.headers.items()},
                await response.json(),
            )

    async def post(self, url, **kwargs):
        """Returns (status, headers, json)"""
        url = self._prefix_url + url
        if "auth" not in kwargs:
            kwargs = self.adjust_request_kwargs(url, "POST", kwargs)

        if not self._client:
            raise ValueError("Client is not ready")

        async with self._client.post(url, **kwargs) as response:
            return (
                response.status,
                {k: v for k, v in response.headers.items()},
                await response.json(),
            )

    async def delete(self, url, **kwargs):
        """Returns (status, headers, json)"""
        url = self._prefix_url + url
        if "auth" not in kwargs:
            kwargs = self.adjust_request_kwargs(url, "DELETE", kwargs)

        if not self._client:
            raise ValueError("Client is not ready")

        async with self._client.delete(url, **kwargs) as response:
            return (
                response.status,
                {k: v for k, v in response.headers.items()},
                await response.json(),
            )


def default_scopes(scopes: list[str]):
    """Decorator for tests that modifies UTMClientSession args to use scopes.

    A test function decorated with this decorator will modify all arguments which
    are UTMClientSessions to set their default_scopes to the scopes specified in
    this decorator (and restore the original default_scopes afterward).

    :param scopes: List of scopes to retrieve (by default) for tokens used to
      authorize requests sent using any of the UTMClientSession arguments to the
      decorated test.
    """

    def decorator_default_scope(func):
        @functools.wraps(func)
        def wrapper_default_scope(*args, **kwargs):
            # Change <UTMClientSession>.default_scopes to scopes for all UTMClientSession arguments
            old_scopes = []
            for arg in args:
                if isinstance(arg, UTMClientSession) or isinstance(
                    arg, AsyncUTMTestSession
                ):
                    old_scopes.append(arg.default_scopes)
                    arg.default_scopes = scopes
            for k, v in kwargs.items():
                if isinstance(v, UTMClientSession) or isinstance(
                    v, AsyncUTMTestSession
                ):
                    old_scopes.append(v.default_scopes)
                    v.default_scopes = scopes

            result = func(*args, **kwargs)

            # Restore original values of <UTMClientSession>.default_scopes for all UTMClientSession arguments
            for arg in args:
                if isinstance(arg, UTMClientSession) or isinstance(
                    arg, AsyncUTMTestSession
                ):
                    arg.default_scopes = old_scopes[0]
                    old_scopes = old_scopes[1:]
            for k, v in kwargs.items():
                if isinstance(v, UTMClientSession) or isinstance(
                    v, AsyncUTMTestSession
                ):
                    v.default_scopes = old_scopes[0]
                    old_scopes = old_scopes[1:]

            return result

        return wrapper_default_scope

    return decorator_default_scope


def default_scope(scope: str):
    """Decorator for tests that modifies UTMClientSession args to use a scope.

    A test function decorated with this decorator will modify all arguments which
    are UTMClientSessions to set their default_scopes to the scope specified in
    this decorator (and restore the original default_scopes afterward).

    :param scopes: Single scope to retrieve (by default) for tokens used to
      authorize requests sent using any of the UTMClientSession arguments to the
      decorated test.
    """
    return default_scopes([scope])


def get_token_claims(headers: dict) -> dict:
    auth_key = [key for key in headers if key.lower() == "authorization"]
    if len(auth_key) == 0:
        return {"error": "Missing Authorization header"}
    if len(auth_key) > 1:
        return {"error": "Multiple Authorization headers: " + ", ".join(auth_key)}
    token: str = headers[auth_key[0]]
    if token.lower().startswith("bearer "):
        token = token[len("bearer ") :]
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except ValueError as e:
        return {"error": "ValueError: " + str(e)}
    except jwt.exceptions.DecodeError as e:
        return {"error": "DecodeError: " + str(e)}


class KMLGenerationSession(requests.Session):
    """
    Requests session that provides additional functionality for generating KMLs:
      * Adds a prefix to URLs that start with a '/'.
    """

    def __init__(self, prefix_url: str, kml_folder: str):
        super().__init__()

        self._prefix_url = prefix_url[0:-1] if prefix_url[-1] == "/" else prefix_url
        self.kml_folder = kml_folder

    # Overrides method on requests.Session
    def prepare_request(self, request, **kwargs):
        # Automatically prefix any unprefixed URLs
        if request.url.startswith("/"):
            request.url = self._prefix_url + request.url

        return super().prepare_request(request, **kwargs)
