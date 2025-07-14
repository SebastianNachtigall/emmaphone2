-- EmmaPhone2 Database Schema
-- Supports multi-tenant friend groups and user management

-- Users table - individual kid accounts
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    display_name VARCHAR(100) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    pin VARCHAR(10), -- Simple PIN for kids
    avatar_color VARCHAR(7) DEFAULT '#667eea', -- Hex color for UI
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    last_login DATETIME,
    is_active BOOLEAN DEFAULT 1
);

-- Friend groups table - families or friend circles
CREATE TABLE friend_groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    invite_code VARCHAR(20) UNIQUE, -- For easy joining
    admin_user_id INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT 1,
    FOREIGN KEY (admin_user_id) REFERENCES users(id)
);

-- Many-to-many: Users can be in multiple groups
CREATE TABLE user_groups (
    user_id INTEGER,
    group_id INTEGER,
    joined_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    is_approved BOOLEAN DEFAULT 1,
    PRIMARY KEY (user_id, group_id),
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES friend_groups(id) ON DELETE CASCADE
);

-- Contact relationships - who can call whom
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    contact_user_id INTEGER,
    display_name VARCHAR(100), -- Custom name for this contact
    speed_dial_position INTEGER, -- 1-4 for quick access
    is_favorite BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (contact_user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE(user_id, contact_user_id),
    UNIQUE(user_id, speed_dial_position)
);

-- Call logs for tracking usage
CREATE TABLE call_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    caller_id INTEGER,
    callee_id INTEGER,
    room_name VARCHAR(255),
    started_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    ended_at DATETIME,
    duration_seconds INTEGER,
    status VARCHAR(20) DEFAULT 'initiated', -- initiated, connected, ended, rejected
    FOREIGN KEY (caller_id) REFERENCES users(id),
    FOREIGN KEY (callee_id) REFERENCES users(id)
);

-- Create indexes for performance
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_active ON users(is_active);
CREATE INDEX idx_user_groups_user ON user_groups(user_id);
CREATE INDEX idx_user_groups_group ON user_groups(group_id);
CREATE INDEX idx_contacts_user ON contacts(user_id);
CREATE INDEX idx_contacts_speed_dial ON contacts(user_id, speed_dial_position);
CREATE INDEX idx_call_logs_participants ON call_logs(caller_id, callee_id);
CREATE INDEX idx_call_logs_started ON call_logs(started_at);

-- Demo data will be created by the application code after users are properly initialized
-- This ensures proper password hashing and avoids foreign key constraint issues