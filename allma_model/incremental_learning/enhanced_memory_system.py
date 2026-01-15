"""
Sistema di memoria potenziato per ALLMA
"""

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import numpy as np
import time
import json

class MemoryItem:
    """Rappresenta un elemento della memoria con metadati"""
    
    def __init__(self, content: str, memory_type: str,
                 context: Optional[Dict] = None,
                 importance: float = 0.5):
        self.content = content
        self.memory_type = memory_type
        self.context = context or {}
        self.importance = importance
        self.creation_time = time.time()
        self.last_access = None
        self.access_count = 0
        self.associations: Dict[str, float] = {}
        
    def access(self):
        """Registra un accesso alla memoria"""
        self.last_access = time.time()
        self.access_count += 1
        
    def add_association(self, memory_id: str, strength: float = 1.0):
        """Aggiunge un'associazione con un'altra memoria"""
        self.associations[memory_id] = strength
        
    def update_association(self, memory_id: str, strength: float):
        """Aggiorna la forza di un'associazione"""
        if memory_id in self.associations:
            self.associations[memory_id] = strength
            
    def get_age(self) -> float:
        """Restituisce l'età della memoria in secondi"""
        return time.time() - self.creation_time
        
    def get_last_access_age(self) -> Optional[float]:
        """Restituisce il tempo dall'ultimo accesso in secondi"""
        if self.last_access is None:
            return None
        return time.time() - self.last_access
        
    def calculate_activation(self) -> float:
        """Calcola il livello di attivazione della memoria"""
        age = self.get_age()
        recency = 1.0
        if self.last_access is not None:
            recency = 1.0 / (1.0 + self.get_last_access_age())
            
        frequency = np.log1p(self.access_count)
        
        activation = (0.4 * recency + 
                     0.3 * frequency + 
                     0.3 * self.importance)
        
        return min(1.0, activation)
        
    def to_dict(self) -> Dict:
        """Converte l'oggetto in un dizionario"""
        return {
            'content': self.content,
            'memory_type': self.memory_type,
            'context': self.context,
            'importance': self.importance,
            'creation_time': self.creation_time,
            'last_access': self.last_access,
            'access_count': self.access_count,
            'associations': self.associations
        }
        
    @classmethod
    def from_dict(cls, data: Dict) -> 'MemoryItem':
        """Crea un oggetto MemoryItem da un dizionario"""
        memory = cls(
            content=data['content'],
            memory_type=data['memory_type'],
            context=data['context'],
            importance=data['importance']
        )
        memory.creation_time = data['creation_time']
        memory.last_access = data['last_access']
        memory.access_count = data['access_count']
        memory.associations = data['associations']
        return memory

class MemoryTrace:
    def __init__(self, content: str, context: Optional[Dict] = None,
                 emotional_valence: float = 0.0, importance: float = 0.5,
                 timestamp: Optional[float] = None):
        self.content = content
        self.context = context or {}
        self.emotional_valence = emotional_valence
        self.importance = importance
        self.timestamp = timestamp or time.time()
        self.last_recall = None
        self.curiosity_impact = 0.0

    def update_last_recall(self):
        """Aggiorna il timestamp dell'ultimo recupero"""
        self.last_recall = time.time()

    def get_age(self) -> float:
        """Calcola l'età della memoria in secondi"""
        return time.time() - self.timestamp

    def get_recall_age(self) -> Optional[float]:
        """Calcola il tempo dall'ultimo recupero in secondi"""
        if self.last_recall is None:
            return None
        return time.time() - self.last_recall

    def calculate_activation(self, current_time: float) -> float:
        """Calcola il livello di attivazione della memoria"""
        age = current_time - self.timestamp
        decay = 0.1  # Fattore di decadimento
        activation = self.importance * np.exp(-decay * age)
        
        if self.last_recall is not None:
            recall_age = current_time - self.last_recall
            recall_boost = 0.5 * np.exp(-decay * recall_age)
            activation += recall_boost
            
        return min(1.0, activation)

    def update_curiosity_impact(self, curiosity_state: Dict):
        """Aggiorna l'impatto della memoria sulla curiosità"""
        novelty = curiosity_state.get('novelty', 0.0)
        relevance = curiosity_state.get('relevance', 0.0)
        
        # Calcola l'impatto sulla curiosità come media pesata
        self.curiosity_impact = 0.7 * novelty + 0.3 * relevance

