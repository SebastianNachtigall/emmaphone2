const express = require('express');
const https = require('https');
const http = require('http');
const fs = require('fs');
const cors = require('cors');
const path = require('path');
const session = require('express-session');
const RedisStore = require('connect-redis')(session);
const redis = require('redis');
const { Server } = require('socket.io');
const { AccessToken } = require('livekit-server-sdk');
const DatabaseManager = require('./database');

const app = express();
const PORT = process.env.PORT || 3001;
const HTTPS_PORT = process.env.HTTPS_PORT || 3443;

app.use(cors());
app.use(express.json());

// Initialize database
const db = new DatabaseManager();

// Initialize Redis client (v3.x API)
let redisClient;
if (process.env.REDIS_URL) {
  redisClient = redis.createClient(process.env.REDIS_URL);
} else {
  redisClient = redis.createClient({
    host: process.env.REDIS_HOST || 'redis',
    port: process.env.REDIS_PORT || 6379
  });
}

redisClient.on('error', (err) => {
  console.error('Redis client error:', err);
});

redisClient.on('connect', () => {
  console.log('Connected to Redis for session storage');
});

// Session configuration with optional Redis store
const sessionConfig = {
  secret: process.env.SESSION_SECRET || 'your-secret-key-change-this',
  resave: false,
  saveUninitialized: false,
  cookie: {
    secure: false, // Keep false for Railway HTTP deployment
    httpOnly: true,
    maxAge: 24 * 60 * 60 * 1000 // 24 hours
  }
};

// Use Redis store if available, otherwise use memory store
if (process.env.REDIS_URL || process.env.REDIS_HOST) {
  sessionConfig.store = new RedisStore({ client: redisClient });
  console.log('Using Redis session store');
} else {
  console.log('Using memory session store (not recommended for production)');
}

app.use(session(sessionConfig));

// Create middleware for serving static files with auth protection (AFTER session middleware)
const serveAuthenticatedStatic = (req, res, next) => {
  // Skip middleware for API routes and root route - they handle their own logic
  if (req.path.startsWith('/api/') || req.path.startsWith('/socket.io/') || req.path === '/') {
    return next();
  }
  
  console.log(`🔍 Static middleware: ${req.path} - Session: ${!!req.session} - User: ${req.session?.user?.username || 'none'}`);
  
  // Allow public assets that don't need authentication
  const publicPaths = [
    '/css/auth.css',
    '/css/style.css', // Needed for login page base styles
    '/js/auth.js',
    '/login.html',
    '/favicon.ico'
  ];
  
  // Allow all JS/CSS files for authenticated users, but check session first
  const isStaticAsset = req.path.endsWith('.js') || req.path.endsWith('.css') || req.path.endsWith('.html');
  
  if (isStaticAsset && req.session && req.session.user) {
    console.log(`✅ Serving authenticated asset: ${req.path}`);
    return express.static('public')(req, res, next);
  }
  
  const isPublicPath = publicPaths.some(path => req.path === path);
  
  if (isPublicPath) {
    console.log(`🌐 Serving public asset: ${req.path}`);
    return express.static('public')(req, res, next);
  }
  
  // For all other static files, check authentication
  if (!req.session || !req.session.user) {
    console.log(`🔀 Redirecting unauthenticated request: ${req.path}`);
    return res.redirect('/login.html');
  }
  
  console.log(`📄 Serving other authenticated file: ${req.path}`);
  return express.static('public')(req, res, next);
};

app.use(serveAuthenticatedStatic);

// Authentication middleware
function requireAuth(req, res, next) {
  console.log('Auth check - Session:', !!req.session, 'User:', !!req.session?.user, 'SessionID:', req.sessionID);
  console.log('Session contents:', req.session);
  if (req.session && req.session.user) {
    return next();
  } else {
    return res.status(401).json({ error: 'Authentication required' });
  }
}

// Optional auth middleware (allows both authenticated and unauthenticated)
function optionalAuth(req, res, next) {
  req.user = req.session && req.session.user ? req.session.user : null;
  next();
}

