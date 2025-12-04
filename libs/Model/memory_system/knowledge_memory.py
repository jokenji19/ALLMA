"""KnowledgeMemory - Sistema di memoria per la conoscenza"""

from typing import Dict, List, Optional
import sqlite3
import json

class KnowledgeMemory:
    def __init__(self, db_path: str = "Model/data/allma.db"):
        """
        Inizializza il sistema di memoria per la conoscenza
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
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
            
            # Commit esplicito per assicurarsi che le tabelle siano create
            conn.commit()
            
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
