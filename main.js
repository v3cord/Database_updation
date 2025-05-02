const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');

function createWindow() {
  const win = new BrowserWindow({
    width: 800,
    height: 600,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
    },
  });

  win.loadFile('index.html');
}

app.whenReady().then(createWindow);

ipcMain.on('run-script', (event) => {
  const py = spawn('python', ['ig_update.py']);

  py.stdout.on('data', (data) => {
    const lines = data.toString().split(/\r?\n/);
    lines.forEach((line) => {
      if (line.startsWith('PROGRESS:')) {
        const percent = line.replace('PROGRESS:', '').trim();
        event.sender.send('progress-update', parseInt(percent));
      } else if (line.startsWith('SKIPPED_SUMMARY_START')) {
        event.sender.send('skipped-start');
      } else if (line.startsWith('SKIPPED_SUMMARY_END')) {
        event.sender.send('skipped-end');
      } else if (line.startsWith('SKIPPED:')) {
        event.sender.send('skipped-entry', line.replace('SKIPPED:', '').trim());
      }
    });
  });

  py.stderr.on('data', (data) => {
    console.error(`stderr: ${data}`);
  });

  py.on('close', (code) => {
    event.sender.send('script-complete');
  });
});
