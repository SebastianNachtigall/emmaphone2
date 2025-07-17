#!/usr/bin/env python3
"""
Test Pi-to-Web calling with Railway LiveKit
"""
import asyncio
import sys
import os
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.livekit_client import LiveKitClient
from hardware.audio import AudioManager
from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pi_web_call():
    """Test Pi calling web users through Railway LiveKit"""
    try:
        logger.info("🧪 Testing Pi-to-Web calling via Railway LiveKit")
        
        # Load settings with Railway LiveKit config
        settings = Settings()
        livekit_config = settings.get_livekit_config()
        
        logger.info(f"🔗 LiveKit URL: {livekit_config['url']}")
        logger.info(f"🔑 API Key: {livekit_config['api_key']}")
        
        # Initialize hardware
        audio_manager = AudioManager()
        await audio_manager.initialize()
        
        # Initialize LiveKit client
        livekit_client = LiveKitClient(
            livekit_config['url'],
            livekit_config['api_key'],
            livekit_config['api_secret']
        )
        
        device_id = "pi_test_device"
        await livekit_client.initialize(device_id)
        
        # Test room connection
        test_room = "test_room_pi_web"
        logger.info(f"🏠 Joining room: {test_room}")
        
        success = await livekit_client.join_room(test_room)
        
        if success:
            logger.info("✅ Successfully connected to Railway LiveKit!")
            logger.info("🎤 Pi is now in the room - web users can join the same room")
            
            # Stay in room for a bit
            logger.info("⏳ Staying in room for 30 seconds...")
            logger.info("💡 Go to https://emmaphone2-production.up.railway.app/")
            logger.info("💡 Join the room 'test_room_pi_web' to test audio")
            
            await asyncio.sleep(30)
            
            # Leave room
            await livekit_client.leave_room()
            logger.info("📤 Left room")
            
        else:
            logger.error("❌ Failed to connect to LiveKit")
        
        # Cleanup
        await livekit_client.stop()
        await audio_manager.stop()
        
        logger.info("✅ Test completed!")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_pi_web_call())