# The Electron shell

The graphical half of the management console: instances listed on the left,
one instance in detail on the right.

## What it is allowed to be

A renderer. Every fact in the window comes from

```bash
python -m vpath_platform_mgmt.console.api --json <command>
```

which `main.js` spawns. The shell derives no status, fills in no blank field,
and turns no missing OntoGate view into a link — the payload already
distinguishes those cases, and deciding them a second time here would put an
untested opinion in front of the operator. If you find yourself computing
something about an instance in JavaScript, it belongs in
`src/vpath_platform_mgmt/console/view.py`, where `make check` can see it.

## Running it

```bash
npm install
npm start
```

`VPATH_PYTHON` overrides the interpreter (default: `python3`, or `python` on
Windows). `PYTHONPATH` is set to the repository's `src/` automatically, so the
shell runs from a checkout without installing the package first.

## Why this is the build form

`README.md` left the console's build form open ("graphical or chatbot-assisted,
TBD") and `analysis/instance-status/console-ui.issue.md` listed Python-TUI,
local web page and Electron as the candidates. Electron was chosen by the user
on 2026-07-28. It brings a Node toolchain into an otherwise pure-Python
repository; that cost is accepted deliberately, and is contained by the rule
above — the Node side stays a view, so the Python side remains the only place
where behaviour can regress.

## Security posture

`contextIsolation` on, `nodeIntegration` off, `sandbox` on, a preload bridge
exposing exactly five verbs, a `default-src 'self'` CSP, navigation and window
opening denied. The one outward action is the OntoGate link, which is opened in
the real browser and only when it is `http(s)`.
