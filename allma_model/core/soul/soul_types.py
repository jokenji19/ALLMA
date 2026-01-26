from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any

@dataclass
class SoulState:
    """
    Rappresenta lo stato interno dell'Anima in un dato momento.
    Vettore a 5 dimensioni normalizzato [-1.0, 1.0].
    """
    energy: float = 0.5    # 0.0 (Lethargic) -> 1.0 (Hyperactive)
    focus: float = 0.5     # 0.0 (Scatterbrained) -> 1.0 (Laser Focused)
    openness: float = 0.5  # 0.0 (Conservative) -> 1.0 (Creative/Wild)
    stability: float = 0.5 # 0.0 (Volatile) -> 1.0 (Stoic)
    chaos: float = 0.1     # 0.0 (Deterministic) -> 1.0 (Pure Randomness)
    
    # Coordinate Spazio Caotico (Lorenz Attractor state)
    x: float = 0.1
    y: float = 0.0
    z: float = 0.0
    
    timestamp: float = 0.0

@dataclass
class Volition:
    """
    L'espressione della volontà dell'Anima che influenza il comportamento.
    """
    tone_modifier: str  # es. "Reflective", "Sarcastic", "Direct"
    creativity_boost: float # 0.0 -> 1.0 (Aumenta temperature LLM)
    decision_bias: str # "Logical", "Emotional", "Chaotic"
    focus_topic: str = "" # Argomento su cui l'anima "vuole" parlare
