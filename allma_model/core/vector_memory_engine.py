"""
VectorMemoryEngine — ALLMA V6 Sprint 3
======================================

Vector search engine basato su SQLite nativo + TF-IDF persistente.

Perché NON FAISS / sqlite-vss:
    - Nessuno dei due compila su Android arm64 senza toolchain NDK custom.
    - SQLite è già disponibile su Android, zero dipendenze extra.

Architettura:
    SQLite DB (allma_vectors.db)
      └─ tabella "memories": id, user_id, content, vector_blob, timestamp, metadata_json
    
    RAM Index (self._index):
      numpy matrix (n_docs × vocab_size) — rebuild on load, aggiornato incrementalmente

Consistenza:
    Il testo SQLite è la fonte autorevole. Il vocabolario e tutti i vettori
    vengono ricostruiti al riavvio e alla prima ricerca dopo una modifica.
    Il confronto dimensionale resta coerente; il costo della ricostruzione
    cresce con il corpus e deve essere misurato sul dispositivo di destinazione.

Uso:
    engine = VectorMemoryEngine(db_path="data/allma_vectors.db")
    engine.add(user_id="u1", content="ho visto il tramonto", metadata={"mood": "sereno"})
    results = engine.search(user_id="u1", query="tramonto cielo", top_k=5)
    # results: List[dict] con 'content', 'score', 'metadata', 'timestamp'
"""

from __future__ import annotations
import sqlite3
import json
import struct
import logging
import math
from collections import Counter
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import threading

import numpy as np

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────
#  Query Expander Light (Sprint V8.1)
# ─────────────────────────────────────────────────────────

class QueryExpander:
    """
    Espande la query per migliorare il recall (Max-Score Algorithm)
    senza usare pesanti modelli LLM o Sentence-Transformers.
    """
    
    # Dizionario statico leggero per sinonimi comuni (espandibile)
    SYNONYMS = {
        "auto": ["automobile", "macchina", "veicolo", "vettura"],
        "macchina": ["automobile", "auto", "veicolo", "vettura"],
        "film": ["cinema", "pellicola", "movie"],
        "libro": ["romanzo", "lettura", "volume"],
        "cibo": ["mangiare", "pasto", "piatto", "cucina"],
        "paura": ["timore", "spavento", "terrore", "ansia"],
        "felice": ["contento", "gioioso", "allegro"],
        "triste": ["infelice", "malinconico", "depresso"],
        "problema": ["difficoltà", "ostacolo", "guasto", "errore"],
        "aiuto": ["supporto", "assistenza", "soccorso"]
    }
    
    # Pattern comuni per l'astrazione del topic
    TOPIC_MARKERS = {
        "cosa penso di": "",
        "cosa ne pensi di": "",
        "ti ricordi": "",
        "ho detto che": "",
        "qual è il mio": "",
        "qual e il mio": "",
        "mi piace": "preferenza",
        "adoro": "preferenza",
        "odio": "avversione"
    }

    @classmethod
    def expand(cls, query: str) -> List[str]:
        """Restituisce una lista di query varianti (originale + espansioni)."""
        variants = [query.lower()]
        words = query.lower().split()
        
        # 1. Sinonimi
        synonym_query = []
        has_synonym = False
        for w in words:
            if w in cls.SYNONYMS:
                synonym_query.append(cls.SYNONYMS[w][0]) # Prendi il primo sinonimo
                has_synonym = True
            else:
                synonym_query.append(w)
        
        if has_synonym:
            variants.append(" ".join(synonym_query))
            
        # 2. Topic Abstraction (Rimuove il "rumore" conversazionale)
        clean_query = query.lower()
        topic_changed = False
        for marker, replacement in cls.TOPIC_MARKERS.items():
            if marker in clean_query:
                clean_query = clean_query.replace(marker, replacement).strip()
                topic_changed = True
                
        if topic_changed and clean_query and clean_query not in variants:
            variants.append(clean_query)
            
        # 3. Parafrasi basilare
        if "come" in words and "fare" in words:
            variants.append(query.lower().replace("come fare", "istruzioni"))
            
        return list(set(variants)) # Rimuove duplicati



