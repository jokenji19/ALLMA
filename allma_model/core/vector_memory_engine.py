"""
VectorMemoryEngine — ALLMA V6 Sprint 3
======================================

Vector search engine basato su SQLite nativo + TF-IDF persistente.

Perché NON FAISS / sqlite-vss:
    - Nessuno dei due compila su Android arm64 senza toolchain NDK custom.
    - SQLite è già disponibile su Android, zero dipendenze extra.

Architettura:
    SQLite DB (allma_vectors.db)
      └─ tabella "memories": id, user_id, content, vector_blob, timestamp, metadata
    
    RAM Index (self._index):
      vettori sparsi + liste inverse per termine, senza matrice documenti × vocabolario

Consistenza:
    Il testo SQLite è la fonte autorevole. Il vocabolario e tutti i vettori
    vengono ricostruiti al riavvio e dopo modifiche o cancellazioni. Gli
    inserimenti aggiungono solo le nuove righe; i punteggi usano le frequenze
    aggiornate del corpus. SQLite resta la fonte autorevole.

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
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
import threading
from contextlib import contextmanager
from allma_model.utils.memory_concepts import words, concepts

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
            
        return list(dict.fromkeys(variants))



# ─────────────────────────────────────────────────────────
#  TF-IDF leggiero (drop-in replacement di SimpleTfidf)
# ─────────────────────────────────────────────────────────

class SparseVector(NamedTuple):
    indices: np.ndarray
    weights: np.ndarray

    @property
    def nbytes(self):
        return self.indices.nbytes + self.weights.nbytes


class _LightTfidf:
    """
    TF-IDF incrementale: supporta .partial_fit(doc) per aggiornare
    il vocabolario senza dover riprocessare tutto il corpus.
    """
    STOP_WORDS = frozenset({
        'a','ad','al','alla','alle','allo','ai','agli','all','con','da','dal','dalla',
        'dalle','di','del','della','dei','degli','delle','dell','e','ed','è','il','lo',
        'la','le','gli','i','in','nel','nella','nelle','nello','nell','ne','per','su',
        'un','uno','una','che','chi','cosa','come','dove','quale','quali','quando',
        'mi','ti','ci','si','io','tu','ho','hai','ha','sono','era','sia','the',
        'an','is','are','on','of','to','my','where','what','which',
    })

    def __init__(self):
        self.vocab: Dict[str, int] = {}   # word -> dim index
        self.df: Dict[str, int] = {}      # word -> doc_frequency
        self.n_docs: int = 0

    def _tokenize(self, text: str) -> List[str]:
        # Discard grammatical glue, never identifiers, names or domain words.
        return [word for word in words(text) if word not in self.STOP_WORDS]

    def encode(self, text: str) -> np.ndarray:
        """Restituisce il vettore TF-IDF per 'text' usando il vocabolario corrente."""
        if not self.vocab:
            return np.zeros(1, dtype=np.float32)
        sparse = self.encode_sparse(text)
        vec = np.zeros(len(self.vocab), dtype=np.float32)
        vec[sparse.indices] = sparse.weights
        return vec

    def encode_sparse(self, text: str) -> SparseVector:
        """Same normalized TF-IDF, allocating only terms present in the text."""
        tokens = self._tokenize(text)
        counts = Counter(tokens)
        pairs = []
        for word, cnt in counts.items():
            if word in self.vocab:
                idf = 1.0 + math.log((self.n_docs + 1) / (self.df.get(word, 0) + 1))
                pairs.append((self.vocab[word], cnt * idf))
        pairs.sort()
        indices = np.fromiter((i for i,_ in pairs),dtype=np.int32,count=len(pairs))
        weights = np.fromiter((value for _,value in pairs),dtype=np.float32,count=len(pairs))
        norm = np.linalg.norm(weights)
        if norm > 0:
            weights /= norm
        return SparseVector(indices,weights)

    def partial_fit(self, text: str) -> None:
        """Aggiorna vocabolario e DF con un nuovo documento."""
        tokens = set(self._tokenize(text))
        for word in tokens:
            if word not in self.vocab:
                self.vocab[word] = len(self.vocab)
            self.df[word] = self.df.get(word, 0) + 1
        self.n_docs += 1

    def encode_counts(self, text):
        counts = Counter(self._tokenize(text))
        pairs = sorted((self.vocab[word], count) for word,count in counts.items() if word in self.vocab)
        return SparseVector(np.fromiter((i for i,_ in pairs),dtype=np.int32,count=len(pairs)),
                            np.fromiter((n for _,n in pairs),dtype=np.float32,count=len(pairs)))

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

    def __init__(self, db_path: str = "data/allma_vectors.db", *, defer_index=False):
        self.db_path = db_path
        self._lock = threading.Lock()
        self._tfidf = _LightTfidf()

        # Both caches scale with observed terms, not all document/term pairs.
        self._index: List[Tuple[int, str, SparseVector]] = []
        self._lexical_index = {}
        self._index_dirty = False
        self._concept_index = {}
        self._cache_loaded = False
        self._revision = None
        self._destructive_revision = None
        self._last_id = 0

        self._init_db()
        if defer_index:
            from .incremental_vector_index import IncrementalVectorIndex
            self._publish_index(IncrementalVectorIndex(_LightTfidf))
        else:
            self._load_state()

    # ── DB setup ──────────────────────────────────────────

    @contextmanager
    def _conn(self):
        connection = sqlite3.connect(self.db_path, check_same_thread=False)
        try:
            with connection:
                yield connection
        finally:
            connection.close()

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
            c.execute("CREATE INDEX IF NOT EXISTS idx_memory_source_key ON memories(source_key)")
            c.executescript('''
                CREATE TABLE IF NOT EXISTS allma_index_revision (
                    singleton INTEGER PRIMARY KEY CHECK(singleton=1),
                    revision INTEGER NOT NULL, destructive INTEGER NOT NULL, total INTEGER NOT NULL);
                INSERT OR IGNORE INTO allma_index_revision
                    SELECT 1,0,0,COUNT(*) FROM memories;
                CREATE TRIGGER IF NOT EXISTS allma_index_insert AFTER INSERT ON memories BEGIN
                    UPDATE allma_index_revision SET revision=revision+1,total=total+1 WHERE singleton=1;
                END;
                CREATE TRIGGER IF NOT EXISTS allma_index_update AFTER UPDATE ON memories BEGIN
                    UPDATE allma_index_revision SET revision=revision+1,destructive=destructive+1 WHERE singleton=1;
                END;
                CREATE TRIGGER IF NOT EXISTS allma_index_delete AFTER DELETE ON memories BEGIN
                    UPDATE allma_index_revision SET revision=revision+1,destructive=destructive+1,total=total-1 WHERE singleton=1;
                END;
            ''')

    def _load_state(self) -> None:
        # Content is authoritative: old releases persisted incompatible vectors.
        self._rebuild_index()

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
            # Check idempotence before touching vocabulary or its persisted cache.
            with self._conn() as c:
                if source_key is not None:
                    existing = c.execute("SELECT id FROM memories WHERE user_id=? AND source_key=?",
                                         (user_id, source_key)).fetchone()
                    if existing:
                        return existing[0]
                cursor = c.execute(
                    "INSERT INTO memories (user_id, content, vector_blob, timestamp, metadata, source_key) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (user_id, content, b'', ts, json.dumps(metadata), source_key)
                )
                row_id = cursor.lastrowid
            # SQLite text is authoritative. Old dense blobs/state remain readable
            # for compatibility, but are not copied again at every insertion.
            # Publish cache invalidation only after the transaction succeeded.
            self._index_dirty = True

            logger.debug(f"[VectorMemory] Added memory id={row_id} for user={user_id}")
            return row_id

    def add_many(self, records):
        """Reconcile attributed sources in one transaction without per-row opens.

        The generator is consumed inside the transaction: a malformed record or
        interrupted batch cannot publish half the startup projection. Existing
        sources keep their identifiers; unchanged rows do not dirty the index.
        """
        def values():
            for record in records:
                yield (record['user_id'],record['content'],b'',
                       record['timestamp'].isoformat(),json.dumps(record['metadata']),record['source_key'])
        with self._lock:
            with self._conn() as connection:
                cursor=connection.executemany('''
                    INSERT INTO memories(user_id,content,vector_blob,timestamp,metadata,source_key)
                    VALUES(?,?,?,?,?,?) ON CONFLICT(user_id,source_key) DO UPDATE SET
                        content=excluded.content, timestamp=excluded.timestamp,
                        metadata=excluded.metadata, vector_blob=excluded.vector_blob
                    WHERE memories.content!=excluded.content OR memories.timestamp!=excluded.timestamp
                        OR memories.metadata!=excluded.metadata
                ''',values())
                changed=cursor.rowcount
            if changed:self._index_dirty=True
        return changed

    def sync_history(self,records,touched=None,*,default=None,guard=None):
        from .history_projection import reconcile
        return reconcile(self,records,touched,default=default,guard=guard)

    def search(self, user_id, query, top_k=5, use_expansion=True,
               allowed_roles=None, exclude_query_replays=False):
        if not query.strip() or top_k <= 0:
            return []
        # Revision, scores and selected sources share one SQLite read snapshot.
        with self._lock, self._conn() as connection:
            connection.execute('BEGIN')
            self._refresh_index(connection)
            return self._search_snapshot(connection,user_id,query,top_k,
                use_expansion,allowed_roles,exclude_query_replays)

    def _search_snapshot(self, connection, user_id, query, top_k,
                         use_expansion, allowed_roles, exclude_query_replays):
        variants = QueryExpander.expand(query) if use_expansion else [query]
        ids, max_scores = self._incremental.score(user_id, variants)
        if not ids:
            return []
        lexical_scores = max_scores.copy()
        query_concepts = concepts(query) if use_expansion else frozenset()
        concept_matches = {}
        if query_concepts:
            positions = {rid:i for i,rid in enumerate(ids)}
            for concept in query_concepts:
                for rid in self._concept_index.get(concept, ()):
                    if rid in positions:
                        concept_matches.setdefault(rid, set()).add(concept)
            for rid, matched in concept_matches.items():
                max_scores[positions[rid]] = max(max_scores[positions[rid]],
                    .65 * len(matched)/len(query_concepts))
        top_indices = np.lexsort((-np.asarray(ids), -max_scores))
        top_indices = [int(i) for i in top_indices if max_scores[i] > 0]
        selected_ids = [ids[i] for i in top_indices]
        results = []
        for start in range(0, len(selected_ids), 256):
            batch = selected_ids[start:start+256]
            placeholders = ','.join('?' * len(batch))
            rows = connection.execute(
                f'SELECT id, content, metadata, timestamp, source_key FROM memories WHERE user_id=? AND id IN ({placeholders})',
                [user_id,*batch]).fetchall()
            row_map = {row[0]:row for row in rows}
            for i, identifier in zip(top_indices[start:start+256],batch):
                row = row_map.get(identifier)
                if row is None:
                    continue
                try:
                    metadata = json.loads(row[2] or '{}')
                except (ValueError, TypeError):
                    continue
                if not isinstance(metadata,dict):
                    continue
                if allowed_roles is not None and (metadata.get('role') not in allowed_roles or metadata.get('is_valid') is False):
                    continue
                if metadata.get('revoked') is True or metadata.get('status') in ('revoked','superseded'):
                    continue
                if exclude_query_replays:
                    from allma_model.utils.memory_evidence import is_replayed_question
                    if is_replayed_question(row[1],query):
                        continue
                results.append({'id':row[0], 'content':row[1], 'score':float(max_scores[i]),
                    'metadata':metadata, 'timestamp':row[3], 'source_key':row[4], 'retrieval':{
                        'kind':('hybrid' if lexical_scores[i] > 0 else 'concept')
                               if identifier in concept_matches else 'lexical',
                        'concept_matches':sorted(concept_matches.get(identifier,())),
                        'world_truth_verified':False}})
                if len(results)>=top_k:
                    return results
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

    def release_cache(self):
        """Discard derived state; source records remain in SQLite."""
        with self._lock:
            count = self.count()
            from .incremental_vector_index import IncrementalVectorIndex
            self._publish_index(IncrementalVectorIndex(_LightTfidf))
            self._cache_loaded = False
            self._index_dirty = True
            return count

    def _publish_index(self, index):
        self._incremental = index
        self._index = index.entries
        self._tfidf = index.tfidf
        self._lexical_index = index.postings
        self._concept_index = index.concepts

    def _refresh_index(self, connection):
        revision, destructive, total = connection.execute(
            'SELECT revision,destructive,total FROM allma_index_revision WHERE singleton=1').fetchone()
        if not self._cache_loaded or destructive != self._destructive_revision:
            self._rebuild_index(connection)
            return
        if revision == self._revision:
            self._index_dirty = False
            return
        rows = connection.execute('SELECT id,user_id,content FROM memories WHERE id>? ORDER BY id',
                                  (self._last_id,)).fetchall()
        if len(self._index)+len(rows) != total:
            self._rebuild_index(connection)
            return
        self._cache_loaded = False
        self._incremental.append(rows)
        self._last_id = rows[-1][0] if rows else self._last_id
        self._revision = revision
        self._signature = (total,self._last_id or None)
        self._index_dirty = False
        self._cache_loaded = True

    def _rebuild_index(self, connection=None):
        """Full recovery only at startup, after deletion/edit or cache release."""
        if connection is None:
            with self._conn() as reader:
                reader.execute('BEGIN')
                return self._rebuild_index_snapshot(reader)
        return self._rebuild_index_snapshot(connection)

    def _rebuild_index_snapshot(self, connection):
        from .incremental_vector_index import IncrementalVectorIndex
        self._cache_loaded = False
        revision, destructive, total = connection.execute(
            'SELECT revision,destructive,total FROM allma_index_revision WHERE singleton=1').fetchone()
        rows = connection.execute('SELECT id,user_id,content FROM memories ORDER BY id').fetchall()
        index = IncrementalVectorIndex(_LightTfidf)
        index.append(rows)
        self._publish_index(index)
        self._last_id = rows[-1][0] if rows else 0
        self._revision, self._destructive_revision = revision, destructive
        self._signature = (total,self._last_id or None)
        self._index_dirty = False
        self._cache_loaded = True
        logger.info('[VectorMemory] Index rebuilt: %d entries',len(rows))
