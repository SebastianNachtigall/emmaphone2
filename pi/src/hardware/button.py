"""
Button Handler for ReSpeaker 2-Mics Pi HAT

Handles the user button on GPIO17 with keyboard fallback for development
"""
import asyncio
import logging
import sys
from enum import Enum
from typing import Optional, Callable

try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except ImportError:
    GPIO_AVAILABLE = False

logger = logging.getLogger(__name__)

class ButtonAction(Enum):
    """Button action types"""
    SHORT_PRESS = "short_press"
    LONG_PRESS = "long_press"
    DOUBLE_PRESS = "double_press"
    TRIPLE_PRESS = "triple_press"

class ButtonHandler:
    """Handles button presses on GPIO17 with keyboard fallback"""
    
    BUTTON_PIN = 17
    LONG_PRESS_TIME = 1.0  # seconds
    DOUBLE_PRESS_TIME = 0.5  # seconds
    TRIPLE_PRESS_TIME = 0.5  # seconds
    
    def __init__(self, use_keyboard: bool = True):
        self.use_keyboard = use_keyboard and not GPIO_AVAILABLE
        self.callbacks = {}
        self.running = False
        self.last_press_time = 0
        self.press_count = 0
        self.keyboard_task = None
        
    async def initialize(self):
        """Initialize button handler"""
        if GPIO_AVAILABLE and not self.use_keyboard:
            try:
                # Clean up any existing GPIO setup
                try:
                    GPIO.cleanup()
                except:
                    pass
                
                # Initialize GPIO
                GPIO.setmode(GPIO.BCM)
                GPIO.setup(self.BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
                # Small delay to ensure GPIO is ready
                await asyncio.sleep(0.1)
                
                # Set up interrupt for button press
                GPIO.add_event_detect(
                    self.BUTTON_PIN, 
                    GPIO.FALLING,
                    callback=self._gpio_callback,
                    bouncetime=200  # 200ms debounce
                )
                
                logger.info("✅ Button handler initialized (GPIO)")
                
            except Exception as e:
                logger.error(f"❌ Failed to initialize GPIO, falling back to keyboard: {e}")
                logger.error(f"   Error details: {type(e).__name__}: {e}")
                self.use_keyboard = True
        
        if self.use_keyboard:
            logger.info("⌨️  Button handler initialized (keyboard fallback)")
            logger.info("💡 Press keys: 's'=short, 'l'=long, 'd'=double, 't'=triple, 'q'=quit")
            self.keyboard_task = asyncio.create_task(self._keyboard_handler())
        
        self.running = True
    
    def _gpio_callback(self, channel):
        """GPIO interrupt callback"""
        if channel == self.BUTTON_PIN:
            asyncio.create_task(self._handle_button_press())
    
    async def _handle_button_press(self):
        """Handle button press logic"""
        current_time = asyncio.get_event_loop().time()
        
        # Reset press count if too much time has passed
        if current_time - self.last_press_time > self.TRIPLE_PRESS_TIME:
            self.press_count = 0
        
        self.press_count += 1
        self.last_press_time = current_time
        
        # Wait to see if more presses are coming
        await asyncio.sleep(self.TRIPLE_PRESS_TIME)
        
        # Check if this is still the latest press
        if current_time == self.last_press_time:
            await self._determine_action()
    
    async def _determine_action(self):
        """Determine what type of button action occurred"""
        if self.press_count == 1:
            # Check if it's a long press
            if not self.use_keyboard:
                # For GPIO, check if button is still pressed
                if GPIO.input(self.BUTTON_PIN) == GPIO.LOW:
                    await asyncio.sleep(self.LONG_PRESS_TIME)
                    if GPIO.input(self.BUTTON_PIN) == GPIO.LOW:
                        action = ButtonAction.LONG_PRESS
                    else:
                        action = ButtonAction.SHORT_PRESS
                else:
                    action = ButtonAction.SHORT_PRESS
            else:
                action = ButtonAction.SHORT_PRESS
        elif self.press_count == 2:
            action = ButtonAction.DOUBLE_PRESS
        elif self.press_count >= 3:
            action = ButtonAction.TRIPLE_PRESS
        else:
            return
        
        # Reset press count
        self.press_count = 0
        
        # Execute callback
        await self._execute_callback(action)
    
    async def _keyboard_handler(self):
        """Handle keyboard input for development"""
        while self.running:
            try:
                # Non-blocking keyboard input
                if sys.stdin.isatty():
                    import select
                    if select.select([sys.stdin], [], [], 0.1)[0]:
                        key = sys.stdin.read(1).lower()
                        
                        action_map = {
                            's': ButtonAction.SHORT_PRESS,
                            'l': ButtonAction.LONG_PRESS,
                            'd': ButtonAction.DOUBLE_PRESS,
                            't': ButtonAction.TRIPLE_PRESS,
                            'q': None  # Quit
                        }
                        
                        if key in action_map:
                            if key == 'q':
                                logger.info("🛑 Quit requested via keyboard")
                                self.running = False
                                break
                            else:
                                await self._execute_callback(action_map[key])
                
                await asyncio.sleep(0.1)
                
            except Exception as e:
                logger.error(f"❌ Keyboard handler error: {e}")
                await asyncio.sleep(0.5)
    
    async def _execute_callback(self, action: ButtonAction):
        """Execute registered callback for action"""
        if action in self.callbacks:
            try:
                callback = self.callbacks[action]
                if asyncio.iscoroutinefunction(callback):
                    await callback(action)
                else:
                    callback(action)
                    
                logger.info(f"🔘 Button action executed: {action.value}")
                
            except Exception as e:
                logger.error(f"❌ Callback error for {action.value}: {e}")
        else:
            logger.info(f"🔘 Button action (no callback): {action.value}")
    
    def register_callback(self, action: ButtonAction, callback: Callable):
        """Register callback for button action"""
        self.callbacks[action] = callback
        logger.info(f"📝 Registered callback for {action.value}")
    
    async def wait_for_press(self):
        """Wait for any button press (utility method)"""
        press_detected = asyncio.Event()
        
        def temp_callback(action):
            press_detected.set()
        
        # Register temporary callback for all actions
        for action in ButtonAction:
            self.register_callback(action, temp_callback)
        
        await press_detected.wait()
        
        # Clear temporary callbacks
        self.callbacks.clear()
    
    async def stop(self):
        """Stop button handler and cleanup"""
        self.running = False
        
        if self.keyboard_task:
            self.keyboard_task.cancel()
        
        if GPIO_AVAILABLE and not self.use_keyboard:
            try:
                GPIO.remove_event_detect(self.BUTTON_PIN)
                GPIO.cleanup()
            except:
                pass
        
        logger.info("🛑 Button handler stopped")