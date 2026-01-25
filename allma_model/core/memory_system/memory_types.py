"""
Definizione dei tipi di memoria utilizzati nel sistema avanzato
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Any, Optional
try:
    import numpy as np
except ImportError:
    np = None

# Fallback for type hinting if numpy is missing
if np is None:
    class MockNumpy:
        class ndarray: pass
        def random(self, *args): return [0.0] * 768
        def rand(self, *args): return [0.0] * 768
        def exp(self, x): return 1.0
        def dot(self, a, b): return 0.0
        def array(self, x): return x
        
        class linalg:
            @staticmethod
            def norm(x): return 1.0
            
    np = MockNumpy()

@dataclass
class Memory:
    """Classe base per una memoria"""
    content: str
    importance: float
    timestamp: datetime
    context: Dict[str, Any]
    embedding: Optional[np.ndarray] = None
    
    def __post_init__(self):
        if self.embedding is None:
            # Placeholder per l'embedding - in produzione useremmo un modello reale
            self.embedding = np.random.rand(768)  # Dimensione standard BERT

@dataclass
class MemoryNode:
    """Nodo di memoria con supporto per collegamenti associativi"""
    memory: Memory
    connections: List['MemoryConnection'] = field(default_factory=list)
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    decay_rate: float = 0.1  # Tasso di decadimento della memoria
    
    def access(self):
        """Accede alla memoria, aggiornando statistiche e forza"""
        self.access_count += 1
        self.last_accessed = datetime.now()
        
    def get_strength(self) -> float:
        """Calcola la forza attuale della memoria considerando il decadimento"""
        if not self.last_accessed:
            return 0.0
        
        time_diff = (datetime.now() - self.last_accessed).total_seconds()
        decay = np.exp(-self.decay_rate * time_diff / (24 * 3600))  # Decadimento esponenziale
        base_strength = 1.0 - (1.0 / (1 + self.access_count))
        return base_strength * decay

@dataclass
class MemoryConnection:
    """Connessione tra due nodi di memoria"""
    target: MemoryNode
    relationship_type: str
    strength: float = 1.0
    created_at: datetime = field(default_factory=datetime.now)
    
    def reinforce(self, amount: float = 0.1):
        """Rinforza la connessione"""
        self.strength = min(1.0, self.strength + amount)
    
    def weaken(self, amount: float = 0.1):
        """Indebolisce la connessione"""
        self.strength = max(0.0, self.strength - amount)

@dataclass
class EmotionalMemory:
    """Gestisce la componente emotiva delle memorie"""
    emotional_valence: float  # -1.0 (molto negativo) a 1.0 (molto positivo)
    emotional_arousal: float  # 0.0 (calmo) a 1.0 (eccitato)
    emotional_dominance: float  # 0.0 (sottomesso) a 1.0 (dominante)
    emotional_tags: List[str] = field(default_factory=list)
    
    def get_emotional_vector(self) -> np.ndarray:
        """Restituisce un vettore che rappresenta lo stato emotivo"""
        return np.array([
            self.emotional_valence,
            self.emotional_arousal,
            self.emotional_dominance
        ])
    
    def calculate_emotional_similarity(self, other: 'EmotionalMemory') -> float:
        """Calcola la similarità emotiva con un'altra memoria"""
        vec1 = self.get_emotional_vector()
        vec2 = other.get_emotional_vector()
        return float(np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2)))

class EmotionalPattern:
    """Identifica e traccia pattern emotivi nel tempo"""
    def __init__(self):
        self.pattern_sequence: List[EmotionalMemory] = []
        self.frequency: Dict[str, int] = {}
        self.triggers: Dict[str, List[str]] = {}
        
    def add_emotional_state(self, emotional_memory: EmotionalMemory, context: Dict[str, Any]):
        """Aggiunge un nuovo stato emotivo e aggiorna i pattern"""
        self.pattern_sequence.append(emotional_memory)
        
        # Identifica trigger dal contesto
        for key, value in context.items():
            if key not in self.triggers:
                self.triggers[key] = []
            if str(value) not in self.triggers[key]:
                self.triggers[key].append(str(value))
        
        # Aggiorna frequenze
        for tag in emotional_memory.emotional_tags:
            self.frequency[tag] = self.frequency.get(tag, 0) + 1
    
    def get_dominant_emotions(self, top_n: int = 3) -> List[str]:
        """Restituisce le emozioni più frequenti"""
        sorted_emotions = sorted(
            self.frequency.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [emotion for emotion, _ in sorted_emotions[:top_n]]
    
    def identify_triggers(self) -> Dict[str, List[str]]:
        """Identifica i trigger più comuni per le emozioni"""
        return {
            emotion: [
                trigger for trigger_type in self.triggers
                for trigger in self.triggers[trigger_type]
            ]
            for emotion in self.get_dominant_emotions()
        }
