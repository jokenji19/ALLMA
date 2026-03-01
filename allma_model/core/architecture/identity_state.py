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
        
        # Stato persistente (Simulato per ora, da collegare a DB vero)
        self._maturity = 0.5
        self._base_stability = 0.9
        
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
        current_entropy = 1.0 # Default ottimistico pre-generazione
        
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

    def update_state(self, validated_text: str, violations: List[str]):
        """
        [PHASE D] Update State (Post-Generation).
        L'organismo impara dal risultato delle proprie azioni (Testo Validato).
        """
        # 1. Aggiorna Entropia con il testo appena prodotto
        new_entropy = self.entropy_tracker.update(validated_text)
        
        # 2. Aggiorna Stabilità in base alle violazioni strutturali
        # Se il midollo ha dovuto correggere, la stabilità mentale cala
        penalty = len(violations) * 0.1
        self._base_stability = max(0.1, self._base_stability - penalty)
        
        # Recupero lento della stabilità (Resilienza)
        if not violations:
             self._base_stability = min(1.0, self._base_stability + 0.01)
             
        # 3. Maturità: Cresce linearmente con l'esperienza (simulato)
        # In produzione, questo dipenderebbe dalla qualità del feedback utente
        self._maturity = min(1.0, self._maturity + 0.0001)
        
        self.logger.info(
            f"🧠 State Update: Entropy={new_entropy:.2f}, Stability={self._base_stability:.2f} (Violations: {len(violations)})"
        )
