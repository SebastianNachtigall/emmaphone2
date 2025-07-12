const express = require('express');
const https = require('https');
const http = require('http');
const fs = require('fs');
const cors = require('cors');
const path = require('path');
const { Server } = require('socket.io');
const { AccessToken } = require('livekit-server-sdk');

const app = express();
const PORT = process.env.PORT || 3001;
const HTTPS_PORT = process.env.HTTPS_PORT || 3443;

app.use(cors());
app.use(express.json());
app.use(express.static('public'));

// Store connected users for call signaling
const connectedUsers = new Map(); // userId -> socketId
const activeUsers = new Map();    // socketId -> userInfo

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

// Call initiation endpoint
app.post('/api/initiate-call', async (req, res) => {
  try {
    const { fromUser, toUser, contactName } = req.body;
    
    if (!fromUser || !toUser) {
      return res.status(400).json({ error: 'fromUser and toUser are required' });
    }

    // Check if target user is connected
    const targetSocketId = connectedUsers.get(toUser);
    if (!targetSocketId) {
      return res.status(404).json({ error: 'Target user not connected' });
    }

    // Create unique room for this call
    const roomName = `call-${fromUser}-to-${toUser}-${Date.now()}`;
    
    // Generate tokens for both users
    const callerToken = await generateToken(roomName, fromUser);
    const calleeToken = await generateToken(roomName, toUser);

    console.log(`Call initiated from ${fromUser} to ${toUser} in room ${roomName}`);

    // Send call invitation to target user
    io.to(targetSocketId).emit('incoming-call', {
      from: fromUser,
      fromName: fromUser,
      roomName: roomName,
      calleeToken: calleeToken
    });

    res.json({
      success: true,
      roomName: roomName,
      callerToken: callerToken
    });

  } catch (error) {
    console.error('Call initiation failed:', error);
    res.status(500).json({ error: 'Failed to initiate call' });
  }
});

// Helper function to generate tokens
async function generateToken(roomName, participantName) {
  const apiKey = 'APIKeySecret_1234567890abcdef';
  const apiSecret = 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
  
  const at = new AccessToken(apiKey, apiSecret, {
    identity: participantName,
    name: participantName,
  });
  
  at.addGrant({
    room: roomName,
    roomJoin: true,
    canPublish: true,
    canSubscribe: true,
    canPublishData: true
  });

  return await at.toJwt();
}

// Create HTTP server
const httpServer = http.createServer(app);

// Create HTTPS server
let httpsServer;
try {
  const httpsOptions = {
    key: fs.readFileSync(path.join(__dirname, '..', 'ssl', 'key.pem')),
    cert: fs.readFileSync(path.join(__dirname, '..', 'ssl', 'cert.pem'))
  };
  httpsServer = https.createServer(httpsOptions, app);
} catch (error) {
  console.log('HTTPS not available, SSL certificates not found. Using HTTP only.');
}

// Setup Socket.IO on HTTPS server (preferred) or HTTP server
const io = new Server(httpsServer || httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

// Socket.IO connection handling
io.on('connection', (socket) => {
  console.log('User connected:', socket.id);

  // User registration for call signaling
  socket.on('register-user', (userData) => {
    const { userId } = userData;
    connectedUsers.set(userId, socket.id);
    activeUsers.set(socket.id, { userId, connectedAt: new Date() });
    
    console.log(`User ${userId} registered with socket ${socket.id}`);
    
    // Send list of online users (for future contact status)
    socket.emit('user-registered', { 
      success: true, 
      userId: userId,
      onlineUsers: Array.from(connectedUsers.keys())
    });
  });

  // Handle call responses
  socket.on('call-response', (response) => {
    const { accepted, callData } = response;
    
    if (accepted) {
      console.log(`Call accepted by ${callData.to}`);
      // The callee will join the room using the provided token
    } else {
      console.log(`Call rejected by ${callData.to}`);
      // Notify caller that call was rejected
      const callerSocketId = connectedUsers.get(callData.from);
      if (callerSocketId) {
        io.to(callerSocketId).emit('call-rejected', {
          by: callData.to
        });
      }
    }
  });

  // Handle disconnection
  socket.on('disconnect', () => {
    const userInfo = activeUsers.get(socket.id);
    if (userInfo) {
      connectedUsers.delete(userInfo.userId);
      activeUsers.delete(socket.id);
      console.log(`User ${userInfo.userId} disconnected`);
    }
  });
});

// Start servers
httpServer.listen(PORT, () => {
  console.log(`EmmaPhone2 HTTP server running on http://localhost:${PORT}`);
  console.log(`Redirecting to HTTPS...`);
});

if (httpsServer) {
  httpsServer.listen(HTTPS_PORT, () => {
    console.log(`EmmaPhone2 HTTPS server running on https://localhost:${HTTPS_PORT}`);
    console.log(`Use HTTPS URL for WebRTC microphone access!`);
    console.log(`Socket.IO available on both HTTP and HTTPS`);
  });
}