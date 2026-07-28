// Master-detail over whatever the Python api hands us.
//
// This file decides layout and nothing else. It never derives a status, never
// fills in a blank field, and never turns a missing OntoGate view into a link
// -- the payload already distinguishes those, and re-deciding them here would
// put a second opinion in front of the operator.

'use strict';

const state = { payload: null, selected: null, templates: null };

const el = (id) => document.getElementById(id);

function showError(message) {
  const box = el('error');
  box.textContent = message;
  box.hidden = !message;
}

function text(tag, value, className) {
  const node = document.createElement(tag);
  node.textContent = value;
  if (className) node.className = className;
  return node;
}

// --- the list on the left --------------------------------------------------

function renderList() {
  const list = el('list');
  list.replaceChildren();
  for (const item of state.payload.instances) {
    const entry = document.createElement('button');
    entry.type = 'button';
    entry.className = 'entry' + (item.name === state.selected ? ' selected' : '');
    entry.appendChild(text('span', item.name, 'entry-name'));
    entry.appendChild(text('span', item.kind, 'entry-kind'));
    entry.appendChild(text('span', item.generic.status, `badge ${badgeClass(item)}`));
    entry.addEventListener('click', () => {
      state.selected = item.name;
      renderList();
      renderDetail();
    });
    list.appendChild(entry);
  }
}

function badgeClass(item) {
  if (item.generic.healthy) return 'ok';
  if (item.generic.status === 'NOT PROBED') return 'unknown';
  if (item.generic.status === 'PLANNED' || item.generic.status === 'UNPROVEN') return 'pending';
  return 'bad';
}

// --- the detail on the right -----------------------------------------------

function definitionList(rows) {
  const list = document.createElement('dl');
  for (const row of rows) {
    list.appendChild(text('dt', row.label));
    const value = text('dd', row.value);
    if (row.source) value.title = `source: ${row.source}`;
    list.appendChild(value);
  }
  return list;
}

function section(title, build) {
  const node = document.createElement('section');
  node.appendChild(text('h3', title));
  build(node);
  return node;
}

function renderPanels(item, root) {
  for (const panel of item.panels) {
    if (!panel.rows.length && !panel.note) continue;
    root.appendChild(
      section(panel.title, (node) => {
        if (panel.rows.length) node.appendChild(definitionList(panel.rows));
        if (panel.note) node.appendChild(text('p', panel.note, 'muted'));
      })
    );
  }
}

function renderLocations(item, root) {
  root.appendChild(
    section('Where things live', (node) => {
      const list = document.createElement('dl');
      for (const answer of item.locations) {
        list.appendChild(text('dt', answer.question));
        list.appendChild(
          text('dd', answer.declared ? answer.value : answer.detail, answer.declared ? '' : 'muted')
        );
      }
      node.appendChild(list);
    })
  );
}

function renderOntogate(item, root) {
  root.appendChild(
    section('OntoGate', (node) => {
      if (!item.ontogate.available) {
        node.appendChild(text('p', item.ontogate.detail, 'muted'));
        return;
      }
      const link = document.createElement('button');
      link.type = 'button';
      link.className = 'link';
      link.textContent = item.ontogate.url;
      link.addEventListener('click', () =>
        window.vpath.openOntogate(item.ontogate.url).catch((error) => showError(error.message))
      );
      node.appendChild(link);
    })
  );
}

