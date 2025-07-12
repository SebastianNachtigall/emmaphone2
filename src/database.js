const Database = require('better-sqlite3');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcrypt');

class DatabaseManager {
    constructor(dbPath = process.env.DB_PATH || './data/db/emmaphone.db') {
        // Ensure directory exists
        const dir = path.dirname(dbPath);
        if (!fs.existsSync(dir)) {
            fs.mkdirSync(dir, { recursive: true });
        }

        this.db = new Database(dbPath);
        this.db.pragma('journal_mode = WAL');
        this.init().then(() => {
            this.createDemoUsers();
        });
    }

    async init() {
        // Read and execute schema
        const schemaPath = path.join(__dirname, '../database/schema.sql');
        if (fs.existsSync(schemaPath)) {
            const schema = fs.readFileSync(schemaPath, 'utf8');
            
            // Split by semicolon and execute each statement
            const statements = schema.split(';').filter(stmt => stmt.trim());
            
            this.db.transaction(() => {
                statements.forEach(stmt => {
                    if (stmt.trim()) {
                        try {
                            this.db.exec(stmt);
                        } catch (error) {
                            // Ignore errors for INSERT statements (might already exist)
                            if (!stmt.trim().toUpperCase().startsWith('INSERT')) {
                                console.error('Database schema error:', error.message);
                            }
                        }
                    }
                });
            })();
            
            console.log('Database initialized successfully');
        }
    }

    async createDemoUsers() {
        // Check if demo users already exist
        const existingUser = this.db.prepare('SELECT id FROM users WHERE username = ?').get('emma');
        if (existingUser) {
            console.log('Demo users already exist');
            return;
        }

        console.log('Creating demo users...');
        
        const demoUsers = [
            { username: 'emma', displayName: 'Emma', password: 'demo123', pin: '1234', avatarColor: '#ff6b6b' },
            { username: 'noah', displayName: 'Noah', password: 'demo123', pin: '1234', avatarColor: '#4ecdc4' },
            { username: 'olivia', displayName: 'Olivia', password: 'demo123', pin: '1234', avatarColor: '#45b7d1' },
            { username: 'liam', displayName: 'Liam', password: 'demo123', pin: '1234', avatarColor: '#96ceb4' }
        ];

        try {
            for (const userData of demoUsers) {
                await this.createUser(
                    userData.username,
                    userData.displayName,
                    userData.password,
                    userData.pin,
                    userData.avatarColor
                );
            }
            
            // Create contacts between demo users
            const contacts = [
                { userId: 1, contactUserId: 2, displayName: 'Noah', speedDial: 1 },
                { userId: 1, contactUserId: 3, displayName: 'Olivia', speedDial: 2 },
                { userId: 1, contactUserId: 4, displayName: 'Liam', speedDial: 3 },
                { userId: 2, contactUserId: 1, displayName: 'Emma', speedDial: 1 },
                { userId: 2, contactUserId: 3, displayName: 'Olivia', speedDial: 2 },
                { userId: 2, contactUserId: 4, displayName: 'Liam', speedDial: 3 }
            ];
            
            for (const contact of contacts) {
                try {
                    this.addContact(contact.userId, contact.contactUserId, contact.displayName, contact.speedDial);
                } catch (error) {
                    // Ignore duplicate contact errors
                }
            }
            
            console.log('Demo users and contacts created successfully');
        } catch (error) {
            console.error('Error creating demo users:', error);
        }
    }

