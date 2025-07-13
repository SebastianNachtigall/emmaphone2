#!/bin/bash

echo "=== ENTRYPOINT OVERRIDE SUCCESS ==="
echo "Date: $(date)"
echo "Container starting with our custom script!"
echo "Port: ${PORT:-7880}"

echo "=== ENVIRONMENT CHECK ==="
env | grep -E "(PORT|RAILWAY|REDIS)" | sort

echo "=== LIVEKIT BINARY CHECK ==="
which livekit-server
echo "Version check:"
livekit-server --version 2>&1 || echo "Version command failed"

echo "=== LIVEKIT HELP CHECK ==="
echo "Getting help output..."
livekit-server --help 2>&1 | head -10 || echo "Help command failed"

echo "=== LIVEKIT KEY TEST ==="
echo "Testing with simple keys..."
timeout 5 livekit-server --keys "test:test" 2>&1 || echo "Simple key test failed with exit code $?"

echo "=== LIVEKIT REAL KEY TEST ==="
echo "Testing with real keys..."
timeout 5 livekit-server --keys "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" 2>&1 || echo "Real key test failed with exit code $?"

echo "=== FINISHED DEBUGGING ==="
echo "All tests completed. Container will now sleep to stay alive."
echo "Check Railway logs to see all the above debug output!"

# Keep container alive
while true; do
    echo "Container still alive at $(date)"
    sleep 60
done