const express = require('express');
const https = require('https');
const fs = require('fs');
const cors = require('cors');
const path = require('path');
const { AccessToken } = require('livekit-server-sdk');

const app = express();
const PORT = process.env.PORT || 3001;
const HTTPS_PORT = process.env.HTTPS_PORT || 3443;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// LiveKit token generation endpoint
app.post('/api/livekit-token', async (req, res) => {
  try {
    const { roomName, participantName } = req.body;
    
    if (!roomName || !participantName) {
      return res.status(400).json({ error: 'roomName and participantName are required' });
    }

    // LiveKit credentials from our configuration
    const apiKey = 'APIKeySecret_1234567890abcdef';
    const apiSecret = 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
    
    const at = new AccessToken(apiKey, apiSecret, {
      identity: participantName,
      name: participantName,
    });
    
    // Grant permissions for audio calling
    at.addGrant({
      room: roomName,
      roomJoin: true,
      canPublish: true,
      canSubscribe: true,
      canPublishData: true
    });

    const token = await at.toJwt();
    
    console.log('Generated LiveKit token for:', participantName, 'in room:', roomName);
    console.log('Token type:', typeof token);
    console.log('Token value:', token);
    
    res.json({ 
      token,
      roomName,
      participantName,
      wsUrl: 'ws://localhost:7880'
    });
    
  } catch (error) {
    console.error('Token generation failed:', error);
    res.status(500).json({ error: 'Failed to generate token' });
  }
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