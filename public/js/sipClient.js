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
            console.log('Starting SIP registration...');
            console.log('Server:', server);
            console.log('Username:', username);
            console.log('URI will be:', `sip:${username}@${server}`);
            
            // Try different WebSocket configurations for LinHome.org
            const wsUrls = [
                `wss://${server}:5065`,  // Common WebRTC port
                `wss://${server}:8089`,  // Alternative WebRTC port
                `wss://${server}:443`,   // HTTPS port
                `wss://${server}:5060`,  // Standard SIP port
                `wss://${server}`,       // Default port
                `ws://${server}:5060`,   // Try non-SSL
                `ws://${server}:8080`,   // Alternative HTTP port
            ];
            
            console.log('Will try WebSocket URLs:', wsUrls);
            
            const sockets = wsUrls.map(url => {
                console.log('Creating socket for:', url);
                return new JsSIP.WebSocketInterface(url);
            });
            
            const configuration = {
                sockets: sockets,
                uri: `sip:${username}@${server}`,
                password: password,
                register: true,
                session_timers: false,
                rtcpMuxPolicy: 'require'
            };

            console.log('JsSIP Configuration:', configuration);
            this.ua = new JsSIP.UA(configuration);

            return new Promise((resolve, reject) => {
                let timeoutId = setTimeout(() => {
                    console.error('Registration timeout after 30 seconds');
                    reject(new Error('Registration timeout'));
                }, 30000);

                this.ua.on('connecting', () => {
                    console.log('JsSIP: Connecting...');
                    this.updateStatus('Connecting...');
                });

                this.ua.on('connected', () => {
                    console.log('JsSIP: Connected to WebSocket');
                    this.updateStatus('Connected');
                });

                this.ua.on('disconnected', (e) => {
                    console.log('JsSIP: Disconnected', e);
                    this.updateStatus('Disconnected');
                    this.isRegistered = false;
                    clearTimeout(timeoutId);
                    if (!this.isRegistered) {
                        reject(new Error('Connection lost before registration'));
                    }
                });

                this.ua.on('registered', (e) => {
                    console.log('JsSIP: Successfully registered', e);
                    this.updateStatus('Registered');
                    this.isRegistered = true;
                    clearTimeout(timeoutId);
                    resolve(true);
                });

                this.ua.on('unregistered', (e) => {
                    console.log('JsSIP: Unregistered', e);
                    this.updateStatus('Unregistered');
                    this.isRegistered = false;
                });

                this.ua.on('registrationFailed', (e) => {
                    console.error('JsSIP: Registration failed', e);
                    this.updateStatus('Registration Failed: ' + (e.cause || 'Unknown error'));
                    this.isRegistered = false;
                    clearTimeout(timeoutId);
                    reject(new Error('Registration failed: ' + (e.cause || e.response?.status_code || 'Unknown error')));
                });

                this.ua.on('newRTCSession', (e) => {
                    console.log('JsSIP: New RTC Session', e);
                    this.handleIncomingCall(e.session);
                });

                console.log('Starting JsSIP UA...');
                this.ua.start();
            });
        } catch (error) {
            console.error('Registration error:', error);
            this.updateStatus('Registration Error: ' + error.message);
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