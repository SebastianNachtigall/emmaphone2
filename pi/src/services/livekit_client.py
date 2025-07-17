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
        """Get access token from web server"""
        try:
            # Get token from web server API
            async with aiohttp.ClientSession() as session:
                token_url = f"{self.server_url}/api/livekit-token"
                
                payload = {
                    "roomName": room_name,
                    "participantName": self.participant_identity
                }
                
                async with session.post(token_url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data["token"]
                    else:
                        error_text = await response.text()
                        raise Exception(f"Token request failed: {response.status} - {error_text}")
                        
        except Exception as e:
            logger.error(f"❌ Failed to get access token: {e}")
            raise
    
    async def join_room(self, room_name: str, token: Optional[str] = None) -> bool:
        """Join a LiveKit room"""
        try:
            if not token:
                token = await self.get_access_token(room_name)
            
            # Connect to the room
            await self.room.connect(
                url=self.server_url.replace("http://", "ws://").replace("https://", "wss://"),
                token=token
            )
            
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
    
    async def publish_audio_track(self, audio_source):
        """Publish audio track to the room"""
        try:
            if not self.room or not self.connected:
                raise Exception("Not connected to room")
            
            # Create audio track from source
            self.audio_source = audio_source
            self.local_audio_track = rtc.LocalAudioTrack.create_audio_track(
                "microphone",
                audio_source
            )
            
            # Publish the track
            options = rtc.TrackPublishOptions()
            options.source = rtc.TrackSource.SOURCE_MICROPHONE
            
            publication = await self.room.local_participant.publish_track(
                self.local_audio_track,
                options
            )
            
            logger.info("🎤 Audio track published")
            return publication
            
        except Exception as e:
            logger.error(f"❌ Failed to publish audio track: {e}")
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
            
            if self.on_audio_received:
                asyncio.create_task(self._safe_callback(self.on_audio_received, track, participant))
    
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