    // User management
    async createUser(username, displayName, password, pin, avatarColor = '#667eea') {
        const passwordHash = await bcrypt.hash(password, 10);
        const stmt = this.db.prepare(`
            INSERT INTO users (username, display_name, password_hash, pin, avatar_color)
            VALUES (?, ?, ?, ?, ?)
        `);
        
        try {
            const result = stmt.run(username, displayName, passwordHash, pin, avatarColor);
            return { id: result.lastInsertRowid, username, displayName };
        } catch (error) {
            if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
                throw new Error('Username already exists');
            }
            throw error;
        }
    }

    async validateUser(username, password) {
        const stmt = this.db.prepare(`
            SELECT id, username, display_name, password_hash, avatar_color, last_login
            FROM users 
            WHERE username = ? AND is_active = 1
        `);
        
        const user = stmt.get(username);
        if (!user) return null;
        
        const isValid = await bcrypt.compare(password, user.password_hash);
        if (!isValid) return null;
        
        // Update last login
        this.db.prepare('UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = ?')
            .run(user.id);
        
        return {
            id: user.id,
            username: user.username,
            displayName: user.display_name,
            avatarColor: user.avatar_color
        };
    }

    getUserById(userId) {
        const stmt = this.db.prepare(`
            SELECT id, username, display_name, avatar_color, created_at, last_login
            FROM users 
            WHERE id = ? AND is_active = 1
        `);
        return stmt.get(userId);
    }

    // Contact management
    getUserContacts(userId) {
        const stmt = this.db.prepare(`
            SELECT c.id, c.contact_user_id, c.display_name, c.speed_dial_position, c.is_favorite,
                   u.username, u.avatar_color
            FROM contacts c
            JOIN users u ON c.contact_user_id = u.id
            WHERE c.user_id = ? AND u.is_active = 1
            ORDER BY c.speed_dial_position ASC, c.display_name ASC
        `);
        return stmt.all(userId);
    }

    addContact(userId, contactUserId, displayName, speedDialPosition = null) {
        const stmt = this.db.prepare(`
            INSERT INTO contacts (user_id, contact_user_id, display_name, speed_dial_position)
            VALUES (?, ?, ?, ?)
        `);
        
        try {
            const result = stmt.run(userId, contactUserId, displayName, speedDialPosition);
            return result.lastInsertRowid;
        } catch (error) {
            if (error.code === 'SQLITE_CONSTRAINT_UNIQUE') {
                throw new Error('Contact already exists or speed dial position taken');
            }
            throw error;
        }
    }

    // Friend group management
    createFriendGroup(name, description, adminUserId) {
        const inviteCode = Math.random().toString(36).substr(2, 8).toUpperCase();
        
        const createGroup = this.db.prepare(`
            INSERT INTO friend_groups (name, description, invite_code, admin_user_id)
            VALUES (?, ?, ?, ?)
        `);
        
        const addUserToGroup = this.db.prepare(`
            INSERT INTO user_groups (user_id, group_id)
            VALUES (?, ?)
        `);
        
        const transaction = this.db.transaction((name, description, adminUserId, inviteCode) => {
            const result = createGroup.run(name, description, inviteCode, adminUserId);
            addUserToGroup.run(adminUserId, result.lastInsertRowid);
            return { id: result.lastInsertRowid, inviteCode };
        });
        
        return transaction(name, description, adminUserId, inviteCode);
    }

    getUserGroups(userId) {
        const stmt = this.db.prepare(`
            SELECT fg.id, fg.name, fg.description, fg.invite_code, fg.admin_user_id,
                   ug.joined_at, (fg.admin_user_id = ?) as is_admin
            FROM friend_groups fg
            JOIN user_groups ug ON fg.id = ug.group_id
            WHERE ug.user_id = ? AND fg.is_active = 1 AND ug.is_approved = 1
        `);
        return stmt.all(userId, userId);
    }

    // Call logging
    logCall(callerId, calleeId, roomName, status = 'initiated') {
        const stmt = this.db.prepare(`
            INSERT INTO call_logs (caller_id, callee_id, room_name, status)
            VALUES (?, ?, ?, ?)
        `);
        return stmt.run(callerId, calleeId, roomName, status).lastInsertRowid;
    }

    updateCallStatus(callLogId, status, endedAt = null) {
        const stmt = this.db.prepare(`
            UPDATE call_logs 
            SET status = ?, ended_at = COALESCE(?, ended_at),
                duration_seconds = CASE 
                    WHEN ? IS NOT NULL THEN 
                        (julianday(?) - julianday(started_at)) * 86400
                    ELSE duration_seconds 
                END
            WHERE id = ?
        `);
        return stmt.run(status, endedAt, endedAt, endedAt, callLogId);
    }

    close() {
        this.db.close();
    }
}

module.exports = DatabaseManager;