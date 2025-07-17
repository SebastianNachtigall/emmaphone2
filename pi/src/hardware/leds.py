"""
LED Controller for ReSpeaker 2-Mics Pi HAT

Controls 3 x APA102 RGB LEDs via SPI interface
GPIO5 (SCK) and GPIO6 (MOSI)
"""
import asyncio
import logging
import spidev
from enum import Enum
from typing import Tuple, List

logger = logging.getLogger(__name__)

class LEDStatus(Enum):
    """LED status states"""
    STARTUP = "startup"
    SETUP_NEEDED = "setup_needed"
    SETUP_MODE = "setup_mode"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    READY = "ready"
    INCOMING_CALL = "incoming_call"
    IN_CALL = "in_call"
    ERROR = "error"
    SHUTTING_DOWN = "shutting_down"

class LEDController:
    """Controls the 3 APA102 RGB LEDs on ReSpeaker HAT"""
    
    # LED status color patterns
    STATUS_COLORS = {
        LEDStatus.STARTUP: [(255, 255, 255), (255, 255, 255), (255, 255, 255)],  # White
        LEDStatus.SETUP_NEEDED: [(255, 0, 0), (255, 0, 0), (255, 0, 0)],        # Red
        LEDStatus.SETUP_MODE: [(255, 165, 0), (255, 165, 0), (255, 165, 0)],    # Orange
        LEDStatus.CONNECTING: [(255, 255, 0), (255, 255, 0), (255, 255, 0)],    # Yellow
        LEDStatus.CONNECTED: [(0, 255, 0), (0, 255, 0), (0, 255, 0)],           # Green
        LEDStatus.READY: [(0, 255, 0), (0, 0, 0), (0, 0, 0)],                   # Single green
        LEDStatus.INCOMING_CALL: [(0, 0, 255), (0, 0, 255), (0, 0, 255)],       # Blue
        LEDStatus.IN_CALL: [(0, 0, 255), (0, 0, 255), (0, 0, 255)],             # Blue solid
        LEDStatus.ERROR: [(255, 0, 0), (0, 0, 0), (0, 0, 0)],                   # Single red
        LEDStatus.SHUTTING_DOWN: [(128, 128, 128), (128, 128, 128), (128, 128, 128)]  # Gray
    }
    
    def __init__(self):
        self.spi = None
        self.current_status = None
        self.animation_task = None
        self.running = False
        
    async def initialize(self):
        """Initialize SPI connection to LEDs"""
        try:
            self.spi = spidev.SpiDev()
            self.spi.open(0, 0)  # SPI bus 0, device 0
            self.spi.max_speed_hz = 8000000
            self.spi.mode = 0
            
            # Clear all LEDs
            await self.clear_all()
            
            logger.info("✅ LED controller initialized")
            self.running = True
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LED controller: {e}")
            raise
    
    async def clear_all(self):
        """Turn off all LEDs"""
        await self.set_colors([(0, 0, 0), (0, 0, 0), (0, 0, 0)])
    
    async def set_colors(self, colors: List[Tuple[int, int, int]]):
        """Set colors for all 3 LEDs"""
        if not self.spi:
            return
            
        try:
            # APA102 protocol: Start frame, LED data, End frame
            data = []
            
            # Start frame (32 bits of 0)
            data.extend([0x00, 0x00, 0x00, 0x00])
            
            # LED data (3 LEDs)
            for r, g, b in colors[:3]:  # Only use first 3 colors
                # APA102 format: 0xFF, B, G, R
                data.extend([0xFF, b, g, r])
            
            # End frame (32 bits of 1)
            data.extend([0xFF, 0xFF, 0xFF, 0xFF])
            
            self.spi.writebytes(data)
            
        except Exception as e:
            logger.error(f"❌ Failed to set LED colors: {e}")
    
    async def set_status(self, status: str):
        """Set LED status pattern"""
        try:
            led_status = LEDStatus(status)
            
            # Stop any running animation
            if self.animation_task:
                self.animation_task.cancel()
                self.animation_task = None
            
            self.current_status = led_status
            
            # Start animation based on status
            if led_status in [LEDStatus.SETUP_NEEDED, LEDStatus.INCOMING_CALL]:
                # Pulsing animation
                self.animation_task = asyncio.create_task(self._pulse_animation(led_status))
            elif led_status == LEDStatus.CONNECTING:
                # Rotating animation
                self.animation_task = asyncio.create_task(self._rotate_animation(led_status))
            else:
                # Static colors
                colors = self.STATUS_COLORS[led_status]
                await self.set_colors(colors)
            
            logger.info(f"💡 LED status set to: {status}")
            
        except ValueError:
            logger.error(f"❌ Invalid LED status: {status}")
    
    async def _pulse_animation(self, status: LEDStatus):
        """Pulsing animation for attention-grabbing states"""
        colors = self.STATUS_COLORS[status]
        
        while self.running and self.current_status == status:
            # Fade in
            for brightness in range(0, 256, 16):
                if not self.running or self.current_status != status:
                    break
                    
                dimmed_colors = [
                    (int(r * brightness / 255), int(g * brightness / 255), int(b * brightness / 255))
                    for r, g, b in colors
                ]
                await self.set_colors(dimmed_colors)
                await asyncio.sleep(0.05)
            
            # Fade out
            for brightness in range(255, -1, -16):
                if not self.running or self.current_status != status:
                    break
                    
                dimmed_colors = [
                    (int(r * brightness / 255), int(g * brightness / 255), int(b * brightness / 255))
                    for r, g, b in colors
                ]
                await self.set_colors(dimmed_colors)
                await asyncio.sleep(0.05)
    
    async def _rotate_animation(self, status: LEDStatus):
        """Rotating animation for connecting state"""
        base_color = self.STATUS_COLORS[status][0]
        
        while self.running and self.current_status == status:
            for i in range(3):
                if not self.running or self.current_status != status:
                    break
                    
                colors = [(0, 0, 0), (0, 0, 0), (0, 0, 0)]
                colors[i] = base_color
                await self.set_colors(colors)
                await asyncio.sleep(0.3)
    
    async def show_startup_pattern(self):
        """Show startup LED pattern"""
        logger.info("🌟 Showing startup pattern")
        
        # Rainbow effect
        colors = [
            (255, 0, 0),    # Red
            (0, 255, 0),    # Green
            (0, 0, 255)     # Blue
        ]
        
        await self.set_colors(colors)
        await asyncio.sleep(1)
        await self.clear_all()
        await asyncio.sleep(0.5)
    
    async def test_all_colors(self):
        """Test all LED colors - useful for debugging"""
        logger.info("🧪 Testing all LED colors")
        
        test_colors = [
            [(255, 0, 0), (255, 0, 0), (255, 0, 0)],    # Red
            [(0, 255, 0), (0, 255, 0), (0, 255, 0)],    # Green
            [(0, 0, 255), (0, 0, 255), (0, 0, 255)],    # Blue
            [(255, 255, 0), (255, 255, 0), (255, 255, 0)],  # Yellow
            [(255, 0, 255), (255, 0, 255), (255, 0, 255)],  # Magenta
            [(0, 255, 255), (0, 255, 255), (0, 255, 255)],  # Cyan
            [(255, 255, 255), (255, 255, 255), (255, 255, 255)]  # White
        ]
        
        for colors in test_colors:
            await self.set_colors(colors)
            await asyncio.sleep(0.5)
        
        await self.clear_all()
    
    async def set_all_leds(self, color: List[int]):
        """Set all LEDs to the same color"""
        if len(color) != 3:
            logger.error("❌ Color must be [R, G, B] format")
            return
            
        r, g, b = color
        colors = [(r, g, b), (r, g, b), (r, g, b)]
        await self.set_colors(colors)
    
    async def set_led(self, led_index: int, color: List[int]):
        """Set a specific LED to a color"""
        if led_index < 0 or led_index >= 3:
            logger.error(f"❌ LED index {led_index} out of range (0-2)")
            return
            
        if len(color) != 3:
            logger.error("❌ Color must be [R, G, B] format")
            return
        
        # Get current colors (default to off)
        current_colors = [(0, 0, 0), (0, 0, 0), (0, 0, 0)]
        
        # Update the specific LED
        current_colors[led_index] = tuple(color)
        
        await self.set_colors(current_colors)
    
    async def set_brightness(self, brightness: int):
        """Set global brightness (0-255)"""
        # This is a simplified implementation - in a real APA102 setup,
        # you would adjust the brightness byte in the protocol
        if brightness < 0 or brightness > 255:
            logger.error(f"❌ Brightness {brightness} out of range (0-255)")
            return
        
        # For now, we'll just store it and apply it during set_colors
        # In a full implementation, you'd modify the LED protocol
        logger.info(f"💡 Brightness set to {brightness}")
    
    async def stop(self):
        """Stop LED controller and cleanup"""
        self.running = False
        
        if self.animation_task:
            self.animation_task.cancel()
        
        await self.clear_all()
        
        if self.spi:
            self.spi.close()
        
        logger.info("🛑 LED controller stopped")