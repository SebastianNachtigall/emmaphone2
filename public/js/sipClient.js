class SIPClient {
    constructor() {
        this.ua = null;
        this.currentSession = null;
        this.isRegistered = false;
        this.remoteAudio = null;
        this.localStream = null;
        this.pc = null;
        
        this.setupAudioElements();
    }

    setupAudioElements() {
        this.remoteAudio = document.createElement('audio');
        this.remoteAudio.autoplay = true;
        this.remoteAudio.controls = false;
        document.body.appendChild(this.remoteAudio);
    }

    async register(server, username, password) {
        try {
            const socket = new JsSIP.WebSocketInterface(`wss://${server}`);
            
            const configuration = {
                sockets: [socket],
                uri: `sip:${username}@${server}`,
                password: password,
                register: true,
                session_timers: false,
                rtcpMuxPolicy: 'require'
            };

            this.ua = new JsSIP.UA(configuration);

            return new Promise((resolve, reject) => {
                this.ua.on('connecting', () => {
                    this.updateStatus('Connecting...');
                });

                this.ua.on('connected', () => {
                    this.updateStatus('Connected');
                });

                this.ua.on('disconnected', () => {
                    this.updateStatus('Disconnected');
                    this.isRegistered = false;
                });

                this.ua.on('registered', () => {
                    this.updateStatus('Registered');
                    this.isRegistered = true;
                    resolve(true);
                });

                this.ua.on('unregistered', () => {
                    this.updateStatus('Unregistered');
                    this.isRegistered = false;
                });

                this.ua.on('registrationFailed', (e) => {
                    this.updateStatus('Registration Failed');
                    this.isRegistered = false;
                    reject(new Error('Registration failed: ' + e.cause));
                });

                this.ua.on('newRTCSession', (e) => {
                    this.handleIncomingCall(e.session);
                });

                this.ua.start();
            });
        } catch (error) {
            console.error('Registration error:', error);
            this.updateStatus('Registration Error');
            throw error;
        }
    }

    async makeCall(number) {
        if (!this.isRegistered) {
            throw new Error('Not registered');
        }

        if (this.currentSession) {
            throw new Error('Call already in progress');
        }

        try {
            await this.getUserMedia();
            
            const eventHandlers = {
                'progress': () => {
                    this.updateStatus('Calling...');
                    this.updateCallControls(true);
                },
                'confirmed': () => {
                    this.updateStatus('In Call');
                },
                'ended': () => {
                    this.handleCallEnded();
                },
                'failed': (e) => {
                    this.updateStatus('Call Failed');
                    this.handleCallEnded();
                    console.error('Call failed:', e);
                }
            };

            const options = {
                eventHandlers: eventHandlers,
                mediaConstraints: {
                    audio: true,
                    video: false
                },
                rtcOfferConstraints: {
                    offerToReceiveAudio: true,
                    offerToReceiveVideo: false
                }
            };

            this.currentSession = this.ua.call(`sip:${number}@${this.ua.configuration.uri.host}`, options);
            
            this.currentSession.on('peerconnection', (e) => {
                this.setupPeerConnection(e.peerconnection);
            });

        } catch (error) {
            console.error('Call error:', error);
            this.updateStatus('Call Error');
            throw error;
        }
    }

    async getUserMedia() {
        try {
            this.localStream = await navigator.mediaDevices.getUserMedia({
                audio: true,
                video: false
            });
        } catch (error) {
            console.error('Error getting user media:', error);
            throw new Error('Microphone access denied');
        }
    }

    setupPeerConnection(pc) {
        this.pc = pc;
        
        pc.ontrack = (event) => {
            console.log('Remote stream received');
            this.remoteAudio.srcObject = event.streams[0];
        };

        if (this.localStream) {
            this.localStream.getTracks().forEach(track => {
                pc.addTrack(track, this.localStream);
            });
        }
    }

    handleIncomingCall(session) {
        console.log('Incoming call from:', session.remote_identity.uri);
        
        const accept = confirm(`Incoming call from ${session.remote_identity.uri}. Accept?`);
        
        if (accept) {
            this.currentSession = session;
            this.setupSessionEventHandlers(session);
            
            session.answer({
                mediaConstraints: {
                    audio: true,
                    video: false
                }
            });
            
            this.updateStatus('Incoming Call');
            this.updateCallControls(true);
        } else {
            session.terminate();
        }
    }

    setupSessionEventHandlers(session) {
        session.on('confirmed', () => {
            this.updateStatus('In Call');
        });

        session.on('ended', () => {
            this.handleCallEnded();
        });

        session.on('failed', () => {
            this.updateStatus('Call Failed');
            this.handleCallEnded();
        });

        session.on('peerconnection', (e) => {
            this.setupPeerConnection(e.peerconnection);
        });
    }

    hangup() {
        if (this.currentSession) {
            this.currentSession.terminate();
        }
    }

    handleCallEnded() {
        console.log('Call ended');
        this.updateStatus('Ready');
        this.updateCallControls(false);
        this.currentSession = null;
        
        if (this.remoteAudio) {
            this.remoteAudio.srcObject = null;
        }
        
        if (this.localStream) {
            this.localStream.getTracks().forEach(track => track.stop());
            this.localStream = null;
        }
        
        this.pc = null;
    }

    updateStatus(status) {
        const statusElement = document.getElementById('status');
        statusElement.textContent = status;
        
        statusElement.className = 'status';
        
        if (status === 'Registered' || status === 'Connected') {
            statusElement.classList.add('connected');
        } else if (status === 'Calling...') {
            statusElement.classList.add('calling');
        } else if (status === 'In Call') {
            statusElement.classList.add('in-call');
        }
    }

    updateCallControls(inCall) {
        const hangupBtn = document.getElementById('hangup-btn');
        const speedDialBtns = document.querySelectorAll('.speed-dial-btn');
        
        hangupBtn.disabled = !inCall;
        
        speedDialBtns.forEach(btn => {
            btn.disabled = inCall;
        });
    }

    setVolume(volume) {
        if (this.remoteAudio) {
            this.remoteAudio.volume = volume;
        }
    }
}