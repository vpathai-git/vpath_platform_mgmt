"use strict";
/* Running applications: what the cluster is doing with the installed apps.
 *
 * The catalog says an app EXISTS and /api/apps says it is INSTALLED; only
 * this asks what is actually RUNNING. Pods are grouped by the namespace they
 * run in — the app's own, plus one kp-<app>-<user> project namespace per
 * provisioned user, which is where workflow pods live.
 *
 * Expanding a row is what costs a cluster call, so a collapsed list costs
 * nothing and only the open app is re-polled. Exactly one row is open at a
 * time, which is also what bounds the polling to one call per interval.
 */

const POD_POLL_MS = 5000;
let openApp = "";
let podTimer = 0;

function stopPodPoll() {
  if (podTimer) { clearTimeout(podTimer); podTimer = 0; }
}

/* Collapse on leaving the dashboard: the section is hidden there, and a
   poll whose result nobody can see is load nobody asked for. */
function collapsePods() {
  stopPodPoll();
  openApp = "";
}

/* Age is computed in the browser, never on the server: a rendered "4d" is
   stale the moment it is sent, and this list re-renders every 5 seconds. */
function age(iso) {
  if (!iso) return "";
  const secs = (Date.now() - Date.parse(iso)) / 1000;
  if (!isFinite(secs) || secs < 0) return "";
  const day = Math.floor(secs / 86400);
  if (day) return day + "d";
  const hour = Math.floor(secs / 3600);
  if (hour) return hour + "h";
  const min = Math.floor(secs / 60);
  return min ? min + "m" : Math.floor(secs) + "s";
}

function podRow(p) {
  return `<tr><td class="mono">${esc(p.name)}</td>` +
    `<td><span class="chip ${p.phase === "Running" ? "ok" : "err"}">` +
    `${esc(p.phase)}</span></td>` +
    `<td class="mono">${esc(p.ready)}</td>` +
    `<td class="mono ${p.restarts ? "" : "dim"}">${esc(p.restarts)}</td>` +
    `<td class="mono dim">${esc(age(p.started_at))}</td></tr>`;
}

/* The order of these three branches is the point. A namespace we could not
   read carries a null pod list, and drawing that as emptiness would state
   the opposite of what happened — so it is answered first. */
function namespaceBlock(ns) {
  const head = `<div class="ns"><span class="chip q">${esc(ns.kind)}</span>` +
    `<span class="mono">${esc(ns.name)}</span></div>`;
  if (ns.pods === null) {
    return head + `<div class="ns-err">${esc(ns.error || "could not be read")}</div>`;
  }
  if (!ns.pods.length) return head + '<div class="dim ns-empty">No pods running</div>';
  return head + '<table class="pods"><tr><th>pod</th><th>phase</th><th>ready</th>' +
    "<th>restarts</th><th>age</th></tr>" + ns.pods.map(podRow).join("") + "</table>";
}

function podsBody(d) {
  const ok = d.sync === "Synced" && d.health === "Healthy";
  return `<div class="meta"><span class="chip ${ok ? "ok" : "err"}">` +
    `${esc(d.sync)} / ${esc(d.health)}</span></div>` +
    (d.namespaces || []).map(namespaceBlock).join("");
}

async function loadPods(name) {
  const detail = $("pods-" + name);
  if (!detail) return;
  try {
    const r = await fetch(`/api/apps/${encodeURIComponent(name)}/pods`,
      {headers: hdrs()});
    const d = await r.json();
    detail.innerHTML = r.ok ? podsBody(d)
      : `<div class="ns-err">${esc(d.detail || "could not read pods")}</div>`;
  } catch (e) {
    detail.innerHTML = `<div class="ns-err">${esc(String(e.message || e))}</div>`;
  }
  if (openApp === name) podTimer = setTimeout(() => loadPods(name), POD_POLL_MS);
}

function toggleApp(name) {
  stopPodPoll();
  openApp = openApp === name ? "" : name;
  renderRunning(APPS);
  if (openApp) loadPods(openApp);
}

/* An app whose install state is unknown stays in the list saying so. Hiding
   it would assert it is not running, which nobody established — the same
   rule the store follows for its Install button. */
function runningSummary(apps) {
  if (apps.some((a) => a.installed === null)) return "install state unknown";
  return apps.filter((a) => a.installed === true).length + " of " +
    apps.length + " installed";
}

function runningRow(a) {
  const open = openApp === a.name;
  const known = a.installed === true;
  return `<div class="run-app"><div class="run-head" data-app="${esc(a.name)}">` +
    `<span class="caret">${open ? "▾" : "▸"}</span>` +
    `<span class="chip ${known ? "ok" : "q"}">${known ? "running" : "unknown"}</span>` +
    `<span class="nm">${esc(a.title || a.name)}</span>` +
    `<span class="mono dim">${esc(a.name)}</span></div>` +
    `<div class="run-detail" id="pods-${esc(a.name)}"${open ? "" : " hidden"}>` +
    (open ? '<div class="dim">Reading the cluster…</div>' : "") + "</div></div>";
}

function renderRunning(apps) {
  const host = $("running");
  if (!host) return;
  $("running-count").textContent = runningSummary(apps);
  const rows = apps.filter((a) => a.installed !== false);
  if (!rows.length) {
    host.innerHTML = '<div class="dim">No applications are installed here</div>';
    return;
  }
  host.innerHTML = rows.map(runningRow).join("");
  host.querySelectorAll(".run-head").forEach((el) => {
    el.onclick = () => toggleApp(el.dataset.app);
  });
}
