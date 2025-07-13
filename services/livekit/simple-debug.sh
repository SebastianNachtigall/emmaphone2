#!/bin/bash

echo "SIMPLE DEBUG: Starting..."
echo "SIMPLE DEBUG: Port is ${PORT:-7880}"
echo "SIMPLE DEBUG: Creating HTML file..."

# Create a simple debug page
cat > /tmp/debug.html << 'EOF'
<!DOCTYPE html>
<html>
<head>
    <title>LiveKit Debug</title>
    <meta http-equiv="refresh" content="10">
    <style>body{font-family:monospace; margin:20px;} pre{background:#f0f0f0; padding:10px;}</style>
</head>
<body>
    <h1>LiveKit Debug - FROM SIMPLE SCRIPT</h1>
    <h2>Environment Variables</h2>
    <pre>
PORT=${PORT}
REDIS_URL=${REDIS_URL}
RAILWAY_SERVICE_NAME=${RAILWAY_SERVICE_NAME}
    </pre>
    
    <h2>LiveKit Binary Check</h2>
    <pre>
EOF

# Add LiveKit binary info to the HTML
echo "which livekit-server: $(which livekit-server 2>&1)" >> /tmp/debug.html
echo "livekit-server --version: $(livekit-server --version 2>&1)" >> /tmp/debug.html
echo "livekit-server --help (first 5 lines):" >> /tmp/debug.html
livekit-server --help 2>&1 | head -5 >> /tmp/debug.html

cat >> /tmp/debug.html << 'EOF'
    </pre>
    
    <h2>LiveKit Test</h2>
    <pre>
EOF

# Test LiveKit with simple keys
echo "Testing with simple keys..." >> /tmp/debug.html
timeout 5 livekit-server --keys "test:test" 2>&1 | head -10 >> /tmp/debug.html || echo "Test failed or timed out" >> /tmp/debug.html

cat >> /tmp/debug.html << 'EOF'
    </pre>
    
    <h2>Status</h2>
    <pre>
This is a simplified debug server using bash and netcat.
If you can see this, the container is working but LiveKit has issues.
    </pre>
</body>
</html>
EOF

echo "SIMPLE DEBUG: HTML file created, starting server..."

# Simple HTTP server using netcat
PORT=${PORT:-7880}
echo "SIMPLE DEBUG: Listening on port $PORT"

while true; do
    echo "SIMPLE DEBUG: Waiting for connection..."
    {
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: text/html"
        echo "Connection: close"
        echo ""
        cat /tmp/debug.html
    } | nc -l -p $PORT
    echo "SIMPLE DEBUG: Served a request"
    sleep 1
done