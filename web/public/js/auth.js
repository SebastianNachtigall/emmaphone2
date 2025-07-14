// Guard: Only run auth.js on login page
if (window.location.pathname !== '/login.html') {
    console.log('Auth.js - Not on login page, exiting early');
} else {

class AuthManager {
    constructor() {
        this.currentTab = 'login';
        this.init();
    }

    init() {
        this.setupTabSwitching();
        this.setupForms();
        this.setupDemoButtons();
        this.setupColorPicker();
        this.checkExistingSession();
    }

    setupTabSwitching() {
        const tabButtons = document.querySelectorAll('.tab-btn');
        const forms = document.querySelectorAll('.auth-form');

        tabButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                this.switchTab(tab);
            });
        });
    }

    switchTab(tab) {
        this.currentTab = tab;
        
        // Update tab buttons
        document.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });
        
        // Update forms
        document.querySelectorAll('.auth-form').forEach(form => {
            form.classList.toggle('active', form.id === `${tab}-form`);
        });
        
        this.hideMessage();
    }

    setupForms() {
        // Login form
        const loginForm = document.getElementById('login-form-element');
        loginForm.addEventListener('submit', (e) => this.handleLogin(e));
        
        // Register form
        const registerForm = document.getElementById('register-form-element');
        registerForm.addEventListener('submit', (e) => this.handleRegister(e));
    }

    setupDemoButtons() {
        const demoButtons = document.querySelectorAll('.demo-btn');
        demoButtons.forEach(btn => {
            btn.addEventListener('click', () => {
                const username = btn.dataset.username;
                const password = btn.dataset.password;
                
                document.getElementById('login-username').value = username;
                document.getElementById('login-password').value = password;
                
                // Auto-submit login form
                this.handleLogin(new Event('submit'), true);
            });
        });
    }

    setupColorPicker() {
        const colorInput = document.getElementById('avatar-color');
        const preview = document.getElementById('avatar-preview');
        const displayNameInput = document.getElementById('register-display-name');

        const updatePreview = () => {
            const color = colorInput.value;
            const name = displayNameInput.value || 'A';
            preview.style.background = color;
            preview.textContent = name.charAt(0).toUpperCase();
        };

        colorInput.addEventListener('input', updatePreview);
        displayNameInput.addEventListener('input', updatePreview);
    }

    async handleLogin(event, isDemoLogin = false) {
        if (!isDemoLogin) {
            event.preventDefault();
        }
        
        const form = document.getElementById('login-form-element');
        const formData = new FormData(form);
        
        const loginData = {
            username: formData.get('username'),
            password: formData.get('password')
        };

        this.setLoading('login', true);
        
        try {
            const response = await fetch('/api/auth/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(loginData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage('Login successful! Redirecting...', 'success');
                
                // Store user info in session storage for the phone app
                sessionStorage.setItem('currentUser', JSON.stringify(result.user));
                
                // Redirect to phone interface
                setTimeout(() => {
                    window.location.href = '/';
                }, 1500);
            } else {
                this.showMessage(result.error || 'Login failed', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            this.showMessage('Connection error. Please try again.', 'error');
        } finally {
            this.setLoading('login', false);
        }
    }

    async handleRegister(event) {
        event.preventDefault();
        
        const form = document.getElementById('register-form-element');
        const formData = new FormData(form);
        
        const registerData = {
            username: formData.get('username'),
            displayName: formData.get('displayName'),
            password: formData.get('password'),
            pin: formData.get('pin') || null,
            avatarColor: formData.get('avatarColor')
        };

        // Basic validation
        if (registerData.username.length < 3) {
            this.showMessage('Username must be at least 3 characters', 'error');
            return;
        }

        if (registerData.password.length < 6) {
            this.showMessage('Password must be at least 6 characters', 'error');
            return;
        }

        this.setLoading('register', true);
        
        try {
            const response = await fetch('/api/auth/register', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(registerData)
            });

            const result = await response.json();

            if (response.ok) {
                this.showMessage('Account created successfully! You can now login.', 'success');
                
                // Switch to login tab and pre-fill username
                setTimeout(() => {
                    this.switchTab('login');
                    document.getElementById('login-username').value = registerData.username;
                    document.getElementById('login-username').focus();
                }, 2000);
            } else {
                this.showMessage(result.error || 'Registration failed', 'error');
            }
        } catch (error) {
            console.error('Registration error:', error);
            this.showMessage('Connection error. Please try again.', 'error');
        } finally {
            this.setLoading('register', false);
        }
    }

    setLoading(formType, isLoading) {
        const form = document.getElementById(`${formType}-form-element`);
        const button = form.querySelector('.auth-btn');
        const spinner = button.querySelector('.btn-spinner');
        const text = button.querySelector('.btn-text');
        
        button.disabled = isLoading;
        spinner.style.display = isLoading ? 'inline' : 'none';
        text.style.display = isLoading ? 'none' : 'inline';
    }

    showMessage(message, type) {
        const messageEl = document.getElementById('auth-message');
        messageEl.textContent = message;
        messageEl.className = `auth-message ${type}`;
        messageEl.style.display = 'block';
        
        // Auto-hide success messages
        if (type === 'success') {
            setTimeout(() => this.hideMessage(), 5000);
        }
    }

    hideMessage() {
        const messageEl = document.getElementById('auth-message');
        messageEl.style.display = 'none';
    }

    async checkExistingSession() {
        try {
            // Only check if we're explicitly on the login page
            console.log('Auth.js - Current pathname:', window.location.pathname);
            if (window.location.pathname !== '/login.html') {
                console.log('Auth.js - Not on login page, skipping session check');
                return;
            }
            
            console.log('Auth.js - Checking existing session');
            const response = await fetch('/api/auth/me');
            if (response.ok) {
                const user = await response.json();
                // User is already logged in, show message and let server handle redirect
                console.log('Auth.js - User already logged in:', user.username);
                this.showMessage('You are already logged in. Redirecting...', 'success');
                // Let the server handle the redirect by navigating to root
                setTimeout(() => {
                    window.location.href = '/';
                }, 1000);
            }
        } catch (error) {
            // Not logged in, stay on auth page
            console.log('No existing session - showing login form');
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new AuthManager();
});

} // End of login page guard