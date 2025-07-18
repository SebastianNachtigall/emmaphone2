# EmmaPhone2 Pi CLI Application

Interactive command-line interface for Pi calling functionality. Perfect for development, testing, and managing your Pi device.

## Features

- 🚀 **Guided User Registration** - Automatic setup if not configured
- 👥 **Online Users** - View and call connected users in real-time
- 📋 **Speed Dial Management** - Configure and call speed dial positions 1-4
- 📞 **Direct Calling** - Call any user by ID
- 📊 **Status Monitoring** - Connection health and diagnostics
- 🔄 **Real-time Updates** - Live user lists and call notifications

## Quick Start

```bash
cd ~/emmaphone2/pi
python3 pi_phone_cli.py
```

## First Time Setup

1. **Run the CLI** - It will detect if you need user registration
2. **Create Account** - Follow guided setup to create your Pi user
3. **Start Calling** - Use the menu to view users and make calls

## Menu Overview

```
🏠 EmmaPhone2 Pi - Interactive CLI
================================
👤 User: YourName (ID: 7) - ✅ Connected
🌐 Web Server: https://emmaphone2-production.up.railway.app
📡 Socket.IO: ✅ Connected

[1] 👥 Show Online Users & Call
[2] 📋 Manage Speed Dial Contacts  
[3] 📞 Call by User ID
[4] 📊 Connection Status
[5] 🔄 Refresh
[0] 🚪 Exit
```

## Usage Examples

### View Online Users and Call
- Select option `[1]` from main menu
- Choose user from list to call immediately
- Press `[R]` to refresh user list

### Configure Speed Dial
- Select option `[2]` from main menu
- Current speed dial positions 1-4 are shown
- Add contacts with `[A]`, remove with `[R]`
- Call speed dial positions directly with `[1-4]`

### Direct Call by ID
- Select option `[3]` from main menu
- Enter user ID (e.g., `1` for demo user Emma)
- Call will be initiated if user is online

### Check Status
- Select option `[4]` for connection diagnostics
- Shows authentication, web server, and Socket.IO status
- Useful for troubleshooting connection issues

## Integration with Hardware

This CLI app is designed to work alongside future hardware:

- **Hardware Buttons** - Speed dial positions 1-4 will map to physical buttons
- **LED Status** - Connection and call status will show on hardware LEDs
- **Hang Up Button** - Physical button to end calls
- **Audio** - Real LiveKit audio integration for actual calls

## Development Notes

- Uses existing `UserManager` and `WebClient` services
- Real-time Socket.IO connection for call signaling
- Async architecture supports background tasks
- Clean shutdown and error handling
- Logging reduced for clean CLI experience

## Troubleshooting

**Connection Issues:**
- Check internet connection
- Verify web server URL in settings
- Use `[4]` Status menu for diagnostics

**Authentication Problems:**
- Delete `~/.emmaphone/settings.json` to reset
- Run setup again with new credentials

**Call Failures:**
- Ensure target user is online (logged into web app)
- Check that Emma or other users are connected
- Use admin panel to verify user status

## Related Files

- `setup_user.py` - Standalone user registration
- `test_web_integration.py` - API testing
- `src/main.py` - Hardware-focused main app
- `debug_session.py` - Session debugging tools

Perfect for Pi development and testing! 🚀