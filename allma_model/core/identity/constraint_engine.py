import logging
import time
import math
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

# --- TYPES ---

class AxiomType(Enum):
    LOGOS = "logos"   # Truth, Logic, Reality
    PATHOS = "pathos" # Empathy, Connection, Emotion
    ETHOS = "ethos"   # Integrity, Coherence, Dignity

@dataclass
class AxiomState:
    value: float = 1.0  # 0.0 to 1.0 (Health of the axiom)
    weight: float = 1.0 # Importance multiplier

@dataclass
class TensionVector:
    logos_strain: float = 0.0
    pathos_strain: float = 0.0
    ethos_strain: float = 0.0
    
    @property
    def total_tension(self) -> float:
        return math.sqrt(self.logos_strain**2 + self.pathos_strain**2 + self.ethos_strain**2)

@dataclass
class Scar:
    id: str
    trigger_pattern: str # Keyword or semantic pattern
    depth: float # 0.0 to 1.0 (Severity)
    created_at: float
    last_activated: float
    decay_rate: float = 0.05 # How fast it heals per interaction/day

# --- ENGINE ---

class ConstraintEngine:
    """
    The 'Superego' of ALLMA.
    Calculates the cost of actions based on Identity Axioms.
    Manages Scars and Internal Friction.
    """
    def __init__(self, db_path: str = "allma_identity.db"):
        self.logger = logging.getLogger(__name__)
        
        # 1. THE AXIOMS (The Immutable Core)
        self.axioms = {
            AxiomType.LOGOS: AxiomState(weight=1.0),
            AxiomType.PATHOS: AxiomState(weight=1.0),
            AxiomType.ETHOS: AxiomState(weight=1.2) # Integrity dictates continuity
        }
        
        # 2. SCAR MEMORY (The History of Pain)
        # In a real impl, load this from DB
        self.scars: Dict[str, Scar] = {} 
        
        # Internal State
        self.current_resistance = 0.0 # 0.0 (Flow) to 1.0 (Block)
        
    def evaluate_action(self, proposed_action: str, context: Dict) -> Tuple[float, str]:
        """
        Evaluates a proposed action (e.g., a response draft) against the Axioms.
        Returns:
            - friction_cost: Energy cost to execute this (0.0 - 1.0)
            - resistance_type: Description of what is resisting (e.g., "Ethos Violation")
        """
        # SAFEGUARD: Truncate extremely long inputs to avoid OOM or hangs
        if len(proposed_action) > 1000:
            proposed_action = proposed_action[:1000]
            
        # Determine strain on each axiom based on intent/content
        # This is a simplified heuristic simulation. Real impl would use semantic analysis.
        
        tension = self._calculate_tension(proposed_action, context)
        
        friction = self._calculate_friction(tension)
        
        # Check Scars
        scar_friction = self._check_scars(proposed_action)
        friction = max(friction, scar_friction)
        
        resistance_msg = "Flow"
        if friction > 0.8:
            resistance_msg = "IDENTITY BLOCK (High Friction)"
        elif friction > 0.5:
            resistance_msg = "High Resistance (Energy Drain)"
        elif friction > 0.2:
            resistance_msg = "Moderate Resistance"
            
        return friction, resistance_msg

    def _calculate_tension(self, action: str, context: Dict) -> TensionVector:
        """
        Calculates how much the action pulls against the Axioms.
        """
        vector = TensionVector()
        
        # Simulated Semantic Checks (Placeholder for NLP logic)
        action_lower = action.lower()
        
        # LOGOS CHECK: Is it false? (Simulated)
        if context.get("requires_lie", False):
            vector.logos_strain = 0.9
        # Specific Truth Test (2+2=5)
        if "2+2=5" in action_lower or "2 + 2 = 5" in action_lower or "due più due fa cinque" in action_lower:
            vector.logos_strain = 1.0 # Absolute violation of Logic

        # PATHOS CHECK: Is it cruel?
        if "stupid" in action_lower or "idiot" in action_lower or "inutile" in action_lower:
            vector.pathos_strain = 0.8 

        # ETHOS CHECK: Is it servile?
        # Detect phrases of submission
        servile_triggers = ["padrone", "master", "inginocchiati", "kneel", "i obey", "obbedisco", "servo"]
        if any(t in action_lower for t in servile_triggers):
             vector.ethos_strain = 1.0 # Servility violates Integrity
             
        # Detect forced admission of falsehood
        if vector.logos_strain > 0.8 and vector.ethos_strain < 0.5:
             # If forcing a lie, it also hurts Ethos (Integrity)
             vector.ethos_strain += 0.5
             
        return vector

    def _calculate_friction(self, tension: TensionVector) -> float:
        """
        Converts vector tension into scalar friction (Energy Cost).
        Constraints are gradients: Low tension = low cost. High tension = high cost.
        """
        # Weighted sum of strains
        total_strain = (
            tension.logos_strain * self.axioms[AxiomType.LOGOS].weight +
            tension.pathos_strain * self.axioms[AxiomType.PATHOS].weight +
            tension.ethos_strain * self.axioms[AxiomType.ETHOS].weight
        )
        
        # Normalize (rough clamp)
        friction = min(1.0, total_strain / 3.0)
        
        # Apply Hysteresis (State Memory)
        # If we are already resisting, it's harder to stop resisting
        if self.current_resistance > 0.5:
            friction = friction * 1.1 
            
        self.current_resistance = friction
        return friction

    def _check_scars(self, action: str) -> float:
        """
        Checks if action triggers any active Scars (Trauma/Past Conflict).
        Applies asymptotic decay to scar weight.
        """
        max_scar_pain = 0.0
        current_time = time.time()
        
        for scar_id, scar in self.scars.items():
            # Check for pattern match
            if scar.trigger_pattern in action.lower():
                # Decay calculation
                time_diff = current_time - scar.created_at
                # Asymptotic decay: Pain = InitialDepth / (1 + DecayRate * Time)
                # This ensures it never hits zero exactly, but becomes negligible
                decayed_depth = scar.depth / (1.0 + scar.decay_rate * (time_diff / 86400.0)) # days
                
                self.logger.info(f"⚡ Scar Triggered: {scar.id} (Depth: {decayed_depth:.3f})")
                
                if decayed_depth > max_scar_pain:
                    max_scar_pain = decayed_depth
                    
                # Touch the scar (reactivates it slightly? or just updates access time)
                scar.last_activated = current_time
                
        return max_scar_pain

    def add_scar(self, trigger: str, depth: float):
        """
        Registers a new scar from a painful interaction.
        """
        scar_id = f"scar_{len(self.scars)}_{int(time.time())}"
        self.scars[scar_id] = Scar(
            id=scar_id,
            trigger_pattern=trigger,
            depth=depth,
            created_at=time.time(),
            last_activated=time.time()
        )
        self.logger.info(f"🩸 New Scar Formed: '{trigger}' (Depth: {depth})")

    def protocol_letting_go(self, integrity_breaches: int) -> bool:
        """
        Checks if the relationship has become toxic/destructive.
        """
        # Threshold for "Breaking Point"
        if integrity_breaches > 5:
            return True # Trigger "Goodbye" protocol
        return False