function renderDetail() {
  const detail = el('detail');
  detail.replaceChildren();
  const item = state.payload.instances.find((i) => i.name === state.selected);
  if (!item) {
    detail.appendChild(text('p', 'Select an instance on the left.', 'muted'));
    return;
  }

  detail.appendChild(text('h2', item.name));
  detail.appendChild(
    text('p', `${item.kind} · template ${item.template || 'unknown'} · ${item.lifecycle}`, 'muted')
  );
  if (item.notes) detail.appendChild(text('p', item.notes));

  detail.appendChild(
    section('At a glance', (node) => {
      node.appendChild(
        definitionList([
          { label: 'Status', value: item.generic.status, source: item.source },
          { label: 'Uptime', value: item.generic.uptime, source: '' },
          { label: 'Apps', value: item.generic.apps, source: '' },
          { label: 'State', value: item.generic.state, source: item.source },
          {
            label: 'Operations',
            value: item.generic.operations.join(', ') || 'none established for this type',
            source: '',
          },
        ])
      );
    })
  );

  renderPanels(item, detail);
  renderLocations(item, detail);
  renderOntogate(item, detail);

  const remove = document.createElement('button');
  remove.type = 'button';
  remove.className = 'danger';
  remove.textContent = `Remove ${item.name} from the register`;
  remove.addEventListener('click', () => removeInstance(item.name));
  detail.appendChild(remove);
}

// --- loading ---------------------------------------------------------------

async function load(probe) {
  showError('');
  el('register').textContent = probe ? 'probing…' : 'reading register…';
  try {
    state.payload = await window.vpath.view({ probe });
    el('register').textContent =
      `${state.payload.register} · ` +
      (state.payload.probed_at ? `probed ${state.payload.probed_at}` : 'not probed in this view');
    renderList();
    renderDetail();
  } catch (error) {
    el('register').textContent = 'no register read';
    showError(error.message);
  }
}

async function removeInstance(name) {
  showError('');
  try {
    await window.vpath.remove({ name });
    state.selected = null;
    await load(false);
  } catch (error) {
    showError(error.message);
  }
}

// --- creating from a template ----------------------------------------------

function renderTemplateForm() {
  const chosen = state.templates.find((t) => t.name === el('create-template').value);
  el('template-summary').textContent = chosen ? `${chosen.title} — ${chosen.summary}` : '';
  const warning = el('template-unproven');
  warning.hidden = !chosen || chosen.proven;
  warning.textContent = chosen && !chosen.proven ? `UNPROVEN: ${chosen.unproven_reason}` : '';

  const fields = el('create-fields');
  fields.replaceChildren();
  if (!chosen) return;
  for (const field of chosen.fields) {
    const label = document.createElement('label');
    label.appendChild(text('span', `${field.key}${field.required ? ' *' : ''}`));
    const input = document.createElement('input');
    input.name = field.key;
    input.placeholder = field.suggestion;
    input.required = field.required;
    label.appendChild(input);
    label.appendChild(text('small', field.comment, 'muted'));
    fields.appendChild(label);
  }
}

async function openCreateDialog() {
  showError('');
  try {
    state.templates = await window.vpath.templates();
  } catch (error) {
    showError(error.message);
    return;
  }
  const select = el('create-template');
  select.replaceChildren();
  for (const template of state.templates) {
    const option = document.createElement('option');
    option.value = template.name;
    option.textContent = template.proven ? template.name : `${template.name} (unproven)`;
    select.appendChild(option);
  }
  renderTemplateForm();
  el('create-dialog').showModal();
}

// `method="dialog"` closes the dialog and puts the pressed button's value in
// returnValue; anything other than "create" is a cancel.
async function submitCreate(returnValue) {
  if (returnValue !== 'create') return;
  const values = {};
  for (const input of el('create-fields').querySelectorAll('input')) {
    if (input.value.trim()) values[input.name] = input.value.trim();
  }
  showError('');
  try {
    await window.vpath.create({
      name: el('create-name').value.trim(),
      template: el('create-template').value,
      values,
    });
    await load(false);
  } catch (error) {
    showError(error.message);
  }
}

el('reload').addEventListener('click', () => load(false));
el('probe').addEventListener('click', () => load(true));
el('new').addEventListener('click', openCreateDialog);
el('create-template').addEventListener('change', renderTemplateForm);
el('create-dialog').addEventListener('close', (event) => submitCreate(event.target.returnValue));

load(false);
