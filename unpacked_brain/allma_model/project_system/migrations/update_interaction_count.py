import sqlite3
import os
import json
from typing import Dict, List

def backup_data(conn: sqlite3.Connection) -> Dict[str, List[Dict]]:
    """
    Backup existing data from the database
    """
    data = {'projects': [], 'project_interactions': []}
    
    # Backup projects
    cursor = conn.execute("SELECT * FROM projects")
    columns = [description[0] for description in cursor.description]
    for row in cursor.fetchall():
        project = dict(zip(columns, row))
        if project.get('metadata'):
            project['metadata'] = json.loads(project['metadata'])
        data['projects'].append(project)
    
    # Backup project_interactions
    cursor = conn.execute("SELECT * FROM project_interactions")
    columns = [description[0] for description in cursor.description]
    for row in cursor.fetchall():
        interaction = dict(zip(columns, row))
        if interaction.get('metadata'):
            interaction['metadata'] = json.loads(interaction['metadata'])
        data['project_interactions'].append(interaction)
    
    return data

def restore_data(conn: sqlite3.Connection, data: Dict[str, List[Dict]]):
    """
    Restore data to the database
    """
    # Restore projects
    for project in data['projects']:
        metadata = json.dumps(project['metadata']) if project.get('metadata') else None
        conn.execute("""
            INSERT INTO projects (id, user_id, name, description, metadata, status,
                                created_at, updated_at, last_updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            project['id'], project['user_id'], project['name'], project['description'],
            metadata, project.get('status', 'active'), project['created_at'],
            project['updated_at'], project['last_updated_at']
        ))
    
    # Restore project_interactions
    for interaction in data['project_interactions']:
        metadata = json.dumps(interaction['metadata']) if interaction.get('metadata') else None
        conn.execute("""
            INSERT INTO project_interactions (id, project_id, interaction_id,
                                           interaction_type, metadata, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            interaction['id'], interaction['project_id'], interaction['interaction_id'],
            interaction['interaction_type'], metadata, interaction['created_at']
        ))

def migrate_interaction_count(db_path: str):
    """
    Aggiorna la tabella projects aggiungendo e inizializzando il campo interaction_count
    """
    with sqlite3.connect(db_path) as conn:
        # Backup existing data
        data = backup_data(conn)
        
        # Drop existing tables
        conn.execute("DROP TABLE IF EXISTS project_interactions")
        conn.execute("DROP TABLE IF EXISTS projects")
        
        # Create tables with new schema
        conn.execute("""
            CREATE TABLE projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL UNIQUE,
                description TEXT,
                metadata TEXT,
                status TEXT DEFAULT 'active',
                interaction_count INTEGER DEFAULT 0,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.execute("""
            CREATE TABLE project_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                interaction_id INTEGER NOT NULL,
                interaction_type TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )
        """)
        
        # Restore data
        restore_data(conn, data)
        
        # Update interaction counts
        conn.execute("""
            UPDATE projects
            SET interaction_count = (
                SELECT COUNT(*)
                FROM project_interactions
                WHERE project_interactions.project_id = projects.id
            )
        """)
        
        print("Database migrated successfully with interaction_count column")

if __name__ == "__main__":
    # Percorso del database relativo alla directory del progetto
    db_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
                          "project_data.db")
    
    migrate_interaction_count(db_path)
    print("Database migrated successfully with interaction_count column")
