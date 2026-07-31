"""Builders that assemble one collaborator each from environment config.

Split out of ``server.py`` along the seam between "how a running console is
put together" (this module) and "the entry point that wires the pieces into
one service and serves it" (``server.py``), to keep each module under the
project's line limit. See ``server.py``'s module docstring for the full
environment-variable contract; the ``require``-based builders fail hard on
missing configuration, while the three that return ``None`` do so to report a
capability this console does not have, which the caller then refuses.
"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from vpath_platform_mgmt.cli.app_cmds import _place_registered_files
from vpath_platform_mgmt.ops import repo_probe, repo_tarball
from vpath_platform_mgmt.ops.app_preflight import require_publishable
from vpath_platform_mgmt.ops.app_registry import AppRegistry, detect_runtime
from vpath_platform_mgmt.ops.argocd import ArgoClient
from vpath_platform_mgmt.ops.bundle import bundle
from vpath_platform_mgmt.ops.engine import EngineAdapter, LocalEngine, SimulatedEngine
from vpath_platform_mgmt.ops.gitea import GiteaClient
from vpath_platform_mgmt.ops.gitops_engine import GitOpsEngine
from vpath_platform_mgmt.ops.apps import AppCatalog
from vpath_platform_mgmt.ops.publish import PublishPipeline
from vpath_platform_mgmt.ops.served_catalog import ServedCatalogReader
from vpath_platform_mgmt.ops.source import SourceMaterializer
from vpath_platform_mgmt.ops.tunnel import TunnelConfig, TunnelError
from vpath_platform_mgmt.ops.tunnel import from_env as tunnel_from_env

ENGINE_MODES = ("simulated", "local", "gitops")
SIMULATED_STEP_DELAY = 0.8
TRUTHY = ("1", "true", "yes")
GITEA_OWNER = "platform"
GITEA_REPO = "k8s-manifests"


def require(env: Mapping[str, str], key: str, mode: str) -> str:
    """Read a mandatory setting, naming the mode that made it mandatory."""
    value = env.get(key, "")
    if not value:
        raise ValueError(f"engine mode '{mode}' requires {key}")
    return value


GITOPS_KEYS = (
    "VPATH_MGMT_GITEA_URL",
    "VPATH_MGMT_GITEA_TOKEN",
    "VPATH_MGMT_K8S_URL",
    "VPATH_MGMT_K8S_TOKEN",
)


def missing_gitops_keys(env: Mapping[str, str]) -> list[str]:
    """Settings ``build_gitops_engine`` requires and this environment lacks.

    Asking before building is what lets an optional GitOps consumer decline
    instead of aborting startup with a ``ValueError``. A test asserts every
    key here is genuinely required, so the two cannot drift apart.
    """
    return [key for key in GITOPS_KEYS if not env.get(key, "")]


def build_gitops_engine(env: Mapping[str, str]) -> GitOpsEngine:
    """Gitea + Kubernetes clients for the API-only deploy path.

    Both endpoints sit inside the platform's private network, so this engine
    is only usable where that network is reachable (on the server, or through
    the operator's tunnel). ``VPATH_MGMT_INSECURE_TLS`` exists for the
    self-signed dev platform and must be set deliberately.
    """
    insecure = env.get("VPATH_MGMT_INSECURE_TLS", "").lower() in TRUTHY
    gitea = GiteaClient(
        base_url=require(env, "VPATH_MGMT_GITEA_URL", "gitops"),
        owner=env.get("VPATH_MGMT_GITEA_OWNER") or GITEA_OWNER,
        repo=env.get("VPATH_MGMT_GITEA_REPO") or GITEA_REPO,
        token=require(env, "VPATH_MGMT_GITEA_TOKEN", "gitops"),
        branch=env.get("VPATH_MGMT_GITEA_BRANCH") or "main",
        verify_tls=not insecure,
    )
    argo = ArgoClient(
        base_url=require(env, "VPATH_MGMT_K8S_URL", "gitops"),
        token=require(env, "VPATH_MGMT_K8S_TOKEN", "gitops"),
        verify_tls=not insecure,
    )
    return GitOpsEngine(gitea, argo)


def build_engine(env: Mapping[str, str]) -> EngineAdapter:
    """Choose the engine adapter from env; fail hard on bad config."""
    mode = env.get("VPATH_MGMT_ENGINE", "simulated")
    if mode not in ENGINE_MODES:
        raise ValueError(
            f"unknown engine mode '{mode}' (expected one of {ENGINE_MODES})"
        )
    if mode == "gitops":
        return build_gitops_engine(env)
    if mode == "local":
        checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
        if not checkout:
            raise ValueError("engine mode 'local' requires VPATH_MGMT_SERVER_CHECKOUT")
        return LocalEngine(Path(checkout), extra_env=parse_engine_env(env))
    return SimulatedEngine(step_delay=SIMULATED_STEP_DELAY)


def repo_root() -> Path:
    """Where instance profiles live — the checkout this package runs from."""
    return Path(__file__).resolve().parents[3]


def resolve_instance_name(env: Mapping[str, str], engine_name: str) -> str:
    """Which declared instance this console drives (register name, e.g. vm5).

    Real engines must be told — silently guessing which box a console talks
    to is the most expensive mistake this tooling can make. The simulated
    engine has no box, so it gets a truthful default.
    """
    name = env.get("VPATH_MGMT_INSTANCE", "")
    if name:
        return name
    if engine_name == "simulated":
        return "sim"
    raise ValueError(
        f"engine mode '{engine_name}' requires VPATH_MGMT_INSTANCE — name "
        "the instance this console drives (see instances.local.env)"
    )


def parse_engine_env(env: Mapping[str, str]) -> dict[str, str]:
    """Parse ``VPATH_MGMT_ENGINE_ENV`` ("K=V,K2=V2") for the engine subprocess.

    The pipeline reads its topology from the environment (e.g.
    ``VPATH_INSTALL_MODE=nuc`` on a single-box target). Malformed entries
    fail hard rather than being skipped.
    """
    raw = env.get("VPATH_MGMT_ENGINE_ENV", "").strip()
    if not raw:
        return {}
    pairs: dict[str, str] = {}
    for item in raw.split(","):
        entry = item.strip()
        if not entry:
            continue
        if "=" not in entry:
            raise ValueError(f"VPATH_MGMT_ENGINE_ENV entry '{entry}' is not KEY=VALUE")
        key, value = entry.split("=", 1)
        if not key.strip():
            raise ValueError("VPATH_MGMT_ENGINE_ENV has an entry with an empty key")
        pairs[key.strip()] = value.strip()
    return pairs


def build_tunnel_config(env: Mapping[str, str]) -> TunnelConfig | None:
    """The instance's tunnel, or ``None`` when it declares none.

    Absent is a legitimate answer — a console running on the box needs no
    tunnel — so this returns None rather than raising. Asking to *start* an
    absent tunnel is what fails, and it says why.
    """
    try:
        return tunnel_from_env(env)
    except TunnelError:
        return None


def build_catalog_root(env: Mapping[str, str]) -> Path:
    """This repository's ``apps/`` folder, which the registry owns."""
    return Path(env.get("VPATH_MGMT_APPS_DIR", "") or (repo_root() / "apps"))


def build_catalog(env: Mapping[str, str]) -> AppCatalog:
    """Catalog over this repo's ``apps/`` plus the server checkout, if any.

    ``VPATH_MGMT_APPS_DIR`` overrides the repo folder. Both sources use the
    same ``<dir>/<app>/vpath-app.yaml`` layout; repo apps win on name clash.
    """
    directories = [build_catalog_root(env)]
    checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
    if checkout:
        directories.append(Path(checkout) / "apps_infra" / "apps")
    return AppCatalog(*directories)


def build_served_catalog(env: Mapping[str, str]) -> ServedCatalogReader | None:
    """Reader for the platform's own catalog, when we know where it lives."""
    platform_url = env.get("VPATH_MGMT_PLATFORM_URL", "")
    if not platform_url:
        return None
    insecure = env.get("VPATH_MGMT_INSECURE_TLS", "").lower() in TRUTHY
    return ServedCatalogReader(platform_url, verify_tls=not insecure)


def build_publish_pipeline(env: Mapping[str, str]) -> PublishPipeline | None:
    """The pipeline, or None when this console cannot serve publish.

    Publish spans both engines: rendering needs the checkout on this host and
    installing needs the Deploy-of-Record. A console with only one of them
    cannot do it, and says so at the verb rather than half way through.

    The gate asks for every setting the GitOps engine needs, not just the
    Gitea URL: a console that starts today with a checkout and a Gitea URL
    but no Kubernetes token must keep starting, publish declined at the verb.
    """
    checkout = env.get("VPATH_MGMT_SERVER_CHECKOUT", "")
    if not checkout or missing_gitops_keys(env):
        return None
    apps_root = build_catalog_root(env)

    def place(name: str, tree: Path) -> None:
        """Send stage lookup, bound to the same apps root as the registry."""
        _place_registered_files(name, tree, apps_root)

    return PublishPipeline(
        registry=AppRegistry(apps_root),
        materializer=SourceMaterializer(Path(checkout)),
        local_engine=LocalEngine(Path(checkout), extra_env=parse_engine_env(env)),
        gitops_engine=build_gitops_engine(env),
        probe=repo_probe.probe,
        materialise=repo_probe.materialise,
        download=repo_tarball.download_tree,
        bundle=bundle,
        place=place,
        inspect=require_publishable,
        runtime_of=detect_runtime,
    )
