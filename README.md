# EmmaPhone2 - Kid-Friendly SIP Client

A web-based SIP client designed for kids, featuring large speed dial buttons and simple interface. Built for eventual deployment on Raspberry Pi Zero 2.

## Features

- **Kid-Friendly Interface**: Large, colorful buttons with clear labels
- **Speed Dial**: 4 programmable speed dial buttons for quick calling
- **WebRTC Audio**: Browser-based audio handling for calls
- **SIP Support**: Full SIP client functionality using JsSIP library
- **Responsive Design**: Works on desktop and mobile devices

## Quick Start

1. Install dependencies:
   ```bash
   npm install
   ```

2. Start the development server:
   ```bash
   npm run dev
   ```

3. Open your browser to `http://localhost:3000`

4. Configure your SIP settings in the configuration panel

## SIP Configuration

You'll need:
- SIP server address (e.g., `sip.example.com`)
- Username and password for your SIP account
- WebRTC-enabled SIP server (most modern SIP providers support this)

## Browser Requirements

- Chrome, Firefox, Safari, or Edge
- HTTPS required for microphone access (use `https://localhost:3000` for local testing)
- WebRTC support

## Development Roadmap

- [x] Phase 1: Web-based SIP client
- [ ] Phase 2: Raspberry Pi hardware integration
- [ ] Phase 3: Configuration web interface
- [ ] Phase 4: Docker containerization
- [ ] Phase 5: Production deployment

## License

MIT