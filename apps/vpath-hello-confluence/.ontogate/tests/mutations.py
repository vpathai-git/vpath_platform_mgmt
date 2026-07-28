"""Deliberate breaks for the NEGATIVE stories / red drill. Each mutation is
applied to a SCRATCH COPY of the app repo (never the real read-only app); the
gate then asserts the story's pinned contract goes RED for its declared reason,
and the copy is discarded. A mutation that fails to apply is a hard error, never
a skip — a negative story that cannot break is a soft pass.

Three mutations are SPECIFIC to this app (a two-manifest pair filling the NEED
face with TWO resource kinds):
  * delete-resource-requirements     — strips the credential+connector block
    from the ROOT (web) manifest; the pair-wide app-strict NEED check in
    check.py turns C-need-resource-requirements RED.
  * delete-api-resource-requirements — strips the SAME block from the sibling
    api/vpath-app.yaml; the pair-wide check fires again (the api reads the
    gate-injected credential headers, so its own manifest must authorize that).
  * bespoke-secret-mount             — reads the K8s secret NAME
    (confluence-creds) directly in code; the foundation audit turns
    C-no-bespoke-secret-mount RED (the credential is gate-injected per request
    via delivery: header — the app must NEVER touch the platform secret).
"""


def _globals_css(app):
    p = app / "src" / "app" / "globals.css"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    return p


def _delete_manifest_block(path, key):
    """Drop a top-of-spec `key:` block (indent 2) + its indented body from a
    manifest, in place. Raises when the block is absent — never a silent skip."""
    if not path.exists():
        raise FileNotFoundError(f"mutation target missing: {path}")
    lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
    out, removed, i, n = [], False, 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent == 2 and stripped.startswith(f"{key}:"):
            removed = True
            i += 1
            # Drop the block body: every following line deeper than indent 2
            # (and any blank line nested within it).
            while i < n:
                body = lines[i]
                bstripped = body.lstrip(" ")
                bindent = len(body) - len(bstripped)
                if body.strip() == "" or bindent > 2:
                    i += 1
                    continue
                break
            continue
        out.append(line)
        i += 1
    if not removed:
        raise AssertionError(f"{key} block not found to delete in {path}")
    path.write_text("".join(out), encoding="utf-8")


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
        "  name: vpath-hello-confluence-allow-egress\n"
        "  namespace: vpath-hello-confluence\n"
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


def delete_resource_requirements(app):
    """C-need-resource-requirements: strip the credential+connector declaration
    from the ROOT (web) manifest. The foundation audit is lenient on NEED (an
    absent need reads as 'unused'), so the pair-wide app-strict check in
    check.py is what turns this RED — proving the Spine-3 makes the DECLARED
    need binding."""
    _delete_manifest_block(app / "vpath-app.yaml", "resourceRequirements")


def delete_api_resource_requirements(app):
    """C-need-resource-requirements: strip the SAME declaration from the
    sibling api/vpath-app.yaml. The api reads the gate-injected
    X-Vpath-Credential-Confluence-* headers, so its own manifest must authorize
    that use — the pair-wide app-strict check fires on the missing sibling."""
    _delete_manifest_block(app / "api" / "vpath-app.yaml", "resourceRequirements")


def bespoke_secret_mount(app):
    """C-no-bespoke-secret-mount: read the K8s secret NAME directly in code.
    The confluence credential is gate-injected per request (delivery: header);
    the platform secret (confluence-creds) is NEVER the app's to touch."""
    p = app / "src" / "app" / "rogue-secret.ts"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "// rogue: reads a K8s secret NAME directly (forbidden, CLAUDE.md §1).\n"
        'export const secretName = "confluence-creds";\n',
        encoding="utf-8",
    )


MUTATIONS = {
    "palette-literal-css": palette_literal_css,
    "hand-jwt-verify": hand_jwt_verify,
    "override-generated-np": override_generated_np,
    "local-navtabs": local_navtabs,
    "soft-default-dns": soft_default_dns,
    "delete-manifest": delete_manifest,
    "delete-resource-requirements": delete_resource_requirements,
    "delete-api-resource-requirements": delete_api_resource_requirements,
    "bespoke-secret-mount": bespoke_secret_mount,
}
