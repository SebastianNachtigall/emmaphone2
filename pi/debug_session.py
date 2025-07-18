#!/usr/bin/env python3
"""
Debug Pi session authentication
"""
import asyncio
import sys
import os
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.user_manager import UserManager
from config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def debug_session():
    """Debug session authentication for Pi"""
    
    print("🔍 Debugging Pi Session Authentication")
    print("=" * 50)
    
    # Load settings
    settings = Settings()
    
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
            
            # Now test a simple API call to check session
            print(f"\n🔍 Testing session with /api/auth/me...")
            url = f"{user_manager.web_api.base_url}/api/auth/me"
            
            async with user_manager.web_api.session.get(url) as response:
                print(f"Status: {response.status}")
                if response.status == 200:
                    me_data = await response.json()
                    print(f"✅ Session working - /api/auth/me returned: {me_data}")
                else:
                    text = await response.text()
                    print(f"❌ Session failed - /api/auth/me returned: {response.status} - {text}")
            
            # Now test the call initiation with debug
            print(f"\n📞 Testing call initiation with session debug...")
            
            # Test both string and number formats
            for toUser_value in ["1", 1]:
                print(f"\n🔍 Testing toUser: {toUser_value} (type: {type(toUser_value).__name__})")
                call_data = {
                    "toUser": toUser_value
                }
                
                url = f"{user_manager.web_api.base_url}/api/initiate-call"
                
                async with user_manager.web_api.session.post(url, json=call_data) as response:
                    print(f"Call API Status: {response.status}")
                    result = await response.text()
                    print(f"Call API Response: {result}")
                    
                    if response.status != 404:
                        break  # Success, stop testing
                
        else:
            print("❌ User authentication failed")
            
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        await user_manager.close()

if __name__ == "__main__":
    asyncio.run(debug_session())