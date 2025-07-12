class EmmaPhone2 {
    constructor() {
        this.liveKitClient = new LiveKitClient();
        this.isConnected = false;
        this.socket = null;
        this.currentUserId = null;
        this.incomingCallData = null;
        
        // Speed dial contacts for testing
        this.speedDialContacts = {
            1: { name: 'User 1001', number: '1001' },
            2: { name: 'User 1002', number: '1002' },
            3: { name: 'User 1003', number: '1003' },
            4: { name: 'User 1004', number: '1004' }
        };
        
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.setupIncomingCallModal();
        this.setupSocket();
        this.updateUI();
        
        console.log('EmmaPhone2 initialized - LiveKit supported:', typeof window.LivekitClient !== 'undefined');
        
        // Check if LiveKit SDK loaded
        if (typeof window.LivekitClient === 'undefined') {
            console.error('LiveKit SDK not loaded');
            this.updateStatus('Error: LiveKit SDK not loaded');
            return;
        }
        
        this.updateStatus('Ready - Click Connect to start');
    }

    setupEventListeners() {
        // Register/Connect button
        const registerBtn = document.getElementById('register-btn');
        if (registerBtn) {
            registerBtn.addEventListener('click', () => this.handleConnection());
        }

        // Speed dial buttons
        for (let i = 1; i <= 4; i++) {
            const btn = document.getElementById(`dial-${i}`);
            if (btn) {
                btn.addEventListener('click', () => this.handleSpeedDial(i));
            }
        }

        // Hangup button
        const hangupBtn = document.getElementById('hangup-btn');
        if (hangupBtn) {
            hangupBtn.addEventListener('click', () => this.handleHangup());
        }

        // Volume control
        const volumeSlider = document.getElementById('volume-slider');
        if (volumeSlider) {
            volumeSlider.addEventListener('input', (e) => {
                this.liveKitClient.setVolume(e.target.value);
            });
        }
    }

    setupSocket() {
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('Connected to server');
        });

        this.socket.on('user-registered', (data) => {
            console.log('User registered:', data);
            this.currentUserId = data.userId;
        });

        this.socket.on('incoming-call', (callData) => {
            console.log('Incoming call:', callData);
            this.showIncomingCall(callData);
        });

        this.socket.on('call-rejected', (data) => {
            console.log('Call rejected by:', data.by);
            this.updateStatus('Call rejected');
        });
    }

    setupIncomingCallModal() {
        const acceptBtn = document.getElementById('accept-call-btn');
        const rejectBtn = document.getElementById('reject-call-btn');

        acceptBtn.addEventListener('click', () => this.acceptCall());
        rejectBtn.addEventListener('click', () => this.rejectCall());
    }

    showIncomingCall(callData) {
        this.incomingCallData = callData;
        
        const modal = document.getElementById('incoming-call-modal');
        const callerName = document.getElementById('caller-name');
        
        callerName.textContent = callData.fromName || callData.from;
        modal.style.display = 'flex';
        
        this.updateStatus('Incoming call...');
    }

    hideIncomingCall() {
        const modal = document.getElementById('incoming-call-modal');
        modal.style.display = 'none';
        this.incomingCallData = null;
    }

    async acceptCall() {
        if (!this.incomingCallData) {
            console.error('No incoming call data available');
            return;
        }
        
        const callData = this.incomingCallData; // Store reference before hiding modal
        this.hideIncomingCall();
        this.updateStatus('Accepting call...');
        
        try {
            // Disconnect from current room if connected
            if (this.liveKitClient.room && this.liveKitClient.isConnected) {
                await this.liveKitClient.disconnect();
            }
            
            // Connect to the call room using the provided token
            const wsUrl = 'ws://localhost:7880';
            await this.liveKitClient.connect(wsUrl, callData.calleeToken);
            
            // Explicitly enable audio and update call controls
            await this.liveKitClient.enableAudio();
            this.liveKitClient.updateCallControls(true);
            
            // Notify server that call was accepted
            this.socket.emit('call-response', {
                accepted: true,
                callData: {
                    from: callData.from,
                    to: this.currentUserId
                }
            });
            
            this.updateStatus(`In call with ${callData.fromName}`);
        } catch (error) {
            console.error('Failed to accept call:', error);
            this.updateStatus('Failed to accept call');
        }
    }

    rejectCall() {
        if (!this.incomingCallData) return;
        
        this.hideIncomingCall();
        this.updateStatus('Call rejected');
        
        // Notify server that call was rejected
        this.socket.emit('call-response', {
            accepted: false,
            callData: {
                from: this.incomingCallData.from,
                to: this.currentUserId
            }
        });
    }

    async handleConnection() {
        try {
            this.updateStatus('Connecting to LiveKit...');
            
            // Generate a demo token for testing
            // In production, this would come from your server
            const tokenResponse = await this.generateTestToken();
            
            if (!tokenResponse || !tokenResponse.token) {
                throw new Error('Failed to get valid token from server');
            }
            
            const wsUrl = tokenResponse.wsUrl || 'ws://localhost:7880';
            const token = tokenResponse.token;
            
            console.log('Connecting to LiveKit:', wsUrl);
            
            await this.liveKitClient.connect(wsUrl, token);
            
            this.isConnected = true;
            this.updateStatus('Connected - Ready to call');
            
            // Register user for call signaling
            const username = document.getElementById('sip-user').value || 'user-' + Date.now();
            this.socket.emit('register-user', { userId: username });
            
            // Update button text
            const registerBtn = document.getElementById('register-btn');
            if (registerBtn) {
                registerBtn.textContent = 'Disconnect';
            }
            
        } catch (error) {
            console.error('Connection failed:', error);
            this.updateStatus('Connection failed: ' + error.message);
        }
    }

    async generateTestToken() {
        // For testing purposes, we'll create a basic token
        // In production, your server would generate proper JWT tokens
        
        
        // This is a simplified approach for local testing
        // You would typically call your server API here
        try {
            const response = await fetch('/api/livekit-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    roomName: 'test-room',
                    participantName: 'user-' + Date.now()
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data; // Return the full response object
            } else {
                const errorText = await response.text();
                throw new Error('Failed to get token from server: ' + response.status + ' ' + errorText);
            }
        } catch (error) {
            console.error('Server token generation failed:', error);
            // For demo purposes, we'll return a placeholder
            // Real LiveKit tokens are JWT tokens with proper signing
            throw new Error('Token generation failed: ' + error.message);
        }
    }

    async handleSpeedDial(contactId) {
        if (!this.isConnected) {
            this.updateStatus('Please connect first');
            return;
        }

        const contact = this.speedDialContacts[contactId];
        if (!contact) {
            console.error('Contact not found:', contactId);
            return;
        }

        try {
            this.updateStatus(`Calling ${contact.name}...`);
            
            // Disconnect from current room if connected
            if (this.liveKitClient.room && this.liveKitClient.isConnected) {
                await this.liveKitClient.disconnect();
            }
            
            // Initiate call through server
            const response = await fetch('/api/initiate-call', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    fromUser: this.currentUserId,
                    toUser: contact.number,
                    contactName: contact.name
                })
            });

            if (response.ok) {
                const callData = await response.json();
                
                // Connect to the call room using caller token
                const wsUrl = 'ws://localhost:7880';
                await this.liveKitClient.connect(wsUrl, callData.callerToken);
                
                // Explicitly enable audio and update call controls
                await this.liveKitClient.enableAudio();
                this.liveKitClient.updateCallControls(true);
                
                this.updateStatus(`Calling ${contact.name}... waiting for answer`);
            } else {
                const error = await response.json();
                throw new Error(error.error || 'Call failed');
            }
        } catch (error) {
            console.error('Call failed:', error);
            this.updateStatus('Call failed: ' + error.message);
        }
    }

    handleHangup() {
        this.liveKitClient.hangup();
    }

    updateUI() {
        // Update speed dial button labels
        for (let i = 1; i <= 4; i++) {
            const btn = document.getElementById(`dial-${i}`);
            const contact = this.speedDialContacts[i];
            
            if (btn && contact) {
                const nameSpan = btn.querySelector('.contact-name');
                const numberSpan = btn.querySelector('.contact-number');
                
                if (nameSpan) nameSpan.textContent = contact.name;
                if (numberSpan) numberSpan.textContent = contact.number;
            }
        }
    }

    updateStatus(message) {
        const statusElement = document.getElementById('status');
        if (statusElement) {
            statusElement.textContent = message;
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.emmaPhone = new EmmaPhone2();
});