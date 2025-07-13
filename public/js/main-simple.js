// Fixed main.js with controlled authentication
console.log('🎯 Fixed main.js loaded');

class EmmaPhone2 {
    constructor() {
        console.log('📱 EmmaPhone2 constructor');
        this.currentUser = null;
        this.authChecked = false;
        this.groups = [];
        this.contacts = [];
        this.socket = null;
        this.livekitClient = null;
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

        // Contact management button
        const manageContactsBtn = document.getElementById('manage-contacts-btn');
        if (manageContactsBtn) {
            manageContactsBtn.addEventListener('click', () => this.showContactManagementModal());
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

        // Contact Management Modal
        const contactModal = document.getElementById('contact-management-modal');
        const contactClose = document.getElementById('contact-management-close');

        if (contactClose) contactClose.addEventListener('click', () => this.hideContactManagementModal());
        if (contactModal) {
            contactModal.addEventListener('click', (e) => {
                if (e.target === contactModal) this.hideContactManagementModal();
            });
        }

        // User search input
        const userSearchInput = document.getElementById('user-search');
        if (userSearchInput) {
            let searchTimeout;
            userSearchInput.addEventListener('input', (e) => {
                clearTimeout(searchTimeout);
                searchTimeout = setTimeout(() => this.handleUserSearch(e.target.value), 300);
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
                // Load friend groups and contacts after successful authentication
                this.loadGroups();
                this.loadContacts();
                this.initializeSocket();
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

    // Contact Management Methods
    async loadContacts() {
        try {
            const response = await fetch('/api/contacts');
            if (response.ok) {
                this.contacts = await response.json();
                console.log('Loaded contacts:', this.contacts);
                this.renderContacts();
            } else {
                this.contacts = [];
                this.renderContacts();
            }
        } catch (error) {
            console.error('Error loading contacts:', error);
            this.contacts = [];
            this.renderContacts();
        }
    }

    renderContacts() {
        // Render speed dial buttons with real contacts
        for (let i = 1; i <= 4; i++) {
            const dialBtn = document.getElementById(`dial-${i}`);
            if (!dialBtn) continue;

            // Find contact with this speed dial position
            const contact = this.contacts.find(c => c.speed_dial_position === i);
            
            // Clone the button to remove all event listeners
            const newDialBtn = dialBtn.cloneNode(true);
            dialBtn.parentNode.replaceChild(newDialBtn, dialBtn);
            
            if (contact) {
                const nameEl = newDialBtn.querySelector('.contact-name');
                const numberEl = newDialBtn.querySelector('.contact-number');
                
                if (nameEl) nameEl.textContent = contact.display_name;
                if (numberEl) numberEl.textContent = contact.username;
                
                // Store contact data for calling
                newDialBtn.dataset.contactUserId = contact.contact_user_id;
                newDialBtn.dataset.contactName = contact.display_name;
                newDialBtn.dataset.contactUsername = contact.username;
                
                // Enable button and add click handler
                newDialBtn.disabled = false;
                newDialBtn.addEventListener('click', () => this.initiateCall(contact));
            } else {
                // No contact for this position
                const nameEl = newDialBtn.querySelector('.contact-name');
                const numberEl = newDialBtn.querySelector('.contact-number');
                
                if (nameEl) nameEl.textContent = `Empty Slot ${i}`;
                if (numberEl) numberEl.textContent = 'No Contact';
                
                // Clear stored data and disable button
                delete newDialBtn.dataset.contactUserId;
                delete newDialBtn.dataset.contactName;
                delete newDialBtn.dataset.contactUsername;
                newDialBtn.disabled = true;
            }
        }
    }

    // Socket.IO initialization
    initializeSocket() {
        if (this.socket) return; // Already initialized
        
        console.log('🔌 Initializing Socket.IO');
        this.socket = io();
        
        this.socket.on('connect', () => {
            console.log('✅ Socket.IO connected');
            // Register this user for call signaling
            this.socket.emit('register-user', { userId: this.currentUser.id });
        });
        
        this.socket.on('user-registered', (data) => {
            console.log('📋 User registered for calls:', data);
        });
        
        this.socket.on('incoming-call', (callData) => {
            console.log('📞 Incoming call:', callData);
            this.showIncomingCallModal(callData);
        });
        
        this.socket.on('call-rejected', (data) => {
            console.log('❌ Call rejected by:', data.by);
            this.updateStatus('Call rejected');
        });
        
        this.socket.on('disconnect', () => {
            console.log('❌ Socket.IO disconnected');
        });
    }

    // Call initiation
    async initiateCall(contact) {
        console.log('📞 Initiating call to:', contact);
        this.updateStatus(`Calling ${contact.display_name}...`);
        
        try {
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
                const result = await response.json();
                console.log('✅ Call initiated:', result);
                // Join LiveKit room as caller
                await this.joinLiveKitRoom(result.roomName, result.callerToken, result.wsUrl);
            } else {
                const error = await response.json();
                console.error('❌ Call initiation failed:', error);
                this.updateStatus(`Call failed: ${error.error}`);
            }
        } catch (error) {
            console.error('❌ Call error:', error);
            this.updateStatus('Call failed - network error');
        }
    }

    // Incoming call handling
    showIncomingCallModal(callData) {
        const modal = document.getElementById('incoming-call-modal');
        const callerName = document.getElementById('caller-name');
        const acceptBtn = document.getElementById('accept-call-btn');
        const rejectBtn = document.getElementById('reject-call-btn');
        
        if (callerName) callerName.textContent = callData.fromName;
        if (modal) modal.style.display = 'flex';
        
        // Handle accept
        if (acceptBtn) {
            acceptBtn.onclick = async () => {
                console.log('✅ Call accepted');
                modal.style.display = 'none';
                
                // Join LiveKit room as callee
                await this.joinLiveKitRoom(callData.roomName, callData.calleeToken, callData.wsUrl);
                
                // Notify caller that call was accepted
                this.socket.emit('call-response', {
                    accepted: true,
                    callData: callData
                });
            };
        }
        
        // Handle reject
        if (rejectBtn) {
            rejectBtn.onclick = () => {
                console.log('❌ Call rejected');
                modal.style.display = 'none';
                
                // Notify caller that call was rejected
                this.socket.emit('call-response', {
                    accepted: false,
                    callData: callData
                });
            };
        }
    }

    // LiveKit room joining
    async joinLiveKitRoom(roomName, token, wsUrl = 'ws://localhost:7880') {
        console.log('🎯 Joining LiveKit room:', roomName);
        this.updateStatus('Connecting to call...');
        
        try {
            // Initialize LiveKit client if not done
            if (!this.livekitClient) {
                this.livekitClient = new LiveKitClient();
            }
            
            // Connect to room
            await this.livekitClient.connect(wsUrl, token);
            console.log('✅ Connected to LiveKit room');
            this.updateStatus('In call - Connected');
            
            // Enable hangup button
            const hangupBtn = document.getElementById('hangup-btn');
            if (hangupBtn) {
                hangupBtn.disabled = false;
                hangupBtn.onclick = () => this.hangupCall();
            }
            
        } catch (error) {
            console.error('❌ Failed to join LiveKit room:', error);
            this.updateStatus('Call connection failed');
        }
    }

    // Hangup call
    hangupCall() {
        console.log('📴 Hanging up call');
        
        if (this.livekitClient) {
            this.livekitClient.disconnect();
            this.livekitClient = null;
        }
        
        // Disable hangup button
        const hangupBtn = document.getElementById('hangup-btn');
        if (hangupBtn) {
            hangupBtn.disabled = true;
            hangupBtn.onclick = null;
        }
        
        this.updateStatus('Call ended');
    }

    // Contact Management Methods
    showContactManagementModal() {
        const modal = document.getElementById('contact-management-modal');
        if (modal) {
            modal.style.display = 'flex';
            this.renderContactManagementSlots();
        }
    }

    hideContactManagementModal() {
        const modal = document.getElementById('contact-management-modal');
        if (modal) {
            modal.style.display = 'none';
        }
    }

    renderContactManagementSlots() {
        // Render current contacts in speed dial slots
        for (let position = 1; position <= 4; position++) {
            const slotContent = document.getElementById(`slot-${position}-content`);
            if (!slotContent) continue;

            const contact = this.contacts.find(c => c.speed_dial_position === position);
            
            if (contact) {
                slotContent.innerHTML = `
                    <div class="contact-item">
                        <div class="contact-info">
                            <div class="contact-avatar" style="background-color: ${contact.avatar_color}">
                                ${contact.display_name.charAt(0).toUpperCase()}
                            </div>
                            <div class="contact-details">
                                <div class="contact-name">${contact.display_name}</div>
                                <div class="contact-username">@${contact.username}</div>
                            </div>
                        </div>
                        <div class="contact-actions">
                            <button class="contact-action-btn edit-contact-btn" onclick="emmaPhone.editContact(${contact.id})">✏️</button>
                            <button class="contact-action-btn remove-contact-btn" onclick="emmaPhone.removeContact(${contact.id})">🗑️</button>
                        </div>
                    </div>
                `;
            } else {
                slotContent.innerHTML = `
                    <button class="add-contact-btn" data-position="${position}">Add Contact</button>
                `;
            }
        }

        // Add event listeners for add contact buttons
        document.querySelectorAll('.add-contact-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const position = parseInt(e.target.dataset.position);
                this.focusSearchForPosition(position);
            });
        });
    }

    focusSearchForPosition(position) {
        this.selectedPosition = position;
        const searchInput = document.getElementById('user-search');
        if (searchInput) {
            searchInput.focus();
            searchInput.placeholder = `Search users for Speed Dial ${position}...`;
        }
        
        // Update all position selects in search results
        document.querySelectorAll('.position-select').forEach(select => {
            select.value = position;
        });
    }

    async handleUserSearch(query) {
        const resultsContainer = document.getElementById('search-results');
        
        if (!query || query.length < 2) {
            resultsContainer.innerHTML = '<div class="search-placeholder">Start typing to search for users...</div>';
            return;
        }

        resultsContainer.innerHTML = '<div class="search-loading">Searching...</div>';

        try {
            const response = await fetch(`/api/users/search?q=${encodeURIComponent(query)}`);
            if (response.ok) {
                const users = await response.json();
                this.renderSearchResults(users);
            } else {
                resultsContainer.innerHTML = '<div class="search-no-results">Search failed. Please try again.</div>';
            }
        } catch (error) {
            console.error('Error searching users:', error);
            resultsContainer.innerHTML = '<div class="search-no-results">Search error. Please try again.</div>';
        }
    }

    renderSearchResults(users) {
        const resultsContainer = document.getElementById('search-results');
        
        if (users.length === 0) {
            resultsContainer.innerHTML = '<div class="search-no-results">No users found.</div>';
            return;
        }

        // Get available positions
        const occupiedPositions = this.contacts.map(c => c.speed_dial_position).filter(p => p);
        const availablePositions = [1, 2, 3, 4].filter(p => !occupiedPositions.includes(p));

        resultsContainer.innerHTML = users.map(user => {
            // Check if user is already a contact
            const isAlreadyContact = this.contacts.some(c => c.contact_user_id === user.id);
            
            return `
                <div class="search-result-item">
                    <div class="search-result-info">
                        <div class="search-result-avatar" style="background-color: ${user.avatar_color}">
                            ${user.display_name.charAt(0).toUpperCase()}
                        </div>
                        <div class="search-result-details">
                            <div class="search-result-name">${user.display_name}</div>
                            <div class="search-result-username">@${user.username}</div>
                        </div>
                    </div>
                    <div class="search-result-actions">
                        <select class="position-select" ${isAlreadyContact ? 'disabled' : ''}>
                            ${availablePositions.map(pos => 
                                `<option value="${pos}" ${pos === this.selectedPosition ? 'selected' : ''}>Slot ${pos}</option>`
                            ).join('')}
                        </select>
                        <button class="add-to-speed-dial-btn" 
                                onclick="emmaPhone.addContactToSpeedDial(${user.id}, '${user.display_name}', this)"
                                ${isAlreadyContact || availablePositions.length === 0 ? 'disabled' : ''}>
                            ${isAlreadyContact ? 'Already Added' : 'Add'}
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    }

    async addContactToSpeedDial(userId, displayName, buttonElement) {
        const positionSelect = buttonElement.parentElement.querySelector('.position-select');
        const position = parseInt(positionSelect.value);

        if (!position) {
            alert('Please select a speed dial position');
            return;
        }

        try {
            const response = await fetch('/api/contacts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    contactUserId: userId,
                    displayName: displayName,
                    speedDialPosition: position
                })
            });

            if (response.ok) {
                const result = await response.json();
                console.log('Contact added:', result);
                
                // Refresh contacts and update UI
                await this.loadContacts();
                this.renderContactManagementSlots();
                
                // Clear search
                const searchInput = document.getElementById('user-search');
                if (searchInput) {
                    searchInput.value = '';
                }
                document.getElementById('search-results').innerHTML = 
                    '<div class="search-placeholder">Start typing to search for users...</div>';
                
                this.updateStatus(`${displayName} added to speed dial ${position}`);
            } else {
                const error = await response.json();
                alert('Failed to add contact: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error adding contact:', error);
            alert('Failed to add contact. Please try again.');
        }
    }

    async removeContact(contactId) {
        const contact = this.contacts.find(c => c.id === contactId);
        if (!contact) return;

        if (!confirm(`Remove ${contact.display_name} from speed dial?`)) {
            return;
        }

        try {
            const response = await fetch(`/api/contacts/${contactId}`, {
                method: 'DELETE'
            });

            if (response.ok) {
                console.log('Contact removed');
                
                // Refresh contacts and update UI
                await this.loadContacts();
                this.renderContactManagementSlots();
                
                this.updateStatus(`${contact.display_name} removed from speed dial`);
            } else {
                const error = await response.json();
                alert('Failed to remove contact: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error removing contact:', error);
            alert('Failed to remove contact. Please try again.');
        }
    }

    async editContact(contactId) {
        const contact = this.contacts.find(c => c.id === contactId);
        if (!contact) return;

        const newDisplayName = prompt('Enter new display name:', contact.display_name);
        if (!newDisplayName || newDisplayName === contact.display_name) {
            return;
        }

        try {
            const response = await fetch(`/api/contacts/${contactId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    displayName: newDisplayName.trim()
                })
            });

            if (response.ok) {
                console.log('Contact updated');
                
                // Refresh contacts and update UI
                await this.loadContacts();
                this.renderContactManagementSlots();
                
                this.updateStatus(`Contact updated to ${newDisplayName}`);
            } else {
                const error = await response.json();
                alert('Failed to update contact: ' + (error.error || 'Unknown error'));
            }
        } catch (error) {
            console.error('Error updating contact:', error);
            alert('Failed to update contact. Please try again.');
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