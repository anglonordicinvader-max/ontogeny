const { app, BrowserWindow, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const net = require('net');
const fs = require('fs');
const { autoUpdater } = require('electron-updater');

let mainWindow;
let pythonProcess;
let blenderProcess;
let backendPort;

const PYTHON_EXE = path.join(__dirname, '..', 'backend', 'ontogeny-backend.exe');
const BLENDER_EXE = path.join(__dirname, '..', 'backend', 'blender', 'blender.exe');

autoUpdater.autoDownload = true;
autoUpdater.autoInstallOnAppQuit = true;

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
      '--python', path.join(__dirname, '..', '..', 'backend', 'blender_server.py'),
      '--', '--port', backendPort
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

  const isDev = !fs.existsSync(path.join(__dirname, '..', 'renderer', 'dist', 'index.html'));
  
  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
    mainWindow.webContents.openDevTools();
  } else {
    mainWindow.loadFile(path.join(__dirname, '..', 'renderer', 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function setupAutoUpdater() {
  autoUpdater.on('checking-for-update', () => {
    console.log('Checking for update...');
  });

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
  await startPythonBackend();
  await startBlender();
  createWindow();
  setupAutoUpdater();
  
  autoUpdater.checkForUpdatesAndNotify();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('window-all-closed', () => {
  if (pythonProcess) pythonProcess.kill();
  if (blenderProcess) blenderProcess.kill();
  if (process.platform !== 'darwin') {
    app.quit();
  }
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
