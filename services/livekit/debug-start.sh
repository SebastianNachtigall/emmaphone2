#!/bin/bash

echo "====== LIVEKIT DEBUG START ======"
echo "Date: $(date)"
echo "PWD: $(pwd)"
echo "User: $(id)"
echo ""

echo "====== ENVIRONMENT ======"
env | sort
echo ""

echo "====== FILESYSTEM CHECK ======"
echo "Root contents:"
ls -la /
echo ""
echo "Usr/bin contents (livekit related):"
ls -la /usr/bin/livekit* 2>/dev/null || echo "No livekit binaries found"
echo ""

echo "====== BINARY CHECK ======"
which livekit-server
echo "Version check:"
livekit-server --version 2>&1
echo ""

echo "====== HELP OUTPUT ======"
echo "Getting help to see available options:"
livekit-server --help 2>&1 | head -30
echo ""

echo "====== ATTEMPTING STARTUP ======"
echo "Command: livekit-server --keys [KEY] --bind 0.0.0.0 --port 7880 --log-level debug"
echo "Starting in 3 seconds..."
sleep 3

# Use strace to see what system calls are being made
echo "Starting with strace to see what's happening..."
timeout 30 strace -e trace=openat,read livekit-server \
  --keys "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" \
  --bind 0.0.0.0 \
  --port 7880 \
  --log-level debug 2>&1

echo ""
echo "====== EXIT CODE: $? ======"
echo "Debug complete. Container will now exit."