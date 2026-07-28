// The shell's main process: window, and one way to reach the Python side.
//
// Every answer this shell shows comes from `vpath_platform_mgmt.console.api
// --json`, spawned here. The shell computes nothing about instances itself --
// if it did, the window could disagree with what `make check` verified.

'use strict';

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { execFile } = require('node:child_process');
const path = require('node:path');

// <repo>/src/vpath_platform_mgmt/console/electron -> <repo>. Only meaningful
// when running from a checkout: in a packaged build this file lives inside
// app.asar, where walking up four directories is not the repository at all.
const REPO_ROOT = path.resolve(__dirname, '..', '..', '..', '..');
const SRC_DIR = path.join(REPO_ROOT, 'src');
const MODULE = 'vpath_platform_mgmt.console.api';

// The api's own exit codes. 1 = the action was refused (bad values, name
// taken); 2 = the truth could not be established (no register, unknown name).
const EXIT_REFUSED = 1;

function pythonExecutable() {
  if (process.env.VPATH_PYTHON) return process.env.VPATH_PYTHON;
  return process.platform === 'win32' ? 'python' : 'python3';
}

// How the Python side is reached differs between a checkout and a build.
//
// From a checkout, the repository's own src/ goes on PYTHONPATH so the console
// runs without installing anything first. A packaged build has no repository:
// it requires `vpath-platform-mgmt` to be installed in the interpreter that
// VPATH_PYTHON names, and putting a stale src/ path on PYTHONPATH there would
// either do nothing or, worse, shadow the installed package with whatever
// happens to sit four directories above app.asar.
//
// The register moves with it. A checkout has a sensible default next to the
// repository; an installed package does not, so a packaged build declares one
// explicit per-user location instead of letting the default resolve to
// somewhere inside site-packages.
function pythonEnvironment() {
  const env = { ...process.env };
  if (app.isPackaged) {
    if (!env.VPATH_INSTANCES_FILE) {
      env.VPATH_INSTANCES_FILE = path.join(app.getPath('userData'), 'instances.local.env');
    }
    return { env, cwd: app.getPath('userData') };
  }
  env.PYTHONPATH = env.PYTHONPATH ? `${SRC_DIR}${path.delimiter}${env.PYTHONPATH}` : SRC_DIR;
  return { env, cwd: REPO_ROOT };
}

// Run one api command and return its parsed JSON. A non-zero exit is turned
// into a rejection carrying the api's own stderr, so the window shows the
// message the tooling wrote rather than a generic failure.
function runApi(args) {
  return new Promise((resolve, reject) => {
    const argv = ['-m', MODULE, '--json', ...args];
    const { env, cwd } = pythonEnvironment();

    execFile(
      pythonExecutable(),
      argv,
      { cwd, env, maxBuffer: 32 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error && typeof error.code !== 'number') {
          reject(
            new Error(
              `could not start ${pythonExecutable()}: ${error.message}\n` +
                'This console is a renderer; it needs a Python interpreter with ' +
                'vpath-platform-mgmt installed. Set VPATH_PYTHON to point at one.'
            )
          );
          return;
        }
        if (error) {
          const detail = (stderr || stdout || '').trim() || `exit ${error.code}`;
          const failure = new Error(detail);
          failure.refused = error.code === EXIT_REFUSED;
          reject(failure);
          return;
        }
        try {
          resolve(JSON.parse(stdout));
        } catch (parseError) {
          reject(new Error(`unreadable answer from ${MODULE}: ${parseError.message}`));
        }
      }
    );
  });
}

function settingsToArgs(values) {
  return Object.entries(values || {}).flatMap(([key, value]) => ['--set', `${key}=${value}`]);
}

function registerArgs(register) {
  return register ? ['--register', register] : [];
}

ipcMain.handle('console:view', (_event, { register, probe }) =>
  runApi([...registerArgs(register), 'view', ...(probe ? ['--probe'] : [])])
);

ipcMain.handle('console:templates', () => runApi(['templates']));

ipcMain.handle('console:create', (_event, { register, name, template, values }) =>
  runApi([...registerArgs(register), 'create', name, '--template', template, ...settingsToArgs(values)])
);

ipcMain.handle('console:update', (_event, { register, name, values }) =>
  runApi([...registerArgs(register), 'update', name, ...settingsToArgs(values)])
);

ipcMain.handle('console:remove', (_event, { register, name }) =>
  runApi([...registerArgs(register), 'remove', name])
);

// The OntoGate view is an address the operator declared in their own register.
// Only http(s) is opened, and only in the real browser -- never inside this
// window, which must stay a renderer of local content.
ipcMain.handle('console:open-ontogate', async (_event, url) => {
  const parsed = new URL(url);
  if (parsed.protocol !== 'http:' && parsed.protocol !== 'https:') {
    throw new Error(`refusing to open ${parsed.protocol} -- only http(s)`);
  }
  await shell.openExternal(parsed.toString());
  return true;
});

function createWindow() {
  const window = new BrowserWindow({
    width: 1280,
    height: 820,
    title: 'VPATH platform management console',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
    },
  });

  // This window renders local files only. Anything that tries to navigate it
  // elsewhere is a bug or an attack; either way it is refused.
  window.webContents.setWindowOpenHandler(() => ({ action: 'deny' }));
  window.webContents.on('will-navigate', (event) => event.preventDefault());

  window.loadFile(path.join(__dirname, 'renderer', 'index.html'));
}

app.whenReady().then(() => {
  createWindow();
  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});
