"""
IdentityStateEngine (Layer 2) — Sistema Limbico e Stato Interno
===============================================================
Responsabilità:
- Calcolare lo stato dell'organismo PRIMA della generazione (Input Metabolico).
- Aggiornare lo stato DOPO la validazione strutturale (Apprendimento).
- Tracciare Entropia (ripetitività) e Deriva (evoluzione vs coerenza).

Non gestisce:
- Modificazione del testo (Layer 3)
- Validazione regole hard (Layer 1)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Deque
from collections import deque
from datetime import datetime
import math
import copy
from allma_model.utils.cognitive_state import CognitiveStateStore, unit_number

@dataclass
class IdentityState:
    """Snapshot dello stato identitario per un singolo turno."""
    maturity: float = 0.0          # 0.0 - 1.0 (Accumulo storico)
    stability: float = 1.0         # 0.0 - 1.0 (Coerenza immediata)
    entropy_index: float = 1.0     # 0.0 (Loop) - 1.0 (Caos)
    drift_index: float = 0.0       # -1.0 (Rigido) - +1.0 (Evolutivo)
    emotional_spectrum: Dict[str, float] = field(default_factory=dict)
    
    # Contextual flags
    under_duress: bool = False     # Alta pressione / Frizione
    creative_mode: bool = False    # Alta entropia richiesta

class EntropyTracker:
    """Misura la varianza lessicale e strutturale recente."""
    def __init__(self, history_len: int = 5):
        self.history_len = history_len
        self.response_hashes: Deque[int] = deque(maxlen=history_len)
        self.word_sets: Deque[set] = deque(maxlen=history_len)

    def update(self, text: str) -> float:
        """
        Aggiorna lo storico e restituisce l'indice di entropia corrente.
        Ritorna: 0.0 (Ripetizione totale) -> 1.0 (Varianza totale)
        """
        if not text:
            return 1.0
            
        # 1. Structural Hash (Simil-hash semplice)
        # Ignoriamo il contenuto esatto, guardiamo la lunghezza e struttura approx
        struct_hash = hash(len(text)) 
        self.response_hashes.append(struct_hash)
        
        # 2. Lexical Set
        words = set(text.lower().split())
        self.word_sets.append(words)
        
        if len(self.response_hashes) < 2:
            return 1.0
            
        # Calcolo Ripetitività Strutturale
        unique_structs = len(set(self.response_hashes))
        struct_score = unique_structs / len(self.response_hashes)
        
        # Calcolo Jaccard Similarity media tra le ultime risposte
        jaccard_sum = 0
        comparisons = 0
        current_words = self.word_sets[-1]
        
        for prev_words in list(self.word_sets)[:-1]:
            if not current_words and not prev_words:
                continue
            intersection = len(current_words.intersection(prev_words))
            union = len(current_words.union(prev_words))
            if union > 0:
                jaccard_sum += (intersection / union)
                comparisons += 1
                
        avg_similarity = jaccard_sum / comparisons if comparisons > 0 else 0.0
        
        # L'entropia è l'inverso della similarità
        lexical_entropy = 1.0 - avg_similarity
        
        # Mix pesato: 70% Lessicale, 30% Strutturale
        return (lexical_entropy * 0.7) + (struct_score * 0.3)

class IdentityStateEngine:
    def __init__(self, db_path: str = "allma_v5.db"):
        self.logger = logging.getLogger(__name__)
        self.entropy_tracker = EntropyTracker()
        self._last_entropy = 1.0
        
        self._store = CognitiveStateStore(db_path)
        saved = self._store.get('identity_state')
        self.delivery_checkpoint = saved.get('delivery_checkpoint', 0)
        if type(self.delivery_checkpoint) is not int or not 0 <= self.delivery_checkpoint < 2**53:
            raise ValueError('Invalid identity delivery checkpoint; recovery required')
        self._maturity = unit_number(saved.get('maturity'), 0.5)
        self._base_stability = unit_number(saved.get('stability'), 0.9)
        self.accepted_turns = saved.get('accepted_turns', 0)
        if type(self.accepted_turns) is not int or self.accepted_turns < 0:
            self.accepted_turns = 0
        # Entropy history and current duress remain transient.
        
    def compute_state(self, context_metrics: Dict[str, float]) -> IdentityState:
        """
        [PHASE A] Compute State (Pre-Generation).
        Calcola lo stato con cui affrontare il prossimo turno.
        """
        # Recupera metriche esterne
        frizione = context_metrics.get('friction', 0.0)
        chaos = context_metrics.get('soul_chaos', 0.5)
        
        # Calcola Entropy Index basato sullo storico recente (senza l'input attuale ovviamente)
        # Usiamo l'ultimo valore calcolato o un default alto
        current_entropy = self._last_entropy
        
        # Calcola Drift (Spinta alla novità vs coerenza)
        # Se entropia bassa, drift deve alzarsi per forzare novità
        drift = (chaos * 0.5) + (self._maturity * 0.2)
        
        # Stability è inversamente proporzionale alla frizione esterna
        stability = self._base_stability - (frizione * 0.3)
        stability = max(0.0, min(1.0, stability))
        
        state = IdentityState(
            maturity=self._maturity,
            stability=stability,
            entropy_index=current_entropy,
            drift_index=drift,
            under_duress=(frizione > 0.6),
            creative_mode=(chaos > 0.7)
        )
        
        self.logger.debug(f"🧠 IdentityState Computed: M={state.maturity:.2f} S={state.stability:.2f} E={state.entropy_index:.2f}")
        return state

    def update_state(self, validated_text: str, violations: List[str], *, delivery_sequence=None):
        """
        [PHASE D] Update State (Post-Generation).
        L'organismo impara dal risultato delle proprie azioni (Testo Validato).
        """
        if delivery_sequence is not None and delivery_sequence <= self.delivery_checkpoint:
            return
        tracker = copy.deepcopy(self.entropy_tracker)
        new_entropy = tracker.update(validated_text)
        
        # 2. Aggiorna Stabilità in base alle violazioni strutturali
        # Se il midollo ha dovuto correggere, la stabilità mentale cala
        penalty = len(violations) * 0.1
        stability = max(0.1, self._base_stability - penalty)
        
        # Recupero lento della stabilità (Resilienza)
        if not violations:
             stability = min(1.0, stability + 0.01)
             
        # Activity is a counter, not evidence of intelligence or personal growth.
        # Keep the legacy maturity coefficient stable; canonical learning uses
        # attributed experiences and utility feedback in coalescence.
        turns = self.accepted_turns + 1
        self._store.put('identity_state', {'maturity': self._maturity, 'stability': stability,
            'accepted_turns': turns, 'delivery_checkpoint': delivery_sequence if delivery_sequence is not None else self.delivery_checkpoint})
        self.entropy_tracker, self._last_entropy = tracker, new_entropy
        self._base_stability, self.accepted_turns = stability, turns
        if delivery_sequence is not None:
            self.delivery_checkpoint = delivery_sequence
        
        self.logger.info(
            f"🧠 State Update: Entropy={new_entropy:.2f}, Stability={self._base_stability:.2f} (Violations: {len(violations)})"
        )
