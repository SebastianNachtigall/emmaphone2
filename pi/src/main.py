#!/usr/bin/env python3
"""
EmmaPhone2 Pi Main Application

Kid-friendly hardware calling device using LiveKit and ReSpeaker HAT.
"""
import asyncio
import logging
import signal
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from hardware.leds import LEDController
from hardware.audio import AudioManager
from hardware.button import ButtonHandler, ButtonAction
from services.wifi_manager import WiFiManager
from services.livekit_client import LiveKitClient
from services.call_manager import CallManager
from config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class EmmaPhoneApp:
    """Main EmmaPhone2 Pi Application"""
    
    def __init__(self):
        self.settings = Settings()
        self.led_controller = LEDController()
        self.audio_manager = AudioManager()
        self.button_handler = ButtonHandler()
        self.wifi_manager = WiFiManager()
        
        # Calling system components
        self.livekit_client = None
        self.call_manager = None
        
        self.running = False
        
    async def initialize(self):
        """Initialize all hardware and services"""
        logger.info("🚀 Starting EmmaPhone2 Pi Application")
        
        # Initialize hardware
        await self.led_controller.initialize()
        await self.audio_manager.initialize()
        await self.button_handler.initialize()
        
        # Show startup LED pattern
        await self.led_controller.show_startup_pattern()
        
        # Check WiFi status
        if await self.wifi_manager.is_connected():
            logger.info("✅ WiFi connected")
            await self.led_controller.set_status("connected")
            await self.start_main_app()
        else:
            logger.info("❌ WiFi not connected - starting setup mode")
            await self.led_controller.set_status("setup_needed")
            await self.start_setup_mode()
    
    async def start_main_app(self):
        """Start the main calling application"""
        logger.info("📞 Starting main calling application")
        await self.led_controller.set_status("ready")
        
        try:
            # Initialize LiveKit client
            livekit_config = self.settings.get_livekit_config()
            server_url = livekit_config.get("url", "ws://localhost:7880")
            api_key = livekit_config.get("api_key", "")
            api_secret = livekit_config.get("api_secret", "")
            
            if not api_key or not api_secret:
                logger.error("❌ LiveKit credentials not configured")
                await self.led_controller.set_status("setup_needed")
                return
            
            self.livekit_client = LiveKitClient(server_url, api_key, api_secret)
            
            # Get device identity
            device_id = f"pi_{self.settings.get('device.id', 'unknown')}"
            await self.livekit_client.initialize(device_id)
            
            # Initialize call manager
            self.call_manager = CallManager(
                server_url=server_url.replace("ws://", "http://").replace("wss://", "https://"),
                device_id=device_id,
                livekit_client=self.livekit_client,
                audio_manager=self.audio_manager,
                led_controller=self.led_controller,
                button_handler=self.button_handler
            )
            
            await self.call_manager.initialize()
            
            # Register device with server
            device_name = self.settings.get('device.name', 'EmmaPhone Pi')
            user_id = self.settings.get('user.id', '1')  # Default to first user
            
            await self.call_manager.register_device(device_name, user_id)
            
            logger.info("✅ Calling system initialized")
            
            # Set up button handlers for speed dial
            self.button_handler.register_callback(
                ButtonAction.DOUBLE_PRESS, 
                self._on_speed_dial_1
            )
            self.button_handler.register_callback(
                ButtonAction.TRIPLE_PRESS, 
                self._on_speed_dial_2
            )
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize calling system: {e}")
            await self.led_controller.set_status("error")
            return
        
    async def start_setup_mode(self):
        """Start WiFi setup mode"""
        logger.info("🔧 Starting setup mode")
        
        # TODO: Start WiFi AP mode
        # TODO: Start web configuration server
        # TODO: Wait for configuration
        
        await self.led_controller.set_status("setup_mode")
    
    async def _on_speed_dial_1(self, action):
        """Handle speed dial 1 (double press)"""
        try:
            if not self.call_manager:
                logger.warning("⚠️ Call manager not initialized")
                return
            
            # Get speed dial contact
            contact_id = self.settings.get_speed_dial(1)
            if not contact_id:
                logger.warning("⚠️ No speed dial contact configured for position 1")
                await self.led_controller.set_status("error")
                await asyncio.sleep(1)
                await self.led_controller.set_status("ready")
                return
            
            logger.info(f"📞 Speed dial 1: calling {contact_id}")
            await self.call_manager.initiate_call(contact_id)
            
        except Exception as e:
            logger.error(f"❌ Speed dial 1 failed: {e}")
    
    async def _on_speed_dial_2(self, action):
        """Handle speed dial 2 (triple press)"""
        try:
            if not self.call_manager:
                logger.warning("⚠️ Call manager not initialized")
                return
            
            # Get speed dial contact
            contact_id = self.settings.get_speed_dial(2)
            if not contact_id:
                logger.warning("⚠️ No speed dial contact configured for position 2")
                await self.led_controller.set_status("error")
                await asyncio.sleep(1)
                await self.led_controller.set_status("ready")
                return
            
            logger.info(f"📞 Speed dial 2: calling {contact_id}")
            await self.call_manager.initiate_call(contact_id)
            
        except Exception as e:
            logger.error(f"❌ Speed dial 2 failed: {e}")
        
    async def shutdown(self):
        """Clean shutdown of all services"""
        logger.info("🛑 Shutting down EmmaPhone2")
        self.running = False
        
        await self.led_controller.set_status("shutting_down")
        
        # Stop calling system
        if self.call_manager:
            await self.call_manager.stop()
        
        # Stop hardware
        await self.audio_manager.stop()
        await self.button_handler.stop()
        await self.led_controller.stop()
        
        logger.info("✅ Shutdown complete")

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}, shutting down...")
    sys.exit(0)

async def main():
    """Main entry point"""
    # Setup signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    app = EmmaPhoneApp()
    
    try:
        await app.initialize()
        app.running = True
        
        # Keep running until shutdown
        while app.running:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt")
    except Exception as e:
        logger.error(f"Application error: {e}")
    finally:
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())