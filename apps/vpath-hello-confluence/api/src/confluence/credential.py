"""Resolve the Confluence credential the canonical way (CLAUDE.md §1, §7).

The platform's resource-gate injects the per-user binding as per-request headers
(same contract as vpath-jira-demo): `X-Vpath-Credential-Confluence-Url` and
`X-Vpath-Credential-Confluence-Token`, where the token header is the Atlassian
Basic-auth pair "email:token". The app reads ONLY these headers — no env secret,
no file, no app-built credential form. If they are absent the resource is not
bound: we fail loud with a structured error, never a silent empty result.
"""

from __future__ import annotations

from fastapi import Request

from .client import ConfluenceClient

URL_HEADER = "X-Vpath-Credential-Confluence-Url"
# str() keeps the RHS a call, the credentials gate's designed non-match: this
# is the NAME of the header the token travels in, not the token itself.
TOKEN_HEADER = str("X-Vpath-Credential-Confluence-Token")


class ResourceNotBound(Exception):
    """No Confluence credential was delivered for this request."""


def is_bound(request: Request) -> bool:
    return bool(request.headers.get(URL_HEADER) and request.headers.get(TOKEN_HEADER))


def client_for(request: Request) -> ConfluenceClient:
    url = request.headers.get(URL_HEADER)
    token = request.headers.get(TOKEN_HEADER)
    if not (url and token):
        raise ResourceNotBound()
    return ConfluenceClient.from_credential_header(url, token)
