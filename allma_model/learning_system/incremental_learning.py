"""IncrementalLearner - Sistema di apprendimento incrementale per ALLMA."""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import logging
import copy
import json
from pathlib import Path
import numpy as np
from allma_model.utils.text_processing import SimpleTfidf, cosine_similarity
import threading
from functools import wraps
from allma_model.utils.persistence import atomic_write_json, preserve_invalid_file, StateRecoveryRequired


def synchronized(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            return method(self, *args, **kwargs)
    return call


def learning_transaction(method):
    """Copy map roots; mutators copy only the topic/user they actually change."""
    @wraps(method)
    def call(self, *args, **kwargs):
        with self._lock:
            fields = ('knowledge_base', 'knowledge_states', 'user_progress',
                      'success_counters', 'responses_pool')
            previous = {key: getattr(self, key) for key in fields}
            dirty = self._index_dirty
            checkpoint = self.delivery_checkpoint
            for key, value in previous.items():
                setattr(self, key, copy.copy(value))
            try:
                return method(self, *args, **kwargs)
            except Exception:
                for key, value in previous.items():
                    setattr(self, key, value)
                self._index_dirty = dirty
                self.delivery_checkpoint = checkpoint
                raise
    return call


class ConfidenceLevel(Enum):
    """Livelli di confidenza possibili."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3

class FeedbackType(Enum):
    """Tipi di feedback possibili."""
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"

@dataclass
class LearningUnit:
    """Unità di apprendimento."""
    topic: str
    content: str
    source: str
    confidence: ConfidenceLevel
    timestamp: datetime
    metadata: Dict = field(default_factory=dict)

@dataclass
class KnowledgeState:
    """Stato della conoscenza per un topic."""
    topic: str
    content: str
    confidence: ConfidenceLevel
    sources: Set[str]
    feedback_history: List[tuple]
    improvement_areas: Set[str]
    last_updated: datetime
    metadata: Dict = field(default_factory=dict)

class IncrementalLearner:
    """Sistema di apprendimento incrementale."""
    
    def __init__(self, storage_path: str = None):
        """Inizializza il sistema di apprendimento."""
        self.knowledge_base = {}  # topic -> List[LearningUnit]
        self.knowledge_states: Dict[str, KnowledgeState] = {}
        self.user_progress: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "topics": set(),
            "confidence_levels": defaultdict(int),
            "recent_learning": [],
            "improvement_areas": set()
        })
        self.vectorizer = SimpleTfidf()
        self.topic_vectors = {}
        self.success_counters: Dict[str, int] = {}  # topic -> count of successful independent responses
        self._lock = threading.RLock()
        # Pool di varianti per i topic HIGH confidence (raffinato dal Dream)
        self.responses_pool: Dict[str, List[str]] = {}  # topic → [variant1, variant2, ...]
        # Persistenza su disco
        self.storage_path = storage_path
        self.load_error = None
        self._index_dirty = False
        self.delivery_checkpoint = 0
        if self.storage_path:
            self.load_state()
        
    @synchronized
    def save_state(self) -> None:
        """Serializza knowledge_states e success_counters su JSON per la persistenza."""
        if not self.storage_path:
            return
        if self.load_error is not None:
            raise StateRecoveryRequired('Archivio di apprendimento da recuperare prima di salvare') from self.load_error
        try:
            data = {
                "schema_version": 2,
                "delivery_checkpoint": self.delivery_checkpoint,
                "knowledge_base": {t: [{
                    "topic": u.topic, "content": u.content, "source": u.source,
                    "confidence": u.confidence.value, "timestamp": u.timestamp.isoformat(),
                    "metadata": u.metadata} for u in units]
                    for t, units in self.knowledge_base.items()},
                "knowledge_states": {
                    t: {
                        "topic": s.topic,
                        "content": s.content,
                        "confidence": s.confidence.value,
                        "sources": list(s.sources),
                        "last_updated": s.last_updated.isoformat(),
                        "feedback_history": [
                            [v.value if isinstance(v, Enum) else v.isoformat() if isinstance(v, datetime) else v for v in row]
                            for row in s.feedback_history],
                        "improvement_areas": sorted(s.improvement_areas),
                        "metadata": s.metadata
                    }
                    for t, s in self.knowledge_states.items()
                },
                "success_counters": self.success_counters,
                "responses_pool": self.responses_pool,
                "user_progress": {u: {
                    "topics": sorted(p["topics"]),
                    "confidence_levels": {k.value: v for k, v in p["confidence_levels"].items()},
                    "recent_learning": p["recent_learning"],
                    "improvement_areas": sorted(p["improvement_areas"])
                } for u, p in self.user_progress.items()}
            }
            atomic_write_json(self.storage_path, data)
            logging.info(f"[IncrementalLearner] State saved ({len(self.knowledge_states)} topics).")
        except Exception as e:
            logging.warning('[IncrementalLearner] save_state failed: %s', type(e).__name__)
            raise

    @staticmethod
    def _progress_factory():
        return {"topics": set(), "confidence_levels": defaultdict(int),
                "recent_learning": [], "improvement_areas": set()}

    @synchronized
    def load_state(self) -> bool:
        """Validate a complete candidate before changing any live collection."""
        if not self.storage_path:
            return True
        path = Path(self.storage_path)
        if not path.exists():
            return self.load_error is None
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
            checkpoint = data.get('delivery_checkpoint', 0) if isinstance(data, dict) else 0
            if type(checkpoint) is not int or not 0 <= checkpoint < 2**53:
                raise ValueError('Invalid learning checkpoint')
            if (not isinstance(data, dict) or type(data.get('schema_version', 1)) is not int
                    or data.get('schema_version', 1) not in (1, 2)
                    or not isinstance(data.get('knowledge_states'), dict)):
                raise ValueError('Invalid learning schema')
            states, base = {}, {}
            for topic, row in data['knowledge_states'].items():
                if (not isinstance(topic, str) or not topic or not isinstance(row, dict)
                        or row.get('topic') != topic or not isinstance(row.get('content'), str)
                        or not isinstance(row.get('metadata', {}), dict)
                        or type(row.get('confidence')) is not int):
                    raise ValueError('Invalid knowledge state')
                sources = row.get('sources', [])
                areas = row.get('improvement_areas', [])
                if (not isinstance(sources, list) or not isinstance(areas, list)
                        or any(not isinstance(v, str) for v in sources + areas)):
                    raise ValueError('Invalid knowledge sources')
                history = []
                for item in row.get('feedback_history', []):
                    if not isinstance(item, list) or len(item) not in (2, 3):
                        raise ValueError('Invalid feedback history')
                    if len(item) == 3:
                        history.append((FeedbackType(item[0]), item[1], datetime.fromisoformat(item[2])))
                    else:
                        history.append((item[0], datetime.fromisoformat(item[1])))
                states[topic] = KnowledgeState(topic, row['content'], ConfidenceLevel(row['confidence']),
                    set(sources), history, set(areas), datetime.fromisoformat(row['last_updated']), row.get('metadata', {}))
            if 'knowledge_base' in data:
                if not isinstance(data['knowledge_base'], dict):
                    raise ValueError('Invalid knowledge base')
                for topic, rows in data['knowledge_base'].items():
                    if not isinstance(topic, str) or not topic or not isinstance(rows, list):
                        raise ValueError('Invalid knowledge units')
                    units = []
                    for row in rows:
                        if (not isinstance(row, dict) or row.get('topic') != topic
                                or not isinstance(row.get('content'), str) or not isinstance(row.get('source'), str)
                                or not isinstance(row.get('metadata', {}), dict) or type(row.get('confidence')) is not int):
                            raise ValueError('Invalid learning unit')
                        units.append(LearningUnit(topic, row['content'], row['source'], ConfidenceLevel(row['confidence']),
                            datetime.fromisoformat(row['timestamp']), row.get('metadata', {})))
                    base[topic] = units
            else:
                for topic, state in states.items():
                    base[topic] = [LearningUnit(topic, state.content, next(iter(sorted(state.sources)), 'legacy'),
                        state.confidence, state.last_updated, dict(state.metadata))]
            progress = defaultdict(self._progress_factory)
            for user, row in data.get('user_progress', {}).items():
                if not isinstance(user, str) or not isinstance(row, dict):
                    raise ValueError('Invalid user progress')
                value = progress[user]
                for key in ('topics', 'improvement_areas'):
                    entries = row.get(key, [])
                    if not isinstance(entries, list) or any(not isinstance(v, str) for v in entries):
                        raise ValueError('Invalid progress topics')
                    value[key] = set(entries)
                recent = row.get('recent_learning', [])
                if not isinstance(recent, list) or any(not isinstance(v, dict) or not all(k in v for k in ('topic','confidence','timestamp')) for v in recent):
                    raise ValueError('Invalid recent learning')
                value['recent_learning'] = recent
                for key, count in row.get('confidence_levels', {}).items():
                    if type(count) is not int or count < 0:
                        raise ValueError('Invalid confidence count')
                    value['confidence_levels'][ConfidenceLevel(int(key))] = count
            counters, pools = data.get('success_counters', {}), data.get('responses_pool', {})
            if (not isinstance(counters, dict) or any(not isinstance(k, str) or type(v) is not int or v < 0 for k,v in counters.items())
                    or not isinstance(pools, dict) or any(not isinstance(k,str) or not isinstance(v,list)
                       or any(not isinstance(t,str) for t in v) for k,v in pools.items())):
                raise ValueError('Invalid learning counters or variants')
        except (OSError, ValueError, TypeError, KeyError, AttributeError) as error:
            self.load_error = error
            try:
                preserve_invalid_file(path)
            except OSError:
                logging.warning('[IncrementalLearner] Cannot preserve invalid archive')
            logging.warning('[IncrementalLearner] Archive unavailable: %s', type(error).__name__)
            return False
        self.knowledge_states, self.knowledge_base, self.user_progress = states, base, progress
        self.success_counters, self.responses_pool = counters, pools
        self.delivery_checkpoint = checkpoint
        self.topic_vectors = {}
        self.vectorizer = SimpleTfidf()
        self._index_dirty = True
        self.load_error = None
        return True

    def _ensure_index(self):
        if not self._index_dirty:
            return
        topics = list(self.knowledge_base)
        docs = [' '.join([t] + [u.content for u in self.knowledge_base[t]]) for t in topics]
        vectorizer = SimpleTfidf()
        vectors = vectorizer.fit_transform(docs) if docs else []
        self.vectorizer, self.topic_vectors = vectorizer, dict(zip(topics, vectors))
        self._index_dirty = False

    @learning_transaction
    def add_response_variants(self, topic: str, variants: List[str]) -> None:
        """Aggiunge varianti di risposta per un topic (usato dal Dream)."""
        topic = topic.lower().strip()
        existing = self.responses_pool.get(topic, [])
        # Mantieni originale + nuove varianti, max 5
        merged = list(dict.fromkeys(existing + variants))[:5]
        self.responses_pool[topic] = merged
        self.save_state()
        logging.info(f"[responses_pool] Topic '{topic}': {len(merged)} varianti disponibili.")

    def get_response_variant(self, topic: str) -> Optional[str]:
        """Restituisce una variante casuale per un topic (fast-path variabile)."""
        import random
        topic = topic.lower().strip()
        pool = self.responses_pool.get(topic, [])
        if pool:
            return random.choice(pool)
        # fallback: usa il content dal knowledge_state
        state = self.knowledge_states.get(topic)
        return state.content if state else None

    @learning_transaction
    def add_learning_unit(
        self,
        unit: LearningUnit
    ) -> bool:
        """
        Aggiunge una nuova unità di apprendimento.
        
        Args:
            unit: Unità di apprendimento
            
        Returns:
            True se l'aggiunta è riuscita
        """
        with self._lock:
            if not unit.topic.strip() or not unit.content.strip():
                return False
                
            self.knowledge_base[unit.topic] = self.knowledge_base.get(unit.topic, []) + [copy.deepcopy(unit)]
            
            # Aggiorna lo stato della conoscenza
            self._update_knowledge_state(unit)
            
            self._index_dirty = True

            self.save_state()
            return True
        
    @learning_transaction
    def integrate_feedback(
        self,
        topic: str,
        feedback_type: FeedbackType,
        message: str,
        metadata: Optional[Dict] = None
    ) -> None:
        """
        Integra il feedback nel sistema di apprendimento.
        
        Args:
            topic: Argomento del feedback
            feedback_type: Tipo di feedback
            message: Messaggio di feedback
            metadata: Metadati aggiuntivi
        """
        if topic not in self.knowledge_states:
            return
            
        state = copy.deepcopy(self.knowledge_states[topic])
        self.knowledge_states[topic] = state

        # Aggiorna la storia del feedback
        state.feedback_history.append(
            (feedback_type, message, datetime.now())
        )
        
        # Aggiorna la confidenza
        if feedback_type == FeedbackType.POSITIVE:
            if state.confidence != ConfidenceLevel.HIGH:
                state.confidence = ConfidenceLevel(state.confidence.value + 1)
        elif feedback_type == FeedbackType.NEGATIVE:
            if state.confidence != ConfidenceLevel.LOW:
                state.confidence = ConfidenceLevel(state.confidence.value - 1)
                
        # Identifica aree di miglioramento
        if feedback_type == FeedbackType.NEGATIVE:
            keywords = ["esempi", "spiegazione", "dettagli", "chiarezza"]
            for keyword in keywords:
                if keyword in message.lower():
                    state.improvement_areas.add(keyword)
                    
        state.last_updated = datetime.now()
        
        # Aggiorna i metadati
        if metadata:
            state.metadata.update(metadata)
            
        self.save_state()

    def get_knowledge_state(
        self,
        topic: str
    ) -> Optional[KnowledgeState]:
        """
        Recupera lo stato della conoscenza per un topic.
        
        Args:
            topic: Topic da recuperare
            
        Returns:
            Stato della conoscenza o None se non trovato
        """
        return self.knowledge_states.get(topic)
    
    @learning_transaction
    def record_success(self, topic: str, threshold: int = 3) -> bool:
        """
        Registra un successo per una risposta indipendente e aumenta la confidenza
        dopo N successi consecutivi.
        
        Args:
            topic: Topic della risposta indipendente
            threshold: Numero di successi necessari per aumentare confidenza (default: 3)
            
        Returns:
            True se la confidenza è stata aumentata, False altrimenti
        """
        with self._lock:
            # Incrementa il contatore
            self.success_counters[topic] = self.success_counters.get(topic, 0) + 1
            
            # Controlla se è tempo di aumentare la confidenza
            if self.success_counters[topic] >= threshold:
                # Reset il contatore
                self.success_counters[topic] = 0
                
                # Cerca la knowledge state per questo topic
                if topic in self.knowledge_states:
                    state = copy.deepcopy(self.knowledge_states[topic])
                    self.knowledge_states[topic] = state
                    # Aumenta la confidenza se non è già al massimo
                    if state.confidence != ConfidenceLevel.HIGH:
                        old_confidence = state.confidence
                        state.confidence = ConfidenceLevel(min(state.confidence.value + 1, 3))
                        logging.info(f"🎓 EVOLUZIONE: Topic '{topic}' confidenza {old_confidence.name} → {state.confidence.name}")
                        # Persisti subito
                        self.save_state()
                        return True
            
            self.save_state()
            return False
        
    @synchronized
    def find_related_knowledge(
        self,
        query: str,
        threshold: float = 0.3,
        user_id: Optional[str] = None
    ) -> List[LearningUnit]:
        """
        Trova conoscenza correlata a una query.
        
        Args:
            query: Query di ricerca
            threshold: Soglia minima di similarità
            
        Returns:
            Lista di unità di apprendimento correlate
        """
        if not query.strip():
            return []
        self._ensure_index()
        if not self.topic_vectors:
            return []
            
        related_units = []
        try:
            query_vectors = self.vectorizer.transform([query])
            query_vector = (query_vectors.toarray() if hasattr(query_vectors, "toarray") else query_vectors)[0]
            for topic, vector in self.topic_vectors.items():
                similarity = cosine_similarity([query_vector], [vector])[0][0]
                if similarity >= threshold:
                    units = [unit for unit in self.knowledge_base[topic]
                             if self._belongs_to_user(unit, user_id)]
                    if units:
                        related_units.append(max(
                            units,
                            key=lambda u: u.timestamp
                        ))
            if related_units:
                return sorted(
                    related_units,
                    key=lambda u: cosine_similarity(
                        [query_vector],
                        [self.topic_vectors[u.topic]]
                    )[0][0],
                    reverse=True
                )
        except Exception as e:
            print(f"Errore nella ricerca: {e}")

        query_tokens = set(query.lower().split())
        for topic, units in self.knowledge_base.items():
            units = [unit for unit in units if self._belongs_to_user(unit, user_id)]
            topic_tokens = set(topic.lower().split())
            if query_tokens & topic_tokens:
                if units:
                    related_units.append(max(
                        units,
                        key=lambda u: u.timestamp
                    ))

        return related_units
            
    def _update_knowledge_state(
        self,
        unit: LearningUnit
    ) -> None:
        """
        Aggiorna lo stato della conoscenza con una nuova unità.
        
        Args:
            unit: Nuova unità di apprendimento
        """
        if unit.topic not in self.knowledge_states:
            # Crea nuovo stato
            self.knowledge_states[unit.topic] = KnowledgeState(
                topic=unit.topic,
                content=unit.content,
                confidence=unit.confidence,
                sources={unit.source},
                feedback_history=[],
                improvement_areas=set(),
                last_updated=unit.timestamp,
                metadata=unit.metadata
            )
        else:
            # Aggiorna stato esistente
            state = copy.deepcopy(self.knowledge_states[unit.topic])
            self.knowledge_states[unit.topic] = state

            # Aggiorna solo se la confidenza è maggiore
            if unit.confidence.value > state.confidence.value:
                state.content = unit.content
                state.confidence = unit.confidence
                
            state.sources.add(unit.source)
            state.last_updated = unit.timestamp
            
    @learning_transaction
    def learn_from_interaction(self, interaction: Dict[str, str], user_id: str, *, delivery_sequence=None) -> Optional[LearningUnit]:
        """
        Apprende dall'interazione con l'utente
        
        Args:
            interaction: Dizionario contenente input, response e feedback
            user_id: ID dell'utente
            
        Returns:
            The created LearningUnit or None
        """
        if delivery_sequence is not None and delivery_sequence <= self.delivery_checkpoint:
            return None
        input_text = interaction.get('input', '')
        response = interaction.get('response', '')
        # Missing/invalid provenance must never promote generated text to a
        # verified fact. Only an explicit host verification admits the answer.
        unverified = interaction.get('response_verified') is not True
        if unverified:
            response = input_text  # attributed user report, never the model's invention
        feedback = interaction.get('feedback', '')
        
        # Usa il topic fornito dal chiamante (già estratto con topic_extractor)
        # Fallback: prima parola significativa dal testo
        topic = interaction.get('topic') or ''
        if not topic:
            words = input_text.lower().split()
            topic = next((word for word in words 
                         if len(word) > 3 and word not in {'want', 'need', 'help', 'please', 'could', 'would'}), 
                        'general')
        topic = topic.lower().strip()
        
        # Crea una nuova unità di apprendimento
        unit = LearningUnit(
            topic=topic,
            content=f"Input: {input_text}\nResponse: {response}",
            source=f"user_{user_id}",
            confidence=ConfidenceLevel.LOW if unverified else ConfidenceLevel.MEDIUM,
            timestamp=datetime.now(),
            metadata={
                'feedback': feedback,
                'user_id': user_id,
                'original_input': input_text,
                'source_kind': 'user_statement' if unverified else 'interaction',
                'knowledge_verified': not unverified
            }
        )
        
        # Aggiunge l'unità alla knowledge base
        self.knowledge_base[topic] = self.knowledge_base.get(topic, []) + [unit]
        self._index_dirty = True
        
        # Aggiorna lo stato della conoscenza
        if topic not in self.knowledge_states:
            self.knowledge_states[topic] = KnowledgeState(
                topic=topic,
                content=response,
                confidence=ConfidenceLevel.LOW if unverified else ConfidenceLevel.MEDIUM,
                sources={f"user_{user_id}"},
                feedback_history=[(feedback, datetime.now())],
                improvement_areas=set(),
                last_updated=datetime.now(),
                metadata={
                    'feedback': feedback,
                    'user_id': user_id,
                    'original_input': input_text,
                'source_kind': 'user_statement' if unverified else 'interaction',
                'knowledge_verified': not unverified
                }
            )
        else:
            state = copy.deepcopy(self.knowledge_states[topic])
            self.knowledge_states[topic] = state
            state.content = response
            state.sources.add(f"user_{user_id}")
            state.feedback_history.append((feedback, datetime.now()))
            state.last_updated = datetime.now()
            state.metadata.update({
                'feedback': feedback,
                'user_id': user_id,
                'original_input': input_text,
                'source_kind': 'user_statement' if unverified else 'interaction',
                'knowledge_verified': not unverified
            })
            
        # Aggiorna il progresso dell'utente
        progress = copy.deepcopy(self.user_progress[user_id])
        self.user_progress[user_id] = progress
        progress["confidence_levels"][unit.confidence] += 1
        progress["topics"].add(topic)
        progress["recent_learning"].append({
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "confidence": unit.confidence.value
        })
        
        if delivery_sequence is not None:
            self.delivery_checkpoint = delivery_sequence
        self.save_state()
        return unit

    def get_knowledge(self, topic: str) -> List[Dict[str, Any]]:
        """
        Recupera la conoscenza su un determinato topic
        
        Args:
            topic: Il topic su cui recuperare la conoscenza
            
        Returns:
            List[Dict[str, Any]]: Lista di unità di conoscenza
        """
        if topic not in self.knowledge_base:
            return []
            
        units = self.knowledge_base[topic]
        return [
            {
                'topic': unit.topic,
                'content': unit.content,
                'source': unit.source,
                'confidence': unit.confidence.value,
                'timestamp': unit.timestamp.isoformat(),
                'metadata': unit.metadata
            }
            for unit in units
        ]

    @staticmethod
    def _belongs_to_user(unit, user_id):
        if user_id is None:
            return True  # Explicit legacy/offline API; core always supplies owner.
        owner = (unit.metadata or {}).get('user_id')
        if owner is None and unit.source.startswith('user_'):
            owner = unit.source[5:]
        return owner == user_id

    @synchronized
    def get_knowledge_by_topic(self, topic: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Recupera la conoscenza per un determinato topic.
        
        Args:
            topic: Topic di cui recuperare la conoscenza
            
        Returns:
            List[Dict[str, Any]]: Lista di unità di conoscenza
        """
        knowledge = []
        topic = topic.lower()
        
        # Cerca conoscenza diretta
        if topic in self.knowledge_base:
            for unit in self.knowledge_base[topic]:
                if not self._belongs_to_user(unit, user_id):
                    continue
                knowledge.append({
                    'topic': unit.topic,
                    'content': unit.content,
                    'confidence': unit.confidence.value,
                    'timestamp': unit.timestamp.isoformat(),
                    'metadata': unit.metadata
                })
                
        # Se non trova nulla, cerca nei topic simili
        if not knowledge:
            for t, units in self.knowledge_base.items():
                similarity = self._calculate_similarity(topic, t)
                if similarity > 0.5:  # Soglia di similarità più alta per topic diretti
                    for unit in units:
                        if not self._belongs_to_user(unit, user_id):
                            continue
                        knowledge.append({
                            'topic': unit.topic,
                            'content': unit.content,
                            'confidence': unit.confidence.value,
                            'timestamp': unit.timestamp.isoformat(),
                            'metadata': unit.metadata
                        })
                    
        return knowledge

    def _calculate_similarity(self, topic1: str, topic2: str) -> float:
        """
        Calcola la similarità tra due topic
        
        Args:
            topic1: Primo topic
            topic2: Secondo topic
            
        Returns:
            Similarità tra i due topic
        """
        # Implementazione della funzione di similarità
        # In questo caso, utilizziamo una semplice similarità di stringhe
        similarity = len(set(topic1.lower().split()) & set(topic2.lower().split())) / len(set(topic1.lower().split()) | set(topic2.lower().split()))
        return similarity

    def get_learning_progress(self, user_id: str) -> Dict[str, Any]:
        """
        Ottiene il progresso dell'apprendimento per un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict con il progresso dell'apprendimento
        """
        if user_id not in self.user_progress:
            return {
                "topics": [],
                "confidence_levels": {
                    "low": 0,
                    "medium": 0,
                    "high": 0
                },
                "recent_learning": [],
                "improvement_areas": []
            }
            
        progress = self.user_progress[user_id]
        
        # Converti i set in liste per la serializzazione JSON
        return {
            "topics": list(progress["topics"]),
            "confidence_levels": {
                "low": progress["confidence_levels"][ConfidenceLevel.LOW],
                "medium": progress["confidence_levels"][ConfidenceLevel.MEDIUM],
                "high": progress["confidence_levels"][ConfidenceLevel.HIGH]
            },
            "recent_learning": [
                {
                    "topic": item["topic"],
                    "confidence": item["confidence"],
                    "timestamp": item["timestamp"]
                }
                for item in progress["recent_learning"][-5:]  # Ultimi 5 elementi
            ],
            "improvement_areas": list(progress["improvement_areas"])
        }
