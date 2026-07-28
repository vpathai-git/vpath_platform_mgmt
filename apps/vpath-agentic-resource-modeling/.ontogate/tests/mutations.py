"""Deliberate breaks for the NEGATIVE stories / red drill. Each mutation is
applied to a SCRATCH COPY of the app repo (never the real read-only app); the
gate then asserts the story's pinned contract goes RED for its declared reason,
and the copy is discarded. A mutation that fails to apply is a hard error, never
a skip — a negative story that cannot break is a soft pass.

Two mutations are SPECIFIC to this app (which fills the NEED face for real):
  * delete-resource-requirements — removes the agent-provider declaration; the
    app-strict NEED check in check.py turns C-need-resource-requirements RED.
  * bespoke-secret-mount — reads a K8s secret NAME directly in code; the
    foundation audit turns C-no-bespoke-secret-mount RED (the app must NEVER
    touch the LLM key — it is platform-managed via envfrom).
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
        "  name: vpath-agentic-resource-modeling-allow-egress\n"
        "  namespace: vpath-agentic-resource-modeling\n"
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
    """C-no-hardcoded-service-dns: a soft-default service-DNS fallback."""
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
    """C-need-resource-requirements: strip the agent-provider declaration from
    the root manifest. The foundation audit is lenient on NEED (an absent need
    reads as 'unused'), so the app-strict NEED check in check.py is what turns
    this RED — proving the Spine-3 makes the DECLARED need binding."""
    p = app / "vpath-app.yaml"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    lines = p.read_text(encoding="utf-8").splitlines(keepends=True)
    out, removed, i, n = [], False, 0, len(lines)
    while i < n:
        line = lines[i]
        stripped = line.lstrip(" ")
        indent = len(line) - len(stripped)
        if indent == 2 and stripped.startswith("resourceRequirements:"):
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
        raise AssertionError("resourceRequirements block not found to delete")
    p.write_text("".join(out), encoding="utf-8")


def bespoke_secret_mount(app):
    """C-no-bespoke-secret-mount: read a K8s secret NAME directly in code. The
    app must NEVER touch the LLM key — it is platform-managed via envfrom."""
    p = app / "src" / "app" / "rogue-secret.ts"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "// rogue: reads a K8s secret NAME directly (forbidden, CLAUDE.md §1).\n"
        'export const secretName = "agentic-resource-modeling-llm-key";\n',
        encoding="utf-8",
    )


def runtime_bespoke_key_read(app):
    """C-no-bespoke-secret-mount (RUNTIME surface): a Python backend module that
    fetches the LLM key itself by naming a K8s secret — the exact way a runtime
    must NOT reach cognition. The SDK transport owns credentials; the app never
    reads a provider key. Distinct from the .ts frontend break: it proves the
    Python runtime surface is red-drilled too."""
    p = app / "api" / "src" / "cognition" / "rogue_runtime.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# rogue runtime: names a K8s secret directly (forbidden, CLAUDE.md §1).\n"
        'secretName = "agentic-resource-modeling-llm-key"\n',
        encoding="utf-8",
    )


def rogue_provider_client(app):
    """C-given-agent-factory: construct a direct LLM-provider client instead of
    reaching cognition via get_agent_factory (the only sanctioned door)."""
    p = app / "api" / "src" / "cognition" / "rogue_provider.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# rogue: a direct provider client (forbidden — cognition ONLY via "
        "get_agent_factory).\n"
        "from openai import OpenAI\n"
        "client = OpenAI()\n",
        encoding="utf-8",
    )


def resource_json_secret(app):
    """C-contract-resource-json: open the forbidden access=resource_json secret
    lane — read_secret refuses it; protected values never ride resource_json."""
    p = app / "api" / "src" / "cognition" / "rogue_resource_json.py"
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(
        "# rogue: reads a secret over the forbidden resource_json lane.\n"
        'secret = read_secret(name="llm-key", access="resource_json")\n',
        encoding="utf-8",
    )


def agent_provider_variant_clash(app):
    """C-need-agent-provider: declare `variant` alongside constraints.agents —
    mutually exclusive (variant is sugar for constraints.agents)."""
    p = app / "vpath-app.yaml"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    text = p.read_text(encoding="utf-8")
    needle = "      - class: agent-provider\n        actions: [use, configure]\n"
    if needle not in text:
        raise AssertionError("agent-provider requirement block not found to clash")
    inject = needle + (
        "        variant: basic-llm\n"
        "        constraints:\n"
        "          agents: [basic-llm]\n"
    )
    p.write_text(text.replace(needle, inject), encoding="utf-8")


def zero_readiness_budget(app):
    """C-need-deploy: set a non-positive readinessBudget — the server removed the
    300s fallback, so a zero/missing budget must fail the deploy."""
    p = app / "vpath-app.yaml"
    if not p.exists():
        raise FileNotFoundError(f"mutation target missing: {p}")
    text = p.read_text(encoding="utf-8")
    if "readinessBudget: 300" not in text:
        raise AssertionError("readinessBudget: 300 not found to zero out")
    p.write_text(
        text.replace("readinessBudget: 300", "readinessBudget: 0"), encoding="utf-8"
    )


MUTATIONS = {
    "palette-literal-css": palette_literal_css,
    "hand-jwt-verify": hand_jwt_verify,
    "override-generated-np": override_generated_np,
    "local-navtabs": local_navtabs,
    "soft-default-dns": soft_default_dns,
    "delete-manifest": delete_manifest,
    "delete-resource-requirements": delete_resource_requirements,
    "bespoke-secret-mount": bespoke_secret_mount,
    "runtime-bespoke-key-read": runtime_bespoke_key_read,
    "rogue-provider-client": rogue_provider_client,
    "resource-json-secret": resource_json_secret,
    "agent-provider-variant-clash": agent_provider_variant_clash,
    "zero-readiness-budget": zero_readiness_budget,
}
