#!/bin/bash

echo "DEBUG: Script starting..."
echo "DEBUG: Date is $(date)"

# Force output to appear
exec > >(tee -a /tmp/debug.log)
exec 2>&1

echo "DEBUG: Environment variables:"
env

echo "DEBUG: Checking livekit-server binary:"
which livekit-server || echo "livekit-server not found in PATH"

if [ -f /usr/bin/livekit-server ]; then
    echo "DEBUG: Found livekit-server at /usr/bin/livekit-server"
    /usr/bin/livekit-server --version 2>&1 || echo "Version command failed"
else
    echo "DEBUG: livekit-server not found at /usr/bin/livekit-server"
fi

echo "DEBUG: Trying to start with debug logging..."

# Try absolute path and catch any errors
/usr/bin/livekit-server \
  --keys "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" \
  --bind 0.0.0.0 \
  --port 7880 \
  --log-level debug 2>&1 || {
    echo "DEBUG: LiveKit startup failed with exit code $?"
    echo "DEBUG: Checking what went wrong..."
    ls -la /usr/bin/livekit* 2>&1 || echo "No livekit binaries found"
}