// Store connected users for call signaling
const connectedUsers = new Map(); // userId -> socketId
const activeUsers = new Map();    // socketId -> userInfo

// Routes
app.get('/', optionalAuth, (req, res) => {
  console.log('📄 GET / - Session exists:', !!req.session);
  console.log('📄 GET / - Session user:', req.session?.user?.username || 'none');
  console.log('📄 GET / - req.user set by middleware:', !!req.user);
  
  // If user is not authenticated, redirect to login
  if (!req.user) {
    console.log('🔀 Redirecting to login page');
    return res.redirect('/login.html');
  }
  console.log('✅ Serving index.html to authenticated user:', req.user.username);
  res.sendFile(path.join(__dirname, '..', 'public', 'index.html'));
});

// Authentication routes
app.post('/api/auth/register', async (req, res) => {
  try {
    const { username, displayName, password, pin, avatarColor } = req.body;
    
    if (!username || !displayName || !password) {
      return res.status(400).json({ error: 'Username, display name, and password are required' });
    }
    
    const user = await db.createUser(username, displayName, password, pin, avatarColor);
    res.json({ success: true, user: { id: user.id, username: user.username, displayName: user.displayName } });
    
  } catch (error) {
    console.error('Registration error:', error);
    if (error.message === 'Username already exists') {
      res.status(409).json({ error: 'Username already exists' });
    } else {
      res.status(500).json({ error: 'Registration failed' });
    }
  }
});

app.post('/api/auth/login', async (req, res) => {
  try {
    const { username, password } = req.body;
    console.log('Login attempt for:', username);
    
    if (!username || !password) {
      return res.status(400).json({ error: 'Username and password are required' });
    }
    
    const user = await db.validateUser(username, password);
    if (!user) {
      console.log('Login failed for:', username);
      return res.status(401).json({ error: 'Invalid username or password' });
    }
    
    // Store user in session
    req.session.user = user;
    console.log('User logged in:', user.username, 'Session ID:', req.sessionID);
    
    res.json({ 
      success: true, 
      user: {
        id: user.id,
        username: user.username,
        displayName: user.displayName,
        avatarColor: user.avatarColor
      }
    });
    
  } catch (error) {
    console.error('Login error:', error);
    res.status(500).json({ error: 'Login failed' });
  }
});

app.post('/api/auth/logout', (req, res) => {
  req.session.destroy((err) => {
    if (err) {
      return res.status(500).json({ error: 'Logout failed' });
    }
    res.json({ success: true });
  });
});

app.get('/api/auth/me', requireAuth, (req, res) => {
  console.log('GET /api/auth/me - User:', req.session.user.username);
  res.json(req.session.user);
});

// Health check endpoint
app.get('/health', (req, res) => {
  res.status(200).json({ status: 'ok', timestamp: new Date().toISOString() });
});

// LiveKit token generation endpoint
app.post('/api/livekit-token', requireAuth, async (req, res) => {
  try {
    const { roomName, participantName } = req.body;
    
    if (!roomName || !participantName) {
      return res.status(400).json({ error: 'roomName and participantName are required' });
    }

    // LiveKit credentials from our configuration
    const apiKey = process.env.LIVEKIT_API_KEY || 'APIKeySecret_1234567890abcdef';
    const apiSecret = process.env.LIVEKIT_API_SECRET || 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
    
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
      wsUrl: process.env.LIVEKIT_URL || 'ws://localhost:7880'
    });
    
  } catch (error) {
    console.error('Token generation failed:', error);
    res.status(500).json({ error: 'Failed to generate token' });
  }
});

// User contacts endpoint
app.get('/api/contacts', requireAuth, (req, res) => {
  try {
    const contacts = db.getUserContacts(req.session.user.id);
    res.json(contacts);
  } catch (error) {
    console.error('Error fetching contacts:', error);
    res.status(500).json({ error: 'Failed to fetch contacts' });
  }
});

