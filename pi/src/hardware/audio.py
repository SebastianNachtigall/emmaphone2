"""
Audio Manager for ReSpeaker 2-Mics Pi HAT

Handles audio recording and playback using PyAudio
"""
import asyncio
import logging
import wave
import pyaudio
import numpy as np
from typing import Optional, Callable

logger = logging.getLogger(__name__)

class AudioManager:
    """Manages audio recording and playback for ReSpeaker HAT"""
    
    # Audio configuration for ReSpeaker HAT
    SAMPLE_RATE = 44100
    CHUNK_SIZE = 1024
    CHANNELS = 2  # Stereo from dual microphones
    FORMAT = pyaudio.paInt16
    
    # Device configuration (usually hw:1,0 for ReSpeaker HAT)
    DEVICE_INDEX = 1  # Card 1 (seeed2micvoicec)
    
    def __init__(self):
        self.pyaudio_instance = None
        self.input_stream = None
        self.output_stream = None
        self.recording = False
        self.playing = False
        self.audio_callback = None
        
    async def initialize(self):
        """Initialize PyAudio"""
        try:
            # Suppress ALSA warnings
            import os
            os.environ['ALSA_PCM_CARD'] = '1'
            os.environ['ALSA_PCM_DEVICE'] = '0'
            
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # List available devices
            await self._list_audio_devices()
            
            logger.info("✅ Audio manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize audio manager: {e}")
            raise
    
    async def _list_audio_devices(self):
        """List available audio devices for debugging"""
        logger.info("🔍 Available audio devices:")
        
        info = self.pyaudio_instance.get_host_api_info_by_index(0)
        device_count = info.get('deviceCount')
        
        for i in range(device_count):
            device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
            
            if device_info.get('maxInputChannels') > 0:
                logger.info(f"  📥 Input Device {i}: {device_info.get('name')}")
            
            if device_info.get('maxOutputChannels') > 0:
                logger.info(f"  📤 Output Device {i}: {device_info.get('name')}")
    
    async def start_recording(self, callback: Optional[Callable] = None):
        """Start audio recording"""
        if self.recording:
            logger.warning("⚠️  Already recording")
            return
        
        try:
            self.audio_callback = callback
            
            self.input_stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                input=True,
                input_device_index=self.DEVICE_INDEX,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=self._audio_callback if callback else None
            )
            
            self.recording = True
            logger.info("🎤 Recording started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording: {e}")
            raise
    
    async def stop_recording(self):
        """Stop audio recording"""
        if not self.recording:
            return
        
        self.recording = False
        
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
            self.input_stream = None
        
        logger.info("🛑 Recording stopped")
    
    async def start_playback(self, callback: Optional[Callable] = None):
        """Start audio playback"""
        if self.playing:
            logger.warning("⚠️  Already playing")
            return
        
        try:
            self.output_stream = self.pyaudio_instance.open(
                format=self.FORMAT,
                channels=self.CHANNELS,
                rate=self.SAMPLE_RATE,
                output=True,
                output_device_index=self.DEVICE_INDEX,
                frames_per_buffer=self.CHUNK_SIZE,
                stream_callback=callback if callback else None
            )
            
            self.playing = True
            logger.info("🔊 Playback started")
            
        except Exception as e:
            logger.error(f"❌ Failed to start playback: {e}")
            raise
    
    async def stop_playback(self):
        """Stop audio playback"""
        if not self.playing:
            return
        
        self.playing = False
        
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
            self.output_stream = None
        
        logger.info("🛑 Playback stopped")
    
    def _audio_callback(self, in_data, frame_count, time_info, status):
        """Audio stream callback"""
        if self.audio_callback:
            try:
                # Convert bytes to numpy array
                audio_data = np.frombuffer(in_data, dtype=np.int16)
                
                # Call user callback
                if asyncio.iscoroutinefunction(self.audio_callback):
                    # For async callbacks, we need to schedule them
                    asyncio.create_task(self.audio_callback(audio_data))
                else:
                    self.audio_callback(audio_data)
                    
            except Exception as e:
                logger.error(f"❌ Audio callback error: {e}")
        
        return (in_data, pyaudio.paContinue)
    
    async def record_to_file(self, filename: str, duration: float):
        """Record audio to WAV file"""
        logger.info(f"📁 Recording to {filename} for {duration} seconds")
        
        frames = []
        
        def record_callback(audio_data):
            frames.append(audio_data.tobytes())
        
        await self.start_recording(record_callback)
        await asyncio.sleep(duration)
        await self.stop_recording()
        
        # Save to file
        with wave.open(filename, 'wb') as wf:
            wf.setnchannels(self.CHANNELS)
            wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.FORMAT))
            wf.setframerate(self.SAMPLE_RATE)
            wf.writeframes(b''.join(frames))
        
        logger.info(f"✅ Recording saved to {filename}")
    
    async def play_from_file(self, filename: str):
        """Play audio from WAV file"""
        logger.info(f"🎵 Playing {filename}")
        
        try:
            with wave.open(filename, 'rb') as wf:
                def play_callback(in_data, frame_count, time_info, status):
                    data = wf.readframes(frame_count)
                    return (data, pyaudio.paContinue if data else pyaudio.paComplete)
                
                await self.start_playback(play_callback)
                
                # Wait for playback to complete
                while self.output_stream.is_active():
                    await asyncio.sleep(0.1)
                
                await self.stop_playback()
                
        except Exception as e:
            logger.error(f"❌ Failed to play file {filename}: {e}")
    
    async def test_loopback(self, duration: float = 5.0):
        """Test audio loopback (record and immediately play back)"""
        logger.info(f"🔄 Testing audio loopback for {duration} seconds")
        
        audio_buffer = []
        
        def record_callback(audio_data):
            audio_buffer.append(audio_data.tobytes())
        
        def play_callback(in_data, frame_count, time_info, status):
            if audio_buffer:
                data = audio_buffer.pop(0)
                return (data, pyaudio.paContinue)
            else:
                return (b'\x00' * frame_count * self.CHANNELS * 2, pyaudio.paContinue)
        
        # Start recording and playback simultaneously
        await self.start_recording(record_callback)
        await asyncio.sleep(0.1)  # Small delay to fill buffer
        await self.start_playback(play_callback)
        
        # Run loopback test
        await asyncio.sleep(duration)
        
        # Stop both
        await self.stop_recording()
        await self.stop_playback()
        
        logger.info("✅ Audio loopback test complete")
    
    async def get_audio_level(self) -> float:
        """Get current audio input level (0.0 to 1.0)"""
        if not self.recording:
            return 0.0
        
        try:
            # Read a chunk of audio data
            data = self.input_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range
            level = min(rms / 32768.0, 1.0)
            
            return level
            
        except Exception as e:
            logger.error(f"❌ Error getting audio level: {e}")
            return 0.0
    
    async def stop(self):
        """Stop all audio operations and cleanup"""
        await self.stop_recording()
        await self.stop_playback()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        logger.info("🛑 Audio manager stopped")