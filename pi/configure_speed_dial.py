#!/usr/bin/env python3
"""
Configure Speed Dial for EmmaPhone2 Pi

Sets up speed dial contacts with user IDs for calling web client users
"""
import os
import sys

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from config.settings import Settings

def configure_speed_dial():
    """Configure speed dial contacts"""
    settings = Settings()
    
    print("🔧 EmmaPhone2 Pi Speed Dial Configuration")
    print("=" * 50)
    
    # These are the demo users created in the web client
    demo_users = {
        "1": "emma",
        "2": "noah", 
        "3": "olivia",
        "4": "liam"
    }
    
    print("\nAvailable demo users:")
    for user_id, username in demo_users.items():
        print(f"  {user_id}: {username}")
    
    print("\nConfigure speed dial positions:")
    
    # Configure speed dial position 1
    print("\n📞 Speed Dial Position 1 (Double Press):")
    user_id_1 = input("Enter user ID (1-4) or custom user ID: ").strip()
    if user_id_1 in demo_users:
        print(f"  → Will call {demo_users[user_id_1]} (ID: {user_id_1})")
    else:
        print(f"  → Will call user ID: {user_id_1}")
    
    # Configure speed dial position 2
    print("\n📞 Speed Dial Position 2 (Triple Press):")
    user_id_2 = input("Enter user ID (1-4) or custom user ID: ").strip()
    if user_id_2 in demo_users:
        print(f"  → Will call {demo_users[user_id_2]} (ID: {user_id_2})")
    else:
        print(f"  → Will call user ID: {user_id_2}")
    
    # Update settings
    if user_id_1:
        settings.set("user.speed_dial.1", user_id_1)
        print(f"✅ Speed dial 1 set to user {user_id_1}")
    
    if user_id_2:
        settings.set("user.speed_dial.2", user_id_2)
        print(f"✅ Speed dial 2 set to user {user_id_2}")
    
    settings.save_settings()
    
    print("\n🎉 Speed dial configuration complete!")
    print("\nUsage:")
    print("  - Double press button: Call speed dial 1")
    print("  - Triple press button: Call speed dial 2")
    print("  - Short press during call: Answer/Hangup")
    print("  - Long press during call: Reject/Hangup")

if __name__ == "__main__":
    configure_speed_dial()