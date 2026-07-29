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
const CONN = {
  connecting: ["Connecting…", "q"],
  connected: ["Connected", "ok"],
  unreachable: ["Unreachable", "err"],
  disconnected: ["Disconnected", "err"],
  "signed-out": ["Signed out", "q"],
};
let connTimer = 0;

/* Badge and Connect button are two halves of one state machine: the button
   shows exactly while the connection is down, so they cannot drift.
   `connected`/`unreachable` speak about the instance (named next to the
   status); `disconnected` means this console's own backend is gone. */
function setConn(state, instance) {
  $("conn").textContent =
    instance ? CONN[state][0] + " · " + instance : CONN[state][0];
  $("conn").className = "badge " + CONN[state][1];
  $("connect").hidden = state !== "disconnected" && state !== "unreachable";
}

async function tick(fresh) {
  connTimer = 0;
  let next = "disconnected";
  let name = "";
  try {
    const r = await fetch("/api/state" + (fresh ? "?fresh=1" : ""),
      {headers: hdrs()});
    if (r.status === 401) { signedOut("Session expired — sign in again"); return; }
    if (r.ok) {
      const s = await r.json();
      render(s);
      const inst = s.instance || {};
      name = inst.name || "";
      next = inst.reachable ? "connected" : "unreachable";
    }
  } catch (e) { /* backend gone or restarting; the badge reports it */ }
  setConn(next, name);
  connTimer = setTimeout(tick, next === "disconnected" ? RETRY_MS : POLL_MS);
}

function connectNow() {
  if (connTimer) clearTimeout(connTimer);
  setConn("connecting");
  tick(true);
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
