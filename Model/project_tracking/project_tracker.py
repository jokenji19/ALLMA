from datetime import datetime
from typing import Dict, List, Optional
import sqlite3
import json
import threading
from enum import Enum

class ProjectStatus(Enum):
    ACTIVE = "active"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    ARCHIVED = "archived"

class ProjectTracker:
    def __init__(self, db_path: str = "memory.db"):
        """
        Inizializza il sistema di tracking dei progetti
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
        self.lock = threading.Lock()
        self._initialize_db()
    
    def _get_db_connection(self):
        """Crea una nuova connessione al database"""
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _initialize_db(self):
        """Inizializza il database SQLite con le tabelle necessarie"""
        with self.lock:
            conn = self._get_db_connection()
            try:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        name TEXT NOT NULL,
                        description TEXT,
                        status TEXT NOT NULL,
                        created_at DATETIME NOT NULL,
                        updated_at DATETIME NOT NULL,
                        metadata TEXT,
                        UNIQUE(user_id, name)
                    )
                """)
                
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS project_interactions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        interaction_id INTEGER NOT NULL,
                        relevance_score FLOAT NOT NULL,
                        created_at DATETIME NOT NULL,
                        FOREIGN KEY(project_id) REFERENCES projects(id),
                        FOREIGN KEY(interaction_id) REFERENCES interactions(id)
                    )
                """)
                conn.commit()
            finally:
                conn.close()
    
    def create_project(
        self,
        name: str,
        description: str = "",
        user_id: str = "",
        status: str = "active",
        metadata: Dict = None
    ) -> bool:
        """
        Crea un nuovo progetto
        
        Args:
            name: Nome del progetto
            description: Descrizione del progetto
            user_id: ID dell'utente
            status: Stato iniziale del progetto
            metadata: Metadati aggiuntivi del progetto
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                # Verifica se il progetto esiste già
                cursor = conn.execute(
                    """
                    SELECT id FROM projects
                    WHERE name = ?
                    """,
                    (name,)
                )
                if cursor.fetchone():
                    print(f"Progetto con nome {name} già esistente")
                    return False
                
                # Crea il nuovo progetto
                cursor.execute(
                    """
                    INSERT INTO projects
                    (name, description, user_id, status, created_at, updated_at, metadata)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        name,
                        description,
                        user_id,
                        status,
                        datetime.now().isoformat(),
                        datetime.now().isoformat(),
                        json.dumps(metadata or {})
                    )
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Errore durante la creazione del progetto: {e}")
                return False
            finally:
                conn.close()
    
    def update_project_status(self, user_id: str, project_name: str, status: ProjectStatus) -> bool:
        """
        Aggiorna lo stato di un progetto
        
        Args:
            user_id: ID dell'utente
            project_name: Nome del progetto
            status: Nuovo stato del progetto
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    UPDATE projects
                    SET status = ?, updated_at = ?
                    WHERE user_id = ? AND name = ?
                    """,
                    (status.value, datetime.now().isoformat(), user_id, project_name)
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Errore durante l'aggiornamento dello stato del progetto: {e}")
                return False
            finally:
                conn.close()
    
    def update_project_metadata(self, user_id: str, project_name: str, metadata: Dict) -> bool:
        """
        Aggiorna i metadati di un progetto
        
        Args:
            user_id: ID dell'utente
            project_name: Nome del progetto
            metadata: Nuovi metadati del progetto
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    UPDATE projects
                    SET metadata = ?, updated_at = ?
                    WHERE user_id = ? AND name = ?
                    """,
                    (
                        json.dumps(metadata),
                        datetime.now().isoformat(),
                        user_id,
                        project_name
                    )
                )
                conn.commit()
                return cursor.rowcount > 0
            except Exception as e:
                print(f"Errore durante l'aggiornamento dei metadati del progetto: {e}")
                return False
            finally:
                conn.close()
    
    def link_interaction(
        self,
        project_name: str,
        interaction_id: int,
        relevance_score: float
    ) -> bool:
        """
        Collega un'interazione a un progetto
        
        Args:
            project_name: Nome del progetto
            interaction_id: ID dell'interazione
            relevance_score: Punteggio di rilevanza dell'interazione per il progetto
        
        Returns:
            bool: True se l'operazione è riuscita
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                # Prima recupera l'ID del progetto
                cursor = conn.execute(
                    """
                    SELECT id FROM projects
                    WHERE name = ?
                    """,
                    (project_name,)
                )
                result = cursor.fetchone()
                if not result:
                    print(f"Progetto con nome {project_name} non trovato")
                    return False
                
                project_id = result[0]
                
                # Ora collega l'interazione
                cursor.execute(
                    """
                    INSERT INTO project_interactions
                    (project_id, interaction_id, relevance_score, created_at)
                    VALUES (?, ?, ?, ?)
                    """,
                    (
                        project_id,
                        interaction_id,
                        relevance_score,
                        datetime.now().isoformat()
                    )
                )
                conn.commit()
                return True
            except Exception as e:
                print(f"Errore durante il collegamento dell'interazione: {e}")
                return False
            finally:
                conn.close()
    
    def get_project_interactions(self, project_id: int, min_relevance: float = 0.5) -> List[Dict]:
        """
        Recupera le interazioni associate a un progetto
        
        Args:
            project_id: ID del progetto
            min_relevance: Punteggio minimo di rilevanza
        
        Returns:
            Lista di interazioni rilevanti
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT i.*, pi.relevance_score
                    FROM interactions i
                    JOIN project_interactions pi ON i.id = pi.interaction_id
                    WHERE pi.project_id = ? AND pi.relevance_score >= ?
                    ORDER BY pi.relevance_score DESC
                    """,
                    (project_id, min_relevance)
                )
                
                interactions = []
                for row in cursor:
                    interaction = dict(row)
                    interaction['context'] = json.loads(interaction['context'])
                    interaction['topics'] = json.loads(interaction['topics'])
                    interactions.append(interaction)
                
                return interactions
            except Exception as e:
                print(f"Errore durante il recupero delle interazioni del progetto: {e}")
                return []
            finally:
                conn.close()
    
    def get_project_summary(self, project_identifier: str) -> Optional[Dict]:
        """
        Recupera un riepilogo del progetto
        
        Args:
            project_identifier: ID o nome del progetto
        
        Returns:
            Dizionario contenente il riepilogo del progetto o None
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                # Prova prima a cercare per ID
                try:
                    project_id = int(project_identifier)
                    where_clause = "p.id = ?"
                    param = project_id
                except ValueError:
                    # Se non è un ID valido, cerca per nome
                    where_clause = "p.name = ?"
                    param = project_identifier
                
                cursor = conn.execute(
                    f"""
                    SELECT 
                        p.id,
                        p.name,
                        p.description,
                        p.user_id,
                        p.status,
                        p.created_at,
                        p.updated_at,
                        p.metadata,
                        COUNT(pi.id) as interaction_count
                    FROM projects p
                    LEFT JOIN project_interactions pi ON p.id = pi.project_id
                    WHERE {where_clause}
                    GROUP BY p.id
                    """,
                    (param,)
                )
                
                result = cursor.fetchone()
                if result is None:
                    print(f"Progetto {project_identifier} non trovato")
                    return None
                
                return {
                    'id': result[0],
                    'name': result[1],
                    'description': result[2],
                    'user_id': result[3],
                    'status': result[4],
                    'created_at': result[5],
                    'updated_at': result[6],
                    'metadata': result[7],
                    'interaction_count': result[8]
                }
            except Exception as e:
                print(f"Errore durante il recupero del progetto: {e}")
                return None
            finally:
                conn.close()
    
    def get_user_projects(self, user_id: str) -> List[Dict]:
        """
        Recupera tutti i progetti di un utente
        
        Args:
            user_id: ID dell'utente
        
        Returns:
            Lista dei progetti dell'utente
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT 
                        p.id,
                        p.name,
                        p.description,
                        p.user_id,
                        p.status,
                        p.created_at,
                        p.updated_at,
                        p.metadata,
                        COUNT(pi.id) as interaction_count
                    FROM projects p
                    LEFT JOIN project_interactions pi ON p.id = pi.project_id
                    WHERE p.user_id = ?
                    GROUP BY p.id
                    ORDER BY p.created_at DESC
                    """,
                    (user_id,)
                )
                
                projects = []
                for row in cursor:
                    project = {
                        'id': row[0],
                        'name': row[1],
                        'description': row[2],
                        'user_id': row[3],
                        'status': row[4],
                        'created_at': row[5],
                        'updated_at': row[6],
                        'metadata': row[7],
                        'interaction_count': row[8]
                    }
                    projects.append(project)
                
                return projects
            except Exception as e:
                print(f"Errore durante il recupero dei progetti dell'utente: {e}")
                return []
            finally:
                conn.close()
