import sqlite3
import threading
import json
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import os

class ProjectTracker:
    """Gestisce il tracciamento dei progetti e delle loro interazioni"""
    
    def __init__(self, db_path: str = None):
        """
        Inizializza il tracker dei progetti
        
        Args:
            db_path: Percorso del database SQLite
        """
        if db_path is None:
            # Usa il percorso predefinito nella directory Model/database
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_dir = os.path.join(os.path.dirname(current_dir), "database")
            os.makedirs(db_dir, exist_ok=True)
            db_path = os.path.join(db_dir, "allma.db")
            
        self.db_path = db_path
        self.lock = threading.Lock()  # Fix: Initialize the lock properly
        self._db_connection = None
        self._init_db()
    
    def __del__(self):
        """Chiude la connessione al database quando l'oggetto viene distrutto"""
        if hasattr(self, '_db_connection') and self._db_connection:
            self._db_connection.close()
    
    def _get_db_connection(self) -> sqlite3.Connection:
        """
        Ottiene una connessione al database
        
        Returns:
            Connessione al database
        """
        if not hasattr(self, '_db_connection') or self._db_connection is None:
            self._db_connection = sqlite3.connect(self.db_path)
            self._db_connection.row_factory = sqlite3.Row
        return self._db_connection
    
    def _init_db(self):
        """Inizializza il database con le tabelle necessarie"""
        conn = self._get_db_connection()
        cursor = conn.cursor()
        
        # Crea la tabella dei progetti se non esiste
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                description TEXT,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crea la tabella delle interazioni se non esiste
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Crea la tabella delle interazioni dei progetti se non esiste
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL,
                interaction_id INTEGER NOT NULL,
                interaction_type TEXT DEFAULT 'general',
                metadata TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (project_id) REFERENCES projects(id),
                FOREIGN KEY (interaction_id) REFERENCES interactions(id),
                UNIQUE(project_id, interaction_id)
            )
        """)
        
        # Migra la tabella project_interactions se necessario
        try:
            # Verifica se le colonne esistono già
            cursor.execute("SELECT interaction_type FROM project_interactions LIMIT 1")
        except sqlite3.OperationalError:
            print("Migrating project_interactions table...")
            # Le colonne non esistono, aggiungile
            cursor.execute("ALTER TABLE project_interactions ADD COLUMN interaction_type TEXT DEFAULT 'general'")
            cursor.execute("ALTER TABLE project_interactions ADD COLUMN metadata TEXT")
            print("Migration completed successfully")
        
        conn.commit()
    
    def create_project(
        self,
        user_id: str,
        name: str,
        description: str = "",
        metadata: Dict = None
    ) -> int:
        """
        Crea un nuovo progetto
        
        Args:
            user_id: ID dell'utente
            name: Nome del progetto
            description: Descrizione del progetto
            metadata: Metadati opzionali del progetto
        
        Returns:
            ID del progetto creato o None se l'operazione fallisce
        """
        try:
            with self.lock:  # Use the lock properly
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                # Inserisci il progetto
                cursor.execute("""
                    INSERT INTO projects
                    (user_id, name, description, metadata)
                    VALUES (?, ?, ?, ?)
                """, (
                    user_id,
                    name,
                    description,
                    json.dumps(metadata or {})
                ))
                
                # Get the ID of the inserted project
                project_id = cursor.lastrowid
                print(f"DEBUG: Progetto creato con ID {project_id}")
                
                # Verifica che il progetto sia stato creato correttamente
                cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
                project = cursor.fetchone()
                print(f"DEBUG: Verifica progetto creato: {dict(project) if project else None}")
                
                conn.commit()
                return project_id
            
        except Exception as e:
            print(f"Errore durante la creazione del progetto: {e}")
            import traceback
            print(f"DEBUG: Traceback completo:\n{traceback.format_exc()}")
            if conn:
                conn.rollback()
            return None
    
    def get_project(self, project_id: Union[int, str]) -> Optional[Dict[str, Any]]:
        """
        Recupera i dettagli di un progetto
        
        Args:
            project_id: ID del progetto (int o str)
        
        Returns:
            Dizionario con i dettagli del progetto o None se non trovato
        """
        try:
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                # Prima recupera i dettagli del progetto
                cursor.execute("""
                    SELECT p.*, 
                           COUNT(DISTINCT pi.interaction_id) as interaction_count
                    FROM projects p
                    LEFT JOIN project_interactions pi ON pi.project_id = p.id
                    WHERE p.id = ?
                    GROUP BY p.id
                """, (project_id,))
                
                row = cursor.fetchone()
                if not row:
                    print(f"DEBUG: Nessun progetto trovato con ID {project_id}")
                    return None
                    
                # Converti la riga in dizionario
                project_dict = dict(row)
                print(f"DEBUG: Dati progetto raw: {project_dict}")
                
                # Parse metadata if it exists
                if project_dict.get('metadata'):
                    project_dict['metadata'] = json.loads(project_dict['metadata'])
                else:
                    project_dict['metadata'] = {}
                
                # Assicurati che interaction_count sia presente e sia un intero
                if 'interaction_count' not in project_dict:
                    print(f"DEBUG: interaction_count non presente nei dati raw")
                    # Conta manualmente le interazioni
                    cursor.execute("""
                        SELECT COUNT(DISTINCT interaction_id) 
                        FROM project_interactions 
                        WHERE project_id = ?
                    """, (project_id,))
                    count = cursor.fetchone()[0]
                    project_dict['interaction_count'] = count
                    
                project_dict['interaction_count'] = int(project_dict.get('interaction_count', 0))
                print(f"DEBUG: Dati progetto finali: {project_dict}")
                
                return project_dict
                    
        except Exception as e:
            print(f"ERROR: Errore nel recupero del progetto: {str(e)}")
            import traceback
            print(f"DEBUG: Traceback completo:\n{traceback.format_exc()}")
            return None
    
    def get_project_summary(self, project_id: Union[int, str]) -> Optional[Dict]:
        """
        Ottiene un riepilogo del progetto con statistiche
        
        Args:
            project_id: ID o nome del progetto
        
        Returns:
            Dizionario con il riepilogo del progetto o None se non trovato
        """
        try:
            if isinstance(project_id, str):
                return self.get_project_by_name(project_id)
            else:
                return self.get_project(project_id)
        except Exception as e:
            print(f"Errore durante il recupero del progetto: {e}")
            return None
    
    def get_project_by_name(self, name: str) -> Optional[Dict]:
        """
        Recupera i dettagli di un progetto dal suo nome
        
        Args:
            name: Nome del progetto
        
        Returns:
            Dizionario con i dettagli del progetto o None se non trovato
        """
        try:
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.execute(
                    """
                    SELECT p.*, (SELECT COUNT(*) FROM project_interactions pi WHERE pi.project_id = p.id) as interaction_count
                    FROM projects p
                    WHERE p.name = ?
                    """,
                    (name,)
                )
                row = cursor.fetchone()
                if row:
                    project = dict(row)
                    project['interaction_count'] = int(project.get('interaction_count', 0))
                    if project['metadata']:
                        project['metadata'] = json.loads(project['metadata'])
                    return project
                return None
        except sqlite3.Error as e:
            print(f"Error getting project by name: {e}")
            return None
    
    def link_interaction(
        self,
        project_id: int,
        interaction_id: int,
        interaction_type: str = "general",
        metadata: Dict = None
    ) -> bool:
        """
        Collega un'interazione a un progetto
        
        Args:
            project_id: ID del progetto
            interaction_id: ID dell'interazione
            interaction_type: Tipo di interazione
            metadata: Metadati opzionali dell'interazione
        
        Returns:
            True se l'operazione è riuscita
        """
        print(f"DEBUG: Tentativo di collegare interazione {interaction_id} al progetto {project_id}")
        try:
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                # Verifica che il progetto esista
                cursor.execute(
                    "SELECT id FROM projects WHERE id = ?",
                    (project_id,)
                )
                project_row = cursor.fetchone()
                if not project_row:
                    print(f"DEBUG: Progetto {project_id} non trovato")
                    print(f"DEBUG: Query SQL: SELECT id FROM projects WHERE id = {project_id}")
                    # Lista tutti i progetti per debug
                    cursor.execute("SELECT id, name FROM projects")
                    all_projects = cursor.fetchall()
                    print(f"DEBUG: Progetti esistenti: {[dict(p) for p in all_projects]}")
                    return False
                    
                # Verifica che l'interazione esista
                cursor.execute(
                    "SELECT id FROM interactions WHERE id = ?",
                    (interaction_id,)
                )
                if not cursor.fetchone():
                    print(f"DEBUG: Interazione {interaction_id} non trovata, la creo...")
                    # Se l'interazione non esiste, la creiamo
                    cursor.execute("""
                        INSERT INTO interactions (id, content, metadata)
                        VALUES (?, ?, ?)
                    """, (
                        interaction_id,
                        "Interazione generata automaticamente",
                        json.dumps({})
                    ))
                    print(f"DEBUG: Interazione {interaction_id} creata con successo")
                
                # Inserisci il collegamento
                try:
                    cursor.execute("""
                        INSERT INTO project_interactions
                        (project_id, interaction_id, interaction_type, metadata)
                        VALUES (?, ?, ?, ?)
                    """, (
                        project_id,
                        interaction_id,
                        interaction_type,
                        json.dumps(metadata or {})
                    ))
                    print(f"DEBUG: Query di inserimento eseguita con successo")
                except sqlite3.IntegrityError as e:
                    print(f"DEBUG: Errore di integrità durante l'inserimento: {e}")
                    return False
                
                conn.commit()
                print(f"DEBUG: Interazione {interaction_id} collegata con successo al progetto {project_id}")
                
                # Verifica il conteggio delle interazioni
                cursor.execute("""
                    SELECT COUNT(DISTINCT interaction_id) 
                    FROM project_interactions 
                    WHERE project_id = ?
                """, (project_id,))
                count = cursor.fetchone()[0]
                print(f"DEBUG: Numero totale di interazioni per il progetto {project_id}: {count}")
                
                return True
                    
        except Exception as e:
            print(f"DEBUG: Errore durante il collegamento dell'interazione: {e}")
            import traceback
            print(f"DEBUG: Traceback completo:\n{traceback.format_exc()}")
            if conn:
                conn.rollback()
            return False
    
    def update_project_status(
        self,
        project_id: int,
        status: str
    ) -> bool:
        """
        Aggiorna lo stato di un progetto
        
        Args:
            project_id: ID del progetto
            status: Nuovo stato del progetto
        
        Returns:
            True se l'operazione è riuscita
        """
        try:
            with self.lock:
                conn = self._get_db_connection()
                cursor = conn.cursor()
                
                # Aggiorna lo stato
                cursor.execute("""
                    UPDATE projects
                    SET status = ?
                    WHERE id = ?
                """, (status, project_id))
                
                if cursor.rowcount == 0:
                    print(f"Progetto {project_id} non trovato")
                    return False
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Errore durante l'aggiornamento dello stato del progetto: {e}")
            return False
        finally:
            conn.close()
