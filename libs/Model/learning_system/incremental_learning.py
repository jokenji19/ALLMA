"""IncrementalLearner - Sistema di apprendimento incrementale per ALLMA."""

from typing import Dict, List, Optional, Set, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import numpy as np
# from sklearn.feature_extraction.text import TfidfVectorizer
# from sklearn.metrics.pairwise import cosine_similarity
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

    def transform(self, documents):
        vectors = []
        for doc in documents:
            words = doc.lower().split()
            counts = Counter(words)
            vector = [counts[word] * self.idf.get(word, 0) for word in self.vocab]
            vectors.append(vector)
        return np.array(vectors)

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return np.array([[0.0]])
    return np.array([[np.dot(v1, v2.T) / (norm1 * norm2)]])
import threading

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
    
    def __init__(self):
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
        self._lock = threading.Lock()
        
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
                
            if unit.topic not in self.knowledge_base:
                self.knowledge_base[unit.topic] = []
            self.knowledge_base[unit.topic].append(unit)
            
            # Aggiorna lo stato della conoscenza
            self._update_knowledge_state(unit)
            
            # Aggiorna i vettori del topic
            try:
                text = f"{unit.topic} {unit.content}"
                if len(self.topic_vectors) == 0:
                    vectors = self.vectorizer.fit_transform([text])
                else:
                    vectors = self.vectorizer.transform([text])
                self.topic_vectors[unit.topic] = vectors.toarray()[0]
            except Exception as e:
                print(f"Errore nel calcolo embeddings: {e}")
                
            return True
        
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
            
        state = self.knowledge_states[topic]
        
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
                    state = self.knowledge_states[topic]
                    # Aumenta la confidenza se non è già al massimo
                    if state.confidence != ConfidenceLevel.HIGH:
                        old_confidence = state.confidence
                        state.confidence = ConfidenceLevel(min(state.confidence.value + 1, 3))
                        logging.info(f"🎓 EVOLUZIONE: Topic '{topic}' confidenza {old_confidence.name} → {state.confidence.name}")
                        return True
            
            return False
        
    def find_related_knowledge(
        self,
        query: str,
        threshold: float = 0.3
    ) -> List[LearningUnit]:
        """
        Trova conoscenza correlata a una query.
        
        Args:
            query: Query di ricerca
            threshold: Soglia minima di similarità
            
        Returns:
            Lista di unità di apprendimento correlate
        """
        if not query.strip() or len(self.topic_vectors) == 0:
            return []
            
        try:
            # Calcola embedding della query
            query_vector = self.vectorizer.transform([query]).toarray()[0]
            
            # Trova topic correlati
            related_units = []
            for topic, vector in self.topic_vectors.items():
                similarity = cosine_similarity([query_vector], [vector])[0][0]
                if similarity >= threshold:
                    # Prendi l'unità più recente per il topic
                    units = self.knowledge_base[topic]
                    if units:
                        related_units.append(max(
                            units,
                            key=lambda u: u.timestamp
                        ))
                        
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
            return []
            
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
            state = self.knowledge_states[unit.topic]
            
            # Aggiorna solo se la confidenza è maggiore
            if unit.confidence.value > state.confidence.value:
                state.content = unit.content
                state.confidence = unit.confidence
                
            state.sources.add(unit.source)
            state.last_updated = unit.timestamp
            
    def learn_from_interaction(self, interaction: Dict[str, str], user_id: str) -> None:
        """
        Apprende dall'interazione con l'utente
        
        Args:
            interaction: Dizionario contenente input, response e feedback
            user_id: ID dell'utente
        """
        input_text = interaction.get('input', '')
        response = interaction.get('response', '')
        feedback = interaction.get('feedback', '')
        
        # Estrai il topic dal testo
        # In questo caso semplice, prendiamo la prima parola significativa
        words = input_text.lower().split()
        topic = next((word for word in words 
                     if len(word) > 3 and word not in {'want', 'need', 'help', 'please', 'could', 'would'}), 
                    'general')
        
        # Crea una nuova unità di apprendimento
        unit = LearningUnit(
            topic=topic,
            content=f"Input: {input_text}\nResponse: {response}",
            source=f"user_{user_id}",
            confidence=ConfidenceLevel.MEDIUM,
            timestamp=datetime.now(),
            metadata={
                'feedback': feedback,
                'user_id': user_id,
                'original_input': input_text
            }
        )
        
        # Aggiunge l'unità alla knowledge base
        if topic not in self.knowledge_base:
            self.knowledge_base[topic] = []
        self.knowledge_base[topic].append(unit)
        
        # Aggiorna lo stato della conoscenza
        if topic not in self.knowledge_states:
            self.knowledge_states[topic] = KnowledgeState(
                topic=topic,
                content=response,
                confidence=ConfidenceLevel.MEDIUM,
                sources={f"user_{user_id}"},
                feedback_history=[(feedback, datetime.now())],
                improvement_areas=set(),
                last_updated=datetime.now(),
                metadata={
                    'feedback': feedback,
                    'user_id': user_id,
                    'original_input': input_text
                }
            )
        else:
            state = self.knowledge_states[topic]
            state.content = response
            state.sources.add(f"user_{user_id}")
            state.feedback_history.append((feedback, datetime.now()))
            state.last_updated = datetime.now()
            state.metadata.update({
                'feedback': feedback,
                'user_id': user_id,
                'original_input': input_text
            })
            
        # Aggiorna il progresso dell'utente
        if user_id not in self.user_progress:
            self.user_progress[user_id] = {
                "topics": set(),
                "recent_learning": []
            }
        
        progress = self.user_progress[user_id]
        progress["topics"].add(topic)
        progress["recent_learning"].append({
            "topic": topic,
            "timestamp": datetime.now().isoformat(),
            "confidence": ConfidenceLevel.MEDIUM.value
        })

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

    def get_knowledge_by_topic(self, topic: str) -> List[Dict[str, Any]]:
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
