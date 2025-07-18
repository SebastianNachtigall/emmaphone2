"""
Settings and Configuration for EmmaPhone2 Pi

Manages application settings and configuration
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Settings:
    """Application settings manager"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Use current user's home directory instead of hardcoded /home/pi
            import os
            config_dir = os.path.expanduser("~/.emmaphone")
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "settings.json"
        self.auth_file = self.config_dir / "auth.json"
        
        # Default settings
        self.defaults = {
            "audio": {
                "sample_rate": 44100,
                "channels": 2,
                "chunk_size": 1024,
                "device_index": 1
            },
            "leds": {
                "brightness": 255,
                "animation_speed": 0.05,
                "status_colors": {
                    "startup": [255, 255, 255],
                    "setup_needed": [255, 0, 0],
                    "ready": [0, 255, 0],
                    "incoming_call": [0, 0, 255],
                    "error": [255, 0, 0]
                }
            },
            "button": {
                "long_press_time": 1.0,
                "double_press_time": 0.5,
                "debounce_time": 0.2
            },
            "wifi": {
                "ap_ssid": "EmmaPhone-Setup",
                "ap_password": "EmmaPhone2024",
                "connection_timeout": 30,
                "scan_timeout": 10
            },
            "web_server": {
                "port": 8080,
                "host": "0.0.0.0",
                "ssl_enabled": False
            },
            "livekit": {
                "url": "wss://emmaphone2-livekit-production.up.railway.app",
                "api_key": "APIKeySecret_emmaphone2_static",
                "api_secret": "emmaphone2_static_secret_key_64chars_long_for_proper_security",
                "room_prefix": "emmaphone"
            },
            "web_client": {
                "url": "https://emmaphone2-production.up.railway.app",
                "api_endpoint": "/api",
                "socket_endpoint": "/socket.io"
            },
            "user": {
                "configured": False,
                "username": "",
                "display_name": "",
                "user_id": "",
                "password": "",
                "contacts": [],
                "speed_dial": {}
            },
            "device": {
                "id": "pi_001",
                "name": "EmmaPhone Pi",
                "type": "pi_zero_2w"
            }
        }
        
        self.settings = self.defaults.copy()
        self.load_settings()
    
    def load_settings(self):
        """Load settings from file"""
        try:
            # Create config directory if it doesn't exist
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded_settings = json.load(f)
                
                # Merge with defaults (recursive)
                self.settings = self._merge_settings(self.defaults, loaded_settings)
                
                logger.info("✅ Settings loaded from file")
            else:
                logger.info("📄 Using default settings")
                
        except Exception as e:
            logger.error(f"❌ Failed to load settings: {e}")
            self.settings = self.defaults.copy()
    
    def save_settings(self):
        """Save current settings to file"""
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w') as f:
                json.dump(self.settings, f, indent=2)
            
            logger.info("✅ Settings saved to file")
            
        except Exception as e:
            logger.error(f"❌ Failed to save settings: {e}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get setting value using dot notation (e.g., 'audio.sample_rate')"""
        try:
            keys = key.split('.')
            value = self.settings
            
            for k in keys:
                value = value[k]
            
            return value
            
        except (KeyError, TypeError):
            return default
    
    def set(self, key: str, value: Any):
        """Set setting value using dot notation"""
        try:
            keys = key.split('.')
            setting = self.settings
            
            # Navigate to the parent of the target key
            for k in keys[:-1]:
                if k not in setting:
                    setting[k] = {}
                setting = setting[k]
            
            # Set the final key
            setting[keys[-1]] = value
            
            logger.info(f"📝 Setting updated: {key} = {value}")
            
        except Exception as e:
            logger.error(f"❌ Failed to set {key}: {e}")
    
    def _merge_settings(self, defaults: Dict, loaded: Dict) -> Dict:
        """Recursively merge loaded settings with defaults"""
        result = defaults.copy()
        
        for key, value in loaded.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_settings(result[key], value)
            else:
                result[key] = value
        
        return result
    
    # Convenience methods for common settings
    
    def get_audio_config(self) -> Dict:
        """Get audio configuration"""
        return self.get("audio", {})
    
    def get_led_config(self) -> Dict:
        """Get LED configuration"""
        return self.get("leds", {})
    
    def get_button_config(self) -> Dict:
        """Get button configuration"""
        return self.get("button", {})
    
    def get_wifi_config(self) -> Dict:
        """Get WiFi configuration"""
        return self.get("wifi", {})
    
    def get_livekit_config(self) -> Dict:
        """Get LiveKit configuration"""
        return self.get("livekit", {})
    
    def get_web_client_config(self) -> Dict:
        """Get web client configuration"""
        return self.get("web_client", {})
    
    def get_user_config(self) -> Dict:
        """Get user configuration"""
        return self.get("user", {})
    
    def set_user_name(self, name: str):
        """Set user name"""
        self.set("user.name", name)
        self.save_settings()
    
    def set_user_id(self, user_id: str):
        """Set user ID"""
        self.set("user.user_id", user_id)
        self.save_settings()
    
    def is_user_configured(self) -> bool:
        """Check if user is configured"""
        return self.get("user.configured", False)
    
    def configure_user(self, username: str, display_name: str, password: str, user_id: str = ""):
        """Configure the Pi user"""
        self.set("user.configured", True)
        self.set("user.username", username)
        self.set("user.display_name", display_name)
        self.set("user.password", password)
        if user_id:
            self.set("user.user_id", user_id)
        self.save_settings()
        logger.info(f"👤 User configured: {username}")
    
    def get_user_credentials(self) -> dict:
        """Get user credentials"""
        return {
            "username": self.get("user.username", ""),
            "display_name": self.get("user.display_name", ""),
            "password": self.get("user.password", ""),
            "user_id": self.get("user.user_id", "")
        }
    
    def clear_user_config(self):
        """Clear user configuration"""
        self.set("user.configured", False)
        self.set("user.username", "")
        self.set("user.display_name", "")
        self.set("user.password", "")
        self.set("user.user_id", "")
        self.set("user.contacts", [])
        self.set("user.speed_dial", {})
        self.save_settings()
        logger.info("👤 User configuration cleared")
    
    def add_contact(self, name: str, user_id: str, speed_dial: Optional[int] = None):
        """Add contact to user's contact list"""
        contacts = self.get("user.contacts", [])
        
        contact = {
            "name": name,
            "user_id": user_id,
            "speed_dial": speed_dial
        }
        
        contacts.append(contact)
        self.set("user.contacts", contacts)
        
        # Update speed dial if specified
        if speed_dial:
            speed_dial_config = self.get("user.speed_dial", {})
            speed_dial_config[str(speed_dial)] = user_id
            self.set("user.speed_dial", speed_dial_config)
        
        self.save_settings()
        logger.info(f"📱 Contact added: {name}")
    
    def get_contacts(self) -> list:
        """Get user's contacts"""
        return self.get("user.contacts", [])
    
    def remove_contact(self, contact_name: str = None, user_id: str = None, speed_dial_position: int = None):
        """Remove contact from user's contact list"""
        contacts = self.get("user.contacts", [])
        speed_dial_config = self.get("user.speed_dial", {})
        
        # Find contact to remove by name, user_id, or speed_dial position
        contact_removed = False
        contacts_to_keep = []
        
        for contact in contacts:
            should_remove = False
            
            if contact_name and contact.get("name") == contact_name:
                should_remove = True
            elif user_id and contact.get("user_id") == user_id:
                should_remove = True
            elif speed_dial_position and contact.get("speed_dial") == speed_dial_position:
                should_remove = True
            
            if should_remove:
                # Remove from speed dial config if exists
                if contact.get("speed_dial"):
                    speed_dial_config.pop(str(contact["speed_dial"]), None)
                contact_removed = True
                logger.info(f"📱 Contact removed: {contact.get('name', 'Unknown')}")
            else:
                contacts_to_keep.append(contact)
        
        if contact_removed:
            self.set("user.contacts", contacts_to_keep)
            self.set("user.speed_dial", speed_dial_config)
            self.save_settings()
            return True
        else:
            logger.warning("📱 Contact not found for removal")
            return False
    
    def get_speed_dial(self, position: int) -> Optional[str]:
        """Get speed dial contact for position"""
        speed_dial_config = self.get("user.speed_dial", {})
        return speed_dial_config.get(str(position))
    
    def set_livekit_credentials(self, url: str, api_key: str, api_secret: str):
        """Set LiveKit credentials"""
        self.set("livekit.url", url)
        self.set("livekit.api_key", api_key)
        self.set("livekit.api_secret", api_secret)
        self.save_settings()
        logger.info("🔐 LiveKit credentials updated")
    
    def is_configured(self) -> bool:
        """Check if basic configuration is complete"""
        livekit_config = self.get_livekit_config()
        web_client_config = self.get_web_client_config()
        
        return (
            livekit_config.get("url") and
            livekit_config.get("api_key") and
            livekit_config.get("api_secret") and
            web_client_config.get("url") and
            self.is_user_configured()
        )
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self.defaults.copy()
        self.save_settings()
        logger.info("🔄 Settings reset to defaults")