// Add new contact
app.post('/api/contacts', requireAuth, (req, res) => {
  try {
    const { contactUserId, displayName, speedDialPosition } = req.body;
    
    if (!contactUserId) {
      return res.status(400).json({ error: 'Contact user ID is required' });
    }
    
    // Prevent adding yourself
    if (contactUserId === req.session.user.id) {
      return res.status(400).json({ error: 'Cannot add yourself as a contact' });
    }
    
    // Check if contact already exists
    const existingContacts = db.getUserContacts(req.session.user.id);
    if (existingContacts.some(c => c.contact_user_id === contactUserId)) {
      return res.status(409).json({ error: 'Contact already exists' });
    }
    
    // Validate speed dial position
    if (speedDialPosition && (speedDialPosition < 1 || speedDialPosition > 4)) {
      return res.status(400).json({ error: 'Speed dial position must be between 1 and 4' });
    }
    
    // Check if speed dial position is already taken
    if (speedDialPosition && existingContacts.some(c => c.speed_dial_position === speedDialPosition)) {
      return res.status(409).json({ error: 'Speed dial position already taken' });
    }
    
    const contactId = db.addContact(req.session.user.id, contactUserId, displayName, speedDialPosition);
    const newContact = db.getUserContacts(req.session.user.id).find(c => c.id === contactId);
    
    res.json({ success: true, contact: newContact });
  } catch (error) {
    console.error('Error adding contact:', error);
    res.status(500).json({ error: 'Failed to add contact' });
  }
});

// Update contact
app.put('/api/contacts/:id', requireAuth, (req, res) => {
  try {
    const contactId = parseInt(req.params.id);
    const { displayName, speedDialPosition } = req.body;
    
    if (isNaN(contactId)) {
      return res.status(400).json({ error: 'Invalid contact ID' });
    }
    
    // Check if contact belongs to user
    const existingContacts = db.getUserContacts(req.session.user.id);
    const contact = existingContacts.find(c => c.id === contactId);
    if (!contact) {
      return res.status(404).json({ error: 'Contact not found' });
    }
    
    // Validate speed dial position if provided
    if (speedDialPosition !== undefined) {
      if (speedDialPosition !== null && (speedDialPosition < 1 || speedDialPosition > 4)) {
        return res.status(400).json({ error: 'Speed dial position must be between 1 and 4' });
      }
      
      // Check if new position is already taken by another contact
      if (speedDialPosition && existingContacts.some(c => c.id !== contactId && c.speed_dial_position === speedDialPosition)) {
        return res.status(409).json({ error: 'Speed dial position already taken' });
      }
    }
    
    const success = db.updateContact(contactId, req.session.user.id, displayName, speedDialPosition);
    if (success) {
      const updatedContact = db.getUserContacts(req.session.user.id).find(c => c.id === contactId);
      res.json({ success: true, contact: updatedContact });
    } else {
      res.status(500).json({ error: 'Failed to update contact' });
    }
  } catch (error) {
    console.error('Error updating contact:', error);
    res.status(500).json({ error: 'Failed to update contact' });
  }
});

// Delete contact
app.delete('/api/contacts/:id', requireAuth, (req, res) => {
  try {
    const contactId = parseInt(req.params.id);
    
    if (isNaN(contactId)) {
      return res.status(400).json({ error: 'Invalid contact ID' });
    }
    
    // Check if contact belongs to user
    const existingContacts = db.getUserContacts(req.session.user.id);
    const contact = existingContacts.find(c => c.id === contactId);
    if (!contact) {
      return res.status(404).json({ error: 'Contact not found' });
    }
    
    const success = db.removeContact(contactId, req.session.user.id);
    if (success) {
      res.json({ success: true });
    } else {
      res.status(500).json({ error: 'Failed to remove contact' });
    }
  } catch (error) {
    console.error('Error removing contact:', error);
    res.status(500).json({ error: 'Failed to remove contact' });
  }
});

