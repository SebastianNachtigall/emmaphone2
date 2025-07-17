# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EmmaPhone2 is a kid-friendly WebRTC calling application built with LiveKit for real-time audio communication. The project is designed for eventual deployment on Raspberry Pi hardware but currently runs as a web application deployed on Railway.

## Development Commands

### Setup and Installation
```bash
npm install                                    # Install dependencies
docker compose -f docker-compose-livekit.yml up -d  # Start LiveKit services
```

### Development
```bash
npm run dev                                    # Start development server with nodemon
npm start                                      # Start production server
```

### Docker Deployment
```bash
# Development environment
docker compose -f docker-compose.dev.yml up -d

# Production environment  
docker compose up -d

# LiveKit infrastructure only
docker compose -f docker-compose-livekit.yml up -d
```

### Database Operations
- Database auto-initializes from `database/schema.sql`
- Demo users are created automatically (emma, noah, olivia, liam - password: demo123)
- Database file location: `./data/db/emmaphone.db` (or `DB_PATH` env var)

## Architecture

### Refactored Structure (Current)
```
emmaphone2/
├── web/                    # Web application (Node.js/Express)
│   ├── src/               # Server code (database.js, server.js)
│   ├── public/            # Frontend (HTML, CSS, JS)
│   ├── package.json       # Web app dependencies
│   └── package-lock.json  # Lock file for Docker builds
├── pi/                     # Raspberry Pi components
│   ├── src/               # Pi-specific code
│   ├── setup-wizard/      # WiFi setup interface
│   ├── hardware/          # GPIO, audio drivers
│   └── systemd/           # Service files
├── shared/                 # Shared code between web and pi
│   ├── auth/              # Authentication logic
│   ├── api/               # API interfaces
│   └── types/             # TypeScript definitions
├── services/livekit/       # LiveKit WebRTC service
└── docker-compose*.yml    # Container orchestration
```

**Note:** The repository currently maintains both old (root level) and new (web/) structures during the migration transition period. Docker builds use the new `web/` directory structure.

### Key Components

**Backend (web/src/server.js)**
- Express.js server with HTTPS/HTTP support
- Session-based authentication with Redis store
- LiveKit JWT token generation
- Socket.IO for real-time call signaling
- RESTful API for user/contact management

**Database (web/src/database.js)**
- SQLite with better-sqlite3
- User accounts, contacts, friend groups
- Call logging and history
- Automatic demo user creation

**Frontend (web/public/)**
- Vanilla JavaScript with LiveKit Web SDK
- Kid-friendly UI with large speed dial buttons
- Real-time audio calling interface
- Authentication forms

**LiveKit Integration**
- WebRTC server for audio communication
- SIP bridge support for traditional phone calls
- Redis for session coordination
- JWT token-based room access

## Railway Deployment

### Current Setup
- **Production**: Deployed from `main` branch with Docker containers
- **Build**: Uses `docker/web/Dockerfile` with `web/` directory structure
- **Testing**: Successfully tested with refactored structure

### Railway Configuration
- Builds from `docker/web/Dockerfile`
- Web service exposed on ports 3001 (HTTP) and 3443 (HTTPS)
- LiveKit service on port 7880
- Redis service on port 6379
- Persistent volumes for database and Redis data

### Docker Build Process
The Dockerfile copies from the refactored structure:
```dockerfile
COPY web/package*.json ./
COPY web/src/ ./src/
COPY web/public/ ./public/
COPY web/database/ ./database/
```

## Environment Variables

```bash
# Server Configuration
PORT=3001                   # HTTP port
HTTPS_PORT=3443            # HTTPS port  
NODE_ENV=production        # Environment mode

# LiveKit Configuration
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=APIKeySecret_1234567890abcdef
LIVEKIT_API_SECRET=abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890

# Database
DB_PATH=./data/db/emmaphone.db

# Session Management
SESSION_SECRET=your-secret-key-change-this
REDIS_URL=redis://localhost:6379  # Optional Redis for sessions
```

