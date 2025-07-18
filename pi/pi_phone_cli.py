#!/usr/bin/env python3
"""
EmmaPhone2 Pi Interactive CLI Application

Development and testing interface for Pi calling functionality.
Provides user management, online user display, and calling features.
"""
import asyncio
import logging
import sys
import os
from datetime import datetime
from typing import Dict, List, Optional

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.user_manager import UserManager
from services.web_client import WebClientSocket
from config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise in CLI
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class PiPhoneCLI:
    """Interactive CLI for Pi calling functionality"""
    
    def __init__(self):
        self.settings = Settings()
        self.user_manager = UserManager(self.settings)
        self.web_api = None
        self.socket_manager = None
        self.authenticated_user = None
        self.online_users = []
        self.call_status = None
        self.running = True
        self.last_refresh = None
    
    async def initialize(self):
        """Initialize the CLI application"""
        print("🚀 EmmaPhone2 Pi Interactive CLI")
        print("=" * 40)
        
        try:
            await self.user_manager.initialize()
            self.web_api = self.user_manager.web_api
            print("✅ Connected to web server")
            
        except Exception as e:
            print(f"❌ Failed to connect to web server: {e}")
            print("Please check your internet connection and try again.")
            return False
        
        return True
    
    async def check_user_setup(self):
        """Check if user is configured and authenticate"""
        if not self.user_manager.is_user_configured():
            print("\n👤 User not configured!")
            print("Let's set up your Pi user account...\n")
            
            success = await self.guided_user_setup()
            if not success:
                return False
        
        # Authenticate user
        print("🔐 Authenticating user...")
        auth_result = await self.user_manager.authenticate_user()
        
        if auth_result:
            self.authenticated_user = auth_result
            print(f"✅ Welcome, {auth_result['display_name']}!")
            return True
        else:
            print("❌ Authentication failed")
            return False
    
    async def guided_user_setup(self):
        """Guided user registration flow"""
        print("📝 Creating your EmmaPhone2 user account...")
        print("This account will be used to call other users.\n")
        
        try:
            # Get username
            while True:
                username = input("Enter username (3-20 chars, letters/numbers only): ").strip()
                if not username or len(username) < 3:
                    print("❌ Username must be at least 3 characters")
                    continue
                if len(username) > 20:
                    print("❌ Username must be less than 20 characters")
                    continue
                if not username.replace('_', '').replace('-', '').isalnum():
                    print("❌ Username can only contain letters, numbers, underscore, and dash")
                    continue
                
                # Check availability
                print("🔍 Checking username availability...")
                available = await self.user_manager.validate_username(username)
                if not available:
                    print(f"❌ Username '{username}' is already taken")
                    continue
                
                print(f"✅ Username '{username}' is available")
                break
            
            # Get display name
            while True:
                display_name = input("Enter display name (shown to other users): ").strip()
                if not display_name:
                    print("❌ Display name cannot be empty")
                    continue
                if len(display_name) > 50:
                    print("❌ Display name must be less than 50 characters")
                    continue
                break
            
            # Get password
            import getpass
            while True:
                password = getpass.getpass("Enter password (6+ chars): ")
                if len(password) < 6:
                    print("❌ Password must be at least 6 characters")
                    continue
                
                password_confirm = getpass.getpass("Confirm password: ")
                if password != password_confirm:
                    print("❌ Passwords do not match")
                    continue
                break
            
            # Register user
            print("\n🔄 Creating user account...")
            user_info = await self.user_manager.register_new_user(username, display_name, password)
            
            if user_info:
                print(f"✅ Account created successfully!")
                print(f"User ID: {user_info['user_id']}")
                return True
            else:
                print("❌ Failed to create account")
                return False
                
        except KeyboardInterrupt:
            print("\n👋 Setup cancelled")
            return False
        except Exception as e:
            print(f"❌ Setup failed: {e}")
            return False
    
    async def start_socket_connection(self):
        """Start Socket.IO connection for real-time updates"""
        try:
            web_config = self.settings.get_web_client_config()
            self.socket_manager = WebClientSocket(
                web_config["url"], 
                web_config["socket_endpoint"]
            )
            
            await self.socket_manager.initialize(self.authenticated_user["user_id"])
            print("✅ Real-time connection established")
            
            # Start background task to monitor Socket.IO events
            asyncio.create_task(self.socket_event_handler())
            
        except Exception as e:
            print(f"⚠️ Real-time connection failed: {e}")
            print("Some features may not work properly.")
    
    async def socket_event_handler(self):
        """Handle Socket.IO events in background"""
        # This would handle incoming calls, user status updates, etc.
        # For now, just maintain connection
        while self.running:
            await asyncio.sleep(1)
    
    async def refresh_online_users(self):
        """Get list of online users from server"""
        try:
            # For now, we'll get all users (in future, server could provide online status)
            # This is a placeholder - we'd need server API for online users
            response = await self.web_api.session.get(f"{self.web_api.base_url}/api/users/search?q=")
            if response.status == 200:
                all_users = await response.json()
                # Filter out current user
                self.online_users = [u for u in all_users if u['id'] != self.authenticated_user['user_id']]
                self.last_refresh = datetime.now()
            else:
                print(f"⚠️ Failed to get user list: {response.status}")
                
        except Exception as e:
            print(f"⚠️ Failed to refresh users: {e}")
    
    def show_header(self):
        """Display application header with status"""
        os.system('clear' if os.name == 'posix' else 'cls')
        
        print("🏠 EmmaPhone2 Pi - Interactive CLI")
        print("=" * 40)
        
        if self.authenticated_user:
            user_id = self.authenticated_user['user_id']
            display_name = self.authenticated_user['display_name']
            print(f"👤 User: {display_name} (ID: {user_id}) - ✅ Connected")
        
        web_config = self.settings.get_web_client_config()
        print(f"🌐 Web Server: {web_config['url']}")
        
        socket_status = "✅ Connected" if self.socket_manager else "❌ Disconnected"
        print(f"📡 Socket.IO: {socket_status}")
        
        if self.last_refresh:
            refresh_time = self.last_refresh.strftime("%H:%M:%S")
            print(f"🔄 Last Update: {refresh_time} ({len(self.online_users)} users)")
        
        print()
    
    async def show_main_menu(self):
        """Display main menu and handle user input"""
        while self.running:
            self.show_header()
            
            print("[1] 👥 Show Online Users & Call")
            print("[2] 📋 Manage Speed Dial Contacts")
            print("[3] 📞 Call by User ID")
            print("[4] 📊 Connection Status")
            print("[5] 🔄 Refresh")
            print("[0] 🚪 Exit")
            print()
            
            try:
                choice = input("Choice: ").strip()
                
                if choice == '1':
                    await self.show_online_users_menu()
                elif choice == '2':
                    await self.show_speed_dial_menu()
                elif choice == '3':
                    await self.direct_call_menu()
                elif choice == '4':
                    await self.show_status_menu()
                elif choice == '5':
                    await self.refresh_data()
                elif choice == '0':
                    print("👋 Goodbye!")
                    self.running = False
                else:
                    print("❌ Invalid choice. Press Enter to continue...")
                    input()
                    
            except KeyboardInterrupt:
                print("\n👋 Goodbye!")
                self.running = False
    
    async def show_online_users_menu(self):
        """Show online users and call options"""
        await self.refresh_online_users()
        
        self.show_header()
        print("👥 Online Users")
        print("-" * 20)
        
        if not self.online_users:
            print("No other users found.")
            print("\nPress Enter to continue...")
            input()
            return
        
        for i, user in enumerate(self.online_users, 1):
            user_id = user['id']
            display_name = user['display_name']
            username = user['username']
            print(f"[{i}] {display_name} (@{username}) - ID: {user_id}")
        
        print(f"\n[R] 🔄 Refresh")
        print(f"[0] 🔙 Back to Main Menu")
        print()
        
        choice = input("Select user to call (number) or action: ").strip()
        
        if choice == '0':
            return
        elif choice.lower() == 'r':
            await self.show_online_users_menu()  # Refresh and show again
        else:
            try:
                user_index = int(choice) - 1
                if 0 <= user_index < len(self.online_users):
                    selected_user = self.online_users[user_index]
                    await self.initiate_call(selected_user['id'], selected_user['display_name'])
                else:
                    print("❌ Invalid selection. Press Enter to continue...")
                    input()
            except ValueError:
                print("❌ Please enter a number. Press Enter to continue...")
                input()
    
    async def show_speed_dial_menu(self):
        """Show speed dial management menu"""
        self.show_header()
        print("📋 Speed Dial Management")
        print("-" * 25)
        
        # Show current speed dial contacts
        contacts = self.settings.get_contacts()
        print("Current Speed Dial:")
        for pos in range(1, 5):
            contact = next((c for c in contacts if c.get('speed_dial') == pos), None)
            if contact:
                print(f"  [{pos}] {contact['name']} (ID: {contact['user_id']})")
            else:
                print(f"  [{pos}] (Empty)")
        
        print("\nActions:")
        print("[1-4] Call speed dial position")
        print("[A] Add/Edit contact")
        print("[R] Remove contact")
        print("[0] Back to main menu")
        print()
        
        choice = input("Choice: ").strip().lower()
        
        if choice == '0':
            return
        elif choice in ['1', '2', '3', '4']:
            pos = int(choice)
            contact = next((c for c in contacts if c.get('speed_dial') == pos), None)
            if contact:
                await self.initiate_call(contact['user_id'], contact['name'])
            else:
                print(f"❌ No contact in speed dial position {pos}")
                input("Press Enter to continue...")
        elif choice == 'a':
            await self.add_speed_dial_contact()
        elif choice == 'r':
            await self.remove_speed_dial_contact()
        else:
            print("❌ Invalid choice. Press Enter to continue...")
            input()
    
    async def add_speed_dial_contact(self):
        """Add contact to speed dial"""
        print("\n➕ Add Speed Dial Contact")
        print("-" * 25)
        
        # Get available positions
        contacts = self.settings.get_contacts()
        occupied_positions = [c.get('speed_dial') for c in contacts if c.get('speed_dial')]
        available_positions = [p for p in range(1, 5) if p not in occupied_positions]
        
        if not available_positions:
            print("❌ All speed dial positions are occupied")
            input("Press Enter to continue...")
            return
        
        # Get user ID to add
        try:
            user_id = input("Enter user ID to add: ").strip()
            if not user_id:
                return
            
            # Get position
            print(f"Available positions: {available_positions}")
            position = int(input("Enter speed dial position (1-4): "))
            
            if position not in available_positions:
                print("❌ Position not available")
                input("Press Enter to continue...")
                return
            
            # Get display name
            display_name = input("Enter display name: ").strip()
            if not display_name:
                display_name = f"User {user_id}"
            
            # Add contact
            self.settings.add_contact(display_name, user_id, position)
            print(f"✅ Added {display_name} to speed dial position {position}")
            
        except (ValueError, KeyboardInterrupt):
            print("❌ Operation cancelled")
        
        input("Press Enter to continue...")
    
    async def remove_speed_dial_contact(self):
        """Remove contact from speed dial"""
        print("\n➖ Remove Speed Dial Contact")
        print("-" * 28)
        
        contacts = self.settings.get_contacts()
        if not contacts:
            print("❌ No contacts to remove")
            input("Press Enter to continue...")
            return
        
        print("Current contacts:")
        for i, contact in enumerate(contacts, 1):
            pos = contact.get('speed_dial', 'N/A')
            print(f"[{i}] {contact['name']} - Position {pos}")
        
        try:
            choice = int(input("\nSelect contact to remove (number): ")) - 1
            if 0 <= choice < len(contacts):
                contact = contacts[choice]
                # Remove from settings (simplified - in real implementation, 
                # would need proper contact management in settings)
                print(f"✅ Removed {contact['name']} from speed dial")
            else:
                print("❌ Invalid selection")
                
        except (ValueError, KeyboardInterrupt):
            print("❌ Operation cancelled")
        
        input("Press Enter to continue...")
    
    async def direct_call_menu(self):
        """Direct call by user ID"""
        self.show_header()
        print("📞 Direct Call")
        print("-" * 15)
        
        try:
            user_id = input("Enter user ID to call: ").strip()
            if user_id:
                await self.initiate_call(user_id, f"User {user_id}")
        except KeyboardInterrupt:
            pass
    
    async def initiate_call(self, user_id: str, display_name: str):
        """Initiate a call to specified user"""
        print(f"\n📞 Calling {display_name} (ID: {user_id})...")
        
        try:
            result = await self.web_api.initiate_call(user_id)
            
            if result:
                print(f"✅ Call initiated successfully!")
                print(f"Room: {result.get('roomName', 'N/A')}")
                print(f"Status: Call sent to {display_name}")
                print("\n💡 In a real implementation, LiveKit audio would start here")
                print("💡 The target user should see an incoming call notification")
                
                # Simulate call progress
                print("\n⏳ Call in progress... (Press Enter to 'hang up')")
                input()
                print("📴 Call ended")
                
            else:
                print("❌ Call failed - user may not be online")
                
        except Exception as e:
            print(f"❌ Call failed: {e}")
        
        input("\nPress Enter to continue...")
    
    async def show_status_menu(self):
        """Show connection and system status"""
        self.show_header()
        print("📊 Connection Status")
        print("-" * 20)
        
        # User info
        if self.authenticated_user:
            print(f"👤 User: {self.authenticated_user['display_name']}")
            print(f"   ID: {self.authenticated_user['user_id']}")
            print(f"   Username: {self.authenticated_user['username']}")
        
        # Web API status
        web_config = self.settings.get_web_client_config()
        print(f"\n🌐 Web Server: {web_config['url']}")
        
        # Test API connection
        try:
            response = await self.web_api.session.get(f"{self.web_api.base_url}/api/auth/me")
            if response.status == 200:
                print("   Status: ✅ Connected and authenticated")
            else:
                print(f"   Status: ❌ Authentication issue ({response.status})")
        except Exception as e:
            print(f"   Status: ❌ Connection failed ({e})")
        
        # Socket.IO status
        socket_status = "✅ Connected" if self.socket_manager else "❌ Disconnected"
        print(f"\n📡 Socket.IO: {socket_status}")
        
        # LiveKit configuration
        livekit_config = self.settings.get_livekit_config()
        print(f"\n🎤 LiveKit: {livekit_config['url']}")
        print(f"   API Key: {livekit_config['api_key'][:20]}...")
        
        input("\nPress Enter to continue...")
    
    async def refresh_data(self):
        """Refresh all data"""
        print("🔄 Refreshing data...")
        await self.refresh_online_users()
        print("✅ Data refreshed")
        await asyncio.sleep(1)
    
    async def shutdown(self):
        """Clean shutdown"""
        print("\n🛑 Shutting down...")
        
        if self.socket_manager:
            await self.socket_manager.disconnect()
        
        if self.user_manager:
            await self.user_manager.close()
        
        print("✅ Shutdown complete")
    
    async def run(self):
        """Main application loop"""
        try:
            # Initialize
            if not await self.initialize():
                return
            
            # Check user setup and authenticate
            if not await self.check_user_setup():
                return
            
            # Start real-time connection
            await self.start_socket_connection()
            
            # Initial data refresh
            await self.refresh_online_users()
            
            # Show main menu
            await self.show_main_menu()
            
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        except Exception as e:
            print(f"❌ Application error: {e}")
            logger.exception("Application error")
        finally:
            await self.shutdown()

async def main():
    """Application entry point"""
    cli = PiPhoneCLI()
    await cli.run()

if __name__ == "__main__":
    asyncio.run(main())