// Search users for adding as contacts
app.get('/api/users/search', requireAuth, (req, res) => {
  try {
    const { q } = req.query;
    
    if (!q || q.trim().length < 2) {
      return res.status(400).json({ error: 'Search query must be at least 2 characters' });
    }
    
    const users = db.searchUsers(q.trim(), req.session.user.id);
    res.json(users);
  } catch (error) {
    console.error('Error searching users:', error);
    res.status(500).json({ error: 'Failed to search users' });
  }
});

// Friend group endpoints
app.get('/api/groups', requireAuth, (req, res) => {
  try {
    const groups = db.getUserGroups(req.session.user.id);
    res.json(groups);
  } catch (error) {
    console.error('Error fetching groups:', error);
    res.status(500).json({ error: 'Failed to fetch groups' });
  }
});

app.post('/api/groups', requireAuth, (req, res) => {
  try {
    const { name, description } = req.body;
    
    if (!name || name.trim().length === 0) {
      return res.status(400).json({ error: 'Group name is required' });
    }
    
    const result = db.createFriendGroup(name.trim(), description?.trim(), req.session.user.id);
    res.json({ 
      success: true, 
      group: { 
        id: result.id, 
        name: name.trim(), 
        description: description?.trim(), 
        inviteCode: result.inviteCode,
        isAdmin: true 
      }
    });
  } catch (error) {
    console.error('Error creating group:', error);
    res.status(500).json({ error: 'Failed to create group' });
  }
});

app.post('/api/groups/join', requireAuth, (req, res) => {
  try {
    const { inviteCode } = req.body;
    
    if (!inviteCode || inviteCode.trim().length === 0) {
      return res.status(400).json({ error: 'Invite code is required' });
    }
    
    const result = db.joinGroupByInviteCode(req.session.user.id, inviteCode.trim().toUpperCase());
    res.json({ success: true, group: result });
  } catch (error) {
    console.error('Error joining group:', error);
    if (error.message === 'Group not found') {
      res.status(404).json({ error: 'Invalid invite code' });
    } else if (error.message === 'Already a member') {
      res.status(409).json({ error: 'Already a member of this group' });
    } else {
      res.status(500).json({ error: 'Failed to join group' });
    }
  }
});

app.get('/api/groups/:groupId/members', requireAuth, (req, res) => {
  try {
    const groupId = parseInt(req.params.groupId);
    if (isNaN(groupId)) {
      return res.status(400).json({ error: 'Invalid group ID' });
    }
    
    const members = db.getGroupMembers(groupId, req.session.user.id);
    res.json(members);
  } catch (error) {
    console.error('Error fetching group members:', error);
    if (error.message === 'Access denied') {
      res.status(403).json({ error: 'Access denied' });
    } else {
      res.status(500).json({ error: 'Failed to fetch group members' });
    }
  }
});

// Call initiation endpoint
app.post('/api/initiate-call', requireAuth, async (req, res) => {
  try {
    const { toUser, contactName } = req.body;
    const fromUser = req.session.user.id; // Use authenticated user ID
    
    if (!fromUser || !toUser) {
      return res.status(400).json({ error: 'fromUser and toUser are required' });
    }

    // Check if target user is connected
    const targetSocketId = connectedUsers.get(toUser);
    if (!targetSocketId) {
      return res.status(404).json({ error: 'Target user not connected' });
    }

    // Get target user's username from database
    const targetUser = db.getUserById(toUser);
    if (!targetUser) {
      return res.status(404).json({ error: 'Target user not found' });
    }

    // Create unique room for this call
    const roomName = `call-${fromUser}-to-${toUser}-${Date.now()}`;
    
    // Generate tokens for both users
    const callerToken = await generateToken(roomName, req.session.user.username);
    const calleeToken = await generateToken(roomName, targetUser.username);
    
    // Log the call
    const callLogId = db.logCall(fromUser, toUser, roomName, 'initiated');

    console.log(`Call initiated from ${fromUser} to ${toUser} in room ${roomName}`);

    // Send call invitation to target user
    io.to(targetSocketId).emit('incoming-call', {
      from: fromUser,
      fromName: req.session.user.displayName || req.session.user.username,
      roomName: roomName,
      calleeToken: calleeToken,
      callLogId: callLogId,
      wsUrl: process.env.LIVEKIT_URL || 'ws://localhost:7880'
    });

    res.json({
      success: true,
      roomName: roomName,
      callerToken: callerToken,
      wsUrl: process.env.LIVEKIT_URL || 'ws://localhost:7880'
    });

  } catch (error) {
    console.error('Call initiation failed:', error);
    res.status(500).json({ error: 'Failed to initiate call' });
  }
});

