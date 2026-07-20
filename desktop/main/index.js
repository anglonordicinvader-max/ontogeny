const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

let mainWindow;
let pythonProcess;
let blenderProcess;
let mujocoProcess;
let backendPort;

// Lazy-evaluated environment checks - avoid module-load-time issues in ASAR
function getIsDev() {
  return !isPackaged;
}

function getIsPortable() {
  return isPackaged && !fs.existsSync(path.join(process.resourcesPath, 'app-update.yml'));
}

const isPackaged = !!process.resourcesPath;

const PYTHON_EXE = isPackaged
  ? path.join(process.resourcesPath, 'backend', 'ontogeny-backend.exe')
  : path.join(__dirname, '..', 'backend', 'ontogeny-backend.exe');
const BLENDER_EXE = isPackaged
  ? path.join(process.resourcesPath, 'backend', 'blender', 'blender.exe')
  : 'C:\\Program Files\\Blender Foundation\\Blender 5.2\\blender.exe';

const MUJOCO_SCRIPT = isPackaged
  ? path.join(process.resourcesPath, 'backend', 'mujoco_simulation.py')
  : path.join(__dirname, '..', '..', 'backend', 'mujoco_simulation.py');

// Configure auto-updater based on environment
function configureAutoUpdater() {
  const isDev = !isPackaged;
  const isPortable = isPackaged && !fs.existsSync(path.join(process.resourcesPath, 'app-update.yml'));
  
  if (!isDev && !isPortable) {
    autoUpdater.autoDownload = true;
    autoUpdater.autoInstallOnAppQuit = true;
  } else {
    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = false;
    autoUpdater.checkForUpdatesAndNotify = () => Promise.resolve();
    autoUpdater.checkForUpdates = () => Promise.resolve();
  }
}

configureAutoUpdater();

function findAvailablePort() {
  return new Promise((resolve, reject) => {
    const server = net.createServer();
    server.listen(0, '127.0.0.1', () => {
      const port = server.address().port;
      server.close(() => resolve(port));
    });
    server.on('error', reject);
  });
}

async function startPythonBackend() {
  backendPort = await findAvailablePort();
  
  if (fs.existsSync(PYTHON_EXE)) {
    pythonProcess = spawn(PYTHON_EXE, ['--port', backendPort], {
      stdio: ['pipe', 'pipe', 'pipe']
    });
  } else {
    console.warn('Python backend not found, using development mode');
    pythonProcess = spawn('python', ['-m', 'uvicorn', 'backend.main:app', '--port', backendPort], {
      cwd: path.join(__dirname, '..', '..'),
      stdio: ['pipe', 'pipe', 'pipe']
    });
  }

  pythonProcess.stdout.on('data', (data) => {
    console.log(`Python: ${data}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`Python Error: ${data}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python process exited with code ${code}`);
  });

  return backendPort;
}

async function startBlender() {
  if (fs.existsSync(BLENDER_EXE)) {
    blenderProcess = spawn(BLENDER_EXE, [
      '--background',
      '--python', path.join(__dirname, '..', '..', 'backend', 'blender_simulation.py'),
      '--', '--port', String(backendPort + 1)
    ], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    blenderProcess.stdout.on('data', (data) => {
      console.log(`Blender: ${data}`);
    });

    blenderProcess.stderr.on('data', (data) => {
      console.error(`Blender Error: ${data}`);
    });
  }
}

async function startMuJoCo() {
  if (fs.existsSync(MUJOCO_SCRIPT)) {
    const pythonExe = fs.existsSync(PYTHON_EXE) ? PYTHON_EXE : 'python';
    const modelArg = process.env.MUJOCO_MODEL || 'g1';
    mujocoProcess = spawn(pythonExe, [
      MUJOCO_SCRIPT,
      '--port', String(backendPort + 2),
      '--model', modelArg
    ], {
      stdio: ['pipe', 'pipe', 'pipe']
    });

    mujocoProcess.stdout.on('data', (data) => {
      console.log(`MuJoCo: ${data}`);
    });

    mujocoProcess.stderr.on('data', (data) => {
      console.error(`MuJoCo Error: ${data}`);
    });
  }
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1920,
    height: 1080,
    minWidth: 1200,
    minHeight: 800,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#0a0a0a',
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload', 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  // Debug: log all renderer console messages to main process
  mainWindow.webContents.on('console-message', (event, level, message, line, sourceId) => {
    console.log(`[Renderer ${level}] ${sourceId}:${line} - ${message}`);
  });

  mainWindow.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {
    console.error(`Failed to load: ${validatedURL} - ${errorCode}: ${errorDescription}`);
  });

  mainWindow.webContents.on('did-finish-load', () => {
    console.log('Renderer finished loading');
  });

  mainWindow.webContents.on('render-process-gone', (event, details) => {
    console.error('Render process gone:', details);
  });

  mainWindow.webContents.on('unresponsive', () => {
    console.error('Renderer unresponsive');
  });

  const useDev = process.env.NODE_ENV === 'development' || process.argv.includes('--dev');
  
  if (useDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    const indexPath = path.join(__dirname, '..', 'renderer', 'dist', 'index.html');
    console.log('Loading production index.html from:', indexPath);
    console.log('File exists:', fs.existsSync(indexPath));
    mainWindow.loadFile(indexPath);
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function setupAutoUpdater() {
  autoUpdater.on('update-available', (info) => {
    console.log('Update available:', info.version);
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Available',
      message: `A new version ${info.version} is available. It will be downloaded automatically.`,
      buttons: ['OK']
    });
  });

  autoUpdater.on('update-not-available', () => {
    console.log('No update available');
  });

  autoUpdater.on('download-progress', (progress) => {
    console.log(`Download speed: ${progress.bytesPerSecond} - ${progress.percent}%`);
  });

  autoUpdater.on('update-downloaded', (info) => {
    console.log('Update downloaded:', info.version);
    dialog.showMessageBox(mainWindow, {
      type: 'info',
      title: 'Update Ready',
      message: 'Update downloaded. The application will restart to apply the update.',
      buttons: ['Restart', 'Later']
    }).then((result) => {
      if (result.response === 0) {
        autoUpdater.quitAndInstall();
      }
    });
  });

  autoUpdater.on('error', (error) => {
    console.error('Auto-updater error:', error);
  });
}

app.whenReady().then(async () => {
  const simulate = process.argv.includes('--simulate');
  if (simulate) {
    backendPort = 8765;
    console.log('[SIM] Simulation mode — using port 8765, skipping Python backend');
  } else {
    await startPythonBackend();
  }
  await startBlender();
  await startMuJoCo();
  createWindow();
  setupAutoUpdater();
  
  // Only check for updates in production (packaged, not portable)
  if (!isPackaged || (isPackaged && !fs.existsSync(path.join(process.resourcesPath, 'app-update.yml')))) {
    // Skip update check for dev and portable
  } else {
    try {
      await autoUpdater.checkForUpdatesAndNotify();
    } catch (error) {
      console.error('Auto-updater check failed (non-fatal):', error.message);
    }
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill();
  if (blenderProcess) blenderProcess.kill();
  if (mujocoProcess) mujocoProcess.kill();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

// Global error handlers
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
  console.error('Unhandled Rejection at:', promise, 'reason:', reason);
});

ipcMain.handle('get-backend-port', () => backendPort);

ipcMain.on('window-minimize', () => mainWindow?.minimize());
ipcMain.on('window-maximize', () => {
  if (mainWindow?.isMaximized()) {
    mainWindow.unmaximize();
  } else {
    mainWindow?.maximize();
  }
});
ipcMain.on('window-close', () => mainWindow?.close());