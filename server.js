const express = require('express');
const { spawn } = require('child_process');
const path = require('path');
const cors = require('cors');
const EventEmitter = require('events');
const logEmitter = new EventEmitter();
const { createProxyMiddleware } = require('http-proxy-middleware');
// 1. Initialize the App
const app = express();
const PORT = 5000;

// 2. Serve Static Files (Your React App)
// Make sure 'dist' matches your actual build folder name!
const DIST_DIR = path.join(__dirname, 'panel/dist');
const SETTINGS_FILE = path.join(__dirname, 'leafcore_iot_backend/source_files/settings_config.json');
app.use(express.static(DIST_DIR));
app.get('/settings_config.json', (req, res) => {
  res.sendFile(SETTINGS_FILE);
});
app.use(cors());
app.use(
  ['/api/sensors', '/api/watering', '/api/status', '/api/control', '/api/settings', '/api/watering-timer'],
  createProxyMiddleware({
    target: 'http://localhost:5001', // Localhost internal IP
    changeOrigin: true,
  })
);
// 3. API Endpoint: Start Bluetooth Service
app.post('/api/bluetooth/start', (req, res) => {
    console.log('Attempting to start Bluetooth Service...');

    // --- CONFIGURATION ---
    const WORK_DIR = '/home/orangepi/Desktop/panel/leafcore_iot_backend';
    const PYTHON_EXEC = path.join(WORK_DIR, '.venv/bin/python');
    const SCRIPT_FILE = path.join(WORK_DIR, 'bluetooth_service.py');
    // ---------------------
    spawn('sudo', ['pkill', '-f', 'bluetooth_service.py']);
    console.log(`Running: sudo ${PYTHON_EXEC} -u ${SCRIPT_FILE}`);    
    try {
        const pythonProcess = spawn('sudo', [PYTHON_EXEC, '-u', SCRIPT_FILE], {
            cwd: WORK_DIR,
            detached: true,
            // CHANGED: 'inherit' -> 'pipe' so we can capture the logs
            stdio: ['ignore', 'pipe', 'pipe'] 
        });

        // Capture Standard Output
        pythonProcess.stdout.on('data', (data) => {
            const msg = data.toString();
            console.log(`[PY-OUT]: ${msg}`);
            logEmitter.emit('log', msg); 
        });

        // Capture Error Output
        pythonProcess.stderr.on('data', (data) => {
            const msg = data.toString();
            console.error(`[PY-ERR]: ${msg}`);
            logEmitter.emit('log', msg);
        });
        pythonProcess.unref();
        res.status(200).json({ message: 'Bluetooth Service Started' });
    } catch (error) {
        console.error("Spawn error:", error);
        res.status(500).json({ error: 'Failed to spawn process' });
    }
});

app.get('/api/bluetooth-logs', (req, res) => {
    res.setHeader('Content-Type', 'text/event-stream');
    res.setHeader('Cache-Control', 'no-cache');
    res.setHeader('Connection', 'keep-alive');

    const sendLog = (msg) => {
        // Send data in SSE format: "data: <message>\n\n"
        res.write(`data: ${JSON.stringify({ message: msg })}\n\n`);
    };

    // Attach listener
    logEmitter.on('log', sendLog);

    // Clean up when client disconnects
    req.on('close', () => {
        logEmitter.off('log', sendLog);
    });
});

// 4. Fallback Route (Required for React Router)
// Redirects any unknown request back to index.html so React can handle it
app.get(/(.*)/, (req, res) => {
    res.sendFile(path.join(DIST_DIR, 'index.html'));
});

// 5. Start the Server
app.listen(PORT, () => {
    console.log(`Smart Server running at http://localhost:${PORT}`);
});
