"use strict";
const $ = (id) => document.getElementById(id);
const chip = (s) =>
  ({queued: "q", running: "run", succeeded: "ok", failed: "err"})[s] || "q";
const hdrs = () => ({
  "Content-Type": "application/json",
  "X-Dev-Actor": $("actor").value || "you",
  "X-Dev-Role": $("role").value,
});
const esc = (s) =>
  String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"})[c]);

let APPS = [];
let PLATFORM = "";
let selectedApp = null;

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
function submitJob() { post({verb: $("verb").value, app: $("app").value}); }
function reinstall() {
  const c = prompt("Destructive: full server reinstall.\nType REINSTALL:");
  if (c !== null) post({verb: "reinstall", app: "server", confirm: c || ""});
}
function deploySelected() {
  if (!selectedApp) return;
  $("a-msg").textContent = "submitting deploy for " + selectedApp.name + "…";
  fetch("/api/jobs", {
    method: "POST", headers: hdrs(),
    body: JSON.stringify({verb: "deploy", app: selectedApp.name}),
  }).then((r) => r.json().then((d) => {
    $("a-msg").textContent = r.ok
      ? "job " + d.job + " accepted — see Server Dashboard"
      : "refused: " + (d.detail || "error");
  }));
}
const fmt = (ts) => new Date(ts * 1000).toLocaleTimeString();

function render(s) {
  const eng = $("engine");
  eng.textContent = s.engine === "simulated"
    ? "SIMULATED ENGINE — no real server contact" : "REAL ENGINE: " + s.engine;
  eng.className = "badge " + (s.engine === "simulated" ? "sim" : "real");
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
    : '<li class="dim">none held</li>';
  $("audit").innerHTML = (s.audit || []).slice(0, 15).map((a) =>
    `<li><span class="mono dim">${fmt(a.at)}</span> ` +
    `<span class="mono">${esc(a.action)}</span> ${esc(a.target)} — ` +
    `${esc(a.actor)} (${esc(a.role)}): <b>${esc(a.result)}</b></li>`).join("")
    || '<li class="dim">empty</li>';
}

/* ---------- application explorer ---------- */
function selectApp(a, rowEl) {
  selectedApp = a;
  showApp();
  document.querySelectorAll(".app-row").forEach((e) => e.classList.remove("sel"));
  rowEl.classList.add("sel");
  $("a-title").textContent = a.title;
  $("a-type").textContent = a.type || "app";
  $("a-desc").textContent = a.description || "";
  $("a-meta").innerHTML =
    [`name: ${esc(a.name)}`, a.base_path ? `path: ${esc(a.base_path)}` : "",
     a.port ? `port: ${a.port}` : "", `folder: ${esc(a.source)}`]
      .filter(Boolean).map((t) => `<span>${t}</span>`).join("");
  const open = $("a-open");
  open.disabled = !a.url;
  open.title = a.url || "set VPATH_MGMT_PLATFORM_URL to enable";
  open.onclick = () => a.url && window.open(a.url, "_blank", "noopener");
  $("a-msg").textContent = a.url ? "" :
    "no platform URL configured — set VPATH_MGMT_PLATFORM_URL to open apps";
  $("f-name").textContent = "Select a file in the explorer";
  $("f-meta").innerHTML = "";
  $("f-body").textContent = "Pick a file on the left to inspect it.";
  loadTree(a, rowEl);
}

async function loadTree(a, rowEl) {
  let holder = rowEl.nextElementSibling;
  if (holder && holder.classList.contains("tree")) { holder.remove(); return; }
  document.querySelectorAll(".tree").forEach((e) => e.remove());
  const r = await fetch(`/api/apps/${encodeURIComponent(a.name)}/tree`,
    {headers: hdrs()});
  if (!r.ok) return;
  const d = await r.json();
  holder = document.createElement("div");
  holder.className = "tree";
  d.nodes.forEach((n) => {
    const depth = n.path.split("/").length - 1;
    const el = document.createElement("div");
    el.className = "tnode";
    el.style.paddingLeft = (16 + depth * 12) + "px";
    el.innerHTML = `<span class="ic">${n.dir ? "▸" : "·"}</span>` +
      esc(n.path.split("/").pop());
    el.title = n.path;
    if (!n.dir) el.onclick = () => openFile(a, n, el);
    holder.appendChild(el);
  });
  rowEl.after(holder);
}

async function openFile(a, node, el) {
  document.querySelectorAll(".tnode").forEach((e) => e.classList.remove("sel"));
  el.classList.add("sel");
  const r = await fetch(
    `/api/apps/${encodeURIComponent(a.name)}/file?path=${encodeURIComponent(node.path)}`,
    {headers: hdrs()});
  const d = await r.json();
  $("f-name").textContent = node.path;
  if (!r.ok) {
    $("f-meta").innerHTML = "";
    $("f-body").textContent = d.detail || "could not read file";
    return;
  }
  $("f-meta").innerHTML = `<span>${d.size} bytes</span>` +
    (d.truncated ? "<span>truncated</span>" : "");
  $("f-body").textContent = d.content;
}

async function loadApps() {
  const r = await fetch("/api/apps", {headers: hdrs()});
  if (!r.ok) return;
  const d = await r.json();
  APPS = d.apps || [];
  PLATFORM = d.platform_url || "";
  const list = $("applist");
  list.innerHTML = "";
  if (!APPS.length) {
    list.innerHTML = '<div class="nav-item dim">no applications found</div>';
    return;
  }
  APPS.forEach((a) => {
    const row = document.createElement("div");
    row.className = "app-row";
    row.innerHTML = `<span class="caret">▸</span><span class="nm">${esc(a.title)}` +
      `</span><span class="tw">${esc(a.type || "")}</span>`;
    row.onclick = () => selectApp(a, row);
    list.appendChild(row);
  });
}

async function tick() {
  try {
    const r = await fetch("/api/state", {headers: hdrs()});
    if (r.ok) render(await r.json());
  } catch (e) { /* server restarting; keep polling */ }
  setTimeout(tick, 1000);
}
loadApps();
tick();
