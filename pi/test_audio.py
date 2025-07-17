#!/usr/bin/env python3
"""
Test script for ReSpeaker 2-Mics Pi HAT audio functionality
"""
import asyncio
import sys
import os
import logging

# Add src directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from hardware.audio import AudioManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_audio():
    """Test audio functionality"""
    try:
        # Initialize audio manager
        audio_manager = AudioManager()
        await audio_manager.initialize()
        
        logger.info("🧪 Starting audio tests...")
        
        # Test 1: Record audio for 3 seconds
        logger.info("Test 1: Recording audio for 3 seconds...")
        logger.info("  → Please speak into the microphone")
        
        recorded_data = await audio_manager.record_audio(duration=3.0)
        
        if recorded_data:
            logger.info(f"  → Recorded {len(recorded_data)} bytes of audio")
            
            # Save to file
            output_file = "/tmp/test_recording.wav"
            await audio_manager.save_audio(recorded_data, output_file)
            logger.info(f"  → Audio saved to {output_file}")
            
            # Test 2: Play back recorded audio
            logger.info("Test 2: Playing back recorded audio...")
            await audio_manager.play_audio_file(output_file)
            logger.info("  → Playback completed")
            
        else:
            logger.warning("  → No audio data recorded")
        
        # Test 3: Audio level monitoring
        logger.info("Test 3: Audio level monitoring (5 seconds)...")
        logger.info("  → Monitoring microphone input levels")
        
        def level_callback(level):
            bar_length = int(level * 20)  # Scale to 0-20 bar
            bar = "█" * bar_length + "░" * (20 - bar_length)
            print(f"\r  Level: [{bar}] {level:.2f}", end="", flush=True)
        
        await audio_manager.monitor_audio_level(duration=5.0, callback=level_callback)
        print()  # New line after monitoring
        
        # Test 4: Device information
        logger.info("Test 4: Audio device information")
        devices = await audio_manager.get_device_info()
        
        for device in devices:
            logger.info(f"  → Device {device['index']}: {device['name']}")
            logger.info(f"    Max input channels: {device['max_input_channels']}")
            logger.info(f"    Max output channels: {device['max_output_channels']}")
            logger.info(f"    Default sample rate: {device['default_sample_rate']}")
        
        # Cleanup
        logger.info("🧹 Cleaning up...")
        await audio_manager.stop()
        
        logger.info("✅ Audio tests completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Audio test failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_audio())