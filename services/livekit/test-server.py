#!/usr/bin/env python3
import os
import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Get environment info
        env_info = []
        for key, value in sorted(os.environ.items()):
            env_info.append(f"{key}={value}")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Railway Container Debug</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                pre {{ background: #f0f0f0; padding: 10px; overflow: auto; }}
                h2 {{ color: #333; border-bottom: 1px solid #ccc; }}
            </style>
        </head>
        <body>
            <h1>🐳 Railway Container Debug - {time.ctime()}</h1>
            
            <h2>✅ SUCCESS: Container is running and web server works!</h2>
            <p>This proves Railway can run our custom containers and serve web pages.</p>
            
            <h2>🌍 Environment Variables</h2>
            <pre>{"<br>".join(env_info)}</pre>
            
            <h2>📁 File System</h2>
            <pre>{self.get_filesystem()}</pre>
            
            <h2>🔍 LiveKit Check</h2>
            <pre>{self.check_livekit()}</pre>
            
            <h2>📊 Container Info</h2>
            <pre>
Working Directory: {os.getcwd()}
Python Version: {subprocess.run(['python3', '--version'], capture_output=True, text=True).stdout.strip()}
User: {subprocess.run(['id'], capture_output=True, text=True).stdout.strip()}
Uptime: {self.get_uptime()}
            </pre>
            
            <h2>🚀 Next Steps</h2>
            <p>Now we know the container works! We can add LiveKit step by step.</p>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def get_filesystem(self):
        try:
            result = subprocess.run(['ls', '-la', '/'], capture_output=True, text=True, timeout=5)
            return result.stdout
        except Exception as e:
            return f"Error: {e}"
    
    def check_livekit(self):
        try:
            # Check if livekit-server exists
            result = subprocess.run(['which', 'livekit-server'], capture_output=True, text=True)
            if result.returncode == 0:
                return f"LiveKit found at: {result.stdout.strip()}"
            else:
                return "LiveKit server not found (expected in Alpine container)"
        except Exception as e:
            return f"Error checking LiveKit: {e}"
    
    def get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                return f"{uptime_seconds:.1f} seconds"
        except:
            return "Unable to read uptime"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7880))
    print(f"🚀 Starting test server on port {port}")
    print(f"🌐 Visit https://emmaphone2-livekit-production.up.railway.app")
    print(f"📝 If you can see this in Railway logs, our debugging works!")
    
    server = HTTPServer(('0.0.0.0', port), TestHandler)
    print(f"✅ Server ready - Railway should show this message!")
    server.serve_forever()