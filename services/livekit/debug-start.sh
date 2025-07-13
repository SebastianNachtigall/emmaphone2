#!/bin/bash

echo "=== LiveKit Debug Start ==="
echo "Date: $(date)"
echo "PWD: $(pwd)"
echo "User: $(whoami)"

echo ""
echo "=== Environment Variables ==="
env | grep -E "(LIVEKIT|REDIS|PORT)" | sort

echo ""
echo "=== File System Check ==="
echo "Root directory contents:"
ls -la /

echo ""
echo "=== LiveKit Binary Check ==="
which livekit-server
livekit-server --version

echo ""
echo "=== LiveKit Help ==="
livekit-server --help | head -20

echo ""
echo "=== Testing Simple Start ==="
echo "Starting LiveKit with minimal config..."

# Try the simplest possible configuration first
livekit-server \
  --bind 0.0.0.0 \
  --port 7880 \
  --keys "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" \
  --log-level debug