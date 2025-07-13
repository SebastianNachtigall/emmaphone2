#!/bin/bash

# Create a simple debug web server that shows info before container crashes
cat > /tmp/debug-server.py << 'EOF'
#!/usr/bin/env python3
import os
import subprocess
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import html

class DebugHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        html_content = f"""
        <html><head><title>LiveKit Debug</title>
        <meta http-equiv="refresh" content="3">
        <style>body{{font-family:monospace; margin:20px;}} pre{{background:#f0f0f0; padding:10px; overflow:auto;}}</style>
        </head><body>
        <h1>LiveKit Debug Info - {time.ctime()}</h1>
        
        <h2>Environment Variables</h2>
        <pre>{html.escape(self.get_env())}</pre>
        
        <h2>File System</h2>
        <pre>{html.escape(self.get_filesystem())}</pre>
        
        <h2>LiveKit Binary</h2>
        <pre>{html.escape(self.get_binary_info())}</pre>
        
        <h2>LiveKit Test Run</h2>
        <pre>{html.escape(self.test_livekit())}</pre>
        
        <h2>Container Status</h2>
        <pre>Uptime: {time.time() - start_time:.1f} seconds
Container will crash soon with LiveKit error...</pre>
        </body></html>
        """
        self.wfile.write(html_content.encode())
    
    def get_env(self):
        try:
            return '\n'.join(f"{k}={v}" for k, v in sorted(os.environ.items()) 
                           if any(x in k.upper() for x in ['PORT', 'RAILWAY', 'LIVEKIT', 'REDIS']))
        except Exception as e:
            return f"Error: {e}"
    
    def get_filesystem(self):
        try:
            result = subprocess.run(['ls', '-la', '/'], capture_output=True, text=True, timeout=5)
            return f"ls -la /:\n{result.stdout}\n{result.stderr}"
        except Exception as e:
            return f"Error: {e}"
    
    def get_binary_info(self):
        try:
            output = ""
            
            # Check which
            result1 = subprocess.run(['which', 'livekit-server'], capture_output=True, text=True)
            output += f"which livekit-server: {result1.returncode}\n{result1.stdout}{result1.stderr}\n\n"
            
            # Check version
            result2 = subprocess.run(['livekit-server', '--version'], capture_output=True, text=True, timeout=5)
            output += f"livekit-server --version: {result2.returncode}\n{result2.stdout}{result2.stderr}\n\n"
            
            # Check help
            result3 = subprocess.run(['livekit-server', '--help'], capture_output=True, text=True, timeout=5)
            help_lines = result3.stdout.split('\n')[:15]
            output += f"livekit-server --help (first 15 lines): {result3.returncode}\n" + '\n'.join(help_lines)
            
            return output
        except Exception as e:
            return f"Error: {e}"
    
    def test_livekit(self):
        try:
            # Test simple keys
            result = subprocess.run([
                'livekit-server', '--keys', 'test:test'
            ], capture_output=True, text=True, timeout=5)
            
            output = f"Test with simple keys:\nExit code: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
            
            return output
        except subprocess.TimeoutExpired:
            return "LiveKit test timed out (might be working!)"
        except Exception as e:
            return f"Error testing LiveKit: {e}"

start_time = time.time()
port = int(os.environ.get('PORT', 7880))
server = HTTPServer(('0.0.0.0', port), DebugHandler)
print(f"Debug server starting on port {port}")
print(f"Visit https://emmaphone2-livekit-production.up.railway.app to see debug info")

# Run for 60 seconds then try to start LiveKit
def delayed_livekit():
    time.sleep(60)
    print("Starting LiveKit after 60 seconds...")
    subprocess.run(['livekit-server', '--keys', 'APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890'])

threading.Thread(target=delayed_livekit, daemon=True).start()
server.serve_forever()
EOF

# Make it executable and run
chmod +x /tmp/debug-server.py
python3 /tmp/debug-server.py