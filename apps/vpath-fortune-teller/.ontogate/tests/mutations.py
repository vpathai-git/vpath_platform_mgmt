"""Deliberate breaks for the NEGATIVE stories / red drill. Each mutation is
applied to a SCRATCH COPY of the app repo (never the real read-only app); the
gate then asserts the story's pinned contract goes RED for its declared reason,
and the copy is discarded. A mutation that fails to apply is a hard error, never
a skip — a negative story that cannot break is a soft pass.
"""


def _globals_css(app):
    p = app / "src" / "app" / "globals.css"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    return p


def palette_literal_css(app):
    """C-tokens-only: inject a #ff0000 hex palette literal into globals.css."""
    p = _globals_css(app)
    p.write_text(
        p.read_text(encoding="utf-8") + "\n.injected { color: #ff0000; }\n",
        encoding="utf-8",
    )


def hand_jwt_verify(app):
    """C-auth-delegated: drop a hand jwt.verify into a new API route."""
    d = app / "src" / "app" / "api" / "rogue"
    d.mkdir(parents=True, exist_ok=True)
    (d / "route.ts").write_text(
        "import jwt from 'jsonwebtoken';\n"
        "export function GET(req: Request) {\n"
        "  const token = req.headers.get('authorization') ?? '';\n"
        "  const payload = jwt.verify(token, process.env.SECRET);\n"
        "  return Response.json(payload);\n"
        "}\n",
        encoding="utf-8",
    )


def override_generated_np(app):
    """C-no-override-generated-k8s: ship a hand networkpolicy.yaml carrying a
    generated name on the generated path (the silent same-name override)."""
    d = app / "kubernetes"
    d.mkdir(parents=True, exist_ok=True)
    (d / "networkpolicy.yaml").write_text(
        "apiVersion: networking.k8s.io/v1\n"
        "kind: NetworkPolicy\n"
        "metadata:\n"
        "  name: vpath-fortune-teller-allow-egress\n"
        "  namespace: vpath-fortune-teller\n"
        "spec:\n"
        "  podSelector: {}\n"
        "  policyTypes: [Egress]\n",
        encoding="utf-8",
    )


def local_navtabs(app):
    """C-zero-header: add a local NavTabs header component."""
    p = app / "src" / "components" / "NavTabs.tsx"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "export function NavTabs() {\n"
        '  return <nav className="tabs">app-local nav</nav>;\n'
        "}\n",
        encoding="utf-8",
    )


def soft_default_dns(app):
    """C-no-hardcoded-service-dns: a soft-default service-DNS fallback. The
    `||` line carries no process.env, so ONLY the DNS contract fires (not the
    broader config-fail-fast one)."""
    p = app / "src" / "app" / "rogue-endpoint.ts"
    p.write_text(
        "const base = process.env.NEO4J_URL;\n"
        'export const endpoint = base || "http://neo4j:7474";\n',
        encoding="utf-8",
    )


def delete_manifest(app):
    """C-fill-manifest: remove the one required FILL socket."""
    p = app / "vpath-app.yaml"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    p.unlink()


MUTATIONS = {
    "palette-literal-css": palette_literal_css,
    "hand-jwt-verify": hand_jwt_verify,
    "override-generated-np": override_generated_np,
    "local-navtabs": local_navtabs,
    "soft-default-dns": soft_default_dns,
    "delete-manifest": delete_manifest,
}
