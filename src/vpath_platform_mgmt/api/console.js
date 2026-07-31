"use strict";
const $ = (id) => document.getElementById(id);
const chip = (s) =>
  ({queued: "q", running: "run", succeeded: "ok", failed: "err"})[s] || "q";
const hdrs = () => VpathAuth.headers();
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})[c]);

/* APPS, PLATFORM and selectedApp live in store.js, which owns the catalog. */

/* ---------- navigation ---------- */
function showDash() {
  $("view-dash").classList.add("on");
  $("view-app").classList.remove("on");
  $("nav-dash").classList.add("sel");
  document.querySelectorAll(".app-row").forEach((e) => e.classList.remove("sel"));
}
function showApp() {
  collapsePods();
  $("view-app").classList.add("on");
  $("view-dash").classList.remove("on");
  $("nav-dash").classList.remove("sel");
}

/* ---------- jobs ---------- */
async function post(body) {
  const r = await fetch("/api/jobs",
    {method: "POST", headers: hdrs(), body: JSON.stringify(body)});
  const d = await r.json();
  $("msg").textContent = r.ok ? "" : (d.detail || "error");
}
function submitJob() {
  const verb = $("verb").value;
  const app = $("app").value;
  if (!app) { $("msg").textContent = "Pick an application first"; return; }
  const picked = APPS.find((a) => a.name === app);
  if (verb === "uninstall" && !confirmUninstall(app, picked && picked.title)) return;
  post({verb: verb, app: app});
}

function reinstall() {
  const c = prompt("Destructive: full server reinstall.\nType REINSTALL:");
  if (c !== null) post({verb: "reinstall", app: "server", confirm: c || ""});
}

/* Install/uninstall of a selected app live in store.js. */
const fmt = (ts) => new Date(ts * 1000).toLocaleTimeString();

/* ---------- add an application ---------- */
/* generate is only sent when a port was given: the registry refuses
   generation flags for a repository that already ships its own
   vpath-app.yaml, which is the common case. On success the job just
   shows up in Recent jobs on the next poll — no second poll loop here. */
async function publishApp(event) {
  event.preventDefault();
  const value = (id) => $(id).value.trim();
  const error = $("add-app-error");
  error.hidden = true;
  error.textContent = "";
  const port = Number(value("add-app-port"));
  const generate = port
    ? {
        name: value("add-app-name"),
        port: port,
        base_path: value("add-app-base-path"),
        title: value("add-app-title"),
      }
    : null;
  try {
    const r = await fetch("/api/apps/publish", {
      method: "POST", headers: hdrs(),
      body: JSON.stringify({
        url: value("add-app-url"),
        ref: value("add-app-ref") || "main",
        path: value("add-app-path"),
        name: value("add-app-name"),
        generate: generate,
      }),
    });
    const d = await r.json();
    if (!r.ok) {
      error.textContent = d.detail || "error";
      error.hidden = false;
      return;
    }
    $("add-app").reset();
  } catch (e) {
    error.textContent = String(e.message || e);
    error.hidden = false;
  }
}
$("add-app").addEventListener("submit", publishApp);

function render(s) {
  $("jobs").innerHTML =
    "<tr><th>id</th><th>verb</th><th>app</th><th>actor</th><th>engine</th>" +
    "<th>state</th><th>step</th></tr>" +
    s.jobs.map((j) =>
      `<tr><td class="mono dim">${esc(j.id)}</td><td class="mono">${esc(j.verb)}</td>` +
      `<td>${esc(j.app)}</td><td>${esc(j.actor)}</td>` +
      `<td><span class="chip ${j.engine === "simulated" ? "q" : "err"}">` +
      `${esc(j.engine)}</span></td>` +
      `<td><span class="chip ${chip(j.state)}">${esc(j.state)}</span></td>` +
      `<td class="dim">${esc(j.step)}</td></tr>`).join("");
  if (s.health) {
    $("healthline").innerHTML =
      `<span class="chip ${s.health.verdict === "healthy" ? "ok" : "err"}">` +
      `${esc(s.health.verdict)}</span> <span class="dim">at ${fmt(s.health.at)}</span>`;
    $("gates").innerHTML = Object.entries(s.health.gates || {}).map(([g, v]) =>
      `<span class="chip ${v === "pass" ? "ok" : "err"}">${esc(g)}</span>`).join("");
  }
  const locks = s.locks || [];
  $("locks").innerHTML = locks.length
    ? locks.map((l) => `<li><span class="mono">${esc(l.scope)}</span> — ` +
        `${esc(l.holder)} <span class="dim">since ${fmt(l.since)}</span></li>`).join("")
    : '<li class="dim">None held</li>';
  $("audit").innerHTML = (s.audit || []).slice(0, 15).map((a) =>
    `<li><span class="mono dim">${fmt(a.at)}</span> ` +
    `<span class="mono">${esc(a.action)}</span> ${esc(a.target)} — ` +
    `${esc(a.actor)} (${esc(a.role)}): <b>${esc(a.result)}</b></li>`).join("")
    || '<li class="dim">Empty</li>';
}

