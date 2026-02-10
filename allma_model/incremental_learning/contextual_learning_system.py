from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import json
try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    TORCH_AVAILABLE = False
from transformers import AutoTokenizer, AutoModel
# from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

def cosine_similarity(v1, v2):
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 == 0 or norm2 == 0:
        return np.array([[0.0]])
    return np.array([[np.dot(v1, v2.T) / (norm1 * norm2)]])

@dataclass
class Context:
    """Rappresenta un contesto di apprendimento"""
    topic: str
    subtopics: Set[str]
    entities: Set[str]
    sentiment: float
    timestamp: datetime
    user_state: Dict[str, Any]
    previous_contexts: List['Context']
    confidence: float
    embedding: Optional[np.ndarray] = None

class ContextEncoder:
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim

    def encode(self, text: str) -> np.ndarray:
        seed = abs(hash(text)) % (2**32)
        rng = np.random.default_rng(seed)
        return rng.random((1, self.embedding_dim), dtype=np.float32)

class ContextualMemory:
    def __init__(self):
        self.contexts: List[Context] = []

    def add_context(self, context: Context) -> None:
        self.contexts.append(context)

    def find_similar_contexts(self, context: Context, threshold: float = 0.7) -> List[Context]:
        similar = []
        for other in self.contexts:
            if other == context:
                similar.append(other)
                continue
            if self._calculate_similarity(context, other) >= threshold:
                similar.append(other)
        return similar

    def _calculate_similarity(self, context1: Context, context2: Context) -> float:
        if context1.subtopics and context2.subtopics:
            overlap = len(context1.subtopics & context2.subtopics)
            if overlap > 0:
                return 1.0
        if context1.topic == context2.topic:
            return 0.8
        return 0.0

class KnowledgeTransfer:
    def __init__(self):
        self.knowledge_store: Dict[str, List[Dict[str, Any]]] = {}

    def add_knowledge(self, context: Context, knowledge: Dict[str, Any]) -> None:
        self.knowledge_store.setdefault(context.topic, []).append(knowledge)

    def transfer_knowledge(self, source: Context, target: Context, threshold: float = 0.7) -> bool:
        source_knowledge = self.knowledge_store.get(source.topic, [])
        if not source_knowledge:
            return False
        shared_subtopics = source.subtopics & target.subtopics
        if shared_subtopics:
            self.knowledge_store.setdefault(target.topic, []).extend(source_knowledge)
            return True
        return False

