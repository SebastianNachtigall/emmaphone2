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
from services.call_manager_v2 import CallManagerV2
from services.user_manager import UserManager
from config.settings import Settings
from web.server import PiWebServer

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
        self.user_manager = None
        self.call_manager = None
        
        # Web interface
        self.web_server = None
        
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
            
            # Check if user is configured
            if self.settings.is_user_configured():
                await self.start_main_app()
            else:
                logger.info("❌ User not configured - starting setup mode")
                await self.led_controller.set_status("setup_needed")
                await self.start_user_setup()
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
            
            # Initialize user manager
            self.user_manager = UserManager(self.settings)
            await self.user_manager.initialize()
            
            # Initialize call manager with user management
            self.call_manager = CallManagerV2(
                livekit_client=self.livekit_client,
                audio_manager=self.audio_manager,
                led_controller=self.led_controller,
                button_handler=self.button_handler,
                user_manager=self.user_manager,
                device_id=device_id
            )
            
            await self.call_manager.initialize()
            
            logger.info("✅ Calling system initialized")
            
            # Initialize web server
            await self.start_web_server()
            
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
        logger.info("🔧 Starting WiFi setup mode")
        
        # TODO: Start WiFi AP mode
        # TODO: Start web configuration server
        # TODO: Wait for configuration
        
        await self.led_controller.set_status("setup_mode")
    
    async def start_user_setup(self):
        """Start user setup mode"""
        logger.info("👤 User setup required")
        
        # Show setup needed status
        await self.led_controller.set_status("setup_needed")
        
        # Display instructions
        logger.info("=" * 50)
        logger.info("🚀 EmmaPhone2 Pi User Setup Required")
        logger.info("=" * 50)
        logger.info("Please run the following command to set up your user:")
        logger.info("python3 setup_user.py")
        logger.info("")
        logger.info("After setup, restart the Pi application:")
        logger.info("python3 src/main.py")
        logger.info("=" * 50)
        
        # Keep showing setup needed status
        while not self.settings.is_user_configured():
            await asyncio.sleep(5)
            await self.led_controller.set_status("setup_needed")
        
        logger.info("✅ User configuration detected - restarting application")
        await self.start_main_app()
    
    async def start_web_server(self):
        """Start the web interface server"""
        try:
            web_port = self.settings.get('web_server.port', 8080)
            
            # Initialize web server
            self.web_server = PiWebServer(self.settings, port=web_port)
            
            # Set manager references for status monitoring
            self.web_server.set_managers(
                call_manager=self.call_manager,
                user_manager=self.user_manager,
                audio_manager=self.audio_manager,
                led_controller=self.led_controller
            )
            
            # Start web server in background thread
            import threading
            web_thread = threading.Thread(
                target=self.web_server.run, 
                kwargs={'host': '0.0.0.0', 'debug': False},
                daemon=True
            )
            web_thread.start()
            
            logger.info(f"✅ Web interface started on http://0.0.0.0:{web_port}")
            logger.info(f"💻 Access from browser: http://pi.local:{web_port} or http://<pi-ip>:{web_port}")
            
        except Exception as e:
            logger.error(f"❌ Failed to start web server: {e}")
            # Don't fail the whole app if web server fails
    
    async def _on_speed_dial_1(self, action):
        """Handle speed dial 1 (double press)"""
        try:
            if not self.call_manager:
                logger.warning("⚠️ Call manager not initialized")
                return
            
            # Get speed dial user ID
            user_id = self.settings.get_speed_dial(1)
            if not user_id:
                logger.warning("⚠️ No speed dial contact configured for position 1")
                await self.led_controller.set_status("error")
                await asyncio.sleep(1)
                await self.led_controller.set_status("ready")
                return
            
            logger.info(f"📞 Speed dial 1: calling user {user_id}")
            await self.call_manager.initiate_call(user_id)
            
        except Exception as e:
            logger.error(f"❌ Speed dial 1 failed: {e}")
    
    async def _on_speed_dial_2(self, action):
        """Handle speed dial 2 (triple press)"""
        try:
            if not self.call_manager:
                logger.warning("⚠️ Call manager not initialized")
                return
            
            # Get speed dial user ID
            user_id = self.settings.get_speed_dial(2)
            if not user_id:
                logger.warning("⚠️ No speed dial contact configured for position 2")
                await self.led_controller.set_status("error")
                await asyncio.sleep(1)
                await self.led_controller.set_status("ready")
                return
            
            logger.info(f"📞 Speed dial 2: calling user {user_id}")
            await self.call_manager.initiate_call(user_id)
            
        except Exception as e:
            logger.error(f"❌ Speed dial 2 failed: {e}")
        
    async def shutdown(self):
        """Clean shutdown of all services"""
        logger.info("🛑 Shutting down EmmaPhone2")
        self.running = False
        
        await self.led_controller.set_status("shutting_down")
        
        # Stop web server
        if self.web_server:
            self.web_server.stop()
        
        # Stop calling system
        if self.call_manager:
            await self.call_manager.stop()
        
        # Stop user manager
        if self.user_manager:
            await self.user_manager.close()
        
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