#!/bin/bash
# EmmaPhone2 Pi Development Environment Setup

echo "🚀 Setting up EmmaPhone2 Pi development environment..."

# Check if we're in the right directory
if [ ! -f "requirements.txt" ]; then
    echo "❌ Error: requirements.txt not found. Please run from pi/ directory."
    exit 1
fi

# Remove existing venv if it exists
if [ -d "venv" ]; then
    echo "🗑️  Removing existing virtual environment..."
    rm -rf venv
fi

# Create fresh virtual environment
echo "🐍 Creating fresh virtual environment..."
python3 -m venv venv

# Activate venv
echo "✅ Activating virtual environment..."
source venv/bin/activate

# Upgrade pip
echo "📦 Upgrading pip..."
pip install --upgrade pip

# Install requirements
echo "📥 Installing requirements..."
pip install -r requirements.txt

# Test critical imports
echo "🧪 Testing critical imports..."
python3 -c "import pyaudio; print('✅ PyAudio: OK')" || echo "❌ PyAudio: FAILED"
python3 -c "import livekit; print('✅ LiveKit: OK')" || echo "❌ LiveKit: FAILED"
python3 -c "import RPi.GPIO; print('✅ GPIO: OK')" || echo "❌ GPIO: FAILED"
python3 -c "import spidev; print('✅ SPI: OK')" || echo "❌ SPI: FAILED"

echo ""
echo "🎉 Setup complete!"
echo "📋 To activate the environment:"
echo "    source venv/bin/activate"
echo ""
echo "🏃 To run the application:"
echo "    python3 src/main.py"
echo ""
echo "🧪 To test hardware:"
echo "    python3 -c \"from src.hardware.leds import LEDController; import asyncio; asyncio.run(LEDController().test_all_colors())\""
echo ""