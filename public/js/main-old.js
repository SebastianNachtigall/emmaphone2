class EmmaPhone2 {
    constructor() {
        this.liveKitClient = new LiveKitClient();
        this.isConnected = false;
        this.socket = null;
        this.currentUser = null;
        this.contacts = [];
        this.incomingCallData = null;
        
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.setupIncomingCallModal();
        
        console.log('EmmaPhone2 initialized - LiveKit supported:', typeof window.LivekitClient !== 'undefined');
        
        // Check if LiveKit SDK loaded
        if (typeof window.LivekitClient === 'undefined') {
            console.error('LiveKit SDK not loaded');
            this.updateStatus('Error: LiveKit SDK not loaded');
            return;
        }
        
        // Check if user is authenticated
        await this.checkAuthentication();
    }

    setupEventListeners() {
        // Connect button
        const connectBtn = document.getElementById('connect-btn');
        if (connectBtn) {
            connectBtn.addEventListener('click', () => this.handleConnection());
        }
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }

        // Speed dial buttons - will be set up after loading contacts
        this.setupSpeedDialButtons();

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
            // User ID is now managed through authentication
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
                    to: this.currentUser.id
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
                to: this.currentUser.id
            }
        });
    }

    async handleConnection() {
        if (this.isConnected) {
            // Disconnect
            await this.disconnect();
            return;
        }
        
        try {
            this.updateStatus('Connecting to LiveKit...');
            
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
            
            // Register user for call signaling with their user ID
            this.socket.emit('register-user', { userId: this.currentUser.id });
            
            this.updateConnectionButton();
            
        } catch (error) {
            console.error('Connection failed:', error);
            this.updateStatus('Connection failed: ' + error.message);
        }
    }

    async generateTestToken() {
        try {
            const response = await fetch('/api/livekit-token', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    roomName: 'lobby-room',
                    participantName: this.currentUser.username
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data;
            } else {
                const errorText = await response.text();
                throw new Error('Failed to get token from server: ' + response.status + ' ' + errorText);
            }
        } catch (error) {
            console.error('Server token generation failed:', error);
            throw new Error('Token generation failed: ' + error.message);
        }
    }

    async handleSpeedDial(contactId) {
        if (!this.isConnected) {
            this.updateStatus('Please connect first');
            return;
        }

        const contact = this.contacts.find(c => c.speed_dial_position === contactId);
        if (!contact) {
            console.error('Contact not found for speed dial:', contactId);
            return;
        }

        try {
            this.updateStatus(`Calling ${contact.display_name}...`);
            
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
                    toUser: contact.contact_user_id,
                    contactName: contact.display_name
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
                
                this.updateStatus(`Calling ${contact.display_name}... waiting for answer`);
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
        this.updateUserInfo();
        this.updateSpeedDialContacts();
        this.updateConnectionButton();
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