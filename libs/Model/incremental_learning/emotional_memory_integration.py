from typing import Dict, List, Set, Optional, Any, Tuple
import numpy as np
from datetime import datetime
import time
import hashlib
import json
import os
import threading
from collections import defaultdict
from dataclasses import dataclass, field
from .memory_system import EnhancedMemorySystem
from .emotional_system import EmotionalSystem, EmotionalState

@dataclass
class MemoryTrace:
    """Classe base per le memorie nel sistema ALLMA"""
    content: str
    context: Optional[Dict] = None
    emotional_valence: float = 0.0
    importance: float = 0.5
    timestamp: Optional[float] = None
    
    def __init__(self, content: str, context: Optional[Dict] = None, 
                 emotional_valence: float = 0.0, importance: float = 0.5,
                 timestamp: Optional[float] = None):
        self.content = content
        self.context = context or {}
        self.emotional_valence = emotional_valence
        self.importance = importance
        self.timestamp = timestamp or time.time()
        self.last_recall = None  # Timestamp dell'ultimo recupero
        self.curiosity_impact = 0.0  # Nuovo campo per tracciare l'impatto sulla curiosità
        
    def update_last_recall(self):
        """Aggiorna il timestamp dell'ultimo recupero"""
        self.last_recall = time.time()
        
    def get_age(self):
        """Calcola l'età della memoria in secondi"""
        return time.time() - self.timestamp
        
    def get_recall_age(self):
        """Calcola il tempo dall'ultimo recupero in secondi"""
        if not self.last_recall:
            return float('inf')
        return time.time() - self.last_recall
        
    def calculate_activation(self, current_time: float):
        """Calcola il livello di attivazione della memoria"""
        age = current_time - self.timestamp
        recall_age = float('inf') if not self.last_recall else current_time - self.last_recall
        
        # Parametri per il calcolo dell'attivazione
        base_activation = 1.0
        age_decay = 0.1
        recall_boost = 0.2
        emotional_boost = abs(self.emotional_valence) * 0.3
        importance_boost = self.importance * 0.4
        
        # Calcolo dell'attivazione
        activation = base_activation * (
            np.exp(-age_decay * age) +  # Decadimento basato sull'età
            np.exp(-age_decay * recall_age) * recall_boost +  # Boost dal recupero recente
            emotional_boost +  # Boost dalle emozioni
            importance_boost  # Boost dall'importanza
        )
        
        return activation
        
    def update_curiosity_impact(self, curiosity_state: Dict):
        """Aggiorna l'impatto della memoria sulla curiosità"""
        # Calcola la novità della memoria
        age_factor = np.exp(-0.1 * self.get_age())
        
        # Considera la complessità del contenuto
        complexity = len(str(self.content)) / 1000  # Normalizzato per lunghezza
        
        # Considera la rilevanza emotiva
        emotional_impact = abs(self.emotional_valence)
        
        # Calcola l'impatto sulla curiosità
        self.curiosity_impact = (
            age_factor * 0.4 +
            complexity * 0.3 +
            emotional_impact * 0.3
        )

