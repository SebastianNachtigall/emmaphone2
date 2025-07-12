// Fixed main.js with controlled authentication
console.log('🎯 Fixed main.js loaded');

class EmmaPhone2 {
    constructor() {
        console.log('📱 EmmaPhone2 constructor');
        this.currentUser = null;
        this.authChecked = false;
        this.init();
    }

    async init() {
        console.log('🚀 EmmaPhone2 init');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Check if LiveKit SDK loaded
        if (typeof window.LivekitClient === 'undefined') {
            console.error('LiveKit SDK not loaded');
            this.updateStatus('Error: LiveKit SDK not loaded');
            return;
        }
        
        // Check authentication ONCE
        await this.checkAuthentication();
    }

    setupEventListeners() {
        console.log('🎧 Setting up event listeners');
        
        // Logout button
        const logoutBtn = document.getElementById('logout-btn');
        if (logoutBtn) {
            logoutBtn.addEventListener('click', () => this.handleLogout());
        }
    }

    async checkAuthentication() {
        if (this.authChecked) {
            console.log('🛑 Auth already checked, skipping');
            return;
        }
        
        this.authChecked = true;
        console.log('🔍 Checking authentication (one time only)');
        
        try {
            const response = await fetch('/api/auth/me');
            if (response.ok) {
                this.currentUser = await response.json();
                console.log('✅ Authenticated user:', this.currentUser);
                this.updateUI();
                this.updateStatus('Ready - Authentication working');
            } else {
                console.log('❌ Not authenticated');
                this.updateStatus('Not authenticated - would redirect to login');
            }
        } catch (error) {
            console.error('❌ Authentication check failed:', error);
            this.updateStatus('Authentication error');
        }
    }

    updateUI() {
        console.log('🎨 Updating UI');
        
        if (this.currentUser) {
            const userNameEl = document.getElementById('user-name');
            if (userNameEl) {
                userNameEl.textContent = this.currentUser.displayName || this.currentUser.username;
            }

            const userAvatarEl = document.getElementById('user-avatar');
            if (userAvatarEl) {
                userAvatarEl.textContent = (this.currentUser.displayName || this.currentUser.username).charAt(0).toUpperCase();
                if (this.currentUser.avatarColor) {
                    userAvatarEl.style.background = this.currentUser.avatarColor;
                }
            }
        }
    }

    updateStatus(message) {
        const statusEl = document.getElementById('status');
        if (statusEl) {
            statusEl.textContent = message;
        }
        console.log('📊 Status:', message);
    }

    async handleLogout() {
        console.log('🚪 Logging out');
        this.updateStatus('Logging out...');
        
        try {
            const response = await fetch('/api/auth/logout', { method: 'POST' });
            if (response.ok) {
                console.log('✅ Logout successful');
                window.location.href = '/login.html';
            } else {
                console.error('❌ Logout failed');
                this.updateStatus('Logout failed');
            }
        } catch (error) {
            console.error('❌ Logout error:', error);
            this.updateStatus('Logout error');
            // Fallback: redirect anyway
            setTimeout(() => {
                window.location.href = '/login.html';
            }, 2000);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 DOM loaded, creating EmmaPhone2');
    new EmmaPhone2();
});