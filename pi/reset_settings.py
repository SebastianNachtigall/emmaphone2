#!/usr/bin/env python3
"""
Reset Pi settings to use Railway LiveKit configuration
"""
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Settings

def reset_settings():
    """Reset settings to defaults with Railway LiveKit config"""
    settings = Settings()
    
    # Force reset to defaults
    settings.reset_to_defaults()
    
    # Verify the settings
    livekit_config = settings.get_livekit_config()
    print("✅ Settings reset!")
    print(f"LiveKit URL: {livekit_config['url']}")
    print(f"API Key: {livekit_config['api_key']}")
    print(f"API Secret: {livekit_config['api_secret'][:20]}...")

if __name__ == "__main__":
    reset_settings()