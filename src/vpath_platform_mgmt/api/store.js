"use strict";
/* The app store: what exists, what is installed, and moving apps between.
 *
 * The catalog lists applications that EXIST; `installed` says which of them
 * the server is actually running. Keeping the two apart is the point — the
 * store offers Install for the former and Uninstall for the latter, and
 * shows "unknown" rather than guessing when the engine cannot report.
 */

let APPS = [];
let PLATFORM = "";
let selectedApp = null;

const INSTALLED_LABEL = {true: "Installed", false: "Not installed", null: "Unknown"};

function confirmUninstall(name, title) {
  return confirm(
    `Uninstall ${title || name}?\n\n` +
    `'${name}' is removed from the Deploy-of-Record and ArgoCD tears down ` +
    "its running workloads. Re-installing needs a fresh render on the build " +
    "host — deploy alone will not bring it back.");
}

function forSelected(verb) {
  if (!selectedApp) return;
  if (verb === "uninstall" &&
      !confirmUninstall(selectedApp.name, selectedApp.title)) return;
  $("a-msg").textContent = `Submitting ${verb} for ${selectedApp.name}…`;
  fetch("/api/jobs", {
    method: "POST", headers: hdrs(),
    body: JSON.stringify({verb: verb, app: selectedApp.name}),
  }).then((r) => r.json().then((d) => {
    $("a-msg").textContent = r.ok
      ? "Job " + d.job + " accepted — see Recent jobs"
      : "Refused: " + (d.detail || "error");
    if (r.ok) setTimeout(loadApps, 4000);
  }));
}

function deploySelected() { forSelected("deploy"); }
function uninstallSelected() { forSelected("uninstall"); }

function installState(a) {
  return a.installed === true ? "true" : a.installed === false ? "false" : "null";
}

/* Install and Uninstall are opposite directions, so only one applies at a
 * time. When the state is unknown neither is offered: acting on a guess is
 * how you uninstall something that was never installed. */
function showInstallButtons(a) {
  const state = installState(a);
  $("a-install").hidden = state !== "false";
  $("a-uninstall").hidden = state !== "true";
  $("a-state").textContent = INSTALLED_LABEL[state];
  $("a-state").className = "chip " + (state === "true" ? "ok" : "q");
}

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
  showInstallButtons(a);
  const open = $("a-open");
  open.disabled = !a.url;
  open.title = a.url || "Set VPATH_MGMT_PLATFORM_URL to enable";
  open.onclick = () => a.url && window.open(a.url, "_blank", "noopener");
  $("a-msg").textContent = a.url ? "" :
    "No platform URL configured — set VPATH_MGMT_PLATFORM_URL to open apps";
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
    $("f-body").textContent = d.detail || "Could not read file";
    return;
  }
  $("f-meta").innerHTML = `<span>${d.size} bytes</span>` +
    (d.truncated ? "<span>Truncated</span>" : "");
  $("f-body").textContent = d.content;
}

/* The job form deploys by app NAME, but people know apps by their title, so
 * the picker shows the title and carries the name as its value. Free text
 * here used to let a typo reach the engine as an unknown app. */
function fillAppPicker() {
  const picker = $("app");
  const chosen = picker.value;
  picker.innerHTML = APPS.length
    ? APPS.map((a) =>
        `<option value="${esc(a.name)}">${esc(a.title || a.name)}</option>`).join("")
    : '<option value="">No applications found</option>';
  if (chosen && APPS.some((a) => a.name === chosen)) picker.value = chosen;
}

/* Two different catalogs, kept visibly apart: what this console can see on
   disk, and what the platform actually serves its users. They are not the
   same population by design, so only the overlap is compared — and an
   unreadable platform says so, because "offers nothing" and "could not ask"
   look identical in a summary line and mean opposite things. */
function showCatalogState(c) {
  const el = $("catalog-state");
  if (!c) { el.innerHTML = ""; return; }
  const parts = [`<span>${c.total} here</span>`];
  parts.push(`<span>${c.installed_here === null
    ? "install state unknown" : c.installed_here + " installed"}</span>`);
  const p = c.platform;
  if (p) {
    parts.push(`<span>${p.served_total} in the platform catalog</span>`);
    if (p.only_on_platform) parts.push(`<span>${p.only_on_platform} not visible here</span>`);
    const bad = (p.label_mismatches || []).length;
    parts.push(bad
      ? `<span class="chip err">${bad} label mismatch${bad > 1 ? "es" : ""}</span>`
      : '<span class="chip ok">labels match</span>');
  } else {
    parts.push(`<span class="dim">platform catalog: ${esc(c.platform_error || "unknown")}</span>`);
  }
  el.innerHTML = parts.join("");
  el.title = (p && (p.label_mismatches || []).length)
    ? p.label_mismatches.map((m) => `${m.name}: here "${m.here}", platform "${m.platform}"`).join("\n")
    : "";
}

async function loadApps() {
  const r = await fetch("/api/apps", {headers: hdrs()});
  if (!r.ok) return;
  const d = await r.json();
  APPS = d.apps || [];
  PLATFORM = d.platform_url || "";
  fillAppPicker();
  showCatalogState(d.catalog);
  const list = $("applist");
  list.innerHTML = "";
  if (!APPS.length) {
    list.innerHTML = '<div class="nav-item dim">No applications found</div>';
    return;
  }
  APPS.forEach((a) => {
    const row = document.createElement("div");
    row.className = "app-row";
    const mark = a.installed === true ? "●" : a.installed === false ? "○" : "?";
    row.innerHTML = `<span class="caret">${mark}</span>` +
      `<span class="nm">${esc(a.title)}</span>` +
      `<span class="tw">${esc(INSTALLED_LABEL[installState(a)])}</span>`;
    row.title = `${a.name} — ${INSTALLED_LABEL[installState(a)]}`;
    row.onclick = () => selectApp(a, row);
    list.appendChild(row);
  });
  if (selectedApp) {
    const fresh = APPS.find((a) => a.name === selectedApp.name);
    if (fresh) { selectedApp = fresh; showInstallButtons(fresh); }
  }
}
