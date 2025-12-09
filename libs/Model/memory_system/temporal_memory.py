from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sqlite3
import json
from collections import defaultdict
import numpy as np
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity as cs
import math
from collections import Counter
import numpy as np

class SimpleTfidf:
    def __init__(self):
        self.vocab = {}
        self.doc_count = 0
        
    def fit_transform(self, documents):
        self.doc_count = len(documents)
        word_counts = []
        all_words = set()
        
        for doc in documents:
            words = doc.lower().split()
            counts = Counter(words)
            word_counts.append(counts)
            all_words.update(words)
            
        self.vocab = sorted(list(all_words))
        self.idf = {}
        
        for word in self.vocab:
            doc_freq = sum(1 for counts in word_counts if word in counts)
            self.idf[word] = math.log(self.doc_count / (1 + doc_freq))
            
        vectors = []
        for counts in word_counts:
            vector = [counts[word] * self.idf[word] for word in self.vocab]
            vectors.append(vector)
            
        return np.array(vectors)

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return np.array([[0.0]])
    return np.array([[np.dot(v1, v2.T) / (norm1 * norm2)]])
import threading
import logging

class TemporalMemorySystem:
    def __init__(self, db_path: str = "memory.db"):
        """
        Inizializza il sistema di memoria temporale.
        
        Args:
            db_path: Percorso del database SQLite
        """
        self.db_path = db_path
        self.context_window = timedelta(days=30)
        self.vectorizer = SimpleTfidf()
        self.lock = threading.Lock()
        
        # Crea le tabelle se non esistono
        with self.lock:
            conn = self._get_db_connection()
            try:
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

    def _get_db_connection(self):
        """Crea una nuova connessione al database"""
        conn = sqlite3.connect(self.db_path, timeout=20)
        conn.row_factory = sqlite3.Row
        return conn

    def store_interaction(
        self,
        user_id: str,
        interaction: Dict,
        metadata: Optional[Dict] = None
    ) -> bool:
        """
        Memorizza una nuova interazione
        
        Args:
            user_id: ID dell'utente
            interaction: Dizionario contenente i dettagli dell'interazione
            metadata: Metadati opzionali
        
        Returns:
            bool: True se l'interazione è stata memorizzata con successo, False altrimenti
        """
        try:
            if not user_id:
                logging.error("User ID mancante")
                return False
                
            # Gestisci contenuto mancante o non valido
            content = interaction.get('content')
            if content is None:
                logging.error("Contenuto mancante")
                return False
            elif not isinstance(content, str):
                content = str(content)
                
            # Gestisci contesto non valido
            context = interaction.get('context', {})
            if not isinstance(context, dict):
                context = {'raw_context': str(context)}
                
            # Gestisci emozione non valida
            emotion = interaction.get('emotion')
            if not isinstance(emotion, str):
                emotion = str(emotion)
                
            with self.lock:
                conn = self._get_db_connection()
                try:
                    # Se c'è un timestamp nell'interazione, usalo
                    timestamp = interaction.get('timestamp', datetime.now().isoformat())
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.isoformat()
                    
                    topics = self._extract_topics(content)
                    
                    # Log dei dati che stiamo per inserire
                    logging.debug(f"Memorizzazione interazione per user_id={user_id}")
                    logging.debug(f"Contenuto={content[:50]}...")
                    
                    cursor = conn.execute(
                        """
                        INSERT INTO interactions 
                        (user_id, timestamp, content, context, emotion, topics, metadata)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            user_id,
                            timestamp,
                            content,
                            json.dumps(context),
                            emotion,
                            json.dumps(topics),
                            json.dumps(metadata or {})
                        )
                    )
                    
                    # Aggiorna i pattern temporali
                    self._update_temporal_patterns(user_id, conn)
                    
                    conn.commit()
                    logging.debug(f"Interazione memorizzata con ID={cursor.lastrowid}")
                    
                    return True
                    
                except Exception as e:
                    logging.error(f"Errore durante la memorizzazione dell'interazione: {e}")
                    conn.rollback()
                    return False
                finally:
                    conn.close()
                    
        except Exception as e:
            logging.error(f"Errore durante la preparazione dell'interazione: {e}")
            return False

    def _update_temporal_patterns(self, user_id: str, conn: sqlite3.Connection):
        """
        Aggiorna i pattern temporali per un utente
        
        Args:
            user_id: ID dell'utente
            conn: Connessione al database
        """
        try:
            # Recupera tutte le interazioni degli ultimi 30 giorni
            cursor = conn.execute(
                """
                SELECT timestamp FROM interactions
                WHERE user_id = ? AND timestamp > ?
                """,
                (user_id, (datetime.now() - self.context_window).isoformat())
            )
            recent_interactions = cursor.fetchall()

            if not recent_interactions:
                return

            # Analizza pattern temporali
            timestamps = [datetime.fromisoformat(t['timestamp']) for t in recent_interactions]
            patterns = {
                'hour_distribution': self._analyze_hour_distribution(timestamps),
                'day_distribution': self._analyze_day_distribution(timestamps),
                'frequency': self._calculate_interaction_frequency(timestamps)
            }

            # Salva i pattern
            conn.execute(
                """
                INSERT OR REPLACE INTO temporal_patterns
                (user_id, pattern_type, pattern_data, last_updated)
                VALUES (?, 'time_patterns', ?, ?)
                """,
                (user_id, json.dumps(patterns), datetime.now().isoformat())
            )
            conn.commit()

        except Exception as e:
            logging.error(f"Errore nell'aggiornamento dei pattern temporali: {str(e)}")
            conn.rollback()

    def _extract_topics(self, content: str) -> List[str]:
        """
        Estrae i topic principali dal contenuto
        
        Args:
            content: Testo da analizzare
        
        Returns:
            Lista di topic estratti
        """
        # Per ora implementazione base, da migliorare con NLP più avanzato
        words = content.lower().split()
        # Rimuovi parole comuni e corte
        topics = [w for w in words if len(w) > 3]
        return topics[:5]  # Ritorna i primi 5 topic

    def _analyze_hour_distribution(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Analizza la distribuzione oraria delle interazioni"""
        hours = [t.hour for t in timestamps]
        distribution = defaultdict(int)
        for h in hours:
            distribution[h] += 1
        total = len(hours)
        return {str(h): count/total for h, count in distribution.items()}

    def _analyze_day_distribution(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Analizza la distribuzione giornaliera delle interazioni"""
        days = [t.strftime('%A') for t in timestamps]
        distribution = defaultdict(int)
        for d in days:
            distribution[d] += 1
        total = len(days)
        return {d: count/total for d, count in distribution.items()}

    def _calculate_interaction_frequency(self, timestamps: List[datetime]) -> Dict[str, float]:
        """Calcola la frequenza media delle interazioni"""
        if len(timestamps) < 2:
            return {'average_gap_hours': 24.0, 'std_gap_hours': 0.0}
        
        # Ordina i timestamp
        timestamps = sorted(timestamps)
        gaps = []
        
        # Calcola gli intervalli tra le interazioni
        for i in range(1, len(timestamps)):
            gap = timestamps[i] - timestamps[i-1]
            # Converti in ore
            gap_hours = gap.total_seconds() / 3600.0
            gaps.append(gap_hours)
        
        average_gap = float(np.mean(gaps))
        std_gap = float(np.std(gaps)) if len(gaps) > 1 else 0.0
        
        return {
            'average_gap_hours': average_gap,
            'std_gap_hours': std_gap
        }

    def get_temporal_patterns(self, user_id: str) -> Optional[Dict]:
        """
        Recupera i pattern temporali per un utente
        
        Args:
            user_id: ID dell'utente
        
        Returns:
            Dizionario contenente i pattern temporali o None
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                # Recupera i pattern salvati
                cursor = conn.execute(
                    """
                    SELECT pattern_data FROM temporal_patterns
                    WHERE user_id = ? AND pattern_type = 'time_patterns'
                    """,
                    (user_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return json.loads(row['pattern_data'])
                
                # Se non ci sono pattern salvati, calcolali
                cursor = conn.execute(
                    """
                    SELECT timestamp FROM interactions
                    WHERE user_id = ? AND timestamp > ?
                    """,
                    (user_id, (datetime.now() - self.context_window).isoformat())
                )
                recent_interactions = cursor.fetchall()
                
                if not recent_interactions:
                    return None
                
                # Analizza pattern temporali
                timestamps = [datetime.fromisoformat(t['timestamp']) for t in recent_interactions]
                patterns = {
                    'hour_distribution': self._analyze_hour_distribution(timestamps),
                    'day_distribution': self._analyze_day_distribution(timestamps),
                    'frequency': self._calculate_interaction_frequency(timestamps)
                }
                
                # Salva i pattern
                conn.execute(
                    """
                    INSERT OR REPLACE INTO temporal_patterns
                    (user_id, pattern_type, pattern_data, last_updated)
                    VALUES (?, 'time_patterns', ?, ?)
                    """,
                    (user_id, json.dumps(patterns), datetime.now().isoformat())
                )
                conn.commit()
                
                return patterns
                
            except Exception as e:
                logging.error(f"Errore nel recupero dei pattern temporali: {str(e)}")
                return None
            finally:
                conn.close()

    def get_relevant_context(self, user_id: str, current_topic: str, limit: int = 5) -> List[dict]:
        """
        Recupera il contesto rilevante basato sul topic corrente
        
        Args:
            user_id: ID dell'utente
            current_topic: Topic corrente
            limit: Numero massimo di interazioni da recuperare
        
        Returns:
            Lista di interazioni rilevanti
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT content, context, timestamp
                    FROM interactions
                    WHERE user_id = ? AND timestamp > ?
                    ORDER BY timestamp DESC
                    """,
                    (user_id, (datetime.now() - self.context_window).isoformat())
                )
                recent_interactions = cursor.fetchall()

                if not recent_interactions:
                    return []

                # Calcola similarità con il topic corrente
                contents = [dict(r)['content'] for r in recent_interactions]
                contents.append(current_topic)
                
                try:
                    tfidf_matrix = self.vectorizer.fit_transform(contents)
                    similarities = cs(tfidf_matrix[-1:], tfidf_matrix[:-1])[0]
                except:
                    # Fallback se la vectorization fallisce
                    similarities = [0] * len(recent_interactions)

                # Ordina per similarità e prendi i top N
                sorted_interactions = sorted(
                    zip(similarities, recent_interactions),
                    key=lambda x: x[0],
                    reverse=True
                )[:limit]

                return [
                    {
                        'content': dict(interaction)['content'],
                        'context': json.loads(dict(interaction)['context']),
                        'timestamp': dict(interaction)['timestamp'],
                        'similarity': float(similarity)
                    }
                    for similarity, interaction in sorted_interactions
                ]

            except Exception as e:
                logging.error(f"Errore nel recupero del contesto: {str(e)}")
                return []
            finally:
                conn.close()

    def get_last_interaction_id(self, user_id: str) -> Optional[int]:
        """
        Recupera l'ID dell'ultima interazione di un utente
        
        Args:
            user_id: ID dell'utente
        
        Returns:
            ID dell'ultima interazione o None
        """
        with self.lock:
            conn = self._get_db_connection()
            try:
                cursor = conn.execute(
                    """
                    SELECT id FROM interactions
                    WHERE user_id = ?
                    ORDER BY timestamp DESC
                    LIMIT 1
                    """,
                    (user_id,)
                )
                result = cursor.fetchone()
                return result[0] if result else None
            except Exception as e:
                logging.error(f"Errore durante il recupero dell'ultima interazione: {str(e)}")
                return None
            finally:
                conn.close()

    def get_interactions(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """
        Recupera le interazioni di un utente in un intervallo di tempo.
        
        Args:
            user_id: ID dell'utente
            start_time: Tempo di inizio opzionale
            end_time: Tempo di fine opzionale
            
        Returns:
            Lista delle interazioni
        """
        if not user_id:
            raise ValueError("User ID richiesto")
            
        query = "SELECT * FROM interactions WHERE user_id = ?"
        params = [user_id]
        
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time.isoformat())
            
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time.isoformat())
            
        query += " ORDER BY timestamp DESC"
        
        with self.lock:
            conn = self._get_db_connection()
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
        interactions = []
        for row in rows:
            interaction = {
                "id": row[0],
                "user_id": row[1],
                "timestamp": datetime.fromisoformat(row[2]),
                "content": row[3],
                "context": json.loads(row[4]) if row[4] else None,
                "emotion": row[5],
                "topics": json.loads(row[6]) if row[6] else None,
                "metadata": json.loads(row[7]) if row[7] else None
            }
            interactions.append(interaction)
            
        return interactions
