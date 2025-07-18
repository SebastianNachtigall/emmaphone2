#!/usr/bin/env python3
"""
User Setup for EmmaPhone2 Pi

Interactive script to set up the Pi user account
"""
import asyncio
import getpass
import os
import sys
import re

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.user_manager import UserManager
from config.settings import Settings

def validate_username(username):
    """Validate username format"""
    if not username:
        return False, "Username cannot be empty"
    
    if len(username) < 3:
        return False, "Username must be at least 3 characters long"
    
    if len(username) > 20:
        return False, "Username must be less than 20 characters"
    
    # Allow letters, numbers, and underscores
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, ""

def validate_display_name(display_name):
    """Validate display name format"""
    if not display_name:
        return False, "Display name cannot be empty"
    
    if len(display_name) > 50:
        return False, "Display name must be less than 50 characters"
    
    return True, ""

def validate_password(password):
    """Validate password strength"""
    if not password:
        return False, "Password cannot be empty"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    return True, ""

async def setup_user():
    """Interactive user setup"""
    print("🚀 EmmaPhone2 Pi User Setup")
    print("=" * 40)
    
    # Initialize settings and user manager
    settings = Settings()
    user_manager = UserManager(settings)
    
    try:
        await user_manager.initialize()
    except Exception as e:
        print(f"❌ Failed to connect to web client: {e}")
        print("Please check your internet connection and web client configuration.")
        return
    
    # Check if user is already configured
    if user_manager.is_user_configured():
        print("⚠️ User is already configured!")
        
        creds = user_manager.get_user_credentials()
        print(f"Current user: {creds.get('display_name', 'Unknown')} (@{creds.get('username', 'unknown')})")
        
        choice = input("\nDo you want to reconfigure? (y/N): ").strip().lower()
        if choice != 'y':
            print("👋 Setup cancelled.")
            return
        
        # Clear existing configuration
        user_manager.clear_user_configuration()
        print("🧹 Existing configuration cleared.")
    
    print("\n📝 Create your EmmaPhone2 user account:")
    print("This will be used to call other users and receive calls.")
    
    # Get username
    while True:
        username = input("\nEnter username: ").strip()
        valid, error = validate_username(username)
        
        if not valid:
            print(f"❌ {error}")
            continue
        
        # Check if username is available
        print("🔍 Checking username availability...")
        available = await user_manager.validate_username(username)
        
        if not available:
            print(f"❌ Username '{username}' is already taken")
            continue
        
        print(f"✅ Username '{username}' is available")
        break
    
    # Get display name
    while True:
        display_name = input("Enter display name (shown to other users): ").strip()
        valid, error = validate_display_name(display_name)
        
        if not valid:
            print(f"❌ {error}")
            continue
        
        break
    
    # Get password
    while True:
        password = getpass.getpass("Enter password: ")
        valid, error = validate_password(password)
        
        if not valid:
            print(f"❌ {error}")
            continue
        
        password_confirm = getpass.getpass("Confirm password: ")
        if password != password_confirm:
            print("❌ Passwords do not match")
            continue
        
        break
    
    # Confirm setup
    print(f"\n📋 Setup Summary:")
    print(f"Username: {username}")
    print(f"Display Name: {display_name}")
    print(f"Password: {'*' * len(password)}")
    
    confirm = input("\nCreate this user? (Y/n): ").strip().lower()
    if confirm == 'n':
        print("👋 Setup cancelled.")
        return
    
    # Register user
    print("\n🔄 Registering user with web client...")
    
    user_info = await user_manager.register_new_user(username, display_name, password)
    
    if user_info:
        print(f"✅ User registered successfully!")
        print(f"User ID: {user_info['user_id']}")
        
        # Test authentication
        print("\n🔐 Testing authentication...")
        auth_result = await user_manager.authenticate_user()
        
        if auth_result:
            print("✅ Authentication successful!")
            print(f"Welcome, {auth_result['display_name']}!")
            
            # Show next steps
            print("\n🎉 Setup Complete!")
            print("\nNext steps:")
            print("1. Configure speed dial contacts:")
            print("   python3 configure_speed_dial.py")
            print()
            print("2. Test your setup:")
            print("   python3 test_web_integration.py")
            print()
            print("3. Start the EmmaPhone2 Pi:")
            print("   python3 src/main.py")
            
        else:
            print("❌ Authentication failed - please check your configuration")
    else:
        print("❌ User registration failed")
    
    await user_manager.close()

async def show_user_status():
    """Show current user status"""
    print("📊 EmmaPhone2 Pi User Status")
    print("=" * 35)
    
    settings = Settings()
    user_manager = UserManager(settings)
    
    try:
        await user_manager.initialize()
        
        initial_status = user_manager.get_setup_status()
        
        print(f"User configured: {'✅' if initial_status['user_configured'] else '❌'}")
        
        auth_successful = False
        if initial_status['user_configured']:
            creds = user_manager.get_user_credentials()
            print(f"Username: {creds.get('username', 'Unknown')}")
            print(f"Display Name: {creds.get('display_name', 'Unknown')}")
            print(f"User ID: {creds.get('user_id', 'Unknown')}")
            
            # Test authentication
            print("\n🔐 Testing authentication...")
            auth_result = await user_manager.authenticate_user()
            
            if auth_result:
                print("✅ Authentication successful!")
                auth_successful = True
            else:
                print("❌ Authentication failed")
        
        # Check final status after authentication
        final_status = user_manager.get_setup_status()
        print(f"\nReady for calling: {'✅' if final_status['ready_for_calling'] else '❌'}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    await user_manager.close()

def main():
    """Main entry point"""
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        asyncio.run(show_user_status())
    else:
        asyncio.run(setup_user())

if __name__ == "__main__":
    main()