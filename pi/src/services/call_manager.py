"""
Call Manager for EmmaPhone2 Pi

Manages call state, integrates with hardware, and handles call signaling
"""
import asyncio
import logging
import json
import aiohttp
import socketio
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from .livekit_client import LiveKitClient
from ..hardware.audio import AudioManager
from ..hardware.leds import LEDController
from ..hardware.button import ButtonHandler, ButtonAction

logger = logging.getLogger(__name__)

class CallState(Enum):
    """Call state enumeration"""
    IDLE = "idle"
    OUTGOING = "outgoing"
    INCOMING = "incoming"
    RINGING = "ringing"
    CONNECTED = "connected"
    ENDED = "ended"
    ERROR = "error"

@dataclass
class CallInfo:
    """Call information"""
    call_id: str
    room_name: str
    caller_name: str
    callee_name: str
    state: CallState
    start_time: Optional[float] = None
    end_time: Optional[float] = None

class CallManager:
    """Manages voice calls between Pi and web clients"""
    
    def __init__(self, 
                 server_url: str,
                 device_id: str,
                 livekit_client: LiveKitClient,
                 audio_manager: AudioManager,
                 led_controller: LEDController,
                 button_handler: ButtonHandler):
        
        self.server_url = server_url
        self.device_id = device_id
        
        # Hardware components
        self.livekit_client = livekit_client
        self.audio_manager = audio_manager
        self.led_controller = led_controller
        self.button_handler = button_handler
        
        # Call state
        self.current_call: Optional[CallInfo] = None
        self.call_state = CallState.IDLE
        
        # Socket.IO connection for real-time signaling
        self.sio = socketio.AsyncClient()
        self.connected_to_server = False
        
        # Callbacks
        self.on_call_state_changed = None
        self.on_call_started = None
        self.on_call_ended = None
        
    async def initialize(self):
        """Initialize call manager"""
        try:
            # Set up Socket.IO event handlers
            self.sio.on("connect", self._on_socket_connected)
            self.sio.on("disconnect", self._on_socket_disconnected)
            self.sio.on("incoming_call", self._on_incoming_call)
            self.sio.on("call_accepted", self._on_call_accepted)
            self.sio.on("call_rejected", self._on_call_rejected)
            self.sio.on("call_ended", self._on_call_ended)
            
            # Set up LiveKit callbacks
            self.livekit_client.on_connected = self._on_livekit_connected
            self.livekit_client.on_disconnected = self._on_livekit_disconnected
            self.livekit_client.on_participant_joined = self._on_participant_joined
            self.livekit_client.on_participant_left = self._on_participant_left
            
            # Set up button handlers
            self.button_handler.register_callback(ButtonAction.SHORT_PRESS, self._on_button_short_press)
            self.button_handler.register_callback(ButtonAction.LONG_PRESS, self._on_button_long_press)
            
            # Connect to server
            await self._connect_to_server()
            
            logger.info("✅ Call manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize call manager: {e}")
            raise
    
    async def _connect_to_server(self):
        """Connect to web server via Socket.IO"""
        try:
            socket_url = self.server_url.replace("http://", "ws://").replace("https://", "wss://")
            
            await self.sio.connect(
                socket_url,
                auth={"device_id": self.device_id, "device_type": "pi"}
            )
            
            logger.info("🔗 Connected to call signaling server")
            
        except Exception as e:
            logger.error(f"❌ Failed to connect to server: {e}")
            raise
    
    async def register_device(self, device_name: str, user_id: str):
        """Register Pi device with web server"""
        try:
            async with aiohttp.ClientSession() as session:
                register_url = f"{self.server_url}/api/pi/register"
                
                payload = {
                    "device_id": self.device_id,
                    "device_name": device_name,
                    "user_id": user_id,
                    "capabilities": ["audio_calling", "led_status", "button_control"]
                }
                
                async with session.post(register_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"✅ Device registered: {data}")
                        return True
                    else:
                        error_text = await response.text()
                        logger.error(f"❌ Registration failed: {response.status} - {error_text}")
                        return False
                        
        except Exception as e:
            logger.error(f"❌ Failed to register device: {e}")
            return False
    
    async def initiate_call(self, target_user: str) -> bool:
        """Initiate a call to a web user"""
        try:
            if self.call_state != CallState.IDLE:
                logger.warning("⚠️ Call already in progress")
                return False
            
            # Generate unique call ID and room name
            import time
            import hashlib
            call_id = hashlib.md5(f"{self.device_id}{target_user}{time.time()}".encode()).hexdigest()[:8]
            room_name = f"call_{call_id}"
            
            # Create call info
            self.current_call = CallInfo(
                call_id=call_id,
                room_name=room_name,
                caller_name=self.device_id,
                callee_name=target_user,
                state=CallState.OUTGOING,
                start_time=time.time()
            )
            
            # Update call state
            await self._set_call_state(CallState.OUTGOING)
            
            # Send call request to server
            await self.sio.emit("initiate_call", {
                "call_id": call_id,
                "room_name": room_name,
                "caller": self.device_id,
                "callee": target_user,
                "device_type": "pi"
            })
            
            logger.info(f"📞 Initiated call to {target_user}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to initiate call: {e}")
            await self._set_call_state(CallState.ERROR)
            return False
    
    async def answer_call(self) -> bool:
        """Answer an incoming call"""
        try:
            if self.call_state != CallState.INCOMING:
                logger.warning("⚠️ No incoming call to answer")
                return False
            
            if not self.current_call:
                logger.error("❌ No call information available")
                return False
            
            # Update call state
            await self._set_call_state(CallState.CONNECTED)
            
            # Join LiveKit room
            success = await self.livekit_client.join_room(self.current_call.room_name)
            if not success:
                await self._set_call_state(CallState.ERROR)
                return False
            
            # Notify server that call was accepted
            await self.sio.emit("call_accepted", {
                "call_id": self.current_call.call_id,
                "device_id": self.device_id
            })
            
            logger.info("📞 Call answered")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to answer call: {e}")
            await self._set_call_state(CallState.ERROR)
            return False
    
    async def reject_call(self) -> bool:
        """Reject an incoming call"""
        try:
            if self.call_state != CallState.INCOMING:
                logger.warning("⚠️ No incoming call to reject")
                return False
            
            if not self.current_call:
                logger.error("❌ No call information available")
                return False
            
            # Notify server that call was rejected
            await self.sio.emit("call_rejected", {
                "call_id": self.current_call.call_id,
                "device_id": self.device_id
            })
            
            # End call
            await self._end_call()
            
            logger.info("📞 Call rejected")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to reject call: {e}")
            return False
    
    async def hang_up(self) -> bool:
        """Hang up current call"""
        try:
            if self.call_state == CallState.IDLE:
                logger.warning("⚠️ No active call to hang up")
                return False
            
            if self.current_call:
                # Notify server that call ended
                await self.sio.emit("call_ended", {
                    "call_id": self.current_call.call_id,
                    "device_id": self.device_id,
                    "reason": "hangup"
                })
            
            # End call
            await self._end_call()
            
            logger.info("📞 Call hung up")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to hang up call: {e}")
            return False
    
    async def _set_call_state(self, new_state: CallState):
        """Set call state and update hardware"""
        old_state = self.call_state
        self.call_state = new_state
        
        if self.current_call:
            self.current_call.state = new_state
        
        # Update LED status based on call state
        if new_state == CallState.IDLE:
            await self.led_controller.set_status("ready")
        elif new_state == CallState.OUTGOING:
            await self.led_controller.set_status("connecting")
        elif new_state == CallState.INCOMING:
            await self.led_controller.set_status("incoming_call")
        elif new_state == CallState.CONNECTED:
            await self.led_controller.set_status("in_call")
        elif new_state == CallState.ERROR:
            await self.led_controller.set_status("error")
        
        logger.info(f"📱 Call state: {old_state.value} → {new_state.value}")
        
        # Trigger callback
        if self.on_call_state_changed:
            await self._safe_callback(self.on_call_state_changed, old_state, new_state)
    
    async def _end_call(self):
        """End current call and cleanup"""
        try:
            # Leave LiveKit room
            await self.livekit_client.leave_room()
            
            # Stop audio
            await self.audio_manager.stop_recording()
            await self.audio_manager.stop_playback()
            
            # Update call end time
            if self.current_call:
                import time
                self.current_call.end_time = time.time()
                
                # Trigger callback
                if self.on_call_ended:
                    await self._safe_callback(self.on_call_ended, self.current_call)
            
            # Reset state
            self.current_call = None
            await self._set_call_state(CallState.IDLE)
            
        except Exception as e:
            logger.error(f"❌ Failed to end call: {e}")
    
    # Socket.IO event handlers
    async def _on_socket_connected(self):
        """Handle Socket.IO connection"""
        self.connected_to_server = True
        logger.info("🔗 Connected to call signaling server")
    
    async def _on_socket_disconnected(self):
        """Handle Socket.IO disconnection"""
        self.connected_to_server = False
        logger.info("🔌 Disconnected from call signaling server")
    
    async def _on_incoming_call(self, data):
        """Handle incoming call notification"""
        try:
            logger.info(f"📞 Incoming call: {data}")
            
            # Create call info
            self.current_call = CallInfo(
                call_id=data["call_id"],
                room_name=data["room_name"],
                caller_name=data["caller"],
                callee_name=data["callee"],
                state=CallState.INCOMING
            )
            
            # Update call state
            await self._set_call_state(CallState.INCOMING)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle incoming call: {e}")
    
    async def _on_call_accepted(self, data):
        """Handle call acceptance"""
        try:
            logger.info(f"📞 Call accepted: {data}")
            
            if self.current_call and self.current_call.call_id == data["call_id"]:
                # Join LiveKit room
                success = await self.livekit_client.join_room(self.current_call.room_name)
                if success:
                    await self._set_call_state(CallState.CONNECTED)
                else:
                    await self._set_call_state(CallState.ERROR)
            
        except Exception as e:
            logger.error(f"❌ Failed to handle call acceptance: {e}")
    
    async def _on_call_rejected(self, data):
        """Handle call rejection"""
        try:
            logger.info(f"📞 Call rejected: {data}")
            
            if self.current_call and self.current_call.call_id == data["call_id"]:
                await self._end_call()
            
        except Exception as e:
            logger.error(f"❌ Failed to handle call rejection: {e}")
    
    async def _on_call_ended(self, data):
        """Handle call end notification"""
        try:
            logger.info(f"📞 Call ended: {data}")
            
            if self.current_call and self.current_call.call_id == data["call_id"]:
                await self._end_call()
            
        except Exception as e:
            logger.error(f"❌ Failed to handle call end: {e}")
    
    # LiveKit event handlers
    async def _on_livekit_connected(self):
        """Handle LiveKit connection"""
        logger.info("🔗 LiveKit connected")
        
        # Start audio publishing
        try:
            await self.livekit_client.publish_audio_track(self.audio_manager)
            await self.audio_manager.start_recording()
            
        except Exception as e:
            logger.error(f"❌ Failed to start audio: {e}")
    
    async def _on_livekit_disconnected(self):
        """Handle LiveKit disconnection"""
        logger.info("🔌 LiveKit disconnected")
        
        # Stop audio
        await self.audio_manager.stop_recording()
        await self.audio_manager.stop_playback()
    
    async def _on_participant_joined(self, participant):
        """Handle participant joining"""
        logger.info(f"👋 Participant joined: {participant.identity}")
        
        # Start audio playback when someone joins
        if self.call_state == CallState.CONNECTED:
            await self.audio_manager.start_playback()
    
    async def _on_participant_left(self, participant):
        """Handle participant leaving"""
        logger.info(f"👋 Participant left: {participant.identity}")
        
        # End call if last participant left
        participants = self.livekit_client.get_participants()
        if len(participants) == 0:
            await self._end_call()
    
    # Button event handlers
    async def _on_button_short_press(self, action):
        """Handle short button press"""
        if self.call_state == CallState.INCOMING:
            await self.answer_call()
        elif self.call_state == CallState.CONNECTED:
            await self.hang_up()
    
    async def _on_button_long_press(self, action):
        """Handle long button press"""
        if self.call_state == CallState.INCOMING:
            await self.reject_call()
        elif self.call_state in [CallState.OUTGOING, CallState.CONNECTED]:
            await self.hang_up()
    
    async def _safe_callback(self, callback, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"❌ Callback error: {e}")
    
    def get_call_state(self) -> CallState:
        """Get current call state"""
        return self.call_state
    
    def get_current_call(self) -> Optional[CallInfo]:
        """Get current call information"""
        return self.current_call
    
    def is_connected_to_server(self) -> bool:
        """Check if connected to signaling server"""
        return self.connected_to_server
    
    async def stop(self):
        """Stop call manager and cleanup"""
        try:
            # End any active call
            if self.call_state != CallState.IDLE:
                await self.hang_up()
            
            # Disconnect from server
            if self.connected_to_server:
                await self.sio.disconnect()
            
            # Stop LiveKit client
            await self.livekit_client.stop()
            
            logger.info("🛑 Call manager stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop call manager: {e}")