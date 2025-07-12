// Fixed main.js with controlled authentication
console.log('🎯 Fixed main.js loaded');

class EmmaPhone2 {
    constructor() {
        console.log('📱 EmmaPhone2 constructor');
        this.currentUser = null;
        this.authChecked = false;
        this.groups = [];
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

        // Friend group buttons
        const createGroupBtn = document.getElementById('create-group-btn');
        if (createGroupBtn) {
            createGroupBtn.addEventListener('click', () => this.showCreateGroupModal());
        }

        const joinGroupBtn = document.getElementById('join-group-btn');
        if (joinGroupBtn) {
            joinGroupBtn.addEventListener('click', () => this.showJoinGroupModal());
        }

        // Modal close buttons and overlays
        this.setupModalListeners();
    }

    setupModalListeners() {
        // Create Group Modal
        const createModal = document.getElementById('create-group-modal');
        const createClose = document.getElementById('create-group-close');
        const createCancel = document.getElementById('create-group-cancel');
        const createForm = document.getElementById('create-group-form');

        if (createClose) createClose.addEventListener('click', () => this.hideCreateGroupModal());
        if (createCancel) createCancel.addEventListener('click', () => this.hideCreateGroupModal());
        if (createModal) {
            createModal.addEventListener('click', (e) => {
                if (e.target === createModal) this.hideCreateGroupModal();
            });
        }
        if (createForm) {
            createForm.addEventListener('submit', (e) => this.handleCreateGroup(e));
        }

        // Join Group Modal
        const joinModal = document.getElementById('join-group-modal');
        const joinClose = document.getElementById('join-group-close');
        const joinCancel = document.getElementById('join-group-cancel');
        const joinForm = document.getElementById('join-group-form');

        if (joinClose) joinClose.addEventListener('click', () => this.hideJoinGroupModal());
        if (joinCancel) joinCancel.addEventListener('click', () => this.hideJoinGroupModal());
        if (joinModal) {
            joinModal.addEventListener('click', (e) => {
                if (e.target === joinModal) this.hideJoinGroupModal();
            });
        }
        if (joinForm) {
            joinForm.addEventListener('submit', (e) => this.handleJoinGroup(e));
        }

        // Group Details Modal
        const detailsModal = document.getElementById('group-details-modal');
        const detailsClose = document.getElementById('group-details-close');

        if (detailsClose) detailsClose.addEventListener('click', () => this.hideGroupDetailsModal());
        if (detailsModal) {
            detailsModal.addEventListener('click', (e) => {
                if (e.target === detailsModal) this.hideGroupDetailsModal();
            });
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
                // Load friend groups after successful authentication
                this.loadGroups();
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

    // Friend Group Management Methods
    async loadGroups() {
        try {
            const response = await fetch('/api/groups');
            if (response.ok) {
                this.groups = await response.json();
                console.log('Loaded groups:', this.groups);
                this.renderGroups();
            } else {
                this.groups = [];
                this.renderGroups();
            }
        } catch (error) {
            console.error('Error loading groups:', error);
            this.groups = [];
            this.renderGroups();
        }
    }

    renderGroups() {
        const groupsList = document.getElementById('groups-list');
        if (!groupsList) return;

        if (this.groups.length === 0) {
            groupsList.innerHTML = `
                <div class="empty-state">
                    <h4>No Groups Yet</h4>
                    <p>Create a group or join one with an invite code to get started!</p>
                </div>
            `;
            return;
        }

        groupsList.innerHTML = this.groups.map(group => `
            <div class="group-card" onclick="emmaPhone.showGroupDetails(${group.id})">
                <div class="group-info">
                    <h4 class="group-name">${group.name}</h4>
                    ${group.description ? `<p class="group-description">${group.description}</p>` : ''}
                </div>
                <div class="group-meta">
                    <span class="group-invite-code">Code: ${group.invite_code}</span>
                    ${group.is_admin ? '<span class="group-admin-badge">Admin</span>' : ''}
                </div>
            </div>
        `).join('');
    }

    showCreateGroupModal() {
        const modal = document.getElementById('create-group-modal');
        if (modal) {
            modal.style.display = 'flex';
            // Clear form
            document.getElementById('group-name').value = '';
            document.getElementById('group-description').value = '';
        }
    }

    hideCreateGroupModal() {
        const modal = document.getElementById('create-group-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async handleCreateGroup(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const groupData = {
            name: formData.get('name'),
            description: formData.get('description')
        };

        try {
            const response = await fetch('/api/groups', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(groupData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Group created:', result);
                this.hideCreateGroupModal();
                await this.loadGroups(); // Refresh groups list
                this.updateStatus(`Group "${result.group.name}" created successfully!`);
            } else {
                const error = await response.json();
                alert('Failed to create group: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error creating group:', error);
            alert('Failed to create group. Please try again.');
        }
    }

    showJoinGroupModal() {
        const modal = document.getElementById('join-group-modal');
        if (modal) {
            modal.style.display = 'flex';
            // Clear form
            document.getElementById('invite-code').value = '';
        }
    }

    hideJoinGroupModal() {
        const modal = document.getElementById('join-group-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    async handleJoinGroup(event) {
        event.preventDefault();
        
        const form = event.target;
        const formData = new FormData(form);
        const joinData = {
            inviteCode: formData.get('inviteCode').trim().toUpperCase()
        };

        try {
            const response = await fetch('/api/groups/join', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(joinData)
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Joined group:', result);
                this.hideJoinGroupModal();
                await this.loadGroups(); // Refresh groups list
                this.updateStatus(`Joined group "${result.group.name}" successfully!`);
            } else {
                const error = await response.json();
                alert('Failed to join group: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error joining group:', error);
            alert('Failed to join group. Please try again.');
        }
    }

    async showGroupDetails(groupId) {
        try {
            // Find the group in our current list
            const group = this.groups.find(g => g.id === groupId);
            if (!group) return;

            // Fetch group members
            const response = await fetch(`/api/groups/${groupId}/members`);
            if (!response.ok) {
                throw new Error('Failed to fetch group members');
            }

            const members = await response.json();
            
            // Show modal with group details
            const modal = document.getElementById('group-details-modal');
            const title = document.getElementById('group-details-title');
            const content = document.getElementById('group-details-content');

            title.textContent = group.name;
            content.innerHTML = `
                <div class="group-details">
                    <div class="group-details-header">
                        <div class="group-details-info">
                            <h4>${group.name}</h4>
                            ${group.description ? `<p>${group.description}</p>` : ''}
                        </div>
                    </div>
                    
                    <div class="group-invite-info">
                        <h5>Invite Code</h5>
                        <p>Share this code with others to invite them to the group:</p>
                        <div class="invite-code-display">
                            <span class="invite-code">${group.invite_code}</span>
                            <button class="copy-btn" onclick="navigator.clipboard.writeText('${group.invite_code}').then(() => alert('Invite code copied!'))">Copy</button>
                        </div>
                    </div>

                    <div class="members-section">
                        <h5>Members (${members.length})</h5>
                        <div class="members-list">
                            ${members.map(member => `
                                <div class="member-card">
                                    <div class="member-avatar" style="background-color: ${member.avatar_color}">
                                        ${member.display_name.charAt(0).toUpperCase()}
                                    </div>
                                    <div class="member-info">
                                        <div class="member-name">${member.display_name}</div>
                                        <div class="member-role">
                                            ${member.is_admin ? '<span class="admin-badge">Admin</span>' : 'Member'}
                                        </div>
                                    </div>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                </div>
            `;

            modal.style.display = 'flex';
        } catch (error) {
            console.error('Error showing group details:', error);
            alert('Failed to load group details');
        }
    }

    hideGroupDetailsModal() {
        const modal = document.getElementById('group-details-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('🌟 DOM loaded, creating EmmaPhone2');
    window.emmaPhone = new EmmaPhone2();
});