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
from hardware.button import ButtonHandler
from services.wifi_manager import WiFiManager
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
        
        # TODO: Initialize LiveKit connection
        # TODO: Start call listening service
        # TODO: Handle button presses for speed dial
        
        # For now, just wait for button presses
        await self.button_handler.wait_for_press()
        
    async def start_setup_mode(self):
        """Start WiFi setup mode"""
        logger.info("🔧 Starting setup mode")
        
        # TODO: Start WiFi AP mode
        # TODO: Start web configuration server
        # TODO: Wait for configuration
        
        await self.led_controller.set_status("setup_mode")
        
    async def shutdown(self):
        """Clean shutdown of all services"""
        logger.info("🛑 Shutting down EmmaPhone2")
        self.running = False
        
        await self.led_controller.set_status("shutting_down")
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