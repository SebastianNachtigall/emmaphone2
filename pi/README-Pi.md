# EmmaPhone2 - Raspberry Pi Development Guide

## 🎯 Project Overview

This directory contains the Raspberry Pi implementation of EmmaPhone2, designed to run on a Pi Zero 2 with a ReSpeaker 2-Mics Pi HAT v2.0 for hardware-based calling functionality.

## 🛠️ Hardware Setup

### Target Hardware
- **Raspberry Pi Zero 2 W** (512MB RAM, ARM64)
- **ReSpeaker 2-Mics Pi HAT v2.0** from Seeed Studio
- **Speaker** connected via 3.5mm audio jack

### ReSpeaker 2-Mics Pi HAT v2.0 Specifications
- **Audio Codec**: TLV320AIC3104
- **Microphones**: 2 analog microphones (dual-mic array)
- **LEDs**: 3 x APA102 RGB LEDs (programmable)
- **User Button**: 1 button connected to GPIO17
- **Audio Output**: 3.5mm audio jack + JST 2.0 speaker out
- **Interfaces**: 2 on-board Grove connectors
- **Communication**: I2S for audio, SPI for LEDs

## 📍 GPIO Pin Assignments

### ReSpeaker HAT Pin Mapping
```
GPIO17 - User Button (pull-up, active low)
GPIO5  - LED SPI Clock (SCK)
GPIO6  - LED SPI Data (MOSI)
I2S    - Audio interface (pre-configured)
```

### Available GPIO Pins (not used by HAT)
- GPIO pins not occupied by the HAT can be used for additional buttons
- Check pinout.xyz/pinout/respeaker_2_mics_phat for full details

## 🐍 Python Development Environment

### Required Python Libraries
```bash
# Core libraries
sudo apt install python3-pip

# Audio processing
pip3 install pyaudio

# LED control (APA102)
pip3 install spidev

# GPIO control
pip3 install RPi.GPIO

# Web communication
pip3 install requests websockets aiohttp

# Audio utilities
pip3 install numpy scipy

# Optional: Audio analysis
pip3 install librosa soundfile
```

### System Setup
```bash
# Enable SPI for LED control
sudo raspi-config
# Navigate to: Interface Options > SPI > Enable

# Install ReSpeaker drivers (if not already done)
git clone https://github.com/HinTak/seeed-voicecard.git
cd seeed-voicecard
sudo ./install.sh
sudo reboot now
```

## 🎵 Audio Configuration

### Test Audio Setup
```bash
# List audio devices
aplay -l
arecord -l

# Test recording (adjust hw:X,Y based on your setup)
arecord -D hw:1,0 -f cd test.wav

# Test playback
aplay -D hw:1,0 test.wav

# Test with alsamixer
alsamixer
```

### Audio Device Information
- **Recording**: Use the dual-microphone array
- **Playback**: 3.5mm audio jack to connected speaker
- **Format**: 16-bit PCM, 44.1kHz recommended
- **Device**: Usually `hw:1,0` for ReSpeaker HAT

## 🏗️ Project Architecture

### Communication with Web App
```
┌─────────────────┐  HTTP/WebSocket   ┌─────────────────┐
│   Web App       │ ◄──────────────► │   Pi App        │
│   (Node.js)     │                  │   (Python)      │
│   LiveKit SDK   │                  │   Hardware      │
│   Authentication│                  │   GPIO/Audio    │
└─────────────────┘                  └─────────────────┘
```

### Pi Responsibilities
- **Hardware Control**: Buttons, LEDs, audio I/O
- **Audio Processing**: Record/playback via PyAudio
- **User Interface**: Physical button interactions
- **API Communication**: HTTP requests to web app
- **Call Handling**: Receive incoming call notifications

### Web App Responsibilities
- **WebRTC**: LiveKit integration for voice calls
- **Authentication**: User login/session management
- **Contact Management**: Speed dial configuration
- **Call Routing**: Initiate calls between users

## 📁 Directory Structure

```
pi/
├── requirements.txt         # Python dependencies
├── src/
│   ├── main.py             # Main application entry point
│   ├── hardware/           # Hardware abstraction layer
│   │   ├── respeaker.py    # ReSpeaker HAT interface
│   │   ├── button.py       # GPIO17 button handling
│   │   ├── leds.py         # APA102 LED control
│   │   └── audio.py        # PyAudio interface
│   ├── api/                # Web app communication
│   │   ├── web_client.py   # HTTP client for web app
│   │   ├── auth.py         # Authentication handling
│   │   └── websocket.py    # WebSocket client
│   ├── services/           # Background services
│   │   ├── call_handler.py # Incoming call logic
│   │   ├── contacts.py     # Contact management
│   │   └── audio_manager.py # Audio stream management
│   └── setup_wizard/       # WiFi setup interface
│       ├── hotspot.py      # Create WiFi hotspot
│       ├── web_server.py   # Configuration web interface
│       └── network.py      # Network configuration
├── systemd/                # System service files
│   └── emmaphone-pi.service
├── config/                 # Configuration files
│   ├── audio.json          # Audio settings
│   ├── hardware.json       # Hardware configuration
│   └── api.json           # API endpoints
├── scripts/                # Utility scripts
│   ├── install.sh          # Installation script
│   ├── test_hardware.py    # Hardware testing
│   └── deploy.sh          # Deployment script
└── docs/                   # Documentation
    ├── hardware_guide.md   # Hardware setup guide
    ├── troubleshooting.md  # Common issues
    └── api_reference.md    # API documentation
```

