// The only bridge between the window and the machine.
//
// The renderer gets these five verbs and nothing else: no filesystem, no
// child processes, no Node. Every one of them is a command the Python api
// already exposes, so the shell cannot invent an operation the tested code
// does not have.

'use strict';

const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('vpath', {
  view: (options) => ipcRenderer.invoke('console:view', options || {}),
  templates: () => ipcRenderer.invoke('console:templates'),
  create: (options) => ipcRenderer.invoke('console:create', options),
  update: (options) => ipcRenderer.invoke('console:update', options),
  remove: (options) => ipcRenderer.invoke('console:remove', options),
  openOntogate: (url) => ipcRenderer.invoke('console:open-ontogate', url),
});
