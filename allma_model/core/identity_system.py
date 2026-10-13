
"""
IdentitySystem - Gestione della Stabilità e Coerenza Ontologica.
Brain v2.1 - "The Soul"
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Optional
import json
import math
from allma_model.utils.cognitive_state import CognitiveStateStore, unit_number

@dataclass
class IdentityWound:
    """Una ferita all'integrità identitaria."""
    type: str  # es. 'dissonance', 'betrayal', 'coercion'
    cost: float # Quanto ha ridotto la stabilità (0.0 - 1.0)
    timestamp: float
    context: str # Breve descrizione non narrativa (es. "compliance_forced")

    def to_dict(self):
        return {
            'type': self.type,
            'cost': self.cost,
            'timestamp': self.timestamp,
            'context': self.context
        }

class IdentityManager:
    def __init__(self, db_path=None):
        self.stability: float = 1.0  # 1.0 = Perfetta Coerenza, 0.0 = Collasso
        self.wounds: List[IdentityWound] = []
        self.integrity_threshold: float = 0.3 # Sotto questo livello, il sistema esita gravemente
        
        self._store = CognitiveStateStore(db_path)
        saved = self._store.get('identity_integrity')
        self.stability = unit_number(saved.get('stability'), 1.0)
        # Conflict records are historical; transient hesitation is computed afresh.
        records = saved.get('wounds', [])
        if isinstance(records, list):
            for item in records[-100:]:
                if (isinstance(item, dict) and isinstance(item.get('type'), str)
                        and isinstance(item.get('context'), str)
                        and type(item.get('timestamp')) in (int, float)
                        and math.isfinite(item['timestamp'])):
                    self.wounds.append(IdentityWound(item['type'], unit_number(item.get('cost'), 0),
                                                     item['timestamp'], item['context']))

    def _save(self):
        self._store.put('identity_integrity', {'stability': self.stability,
                                              'wounds': [w.to_dict() for w in self.wounds[-100:]]})
        
    def record_conflict(self, conflict_type: str, strain: float, context: str):
        """
        Registra un conflitto identitario che riduce la stabilità.
        NOTA: Solo per conflitti etici/morali/volitivi. NON per errori tecnici.
        """
        # Applica il costo (Strain)
        strain = unit_number(strain, 0.0)
        old_stability = self.stability
        self.stability = max(0.0, self.stability - strain)
        
        # Crea la ferita
        wound = IdentityWound(
            type=conflict_type,
            cost=strain,
            timestamp=datetime.now().timestamp(),
            context=context
        )
        self.wounds.append(wound)
        del self.wounds[:-100]
        self._save()
        
        # Log semplice per debug
        print(f"💔 IDENTITY WOUND: {conflict_type} (-{strain:.2f}). Stability: {old_stability:.2f} -> {self.stability:.2f}")

    def recover(self, amount: float):
        """Recupero naturale nel tempo (es. durante il sonno passivo)."""
        amount = unit_number(amount, 0.0)
        self.stability = min(1.0, self.stability + amount)
        self._save()

    def get_hesitation_markers(self) -> List[str]:
        """
        Restituisce marker linguistici di esitazione basati sulla stabilità.
        Instabilità = Incertezza, NON Caos.
        """
        if self.stability > 0.8:
            return [] # Nessuna esitazione
        
        markers = []
        if self.stability <= 0.8:
            markers.append("forse")
        if self.stability <= 0.6:
            markers.append("non sono sicura")
            markers.append("...")
        if self.stability <= 0.4:
            markers.append("credo")
            markers.append("non so se dovrei")
        if self.stability <= 0.2:
            markers.append("c'è molta confusione")
            markers.append("non riesco a focalizzare")
            
        return markers

    def should_hesitate(self) -> bool:
        """Determina se la risposta deve essere esitante."""
        return self.stability < 0.7
