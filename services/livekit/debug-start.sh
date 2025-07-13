#!/bin/bash

# Output to stderr so Railway sees it
exec 1>&2

echo "RAILWAY-DEBUG: ====== LIVEKIT DEBUG START ======" 
echo "RAILWAY-DEBUG: Date: $(date)"
echo "RAILWAY-DEBUG: PWD: $(pwd)"
echo "RAILWAY-DEBUG: User: $(id)"

echo "RAILWAY-DEBUG: ====== ENVIRONMENT ======"
env | grep -E "(PORT|RAILWAY|LIVEKIT)" | sort

echo "RAILWAY-DEBUG: ====== BINARY CHECK ======"
which livekit-server || echo "RAILWAY-DEBUG: livekit-server not found"
livekit-server --version 2>&1 || echo "RAILWAY-DEBUG: version failed"

echo "RAILWAY-DEBUG: ====== HELP CHECK ======"
livekit-server --help 2>&1 | head -10 || echo "RAILWAY-DEBUG: help failed"

echo "RAILWAY-DEBUG: ====== ATTEMPTING MINIMAL START ======"
echo "RAILWAY-DEBUG: About to run livekit-server with keys..."

# Try the absolute minimal command to see what happens
livekit-server --keys "test:test" 2>&1 || {
    echo "RAILWAY-DEBUG: Simple keys failed with exit code $?"
}

echo "RAILWAY-DEBUG: ====== TRYING REAL KEYS ======"
livekit-server --keys "APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890" 2>&1 || {
    echo "RAILWAY-DEBUG: Real keys failed with exit code $?"
}

echo "RAILWAY-DEBUG: ====== DEBUG COMPLETE ======"