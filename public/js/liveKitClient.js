class LiveKitClient {
    constructor() {
        this.room = null;
        this.isConnected = false;
        this.localAudioTrack = null;
        this.remoteAudio = null;
        this.currentContact = null;
        
        this.setupAudioElements();
    }

    setupAudioElements() {
        this.remoteAudio = document.createElement('audio');
        this.remoteAudio.autoplay = true;
        this.remoteAudio.controls = false;
        document.body.appendChild(this.remoteAudio);
    }

    async connect(wsUrl, token) {
        try {
            console.log('Connecting to LiveKit server:', wsUrl);
            
            // Import LiveKit from global scope (loaded via CDN)
            const { Room, RoomEvent, Track } = window.LivekitClient;
            
            this.room = new Room({
                adaptiveStream: true,
                dynacast: true,
                audioCaptureDefaults: {
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            this.setupRoomEventListeners();

            await this.room.connect(wsUrl, token);
            console.log('Connected to LiveKit room');
            
            this.isConnected = true;
            this.updateStatus('Connected to LiveKit');
            
            return true;
        } catch (error) {
            console.error('LiveKit connection failed:', error);
            this.updateStatus('Connection Failed: ' + error.message);
            throw error;
        }
    }

    setupRoomEventListeners() {
        const { RoomEvent, Track } = window.LivekitClient;
        
        this.room
            .on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
                
                if (track.kind === Track.Kind.Audio) {
                    const audioElement = track.attach();
                    audioElement.id = `audio-${participant.identity}`;
                    document.body.appendChild(audioElement);
                    this.updateStatus('In Call with ' + participant.identity);
                }
            })
            .on(RoomEvent.TrackUnsubscribed, (track, publication, participant) => {
                
                if (track.kind === Track.Kind.Audio) {
                    const audioElement = document.getElementById(`audio-${participant.identity}`);
                    if (audioElement) {
                        audioElement.remove();
                    }
                }
            })
            .on(RoomEvent.ParticipantConnected, (participant) => {
                this.updateStatus('Call connected');
            })
            .on(RoomEvent.ParticipantDisconnected, (participant) => {
                this.updateStatus('Call ended');
                this.handleCallEnded();
            })
            .on(RoomEvent.Disconnected, (reason) => {
                console.log('Disconnected from room:', reason);
                this.handleCallEnded();
            })
            .on(RoomEvent.AudioPlaybackStatusChanged, () => {
                if (!this.room.canPlaybackAudio) {
                    this.showAudioStartButton();
                }
            });
    }

    async enableAudio() {
        try {
            const { createLocalTracks, Track } = window.LivekitClient;
            
            const tracks = await createLocalTracks({
                audio: true,
                video: false
            });

            const audioTrack = tracks.find(track => track.kind === Track.Kind.Audio);
            if (audioTrack) {
                await this.room.localParticipant.publishTrack(audioTrack);
                this.localAudioTrack = audioTrack;
                return true;
            }
        } catch (error) {
            console.error('Failed to enable audio:', error);
            throw new Error('Microphone access denied');
        }
    }

    async makeCall(contactNumber, contactName) {
        if (!this.isConnected) {
            throw new Error('Not connected to LiveKit');
        }

        try {
            this.currentContact = { number: contactNumber, name: contactName };
            
            // Enable audio first
            await this.enableAudio();
            
            // In a real implementation, this would trigger SIP participant creation
            // For now, we'll simulate by updating status
            this.updateStatus(`Calling ${contactName}...`);
            this.updateCallControls(true);
            
            // Simulate call connection after 2 seconds
            setTimeout(() => {
                this.updateStatus(`Connected to ${contactName}`);
            }, 2000);
            
            return true;
        } catch (error) {
            console.error('Call failed:', error);
            this.updateStatus('Call Failed');
            this.handleCallEnded();
            throw error;
        }
    }

    hangup() {
        if (this.room) {
            this.room.disconnect();
        }
    }

    handleCallEnded() {
        this.updateStatus('Ready');
        this.updateCallControls(false);
        this.currentContact = null;
        
        // Clean up local tracks
        if (this.localAudioTrack) {
            this.localAudioTrack.stop();
            this.localAudioTrack = null;
        }
        
        // Clean up remote audio elements
        const remoteAudioElements = document.querySelectorAll('audio[id^="audio-"]');
        remoteAudioElements.forEach(element => element.remove());
    }

    showAudioStartButton() {
        const startAudioBtn = document.createElement('button');
        startAudioBtn.textContent = 'Start Audio';
        startAudioBtn.className = 'control-btn audio-start-btn';
        startAudioBtn.onclick = async () => {
            try {
                await this.room.startAudio();
                startAudioBtn.remove();
            } catch (error) {
                console.error('Failed to start audio:', error);
            }
        };
        
        const callControls = document.querySelector('.call-controls');
        if (callControls) {
            callControls.appendChild(startAudioBtn);
        }
    }

    toggleMute() {
        if (this.localAudioTrack) {
            const currentlyMuted = this.localAudioTrack.isMuted;
            this.localAudioTrack.setMuted(!currentlyMuted);
            
            const muteBtn = document.querySelector('.mute-btn');
            if (muteBtn) {
                muteBtn.textContent = currentlyMuted ? 'Mute' : 'Unmute';
            }
            
        }
    }

    updateStatus(status) {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = status;
            
            statusElement.className = 'status';
            
            if (status.includes('Connected') || status.includes('Ready')) {
                statusElement.classList.add('connected');
            } else if (status.includes('Calling')) {
                statusElement.classList.add('calling');
            } else if (status.includes('In Call')) {
                statusElement.classList.add('in-call');
            }
        }
    }

    updateCallControls(inCall) {
        const hangupBtn = document.getElementById('hangup-btn');
        const speedDialBtns = document.querySelectorAll('.speed-dial-btn');
        
        if (hangupBtn) {
            hangupBtn.disabled = !inCall;
        }
        
        speedDialBtns.forEach(btn => {
            btn.disabled = inCall;
        });
    }

    setVolume(volume) {
        const remoteAudioElements = document.querySelectorAll('audio[id^="audio-"]');
        remoteAudioElements.forEach(element => {
            element.volume = volume;
        });
    }
}