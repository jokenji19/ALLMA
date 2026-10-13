"""KnowledgeMemory - Sistema di memoria per la conoscenza"""

from typing import Dict, List, Optional
import sqlite3
import json
from dataclasses import asdict, is_dataclass
from enum import Enum
from pathlib import Path

class KnowledgeMemory:
    def __init__(self, db_path: str = "Model/data/allma.db"):
        """
        Inizializza il sistema di memoria per la conoscenza
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
        
        # Ensure directory exists
        import os
        dirname = os.path.dirname(db_path)
        if dirname and not os.path.exists(dirname):
            try:
                os.makedirs(dirname)
            except Exception as e:
                print(f"Failed to create KnowledgeMemory DB dir: {e}")

        self._init_db()
        
    def _init_db(self):
        """Inizializza il database se non esiste"""
        with sqlite3.connect(self.db_path) as conn:
            # Crea la tabella knowledge se non esiste
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Crea indici per migliorare le performance delle ricerche
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_content
                ON knowledge(content)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_knowledge_metadata
                ON knowledge(metadata)
            """)
            conn.execute('CREATE TABLE IF NOT EXISTS cognitive_concepts (name TEXT PRIMARY KEY, data TEXT NOT NULL)')
            conn.execute('CREATE TABLE IF NOT EXISTS knowledge_imports (source TEXT PRIMARY KEY)')
            
            # Commit esplicito per assicurarsi che le tabelle siano create
            conn.commit()

    @staticmethod
    def _json_default(value):
        if isinstance(value, Enum):
            return value.value
        if is_dataclass(value):
            return asdict(value)
        if hasattr(value, 'to_dict'):
            return value.to_dict()
        raise TypeError('Unsupported concept metadata')

    def get_concept(self, name):
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute('SELECT data FROM cognitive_concepts WHERE name=?', (name,)).fetchone()
        return json.loads(row[0]) if row else None

    def has_concept(self, name):
        return self.get_concept(name) is not None

    def get_all_concepts(self):
        with sqlite3.connect(self.db_path) as conn:
            return [row[0] for row in conn.execute('SELECT name FROM cognitive_concepts ORDER BY name')]

    def add_concept(self, name, data):
        # Coalescence observations are not independently verified knowledge.
        record = dict(data, knowledge_verified=False)
        encoded = json.dumps(record, default=self._json_default, ensure_ascii=False)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('INSERT OR IGNORE INTO cognitive_concepts(name,data) VALUES (?,?)', (name, encoded))

    def update_concept(self, name, changes):
        with sqlite3.connect(self.db_path) as conn:
            # Lock before reading, otherwise concurrent read/modify/write updates
            # can overwrite fields saved by another connection in the meantime.
            conn.execute('BEGIN IMMEDIATE')
            row = conn.execute('SELECT data FROM cognitive_concepts WHERE name=?', (name,)).fetchone()
            record = json.loads(row[0]) if row else {}
            record.update(changes)
            record['knowledge_verified'] = False
            conn.execute('INSERT OR REPLACE INTO cognitive_concepts(name,data) VALUES (?,?)',
                         (name, json.dumps(record, default=self._json_default, ensure_ascii=False)))

    def import_legacy(self, source):
        """Copy legacy knowledge once, transactionally; retain the original database."""
        source = Path(source).resolve()
        if not source.is_file() or source == Path(self.db_path).resolve():
            return
        with sqlite3.connect(self.db_path) as conn:
            if conn.execute('SELECT 1 FROM knowledge_imports WHERE source=?', (str(source),)).fetchone():
                return
            with sqlite3.connect(source.as_uri() + '?mode=ro', uri=True) as old:
                tables = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if 'knowledge' in tables:
                    for content, metadata, created in old.execute('SELECT content,metadata,created_at FROM knowledge'):
                        if not conn.execute('SELECT 1 FROM knowledge WHERE content=? AND metadata IS ?', (content, metadata)).fetchone():
                            conn.execute('INSERT INTO knowledge(content,metadata,created_at) VALUES (?,?,?)',
                                         (content, metadata, created))
                if 'cognitive_concepts' in tables:
                    for name, data in old.execute('SELECT name,data FROM cognitive_concepts'):
                        conn.execute('INSERT OR IGNORE INTO cognitive_concepts(name,data) VALUES (?,?)', (name, data))
            conn.execute('INSERT INTO knowledge_imports(source) VALUES (?)', (str(source),))
            
    def store_knowledge(self, content: str, metadata: Optional[Dict] = None):
        """
        Memorizza una nuova conoscenza
        
        Args:
            content: Contenuto della conoscenza
            metadata: Metadati opzionali
        """
        # Assicurati che il database sia inizializzato
        self._init_db()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO knowledge (content, metadata) VALUES (?, ?)",
                (content, json.dumps(metadata) if metadata else None)
            )
            conn.commit()
            
    def get_knowledge_for_text(self, text: str, limit: int = 5) -> List[str]:
        """
        Recupera la conoscenza rilevante per un testo
        
        Args:
            text: Testo per cui cercare conoscenza rilevante
            limit: Numero massimo di risultati
            
        Returns:
            List[str]: Lista di conoscenze rilevanti
        """
        # Assicurati che il database sia inizializzato
        self._init_db()
        
        with sqlite3.connect(self.db_path) as conn:
            # Cerca parole chiave nel testo
            keywords = [word.lower() for word in text.split() if len(word) > 3]
            keywords.extend([
                "technical", "requirements", "technology", "stack",
                "framework", "performance", "speed", "time"
            ])
            
            # Costruisci la query SQL
            query = "SELECT DISTINCT content FROM knowledge"
            
            # Se ci sono parole chiave, aggiungi la clausola WHERE
            if keywords:
                conditions = []
                params = []
                
                for keyword in keywords:
                    conditions.append("LOWER(content) LIKE ?")
                    params.append(f"%{keyword}%")
                    
                    # Cerca anche nei metadati
                    conditions.append("LOWER(metadata) LIKE ?")
                    params.append(f"%{keyword}%")
                    
                query += " WHERE " + " OR ".join(conditions)
                
            query += f" LIMIT {limit}"
            
            # Esegui la query
            cursor = conn.execute(query, params if keywords else [])
            return [row[0] for row in cursor.fetchall()]
            
    def get_all_knowledge(self) -> List[Dict]:
        """
        Recupera tutta la conoscenza memorizzata
        
        Returns:
            List[Dict]: Lista di dizionari con la conoscenza
        """
        # Assicurati che il database sia inizializzato
        self._init_db()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                "SELECT content, metadata, created_at FROM knowledge"
            )
            return [dict(row) for row in cursor.fetchall()]

    def get_metadata(self, content: str) -> Optional[Dict]:
        """
        Recupera i metadati di una conoscenza
        
        Args:
            content: Contenuto della conoscenza
            
        Returns:
            Optional[Dict]: Metadati della conoscenza o None se non trovata
        """
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute(
                "SELECT metadata FROM knowledge WHERE content = ?",
                (content,)
            ).fetchone()
            
            if result and result[0]:
                return json.loads(result[0])
            return None
