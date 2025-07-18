#!/usr/bin/env python3
"""
Test Web Client Integration for EmmaPhone2 Pi

Tests the new web client API integration without full hardware
"""
import asyncio
import logging
import sys
import os

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.user_manager import UserManager
from config.settings import Settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_web_client_integration():
    """Test web client API integration"""
    
    print("🧪 Testing EmmaPhone2 Pi Web Client Integration")
    print("=" * 50)
    
    # Load settings
    settings = Settings()
    
    # Check if user is configured
    if not settings.is_user_configured():
        print("❌ User not configured")
        print("Please run 'python3 setup_user.py' first")
        return
    
    # Initialize user manager
    user_manager = UserManager(settings)
    
    try:
        await user_manager.initialize()
        print("✅ User manager initialized")
        
        # Test authentication
        print(f"\n🔐 Testing user authentication...")
        auth_result = await user_manager.authenticate_user()
        
        if auth_result:
            print(f"✅ User authenticated:")
            print(f"  Username: {auth_result['username']}")
            print(f"  User ID: {auth_result['user_id']}")
            print(f"  Display Name: {auth_result['display_name']}")
            
            # Test getting contacts
            print(f"\n📋 Getting user contacts...")
            contacts = await user_manager.web_api.get_user_contacts()
            
            if contacts:
                print(f"✅ Retrieved {len(contacts)} contacts:")
                for contact in contacts[:3]:  # Show first 3
                    print(f"  - {contact.get('contact_name', 'N/A')} (ID: {contact.get('contact_user_id', 'N/A')})")
            else:
                print("⚠️ No contacts found (this is normal for a new user)")
            
            # Test Socket.IO connection
            print(f"\n🔌 Testing Socket.IO connection...")
            from services.web_client import WebClientSocket
            web_config = settings.get_web_client_config()
            socket = WebClientSocket(web_config["url"], web_config["socket_endpoint"])
            
            try:
                await socket.initialize(auth_result["user_id"])
                print("✅ Socket.IO connected")
                
                # Keep connection alive for a moment
                await asyncio.sleep(2)
                
                await socket.disconnect()
                print("✅ Socket.IO disconnected")
                
            except Exception as e:
                print(f"❌ Socket.IO test failed: {e}")
            
        else:
            print("❌ User authentication failed")
            
    except Exception as e:
        print(f"❌ User manager test failed: {e}")
        
    finally:
        await user_manager.close()
        
    print("\n🎉 Web client integration test complete!")

async def test_call_simulation():
    """Simulate a call initiation"""
    
    print("\n🧪 Testing Call Simulation")
    print("=" * 30)
    
    # Load settings
    settings = Settings()
    
    # Check if user is configured
    if not settings.is_user_configured():
        print("❌ User not configured")
        print("Please run 'python3 setup_user.py' first")
        return
    
    # Initialize user manager
    user_manager = UserManager(settings)
    
    try:
        await user_manager.initialize()
        
        # Authenticate user
        auth_result = await user_manager.authenticate_user()
        
        if auth_result:
            print(f"✅ User authenticated: {auth_result['username']}")
            
            # Try to initiate a call to demo user
            target_user_id = "1"  # Demo user 'emma'
            
            print(f"\n📞 Initiating call to user {target_user_id}...")
            call_result = await user_manager.web_api.initiate_call(target_user_id)
            
            if call_result:
                print(f"✅ Call initiated successfully:")
                print(f"  Room: {call_result.get('room_name', 'N/A')}")
                print(f"  Call ID: {call_result.get('call_id', 'N/A')}")
                print(f"  Token: {call_result.get('token', 'N/A')[:20]}...")
            else:
                print("❌ Call initiation failed")
                print("Note: This is expected if target user is not online")
            
        else:
            print("❌ User authentication failed")
            
    except Exception as e:
        print(f"❌ Call simulation failed: {e}")
        
    finally:
        await user_manager.close()

async def main():
    """Run all tests"""
    await test_web_client_integration()
    await test_call_simulation()

if __name__ == "__main__":
    asyncio.run(main())