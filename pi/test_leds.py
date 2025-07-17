#!/usr/bin/env python3
"""
Test script for ReSpeaker 2-Mics Pi HAT LED functionality
"""
import asyncio
import sys
import os
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hardware.leds import LEDController

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_leds():
    """Test LED functionality"""
    try:
        # Initialize LED controller
        led_controller = LEDController()
        await led_controller.initialize()
        
        logger.info("🧪 Starting LED tests...")
        
        # Test 1: Basic colors
        logger.info("Test 1: Basic colors")
        colors = [
            ([255, 0, 0], "Red"),
            ([0, 255, 0], "Green"), 
            ([0, 0, 255], "Blue"),
            ([255, 255, 0], "Yellow"),
            ([255, 0, 255], "Magenta"),
            ([0, 255, 255], "Cyan"),
            ([255, 255, 255], "White")
        ]
        
        for color, name in colors:
            logger.info(f"  → {name}")
            await led_controller.set_all_leds(color)
            await asyncio.sleep(1)
        
        # Test 2: Individual LED control
        logger.info("Test 2: Individual LED control")
        await led_controller.set_all_leds([0, 0, 0])  # Turn off all
        await asyncio.sleep(0.5)
        
        # Light up each LED individually
        for i in range(3):
            logger.info(f"  → LED {i}")
            await led_controller.set_led(i, [255, 255, 255])
            await asyncio.sleep(0.5)
            await led_controller.set_led(i, [0, 0, 0])
            await asyncio.sleep(0.5)
        
        # Test 3: Status patterns
        logger.info("Test 3: Status patterns")
        statuses = ['startup', 'ready', 'incoming_call', 'connected', 'error']
        
        for status in statuses:
            logger.info(f"  → {status}")
            await led_controller.set_status(status)
            await asyncio.sleep(2)
        
        # Test 4: Breathing effect
        logger.info("Test 4: Breathing effect")
        await led_controller.set_all_leds([0, 255, 0])  # Green base
        
        for brightness in range(0, 256, 20):
            await led_controller.set_brightness(brightness)
            await asyncio.sleep(0.1)
        
        for brightness in range(255, -1, -20):
            await led_controller.set_brightness(brightness)
            await asyncio.sleep(0.1)
        
        # Test 5: Rainbow effect
        logger.info("Test 5: Rainbow effect")
        await led_controller.set_brightness(100)
        
        for hue in range(0, 360, 30):
            # Convert HSV to RGB
            import colorsys
            r, g, b = colorsys.hsv_to_rgb(hue/360, 1.0, 1.0)
            color = [int(r*255), int(g*255), int(b*255)]
            await led_controller.set_all_leds(color)
            await asyncio.sleep(0.2)
        
        # Cleanup
        logger.info("🧹 Cleaning up...")
        await led_controller.set_all_leds([0, 0, 0])  # Turn off all LEDs
        await led_controller.stop()
        
        logger.info("✅ LED tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ LED test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_leds())