# ─────────────────────────────────────────────────────────
#  TF-IDF leggiero (drop-in replacement di SimpleTfidf)
# ─────────────────────────────────────────────────────────

class _LightTfidf:
    """
    TF-IDF incrementale: supporta .partial_fit(doc) per aggiornare
    il vocabolario senza dover riprocessare tutto il corpus.
    """
    def __init__(self):
        self.vocab: Dict[str, int] = {}   # word -> dim index
        self.df: Dict[str, int] = {}      # word -> doc_frequency
        self.n_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        return text.lower().split()

    def encode(self, text: str) -> np.ndarray:
        """Restituisce il vettore TF-IDF per 'text' usando il vocabolario corrente."""
        if not self.vocab:
            return np.zeros(1, dtype=np.float32)
        tokens = self._tokenize(text)
        counts = Counter(tokens)
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        for word, cnt in counts.items():
            if word in self.vocab:
                idf = 1.0 + math.log((self.n_docs + 1) / (self.df.get(word, 0) + 1))
                vec[self.vocab[word]] = cnt * idf
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def partial_fit(self, text: str) -> None:
        """Aggiorna vocabolario e DF con un nuovo documento."""
        tokens = set(self._tokenize(text))
        for word in tokens:
            if word not in self.vocab:
                self.vocab[word] = len(self.vocab)
            self.df[word] = self.df.get(word, 0) + 1
        self.n_docs += 1

    def vocab_size(self) -> int:
        return len(self.vocab)

    def to_dict(self) -> Dict[str, Any]:
        return {"vocab": self.vocab, "df": self.df, "n_docs": self.n_docs}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> '_LightTfidf':
        obj = cls()
        obj.vocab = data.get("vocab", {})
        obj.df = data.get("df", {})
        obj.n_docs = data.get("n_docs", 0)
        return obj


# ─────────────────────────────────────────────────────────
#  Serializzazione vettori → BLOB SQLite
# ─────────────────────────────────────────────────────────

def _vec_to_blob(vec: np.ndarray) -> bytes:
    """Serializza un vettore float32 in bytes."""
    arr = vec.astype(np.float32)
    return struct.pack(f"{len(arr)}f", *arr)

def _blob_to_vec(blob: bytes) -> np.ndarray:
    """Deserializza bytes → numpy array float32."""
    n = len(blob) // 4
    return np.array(struct.unpack(f"{n}f", blob), dtype=np.float32)


# ─────────────────────────────────────────────────────────
#  VectorMemoryEngine
# ─────────────────────────────────────────────────────────

