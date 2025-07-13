#!/bin/bash

echo "=== LiveKit Server Starting ==="
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

# Set up environment variables for Railway
export LIVEKIT_CONFIG_FILE="/etc/livekit.yaml"

# Use Railway's PORT if provided, otherwise default to 7880
export PORT=${PORT:-7880}

# Use Railway Redis URL if available
if [ -n "$REDIS_URL" ]; then
    echo "Using Railway Redis: $REDIS_URL"
    # Extract host and port from Redis URL for LiveKit config
    # Format: redis://default:password@host:port
    REDIS_HOST=$(echo $REDIS_URL | sed -n 's|redis://[^@]*@\([^:]*\):.*|\1|p')
    REDIS_PORT=$(echo $REDIS_URL | sed -n 's|redis://[^@]*@[^:]*:\([0-9]*\).*|\1|p')
    
    # Debug the parsing
    echo "Parsed Redis Host: '$REDIS_HOST'"
    echo "Parsed Redis Port: '$REDIS_PORT'"
    
    # Ensure we have valid values
    if [ -z "$REDIS_HOST" ] || [ -z "$REDIS_PORT" ]; then
        echo "Failed to parse Redis URL, falling back to defaults"
        export REDIS_HOST=redis
        export REDIS_PORT=6379
    else
        export REDIS_HOST="$REDIS_HOST"
        export REDIS_PORT="$REDIS_PORT"
    fi
else
    echo "No Redis URL provided, using default redis:6379"
    export REDIS_HOST=redis
    export REDIS_PORT=6379
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

# Create a runtime config file with Railway-specific settings
cat > /tmp/livekit-runtime.yaml << EOF
port: $PORT
bind_addresses:
  - "0.0.0.0"

keys:
  $LIVEKIT_API_KEY: $LIVEKIT_API_SECRET

redis:
  address: $REDIS_HOST:$REDIS_PORT

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

# Start LiveKit server
exec livekit-server --config /tmp/livekit-runtime.yaml