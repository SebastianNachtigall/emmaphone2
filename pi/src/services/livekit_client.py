"""
LiveKit WebRTC Client for EmmaPhone2 Pi

Handles WebRTC room connections and audio streaming using LiveKit Python SDK
"""
import asyncio
import logging
import json
import aiohttp
from typing import Optional, Callable, Dict, Any
from livekit import rtc

logger = logging.getLogger(__name__)

class LiveKitClient:
    """LiveKit WebRTC client for Pi audio calling"""
    
    def __init__(self, server_url: str, api_key: str, api_secret: str):
        self.server_url = server_url
        self.api_key = api_key
        self.api_secret = api_secret
        
        # Connection state
        self.room = None
        self.connected = False
        self.participant_identity = None
        
        # Audio components
        self.audio_source = None
        self.local_audio_track = None
        self.remote_audio_track = None
        
        # Event loop for threading
        self.main_loop = None
        
        # Callbacks
        self.on_connected = None
        self.on_disconnected = None
        self.on_participant_joined = None
        self.on_participant_left = None
        self.on_audio_received = None
        
    async def initialize(self, participant_identity: str):
        """Initialize the LiveKit client"""
        try:
            self.participant_identity = participant_identity
            
            # Store main event loop for threading
            try:
                self.main_loop = asyncio.get_running_loop()
            except RuntimeError:
                self.main_loop = None
            
            # Create room instance
            self.room = rtc.Room()
            
            # Set up event handlers
            self.room.on("connected", self._on_connected)
            self.room.on("disconnected", self._on_disconnected)
            self.room.on("participant_connected", self._on_participant_connected)
            self.room.on("participant_disconnected", self._on_participant_disconnected)
            self.room.on("track_subscribed", self._on_track_subscribed)
            self.room.on("track_unsubscribed", self._on_track_unsubscribed)
            
            logger.info(f"✅ LiveKit client initialized for {participant_identity}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize LiveKit client: {e}")
            raise
    
    async def get_access_token(self, room_name: str) -> str:
        """Generate access token locally using LiveKit credentials"""
        try:
            from livekit import api
            
            # Create access token locally
            token = api.AccessToken(self.api_key, self.api_secret)
            token.with_identity(self.participant_identity)
            token.with_name(self.participant_identity)
            token.with_grants(api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
                can_publish_data=True
            ))
            
            jwt_token = token.to_jwt()
            logger.info(f"✅ Generated local access token for room: {room_name}")
            return jwt_token
                        
        except Exception as e:
            logger.error(f"❌ Failed to generate access token: {e}")
            raise
    
    async def join_room(self, room_name: str, token: Optional[str] = None) -> bool:
        """Join a LiveKit room"""
        try:
            if not token:
                token = await self.get_access_token(room_name)
            
            # Connect to the room
            await self.room.connect(
                url=self.server_url,  # URL should already be wss:// format
                token=token
            )
            
            # Set connected flag manually since callback might not fire
            self.connected = True
            
            logger.info(f"✅ Joined room: {room_name}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to join room {room_name}: {e}")
            return False
    
    async def leave_room(self):
        """Leave the current room"""
        try:
            if self.room and self.connected:
                await self.room.disconnect()
                logger.info("📤 Left room")
                
        except Exception as e:
            logger.error(f"❌ Failed to leave room: {e}")
    
    async def publish_audio_track(self, audio_manager):
        """Publish audio track to the room"""
        try:
            if not self.room or not self.connected:
                raise Exception("Not connected to room")
            
            logger.info("🎤 Creating LiveKit audio source...")
            
            # Create audio source compatible with LiveKit
            from livekit import rtc
            
            # Create audio source with Pi's audio configuration
            self.audio_source = rtc.AudioSource(
                sample_rate=audio_manager.SAMPLE_RATE,
                num_channels=audio_manager.CHANNELS
            )
            
            # Create audio track from source
            self.local_audio_track = rtc.LocalAudioTrack.create_audio_track(
                "microphone",
                self.audio_source
            )
            
            logger.info("🎤 Created LiveKit audio track")
            
            # Publish the track
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE
            
            publication = await self.room.local_participant.publish_track(
                self.local_audio_track,
                options
            )
            
            logger.info("🎤 Audio track published to LiveKit room")
            
            # Start feeding audio data to LiveKit
            await self._start_audio_capture(audio_manager)
            
            return publication
            
        except Exception as e:
            logger.error(f"❌ Failed to publish audio track: {e}")
            raise
    
    async def _start_audio_capture(self, audio_manager):
        """Start capturing audio from Pi and feeding to LiveKit"""
        try:
            logger.info("🎤 Starting audio capture for LiveKit...")
            
            # Add frame counter for debugging
            self.frame_count = 0
            
            def audio_callback(audio_data):
                """Callback to send audio data to LiveKit"""
                try:
                    self.frame_count += 1
                    
                    if self.audio_source and len(audio_data) > 0:
                        # Log first few frames for debugging
                        if self.frame_count <= 5:
                            logger.info(f"🎤 Audio frame {self.frame_count}: {len(audio_data)} samples, type: {type(audio_data)}")
                        elif self.frame_count == 50:
                            logger.info(f"🎤 Audio streaming: {self.frame_count} frames sent so far")
                        
                        # Convert numpy array to the format LiveKit expects
                        import numpy as np
                        if isinstance(audio_data, np.ndarray):
                            # Apply gain reduction to prevent clipping (reduce volume by 75%)
                            audio_float = audio_data.astype(np.float32) * 0.25
                            # Convert to int16 PCM data
                            audio_pcm = audio_float.astype(np.int16)
                            
                            # Check for silence (all zeros)
                            if self.frame_count <= 5:
                                max_amplitude = np.max(np.abs(audio_pcm))
                                logger.info(f"🎤 Frame {self.frame_count} max amplitude: {max_amplitude} (after gain reduction)")
                            
                            # Create AudioFrame and send to LiveKit
                            frame = rtc.AudioFrame(
                                data=audio_pcm.tobytes(),
                                sample_rate=audio_manager.SAMPLE_RATE,
                                num_channels=audio_manager.CHANNELS,
                                samples_per_channel=len(audio_pcm) // audio_manager.CHANNELS
                            )
                            
                            # Send frame to LiveKit using main event loop
                            if self.main_loop and not self.main_loop.is_closed():
                                try:
                                    # Schedule in the main event loop
                                    future = asyncio.run_coroutine_threadsafe(
                                        self.audio_source.capture_frame(frame), self.main_loop
                                    )
                                    # Log success for first few frames
                                    if self.frame_count <= 3:
                                        logger.info(f"🎤 Frame {self.frame_count} sent to LiveKit successfully")
                                except Exception as e:
                                    if self.frame_count <= 5:
                                        logger.error(f"❌ Failed to send frame {self.frame_count}: {e}")
                            
                except Exception as e:
                    # Don't spam logs for threading issues
                    if "event loop" not in str(e) and self.frame_count <= 5:
                        logger.error(f"❌ Audio callback error frame {self.frame_count}: {e}")
            
            # Start recording with our callback
            await audio_manager.start_recording(audio_callback)
            logger.info("🎤 Audio capture started for LiveKit")
            
        except Exception as e:
            logger.error(f"❌ Failed to start audio capture: {e}")
            raise
    
    async def unpublish_audio_track(self):
        """Unpublish audio track"""
        try:
            if self.local_audio_track and self.room:
                await self.room.local_participant.unpublish_track(
                    self.local_audio_track.sid
                )
                self.local_audio_track = None
                logger.info("🔇 Audio track unpublished")
                
        except Exception as e:
            logger.error(f"❌ Failed to unpublish audio track: {e}")
    
    async def set_audio_enabled(self, enabled: bool):
        """Enable or disable audio publishing"""
        try:
            if self.local_audio_track:
                self.local_audio_track.enable(enabled)
                logger.info(f"🎤 Audio {'enabled' if enabled else 'disabled'}")
                
        except Exception as e:
            logger.error(f"❌ Failed to set audio enabled: {e}")
    
    def get_participants(self) -> Dict[str, Any]:
        """Get list of room participants"""
        if not self.room:
            return {}
        
        participants = {}
        for participant in self.room.remote_participants.values():
            participants[participant.identity] = {
                "identity": participant.identity,
                "name": participant.name,
                "metadata": participant.metadata,
                "tracks": list(participant.track_publications.keys())
            }
        
        return participants
    
    def is_connected(self) -> bool:
        """Check if connected to room"""
        return self.connected
    
    def get_room_name(self) -> Optional[str]:
        """Get current room name"""
        return self.room.name if self.room else None
    
    # Event handlers
    def _on_connected(self):
        """Handle room connection"""
        self.connected = True
        logger.info("🔗 Connected to LiveKit room")
        
        if self.on_connected:
            asyncio.create_task(self._safe_callback(self.on_connected))
    
    def _on_disconnected(self):
        """Handle room disconnection"""
        self.connected = False
        logger.info("🔌 Disconnected from LiveKit room")
        
        if self.on_disconnected:
            asyncio.create_task(self._safe_callback(self.on_disconnected))
    
    def _on_participant_connected(self, participant):
        """Handle participant joining"""
        logger.info(f"👋 Participant joined: {participant.identity}")
        
        if self.on_participant_joined:
            asyncio.create_task(self._safe_callback(self.on_participant_joined, participant))
    
    def _on_participant_disconnected(self, participant):
        """Handle participant leaving"""
        logger.info(f"👋 Participant left: {participant.identity}")
        
        if self.on_participant_left:
            asyncio.create_task(self._safe_callback(self.on_participant_left, participant))
    
    def _on_track_subscribed(self, track, publication, participant):
        """Handle track subscription"""
        logger.info(f"📡 Track subscribed: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            self.remote_audio_track = track
            logger.info(f"🔊 Audio track from {participant.identity} - starting playback...")
            
            # Start processing incoming audio
            asyncio.create_task(self._process_incoming_audio(track, participant))
            
            if self.on_audio_received:
                asyncio.create_task(self._safe_callback(self.on_audio_received, track, participant))
    
    async def _process_incoming_audio(self, track, participant):
        """Process incoming audio track and send to speakers"""
        try:
            logger.info(f"🔊 Starting audio processing from {participant.identity}")
            
            # Create audio stream to read frames from the track
            audio_stream = rtc.AudioStream(track)
            frame_count = 0
            
            async for audio_frame in audio_stream:
                frame_count += 1
                
                # Log first few frames for debugging
                if frame_count <= 3:
                    logger.info(f"🔊 Received audio frame {frame_count}: {audio_frame.samples_per_channel} samples")
                elif frame_count == 50:
                    logger.info(f"🔊 Audio playback: {frame_count} frames received so far")
                
                # TODO: Send audio_frame to Pi speakers through audio_manager
                # For now, just log that we're receiving audio
                
        except Exception as e:
            logger.error(f"❌ Failed to process incoming audio from {participant.identity}: {e}")
    
    def _on_track_unsubscribed(self, track, publication, participant):
        """Handle track unsubscription"""
        logger.info(f"📡 Track unsubscribed: {track.kind} from {participant.identity}")
        
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            self.remote_audio_track = None
    
    async def _safe_callback(self, callback, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"❌ Callback error: {e}")
    
    async def stop(self):
        """Stop LiveKit client and cleanup"""
        try:
            await self.unpublish_audio_track()
            await self.leave_room()
            
            self.room = None
            self.connected = False
            self.audio_source = None
            
            logger.info("🛑 LiveKit client stopped")
            
        except Exception as e:
            logger.error(f"❌ Failed to stop LiveKit client: {e}")