class VectorMemoryEngine:
    """
    Motor di ricerca semantica persistente per ALLMA.
    Thread-safe: usa un Lock per SQLite (non thread-safe di default).
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS memories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id     TEXT    NOT NULL,
        content     TEXT    NOT NULL,
        vector_blob BLOB,
        timestamp   TEXT    NOT NULL,
        metadata    TEXT    DEFAULT '{}'
    );
    CREATE TABLE IF NOT EXISTS tfidf_state (
        id    INTEGER PRIMARY KEY CHECK (id = 1),
        state TEXT    NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_user ON memories(user_id);
    """

    def __init__(self, db_path: str = "data/allma_vectors.db"):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._tfidf = _LightTfidf()

        # RAM index: lista di (row_id, user_id, np.ndarray)
        self._index: List[Tuple[int, str, np.ndarray]] = []
        self._index_dirty = False

        self._init_db()
        self._load_state()

    # ── DB setup ──────────────────────────────────────────

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path, check_same_thread=False)

    def _init_db(self) -> None:
        import os
        os.makedirs(os.path.dirname(self.db_path) if os.path.dirname(self.db_path) else ".", exist_ok=True)
        with self._conn() as c:
            # --- V7.1: SQLite Ottimizzazione Mobile (Concurrency) ---
            c.execute("PRAGMA journal_mode=WAL;")
            c.execute("PRAGMA synchronous=NORMAL;")
            c.executescript(self.SCHEMA)
            columns = {row[1] for row in c.execute("PRAGMA table_info(memories)")}
            if "source_key" not in columns:
                c.execute("ALTER TABLE memories ADD COLUMN source_key TEXT")
            c.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_memory_source ON memories(user_id, source_key)")

    def _load_state(self) -> None:
        # Content is authoritative: old releases persisted incompatible vectors.
        self._rebuild_index()

    def _save_tfidf_state(self, cursor: sqlite3.Cursor) -> None:
        state_json = json.dumps(self._tfidf.to_dict())
        cursor.execute(
            "INSERT OR REPLACE INTO tfidf_state (id, state) VALUES (1, ?)",
            (state_json,)
        )

    # ── Public API ────────────────────────────────────────

    def add(
        self,
        user_id: str,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        timestamp: Optional[datetime] = None,
        source_key: Optional[str] = None,
    ) -> int:
        """
        Aggiunge una memoria al DB e all'indice RAM.
        Aggiorna il vocabolario TF-IDF incrementalmente.

        Returns:
            row_id del record inserito.
        """
        if metadata is None:
            metadata = {}
        ts = (timestamp or datetime.now()).isoformat()

        with self._lock:
            # 1. Aggiorna vocabolario
            self._tfidf.partial_fit(content)

            # 2. Encode
            vec = self._tfidf.encode(content)
            blob = _vec_to_blob(vec)

            # 3. Inserisci su DB
            with self._conn() as c:
                if source_key is not None:
                    existing = c.execute("SELECT id FROM memories WHERE user_id=? AND source_key=?",
                                         (user_id, source_key)).fetchone()
                    if existing:
                        self._index_dirty = True
                        return existing[0]
                cursor = c.execute(
                    "INSERT INTO memories (user_id, content, vector_blob, timestamp, metadata, source_key) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, content, blob, ts, json.dumps(metadata), source_key)
                )
                row_id = cursor.lastrowid
                self._save_tfidf_state(cursor)

            # 4. Aggiorna indice RAM
            self._index.append((row_id, user_id, vec))

            # 5. Re-encode tutti i vettori se il vocabolario è cresciuto
            # (Necessario perché un nuovo termine cambia le dimensioni)
            # Lo facciamo in modo lazy: marco come dirty per il prossimo search()
            self._index_dirty = True

            logger.debug(f"[VectorMemory] Added memory id={row_id} for user={user_id}")
            return row_id

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        use_expansion: bool = True,
        allowed_roles=None
    ) -> List[Dict[str, Any]]:
        """
        Ricerca semantica: restituisce le `top_k` memorie più simili alla query.

        Returns:
            Lista di dict: {id, content, score, metadata, timestamp}
        """
        if not query.strip() or top_k <= 0:
            return []

        with self._lock:
            with self._conn() as c:
                signature = c.execute("SELECT COUNT(*), MAX(id) FROM memories").fetchone()
            if self._index_dirty or signature != getattr(self, '_signature', None):
                self._rebuild_index()

            # Filtra per user_id
            user_entries = [(rid, vec) for rid, uid, vec in self._index if uid == user_id]
            if not user_entries:
                return []

            ids = [e[0] for e in user_entries]
            matrix = np.vstack([e[1] for e in user_entries])  # shape: (n, vocab)

            # Genera varianti della query (Query Expansion)
            query_variants = QueryExpander.expand(query) if use_expansion else [query]
            
            # Max-Score Algorithm: Calcola i cosine_scores per ogni variante e prendi il massimo per ogni documento
            max_scores = np.zeros(matrix.shape[0])
            
            for qv in query_variants:
                q_vec = self._tfidf.encode(qv)
                
                # Allinea dimensioni (il vocab potrebbe essere cresciuto)
                if q_vec.shape[0] != matrix.shape[1]:
                    min_dim = min(q_vec.shape[0], matrix.shape[1])
                    q_vec = q_vec[:min_dim]
                    mat_aligned = matrix[:, :min_dim]
                else:
                    mat_aligned = matrix
                    
                # Cosine similarity per questa variante
                scores_variant = mat_aligned @ q_vec
                
                # Element-wise maximum
                max_scores = np.maximum(max_scores, scores_variant)

            # Top-k basato sul Max-Score
            top_indices = np.argsort(max_scores)[::-1]
            if allowed_roles is None:
                top_indices = top_indices[:top_k]

        # Fetch da DB i record selezionati
        selected_ids = [ids[i] for i in top_indices]
        results = []
        try:
            with self._conn() as c:
                placeholders = ",".join("?" * len(selected_ids))
                rows = c.execute(
                    f"SELECT id, content, metadata, timestamp FROM memories WHERE id IN ({placeholders})",
                    selected_ids
                ).fetchall()
                row_map = {r[0]: r for r in rows}

            for i, sid in zip(top_indices, selected_ids):
                if sid in row_map and max_scores[i] > 0:
                    r = row_map[sid]
                    metadata = json.loads(r[2] or '{}')
                    if allowed_roles is not None and (metadata.get('role') not in allowed_roles or metadata.get('is_valid') is False):
                        continue
                    results.append({
                        "id": r[0],
                        "content": r[1],
                        "score": float(max_scores[i]),
                        "metadata": metadata,
                        "timestamp": r[3],
                    })
                    if len(results) >= top_k:
                        break
        except Exception as e:
            logger.error(f"[VectorMemory] Search fetch error: {e}")

        return results

    def count(self, user_id: Optional[str] = None) -> int:
        """Numero di memorie nel DB."""
        with self._conn() as c:
            if user_id:
                return c.execute(
                    "SELECT COUNT(*) FROM memories WHERE user_id=?", (user_id,)
                ).fetchone()[0]
            return c.execute("SELECT COUNT(*) FROM memories").fetchone()[0]

    def clear_user(self, user_id: str) -> None:
        """Rimuove tutte le memorie di un utente."""
        with self._lock:
            with self._conn() as c:
                c.execute("DELETE FROM memories WHERE user_id=?", (user_id,))
            self._index_dirty = True
            self._rebuild_index()

    # ── Internal ──────────────────────────────────────────

    def _rebuild_index(self) -> None:
        """
        Re-encode tutti i vettori usando il vocabolario corrente.
        Chiamato quando il vocab è cresciuto dopo un add().
        Avviene in RAM senza toccare il DB (i blob nel DB vengono
        aggiornati solo al prossimo checkpoint per non bloccare I/O).
        """
        logger.debug(f"[VectorMemory] Rebuilding index (vocab size={self._tfidf.vocab_size()})")
        try:
            with self._conn() as c:
                rows = c.execute(
                    "SELECT id, user_id, content FROM memories"
                ).fetchall()

            self._tfidf = _LightTfidf()
            for _, _, content in rows:
                self._tfidf.partial_fit(content)
            new_index = []
            updated_blobs = []
            for row_id, uid, content in rows:
                vec = self._tfidf.encode(content)
                new_index.append((row_id, uid, vec))
                updated_blobs.append((_vec_to_blob(vec), row_id))

            # Aggiorna i blob su DB in batch
            with self._conn() as c:
                c.executemany(
                    "UPDATE memories SET vector_blob=? WHERE id=?",
                    updated_blobs
                )
                self._save_tfidf_state(c.cursor())

            self._index = new_index
            self._index_dirty = False
            self._signature = (len(rows), max((row[0] for row in rows), default=None))
            logger.info(f"[VectorMemory] Index rebuilt: {len(self._index)} entries")
        except Exception as e:
            logger.error(f"[VectorMemory] Rebuild failed: {e}", exc_info=True)
            raise
