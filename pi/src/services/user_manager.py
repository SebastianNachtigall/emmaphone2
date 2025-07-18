"""
User Management Service for EmmaPhone2 Pi

Handles user registration, authentication, and management with web client
"""
import asyncio
import logging
import secrets
from typing import Optional, Dict, Any

from .web_client import WebClientAPI
from config.settings import Settings

logger = logging.getLogger(__name__)

class UserManager:
    """Manages Pi user registration and authentication"""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.web_api = None
        self.authenticated_user = None
    
    async def initialize(self):
        """Initialize user manager"""
        try:
            web_config = self.settings.get_web_client_config()
            self.web_api = WebClientAPI(
                web_config.get("url", ""),
                web_config.get("api_endpoint", "/api")
            )
            await self.web_api.initialize()
            logger.info("✅ User manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize user manager: {e}")
            raise
    
    async def close(self):
        """Close user manager"""
        if self.web_api:
            await self.web_api.close()
    
    def is_user_configured(self) -> bool:
        """Check if user is configured"""
        return self.settings.is_user_configured()
    
    async def register_new_user(self, username: str, display_name: str, password: str = None) -> Optional[Dict]:
        """Register a new user with the web client"""
        try:
            if self.is_user_configured():
                logger.warning("⚠️ User already configured")
                return None
            
            # Generate secure password if not provided
            if not password:
                password = secrets.token_urlsafe(32)
            
            # Register with web client
            register_data = {
                "username": username,
                "displayName": display_name,
                "password": password,
                "avatarColor": "#FF6B35"  # Orange for Pi users
            }
            
            url = f"{self.web_api.base_url}{self.web_api.api_endpoint}/auth/register"
            
            async with self.web_api.session.post(url, json=register_data) as response:
                if response.status == 200:
                    result = await response.json()
                    user_data = result.get("user", {})
                    user_id = user_data.get("id")
                    
                    if user_id:
                        # Save user configuration
                        self.settings.configure_user(username, display_name, password, str(user_id))
                        
                        user_info = {
                            "user_id": user_id,
                            "username": username,
                            "display_name": display_name,
                            "password": password
                        }
                        
                        logger.info(f"✅ New user registered: {username} (ID: {user_id})")
                        return user_info
                    else:
                        logger.error("❌ Registration succeeded but no user ID received")
                        return None
                        
                elif response.status == 409:
                    logger.error(f"❌ Username '{username}' already exists")
                    return None
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Registration failed: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to register user: {e}")
            return None
    
    async def authenticate_user(self, username: str = None, password: str = None) -> Optional[Dict]:
        """Authenticate user with web client"""
        try:
            # Use stored credentials if not provided
            if not username or not password:
                creds = self.settings.get_user_credentials()
                username = creds.get("username", "")
                password = creds.get("password", "")
            
            if not username or not password:
                logger.error("❌ No credentials available")
                return None
            
            # Login with web client
            login_data = {
                "username": username,
                "password": password
            }
            
            url = f"{self.web_api.base_url}{self.web_api.api_endpoint}/auth/login"
            
            async with self.web_api.session.post(url, json=login_data) as response:
                if response.status == 200:
                    result = await response.json()
                    user_data = result.get("user", {})
                    user_id = user_data.get("id")
                    display_name = user_data.get("displayName", username)
                    
                    if user_id:
                        # Update stored user ID if it changed
                        stored_creds = self.settings.get_user_credentials()
                        if stored_creds.get("user_id") != str(user_id):
                            self.settings.set_user_id(str(user_id))
                        
                        self.authenticated_user = {
                            "user_id": user_id,
                            "username": username,
                            "display_name": display_name
                        }
                        
                        # Update web API authentication state
                        self.web_api.authenticated = True
                        self.web_api.user_id = user_id
                        self.web_api.username = username
                        
                        logger.info(f"✅ User authenticated: {username} (ID: {user_id})")
                        return self.authenticated_user
                    else:
                        logger.error("❌ Authentication succeeded but no user ID received")
                        return None
                        
                else:
                    error_text = await response.text()
                    logger.error(f"❌ Authentication failed: {response.status} - {error_text}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Failed to authenticate user: {e}")
            return None
    
    def get_authenticated_user(self) -> Optional[Dict]:
        """Get currently authenticated user"""
        return self.authenticated_user
    
    def get_user_credentials(self) -> Dict:
        """Get stored user credentials"""
        return self.settings.get_user_credentials()
    
    async def validate_username(self, username: str) -> bool:
        """Validate if username is available"""
        try:
            # Simple validation - check if user exists
            check_data = {"username": username}
            url = f"{self.web_api.base_url}{self.web_api.api_endpoint}/check-username"
            
            async with self.web_api.session.post(url, json=check_data) as response:
                if response.status == 200:
                    result = await response.json()
                    return result.get("available", False)
                else:
                    # If endpoint doesn't exist, assume available
                    return True
                    
        except Exception as e:
            logger.warning(f"⚠️ Username validation failed: {e}")
            return True  # Assume available if we can't check
    
    def clear_user_configuration(self):
        """Clear user configuration"""
        self.settings.clear_user_config()
        self.authenticated_user = None
        if self.web_api:
            self.web_api.authenticated = False
            self.web_api.user_id = None
            self.web_api.username = None
        logger.info("🧹 User configuration cleared")
    
    def get_setup_status(self) -> Dict:
        """Get current setup status"""
        return {
            "user_configured": self.is_user_configured(),
            "credentials_valid": bool(self.authenticated_user),
            "ready_for_calling": self.is_user_configured() and bool(self.authenticated_user)
        }