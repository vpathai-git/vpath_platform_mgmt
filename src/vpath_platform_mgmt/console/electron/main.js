// The shell's main process: window, and one way to reach the Python side.
//
// Every answer this shell shows comes from `vpath_platform_mgmt.console.api
// --json`, spawned here. The shell computes nothing about instances itself --
// if it did, the window could disagree with what `make check` verified.

'use strict';

const { app, BrowserWindow, ipcMain, shell } = require('electron');
const { execFile } = require('node:child_process');
const path = require('node:path');

// <repo>/src/vpath_platform_mgmt/console/electron -> <repo>
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

// Run one api command and return its parsed JSON. A non-zero exit is turned
// into a rejection carrying the api's own stderr, so the window shows the
// message the tooling wrote rather than a generic failure.
function runApi(args) {
  return new Promise((resolve, reject) => {
    const argv = ['-m', MODULE, '--json', ...args];
    const env = { ...process.env };
    env.PYTHONPATH = env.PYTHONPATH ? `${SRC_DIR}${path.delimiter}${env.PYTHONPATH}` : SRC_DIR;

    execFile(
      pythonExecutable(),
      argv,
      { cwd: REPO_ROOT, env, maxBuffer: 32 * 1024 * 1024 },
      (error, stdout, stderr) => {
        if (error && typeof error.code !== 'number') {
          reject(new Error(`could not start ${pythonExecutable()}: ${error.message}`));
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