class EnhancedMemorySystem:
    def __init__(self):
        """Inizializza il sistema di memoria potenziato"""
        self.episodic = {}  # Memorie episodiche
        self.semantic = {}  # Memorie semantiche
        self.procedural = {}  # Memorie procedurali
        self.associations = {}  # Associazioni tra memorie
        self.emotional_index = {}  # Indice emotivo delle memorie
        
    def store_memory(self, memory_type: str, content: str,
                    context: Optional[Dict] = None,
                    emotional_valence: float = 0.0,
                    importance: float = 0.5) -> str:
        """
        Memorizza una nuova memoria
        
        Args:
            memory_type: Tipo di memoria (episodic, semantic, procedural)
            content: Contenuto della memoria
            context: Contesto della memoria
            emotional_valence: Valenza emotiva (-1 a 1)
            importance: Importanza della memoria (0 a 1)
            
        Returns:
            ID della memoria memorizzata
        """
        memory = MemoryTrace(
            content=content,
            context=context,
            emotional_valence=emotional_valence,
            importance=importance
        )
        
        # Genera un ID unico per la memoria
        memory_id = f"{memory_type}_{int(time.time())}"
        
        # Memorizza in base al tipo
        if memory_type == 'episodic':
            self.episodic[memory_id] = memory
        elif memory_type == 'semantic':
            self.semantic[memory_id] = memory
        elif memory_type == 'procedural':
            self.procedural[memory_id] = memory
        else:
            raise ValueError(f"Tipo di memoria non valido: {memory_type}")
            
        # Aggiorna l'indice emotivo
        self._update_emotional_index(memory_id, memory)
            
        return memory_id
        
    def retrieve_memory(self, memory_id: str) -> Optional[MemoryTrace]:
        """Recupera una memoria dato il suo ID"""
        memory = None
        
        # Cerca nei diversi tipi di memoria
        if memory_id.startswith('episodic_'):
            memory = self.episodic.get(memory_id)
        elif memory_id.startswith('semantic_'):
            memory = self.semantic.get(memory_id)
        elif memory_id.startswith('procedural_'):
            memory = self.procedural.get(memory_id)
            
        if memory:
            memory.update_last_recall()
            
        return memory
        
    def search_memories(self, query: str, context: Optional[Dict] = None,
                       memory_type: Optional[str] = None) -> List[Tuple[str, MemoryTrace]]:
        """
        Cerca memorie in base a query e contesto
        
        Args:
            query: Query di ricerca
            context: Contesto per filtrare i risultati
            memory_type: Tipo di memoria da cercare
            
        Returns:
            Lista di tuple (id, memoria)
        """
        results = []
        
        # Determina quali memorie cercare
        memories_to_search = []
        if memory_type == 'episodic' or memory_type is None:
            memories_to_search.append(self.episodic)
        if memory_type == 'semantic' or memory_type is None:
            memories_to_search.append(self.semantic)
        if memory_type == 'procedural' or memory_type is None:
            memories_to_search.append(self.procedural)
            
        # Cerca in tutte le memorie selezionate
        current_time = time.time()
        for memory_dict in memories_to_search:
            for memory_id, memory in memory_dict.items():
                relevance = self._calculate_relevance(query, memory.content)
                if context:
                    context_match = self._match_context(memory.context, context)
                    relevance *= context_match
                    
                activation = memory.calculate_activation(current_time)
                final_score = relevance * activation
                
                if final_score > 0.3:  # Soglia minima di rilevanza
                    results.append((memory_id, memory))
                    
        # Ordina per rilevanza
        results.sort(key=lambda x: x[1].calculate_activation(current_time), reverse=True)
        return results
        
    def associate_memories(self, memory_id1: str, memory_id2: str,
                         strength: float = 1.0):
        """Crea un'associazione tra due memorie"""
        if memory_id1 not in self.associations:
            self.associations[memory_id1] = {}
        self.associations[memory_id1][memory_id2] = strength
        
        if memory_id2 not in self.associations:
            self.associations[memory_id2] = {}
        self.associations[memory_id2][memory_id1] = strength
        
    def get_associated_memories(self, memory_id: str,
                              min_strength: float = 0.5) -> List[Tuple[str, float]]:
        """Recupera le memorie associate a una data memoria"""
        if memory_id not in self.associations:
            return []
            
        associations = self.associations[memory_id]
        return [(mid, strength) for mid, strength in associations.items()
                if strength >= min_strength]
        
    def _calculate_relevance(self, query: str, content: str) -> float:
        """Calcola la rilevanza tra query e contenuto"""
        # Implementazione semplificata - da migliorare con NLP
        query_words = set(query.lower().split())
        content_words = set(content.lower().split())
        
        intersection = query_words & content_words
        union = query_words | content_words
        
        if not union:
            return 0.0
            
        return len(intersection) / len(union)
        
    def _match_context(self, memory_context: Dict,
                      query_context: Dict) -> float:
        """Calcola la corrispondenza tra contesti"""
        if not memory_context or not query_context:
            return 1.0
            
        matches = 0
        total = 0
        
        for key, value in query_context.items():
            if key in memory_context:
                if isinstance(value, (int, float)):
                    # Per valori numerici, calcola similarità relativa
                    diff = abs(value - memory_context[key])
                    max_val = max(abs(value), abs(memory_context[key]))
                    if max_val > 0:
                        matches += 1 - (diff / max_val)
                    else:
                        matches += 1
                else:
                    # Per altri tipi, confronto esatto
                    matches += 1 if value == memory_context[key] else 0
                total += 1
                
        return matches / total if total > 0 else 1.0
        
    def _update_emotional_index(self, memory_id: str, memory: MemoryTrace):
        """Aggiorna l'indice emotivo"""
        valence = memory.emotional_valence
        if valence not in self.emotional_index:
            self.emotional_index[valence] = set()
        self.emotional_index[valence].add(memory_id)
        
    def get_emotional_memories(self, valence_range: Tuple[float, float]) -> List[Tuple[str, MemoryTrace]]:
        """Recupera memorie in un dato range di valenza emotiva"""
        results = []
        min_val, max_val = valence_range
        
        for valence, memory_ids in self.emotional_index.items():
            if min_val <= valence <= max_val:
                for memory_id in memory_ids:
                    memory = self.retrieve_memory(memory_id)
                    if memory:
                        results.append((memory_id, memory))
                        
        return results
        
    def consolidate_memories(self):
        """Consolida le memorie, rafforzando o indebolendo connessioni"""
        current_time = time.time()
        
        # Aggiorna le associazioni
        for memory_id1, associations in self.associations.items():
            memory1 = self.retrieve_memory(memory_id1)
            if not memory1:
                continue
                
            for memory_id2, strength in list(associations.items()):
                memory2 = self.retrieve_memory(memory_id2)
                if not memory2:
                    del associations[memory_id2]
                    continue
                    
                # Calcola nuovo peso dell'associazione
                age1 = memory1.get_age()
                age2 = memory2.get_age()
                recall1 = memory1.get_recall_age() or age1
                recall2 = memory2.get_recall_age() or age2
                
                # Rinforzo basato su recenti richiami
                recall_factor = np.mean([
                    np.exp(-0.1 * recall1),
                    np.exp(-0.1 * recall2)
                ])
                
                # Aggiorna forza dell'associazione
                new_strength = strength * (0.9 + 0.1 * recall_factor)
                associations[memory_id2] = new_strength
                
                # Se l'associazione è troppo debole, rimuovila
                if new_strength < 0.1:
                    del associations[memory_id2]
                    
    def save_to_file(self, filename: str):
        """Salva il sistema di memoria su file"""
        data = {
            'episodic': {k: self._serialize_memory(v) for k, v in self.episodic.items()},
            'semantic': {k: self._serialize_memory(v) for k, v in self.semantic.items()},
            'procedural': {k: self._serialize_memory(v) for k, v in self.procedural.items()},
            'associations': self.associations,
            'emotional_index': {str(k): list(v) for k, v in self.emotional_index.items()}
        }
        
        with open(filename, 'w') as f:
            json.dump(data, f)
            
    def load_from_file(self, filename: str):
        """Carica il sistema di memoria da file"""
        with open(filename, 'r') as f:
            data = json.load(f)
            
        self.episodic = {k: self._deserialize_memory(v) for k, v in data['episodic'].items()}
        self.semantic = {k: self._deserialize_memory(v) for k, v in data['semantic'].items()}
        self.procedural = {k: self._deserialize_memory(v) for k, v in data['procedural'].items()}
        self.associations = data['associations']
        self.emotional_index = {float(k): set(v) for k, v in data['emotional_index'].items()}
        
    def _serialize_memory(self, memory: MemoryTrace) -> Dict:
        """Serializza un oggetto MemoryTrace"""
        return {
            'content': memory.content,
            'context': memory.context,
            'emotional_valence': memory.emotional_valence,
            'importance': memory.importance,
            'timestamp': memory.timestamp,
            'last_recall': memory.last_recall,
            'curiosity_impact': memory.curiosity_impact
        }
        
    def _deserialize_memory(self, data: Dict) -> MemoryTrace:
        """Deserializza un dizionario in un oggetto MemoryTrace"""
        memory = MemoryTrace(
            content=data['content'],
            context=data['context'],
            emotional_valence=data['emotional_valence'],
            importance=data['importance'],
            timestamp=data['timestamp']
        )
        memory.last_recall = data['last_recall']
        memory.curiosity_impact = data['curiosity_impact']
        return memory
