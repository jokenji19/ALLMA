import sqlite3
import os

def init_db(db_path: str):
    """
    Inizializza il database SQLite.
    
    Args:
        db_path: Percorso del database
    """
    conn = sqlite3.connect(db_path)
    try:
        # Crea tabella interazioni
        conn.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                content TEXT NOT NULL,
                context TEXT,
                emotion TEXT,
                topics TEXT,
                metadata TEXT,
                UNIQUE(user_id, timestamp)
            )
        """)
        
        # Crea tabella progetti
        conn.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                metadata TEXT,
                interaction_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """)
        
        # Crea tabella pattern temporali
        conn.execute("""
            CREATE TABLE IF NOT EXISTS temporal_patterns (
                user_id TEXT NOT NULL,
                pattern_type TEXT NOT NULL,
                pattern_data TEXT NOT NULL,
                last_updated DATETIME NOT NULL,
                PRIMARY KEY (user_id, pattern_type)
            )
        """)
        
        conn.commit()
    finally:
        conn.close()
