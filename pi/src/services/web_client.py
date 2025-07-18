"""
Web Client API Integration for EmmaPhone2 Pi

Handles communication with the web client API for user-based calling
"""
import asyncio
import aiohttp
import logging
import json
from typing import Dict, Optional, Any
import socketio

logger = logging.getLogger(__name__)

class WebClientAPI:
    """Web client API integration for Pi device"""
    
    def __init__(self, base_url: str, api_endpoint: str = "/api"):
        self.base_url = base_url.rstrip('/')
        self.api_endpoint = api_endpoint
        self.session = None
        self.authenticated = False
        self.user_id = None
        self.username = None
        
    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        logger.info(f"✅ WebClient API initialized: {self.base_url}")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
            self.session = None
            logger.info("🔌 WebClient API session closed")
    
    
    async def initiate_call(self, target_user_id: str) -> Optional[Dict]:
        """Initiate a call to another user via web client API"""
        try:
            if not self.authenticated:
                logger.error("❌ Not authenticated with web client")
                return None
            
            call_data = {
                "to_user": target_user_id
            }
            
            url = f"{self.base_url}{self.api_endpoint}/initiate-call"
            
            async with self.session.post(url, json=call_data) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Call initiated to user {target_user_id}")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to initiate call: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to initiate call: {e}")
            return None
    
    async def get_user_contacts(self) -> Optional[list]:
        """Get user's contacts from web client"""
        try:
            if not self.authenticated:
                logger.error("❌ Not authenticated with web client")
                return None
            
            url = f"{self.base_url}{self.api_endpoint}/contacts"
            
            async with self.session.get(url) as response:
                if response.status == 200:
                    result = await response.json()
                    logger.info(f"✅ Retrieved {len(result)} contacts")
                    return result
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Failed to get contacts: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to get contacts: {e}")
            return None

class WebClientSocket:
    """Socket.IO client for real-time communication with web client"""
    
    def __init__(self, base_url: str, socket_endpoint: str = "/socket.io"):
        self.base_url = base_url.rstrip('/')
        self.socket_endpoint = socket_endpoint
        self.sio = None
        self.connected = False
        self.user_id = None
        self.on_incoming_call = None
        self.on_call_ended = None
        
    async def initialize(self, user_id: str):
        """Initialize Socket.IO connection"""
        try:
            self.user_id = user_id
            self.sio = socketio.AsyncClient()
            
            # Register event handlers
            self.sio.on('connect', self._on_connect)
            self.sio.on('disconnect', self._on_disconnect)
            self.sio.on('incoming-call', self._on_incoming_call)
            self.sio.on('call-ended', self._on_call_ended)
            
            # Connect to server
            await self.sio.connect(f"{self.base_url}{self.socket_endpoint}")
            
            logger.info(f"✅ Socket.IO connected: {self.base_url}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Socket.IO: {e}")
            raise
    
    async def register_user(self):
        """Register user with Socket.IO server"""
        try:
            if not self.connected:
                logger.error("❌ Socket.IO not connected")
                return
            
            user_data = {
                "userId": self.user_id,
                "deviceType": "pi"
            }
            
            await self.sio.emit('register-user', user_data)
            logger.info(f"✅ User registered with Socket.IO: {self.user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to register user: {e}")
    
    async def disconnect(self):
        """Disconnect from Socket.IO server"""
        try:
            if self.sio and self.connected:
                await self.sio.disconnect()
                logger.info("🔌 Socket.IO disconnected")
                
        except Exception as e:
            logger.error(f"❌ Failed to disconnect Socket.IO: {e}")
    
    def _on_connect(self):
        """Handle Socket.IO connection"""
        self.connected = True
        logger.info("🔗 Socket.IO connected")
        
        # Register user after connection
        asyncio.create_task(self.register_user())
    
    def _on_disconnect(self):
        """Handle Socket.IO disconnection"""
        self.connected = False
        logger.info("🔌 Socket.IO disconnected")
    
    def _on_incoming_call(self, data):
        """Handle incoming call notification"""
        logger.info(f"📞 Incoming call from: {data.get('from_user')}")
        
        if self.on_incoming_call:
            asyncio.create_task(self._safe_callback(self.on_incoming_call, data))
    
    def _on_call_ended(self, data):
        """Handle call ended notification"""
        logger.info(f"📴 Call ended: {data.get('reason', 'unknown')}")
        
        if self.on_call_ended:
            asyncio.create_task(self._safe_callback(self.on_call_ended, data))
    
    async def _safe_callback(self, callback, *args):
        """Safely execute callback function"""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(*args)
            else:
                callback(*args)
        except Exception as e:
            logger.error(f"❌ Socket callback error: {e}")
    
    async def accept_call(self, call_data: Dict):
        """Accept an incoming call"""
        try:
            if not self.connected:
                logger.error("❌ Socket.IO not connected")
                return
            
            await self.sio.emit('accept-call', call_data)
            logger.info("✅ Call accepted")
            
        except Exception as e:
            logger.error(f"❌ Failed to accept call: {e}")
    
    async def reject_call(self, call_data: Dict):
        """Reject an incoming call"""
        try:
            if not self.connected:
                logger.error("❌ Socket.IO not connected")
                return
            
            await self.sio.emit('reject-call', call_data)
            logger.info("✅ Call rejected")
            
        except Exception as e:
            logger.error(f"❌ Failed to reject call: {e}")