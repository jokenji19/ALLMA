"""
Enhanced Memory System
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending

Sistema di memoria avanzato che integra memoria di lavoro, breve termine, lungo termine,
associativa e procedurale.
"""

from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
import numpy as np
from datetime import datetime, timedelta
import json
import logging
import math
try:
    import torch
    from torch.nn.functional import cosine_similarity
    TORCH_AVAILABLE = True
except ImportError:
    torch = None
    cosine_similarity = None
    TORCH_AVAILABLE = False
from collections import defaultdict
import threading
from threading import Lock

@dataclass
class Memory:
    """Classe base per le memorie nel sistema ALLMA"""
    content: str
    timestamp: datetime = field(default_factory=datetime.now)
    emotional_valence: float = 0.0
    importance: float = 0.0
    context: Dict[str, Any] = field(default_factory=dict)
    type: str = "base"  # base, episodic, semantic, procedural
    
    def __post_init__(self):
        if not -1.0 <= self.emotional_valence <= 1.0:
            raise ValueError("La valenza emotiva deve essere tra -1.0 e 1.0")
            
    def update_importance(self, new_importance: float):
        """Aggiorna l'importanza della memoria"""
        self.importance = new_importance
        
    def add_context(self, key: str, value: Any):
        """Aggiunge informazioni al contesto"""
        self.context[key] = value
        
    def get_age(self) -> timedelta:
        """Calcola l'età della memoria"""
        return datetime.now() - self.timestamp
        
    def to_dict(self) -> Dict[str, Any]:
        """Converte la memoria in dizionario"""
        return {
            'content': self.content,
            'timestamp': self.timestamp.isoformat(),
            'emotional_valence': self.emotional_valence,
            'importance': self.importance,
            'context': self.context,
            'type': self.type
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Memory':
        """Crea una memoria da un dizionario"""
        data['timestamp'] = datetime.fromisoformat(data['timestamp'])
        return cls(**data)

@dataclass
class MemoryItem:
    """Rappresenta un singolo item di memoria"""
    content: str
    timestamp: datetime
    type: str  # 'experience', 'concept', 'relation'
    context: Dict[str, Any] = field(default_factory=dict)
    emotional_valence: float = 0.0
    importance: float = 0.0
    frequency: int = 1
    last_accessed: datetime = field(default_factory=datetime.now)
    associations: Set[str] = field(default_factory=set)
    categories: Set[str] = field(default_factory=set)
    patterns: Set[str] = field(default_factory=set)
    recall_count: int = 0
    last_recall: datetime = field(default_factory=datetime.now)
    strength: float = 1.0  # Forza della memoria (inizialmente 1.0)

class WorkingMemory:
    """Gestisce la memoria di lavoro (capacità limitata, accesso rapido)"""
    def __init__(self, capacity: int = 7):  # Miller's Law: 7 ± 2 items
        self.capacity = capacity
        self.items: List[MemoryItem] = []
        self._lock = Lock()
        
    def add_item(self, item: MemoryItem):
        """Aggiunge un item alla memoria di lavoro"""
        with self._lock:
            if len(self.items) >= self.capacity:
                # Rimuovi l'item meno importante
                self.items.sort(key=lambda x: x.importance)
                self.items.pop(0)
            self.items.append(item)
        
    def get_items(self) -> List[MemoryItem]:
        """Recupera tutti gli items nella memoria di lavoro"""
        with self._lock:
            return self.items.copy()
        
    def clear(self):
        """Pulisce la memoria di lavoro"""
        with self._lock:
            self.items.clear()

class ShortTermMemory:
    """Gestisce la memoria a breve termine"""
    def __init__(self, retention_time: timedelta = timedelta(seconds=10)):
        self.retention_time = retention_time
        self.items: List[MemoryItem] = []
        self._lock = Lock()
        
    def add_item(self, item: MemoryItem):
        """Aggiunge un item alla memoria a breve termine"""
        with self._lock:
            self.items.append(item)
            current_time = datetime.now()
            self.items = [
                item for item in self.items
                if (current_time - item.timestamp) <= self.retention_time
            ]
        
    def get_recent_items(self, n: int = 10) -> List[MemoryItem]:
        """Recupera gli n items più recenti"""
        with self._lock:
            current_time = datetime.now()
            self.items = [
                item for item in self.items
                if (current_time - item.timestamp) <= self.retention_time
            ]
            return sorted(
                self.items,
                key=lambda x: x.timestamp,
                reverse=True
            )[:n]

class LongTermMemory:
    """Gestisce la memoria a lungo termine con forgetting curves"""
    def __init__(self):
        self.items: List[MemoryItem] = []
        self.associations: Dict[str, Set[str]] = defaultdict(set)
        self._lock = Lock()
        
    def add_item(self, item: MemoryItem):
        """Aggiunge un item alla memoria a lungo termine"""
        with self._lock:
            self.items.append(item)
            # Aggiorna le associazioni
            for concept in item.associations:
                self.associations[concept].update(
                    item.associations - {concept}
                )
            
    def get_memory_strength(self, item: MemoryItem) -> float:
        """Calcola la forza attuale di un ricordo usando la curva dell'oblio di Ebbinghaus"""
        time_diff = datetime.now() - item.last_recall
        hours = time_diff.total_seconds() / 3600
        
        # R = e^(-t/S), dove S è la stabilità della memoria
        stability = 1.0 + (0.5 * item.recall_count)  # La stabilità aumenta con i richiami
        strength = math.exp(-hours / (24.0 * stability))
        
        # Considera anche l'importanza e l'intensità emotiva
        strength *= (0.3 + 0.7 * item.importance)
        strength *= (0.3 + 0.7 * item.emotional_valence)
        
        return min(1.0, strength)
        
    def recall_item(self, item: MemoryItem):
        """Richiama un item, rafforzando la memoria"""
        with self._lock:
            item.recall_count += 1
            item.last_recall = datetime.now()
            item.memory_strength = self.get_memory_strength(item)
        
    def get_associated_items(self, concepts: Set[str], threshold: float = 0.2) -> List[MemoryItem]:
        """Recupera items associati a determinati concetti"""
        with self._lock:
            relevant_items = []
            for item in self.items:
                # Calcola la sovrapposizione tra i concetti
                overlap = len(item.associations.intersection(concepts)) / len(concepts)
                if overlap >= threshold:
                    item.memory_strength = self.get_memory_strength(item)
                    if item.memory_strength >= threshold:
                        relevant_items.append(item)
        
            return sorted(
                relevant_items,
                key=lambda x: (x.memory_strength, x.importance),
                reverse=True
            )

class AssociativeMemory:
    """Gestisce le associazioni tra concetti usando una rete neurale semplice"""
    def __init__(self, embedding_dim: int = 64):
        self.embedding_dim = embedding_dim
        self.concept_embeddings: Dict[str, 'torch.Tensor'] = {}
        self._lock = Lock()
        
    def add_association(self, concept1: str, concept2: str, strength: float = 1.0):
        """Crea o rafforza un'associazione tra due concetti"""
        with self._lock:
            # Crea embeddings se non esistono
            if concept1 not in self.concept_embeddings:
                self.concept_embeddings[concept1] = torch.randn(self.embedding_dim)
            if concept2 not in self.concept_embeddings:
                self.concept_embeddings[concept2] = torch.randn(self.embedding_dim)
            
            # Avvicina gli embeddings in base alla forza dell'associazione
            emb1 = self.concept_embeddings[concept1]
            emb2 = self.concept_embeddings[concept2]
            mean_emb = (emb1 + emb2) / 2
            
            self.concept_embeddings[concept1] = (
                emb1 * (1 - strength) + mean_emb * strength
            )
            self.concept_embeddings[concept2] = (
                emb2 * (1 - strength) + mean_emb * strength
            )
        
    def get_similar_concepts(self, concept: str, threshold: float = 0.7) -> List[Tuple[str, float]]:
        """Trova concetti simili usando la similarità del coseno"""
        with self._lock:
            if concept not in self.concept_embeddings:
                return []
            
            target_emb = self.concept_embeddings[concept]
            similarities = []
        
            for other_concept, other_emb in self.concept_embeddings.items():
                if other_concept != concept:
                    sim = cosine_similarity(
                        target_emb.unsqueeze(0),
                        other_emb.unsqueeze(0)
                    ).item()
                    if sim >= threshold:
                        similarities.append((other_concept, sim))
                    
            return sorted(similarities, key=lambda x: x[1], reverse=True)

class ProceduralMemory:
    """Gestisce la memoria delle procedure e abilità"""
    
    def __init__(self):
        self.procedures: Dict[str, Dict] = {}
        self._lock = Lock()
        
    def add_procedure(self, name: str, steps: List[str], context: Dict = None):
        """Aggiunge una nuova procedura"""
        with self._lock:
            self.procedures[name] = {
                'steps': steps,
                'context': context or {},
                'mastery_level': 0.0,
                'practice_count': 0,
                'last_practice': datetime.now()
            }
        
    def practice_procedure(self, name: str, success_rate: float):
        """Registra la pratica di una procedura"""
        with self._lock:
            if name not in self.procedures:
                return
            
            proc = self.procedures[name]
            proc['practice_count'] += 1
        
            # Aggiorna il livello di maestria usando una curva logaritmica
            current_level = proc['mastery_level']
            practice_effect = success_rate * (1.0 - current_level) * 0.1
            proc['mastery_level'] = min(1.0, current_level + practice_effect)
            proc['last_practice'] = datetime.now()
        
    def get_procedure(self, name: str) -> Optional[Dict]:
        """Recupera una procedura"""
        with self._lock:
            return self.procedures.get(name)
        
    def get_mastery_level(self, name: str) -> float:
        """Ottiene il livello di maestria di una procedura"""
        with self._lock:
            if name not in self.procedures:
                return 0.0
            return self.procedures[name]['mastery_level']

class EpisodicMemory:
    """Gestisce la memoria episodica"""
    
    def __init__(self):
        self.memories: List[MemoryItem] = []
        self.memory_stats = {
            'total_memories': 0,
            'consolidated_memories': 0,
            'retrieved_memories': 0
        }
        self.last_consolidation = datetime.now()
        self._lock = Lock()
        
    def add_memory(self, content: str, emotional_valence: float, context: Dict = None) -> None:
        """Aggiunge una nuova memoria episodica"""
        with self._lock:
            importance = self._calculate_importance(emotional_valence, context)
            categories = self._categorize_memory(content, context)
            patterns = self._find_patterns(content, context)
            associations = self._extract_associations(content, context)
            memory = MemoryItem(
                content=content,
                timestamp=datetime.now(),
                type="episodic",  # Tipo di memoria
                context=context,
                emotional_valence=emotional_valence,
                importance=importance,
                associations=associations,
                recall_count=0,
                last_recall=datetime.now(),
                categories=categories,
                patterns=patterns
            )
            self.memories.append(memory)
            self.memory_stats['total_memories'] += 1
        
    def recall(self, query: str, context: Dict = None, limit: int = 5) -> List[MemoryItem]:
        """Recupera memorie in base a query e contesto"""
        with self._lock:
            if not self.memories:
                return []
            
            # Calcola rilevanza per ogni memoria
            memories_with_relevance = []
            for memory in self.memories:
                relevance = self._calculate_relevance(memory, query, context)
                memories_with_relevance.append((memory, relevance))
            
            # Ordina per rilevanza e prendi i top N
            memories_with_relevance.sort(key=lambda x: x[1], reverse=True)
            return [m[0] for m in memories_with_relevance[:limit]]
        
    def _calculate_relevance(self, memory: MemoryItem, query: str, context: Dict = None) -> float:
        """Calcola la rilevanza di una memoria rispetto a query e contesto"""
        # Rilevanza basata sul contenuto
        content_relevance = self._calculate_text_similarity(memory.content.lower(), query.lower())
        
        # Rilevanza basata sul contesto
        context_relevance = 0.0
        if context and memory.context:
            matching_context = sum(
                memory.context.get(k) == v 
                for k, v in context.items() 
                if k in memory.context
            )
            total_context = len(context)
            context_relevance = matching_context / total_context if total_context > 0 else 0.0
            
        # Rilevanza basata su importanza e forza
        importance_relevance = memory.importance * memory.strength
        
        # Combina i diversi fattori
        # Pesi: contenuto (0.4), contesto (0.3), importanza (0.3)
        return (0.4 * content_relevance + 
                0.3 * context_relevance + 
                0.3 * importance_relevance)
                
    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """Calcola la similarità tra due testi"""
        # Normalizza e tokenizza i testi
        text1 = text1.lower()
        text2 = text2.lower()
        
        # Limita la lunghezza dei testi per evitare problemi di performance
        max_words = 100
        words1 = text1.split()[:max_words]
        words2 = text2.split()[:max_words]
        
        if not words1 or not words2:
            return 0.0
            
        # Usa set per calcolare rapidamente intersezione e unione
        set1 = set(words1)
        set2 = set(words2)
        
        intersection = len(set1 & set2)
        union = len(set1 | set2)
        
        return intersection / union if union > 0 else 0.0
        
    def _calculate_importance(self, emotional_valence: float, context: Dict = None) -> float:
        """Calcola l'importanza di una memoria"""
        # Base importance from emotional valence (0.3 weight)
        importance = 0.3 * abs(emotional_valence)
        
        # Context-based importance (0.7 weight)
        if context:
            # Novel experiences are very important
            if context.get('is_novel', False):
                importance += 0.3
                
            # Significant events are important    
            if context.get('is_significant', False):
                importance += 0.2
                
            # Learning experiences are important
            if context.get('is_learning', False):
                importance += 0.2
                
        return min(1.0, importance)
        
    def _categorize_memory(self, content: str, context: Dict = None) -> Set[str]:
        """Categorizza una memoria in base a contenuto e contesto"""
        categories = set()
        
        # Categorie basate sul contesto
        if context:
            if 'activity' in context:
                categories.add(f"attività_{context['activity']}")
                
            if context.get('is_learning', False):
                categories.add('apprendimento')
                
            if context.get('social', False):
                categories.add('sociale')
                
        # Categorie basate sul contenuto
        content_lower = content.lower()
        if any(word in content_lower for word in ['imparo', 'studio', 'imparando']):
            categories.add('apprendimento')
            
        if any(word in content_lower for word in ['felice', 'triste', 'arrabbiato', 'paura']):
            categories.add('emozioni')
            
        return categories
        
    def _find_patterns(self, content: str, context: Dict = None) -> Set[str]:
        """Trova pattern in una memoria"""
        patterns = set()
        
        # Pattern basato su attività ripetute
        if context and 'activity' in context:
            similar_memories = [
                m for m in self.memories 
                if m.context.get('activity') == context['activity']
            ]
            if similar_memories:
                patterns.add('pattern_0')  # Pattern di attività ripetuta
                
        # Pattern basato su sequenze temporali
        if len(self.memories) >= 2:
            last_memory = self.memories[-1]
            if last_memory.context == context:
                patterns.add('pattern_1')  # Pattern di continuità contestuale
                
        # Pattern basato su contenuto simile
        content_words = set(content.lower().split())
        for memory in self.memories[-5:]:  # Controlla solo le ultime 5 memorie
            memory_words = set(memory.content.lower().split())
            similarity = len(content_words & memory_words) / len(content_words | memory_words)
            if similarity > 0.3:  # Soglia di similarità
                patterns.add('pattern_2')  # Pattern di contenuto simile
                break
                
        # Pattern basato su emozioni simili
        if len(self.memories) >= 2:
            last_memory = self.memories[-1]
            if abs(last_memory.emotional_valence - self.memories[-2].emotional_valence) < 0.2:
                patterns.add('pattern_3')  # Pattern di continuità emotiva
                
        return patterns
        
    def _extract_associations(self, content: str, context: Dict = None) -> Set[str]:
        """Estrae associazioni da una memoria"""
        associations = set()
        
        # Associazioni basate sul contesto
        if context:
            if 'activity' in context:
                associations.add(f"attività_{context['activity']}")
                
            if 'location' in context:
                associations.add(f"luogo_{context['location']}")
                
        # Associazioni basate sul contenuto
        content_lower = content.lower()
        words = content_lower.split()
        
        # Associazioni con altre memorie recenti
        if self.memories:
            last_memory = self.memories[-1]
            common_words = set(words) & set(last_memory.content.lower().split())
            associations.update(common_words)
            
        return associations
        
    def get_associated_memories(self, memory_index: int) -> List[Tuple[MemoryItem, float]]:
        """Trova memorie associate a una memoria specifica"""
        with self._lock:
            if not (0 <= memory_index < len(self.memories)):
                return []
            
            target_memory = self.memories[memory_index]
            associated = []
        
            for i, memory in enumerate(self.memories):
                if i == memory_index:
                    continue
                
                # Calcola forza dell'associazione
                association_strength = self._calculate_association_strength(
                    target_memory, memory
                )
            
                if association_strength > 0:
                    associated.append((memory, association_strength))
                    
            # Ordina per forza dell'associazione
            associated.sort(key=lambda x: x[1], reverse=True)
            return associated
        
    def _calculate_association_strength(self, memory1: MemoryItem, memory2: MemoryItem) -> float:
        """Calcola la forza dell'associazione tra due memorie"""
        # Similarità del contesto
        context_similarity = 0.0
        if memory1.context and memory2.context:
            common_context = set(memory1.context.items()) & set(memory2.context.items())
            total_context = set(memory1.context.items()) | set(memory2.context.items())
            context_similarity = len(common_context) / len(total_context) if total_context else 0.0
            
        # Similarità del contenuto
        content_similarity = self._calculate_text_similarity(
            memory1.content.lower(),
            memory2.content.lower()
        )
        
        # Similarità delle categorie
        category_similarity = 0.0
        if memory1.categories and memory2.categories:
            common_categories = memory1.categories & memory2.categories
            total_categories = memory1.categories | memory2.categories
            category_similarity = len(common_categories) / len(total_categories)
            
        # Combina i fattori con pesi
        return (0.4 * context_similarity + 
                0.3 * content_similarity + 
                0.3 * category_similarity)
                
    def find_memory_chains(self, start_index: int, max_depth: int = 3) -> List[List[MemoryItem]]:
        """Trova catene di memorie associate"""
        with self._lock:
            if not (0 <= start_index < len(self.memories)):
                return []
            
            def build_chain(current_index: int, current_chain: List[MemoryItem], depth: int) -> List[List[MemoryItem]]:
                if depth >= max_depth:
                    return [current_chain]
                
                chains = []
                associated = self.get_associated_memories(current_index)
            
                for memory, strength in associated[:2]:  # Considera solo le 2 associazioni più forti
                    if memory not in current_chain and strength > 0.5:
                        new_chain = current_chain + [memory]
                        chains.extend(build_chain(self.memories.index(memory), new_chain, depth + 1))
                    
                return chains if chains else [current_chain]
            
            start_memory = self.memories[start_index]
            return build_chain(start_index, [start_memory], 0)
        
    def apply_forgetting(self) -> None:
        """Applica il meccanismo di oblio"""
        with self._lock:
            current_time = datetime.now()
        
            for memory in self.memories:
                # Calcola il tempo trascorso dall'ultimo richiamo
                time_since_recall = (current_time - memory.last_recall).total_seconds()
            
                # Decadimento esponenziale della forza
                decay_rate = 0.1  # Parametro che controlla la velocità di decadimento
                memory.strength *= math.exp(-decay_rate * (time_since_recall / (24 * 3600)))  # Normalizza a giorni
            
                # Rinforzo basato sul numero di richiami
                memory.strength = min(1.0, memory.strength + (0.1 * memory.recall_count))
            
    def consolidate(self) -> None:
        """Consolida le memorie"""
        with self._lock:
            current_time = datetime.now()
            consolidation_interval = timedelta(seconds=10)
        
            if current_time - self.last_consolidation < consolidation_interval:
                return
            
            # Rimuovi memorie deboli
            self.memories = [m for m in self.memories if m.strength > 0.2]
            self.memory_stats['consolidated_memories'] += len(self.memories)
        
            # Aggiorna timestamp di consolidamento
            self.last_consolidation = current_time

class SemanticMemory:
    """Gestisce la memoria semantica (conoscenza concettuale)"""
    
    def __init__(self):
        self.concepts: Dict[str, Dict] = {}
        self.relationships: Dict[str, Set[Tuple[str, str]]] = defaultdict(set)
        self._lock = Lock()
        
    def add_concept(self, concept: str, attributes: Dict):
        """Aggiunge o aggiorna un concetto"""
        with self._lock:
            if concept in self.concepts:
                self.concepts[concept].update(attributes)
            else:
                self.concepts[concept] = attributes
            
    def add_relationship(self, concept1: str, relation: str, concept2: str):
        """Aggiunge una relazione tra concetti"""
        with self._lock:
            self.relationships[concept1].add((relation, concept2))
        
    def get_related_concepts(self, concept: str) -> Dict[str, Set[str]]:
        """Trova concetti correlati"""
        with self._lock:
            if concept not in self.relationships:
                return {}
            
            related = defaultdict(set)
            for relation, target in self.relationships[concept]:
                related[relation].add(target)
            
            return dict(related)
        
    def query_knowledge(self, query: str) -> List[Dict]:
        """Interroga la base di conoscenza"""
        with self._lock:
            results = []
            for concept, attributes in self.concepts.items():
                if query.lower() in concept.lower():
                    result = {"concept": concept, "attributes": attributes}
                    if concept in self.relationships:
                        result["relationships"] = self.get_related_concepts(concept)
                    results.append(result)
            return results

class MemorySystem:
    """Sistema di memoria avanzato che integra diversi tipi di memoria"""
    
    def __init__(self, mobile_mode: bool = False):
        """Inizializza il sistema di memoria"""
        self._lock = threading.Lock()
        self.working_memory: List[MemoryItem] = []
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        self.procedural = ProceduralMemory()
        self.mobile_mode = mobile_mode
        
        # Configurazione
        if self.mobile_mode:
            self.max_working_memory = 5  # Ridotto per mobile
            self.consolidation_interval = 300  # 5 minuti per mobile
        else:
            self.max_working_memory = 10
            self.consolidation_interval = 1800  # 30 minuti
            
        self.consolidation_threshold = 0.5
        self.retrieval_threshold = 0.3
        self.importance_threshold = 0.4
        self.emotion_weight = 0.3
        self.recency_weight = 0.4
        self.relevance_weight = 0.3
        self.last_consolidation = datetime.now()
        
    def process_experience(self, experience: str, emotional_valence: float = 0.0) -> dict:
        """
        Processa una nuova esperienza
        
        Args:
            experience: Esperienza da processare
            emotional_valence: Valenza emotiva dell'esperienza (-1.0 a 1.0)
            
        Returns:
            Dizionario con i risultati del processamento
            
        Raises:
            ValueError: Se l'esperienza è vuota o la valenza emotiva non è valida
        """
        # Validazione input
        if not experience or not experience.strip():
            raise ValueError("L'esperienza non può essere vuota")
            
        if not -1.0 <= emotional_valence <= 1.0:
            raise ValueError("La valenza emotiva deve essere tra -1.0 e 1.0")
            
        # Estrai concetti una sola volta
        concepts = self._extract_concepts(experience)
        importance = self._calculate_importance(experience, emotional_valence)
            
        # Aggiungi alla memoria di lavoro
        memory_item = {
            "content": experience,
            "timestamp": datetime.now().isoformat(),
            "emotional_valence": emotional_valence,
            "importance": importance,
            "concepts": concepts
        }
        
        self.add_memory(memory_item)
        
        # Verifica se è necessario consolidare
        consolidation_performed = False
        if self._should_consolidate():
            # Esegui consolidamento in modo asincrono
            threading.Thread(target=self._consolidate_memories).start()
            consolidation_performed = True
        
        return {
            "memory_item": memory_item,
            "consolidation_performed": consolidation_performed,
            "memory_stored": True
        }
        
    def recall_memory(self, query: str, context: Dict = None) -> List[Dict]:
        """
        Recupera memorie rilevanti basate su query e contesto
        
        Args:
            query: Stringa di ricerca
            context: Dizionario con informazioni contestuali
            
        Returns:
            Lista di MemoryItem rilevanti
        """
        with self._lock:
            # Recupera memorie da varie fonti
            working_memories = self.working_memory
            short_term_memories = []
            episodic_memories = self.episodic.recall(query, context)
            
            # Combina tutte le memorie
            all_memories = working_memories + short_term_memories + episodic_memories
            
            # Pre-calcola i valori per il sorting
            now = datetime.now()
            memories_with_scores = []
            for memory in all_memories:
                # Calcola il timestamp una sola volta
                timestamp = datetime.fromisoformat(memory["timestamp"])
                recency_score = -((now - timestamp).total_seconds())
                
                # Crea una tupla con tutti i valori di ordinamento
                sort_values = (
                    memory["importance"],
                    abs(memory["emotional_valence"]),
                    recency_score
                )
                
                memories_with_scores.append((sort_values, memory))
            
            # Ordina usando i valori pre-calcolati
            memories_with_scores.sort(key=lambda x: x[0], reverse=True)
            
            # Estrai solo le memorie ordinate
            sorted_memories = [item[1] for item in memories_with_scores]
            
            return sorted_memories
        
    def _calculate_importance(self, experience: str, emotional_valence: float) -> float:
        """Calcola l'importanza di un'esperienza"""
        # Fattori che influenzano l'importanza
        factors = {
            "emotional_intensity": self._get_emotional_intensity(emotional_valence),
            "complexity": len(self._extract_concepts(experience)) * 0.1,
            "learning_level": 0.0,  # Non disponibile in questo contesto
            "confidence": 0.5  # Non disponibile in questo contesto
        }
        
        # Pesi per ciascun fattore
        weights = {
            "emotional_intensity": 0.4,
            "complexity": 0.3,
            "learning_level": 0.2,
            "confidence": 0.1
        }
        
        importance = sum(
            factor * weights[name]
            for name, factor in factors.items()
        )
        
        return min(max(importance, 0.0), 1.0)
        
    def _get_emotional_intensity(self, emotional_valence: float) -> float:
        """Calcola l'intensità emotiva"""
        return abs(emotional_valence)
        
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calcola la rilevanza tra query e contenuto"""
        # Normalizza e tokenizza i testi
        query = query.lower()
        content = content.lower()
        
        # Limita la lunghezza dei testi per evitare problemi di performance
        max_words = 100
        query_words = query.split()[:max_words]
        content_words = content.split()[:max_words]
        
        if not query_words or not content_words:
            return 0.0
            
        # Usa set per calcolare rapidamente intersezione e unione
        query_set = set(query_words)
        content_set = set(content_words)
        
        intersection = len(query_set & content_set)
        union = len(query_set | content_set)
        
        return intersection / union if union > 0 else 0.0
        
    def _update_concept_network(self, experience: str):
        """Aggiorna la rete di relazioni tra concetti"""
        # Limita il numero di concetti da elaborare
        concepts = self._extract_concepts(experience)[:10]  # Processa al massimo 10 concetti
        if not concepts:
            return
            
        # Aggiorna la rete concettuale
        for i, concept1 in enumerate(concepts):
            if concept1 not in self.concept_network:
                self.concept_network[concept1] = []
                
            # Collega solo ai concetti successivi per evitare duplicati
            for concept2 in concepts[i+1:]:
                if concept2 not in self.concept_network[concept1]:
                    self.concept_network[concept1].append(concept2)
                    
                if concept2 not in self.concept_network:
                    self.concept_network[concept2] = [concept1]
                elif concept1 not in self.concept_network[concept2]:
                    self.concept_network[concept2].append(concept1)
                    
    def _calculate_familiarity(self, concepts: List[str]) -> float:
        """Calcola quanto familiari sono i concetti al sistema"""
        if not concepts:
            return 0.0
            
        known_concepts = set(self.concept_network.keys())
        concept_set = set(concepts)
        
        # Calcola la proporzione di concetti conosciuti
        familiarity = len(concept_set.intersection(known_concepts)) / len(concept_set)
        
        return familiarity
        
    def _find_related_concepts(self, concepts: List[str]) -> List[str]:
        """Trova concetti correlati nella rete concettuale"""
        related = set()
        
        for concept in concepts:
            if concept in self.concept_network:
                related.update(self.concept_network[concept])
                
        return list(related)
        
    def recall_memory(self, query: str, context: Dict = None) -> List[MemoryItem]:
        """
        Recupera memorie rilevanti basate su query e contesto
        
        Args:
            query: Stringa di ricerca
            context: Dizionario con informazioni contestuali
            
        Returns:
            Lista di MemoryItem rilevanti
        """
        with self._lock:
            # Cerca prima nella memoria di lavoro
            working_memories = self.working_memory
            
            # Poi nella memoria a breve termine
            short_term_memories = []
            
            # Infine nella memoria episodica
            episodic_memories = self.episodic.recall(query, context)
            
            # Combina e ordina per rilevanza
            all_memories = working_memories + short_term_memories + episodic_memories
            all_memories.sort(key=lambda x: (
                x["importance"],  # Prima le memorie più importanti
                abs(x["emotional_valence"]),  # Poi quelle più emotive
                -((datetime.now() - datetime.fromisoformat(x["timestamp"])).total_seconds())  # Infine le più recenti
            ), reverse=True)
            
            return all_memories
            
    @property
    def memories(self):
        """Restituisce tutte le memorie del sistema"""
        with self._lock:
            return self.working_memory + self.episodic.memories

    def get_memory_stats(self) -> Dict:
        """Restituisce le statistiche del sistema di memoria"""
        with self._lock:
            memories = self.memories
            total_memories = len(memories)
            consolidated_memories = sum(1 for m in memories if getattr(m, 'consolidated', False))
            retrieved_memories = sum(1 for m in memories if getattr(m, 'retrieved', False))
            
            return {
                'total_memories': total_memories,
                'consolidated_memories': consolidated_memories,
                'retrieved_memories': retrieved_memories,
                'average_importance': sum(getattr(m, 'importance', 0) for m in memories) / total_memories if total_memories > 0 else 0
            }
            
    def _consolidate_memories(self):
        """Consolida le memorie dalla working memory alla long term memory"""
        now = datetime.now()
        
        # Sposta le memorie vecchie nella long term memory
        for memory in self.working_memory[:]:
            memory_time = datetime.fromisoformat(memory["timestamp"])
            if (now - memory_time).total_seconds() >= self.consolidation_interval:
                self.working_memory.remove(memory)
                self.long_term_memory.append(memory)
                
        # Aggiorna il timestamp dell'ultimo consolidamento
        self.last_consolidation = now
        
    def save_to_file(self, filename: str):
        """Salva lo stato del sistema su file"""
        with self._lock:
            state = self.get_state()
            with open(filename, 'w') as f:
                json.dump(state, f, default=self._json_serialize)
            
    def load_from_file(self, filename: str):
        """Carica lo stato del sistema da file"""
        with self._lock:
            with open(filename, 'r') as f:
                state = json.load(f)
            self.restore_state(state)
        
    def _json_serialize(self, obj):
        """Serializza oggetti speciali per JSON"""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return vars(obj)
        
    def get_state(self) -> Dict:
        """Ottiene lo stato corrente del sistema"""
        with self._lock:
            return {
                "episodic_memories": [vars(m) for m in self.episodic.memories],
                "semantic_concepts": self.semantic.concepts,
                "procedural_procedures": self.procedural.procedures,
                "total_memories": len(self.episodic.memories),
                "last_consolidation": self.last_consolidation
            }
        
    def restore_state(self, state: Dict):
        """Ripristina lo stato del sistema"""
        with self._lock:
            # Ripristina memorie episodiche
            self.episodic.memories = []
            for mem_dict in state["episodic_memories"]:
                # Converti le liste in set dove necessario
                if "associations" in mem_dict:
                    mem_dict["associations"] = set(mem_dict["associations"])
                if "categories" in mem_dict:
                    mem_dict["categories"] = set(mem_dict["categories"])
                if "patterns" in mem_dict:
                    mem_dict["patterns"] = set(mem_dict["patterns"])
                
                # Converti le stringhe ISO in datetime
                if "timestamp" in mem_dict:
                    mem_dict["timestamp"] = datetime.fromisoformat(mem_dict["timestamp"])
                if "last_recall" in mem_dict:
                    mem_dict["last_recall"] = datetime.fromisoformat(mem_dict["last_recall"])
                
                memory = MemoryItem(**mem_dict)
                self.episodic.memories.append(memory)
            
            # Ripristina concetti semantici
            self.semantic.concepts = state["semantic_concepts"]
            
            # Ripristina procedure
            self.procedural.procedures = state["procedural_procedures"]
            
            # Ripristina timestamp consolidamento
            if isinstance(state["last_consolidation"], str):
                self.last_consolidation = datetime.fromisoformat(state["last_consolidation"])
            else:
                self.last_consolidation = datetime.now()

    def _extract_concepts(self, text: str) -> List[str]:
        """Estrae concetti da un testo"""
        # Usa un set per ricerca O(1)
        keywords = {"imparo", "studio", "imparando", "felice", "triste", "arrabbiato", "paura"}
        # List comprehension più efficiente del ciclo for
        return [word for word in text.lower().split() if word in keywords]

    def add_memory(self, memory_item: Dict) -> None:
        """
        Aggiunge un item alla memoria di lavoro
        
        Args:
            memory_item: Dizionario contenente i dettagli della memoria
        
        Raises:
            ValueError: Se memory_item non è valido
        """
        if not isinstance(memory_item, dict):
            raise ValueError("memory_item deve essere un dizionario")
            
        # Valida il contenuto
        if 'content' not in memory_item or memory_item['content'] is None:
            raise ValueError("memory_item deve contenere un campo 'content' non nullo")
            
        if 'context' not in memory_item:
            raise ValueError("memory_item deve contenere un campo 'context'")
            
        # Aggiungi alla memoria di lavoro
        if not hasattr(self, 'working_memory'):
            self.working_memory = []
            
        self.working_memory.append(memory_item)

    def _should_consolidate(self) -> bool:
        """Verifica se è necessario consolidare le memorie"""
        if not hasattr(self, 'last_consolidation'):
            self.last_consolidation = None
            
        if self.last_consolidation is None:
            return True
            
        time_since_last = (datetime.now() - self.last_consolidation).total_seconds()
        return time_since_last >= self.consolidation_interval

class EnhancedMemorySystem(MemorySystem):
    """Sistema di memoria potenziato con funzionalità avanzate"""
    
    def __init__(self):
        super().__init__()
        self.working_memory = WorkingMemory()
        self.short_term = ShortTermMemory()
        self.long_term = LongTermMemory()
        self.associative = AssociativeMemory()
        self.procedural = ProceduralMemory()
        self.episodic = EpisodicMemory()
        self.semantic = SemanticMemory()
        
    def process_experience(self, experience: str, emotional_valence: float = 0.0) -> Dict[str, Any]:
        """
        Processa un'esperienza usando tutti i sistemi di memoria
        
        Args:
            experience: L'esperienza da processare
            emotional_valence: La valenza emotiva (-1.0 a 1.0)
            
        Returns:
            Dizionario con i risultati del processamento
        """
        # Validazione input
        if not experience:
            raise ValueError("L'esperienza non può essere vuota")
        if not -1.0 <= emotional_valence <= 1.0:
            raise ValueError("La valenza emotiva deve essere tra -1.0 e 1.0")
            
        # Crea memory item
        memory_item = MemoryItem(
            content=experience,
            timestamp=datetime.now(),
            type='experience',
            emotional_valence=emotional_valence
        )
        
        # Processa nei vari sistemi
        self.working_memory.add_item(memory_item)
        self.short_term.add_item(memory_item)
        self.episodic.add_memory(experience, emotional_valence)
        
        # Estrai e processa concetti
        concepts = self._extract_concepts(experience)
        for concept in concepts:
            self.semantic.add_concept(concept, {'source': experience})
            
        # Aggiorna associazioni
        if len(concepts) > 1:
            for i in range(len(concepts)-1):
                self.associative.add_association(concepts[i], concepts[i+1])
                
        # Verifica consolidamento
        consolidation_performed = False
        if self._should_consolidate():
            self._consolidate_memories()
            consolidation_performed = True
            
        return {
            'memory_stored': True,
            'concepts_extracted': concepts,
            'consolidation_performed': consolidation_performed
        }
        
    def recall_memory(self, query: str, context: Dict = None) -> List[MemoryItem]:
        """
        Recupera memorie usando tutti i sistemi disponibili
        
        Args:
            query: La query di ricerca
            context: Contesto opzionale
            
        Returns:
            Lista di memorie rilevanti
        """
        results = []
        
        # Cerca nella working memory
        results.extend(self.working_memory.items)
        
        # Cerca nella short term
        results.extend(self.short_term.get_recent_items())
        
        # Cerca nella long term
        concepts = self._extract_concepts(query)
        if concepts:
            results.extend(self.long_term.get_associated_items(set(concepts)))
            
        # Cerca memorie episodiche
        episodic_results = self.episodic.recall(query, context)
        results.extend(episodic_results)
        
        # Rimuovi duplicati e ordina per rilevanza
        unique_results = list(set(results))
        unique_results.sort(key=lambda x: self._calculate_relevance(query, x.content), reverse=True)
        
        return unique_results
