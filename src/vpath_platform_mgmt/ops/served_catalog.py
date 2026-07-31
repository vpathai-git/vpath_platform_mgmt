"""What the platform's sidebar actually offers, and where it disagrees.

The catalog a user sees is not the manifests on disk. A manifest is compiled
into the ``app-catalog`` ConfigMap and mounted into ``vpath-web`` with
``subPath``, which Kubernetes never refreshes in a running pod, so three copies
exist and any two can disagree. Worse, ``/api/version`` never moves for a
manifest-only change -- it is not code and never lands in a build id -- so the
usual "is it deployed?" check answers the wrong question. This reads the end of
that chain: the JSON a browser is actually served.

What it does NOT claim
----------------------
Manifests the console can see and entries the platform serves are not the same
population by design: this repo carries demo apps, while the server checkout
carries the platform's own. Only apps present in *both* are compared; the rest
are counted and named as such, never reported as drift. A count of "apps the
platform serves that we cannot see" is a fact about this console's reach, not
a problem with the platform.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any

import httpx

from vpath_platform_mgmt.ops.apps import AppEntry

CATALOG_PATH = "/app-catalog.json"
TIMEOUT_SECONDS = 5.0
CACHE_TTL_SECONDS = 30.0


class ServedCatalogError(Exception):
    """The platform's catalog could not be read."""


@dataclass(frozen=True)
class ServedEntry:
    """One entry exactly as the platform hands it to a browser."""

    name: str
    label: str


def parse(payload: Any) -> list[ServedEntry]:
    """Read the platform's catalog JSON, refusing anything unexpected."""
    if not isinstance(payload, list):
        raise ServedCatalogError("the platform's catalog is not a JSON list")
    entries: list[ServedEntry] = []
    for item in payload:
        if not isinstance(item, dict):
            raise ServedCatalogError("a catalog entry is not an object")
        name, label = item.get("name"), item.get("label")
        if not isinstance(name, str) or not isinstance(label, str):
            raise ServedCatalogError("a catalog entry lacks a string name/label")
        entries.append(ServedEntry(name=name, label=label))
    return entries


def compare(
    manifests: Sequence[AppEntry], served: Sequence[ServedEntry]
) -> dict[str, object]:
    """Compare only what is comparable, and name the rest for what it is."""
    served_by_name = {entry.name: entry for entry in served}
    shared = 0
    mismatches: list[dict[str, str]] = []
    for manifest in manifests:
        entry = served_by_name.get(manifest.name)
        if entry is None:
            continue
        shared += 1
        if entry.label != manifest.title:
            mismatches.append(
                {
                    "name": manifest.name,
                    "here": manifest.title,
                    "platform": entry.label,
                }
            )
    return {
        "served_total": len(served),
        "shared": shared,
        "only_here": len(manifests) - shared,
        "only_on_platform": len(served) - shared,
        "label_mismatches": mismatches,
    }


class ServedCatalogReader:
    """Reads the platform's catalog, cached so a page poll cannot hammer it."""

    def __init__(
        self,
        platform_url: str,
        verify_tls: bool = True,
        client: httpx.Client | None = None,
        now: object = time.monotonic,
    ) -> None:
        self._url = platform_url.rstrip("/") + CATALOG_PATH
        self._client = client or httpx.Client(
            verify=verify_tls, timeout=TIMEOUT_SECONDS
        )
        self._now = now
        self._cached: list[ServedEntry] | None = None
        self._cached_at = 0.0

    def entries(self) -> list[ServedEntry]:
        """The served catalog, from cache when it is still fresh."""
        clock = self._now
        stamp = clock() if callable(clock) else 0.0
        if self._cached is not None and stamp - self._cached_at < CACHE_TTL_SECONDS:
            return self._cached
        try:
            response = self._client.get(self._url)
        except httpx.HTTPError as exc:
            raise ServedCatalogError(f"the platform did not answer: {exc}") from exc
        if response.status_code != 200:
            raise ServedCatalogError(
                f"the platform answered {response.status_code} for its catalog"
            )
        entries = parse(response.json())
        self._cached, self._cached_at = entries, stamp
        return entries