## Development Workflow

1. **Local Development**: Use `npm run dev` with LiveKit services via Docker
2. **Testing**: Access via `https://localhost:3443` (HTTPS required for microphone)
3. **Authentication**: Use demo accounts or register new users
4. **Calling**: Use speed dial buttons to test inter-user calling
5. **Railway Deployment**: Builds automatically from main branch

## Important Notes

- **HTTPS Required**: WebRTC microphone access requires HTTPS in browsers
- **LiveKit Dependencies**: Application depends on LiveKit server being available
- **Database Auto-Init**: Database and demo users are created automatically
- **Port Configuration**: HTTP (3001), HTTPS (3443), LiveKit (7880), Redis (6379)
- **Session Storage**: Supports both Redis and memory-based sessions
- **SSL Certificates**: Located in `ssl/` directory for HTTPS support
- **Migration State**: Repository maintains both old and new structures during transition
- **Docker Builds**: Use the refactored `web/` directory structure

## Testing

- Demo users: emma, noah, olivia, liam (password: demo123)
- Multiple browser windows can simulate different users
- Speed dial positions 1-4 are available for contacts
- Call logs are automatically recorded in database

## Raspberry Pi Development (Current Focus)

### Hardware Setup
- **Target Device**: Raspberry Pi Zero 2 W (512MB RAM, ARM64)
- **Audio HAT**: ReSpeaker 2-Mics Pi HAT v2.0 from Seeed Studio
  - 2 analog microphones (dual-mic array)
  - 3 x APA102 RGB LEDs (GPIO5/6 SPI control)
  - 1 User Button (GPIO17)
  - 3.5mm audio jack (speaker connected)
  - Audio drivers already installed and working (alsamixer, aplay, arecord)

### Development Strategy
- **Language**: Python (not Node.js) for Pi development
- **Architecture**: Web App (Node.js) ↔ Pi App (Python) via HTTP/WebSocket
- **LiveKit**: Testing LiveKit Python SDK for direct WebRTC audio
- **Environment**: Python venv for clean, reproducible development

### Pi Application Requirements
1. **Boot Sequence**: 
   - Check WiFi config → Connect OR start AP mode for setup
   - WiFi setup via hotspot "EmmaPhone-Setup" if no config
   - Web interface for user authentication once connected
   - Main calling application with hardware controls

2. **Hardware Integration**:
   - Button control (GPIO17) for speed dial/call actions
   - LED status indicators (3 RGB LEDs) for system state
   - Audio I/O via ReSpeaker HAT (PyAudio interface)
   - WiFi management and AP mode capability

3. **State Management**:
   - setup_needed (red LED) → connecting (yellow) → ready (green)
   - incoming_call (blue pulse) → in_call (blue solid)
   - Button actions: short=answer, long=speed_dial, double=hangup

### Development Environment Setup
- **Git**: Configured on Pi with SSH keys
- **Virtual Environment**: `~/emmaphone2/pi/venv/` for clean installs
- **Reset Script**: `setup_pi_env.sh` for returning to clean state
- **Dependencies**: LiveKit Python SDK, RPi.GPIO, PyAudio, requests, websockets

### Next Steps
1. Test LiveKit Python SDK compatibility on Pi Zero 2
2. Verify ReSpeaker HAT integration with Python
3. Create basic project structure with WiFi manager
4. Implement hardware control interfaces
5. Build web interface for authentication and setup

### Code Reuse Strategy
- **HTML/CSS**: Adapt web app templates for Pi web interface
- **API Contracts**: Same endpoints, Python implementation
- **Authentication**: Same flow, different backend
- **Cannot Reuse**: LiveKit Web SDK (testing Python equivalent)

## Future Development

The project is structured to support:
- Raspberry Pi hardware integration (`pi/` directory) - IN PROGRESS
- Hardware button interface - PLANNED
- WiFi setup wizard - PLANNED
- GPIO audio drivers - PLANNED
- Systemd service configuration - PLANNED