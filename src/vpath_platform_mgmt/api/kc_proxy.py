"""Serve Keycloak through the console, for browsers with no route to it.

The console reaches Keycloak (over an overlay or a tunnel); the browser often
cannot. Since an authorization-code login *requires* the user agent to visit
the identity provider, a browser without that route can never sign in — no
amount of server-side token handling changes that.

So the console relays it: ``/keycloak/*`` is forwarded upstream, and absolute
URLs pointing at Keycloak's configured hostname are rewritten to point back
here. The browser then only ever talks to the console.

This deliberately does NOT touch Keycloak's own hostname configuration. That
setting fixes the ``iss`` claim of every token the platform issues; relaxing
it so URLs follow the request would make the issuer vary by access path and
break validation for every other app on the platform.

The relay carries an unauthenticated login flow, so it is narrow on purpose:
one upstream, fixed by configuration, and no request header from the caller
chooses where traffic goes.
"""

from __future__ import annotations

from urllib.parse import urlsplit

import httpx
from fastapi import FastAPI, Request, Response

PREFIX = "/keycloak"
TIMEOUT_SECONDS = 30.0
METHODS = ["GET", "POST", "PUT", "DELETE", "OPTIONS", "HEAD"]
# Hop-by-hop headers are per-connection and must not be relayed.
DROP_REQUEST = {"host", "content-length", "accept-encoding", "connection"}
DROP_RESPONSE = {
    "content-length",
    "content-encoding",
    "transfer-encoding",
    "connection",
    "keep-alive",
    # Upstream is HTTPS and says so; this origin may not be. Relaying HSTS
    # would tell the browser to force TLS on the console's own host.
    "strict-transport-security",
}
REWRITABLE = ("text/", "application/json", "application/javascript", "application/xml")


class KeycloakProxy:
    """Relays ``/keycloak/*`` upstream and rewrites URLs back to the console."""

    def __init__(
        self,
        upstream: str,
        public_base: str,
        verify_tls: bool = True,
        client: httpx.AsyncClient | None = None,
    ) -> None:
        if not upstream or not public_base:
            raise ValueError(
                "the Keycloak relay needs both an upstream URL and the public "
                "base it must rewrite (VPATH_MGMT_KC_PROXY_UPSTREAM / _PUBLIC)"
            )
        self._upstream = upstream.rstrip("/")
        self._public = public_base.rstrip("/")
        # Keycloak builds some URLs (notably token_endpoint) from the request
        # Host rather than its configured hostname. Presenting the public host
        # upstream keeps every URL it emits in the one form the rewrite knows;
        # otherwise those leak through as an unreachable host.
        self._public_host = urlsplit(self._public).netloc
        self._client = client or httpx.AsyncClient(
            verify=verify_tls, timeout=TIMEOUT_SECONDS, follow_redirects=False
        )

    def _local_base(self, request: Request) -> str:
        return str(request.base_url).rstrip("/") + PREFIX

    def rewrite(self, text: str, local_base: str) -> str:
        """Point Keycloak's absolute URLs back at the console."""
        return text.replace(self._public, local_base)

    @staticmethod
    def adapt_cookie(value: str, secure_origin: bool) -> str:
        """Make an upstream cookie storable on this origin.

        Keycloak sits behind TLS and marks its session cookies ``Secure``.
        Served over plain HTTP the browser silently discards them, so the
        login session never sticks and every visit asks for a password
        again. ``SameSite=None`` goes the same way — browsers require
        ``Secure`` with it — and since the relay makes the whole flow
        same-origin, ``Lax`` is the accurate replacement.
        """
        if secure_origin:
            return value
        kept = [part for part in value.split(";") if part.strip().lower() != "secure"]
        rejoined = ";".join(kept)
        return rejoined.replace("SameSite=None", "SameSite=Lax")

    async def handle(self, request: Request, path: str) -> Response:
        """Forward one request upstream and relay the rewritten response."""
        url = f"{self._upstream}/{path}"
        headers = {
            key: value
            for key, value in request.headers.items()
            if key.lower() not in DROP_REQUEST
        }
        headers["host"] = self._public_host
        upstream = await self._client.request(
            request.method,
            url,
            params=dict(request.query_params),
            headers=headers,
            content=await request.body(),
        )
        return self._relay(
            upstream, self._local_base(request), request.url.scheme == "https"
        )

    def _relay(
        self, upstream: httpx.Response, local_base: str, secure_origin: bool
    ) -> Response:
        plain: dict[str, str] = {}
        cookies: list[str] = []
        for key, value in upstream.headers.multi_items():
            if key.lower() in DROP_RESPONSE:
                continue
            rewritten = self.rewrite(value, local_base)
            if key.lower() == "set-cookie":
                # Keycloak sets several cookies per response; a dict would
                # keep only the last one and the login would half-work.
                cookies.append(self.adapt_cookie(rewritten, secure_origin))
            else:
                plain[key] = rewritten
        content_type = upstream.headers.get("content-type", "")
        if any(kind in content_type for kind in REWRITABLE):
            body = self.rewrite(upstream.text, local_base).encode("utf-8")
        else:
            body = upstream.content
        response = Response(
            content=body, status_code=upstream.status_code, headers=plain
        )
        for cookie in cookies:
            response.raw_headers.append((b"set-cookie", cookie.encode("latin-1")))
        return response


def register(app: FastAPI, proxy: KeycloakProxy) -> None:
    """Mount the relay ahead of the console's catch-all asset route."""

    @app.api_route(f"{PREFIX}/{{path:path}}", methods=METHODS, include_in_schema=False)
    async def keycloak(request: Request, path: str) -> Response:
        """Relay one Keycloak request; the browser never leaves this origin."""
        return await proxy.handle(request, path)
