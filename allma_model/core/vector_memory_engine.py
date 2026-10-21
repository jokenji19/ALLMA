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
      vettori sparsi + liste inverse per termine, senza matrice documenti × vocabolario

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
from typing import List, Dict, Any, Optional, Tuple, NamedTuple
import threading
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

        # Both caches scale with observed terms, not all document/term pairs.
        self._index: List[Tuple[int, str, SparseVector]] = []
        self._lexical_index = {}
        self._index_dirty = False
        self._concept_index = {}

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

    def search(
        self,
        user_id: str,
        query: str,
        top_k: int = 5,
        use_expansion: bool = True,
        allowed_roles=None,
        exclude_query_replays=False
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
            user_entries = [(i,rid) for i,(rid,uid,_) in enumerate(self._index) if uid == user_id]
            if not user_entries:
                return []

            ids = [rid for _,rid in user_entries]
            user_positions = np.full(len(self._index),-1,dtype=np.intp)
            user_positions[[i for i,_ in user_entries]] = np.arange(len(ids))

            # Genera varianti della query (Query Expansion)
            query_variants = QueryExpander.expand(query) if use_expansion else [query]
            
            # Max-Score Algorithm: Calcola i cosine_scores per ogni variante e prendi il massimo per ogni documento
            max_scores = np.zeros(len(ids),dtype=np.float32)
            
            for qv in query_variants:
                q_vec = self._tfidf.encode_sparse(qv)
                scores_variant = np.zeros(len(ids),dtype=np.float32)
                for term,weight in zip(q_vec.indices,q_vec.weights):
                    positions,weights = self._lexical_index[int(term)]
                    scoped_positions = user_positions[positions]
                    mask = scoped_positions >= 0
                    # One posting per document/term: no duplicate indices.
                    scores_variant[scoped_positions[mask]] += weights[mask]*weight
                
                # Element-wise maximum
                max_scores = np.maximum(max_scores, scores_variant)

            max_scores = np.clip(max_scores, 0., 1.)
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
                    # A retrieval relevance estimate, not probability or truth.
                    max_scores[positions[rid]] = max(max_scores[positions[rid]],
                        .65 * len(matched)/len(query_concepts))

            # Stable ordering; ties do not select a different source on restart.
            top_indices = np.lexsort((-np.asarray(ids), -max_scores))
            top_indices = [int(i) for i in top_indices if max_scores[i] > 0]

        # Fetch da DB i record selezionati
        selected_ids = [ids[i] for i in top_indices]
        results = []
        try:
            with self._conn() as c:
              # Android SQLite may limit parameters to 999. Filter each batch
              # before counting hits; irrelevant roles cannot consume top_k.
              for start in range(0, len(selected_ids), 256):
                batch = selected_ids[start:start+256]
                placeholders = ",".join("?" * len(batch))
                rows = c.execute(
                    f"SELECT id, content, metadata, timestamp FROM memories WHERE user_id=? AND id IN ({placeholders})",
                    [user_id, *batch]).fetchall()
                row_map = {r[0]: r for r in rows}
                for i, sid in zip(top_indices[start:start+256], batch):
                    if sid not in row_map:
                        continue
                    r = row_map[sid]
                    try:
                        metadata = json.loads(r[2] or '{}')
                    except (ValueError, TypeError):
                        continue
                    if not isinstance(metadata, dict):
                        continue
                    if allowed_roles is not None and (metadata.get('role') not in allowed_roles or metadata.get('is_valid') is False):
                        continue
                    if metadata.get('revoked') is True or metadata.get('status') in ('revoked','superseded'):
                        continue
                    if exclude_query_replays:
                        from allma_model.utils.memory_evidence import is_replayed_question
                        if is_replayed_question(r[1], query):
                            continue
                    results.append({
                        "id": r[0],
                        "content": r[1],
                        "score": float(max_scores[i]),
                        "metadata": metadata,
                        "timestamp": r[3],
                        "retrieval": {
                            'kind':('hybrid' if lexical_scores[i] > 0 else 'concept')
                                   if sid in concept_matches else 'lexical',
                            'concept_matches': sorted(concept_matches.get(sid, ())),
                            'world_truth_verified': False,
                        },
                    })
                    if len(results) >= top_k:
                        break
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

    def release_cache(self):
        """Drop reconstructible RAM state; return the retained record count."""
        with self._lock:
            count = self.count()
            self._index = []
            self._lexical_index = {}
            self._concept_index = {}
            self._tfidf = _LightTfidf()
            self._index_dirty = True
            return count

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
                    "SELECT id, user_id, content FROM memories ORDER BY id"
                ).fetchall()

            tfidf = _LightTfidf()
            for _, _, content in rows:
                tfidf.partial_fit(content)
            new_index = []
            concept_index = {}
            postings = {}
            for row_id, uid, content in rows:
                vec = tfidf.encode_sparse(content)
                position = len(new_index)
                new_index.append((row_id, uid, vec))
                for term,weight in zip(vec.indices,vec.weights):
                    posting = postings.setdefault(int(term),([],[]))
                    posting[0].append(position)
                    posting[1].append(weight)
                for concept in concepts(content):
                    concept_index.setdefault(concept, set()).add(row_id)

            # Content is authoritative; rebuilt vectors are a RAM cache.
            # Do not rewrite every SQLite blob on each search/restart.
            self._index = new_index
            self._tfidf = tfidf
            self._lexical_index = {term:(np.asarray(indices,dtype=np.intp),np.asarray(weights,dtype=np.float32))
                                   for term,(indices,weights) in postings.items()}
            self._concept_index = concept_index
            self._index_dirty = False
            self._signature = (len(rows), max((row[0] for row in rows), default=None))
            logger.info(f"[VectorMemory] Index rebuilt: {len(self._index)} entries")
        except Exception as e:
            logger.error(f"[VectorMemory] Rebuild failed: {e}", exc_info=True)
            raise
