"use strict";
/* Fleet master-detail: lists register instances; does not switch the ops engine. */

function coarseChip(coarse) {
  const c = String(coarse || "?").toLowerCase();
  if (c === "healthy") return "ok";
  if (c === "unhealthy" || c === "unreachable" || c === "drift") return "err";
  return "q";
}

async function loadInstances() {
  const list = $("instancelist");
  if (!list) return;
  list.innerHTML = '<div class="inst-empty">Loading instances…</div>';
  const r = await fetch("/api/instances", {headers: hdrs()});
  if (!r.ok) {
    list.innerHTML =
      '<div class="inst-empty">Instances unavailable. Check sign-in and ' +
      "that the console can read instances.local.env.</div>";
    return;
  }
  const rows = await r.json();
  if (!rows.length) {
    list.innerHTML =
      '<div class="inst-empty">No fleet register yet. Add instances to ' +
      '<span class="mono">instances.local.env</span>. This list does not ' +
      "switch the ops drive (header).</div>";
    return;
  }
  list.innerHTML = rows.map((row) => {
    const n = esc(row.name);
    return `<div class="nav-item inst-row" data-name="${n}" role="button"
      tabindex="0" onclick="showInstance('${n}')"
      onkeydown="if(event.key==='Enter'||event.key===' '){event.preventDefault();showInstance('${n}')}">
      <span class="nm">${n}</span>
      <span class="chip ${coarseChip(row.coarse)}">${esc(row.coarse || "?")}</span>
      <span class="tw">${esc(row.kind)}</span>
    </div>`;
  }).join("");
}

async function showInstance(name) {
  $("view-dash").classList.remove("on");
  $("view-app").classList.remove("on");
  $("view-instance").classList.add("on");
  $("nav-dash").classList.remove("sel");
  document.querySelectorAll(".app-row,.inst-row").forEach((e) => e.classList.remove("sel"));
  document.querySelectorAll(`.inst-row[data-name="${CSS.escape(name)}"]`)
    .forEach((e) => e.classList.add("sel"));
  $("instance-detail").textContent = "Loading…";
  const r = await fetch("/api/instances/" + encodeURIComponent(name), {headers: hdrs()});
  if (!r.ok) {
    $("instance-detail").textContent = "Failed to load instance";
    return;
  }
  const d = await r.json();
  const facts = (d.probe.facts || []).map((f) =>
    `<div class="meta">${esc(f.label)}: ${esc(f.value)}</div>`).join("");
  const gaps = (d.probe.gaps || []).map((g) =>
    `<div class="error">! ${esc(g.label)}: ${esc(g.value)}</div>`).join("");
  const hist = (d.history || []).slice().reverse().slice(0, 8).map((h) =>
    `<li>${esc(h.ts)} · ${esc(h.coarse)}</li>`).join("");
  const onto = d.ontogate_url
    ? `<a href="${esc(d.ontogate_url)}" target="_blank" rel="noopener">OntoGate</a>`
    : '<span class="dim">OntoGate not available</span>';
  $("instance-detail").innerHTML =
    `<h2>${esc(d.name)}</h2>` +
    `<p class="meta">${esc(d.kind)} · ${esc(d.lifecycle)} · ${esc(d.probe.verdict)}</p>` +
    `<p id="instance-ontogate">${onto}</p>` +
    `<section><h3>Status</h3>${facts || '<div class="dim">No facts</div>'}${gaps}</section>` +
    `<section><h3>History</h3><ul id="instance-history">` +
    `${hist || '<li class="dim">None yet</li>'}</ul></section>` +
    `<section><h3>Ops</h3><p class="dim">Mutating ops stay on the ops drive ` +
    `named in the header. This fleet panel is read-only status.</p></section>`;
}

document.addEventListener("DOMContentLoaded", () => {
  if ($("instancelist")) loadInstances();
});
