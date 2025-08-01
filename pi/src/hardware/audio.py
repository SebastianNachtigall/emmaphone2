"""
Audio Manager for ReSpeaker 2-Mics Pi HAT

Handles audio recording and playback using PyAudio
"""
import asyncio
import logging
import time
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
    
    # Device configuration (auto-detect ReSpeaker HAT)
    DEVICE_INDEX = None  # Will be auto-detected
    
    def __init__(self):
        self.pyaudio_instance = None
        self.input_stream = None
        self.output_stream = None
        self.recording = False
        self.playing = False
        self.audio_callback = None
        
        # Call recording - mixed audio (both participants)
        self.call_recording_frames = []
        self.call_recording_filename = None
        self.call_recording_active = False
        
    async def initialize(self):
        """Initialize PyAudio"""
        try:
            # Suppress ALSA warnings
            import os
            os.environ['ALSA_PCM_CARD'] = '1'
            os.environ['ALSA_PCM_DEVICE'] = '0'
            
            self.pyaudio_instance = pyaudio.PyAudio()
            
            # Auto-detect ReSpeaker device
            await self._detect_audio_device()
            
            # List available devices
            await self._list_audio_devices()
            
            logger.info("✅ Audio manager initialized")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize audio manager: {e}")
            raise
    
    async def _detect_audio_device(self):
        """Auto-detect ReSpeaker HAT or best available input device"""
        try:
            info = self.pyaudio_instance.get_host_api_info_by_index(0)
            device_count = info.get('deviceCount')
            
            # Look for ReSpeaker devices first
            respeaker_devices = []
            input_devices = []
            
            for i in range(device_count):
                device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
                device_name = device_info.get('name', '').lower()
                max_inputs = device_info.get('maxInputChannels', 0)
                
                if max_inputs > 0:
                    input_devices.append((i, device_name, max_inputs))
                    
                    # Check for ReSpeaker patterns
                    if any(pattern in device_name for pattern in ['respeaker', 'seeed', '2mic']):
                        respeaker_devices.append((i, device_name, max_inputs))
            
            # Prefer ReSpeaker devices
            if respeaker_devices:
                self.DEVICE_INDEX = respeaker_devices[0][0]
                logger.info(f"🎤 Detected ReSpeaker device: {respeaker_devices[0][1]} (index {self.DEVICE_INDEX})")
            elif input_devices:
                # Fall back to first available input device
                self.DEVICE_INDEX = input_devices[0][0]
                logger.info(f"🎤 Using input device: {input_devices[0][1]} (index {self.DEVICE_INDEX})")
            else:
                # Default fallback
                self.DEVICE_INDEX = 1
                logger.warning(f"⚠️ No input devices found, using default index {self.DEVICE_INDEX}")
                
        except Exception as e:
            logger.error(f"❌ Device detection failed: {e}")
            self.DEVICE_INDEX = 1  # Fallback
    
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
            # Skip level reading if stream is being used for file recording
            if hasattr(self, 'recording_frames') and self.recording_frames is not None:
                return 0.0  # Return 0 during file recording to avoid conflicts
            
            # Read a chunk of audio data
            data = self.input_stream.read(self.CHUNK_SIZE, exception_on_overflow=False)
            audio_data = np.frombuffer(data, dtype=np.int16)
            
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            
            # Normalize to 0-1 range
            level = min(rms / 32768.0, 1.0)
            
            return level
            
        except Exception as e:
            # Silently return 0 for stream conflicts during call recording
            if "callback stream" in str(e) or "Stream closed" in str(e):
                return 0.0
            logger.error(f"❌ Error getting audio level: {e}")
            return 0.0
    
    async def record_audio(self, duration: float = 3.0) -> Optional[bytes]:
        """Record audio for specified duration and return raw audio data"""
        logger.info(f"🎤 Recording audio for {duration} seconds")
        
        frames = []
        
        def record_callback(audio_data):
            frames.append(audio_data.tobytes())
        
        try:
            await self.start_recording(record_callback)
            await asyncio.sleep(duration)
            await self.stop_recording()
            
            if frames:
                audio_data = b''.join(frames)
                logger.info(f"✅ Recorded {len(audio_data)} bytes")
                return audio_data
            else:
                logger.warning("⚠️  No audio data recorded")
                return None
                
        except Exception as e:
            logger.error(f"❌ Failed to record audio: {e}")
            return None
    
    async def save_audio(self, audio_data: bytes, filename: str):
        """Save raw audio data to WAV file"""
        try:
            with wave.open(filename, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.FORMAT))
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(audio_data)
            
            logger.info(f"✅ Audio saved to {filename}")
            
        except Exception as e:
            logger.error(f"❌ Failed to save audio to {filename}: {e}")
    
    async def play_audio_file(self, filename: str):
        """Play audio from WAV file"""
        return await self.play_from_file(filename)
    
    async def monitor_audio_level(self, duration: float = 5.0, callback: Optional[Callable] = None):
        """Monitor audio input levels for specified duration"""
        logger.info(f"📊 Monitoring audio levels for {duration} seconds")
        
        levels = []
        
        def level_callback(audio_data):
            # Calculate RMS level
            rms = np.sqrt(np.mean(audio_data.astype(np.float32) ** 2))
            level = min(rms / 32768.0, 1.0)
            levels.append(level)
            
            if callback:
                callback(level)
        
        try:
            await self.start_recording(level_callback)
            await asyncio.sleep(duration)
            await self.stop_recording()
            
            if levels:
                avg_level = np.mean(levels)
                max_level = np.max(levels)
                logger.info(f"📈 Average level: {avg_level:.3f}, Max level: {max_level:.3f}")
            
        except Exception as e:
            logger.error(f"❌ Failed to monitor audio levels: {e}")
    
    async def get_device_info(self) -> list:
        """Get detailed information about available audio devices"""
        devices = []
        
        if not self.pyaudio_instance:
            return devices
        
        info = self.pyaudio_instance.get_host_api_info_by_index(0)
        device_count = info.get('deviceCount')
        
        for i in range(device_count):
            device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, i)
            
            devices.append({
                'index': i,
                'name': device_info.get('name', 'Unknown'),
                'max_input_channels': device_info.get('maxInputChannels', 0),
                'max_output_channels': device_info.get('maxOutputChannels', 0),
                'default_sample_rate': device_info.get('defaultSampleRate', 0)
            })
        
        return devices
    
    def set_device_index(self, device_index: int):
        """Manually set the audio device index"""
        old_index = self.DEVICE_INDEX
        self.DEVICE_INDEX = device_index
        logger.info(f"🎤 Audio device changed from {old_index} to {device_index}")
    
    def get_current_device_info(self) -> dict:
        """Get information about currently selected device"""
        if not self.pyaudio_instance or self.DEVICE_INDEX is None:
            return {}
        
        try:
            device_info = self.pyaudio_instance.get_device_info_by_host_api_device_index(0, self.DEVICE_INDEX)
            return {
                'index': self.DEVICE_INDEX,
                'name': device_info.get('name', 'Unknown'),
                'max_input_channels': device_info.get('maxInputChannels', 0),
                'max_output_channels': device_info.get('maxOutputChannels', 0),
                'default_sample_rate': device_info.get('defaultSampleRate', 0)
            }
        except Exception as e:
            logger.error(f"❌ Error getting current device info: {e}")
            return {}
    
    async def start_recording_to_file(self, filename: str) -> bool:
        """Start continuous recording to file for call recording"""
        try:
            if self.recording:
                logger.warning("⚠️ Already recording, stopping current recording first")
                await self.stop_recording()
            
            # Initialize recording state
            self.recording_frames = []
            self.recording_filename = filename
            
            logger.info(f"📹 Starting file recording to: {filename}")
            logger.info(f"🎤 Using device index: {self.DEVICE_INDEX}")
            
            def file_record_callback(audio_data):
                """Callback to collect audio data for file recording"""
                self.recording_frames.append(audio_data.tobytes())
                if len(self.recording_frames) % 100 == 0:  # Log every ~2.3 seconds
                    logger.info(f"📹 Recording: {len(self.recording_frames)} chunks collected")
            
            await self.start_recording(file_record_callback)
            logger.info(f"📹 File recording started successfully: {filename}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start recording to file: {e}")
            return False
    
    async def stop_recording_to_file(self) -> bool:
        """Stop continuous recording and save to file"""
        try:
            if not self.recording or not hasattr(self, 'recording_frames'):
                logger.warning("⚠️ No active file recording to stop")
                return False
            
            await self.stop_recording()
            
            if hasattr(self, 'recording_frames') and self.recording_frames:
                # Save recorded data to file
                with wave.open(self.recording_filename, 'wb') as wf:
                    wf.setnchannels(self.CHANNELS)
                    wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.FORMAT))
                    wf.setframerate(self.SAMPLE_RATE)
                    wf.writeframes(b''.join(self.recording_frames))
                
                logger.info(f"📹 Recording saved to: {self.recording_filename}")
                
                # Cleanup
                delattr(self, 'recording_frames')
                delattr(self, 'recording_filename')
                return True
            else:
                logger.warning("⚠️ No audio data recorded to file")
                return False
                
        except Exception as e:
            logger.error(f"❌ Failed to stop recording to file: {e}")
            return False

    async def stop(self):
        """Stop all audio operations and cleanup"""
        await self.stop_recording()
        await self.stop_playback()
        
        if self.pyaudio_instance:
            self.pyaudio_instance.terminate()
            self.pyaudio_instance = None
        
        logger.info("🛑 Audio manager stopped")
    
    async def start_call_recording_mixed(self, filename: str) -> bool:
        """Start mixed call recording (both microphone and incoming audio)"""
        try:
            self.call_recording_frames = []
            self.call_recording_filename = filename
            self.call_recording_active = True
            
            logger.info(f"📹 Started mixed call recording: {filename}")
            logger.info("📹 Recording will capture both microphone input and incoming audio")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start mixed call recording: {e}")
            return False
    
    def add_microphone_to_recording(self, audio_data: np.ndarray):
        """Add microphone audio to call recording"""
        if self.call_recording_active:
            # Store with channel identifier (0 = microphone)
            self.call_recording_frames.append({
                'source': 'microphone',
                'data': audio_data.tobytes(),
                'timestamp': time.time()
            })
    
    def add_incoming_to_recording(self, audio_data: bytes):
        """Add incoming audio (from LiveKit) to call recording"""
        if self.call_recording_active:
            # Store with channel identifier (1 = incoming)
            self.call_recording_frames.append({
                'source': 'incoming',
                'data': audio_data,
                'timestamp': time.time()
            })
    
    async def stop_call_recording_mixed(self) -> Optional[str]:
        """Stop mixed call recording and save to file"""
        try:
            if not self.call_recording_active:
                logger.warning("⚠️ No active mixed call recording to stop")
                return None
            
            self.call_recording_active = False
            
            if not self.call_recording_frames:
                logger.warning("⚠️ No audio data recorded")
                return None
            
            # Sort frames by timestamp to maintain chronological order
            self.call_recording_frames.sort(key=lambda x: x['timestamp'])
            
            # Mix the audio streams
            mixed_audio = self._mix_audio_streams()
            
            # Save to WAV file
            with wave.open(self.call_recording_filename, 'wb') as wf:
                wf.setnchannels(self.CHANNELS)
                wf.setsampwidth(self.pyaudio_instance.get_sample_size(self.FORMAT))
                wf.setframerate(self.SAMPLE_RATE)
                wf.writeframes(mixed_audio)
            
            logger.info(f"📹 Mixed call recording saved: {self.call_recording_filename}")
            logger.info(f"📹 Recorded {len(self.call_recording_frames)} audio chunks")
            
            filename = self.call_recording_filename
            
            # Cleanup
            self.call_recording_frames = []
            self.call_recording_filename = None
            
            return filename
            
        except Exception as e:
            logger.error(f"❌ Failed to stop mixed call recording: {e}")
            return None
    
    def _mix_audio_streams(self) -> bytes:
        """Mix microphone and incoming audio streams into single audio track"""
        try:
            import time
            
            # Group frames by time windows (e.g., 50ms windows)
            window_size = 0.05  # 50ms
            start_time = self.call_recording_frames[0]['timestamp']
            
            mixed_chunks = []
            current_window_start = start_time
            
            while current_window_start < self.call_recording_frames[-1]['timestamp']:
                window_end = current_window_start + window_size
                
                # Get all frames in this time window
                window_frames = [
                    frame for frame in self.call_recording_frames
                    if current_window_start <= frame['timestamp'] < window_end
                ]
                
                if window_frames:
                    # Mix audio for this window
                    mic_data = []
                    incoming_data = []
                    
                    for frame in window_frames:
                        audio_array = np.frombuffer(frame['data'], dtype=np.int16)
                        if frame['source'] == 'microphone':
                            mic_data.append(audio_array)
                        else:  # incoming
                            incoming_data.append(audio_array)
                    
                    # Average microphone data
                    if mic_data:
                        mic_mixed = np.mean(mic_data, axis=0).astype(np.int16)
                    else:
                        mic_mixed = np.zeros(self.CHUNK_SIZE * self.CHANNELS, dtype=np.int16)
                    
                    # Average incoming data
                    if incoming_data:
                        incoming_mixed = np.mean(incoming_data, axis=0).astype(np.int16)
                    else:
                        incoming_mixed = np.zeros(self.CHUNK_SIZE * self.CHANNELS, dtype=np.int16)
                    
                    # Mix both streams (simple addition with clipping prevention)
                    mixed = (mic_mixed.astype(np.int32) + incoming_mixed.astype(np.int32)) // 2
                    mixed = np.clip(mixed, -32768, 32767).astype(np.int16)
                    
                    mixed_chunks.append(mixed.tobytes())
                else:
                    # Add silence for gaps
                    silence = np.zeros(self.CHUNK_SIZE * self.CHANNELS, dtype=np.int16)
                    mixed_chunks.append(silence.tobytes())
                
                current_window_start = window_end
            
            return b''.join(mixed_chunks)
            
        except Exception as e:
            logger.error(f"❌ Failed to mix audio streams: {e}")
            # Fallback: just concatenate microphone audio
            mic_frames = [f['data'] for f in self.call_recording_frames if f['source'] == 'microphone']
            return b''.join(mic_frames)