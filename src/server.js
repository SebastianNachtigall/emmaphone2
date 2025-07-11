const express = require('express');
const https = require('https');
const fs = require('fs');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 3001;
const HTTPS_PORT = process.env.HTTPS_PORT || 3443;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// HTTP server (redirect to HTTPS)
app.listen(PORT, () => {
  console.log(`EmmaPhone2 HTTP server running on http://localhost:${PORT}`);
  console.log(`Redirecting to HTTPS...`);
});

// HTTPS server
try {
  const httpsOptions = {
    key: fs.readFileSync(path.join(__dirname, '..', 'ssl', 'key.pem')),
    cert: fs.readFileSync(path.join(__dirname, '..', 'ssl', 'cert.pem'))
  };

  https.createServer(httpsOptions, app).listen(HTTPS_PORT, () => {
    console.log(`EmmaPhone2 HTTPS server running on https://localhost:${HTTPS_PORT}`);
    console.log(`Use HTTPS URL for WebRTC microphone access!`);
  });
} catch (error) {
  console.log('HTTPS not available, SSL certificates not found. Using HTTP only.');
}