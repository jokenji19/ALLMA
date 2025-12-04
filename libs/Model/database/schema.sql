-- Schema del database ALLMA

-- Tabella delle preferenze utente
CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    preference_type TEXT NOT NULL,
    preference_value TEXT NOT NULL,
    metadata TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(user_id, preference_type)
);

-- Tabella della storia delle preferenze
CREATE TABLE IF NOT EXISTS preference_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    interaction_id INTEGER,
    preference_type TEXT NOT NULL,
    observed_value TEXT NOT NULL,
    metadata TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (interaction_id) REFERENCES interactions(id)
);

-- Tabella delle interazioni
CREATE TABLE IF NOT EXISTS interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    context TEXT,
    metadata TEXT,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella dei progetti
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT,
    user_id TEXT NOT NULL,
    status TEXT DEFAULT 'active',
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabella delle interazioni dei progetti
CREATE TABLE IF NOT EXISTS project_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    interaction_id INTEGER NOT NULL,
    interaction_type TEXT NOT NULL,
    metadata TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (project_id) REFERENCES projects(id),
    FOREIGN KEY (interaction_id) REFERENCES interactions(id)
);

-- Tabella dei pattern temporali
CREATE TABLE IF NOT EXISTS temporal_patterns (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    pattern_type TEXT NOT NULL,
    pattern_data TEXT NOT NULL,
    metadata TEXT,
    confidence REAL DEFAULT 1.0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indici per migliorare le performance
CREATE INDEX IF NOT EXISTS idx_user_preferences_user ON user_preferences(user_id);
CREATE INDEX IF NOT EXISTS idx_interactions_user ON interactions(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_user ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_project_interactions_project ON project_interactions(project_id);
CREATE INDEX IF NOT EXISTS idx_project_interactions_interaction ON project_interactions(interaction_id);
CREATE INDEX IF NOT EXISTS idx_temporal_patterns_user ON temporal_patterns(user_id);
CREATE INDEX IF NOT EXISTS idx_preference_history_user ON preference_history(user_id);
CREATE INDEX IF NOT EXISTS idx_preference_history_interaction ON preference_history(interaction_id);

-- Trigger per aggiornare updated_at e last_updated
CREATE TRIGGER IF NOT EXISTS update_user_preferences_timestamp 
AFTER UPDATE ON user_preferences
BEGIN
    UPDATE user_preferences SET updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_projects_timestamp
AFTER UPDATE ON projects
BEGIN
    UPDATE projects SET updated_at = CURRENT_TIMESTAMP,
                       last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_interactions_timestamp
AFTER UPDATE ON interactions
BEGIN
    UPDATE interactions SET last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_project_interactions_timestamp
AFTER UPDATE ON project_interactions
BEGIN
    UPDATE project_interactions SET last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_temporal_patterns_timestamp
AFTER UPDATE ON temporal_patterns
BEGIN
    UPDATE temporal_patterns SET updated_at = CURRENT_TIMESTAMP,
                               last_updated = CURRENT_TIMESTAMP
    WHERE id = NEW.id;
END;
