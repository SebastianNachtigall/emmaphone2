#!/bin/bash

echo "=== LiveKit Server Starting (Test Deploy) ==="
echo "Date: $(date)"
echo "Port: ${PORT:-7880}"

# Check if LiveKit binary exists
if ! command -v livekit-server &> /dev/null; then
    echo "ERROR: livekit-server binary not found!"
    echo "Available binaries in /usr/local/bin:"
    ls -la /usr/local/bin/
    exit 1
fi

echo "LiveKit binary found: $(which livekit-server)"
echo "LiveKit version: $(livekit-server --version)"

# Check for Redis-related environment variables that might be interfering
echo "=== ENVIRONMENT CHECK ==="
env | grep -i redis | head -10 || echo "No Redis environment variables found"

# Clear any Redis environment variables that might override our config
unset REDIS_HOST
unset REDIS_PORT  
unset REDIS_URL
unset REDIS_URL_VAR
unset REDIS_PASSWORD
unset LIVEKIT_REDIS_HOST
unset LIVEKIT_REDIS_PORT

# Set up environment variables for Railway
export LIVEKIT_CONFIG_FILE="/etc/livekit.yaml"

# Use Railway's PORT if provided, otherwise default to 7880
export PORT=${PORT:-7880}

# Store the Railway Redis URL before we unset it
RAILWAY_REDIS_URL="$REDIS_URL"

# Use Railway Redis URL if available
if [ -n "$RAILWAY_REDIS_URL" ]; then
    echo "Using Railway Redis: $RAILWAY_REDIS_URL"
    
    # Extract components from Redis URL for LiveKit config
    # Format: redis://default:password@host:port
    REDIS_USER=$(echo $RAILWAY_REDIS_URL | sed -n 's|redis://\([^:]*\):.*|\1|p')
    REDIS_PASS=$(echo $RAILWAY_REDIS_URL | sed -n 's|redis://[^:]*:\([^@]*\)@.*|\1|p')
    REDIS_HOST=$(echo $RAILWAY_REDIS_URL | sed -n 's|redis://[^@]*@\([^:]*\):.*|\1|p')
    REDIS_PORT=$(echo $RAILWAY_REDIS_URL | sed -n 's|redis://[^@]*@[^:]*:\([0-9]*\).*|\1|p')
    
    # Debug the parsing
    echo "Parsed Redis User: '$REDIS_USER'"
    echo "Parsed Redis Pass: [HIDDEN]"
    echo "Parsed Redis Host: '$REDIS_HOST'"
    echo "Parsed Redis Port: '$REDIS_PORT'"
    
    # Ensure we have valid values
    if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
        echo "Failed to parse Redis URL, falling back to defaults"
        export REDIS_HOST=redis
        export REDIS_PORT=6379
        export REDIS_USER=""
        export REDIS_PASS=""
    else
        export REDIS_HOST="$REDIS_HOST"
        export REDIS_PORT="$REDIS_PORT"
        export REDIS_USER="$REDIS_USER"
        export REDIS_PASS="$REDIS_PASS"
    fi
else
    echo "No Redis URL provided, will run in standalone mode"
    # Don't set these - they will be used by LiveKit automatically!
    # export REDIS_HOST=redis
    # export REDIS_PORT=6379
    export REDIS_USER=""
    export REDIS_PASS=""
fi

# Generate secure API keys if not provided
if [ -z "$LIVEKIT_API_KEY" ]; then
    export LIVEKIT_API_KEY="APIKeySecret_$(openssl rand -hex 16)"
fi
if [ -z "$LIVEKIT_API_SECRET" ]; then
    export LIVEKIT_API_SECRET=$(openssl rand -hex 32)
fi

echo "API Key: $LIVEKIT_API_KEY"
echo "Redis: $REDIS_HOST:$REDIS_PORT"

# Create a minimal config file without Redis section
cat > /tmp/livekit-runtime.yaml << EOF
port: $PORT
bind_addresses:
  - "0.0.0.0"

keys:
  $LIVEKIT_API_KEY: $LIVEKIT_API_SECRET

rtc:
  tcp_port: 7881
  port_range_start: 50000
  port_range_end: 60000
  use_external_ip: false
  stun_servers:
    - "stun.l.google.com:19302"
    - "stun1.l.google.com:19302"

log_level: info
development: true

room:
  empty_timeout: 300
  auto_create: true
EOF

echo "=== Starting LiveKit Server ==="
echo "Config file: /tmp/livekit-runtime.yaml"
echo "Binding to 0.0.0.0:$PORT"

echo "=== CONFIG FILE DEBUG ==="
echo "Redis section of config:"
grep -A 4 "redis:" /tmp/livekit-runtime.yaml

# Try starting LiveKit with minimal command line only (no config file)
echo "Starting LiveKit with minimal command line configuration..."
echo "Keys being used: $LIVEKIT_API_KEY: [SECRET]"
exec livekit-server \
    --keys "$LIVEKIT_API_KEY: $LIVEKIT_API_SECRET" \
    --bind 0.0.0.0 \
    --dev