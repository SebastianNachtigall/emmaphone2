#!/usr/bin/env python3
"""
Test script for EmmaPhone2 Pi Web Interface

This script starts just the web server for testing without hardware dependencies.
"""
import sys
import os
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / 'src'))

from config.settings import Settings
from web.server import PiWebServer

def main():
    """Test the web interface"""
    print("🚀 Testing EmmaPhone2 Pi Web Interface")
    print("=" * 50)
    
    # Initialize settings
    settings = Settings()
    
    # Create web server
    web_server = PiWebServer(settings, port=8080)
    
    print("Starting web interface on http://localhost:8080")
    print("Access from browser: http://localhost:8080")
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    try:
        # Run web server
        web_server.run(host='0.0.0.0', debug=True)
    except KeyboardInterrupt:
        print("\n👋 Stopping web interface")

if __name__ == "__main__":
    main()