class EmotionalMemoryIntegration:
    """Integra il sistema emotivo con il sistema di memoria potenziato"""
    
    def __init__(self):
        """Inizializza il sistema di integrazione emotiva-memoria"""
        self.memory_system = None  # Sarà impostato esternamente
        self.emotional_system = None  # Sarà impostato esternamente
        self.memories = []
        
    def process_input(self, input_text: str, context: Optional[Dict] = None):
        """Elabora l'input attraverso i sistemi emotivo e di memoria"""
        if not context:
            context = {}
            
        # Analizza il contenuto emotivo
        emotional_analysis = self.emotional_system.analyze_text(input_text)
        emotional_valence = emotional_analysis.get('valence', 0.0)
        
        # Determina se l'esperienza è significativa
        is_significant = abs(emotional_valence) > 0.7 or len(input_text.split()) > 20
        
        # Aggiorna il contesto con lo stato emotivo
        context['emotional_state'] = {
            'valence': emotional_valence,
            'is_significant': is_significant
        }
        
        # Crea una nuova memoria episodica
        memory = MemoryTrace(
            content=input_text,
            context=context,
            emotional_valence=emotional_valence,
            importance=1.0 if is_significant else 0.5,
            timestamp=context['timestamp']
        )
        
        # Aggiorna il sistema di memoria
        self.memory_system.process_experience(memory.content, memory.emotional_valence)
        
        # Recupera memorie correlate
        memories = self.memory_system.recall_memory(input_text, context)
        
        # Aggiorna lo stato emotivo
        self._update_emotional_state_from_memories(memories)
        
        # Processa l'input attraverso il sistema di curiosità
        curiosity_response = self.memory_system.curiosity.process_input(input_text, context)
        
        # Integra curiosità con le memorie
        integrated_response = self.memory_system._integrate_curiosity_with_memories(
            curiosity_response,
            memories,
            context
        )
        
        return self.emotional_system.current_state, integrated_response
        
    def _extract_concepts(self, text: str, context: Optional[Dict] = None) -> Dict:
        """Estrae concetti dal testo con i loro attributi e relazioni"""
        concepts = {}
        
        # Lista di concetti predefiniti con attributi
        predefined_concepts = {
            'gatto': {
                'attributes': ['mammifero', 'domestico', 'affettuoso'],
                'relationships': [('è', 'animale'), ('ha', 'pelo'), ('evoca_emozione', 'positivo')]
            },
            'giornata': {
                'attributes': ['bella', 'importante', 'significativa'],
                'relationships': [('è', 'tempo'), ('evoca_emozione', 'positivo')]
            },
            'progetto': {
                'attributes': ['nuovo', 'interessante', 'stimolante'],
                'relationships': [('è', 'lavoro'), ('evoca_emozione', 'positivo')]
            }
        }
        
        # Cerca concetti nel testo
        words = text.lower().split()
        for word in words:
            # Controlla i concetti predefiniti
            for concept, info in predefined_concepts.items():
                if concept in word:
                    concepts[concept] = info.copy()
                    
            # Estrai attributi dal contesto
            if context and 'attributes' in context:
                for attr in context['attributes']:
                    if attr in word:
                        concept = words[max(0, words.index(word)-1)]
                        if concept not in concepts:
                            concepts[concept] = {'attributes': [], 'relationships': []}
                        if attr not in concepts[concept]['attributes']:
                            concepts[concept]['attributes'].append(attr)
                            
        return concepts
        
    def _update_emotional_state_from_memories(self, memories: List[MemoryTrace]) -> None:
        """Aggiorna lo stato emotivo basato sulle memorie"""
        if not memories:
            return
            
        total_valence = 0.0
        total_weight = 0.0
        
        for memory in memories:
            # Calcola il peso della memoria
            age = memory.get_age()
            importance = memory.importance
            weight = importance * np.exp(-0.1 * age)  # Decadimento esponenziale
            
            # Aggiorna i totali
            total_valence += memory.emotional_valence * weight
            total_weight += weight
            
        if total_weight > 0:
            # Calcola la valenza emotiva media pesata
            average_valence = total_valence / total_weight
            
            # Aggiorna lo stato emotivo
            self.emotional_system.update_state(average_valence)
            
    def generate_response(self, input_text: str, context: Optional[Dict] = None):
        """Genera una risposta basata sullo stato emotivo e le memorie"""
        # Recupera memorie rilevanti
        memories = self.memory_system.recall_memory(input_text, context)
        
        # Seleziona le memorie più rilevanti
        relevant_memories = self._select_relevant_memories(memories)
        
        # Arricchisci il contesto con lo stato emotivo
        enriched_context = self._enrich_context(context, self.emotional_system.current_state)
        
        # TODO: Implementa la logica per generare una risposta basata su memorie e contesto
        return "Risposta generata basata su memorie ed emozioni"
        
    def _select_relevant_memories(self, memories: List[MemoryTrace]) -> List[MemoryTrace]:
        """Seleziona le memorie più rilevanti per la risposta"""
        if not memories:
            return []
            
        # Ordina le memorie per importanza e attivazione
        current_time = time.time()
        memories.sort(
            key=lambda m: (
                m.importance * 0.6 +  # Peso dell'importanza
                m.calculate_activation(current_time) * 0.4  # Peso dell'attivazione
            ),
            reverse=True
        )
        
        # Seleziona le top N memorie
        return memories[:5]  # Limita a 5 memorie
        
    def _enrich_context(self, context: Optional[Dict], emotional_state: EmotionalState) -> Dict:
        """Arricchisce il contesto con informazioni emotive"""
        if not context:
            context = {}
            
        context['emotional_state'] = {
            'valence': emotional_state.valence,
            'arousal': emotional_state.arousal,
            'dominance': emotional_state.dominance
        }
        
        return context
        
    def _serialize_memory_trace(self, memory_trace: MemoryTrace) -> Dict:
        """Serializza un oggetto MemoryTrace in un dizionario"""
        return {
            'content': memory_trace.content,
            'context': memory_trace.context,
            'emotional_valence': memory_trace.emotional_valence,
            'importance': memory_trace.importance,
            'timestamp': memory_trace.timestamp,
            'last_recall': memory_trace.last_recall,
            'curiosity_impact': memory_trace.curiosity_impact
        }
        
    def _serialize_memories(self, memories: List[MemoryTrace]) -> List[Dict]:
        """Serializza le memorie in un formato JSON-compatibile"""
        return [self._serialize_memory_trace(m) for m in memories]
        
    def save_state(self, filename_prefix: str):
        """Salva lo stato di entrambi i sistemi"""
        # Salva lo stato del sistema emotivo
        emotional_state = {
            'current_state': self.emotional_system.current_state.__dict__,
            'history': self.emotional_system.history
        }
        with open(f"{filename_prefix}_emotional.json", 'w') as f:
            json.dump(emotional_state, f)
            
        # Salva lo stato del sistema di memoria
        memory_state = {
            'memories': self._serialize_memories(self.memories)
        }
        with open(f"{filename_prefix}_memory.json", 'w') as f:
            json.dump(memory_state, f)
            
    def _deserialize_memory_trace(self, data: Dict) -> MemoryTrace:
        """Deserializza un dizionario in un oggetto MemoryTrace"""
        memory = MemoryTrace(
            content=data['content'],
            context=data['context'],
            emotional_valence=data['emotional_valence'],
            importance=data['importance'],
            timestamp=data['timestamp']
        )
        memory.last_recall = data.get('last_recall')
        memory.curiosity_impact = data.get('curiosity_impact', 0.0)
        return memory
        
    def _deserialize_memories(self, memories: List[Dict]) -> List[MemoryTrace]:
        """Deserializza le memorie da un formato JSON-compatibile"""
        return [self._deserialize_memory_trace(m) for m in memories]
        
    def load_state(self, filename_prefix: str):
        """Carica lo stato di entrambi i sistemi"""
        # Carica lo stato del sistema emotivo
        try:
            with open(f"{filename_prefix}_emotional.json", 'r') as f:
                emotional_state = json.load(f)
                self.emotional_system.current_state = EmotionalState(**emotional_state['current_state'])
                self.emotional_system.history = emotional_state['history']
        except FileNotFoundError:
            print(f"File {filename_prefix}_emotional.json non trovato")
            
        # Carica lo stato del sistema di memoria
        try:
            with open(f"{filename_prefix}_memory.json", 'r') as f:
                memory_state = json.load(f)
                self.memories = self._deserialize_memories(memory_state['memories'])
        except FileNotFoundError:
            print(f"File {filename_prefix}_memory.json non trovato")
            
    def process_experience(self, experience: str, emotion: Any, context: Dict):
        """Processa un'esperienza integrando emozioni e memoria"""
        # Crea una nuova memoria
        memory = MemoryTrace(
            content=experience,
            context=context,
            emotional_valence=emotion.valence,
            importance=abs(emotion.valence),  # L'importanza è proporzionale all'intensità emotiva
            timestamp=time.time()
        )
        
        # Aggiorna il sistema di memoria
        self.memory_system.process_experience(
            experience=memory.content,
            emotional_valence=memory.emotional_valence
        )
        
        # Aggiorna lo stato emotivo
        self.emotional_system.update_state(emotion.valence)
        
        return {
            'memory_stored': True,
            'emotional_state_updated': True
        }