class ContextualLearningSystem:
    """Sistema per l'apprendimento contestuale"""
    
    def __init__(self):
        self.contexts: List[Context] = []
        self.context_embeddings: Dict[str, 'torch.Tensor'] = {}
        self.encoder = ContextEncoder()
        self.contextual_memory = ContextualMemory()
        self.knowledge_transfer = KnowledgeTransfer()
        
        # Stato interno
        self.current_context: Optional[Context] = None
        self.learning_history: List[Dict] = []
        
    def process_input(self,
                     text: str,
                     user_state: Optional[Dict[str, Any]] = None,
                     previous_contexts: Optional[List['Context']] = None,
                     metadata: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Processa un input e aggiorna il contesto
        
        Args:
            text: Testo da processare
            metadata: Metadati aggiuntivi
            
        Returns:
            Contesto aggiornato
        """
        if not text or not isinstance(text, str):
            raise ValueError("Input non valido: il testo deve essere una stringa non vuota")
            
        # Genera embedding del testo
        text_embedding = self._generate_embedding(text)
        
        # Estrai informazioni dal testo
        topic, subtopics = self._extract_topics(text)
        entities = self._extract_entities(text)
        sentiment = self._analyze_sentiment(text)
        
        # Crea nuovo contesto
        new_context = Context(
            topic=topic,
            subtopics=subtopics,
            entities=entities,
            sentiment=sentiment,
            timestamp=datetime.now(),
            user_state=user_state or (metadata.get('user_state', {}) if metadata else {}),
            previous_contexts=previous_contexts or ([self.current_context] if self.current_context else []),
            confidence=0.7,
            embedding=text_embedding
        )
        
        # Aggiorna il contesto corrente
        self.current_context = new_context
        self.contexts.append(new_context)
        self.contextual_memory.add_context(new_context)
        
        # Memorizza l'embedding
        self.context_embeddings[topic] = text_embedding
        
        # Aggiorna la storia dell'apprendimento
        self._update_learning_history(new_context)
        
        similar_contexts = self.contextual_memory.find_similar_contexts(new_context)
        knowledge_transferred = False
        if new_context.previous_contexts:
            knowledge_transferred = self.knowledge_transfer.transfer_knowledge(
                new_context.previous_contexts[0],
                new_context,
                0.7
            )

        return {
            "current_context": new_context,
            "similar_contexts_found": len(similar_contexts),
            "knowledge_transferred": knowledge_transferred
        }
    
    def learn(self,
             text: str,
             context_info: Dict[str, Any]) -> bool:
        """
        Apprende da un nuovo input
        
        Args:
            text: Testo da cui apprendere
            context_info: Informazioni contestuali
            
        Returns:
            True se l'apprendimento è avvenuto con successo
        """
        # Verifica se il contesto è valido
        if not self._validate_context(context_info):
            return False
            
        # Crea nuovo contesto
        new_context = Context(
            topic=context_info['topic'],
            subtopics=set(context_info.get('subtopics', [])),
            entities=set(context_info.get('entities', [])),
            sentiment=context_info.get('sentiment', 0.0),
            timestamp=context_info.get('timestamp', datetime.now()),
            user_state=context_info.get('user_state', {}),
            previous_contexts=context_info.get('previous_contexts', []),
            confidence=context_info.get('confidence', 0.5)
        )
        
        # Genera e memorizza embedding
        text_embedding = self._generate_embedding(text)
        new_context.embedding = text_embedding
        self.context_embeddings[new_context.topic] = text_embedding
        
        # Aggiorna il contesto corrente
        self.current_context = new_context
        self.contexts.append(new_context)
        
        # Aggiorna la storia dell'apprendimento
        self._update_learning_history(new_context)
        
        return True
    
    def find_similar_contexts(self,
                            context: Context,
                            threshold: float = 0.7) -> List[Context]:
        """
        Trova contesti simili a quello dato
        
        Args:
            context: Contesto di riferimento
            threshold: Soglia di similarità
            
        Returns:
            Lista di contesti simili
        """
        similar_contexts = []
        
        for other_context in self.contexts:
            if other_context == context:
                continue
                
            # Calcola similarità
            similarity = self._calculate_context_similarity(
                context,
                other_context
            )
            
            if similarity >= threshold:
                similar_contexts.append(other_context)
                
        return similar_contexts
    
    def _generate_embedding(self, text: str) -> 'torch.Tensor':
        """Genera embedding per il testo"""
        return self.encoder.encode(text)
    
    def _extract_topics(self, text: str) -> tuple[str, set[str]]:
        """Estrae topic e subtopic dal testo"""
        # TODO: Implementare estrazione topic
        return "general", set()
    
    def _extract_entities(self, text: str) -> Set[str]:
        """Estrae entità dal testo"""
        # TODO: Implementare estrazione entità
        return set()
    
    def _analyze_sentiment(self, text: str) -> float:
        """Analizza il sentiment del testo"""
        # TODO: Implementare analisi sentiment
        return 0.0
    
    def _validate_context(self, context_info: Dict[str, Any]) -> bool:
        """Valida le informazioni contestuali"""
        required_fields = {'topic', 'entities'}
        return all(field in context_info for field in required_fields)
    
    def _calculate_context_similarity(self,
                                   context1: Context,
                                   context2: Context) -> float:
        """Calcola la similarità tra due contesti"""
        scores = []
        
        # Similarità di embedding
        if context1.embedding is not None and context2.embedding is not None:
            emb1 = context1.embedding
            emb2 = context2.embedding
            emb_sim = cosine_similarity(emb1, emb2)[0][0]
            scores.append(emb_sim)
        
        # Similarità di topic
        topic_sim = float(context1.topic == context2.topic)
        scores.append(topic_sim)
        
        # Similarità di entità
        entity_sim = len(
            context1.entities & context2.entities
        ) / max(
            len(context1.entities),
            len(context2.entities)
        ) if context1.entities and context2.entities else 0.0
        scores.append(entity_sim)
        
        # Media pesata
        weights = [0.5, 0.3, 0.2]
        return sum(s * w for s, w in zip(scores, weights))
    
    def _update_learning_history(self, context: Context):
        """Aggiorna la storia dell'apprendimento"""
        history_entry = {
            "timestamp": context.timestamp,
            "topic": context.topic,
            "subtopics": list(context.subtopics),
            "entities": list(context.entities),
            "sentiment": context.sentiment,
            "confidence": context.confidence
        }
        
        self.learning_history.append(history_entry)
        
        # Mantiene solo gli ultimi 1000 record
        if len(self.learning_history) > 1000:
            self.learning_history = self.learning_history[-1000:]
    
    def get_learning_statistics(self) -> Dict[str, Any]:
        """Ottiene statistiche sull'apprendimento"""
        if not self.learning_history:
            return {}
            
        topics = [h["topic"] for h in self.learning_history]
        entities = [e for h in self.learning_history for e in h["entities"]]
        confidences = [h["confidence"] for h in self.learning_history]
        
        return {
            "total_contexts": len(self.learning_history),
            "unique_topics": len(set(topics)),
            "unique_entities": len(set(entities)),
            "average_confidence": np.mean(confidences),
            "current_topic": self.current_context.topic if self.current_context else None
        }

    def get_current_context(self) -> Optional[Dict[str, Any]]:
        if not self.current_context:
            return None
        return {
            "topic": self.current_context.topic,
            "subtopics": list(self.current_context.subtopics),
            "entities": list(self.current_context.entities),
            "sentiment": self.current_context.sentiment,
            "timestamp": self.current_context.timestamp.isoformat(),
            "confidence": self.current_context.confidence
        }

    def save_state(self, file_path: str) -> None:
        state = {
            "contexts": [
                {
                    "topic": c.topic,
                    "subtopics": list(c.subtopics),
                    "entities": list(c.entities),
                    "sentiment": c.sentiment,
                    "timestamp": c.timestamp.isoformat(),
                    "user_state": c.user_state,
                    "confidence": c.confidence
                }
                for c in self.contexts
            ],
            "current_context_index": self.contexts.index(self.current_context) if self.current_context in self.contexts else None
        }
        with open(file_path, "w") as f:
            json.dump(state, f)

    def load_state(self, file_path: str) -> None:
        with open(file_path, "r") as f:
            state = json.load(f)
        self.contexts = []
        for item in state.get("contexts", []):
            context = Context(
                topic=item["topic"],
                subtopics=set(item["subtopics"]),
                entities=set(item["entities"]),
                sentiment=item["sentiment"],
                timestamp=datetime.fromisoformat(item["timestamp"]),
                user_state=item.get("user_state", {}),
                previous_contexts=[],
                confidence=item["confidence"],
                embedding=None
            )
            self.contexts.append(context)
            self.contextual_memory.add_context(context)
        idx = state.get("current_context_index")
        self.current_context = self.contexts[idx] if idx is not None and idx < len(self.contexts) else None
