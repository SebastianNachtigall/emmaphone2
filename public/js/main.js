class EmmaPhone {
    constructor() {
        this.sipClient = new SIPClient();
        this.speedDialContacts = {
            1: { name: 'Friend 1', number: '+1234567890' },
            2: { name: 'Friend 2', number: '+1234567891' },
            3: { name: 'Friend 3', number: '+1234567892' },
            4: { name: 'Friend 4', number: '+1234567893' }
        };
        
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        document.getElementById('register-btn').addEventListener('click', () => {
            this.handleRegistration();
        });

        document.getElementById('hangup-btn').addEventListener('click', () => {
            this.sipClient.hangup();
        });

        document.getElementById('volume-slider').addEventListener('input', (e) => {
            this.sipClient.setVolume(e.target.value);
        });

        document.querySelectorAll('.speed-dial-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const contactId = e.currentTarget.dataset.contact;
                this.handleSpeedDial(contactId);
            });
        });

        this.loadStoredConfig();
    }

    async handleRegistration() {
        const server = document.getElementById('sip-server').value;
        const username = document.getElementById('sip-user').value;
        const password = document.getElementById('sip-password').value;

        if (!server || !username || !password) {
            alert('Please fill in all SIP configuration fields');
            return;
        }

        try {
            await this.sipClient.register(server, username, password);
            this.storeConfig(server, username, password);
            alert('Successfully registered!');
        } catch (error) {
            console.error('Registration failed:', error);
            alert('Registration failed: ' + error.message);
        }
    }

    async handleSpeedDial(contactId) {
        const contact = this.speedDialContacts[contactId];
        
        if (!contact) {
            console.error('Contact not found:', contactId);
            return;
        }

        if (!this.sipClient.isRegistered) {
            alert('Please register first');
            return;
        }

        try {
            await this.sipClient.makeCall(contact.number);
        } catch (error) {
            console.error('Call failed:', error);
            alert('Call failed: ' + error.message);
        }
    }

    storeConfig(server, username, password) {
        localStorage.setItem('sip-config', JSON.stringify({
            server,
            username,
            password
        }));
    }

    loadStoredConfig() {
        const stored = localStorage.getItem('sip-config');
        if (stored) {
            try {
                const config = JSON.parse(stored);
                document.getElementById('sip-server').value = config.server || '';
                document.getElementById('sip-user').value = config.username || '';
                document.getElementById('sip-password').value = config.password || '';
            } catch (error) {
                console.error('Error loading stored config:', error);
            }
        }
    }

    updateSpeedDialContact(contactId, name, number) {
        this.speedDialContacts[contactId] = { name, number };
        
        const btn = document.getElementById(`dial-${contactId}`);
        if (btn) {
            btn.querySelector('.contact-name').textContent = name;
            btn.querySelector('.contact-number').textContent = number;
        }
        
        this.storeSpeedDialContacts();
    }

    storeSpeedDialContacts() {
        localStorage.setItem('speed-dial-contacts', JSON.stringify(this.speedDialContacts));
    }

    loadStoredSpeedDialContacts() {
        const stored = localStorage.getItem('speed-dial-contacts');
        if (stored) {
            try {
                const contacts = JSON.parse(stored);
                this.speedDialContacts = { ...this.speedDialContacts, ...contacts };
                
                Object.entries(this.speedDialContacts).forEach(([id, contact]) => {
                    this.updateSpeedDialContact(id, contact.name, contact.number);
                });
            } catch (error) {
                console.error('Error loading stored contacts:', error);
            }
        }
    }
}

document.addEventListener('DOMContentLoaded', () => {
    window.emmaPhone = new EmmaPhone();
    
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
        console.log('WebRTC supported');
    } else {
        console.error('WebRTC not supported');
        alert('Your browser does not support WebRTC. Please use a modern browser like Chrome, Firefox, or Safari.');
    }
});