from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass
import numpy as np
from datetime import datetime
import torch
from transformers import AutoTokenizer, AutoModel
from sklearn.metrics.pairwise import cosine_similarity

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
    embedding: Optional[torch.Tensor] = None

class ContextualLearningSystem:
    """Sistema per l'apprendimento contestuale"""
    
    def __init__(self):
        self.contexts: List[Context] = []
        self.context_embeddings: Dict[str, torch.Tensor] = {}
        
        # Carica il modello per le embedding
        self.tokenizer = AutoTokenizer.from_pretrained("dbmdz/bert-base-italian-xxl-uncased")
        self.model = AutoModel.from_pretrained("dbmdz/bert-base-italian-xxl-uncased")
        
        # Stato interno
        self.current_context: Optional[Context] = None
        self.learning_history: List[Dict] = []
        
    def process_input(self,
                     text: str,
                     metadata: Dict[str, Any] = None) -> Context:
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
            user_state=metadata.get('user_state', {}) if metadata else {},
            previous_contexts=[self.current_context] if self.current_context else [],
            confidence=0.7,
            embedding=text_embedding
        )
        
        # Aggiorna il contesto corrente
        self.current_context = new_context
        self.contexts.append(new_context)
        
        # Memorizza l'embedding
        self.context_embeddings[topic] = text_embedding
        
        # Aggiorna la storia dell'apprendimento
        self._update_learning_history(new_context)
        
        return new_context
    
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
    
    def _generate_embedding(self, text: str) -> torch.Tensor:
        """Genera embedding per il testo"""
        inputs = self.tokenizer(
            text,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=512
        )
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            embedding = outputs.last_hidden_state.mean(dim=1)
            
        return embedding
    
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
            emb_sim = cosine_similarity(
                context1.embedding.numpy(),
                context2.embedding.numpy()
            )[0][0]
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
