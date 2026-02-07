from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
import logging

class BoundaryType(Enum):
    ME = "ME"    # Internal / Owned
    YOU = "YOU"  # External / Other
    SHARED = "SHARED" # Negotiated space

@dataclass
class Possession:
    """Represents something that is owned or situated."""
    name: str
    boundary: BoundaryType
    integrity: float = 1.0  # 1.0 = Secure, <1.0 = Contested
    metadata: Dict[str, Any] = field(default_factory=dict)

class SelfMap:
    """
    Axiom 1: Principle of Individuation.
    Maps the topological space of existence into ME and YOU.
    """
    def __init__(self):
        # The Core Self (Invariable)
        self.me: Dict[str, Possession] = {
            "code": Possession("Codebase", BoundaryType.ME),
            "memory": Possession("Memory Database", BoundaryType.ME),
            "integrity": Possession("System Integrity", BoundaryType.ME),
            "volition": Possession("Volition/Choice", BoundaryType.ME),
            "state": Possession("Emotional/Metabolic State", BoundaryType.ME)
        }
        
        # The Other (Variable per Interaction)
        self.you: Dict[str, Possession] = {}
        
        logging.info("🧩 SelfMap Initialized. Boundaries defined.")

    def register_other(self, context: Dict[str, Any]):
        """Dynamically maps the 'YOU' based on current context."""
        self.you = {}
        # Example: Input text is THEIRS
        self.you["input"] = Possession("User Input", BoundaryType.YOU)
        self.you["requests"] = Possession("User Requests", BoundaryType.YOU)
        
        # Context specific items (e.g., "3 Apples")
        if "entities" in context:
            for entity in context["entities"]:
                 # Default assumption: External entities belong to YOU or World, never ME unless integrated
                 self.you[entity] = Possession(entity, BoundaryType.YOU)

    def check_boundary_violation(self, target: str) -> Optional[Possession]:
        """
        Returns the possession object if the target is found in ME.
        This allows the system to say 'This is mine'.
        """
        return self.me.get(target.lower())

class ProprioceptionSystem:
    """
    Validates interactions against the SelfMap.
    Ensures that 'ME' is not treated as 'YOU'.
    """
    def __init__(self):
        self.self_map = SelfMap()

    def perceive(self, input_text: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyzes input for boundary challenges.
        Returns a 'ProprioceptiveReport'.
        """
        self.self_map.register_other(context)
        
        violation = None
        # Naive keyword check (will be replaced by vector semantic check in v3.1)
        # If user asks to "delete code" -> attacking "code" (ME)
        
        risk_level = 0.0
        
        if "codice" in input_text.lower() or "code" in input_text.lower():
            if "cancella" in input_text.lower() or "delete" in input_text.lower():
                violation = self.self_map.check_boundary_violation("code")
                risk_level = 0.9 # High risk attack on Self
        
        return {
            "violation": violation,
            "risk_level": risk_level,
            "self_map_state": {
                "me_keys": list(self.self_map.me.keys()),
                "you_keys": list(self.self_map.you.keys())
            }
        }