/* ---------- connection ---------- */
const POLL_MS = 1000;
const RETRY_MS = 5000;
/* label, chip class, and the fallback detail for states the server cannot
   explain — when the backend itself is gone there is no /api/state to carry
   a diagnosis, and that is the failure an operator hits most often. */
const CONN = {
  connecting: ["Connecting…", "q", ""],
  connected: ["Connected", "ok", ""],
  unreachable: ["Unreachable", "err", ""],
  disconnected: ["Disconnected", "err",
    "this console's own backend is not answering — is vpath-console still running?"],
  "signed-out": ["Signed out", "q", ""],
};
let connTimer = 0;

/* Badge, detail and buttons are all halves of one state machine: they are
   set together, so they cannot drift. `connected`/`unreachable` speak about
   the instance (named next to the status); `disconnected` means this
   console's own backend is gone. The detail says WHY, because a dead tunnel,
   an expired token and a stopped platform are one red badge and three
   different fixes — "Start tunnel" is offered only for the one it fixes. */
function setConn(state, instance, detail, reason) {
  const down = state === "disconnected" || state === "unreachable";
  $("conn").textContent =
    instance ? CONN[state][0] + " · " + instance : CONN[state][0];
  $("conn").className = "badge " + CONN[state][1];
  $("conn-detail").textContent = down ? (detail || CONN[state][2]) : "";
  $("connect").hidden = !down;
  $("tunnel").hidden = reason !== "no-route";
}

async function tick(fresh) {
  connTimer = 0;
  let next = "disconnected";
  let inst = {};
  try {
    const r = await fetch("/api/state" + (fresh ? "?fresh=1" : ""),
      {headers: hdrs()});
    if (r.status === 401) { signedOut("Session expired — sign in again"); return; }
    if (r.ok) {
      const s = await r.json();
      render(s);
      inst = s.instance || {};
      next = inst.reachable ? "connected" : "unreachable";
    }
  } catch (e) { /* backend gone or restarting; the badge reports it */ }
  setConn(next, inst.name || "", inst.detail || "", inst.reason || "");
  connTimer = setTimeout(tick, next === "disconnected" ? RETRY_MS : POLL_MS);
}

function connectNow() {
  if (connTimer) clearTimeout(connTimer);
  setConn("connecting");
  tick(true);
}

/* Starting a tunnel spawns ssh on the console's host, so it is a deliberate
   second click — never something a failed poll does by itself. */
async function startTunnel() {
  const button = $("tunnel");
  button.disabled = true;
  $("conn-detail").textContent = "Opening the SSH tunnel…";
  try {
    const r = await fetch("/api/instance/tunnel",
      {method: "POST", headers: hdrs()});
    const d = await r.json();
    if (!r.ok) {
      $("conn-detail").textContent = d.detail || "Tunnel failed";
      return;
    }
    connectNow();
  } catch (e) {
    $("conn-detail").textContent = String(e.message || e);
  } finally {
    button.disabled = false;
  }
}

/* ---------- sign-in ---------- */
function signIn() { VpathAuth.signIn().catch((e) => fatal(e)); }
function signOut() { VpathAuth.signOut(); signedOut("Signed out"); }

function signedOut(why) {
  $("whoami").textContent = why;
  $("signin").hidden = false;
  $("signout").hidden = true;
  setConn("signed-out");
}

function signedIn(who) {
  $("whoami").textContent = `${who.actor} · ${who.role}`;
  $("signin").hidden = true;
  $("signout").hidden = false;
}

function fatal(err) {
  $("conn").textContent = "Sign-in failed";
  $("conn").className = "badge err";
  $("msg").textContent = String(err.message || err);
}

VpathAuth.init().then((session) => {
  if (session.mode === "oidc") {
    $("dev-identity").hidden = true;
    $("oidc-identity").hidden = false;
    if (session.error) {
      const rejected = session.error.startsWith("signed in");
      signedOut(rejected ? "Token rejected" : "Cannot reach Keycloak");
      // A rejected token is worth retrying after a fix; an unreachable
      // Keycloak is not, so only that one disables the button.
      $("signin").disabled = !rejected;
      fatal(new Error(session.error));
      return;
    }
    if (!session.authenticated) {
      signedOut("Not signed in");
      return;
    }
    signedIn(session.identity);
  }
  loadApps();
  tick();
}).catch((e) => fatal(e));
