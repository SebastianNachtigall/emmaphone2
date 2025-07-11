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
            console.log('=== NEW VERSION LOADED ===');
            console.log('Starting SIP registration...');
            console.log('Server:', server);
            console.log('Username:', username);
            console.log('URI will be:', `sip:${username}@${server}`);
            
            // Local Asterisk server configuration
            if (server === 'localhost') {
                console.log('=== LOCAL ASTERISK SERVER ===');
                console.log('Connecting to local Asterisk server...');
                
                // Use localhost WebSocket connection
                const wsUrls = [
                    `ws://${server}:8088/ws`,        // Local Asterisk WebSocket
                ];
                
                console.log('Local Asterisk WebSocket URLs:', wsUrls);
                
                const sockets = wsUrls.map(url => {
                    console.log('Creating local Asterisk socket for:', url);
                    return new JsSIP.WebSocketInterface(url);
                });
                
                const configuration = {
                    sockets: sockets,
                    uri: `sip:${username}@${server}`,
                    password: password,
                    register: true,
                    session_timers: false,
                    rtcpMuxPolicy: 'require',
                    pcConfig: {
                        iceServers: [
                            { urls: 'stun:stun.l.google.com:19302' }
                        ]
                    }
                };
                
                console.log('Local Asterisk Configuration:', configuration);
                this.ua = new JsSIP.UA(configuration);
                
                return new Promise((resolve, reject) => {
                    let timeoutId = setTimeout(() => {
                        console.error('Registration timeout after 30 seconds');
                        reject(new Error('Registration timeout'));
                    }, 30000);

                    this.ua.on('connecting', () => {
                        console.log('Local Asterisk: Connecting...');
                        this.updateStatus('Connecting...');
                    });

                    this.ua.on('connected', () => {
                        console.log('Local Asterisk: Connected to WebSocket');
                        this.updateStatus('Connected');
                    });

                    this.ua.on('disconnected', (e) => {
                        console.log('Local Asterisk: Disconnected', e);
                        this.updateStatus('Disconnected');
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        if (!this.isRegistered) {
                            reject(new Error('Connection lost before registration'));
                        }
                    });

                    this.ua.on('registered', (e) => {
                        console.log('Local Asterisk: Successfully registered', e);
                        this.updateStatus('Registered');
                        this.isRegistered = true;
                        clearTimeout(timeoutId);
                        resolve(true);
                    });

                    this.ua.on('unregistered', (e) => {
                        console.log('Local Asterisk: Unregistered', e);
                        this.updateStatus('Unregistered');
                        this.isRegistered = false;
                    });

                    this.ua.on('registrationFailed', (e) => {
                        console.error('Local Asterisk: Registration failed', e);
                        this.updateStatus('Registration Failed: ' + (e.cause || 'Unknown error'));
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        reject(new Error('Registration failed: ' + (e.cause || e.response?.status_code || 'Unknown error')));
                    });

                    this.ua.on('newRTCSession', (e) => {
                        console.log('Local Asterisk: New RTC Session', e);
                        if (e.originator === 'remote') {
                            console.log('Incoming call detected');
                            this.handleIncomingCall(e.session);
                        } else {
                            console.log('Outgoing call session created');
                        }
                    });

                    console.log('Starting Local Asterisk JsSIP UA...');
                    this.ua.start();
                });
            } else if (server === 'sip2sip.info') {
                console.log('=== SIP2SIP.INFO SERVER ===');
                console.log('Connecting to SIP2SIP.info server...');
                
                // Use proxy.sipthor.net as per SIP2SIP.info official configuration
                const proxyServer = 'proxy.sipthor.net';
                const wsUrls = [
                    `wss://${proxyServer}`,          // Direct WebSocket connection  
                    `wss://${proxyServer}/ws`,       // WebSocket path
                    `wss://${proxyServer}:443`,      // HTTPS port
                    `wss://${proxyServer}:5061`,     // TLS SIP port
                    `wss://${proxyServer}:8080`,     // Alternative WebRTC port
                ];
                
                console.log('SIP2SIP.info WebSocket URLs:', wsUrls);
                
                const sockets = wsUrls.map(url => {
                    console.log('Creating SIP2SIP.info socket for:', url);
                    return new JsSIP.WebSocketInterface(url);
                });
                
                const configuration = {
                    sockets: sockets,
                    uri: `sip:${username}@${server}`,
                    password: password,
                    register: true,
                    session_timers: false,
                    rtcpMuxPolicy: 'require',
                    pcConfig: {
                        iceServers: [
                            { urls: 'stun:stun.l.google.com:19302' }
                        ]
                    }
                };
                
                console.log('SIP2SIP.info Configuration:', configuration);
                this.ua = new JsSIP.UA(configuration);
                
                return new Promise((resolve, reject) => {
                    let timeoutId = setTimeout(() => {
                        console.error('Registration timeout after 30 seconds');
                        reject(new Error('Registration timeout'));
                    }, 30000);

                    this.ua.on('connecting', () => {
                        console.log('SIP2SIP.info: Connecting...');
                        this.updateStatus('Connecting...');
                    });

                    this.ua.on('connected', () => {
                        console.log('SIP2SIP.info: Connected to WebSocket');
                        this.updateStatus('Connected');
                    });

                    this.ua.on('disconnected', (e) => {
                        console.log('SIP2SIP.info: Disconnected', e);
                        this.updateStatus('Disconnected');
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        if (!this.isRegistered) {
                            reject(new Error('Connection lost before registration'));
                        }
                    });

                    this.ua.on('registered', (e) => {
                        console.log('SIP2SIP.info: Successfully registered', e);
                        this.updateStatus('Registered');
                        this.isRegistered = true;
                        clearTimeout(timeoutId);
                        resolve(true);
                    });

                    this.ua.on('unregistered', (e) => {
                        console.log('SIP2SIP.info: Unregistered', e);
                        this.updateStatus('Unregistered');
                        this.isRegistered = false;
                    });

                    this.ua.on('registrationFailed', (e) => {
                        console.error('SIP2SIP.info: Registration failed', e);
                        this.updateStatus('Registration Failed: ' + (e.cause || 'Unknown error'));
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        reject(new Error('Registration failed: ' + (e.cause || e.response?.status_code || 'Unknown error')));
                    });

                    this.ua.on('newRTCSession', (e) => {
                        console.log('SIP2SIP.info: New RTC Session', e);
                        if (e.originator === 'remote') {
                            console.log('Incoming call detected');
                            this.handleIncomingCall(e.session);
                        } else {
                            console.log('Outgoing call session created');
                        }
                    });

                    console.log('Starting SIP2SIP.info JsSIP UA...');
                    this.ua.start();
                });
            } else if (server === 'sip.linhome.org') {
                console.log('=== LINHOME.ORG SERVER ===');
                console.log('Connecting to LinHome.org server...');
                
                // Configure WebRTC SIP WebSocket URLs
                const wsUrls = [
                    `wss://${server}:443/ws`,   // Standard HTTPS with WebSocket path
                    `wss://${server}/ws`,       // WebSocket path on default port
                    `wss://${server}:5060/ws`,  // SIP port with WebSocket
                    `wss://${server}:8080/ws`,  // Alternative HTTP port with WebSocket
                ];
                
                console.log('WebRTC SIP WebSocket URLs:', wsUrls);
                
                const sockets = wsUrls.map(url => {
                    console.log('Creating WebRTC socket for:', url);
                    return new JsSIP.WebSocketInterface(url);
                });
                
                const configuration = {
                    sockets: sockets,
                    uri: `sip:${username}@${server}`,
                    password: password,
                    register: true,
                    session_timers: false,
                    rtcpMuxPolicy: 'require',
                    pcConfig: {
                        iceServers: [
                            { urls: 'stun:stun.l.google.com:19302' }
                        ]
                    }
                };
                
                console.log('WebRTC SIP Configuration:', configuration);
                this.ua = new JsSIP.UA(configuration);
                
                // Use the Asterisk configuration and skip the general WebSocket setup
                return new Promise((resolve, reject) => {
                    let timeoutId = setTimeout(() => {
                        console.error('Registration timeout after 30 seconds');
                        reject(new Error('Registration timeout'));
                    }, 30000);

                    this.ua.on('connecting', () => {
                        console.log('WebRTC SIP: Connecting...');
                        this.updateStatus('Connecting...');
                    });

                    this.ua.on('connected', () => {
                        console.log('WebRTC SIP: Connected to WebSocket');
                        this.updateStatus('Connected');
                    });

                    this.ua.on('disconnected', (e) => {
                        console.log('WebRTC SIP: Disconnected', e);
                        this.updateStatus('Disconnected');
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        if (!this.isRegistered) {
                            reject(new Error('Connection lost before registration'));
                        }
                    });

                    this.ua.on('registered', (e) => {
                        console.log('WebRTC SIP: Successfully registered', e);
                        this.updateStatus('Registered');
                        this.isRegistered = true;
                        clearTimeout(timeoutId);
                        resolve(true);
                    });

                    this.ua.on('unregistered', (e) => {
                        console.log('WebRTC SIP: Unregistered', e);
                        this.updateStatus('Unregistered');
                        this.isRegistered = false;
                    });

                    this.ua.on('registrationFailed', (e) => {
                        console.error('WebRTC SIP: Registration failed', e);
                        this.updateStatus('Registration Failed: ' + (e.cause || 'Unknown error'));
                        this.isRegistered = false;
                        clearTimeout(timeoutId);
                        reject(new Error('Registration failed: ' + (e.cause || e.response?.status_code || 'Unknown error')));
                    });

                    this.ua.on('newRTCSession', (e) => {
                        console.log('WebRTC SIP: New RTC Session', e);
                        // Only handle truly incoming calls, not outgoing calls we initiated
                        if (e.originator === 'remote') {
                            console.log('Incoming call detected');
                            this.handleIncomingCall(e.session);
                        } else {
                            console.log('Outgoing call session created');
                        }
                    });

                    console.log('Starting WebRTC SIP JsSIP UA...');
                    this.ua.start();
                });
            } else if (server === 'localhost' || server === 'demo') {
                console.log('=== DEMO MODE ACTIVATED ===');
                console.log('Simulating successful SIP registration...');
                
                this.updateStatus('Connecting...');
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                this.updateStatus('Connected');
                await new Promise(resolve => setTimeout(resolve, 1000));
                
                this.updateStatus('Registered');
                this.isRegistered = true;
                
                console.log('Demo registration successful!');
                return true;
            }
            
            // WebRTC-specific WebSocket configuration
            const wsUrls = [
                `wss://${server}:8989/ws`,  // Janus WebRTC Gateway
                `wss://${server}:8188`,     // Janus WebSocket port
                `wss://${server}`,          // Default HTTPS port
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
            
            console.log('Full SIP URI:', `sip:${username}@${server}`);

            console.log('JsSIP Configuration with multiple sockets:', configuration);
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
                    audio: {
                        echoCancellation: true,
                        noiseSuppression: true,
                        autoGainControl: true
                    },
                    video: false
                },
                rtcOfferConstraints: {
                    offerToReceiveAudio: true,
                    offerToReceiveVideo: false
                },
                rtcAnswerConstraints: {
                    offerToReceiveAudio: true,
                    offerToReceiveVideo: false
                },
                rtcConfiguration: {
                    iceServers: [
                        { urls: 'stun:stun.l.google.com:19302' }
                    ]
                }
            };

            this.currentSession = this.ua.call(`sip:${number}@${this.ua.configuration.uri.host}`, options);
            
            this.currentSession.on('peerconnection', (e) => {
                this.setupPeerConnection(e.peerconnection);
            });

        } catch (error) {
            console.error('Call error:', error);
            this.updateStatus('Call Error');
            this.handleCallEnded(); // Clean up any partial session state
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

    async handleIncomingCall(session) {
        console.log('Incoming call from:', session.remote_identity.uri);
        
        // Set up event handlers first, before any user interaction
        this.currentSession = session;
        this.setupSessionEventHandlers(session);
        
        // Update UI to show incoming call
        this.updateStatus('Incoming Call');
        this.updateCallControls(true);
        
        try {
            // Get user media before answering
            await this.getUserMedia();
            
            const accept = confirm(`Incoming call from ${session.remote_identity.uri.user || 'Unknown'}. Accept?`);
            
            if (accept) {
                console.log('User accepted the call, answering...');
                
                session.answer({
                    mediaConstraints: {
                        audio: {
                            echoCancellation: true,
                            noiseSuppression: true,
                            autoGainControl: true
                        },
                        video: false
                    },
                    rtcAnswerConstraints: {
                        offerToReceiveAudio: true,
                        offerToReceiveVideo: false
                    }
                });
                
                this.updateStatus('Answering Call');
            } else {
                console.log('User rejected the call');
                try {
                    session.terminate();
                } catch (e) {
                    console.log('Session already terminated:', e);
                }
                this.handleCallEnded();
            }
        } catch (error) {
            console.error('Error handling incoming call:', error);
            try {
                if (session && session.status !== 8) { // 8 = terminated
                    session.terminate();
                }
            } catch (e) {
                console.log('Session already terminated during error handling:', e);
            }
            this.handleCallEnded();
        }
    }

    setupSessionEventHandlers(session) {
        session.on('confirmed', () => {
            console.log('Call confirmed');
            this.updateStatus('In Call');
        });

        session.on('ended', () => {
            console.log('Call ended');
            this.handleCallEnded();
        });

        session.on('failed', (e) => {
            console.log('Call failed:', e);
            this.updateStatus('Call Failed');
            this.handleCallEnded();
        });

        session.on('peerconnection', (e) => {
            console.log('Peer connection established');
            this.setupPeerConnection(e.peerconnection);
        });
        
        session.on('accepted', () => {
            console.log('Call accepted');
            this.updateStatus('Call Connected');
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