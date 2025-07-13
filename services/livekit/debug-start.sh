#!/bin/bash

echo "DEBUG: Script starting..."
echo "DEBUG: Creating debug info file..."

# Create debug info in a file
cat > /tmp/debug-info.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>LiveKit Debug</title>
    <meta http-equiv="refresh" content="5">
    <style>body{font-family:monospace; margin:20px;} pre{background:#f0f0f0; padding:10px;}</style>
</head>
<body>
    <h1>LiveKit Debug Info - $(date)</h1>
    
    <h2>Environment Variables</h2>
    <pre>$(env | grep -E "(PORT|RAILWAY|LIVEKIT|REDIS)" | sort)</pre>
    
    <h2>File System Check</h2>
    <pre>$(ls -la / 2>&1)</pre>
    
    <h2>LiveKit Binary Check</h2>
    <pre>which: $(which livekit-server 2>&1)
version: $(livekit-server --version 2>&1)
help: $(livekit-server --help 2>&1 | head -10)</pre>
    
    <h2>LiveKit Test</h2>
    <pre>$(livekit-server --keys "test:test" 2>&1 | head -20)</pre>
    
    <h2>Container Info</h2>
    <pre>Date: $(date)
PWD: $(pwd)
User: $(id)
Uptime: $(cat /proc/uptime)</pre>
</body>
</html>
EOF

echo "DEBUG: Starting simple HTTP server on port ${PORT:-7880}..."

# Simple HTTP server using bash and nc (netcat)
while true; do
    {
        echo "HTTP/1.1 200 OK"
        echo "Content-Type: text/html"
        echo "Connection: close"
        echo ""
        cat /tmp/debug-info.html
    } | nc -l -p ${PORT:-7880} -q 1
    
    echo "DEBUG: Served debug page"
    
    # Update debug info for next request
    cat > /tmp/debug-info.html << EOF
<!DOCTYPE html>
<html>
<head>
    <title>LiveKit Debug</title>
    <meta http-equiv="refresh" content="5">
    <style>body{font-family:monospace; margin:20px;} pre{background:#f0f0f0; padding:10px;}</style>
</head>
<body>
    <h1>LiveKit Debug Info - $(date)</h1>
    
    <h2>Environment Variables</h2>
    <pre>$(env | grep -E "(PORT|RAILWAY|LIVEKIT|REDIS)" | sort)</pre>
    
    <h2>File System Check</h2>
    <pre>$(ls -la / 2>&1)</pre>
    
    <h2>LiveKit Binary Check</h2>
    <pre>which: $(which livekit-server 2>&1)
version: $(livekit-server --version 2>&1)
help: $(livekit-server --help 2>&1 | head -10)</pre>
    
    <h2>LiveKit Test</h2>
    <pre>$(livekit-server --keys "test:test" 2>&1 | head -20)</pre>
    
    <h2>Container Info</h2>
    <pre>Date: $(date)
PWD: $(pwd)
User: $(id)
Uptime: $(cat /proc/uptime)</pre>
</body>
</html>
EOF
done