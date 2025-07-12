class EmmaPhone2 {
    constructor() {
        this.liveKitClient = new LiveKitClient();
        this.isConnected = false;
        
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
        this.updateUI();
        
        console.log('EmmaPhone2 LiveKit Edition initialized');
        console.log('LiveKit supported:', typeof window.LivekitClient !== 'undefined');
        
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

    async handleConnection() {
        try {
            console.log('Starting LiveKit connection...');
            this.updateStatus('Connecting to LiveKit...');
            
            // Generate a demo token for testing
            // In production, this would come from your server
            const tokenResponse = await this.generateTestToken();
            
            if (!tokenResponse || !tokenResponse.token) {
                throw new Error('Failed to get valid token from server');
            }
            
            const wsUrl = tokenResponse.wsUrl || 'ws://localhost:7880';
            const token = tokenResponse.token;
            
            console.log('Using token:', token.substring(0, 50) + '...');
            console.log('Connecting to:', wsUrl);
            
            await this.liveKitClient.connect(wsUrl, token);
            
            this.isConnected = true;
            this.updateStatus('Connected - Ready to call');
            
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
        
        console.log('Generating test token for LiveKit...');
        
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
                console.log('Token response from server:', data);
                return data; // Return the full response object
            } else {
                const errorText = await response.text();
                throw new Error('Failed to get token from server: ' + response.status + ' ' + errorText);
            }
        } catch (error) {
            console.error('Server token generation failed:', error);
            console.log('Response details:', error);
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
            console.log('Speed dial pressed:', contactId, contact);
            await this.liveKitClient.makeCall(contact.number, contact.name);
        } catch (error) {
            console.error('Call failed:', error);
            this.updateStatus('Call failed: ' + error.message);
        }
    }

    handleHangup() {
        console.log('Hangup button pressed');
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
            console.log('Status:', message);
        }
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.emmaPhone = new EmmaPhone2();
});