// Helper function to generate tokens
async function generateToken(roomName, participantName) {
  const apiKey = process.env.LIVEKIT_API_KEY || 'APIKeySecret_1234567890abcdef';
  const apiSecret = process.env.LIVEKIT_API_SECRET || 'abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890';
  
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

// Admin endpoints for user management
app.get('/api/admin/users', requireAuth, (req, res) => {
  try {
    // Get all users with stats
    const users = db.getAllUsers();
    const stats = {
      total: users.length,
      active: users.filter(u => u.is_active).length,
      pi_devices: users.filter(u => u.username.startsWith('pi_') || u.username.toLowerCase().includes('pi')).length
    };
    
    res.json({ users, stats });
  } catch (error) {
    console.error('Error fetching users for admin:', error);
    res.status(500).json({ error: 'Failed to fetch users' });
  }
});

app.delete('/api/admin/users/:userId', requireAuth, (req, res) => {
  try {
    const userId = parseInt(req.params.userId);
    
    if (isNaN(userId)) {
      return res.status(400).json({ error: 'Invalid user ID' });
    }
    
    // Don't allow deleting yourself
    if (userId === req.session.user.id) {
      return res.status(400).json({ error: 'Cannot delete yourself' });
    }
    
    const success = db.deleteUser(userId);
    if (success) {
      console.log(`Admin ${req.session.user.username} deleted user ID ${userId}`);
      res.json({ success: true });
    } else {
      res.status(404).json({ error: 'User not found' });
    }
  } catch (error) {
    console.error('Error deleting user:', error);
    res.status(500).json({ error: 'Failed to delete user' });
  }
});

app.post('/api/admin/users/:userId/deactivate', requireAuth, (req, res) => {
  try {
    const userId = parseInt(req.params.userId);
    
    if (isNaN(userId)) {
      return res.status(400).json({ error: 'Invalid user ID' });
    }
    
    // Don't allow deactivating yourself
    if (userId === req.session.user.id) {
      return res.status(400).json({ error: 'Cannot deactivate yourself' });
    }
    
    const success = db.updateUserStatus(userId, false);
    if (success) {
      console.log(`Admin ${req.session.user.username} deactivated user ID ${userId}`);
      res.json({ success: true });
    } else {
      res.status(404).json({ error: 'User not found' });
    }
  } catch (error) {
    console.error('Error deactivating user:', error);
    res.status(500).json({ error: 'Failed to deactivate user' });
  }
});

app.post('/api/admin/users/:userId/activate', requireAuth, (req, res) => {
  try {
    const userId = parseInt(req.params.userId);
    
    if (isNaN(userId)) {
      return res.status(400).json({ error: 'Invalid user ID' });
    }
    
    const success = db.updateUserStatus(userId, true);
    if (success) {
      console.log(`Admin ${req.session.user.username} activated user ID ${userId}`);
      res.json({ success: true });
    } else {
      res.status(404).json({ error: 'User not found' });
    }
  } catch (error) {
    console.error('Error activating user:', error);
    res.status(500).json({ error: 'Failed to activate user' });
  }
});

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

// Setup Socket.IO on HTTP server (HTTPS certs not available in dev)
const io = new Server(httpServer, {
  cors: {
    origin: "*",
    methods: ["GET", "POST"]
  }
});

console.log('Socket.IO server attached to HTTP server on port', PORT);

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