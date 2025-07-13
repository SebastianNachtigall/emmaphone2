#!/usr/bin/env python3
import os
import subprocess
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

class LiveKitTestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        
        # Get environment info
        env_info = []
        for key, value in sorted(os.environ.items()):
            if any(x in key.upper() for x in ['PORT', 'RAILWAY', 'LIVEKIT', 'REDIS']):
                env_info.append(f"{key}={value}")
        
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LiveKit + Railway Debug</title>
            <meta http-equiv="refresh" content="10">
            <style>
                body {{ font-family: monospace; margin: 20px; }}
                pre {{ background: #f0f0f0; padding: 10px; overflow: auto; max-height: 300px; }}
                h2 {{ color: #333; border-bottom: 1px solid #ccc; }}
                .error {{ color: red; }}
                .success {{ color: green; }}
            </style>
        </head>
        <body>
            <h1>🔍 LiveKit + Railway Debug - {time.ctime()}</h1>
            
            <h2>🌍 Environment Variables</h2>
            <pre>{"<br>".join(env_info)}</pre>
            
            <h2>📁 File System Check</h2>
            <pre>{self.get_filesystem()}</pre>
            
            <h2>🚀 LiveKit Binary Info</h2>
            <pre>{self.get_livekit_info()}</pre>
            
            <h2>🧪 LiveKit Tests</h2>
            <pre>{self.test_livekit_commands()}</pre>
            
            <h2>🎯 Final LiveKit Test</h2>
            <pre>{self.get_livekit_test_result()}</pre>
            
            <h2>📊 Container Status</h2>
            <pre>
Working Directory: {os.getcwd()}
Python Version: {subprocess.run(['python3', '--version'], capture_output=True, text=True).stdout.strip()}
User: {subprocess.run(['id'], capture_output=True, text=True).stdout.strip()}
Uptime: {self.get_uptime()}
            </pre>
        </body>
        </html>
        """
        self.wfile.write(html.encode())
    
    def get_filesystem(self):
        try:
            result = subprocess.run(['ls', '-la', '/usr/bin/livekit*'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return f"LiveKit binaries found:\n{result.stdout}"
            else:
                return f"No LiveKit binaries found in /usr/bin/\nError: {result.stderr}"
        except Exception as e:
            return f"Error: {e}"
    
    def get_livekit_info(self):
        try:
            output = ""
            
            # Check which
            result1 = subprocess.run(['which', 'livekit-server'], capture_output=True, text=True)
            output += f"which livekit-server: {result1.returncode}\n"
            output += f"Path: {result1.stdout.strip()}\n"
            output += f"Error: {result1.stderr}\n\n"
            
            # Check version
            result2 = subprocess.run(['livekit-server', '--version'], capture_output=True, text=True, timeout=10)
            output += f"livekit-server --version: {result2.returncode}\n"
            output += f"Output: {result2.stdout}\n"
            output += f"Error: {result2.stderr}\n\n"
            
            return output
        except Exception as e:
            return f"Error getting LiveKit info: {e}"
    
    def test_livekit_commands(self):
        try:
            output = ""
            
            # Test 1: Help command
            result1 = subprocess.run(['livekit-server', '--help'], capture_output=True, text=True, timeout=10)
            help_lines = result1.stdout.split('\n')[:20] if result1.stdout else []
            output += f"HELP TEST - Exit code: {result1.returncode}\n"
            output += f"First 20 lines:\n" + '\n'.join(help_lines) + "\n"
            output += f"Stderr: {result1.stderr}\n\n"
            
            # Test 2: Simple keys test
            result2 = subprocess.run(['livekit-server', '--keys', 'test:test'], 
                                   capture_output=True, text=True, timeout=5)
            output += f"SIMPLE KEYS TEST - Exit code: {result2.returncode}\n"
            output += f"Stdout: {result2.stdout}\n"
            output += f"Stderr: {result2.stderr}\n\n"
            
            return output
        except subprocess.TimeoutExpired:
            return "Commands timed out (might be working or hanging)"
        except Exception as e:
            return f"Error testing commands: {e}"
    
    def get_livekit_test_result(self):
        global livekit_test_result
        return livekit_test_result
    
    def get_uptime(self):
        try:
            with open('/proc/uptime', 'r') as f:
                uptime_seconds = float(f.read().split()[0])
                return f"{uptime_seconds:.1f} seconds"
        except:
            return "Unable to read uptime"

# Global variable to store LiveKit test results
livekit_test_result = "Test not started yet..."

def test_livekit_in_background():
    """Test LiveKit in the background and store results"""
    global livekit_test_result
    
    time.sleep(5)  # Give web server time to start
    
    livekit_test_result = "Testing LiveKit with real keys...\n"
    
    try:
        # Test with the real keys that were failing
        result = subprocess.run([
            'livekit-server',
            '--keys', 'APIKeySecret_1234567890abcdef:abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890',
            '--bind', '0.0.0.0',
            '--port', '7881',  # Use different port so web server can keep running
            '--log-level', 'debug'
        ], capture_output=True, text=True, timeout=15)
        
        livekit_test_result += f"REAL KEYS TEST COMPLETED\n"
        livekit_test_result += f"Exit code: {result.returncode}\n"
        livekit_test_result += f"Stdout (first 50 lines):\n"
        livekit_test_result += '\n'.join(result.stdout.split('\n')[:50]) + "\n"
        livekit_test_result += f"\nStderr (first 50 lines):\n"
        livekit_test_result += '\n'.join(result.stderr.split('\n')[:50]) + "\n"
        
    except subprocess.TimeoutExpired:
        livekit_test_result += "LiveKit test timed out after 15 seconds (might be running successfully!)\n"
    except Exception as e:
        livekit_test_result += f"Error during LiveKit test: {e}\n"

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 7880))
    print(f"🚀 Starting LiveKit debug server on port {port}")
    print(f"🌐 Visit https://emmaphone2-livekit-production.up.railway.app")
    print(f"🔍 Will test LiveKit in background after 5 seconds...")
    
    # Start LiveKit test in background
    threading.Thread(target=test_livekit_in_background, daemon=True).start()
    
    server = HTTPServer(('0.0.0.0', port), LiveKitTestHandler)
    print(f"✅ Debug server ready!")
    server.serve_forever()