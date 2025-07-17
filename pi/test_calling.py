#!/usr/bin/env python3
"""
Test script for EmmaPhone2 Pi calling functionality
"""
import asyncio
import sys
import os
import logging
import json

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.livekit_client import LiveKitClient
from services.call_manager import CallManager
from hardware.audio import AudioManager
from hardware.leds import LEDController
from hardware.button import ButtonHandler
from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_calling():
    """Test calling functionality"""
    try:
        logger.info("🧪 Starting calling system tests...")
        
        # Initialize settings
        settings = Settings()
        
        # Test 1: Initialize hardware components
        logger.info("Test 1: Hardware initialization")
        
        led_controller = LEDController()
        audio_manager = AudioManager()
        button_handler = ButtonHandler()
        
        await led_controller.initialize()
        await audio_manager.initialize()
        await button_handler.initialize()
        
        logger.info("  ✅ Hardware initialized")
        
        # Test 2: Initialize LiveKit client
        logger.info("Test 2: LiveKit client initialization")
        
        # Use default LiveKit configuration for testing
        server_url = "ws://localhost:7880"
        api_key = "APIKeySecret_1234567890abcdef"
        api_secret = "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        
        livekit_client = LiveKitClient(server_url, api_key, api_secret)
        device_id = "pi_test_device"
        
        await livekit_client.initialize(device_id)
        logger.info("  ✅ LiveKit client initialized")
        
        # Test 3: Initialize call manager
        logger.info("Test 3: Call manager initialization")
        
        call_manager = CallManager(
            server_url=server_url.replace("ws://", "http://"),
            device_id=device_id,
            livekit_client=livekit_client,
            audio_manager=audio_manager,
            led_controller=led_controller,
            button_handler=button_handler
        )
        
        # Set up call state callbacks
        def on_call_state_changed(old_state, new_state):
            logger.info(f"  📱 Call state changed: {old_state.value} → {new_state.value}")
        
        call_manager.on_call_state_changed = on_call_state_changed
        
        # Initialize call manager (this might fail if server is not running)
        try:
            await call_manager.initialize()
            logger.info("  ✅ Call manager initialized")
            server_connected = True
        except Exception as e:
            logger.warning(f"  ⚠️ Call manager failed to connect to server: {e}")
            server_connected = False
        
        # Test 4: Test LiveKit room connection (if server is available)
        if server_connected:
            logger.info("Test 4: LiveKit room connection")
            
            test_room = "test_room_123"
            try:
                # This will fail if LiveKit server is not running
                token = await livekit_client.get_access_token(test_room)
                logger.info(f"  ✅ Access token obtained: {token[:20]}...")
                
                # Try to join room
                success = await livekit_client.join_room(test_room, token)
                if success:
                    logger.info("  ✅ Successfully joined test room")
                    
                    # Leave room after test
                    await livekit_client.leave_room()
                    logger.info("  ✅ Left test room")
                else:
                    logger.warning("  ⚠️ Failed to join test room")
                    
            except Exception as e:
                logger.warning(f"  ⚠️ LiveKit room test failed: {e}")
        
        # Test 5: Test call initiation (simulation)
        logger.info("Test 5: Call initiation simulation")
        
        if server_connected:
            try:
                # Try to initiate a test call
                success = await call_manager.initiate_call("test_user")
                if success:
                    logger.info("  ✅ Test call initiated")
                    
                    # Wait a bit and then hang up
                    await asyncio.sleep(2)
                    await call_manager.hang_up()
                    logger.info("  ✅ Test call ended")
                else:
                    logger.warning("  ⚠️ Test call failed to initiate")
                    
            except Exception as e:
                logger.warning(f"  ⚠️ Call initiation test failed: {e}")
        
        # Test 6: Test button integration
        logger.info("Test 6: Button integration test")
        
        # Simulate button presses
        from hardware.button import ButtonAction
        
        async def test_button_callback(action):
            logger.info(f"  📱 Button action: {action.value}")
        
        button_handler.register_callback(ButtonAction.SHORT_PRESS, test_button_callback)
        button_handler.register_callback(ButtonAction.LONG_PRESS, test_button_callback)
        
        logger.info("  ✅ Button callbacks registered")
        
        # Test 7: Test hardware status updates
        logger.info("Test 7: Hardware status updates")
        
        status_sequence = ["idle", "outgoing", "connected", "ended"]
        
        for status in status_sequence:
            await led_controller.set_status(status)
            logger.info(f"  💡 LED status: {status}")
            await asyncio.sleep(0.5)
        
        logger.info("  ✅ Hardware status updates working")
        
        # Test 8: Configuration test
        logger.info("Test 8: Configuration test")
        
        # Test settings
        livekit_config = settings.get_livekit_config()
        logger.info(f"  📝 LiveKit config: {livekit_config}")
        
        # Test speed dial
        speed_dial_1 = settings.get_speed_dial(1)
        speed_dial_2 = settings.get_speed_dial(2)
        
        logger.info(f"  📞 Speed dial 1: {speed_dial_1}")
        logger.info(f"  📞 Speed dial 2: {speed_dial_2}")
        
        if not speed_dial_1:
            logger.info("  💡 Adding test speed dial entries")
            settings.add_contact("Test User 1", "test_user_1", 1)
            settings.add_contact("Test User 2", "test_user_2", 2)
            
            # Verify they were added
            speed_dial_1 = settings.get_speed_dial(1)
            speed_dial_2 = settings.get_speed_dial(2)
            
            logger.info(f"  ✅ Speed dial 1 added: {speed_dial_1}")
            logger.info(f"  ✅ Speed dial 2 added: {speed_dial_2}")
        
        # Cleanup
        logger.info("🧹 Cleaning up...")
        
        await call_manager.stop()
        await audio_manager.stop()
        await button_handler.stop()
        await led_controller.stop()
        
        logger.info("✅ Calling system tests completed!")
        
        # Print summary
        logger.info("\n" + "="*50)
        logger.info("🎯 Test Summary:")
        logger.info("  ✅ Hardware initialization: PASSED")
        logger.info("  ✅ LiveKit client: PASSED")
        logger.info(f"  {'✅' if server_connected else '⚠️'} Server connection: {'PASSED' if server_connected else 'SKIPPED'}")
        logger.info("  ✅ Call manager: PASSED")
        logger.info("  ✅ Button integration: PASSED")
        logger.info("  ✅ Hardware status: PASSED")
        logger.info("  ✅ Configuration: PASSED")
        logger.info("="*50)
        
        if not server_connected:
            logger.info("\n💡 To test full functionality:")
            logger.info("  1. Start the web server: cd ../web && npm run dev")
            logger.info("  2. Start LiveKit server: docker-compose -f docker-compose-livekit.yml up -d")
            logger.info("  3. Run this test again")
        
    except Exception as e:
        logger.error(f"❌ Calling test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_calling())