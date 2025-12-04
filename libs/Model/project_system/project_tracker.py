"""ProjectTracker - Sistema di tracciamento progetti"""

from typing import Dict, List, Optional
from datetime import datetime
import sqlite3
import json
import os
from .project import Project

class ProjectTracker:
    def __init__(self, db_path: str):
        """
        Inizializza il sistema di tracciamento progetti
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
        # Crea la directory se non esiste e non è la directory corrente
        dirname = os.path.dirname(db_path)
        if dirname:  # Se c'è una directory padre
            os.makedirs(dirname, exist_ok=True)
        self._init_db()
        
    def _init_db(self):
        """Inizializza il database se non esiste"""
        with sqlite3.connect(self.db_path) as conn:
            # Crea le tabelle se non esistono
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
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
                CREATE TABLE IF NOT EXISTS project_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    interaction_id INTEGER NOT NULL,
                    interaction_type TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (project_id) REFERENCES projects(id)
                )
            """)
            
    def _get_db_connection(self):
        """Ottiene una connessione al database"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def create_project(
        self,
        user_id: str,
        name: str,
        description: str = "",
        metadata: Dict = None
    ) -> Optional[int]:
        """
        Crea un nuovo progetto
        
        Args:
            user_id: ID dell'utente
            name: Nome del progetto
            description: Descrizione del progetto
            metadata: Metadati aggiuntivi
            
        Returns:
            ID del progetto creato o None se il nome è già in uso
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Controlla se esiste già un progetto con lo stesso nome
                cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
                if cursor.fetchone():
                    print(f"Errore durante la creazione del progetto: UNIQUE constraint failed: projects.name")
                    return None
                
                # Inserisci il nuovo progetto
                cursor.execute("""
                    INSERT INTO projects (user_id, name, description, metadata)
                    VALUES (?, ?, ?, ?)
                """, (user_id, name, description, json.dumps(metadata or {})))
                return cursor.lastrowid
        except sqlite3.IntegrityError as e:
            print(f"Errore durante la creazione del progetto: {str(e)}")
            return None
            
    def get_project(self, project_id: int) -> Optional[Project]:
        """
        Ottiene i dettagli di un progetto dal database
        
        Args:
            project_id: ID del progetto da recuperare
            
        Returns:
            Istanza di Project o None se non trovato
        """
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT p.id, p.user_id, p.name, p.description, p.metadata, p.created_at
                FROM projects p
                WHERE p.id = ?
                """,
                (project_id,)
            )
            row = cursor.fetchone()
            
            if row is None:
                return None
                
            project_data = {
                'id': row[0],
                'user_id': row[1],
                'name': row[2],
                'description': row[3],
                'metadata': json.loads(row[4]) if row[4] else {},
                'created_at': row[5],
                'interaction_count': self.get_interaction_count(project_id)
            }
            
            return Project.from_dict(project_data)
            
    def get_user_projects(self, user_id: str) -> List[Project]:
        """
        Recupera i progetti di un utente
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Lista di progetti
        """
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT id, name, description, created_at
                FROM projects
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,)
            )
            
            projects = []
            for row in cursor.fetchall():
                project_data = {
                    "id": row[0],
                    "user_id": user_id,
                    "name": row[1],
                    "description": row[2],
                    "created_at": row[3]
                }
                projects.append(Project.from_dict(project_data))
                
            return projects
            
    def link_interaction(
        self,
        project_id: int,
        interaction_id: int,
        interaction_type: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Collega un'interazione a un progetto
        
        Args:
            project_id: ID del progetto
            interaction_id: ID dell'interazione
            interaction_type: Tipo di interazione
            metadata: Metadati aggiuntivi
            
        Returns:
            True se il collegamento è riuscito, False altrimenti
        """
        with self._get_db_connection() as conn:
            try:
                # Verifica che il progetto esista
                cursor = conn.execute(
                    "SELECT id FROM projects WHERE id = ?",
                    (project_id,)
                )
                if not cursor.fetchone():
                    print(f"Progetto {project_id} non trovato")
                    return False

                # Collega l'interazione
                conn.execute(
                    """
                    INSERT INTO project_interactions
                    (project_id, interaction_id, interaction_type, metadata)
                    VALUES (?, ?, ?, ?)
                    """,
                    (project_id, interaction_id, interaction_type, json.dumps(metadata) if metadata else None)
                )
                
                # Aggiorna timestamp e conteggio interazioni del progetto
                conn.execute(
                    """
                    UPDATE projects
                    SET last_updated_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP,
                        interaction_count = interaction_count + 1
                    WHERE id = ?
                    """,
                    (project_id,)
                )
                
                return True
            except sqlite3.Error as e:
                print(f"Errore durante il collegamento dell'interazione: {e}")
                return False

    def get_project_interactions(
        self,
        project_id: int,
        limit: Optional[int] = None
    ) -> List[Dict]:
        """
        Recupera le interazioni di un progetto
        
        Args:
            project_id: ID del progetto
            limit: Limite di interazioni da recuperare
            
        Returns:
            Lista di interazioni
        """
        query = """
            SELECT interaction_id, interaction_type, metadata, created_at
            FROM project_interactions
            WHERE project_id = ?
            ORDER BY created_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, (project_id,))
            
            interactions = []
            for row in cursor.fetchall():
                interactions.append({
                    "interaction_id": row[0],
                    "type": row[1],
                    "metadata": row[2],
                    "created_at": row[3]
                })
                
            return interactions

    def get_interaction_count(self, project_id: int) -> int:
        """
        Ottiene il numero di interazioni per un progetto
        
        Args:
            project_id: ID del progetto
            
        Returns:
            Numero di interazioni
        """
        with self._get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT interaction_count 
                FROM projects 
                WHERE id = ?
                """,
                (project_id,)
            )
            return cursor.fetchone()[0]

    def update_project_status(
        self,
        project_id: int,
        status: str,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Aggiorna lo stato di un progetto
        
        Args:
            project_id: ID del progetto
            status: Nuovo stato del progetto
            metadata: Metadati aggiuntivi
            
        Returns:
            True se l'aggiornamento è riuscito, False altrimenti
        """
        with self._get_db_connection() as conn:
            try:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE projects
                    SET status = ?,
                        metadata = ?,
                        updated_at = CURRENT_TIMESTAMP,
                        last_updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (status, json.dumps(metadata) if metadata else None, project_id)
                )
                conn.commit()
                return cursor.rowcount > 0
            except sqlite3.Error as e:
                print(f"Errore durante l'aggiornamento dello stato: {e}")
                return False

    def get_project_summary(self, project_id: int) -> Optional[Dict]:
        """
        Recupera un riepilogo del progetto
        
        Args:
            project_id: ID del progetto
            
        Returns:
            Dizionario con il riepilogo del progetto o None se non trovato
        """
        with self._get_db_connection() as conn:
            try:
                # Recupera i dati del progetto
                cursor = conn.execute(
                    """
                    SELECT p.*, COUNT(pi.id) as interaction_count
                    FROM projects p
                    LEFT JOIN project_interactions pi ON p.id = pi.project_id
                    WHERE p.id = ?
                    GROUP BY p.id
                    """,
                    (project_id,)
                )
                project = cursor.fetchone()
                
                if not project:
                    return None
                    
                # Decodifica i metadati JSON
                metadata = json.loads(project['metadata']) if project['metadata'] else {}
                
                return {
                    'id': project['id'],
                    'name': project['name'],
                    'description': project['description'],
                    'user_id': project['user_id'],
                    'status': project['status'],
                    'metadata': metadata,
                    'created_at': project['created_at'],
                    'updated_at': project['updated_at'],
                    'last_updated_at': project['last_updated_at'],
                    'interaction_count': project['interaction_count']
                }
                
            except (sqlite3.Error, json.JSONDecodeError) as e:
                print(f"Errore durante il recupero del riepilogo: {e}")
                return None

    def update_project_interaction(
        self,
        project_id: int,
        interaction_id: int,
        metadata: Dict
    ) -> bool:
        """
        Aggiorna i metadati di un'interazione esistente
        
        Args:
            project_id: ID del progetto
            interaction_id: ID dell'interazione
            metadata: Nuovi metadati
            
        Returns:
            True se l'aggiornamento è riuscito, False altrimenti
        """
        with self._get_db_connection() as conn:
            try:
                # Verifica che l'interazione esista per il progetto
                cursor = conn.execute(
                    """
                    SELECT id FROM project_interactions 
                    WHERE project_id = ? AND interaction_id = ?
                    """,
                    (project_id, interaction_id)
                )
                if not cursor.fetchone():
                    print(f"Interazione {interaction_id} non trovata per il progetto {project_id}")
                    return False

                # Aggiorna i metadati
                conn.execute(
                    """
                    UPDATE project_interactions
                    SET metadata = ?
                    WHERE project_id = ? AND interaction_id = ?
                    """,
                    (json.dumps(metadata), project_id, interaction_id)
                )
                
                # Aggiorna timestamp del progetto
                conn.execute(
                    """
                    UPDATE projects
                    SET last_updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """,
                    (project_id,)
                )
                
                return True
            except sqlite3.Error as e:
                print(f"Errore durante l'aggiornamento dell'interazione: {e}")
                return False
