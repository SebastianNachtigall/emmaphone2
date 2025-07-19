"""
Enhanced Call Manager for EmmaPhone2 Pi - Web Client Integration

Manages call state using web client API for user-based calling instead of direct room management
"""
import asyncio
import logging
import time
from enum import Enum
from typing import Optional, Dict, Any, Callable
from dataclasses import dataclass

from .livekit_client import LiveKitClient
from .web_client import WebClientAPI, WebClientSocket
from .user_manager import UserManager
from hardware.audio import AudioManager
from hardware.leds import LEDController
from hardware.button import ButtonHandler, ButtonAction

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
    livekit_token: Optional[str] = None

class CallManagerV2:
    """Enhanced call manager with web client API integration"""
    
    def __init__(self, 
                 livekit_client: LiveKitClient,
                 audio_manager: AudioManager,
                 led_controller: LEDController,
                 button_handler: ButtonHandler,
                 user_manager: UserManager,
                 device_id: str):
        
        self.device_id = device_id
        
        # Hardware components
        self.livekit_client = livekit_client
        self.audio_manager = audio_manager
        self.led_controller = led_controller
        self.button_handler = button_handler
        
        # User management
        self.user_manager = user_manager
        self.web_api = None
        self.web_socket = None
        
        # Call state
        self.current_call: Optional[CallInfo] = None
        self.call_state = CallState.IDLE
        self.pi_user_info: Optional[Dict] = None
        
        # Call recording
        self.call_recording_enabled = False
        self.call_recording_filename = None
        
        # Callbacks
        self.on_call_state_changed = None
        self.on_call_started = None
        self.on_call_ended = None
        
    async def initialize(self):
        """Initialize call manager with web client integration"""
        try:
            # Check if user is configured
            if not self.user_manager.is_user_configured():
                raise Exception("User not configured. Please run setup_user.py first.")
            
            # Authenticate user
            pi_user = await self.user_manager.authenticate_user()
            if not pi_user:
                raise Exception("Failed to authenticate user with web client")
            
            self.pi_user_info = pi_user
            logger.info(f"✅ User authenticated: {pi_user['username']} (ID: {pi_user['user_id']})")
            
            # Get web API from user manager
            self.web_api = self.user_manager.web_api
            
            # Initialize Socket.IO connection
            web_config = self.user_manager.settings.get_web_client_config()
            self.web_socket = WebClientSocket(
                web_config.get("url", ""),
                web_config.get("socket_endpoint", "/socket.io")
            )
            
            await self.web_socket.initialize(pi_user["user_id"])
            
            # Set up Socket.IO callbacks
            self.web_socket.on_incoming_call = self._on_incoming_call
            self.web_socket.on_call_ended = self._on_call_ended
            
            # Set up LiveKit callbacks
            self.livekit_client.on_connected = self._on_livekit_connected
            self.livekit_client.on_disconnected = self._on_livekit_disconnected
            self.livekit_client.on_participant_joined = self._on_participant_joined
            self.livekit_client.on_participant_left = self._on_participant_left
            
            # Set up button handlers
            self.button_handler.register_callback(ButtonAction.SHORT_PRESS, self._on_button_short_press)
            self.button_handler.register_callback(ButtonAction.LONG_PRESS, self._on_button_long_press)
            
            logger.info("✅ Call manager initialized with web client integration")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize call manager: {e}")
            raise
    
    async def initiate_call(self, target_user_id: str) -> bool:
        """Initiate a call to a web user using web client API"""
        try:
            if self.call_state != CallState.IDLE:
                logger.warning("⚠️ Call already in progress")
                return False
            
            if not self.pi_user_info:
                logger.error("❌ Pi user not registered")
                return False
            
            # Update call state
            await self._set_call_state(CallState.OUTGOING)
            
            # Use web client API to initiate call
            call_result = await self.web_api.initiate_call(target_user_id)
            
            if not call_result:
                logger.error("❌ Failed to initiate call via web client API")
                await self._set_call_state(CallState.ERROR)
                return False
            
            logger.info(f"📞 Call result from web API: {call_result}")
            
            # Extract call information (mapping server field names)
            room_name = call_result.get("roomName", "") or call_result.get("room_name", "")
            livekit_token = call_result.get("callerToken", "") or call_result.get("token", "")
            
            if not room_name or not livekit_token:
                logger.error("❌ Invalid call response from web client")
                await self._set_call_state(CallState.ERROR)
                return False
            
            # Create call info
            self.current_call = CallInfo(
                call_id=call_result.get("callLogId", "") or call_result.get("call_id", ""),
                room_name=room_name,
                caller_name=self.pi_user_info["username"],
                callee_name=target_user_id,
                state=CallState.OUTGOING,
                start_time=time.time(),
                livekit_token=livekit_token
            )
            
            # Join LiveKit room directly (web client handles signaling)
            success = await self.livekit_client.join_room(room_name, livekit_token)
            if success:
                await self._set_call_state(CallState.CONNECTED)
                
                # Small delay to ensure room connection is fully established
                await asyncio.sleep(0.5)
                
                # Start audio publishing after room join
                logger.info("🎤 Starting audio publishing after room join")
                try:
                    await self.livekit_client.publish_audio_track(self.audio_manager)
                    logger.info("🎤 Audio track published successfully")
                    
                    # Start audio recording for LiveKit
                    await self.audio_manager.start_recording()
                    logger.info("🎤 Audio recording started for LiveKit")
                    
                except Exception as e:
                    logger.error(f"❌ Failed to start audio publishing: {e}")
                
                # Start call recording immediately after successful room join
                if self.call_recording_enabled and self.current_call:
                    logger.info("📹 Attempting to start call recording after room join")
                    try:
                        await self.start_call_recording()
                    except Exception as e:
                        logger.error(f"❌ Failed to start call recording: {e}")
                
                logger.info(f"📞 Call initiated to user {target_user_id}")
                return True
            else:
                await self._set_call_state(CallState.ERROR)
                return False
            
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
            
            # Accept call via Socket.IO
            call_data = {
                "call_id": self.current_call.call_id,
                "room_name": self.current_call.room_name,
                "token": self.current_call.livekit_token
            }
            
            await self.web_socket.accept_call(call_data)
            
            # Join LiveKit room
            success = await self.livekit_client.join_room(
                self.current_call.room_name, 
                self.current_call.livekit_token
            )
            
            if success:
                await self._set_call_state(CallState.CONNECTED)
                logger.info("📞 Call answered")
                return True
            else:
                await self._set_call_state(CallState.ERROR)
                return False
            
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
            
            # Reject call via Socket.IO
            call_data = {
                "call_id": self.current_call.call_id,
                "room_name": self.current_call.room_name
            }
            
            await self.web_socket.reject_call(call_data)
            
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
            
            logger.info("📞 Hanging up call...")
            
            # End call (web client will handle signaling)
            await self._end_call()
            
            logger.info("📞 Call hung up successfully")
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
            # Check if already ending
            if self.call_state == CallState.IDLE:
                logger.info("📞 Call already ended")
                return
            
            logger.info("📞 Ending call - starting cleanup...")
            
            # Stop call recording first if active
            if self.call_recording_enabled:
                try:
                    recording_file = await self.stop_call_recording()
                    if recording_file:
                        logger.info(f"📹 Call recording saved: {recording_file}")
                except Exception as e:
                    logger.error(f"❌ Failed to stop call recording: {e}")
            
            # Leave LiveKit room
            try:
                await self.livekit_client.leave_room()
                logger.info("📞 Left LiveKit room")
            except Exception as e:
                logger.error(f"❌ Failed to leave LiveKit room: {e}")
            
            # Stop audio
            try:
                await self.audio_manager.stop_recording()
                await self.audio_manager.stop_playback()
                logger.info("📞 Audio stopped")
            except Exception as e:
                logger.error(f"❌ Failed to stop audio: {e}")
            
            # Update call end time
            if self.current_call:
                self.current_call.end_time = time.time()
                
                # Trigger callback
                if self.on_call_ended:
                    try:
                        await self._safe_callback(self.on_call_ended, self.current_call)
                    except Exception as e:
                        logger.error(f"❌ Failed to trigger call ended callback: {e}")
            
            # Reset state
            self.current_call = None
            await self._set_call_state(CallState.IDLE)
            
            logger.info("📞 Call cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Failed to end call: {e}")
            # Force state reset even if cleanup failed
            self.current_call = None
            try:
                await self._set_call_state(CallState.IDLE)
            except:
                self.call_state = CallState.IDLE
    
    # Socket.IO event handlers
    async def _on_incoming_call(self, data):
        """Handle incoming call notification from web client"""
        try:
            logger.info(f"📞 Incoming call from web client: {data}")
            
            # Extract call information (mapping server field names to our expected names)
            from_user = data.get("from", "") or data.get("from_user", "")
            from_name = data.get("fromName", "") or data.get("from_name", "")
            room_name = data.get("roomName", "") or data.get("room_name", "")
            token = data.get("calleeToken", "") or data.get("token", "")
            call_id = data.get("callLogId", "") or data.get("call_id", "")
            
            if not all([from_user, room_name, token, call_id]):
                logger.error(f"❌ Invalid incoming call data - missing fields: from_user={from_user}, room_name={room_name}, token={bool(token)}, call_id={call_id}")
                return
            
            # Create call info
            self.current_call = CallInfo(
                call_id=call_id,
                room_name=room_name,
                caller_name=from_name or from_user,  # Use display name if available, fallback to user ID
                callee_name=self.pi_user_info["username"] if self.pi_user_info else "",
                state=CallState.INCOMING,
                livekit_token=token
            )
            
            # Update call state
            await self._set_call_state(CallState.INCOMING)
            
            logger.info(f"📞 Incoming call from {from_name or from_user} (ID: {from_user}) ready to answer")
            
        except Exception as e:
            logger.error(f"❌ Failed to handle incoming call: {e}")
    
    async def _on_call_ended(self, data):
        """Handle call end notification from web client"""
        try:
            logger.info(f"📞 Call ended by web client: {data}")
            
            if self.current_call:
                await self._end_call()
            
        except Exception as e:
            logger.error(f"❌ Failed to handle call end: {e}")
    
    # LiveKit event handlers
    def _on_livekit_connected(self):
        """Handle LiveKit connection"""
        logger.info("🔗 LiveKit connected")
        
        # Start audio publishing
        async def start_audio():
            try:
                logger.info("🔗 LiveKit connected - starting audio publishing")
                await self.livekit_client.publish_audio_track(self.audio_manager)
                logger.info("🎤 Audio track published to LiveKit")
                
                await self.audio_manager.start_recording()
                logger.info("🎤 Audio recording started for LiveKit")
                
                # Start call recording if enabled
                if self.call_recording_enabled and self.current_call:
                    await self.start_call_recording()
                
            except Exception as e:
                logger.error(f"❌ Failed to start audio: {e}")
        
        asyncio.create_task(start_audio())
    
    def _on_livekit_disconnected(self):
        """Handle LiveKit disconnection"""
        logger.info("🔌 LiveKit disconnected")
        
        # Stop audio and call recording
        async def stop_audio():
            await self.audio_manager.stop_recording()
            await self.audio_manager.stop_playback()
            
            # Stop call recording if active
            if self.call_recording_enabled:
                recording_file = await self.stop_call_recording()
                if recording_file:
                    logger.info(f"📹 Call recording saved: {recording_file}")
        
        asyncio.create_task(stop_audio())
    
    def _on_participant_joined(self, participant):
        """Handle participant joining"""
        logger.info(f"👋 Participant joined: {participant.identity}")
        
        # Start audio playback when someone joins
        async def start_playback():
            if self.call_state == CallState.CONNECTED:
                await self.audio_manager.start_playback()
        
        asyncio.create_task(start_playback())
    
    def _on_participant_left(self, participant):
        """Handle participant leaving"""
        logger.info(f"👋 Participant left: {participant.identity}")
        
        # End call if last participant left
        async def check_end_call():
            participants = self.livekit_client.get_participants()
            if len(participants) == 0:
                await self._end_call()
        
        asyncio.create_task(check_end_call())
    
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
    
    # Public interface
    def get_call_state(self) -> CallState:
        """Get current call state"""
        return self.call_state
    
    def get_current_call(self) -> Optional[CallInfo]:
        """Get current call information"""
        return self.current_call
    
    def get_pi_user_info(self) -> Optional[Dict]:
        """Get Pi user information"""
        return self.pi_user_info
    
    def is_connected_to_web_client(self) -> bool:
        """Check if connected to web client"""
        return self.web_socket.connected
    
    async def get_contacts(self) -> Optional[list]:
        """Get contacts from web client"""
        return await self.web_api.get_user_contacts()
    
    def enable_call_recording(self) -> bool:
        """Enable call recording for debugging"""
        try:
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            self.call_recording_filename = f"/tmp/call_recording_{timestamp}.wav"
            self.call_recording_enabled = True
            logger.info(f"📹 Call recording enabled: {self.call_recording_filename}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to enable call recording: {e}")
            return False
    
    def disable_call_recording(self):
        """Disable call recording"""
        self.call_recording_enabled = False
        self.call_recording_filename = None
        logger.info("📹 Call recording disabled")
    
    def get_call_recording_file(self) -> Optional[str]:
        """Get the current call recording filename"""
        return self.call_recording_filename if self.call_recording_enabled else None
    
    async def start_call_recording(self) -> bool:
        """Start recording the current call for debugging"""
        try:
            if not self.call_recording_enabled:
                logger.warning("⚠️ Call recording not enabled")
                return False
            
            if not self.current_call or self.call_state != CallState.CONNECTED:
                logger.warning("⚠️ No active call to record")
                return False
            
            # Start recording through audio manager
            if hasattr(self.audio_manager, 'start_recording_to_file'):
                success = await self.audio_manager.start_recording_to_file(self.call_recording_filename)
                if success:
                    logger.info(f"📹 Call recording started: {self.call_recording_filename}")
                    return True
                else:
                    logger.error("❌ Failed to start call recording")
                    return False
            else:
                logger.warning("⚠️ Audio manager doesn't support file recording")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to start call recording: {e}")
            return False
    
    async def stop_call_recording(self) -> Optional[str]:
        """Stop call recording and return filename"""
        try:
            if not self.call_recording_enabled or not self.call_recording_filename:
                return None
            
            # Stop recording through audio manager
            if hasattr(self.audio_manager, 'stop_recording_to_file'):
                await self.audio_manager.stop_recording_to_file()
            
            recording_file = self.call_recording_filename
            self.disable_call_recording()
            
            logger.info(f"📹 Call recording stopped: {recording_file}")
            return recording_file
            
        except Exception as e:
            logger.error(f"❌ Failed to stop call recording: {e}")
            return None
    
    async def stop(self):
        """Stop call manager and cleanup"""
        try:
            # End any active call
            if self.call_state != CallState.IDLE:
                await self.hang_up()
            
            # Disconnect from web client
            if self.web_socket:
                await self.web_socket.disconnect()
            
            # Close user manager
            await self.user_manager.close()
            
            # Stop LiveKit client
            await self.livekit_client.stop()
            
            logger.info("🛑 Call manager stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop call manager: {e}")