## 🔧 Hardware Control Examples

### Button Control
```python
import RPi.GPIO as GPIO
import time

BUTTON_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

def button_callback(channel):
    print("Button pressed!")

GPIO.add_event_detect(BUTTON_PIN, GPIO.FALLING, 
                     callback=button_callback, bouncetime=300)
```

### LED Control (APA102)
```python
import spidev
import time

class LEDController:
    def __init__(self):
        self.spi = spidev.SpiDev()
        self.spi.open(0, 0)  # SPI bus 0, device 0
        self.spi.max_speed_hz = 8000000
        
    def set_color(self, led_index, r, g, b):
        # APA102 LED control implementation
        pass
        
    def all_off(self):
        # Turn off all LEDs
        pass
```

### Audio Recording
```python
import pyaudio
import wave

def record_audio(duration=5):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 2  # Stereo from dual mics
    RATE = 44100
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    input=True,
                    frames_per_buffer=CHUNK)
    
    frames = []
    for i in range(0, int(RATE / CHUNK * duration)):
        data = stream.read(CHUNK)
        frames.append(data)
    
    stream.stop_stream()
    stream.close()
    p.terminate()
    
    return frames
```

## 🌐 API Communication

### Web App Endpoints
```python
# Base URL for web app
WEB_APP_URL = "https://your-railway-app.com"

# API endpoints
ENDPOINTS = {
    "auth": "/api/auth/login",
    "contacts": "/api/contacts",
    "call_initiate": "/api/initiate-call",
    "health": "/health"
}
```

### WebSocket Events
```python
# Incoming events from web app
WEBSOCKET_EVENTS = {
    "incoming_call": "handle_incoming_call",
    "call_ended": "handle_call_ended",
    "contact_update": "handle_contact_update"
}
```

## 🚀 Development Workflow

### Local Development
1. **Write code** in `pi/src/` on your local machine
2. **Test basic logic** without hardware (mock GPIO)
3. **Commit changes** to git repository

### Pi Testing
1. **SSH into Pi**: `ssh pi@your-pi-ip`
2. **Pull changes**: `cd emmaphone2 && git pull`
3. **Install dependencies**: `pip3 install -r requirements.txt`
4. **Test on hardware**: `python3 src/main.py`

### Deployment
1. **Create systemd service**
2. **Enable auto-start**: `sudo systemctl enable emmaphone-pi`
3. **Start service**: `sudo systemctl start emmaphone-pi`

## 🐛 Troubleshooting

### Common Issues
- **Audio not working**: Check `alsamixer` levels, verify driver installation
- **GPIO permissions**: Run with `sudo` or add user to `gpio` group
- **SPI not available**: Enable SPI in `raspi-config`
- **Import errors**: Ensure all Python dependencies are installed

### Hardware Testing
```bash
# Test button
python3 scripts/test_hardware.py --button

# Test LEDs
python3 scripts/test_hardware.py --leds

# Test audio
python3 scripts/test_hardware.py --audio
```

## 📚 Resources

### Documentation
- [ReSpeaker HAT Wiki](https://wiki.seeedstudio.com/ReSpeaker_2_Mics_Pi_HAT/)
- [Pi GPIO Pinout](https://pinout.xyz/pinout/respeaker_2_mics_phat)
- [PyAudio Documentation](https://pypi.org/project/PyAudio/)

### GitHub Resources
- [seeed-voicecard](https://github.com/HinTak/seeed-voicecard) - Audio drivers
- [mic_hat](https://github.com/respeaker/mic_hat) - LED control examples

## 🎯 Next Steps

1. **Set up basic Python structure**
2. **Test hardware interfaces** (button, LEDs, audio)
3. **Implement web app communication**
4. **Create call handling logic**
5. **Add systemd service**
6. **Test full workflow**

## 📝 Notes

- Pi Zero 2 has limited resources - optimize for performance
- Audio latency is critical for voice calls
- LED feedback improves user experience
- Single button interface should be intuitive
- Error handling is crucial for embedded device