"""
Neuroplastic Governance (Layer 4) — Memoria Immunitaria
=======================================================
Responsabilità:
- Gestire dinamicamente le regole (blacklist) del Structural Core.
- Rinforzare le regole utili (Violation Tracker).
- Dimenticare le regole obsolete (Biological Cap & Weighted Decay).
- Aggiornamento asincrono o per-turno.

Non gestisce:
- Validazione diretta (Layer 1)
- Stato emotivo (Layer 2)
"""

import logging
from dataclasses import dataclass, field
from typing import List, Dict, Tuple, Optional
from datetime import datetime, timedelta
import re
import copy
from functools import wraps
from allma_model.utils.cognitive_state import CognitiveStateStore


def rules_transaction(method):
    @wraps(method)
    def call(self, *args, **kwargs):
        original = self.rules
        checkpoint = self.delivery_checkpoint
        self.rules = copy.deepcopy(original)
        try:
            return method(self, *args, **kwargs)
        except Exception:
            self.rules = original
            self.delivery_checkpoint = checkpoint
            raise
    return call

@dataclass
class LearnedRule:
    """Una regola appresa o innata, con punteggio di utilità biologica."""
    pattern: str
    replacement: str
    activation_count: int = 0
    last_activated: datetime = field(default_factory=datetime.now)
    created_at: datetime = field(default_factory=datetime.now)
    decay_factor: float = 0.95  # Quanto velocemente perde importanza

    @property
    def activity_score(self) -> float:
        """
        Calcola lo score di attività biologica.
        Score = (Attivazioni * Decadimento) / Ore di inattività
        """
        delta = datetime.now() - self.last_activated
        # Evitiamo divisione per zero, minimo 0.1 ore (~6 minuti)
        hours_inactive = max(0.1, delta.total_seconds() / 3600.0)
        
        # Formula base: Più è attiva, più alto lo score. Più tempo passa, più scende.
        raw_score = (self.activation_count * self.decay_factor) / hours_inactive
        return round(raw_score, 4)

class NeuroplasticitySystem:
    def __init__(self, db_path: str = "allma_v5.db"):
        self.logger = logging.getLogger(__name__)
        self.rules: Dict[str, LearnedRule] = {}
        self.max_synapses = 50 # Biological Cap (Limite massimo di regole attive)
        self._store = CognitiveStateStore(db_path)
        self.delivery_checkpoint = self._store.get('neuroplasticity').get('delivery_checkpoint', 0)
        if type(self.delivery_checkpoint) is not int or not 0 <= self.delivery_checkpoint < 2**53:
            raise ValueError('Invalid neuroplasticity delivery checkpoint; recovery required')
        
        # Inizializza con regole base (Bootstrap)
        self._bootstrap_memory()
        saved = self._store.get('neuroplasticity').get('rules', [])
        if isinstance(saved, list):
            for item in saved[:self.max_synapses]:
                try:
                    if not isinstance(item, dict) or not isinstance(item.get('pattern'), str) or not isinstance(item.get('replacement'), str):
                        continue
                    if type(item.get('activation_count')) is not int or item['activation_count'] < 0:
                        continue
                    re.compile(item['pattern'])
                    rule = LearnedRule(pattern=item['pattern'], replacement=item['replacement'],
                        activation_count=item['activation_count'],
                        last_activated=datetime.fromisoformat(item['last_activated']),
                        created_at=datetime.fromisoformat(item['created_at']))
                    if rule.last_activated.tzinfo or rule.created_at.tzinfo:
                        continue
                    self.rules[rule.pattern] = rule
                except (ValueError, TypeError, KeyError, re.error):
                    continue

    def _save(self):
        self._store.put('neuroplasticity', {'delivery_checkpoint': self.delivery_checkpoint, 'rules': [{
            'pattern': r.pattern, 'replacement': r.replacement, 'activation_count': r.activation_count,
            'last_activated': r.last_activated.isoformat(), 'created_at': r.created_at.isoformat()
        } for r in self.rules.values()]})

    def _bootstrap_memory(self):
        """Carica le regole innate (hardcoded) nella memoria plastica."""
        # Copia delle regole di base del StructuralCore per tracciarle
        # Identity is checked separately; do not delete general knowledge or quoted text.
        initial_patterns = []
        
        for p, r in initial_patterns:
            # Le regole base partono con un'attivazione alta per non essere dimenticate subito
            self.add_rule(p, r, initial_activation=100) 

    @rules_transaction
    def add_rule(self, pattern: str, replacement: str, initial_activation: int = 1):
        """Aggiunge o aggiorna una regola."""
        re.compile(pattern)
        if not pattern or not isinstance(replacement, str) or type(initial_activation) is not int or initial_activation < 0:
            raise ValueError('Invalid learned rule')
        if pattern not in self.rules:
            self.rules[pattern] = LearnedRule(
                pattern=pattern, 
                replacement=replacement, 
                activation_count=initial_activation
            )
        else:
            # Se esiste già, rinforzala
            self.rules[pattern].activation_count += initial_activation
            self.rules[pattern].last_activated = datetime.now()
        self.prune_synapses()
        self._save()

    @rules_transaction
    def analyze(self, violations: List[str], *, delivery_sequence=None):
        """
        [PHASE D] Analisi Cognitiva.
        Analizza le violazioni rilevate dal StructuralCore e rinforza le sinapsi corrispondenti.
        """
        if delivery_sequence is not None:
            if delivery_sequence <= self.delivery_checkpoint:
                return
            self.delivery_checkpoint = delivery_sequence
        reinforced_count = 0
        
        for v in violations:
            if v.startswith("FORBIDDEN:"):
                # Estrai pattern (ora completo grazie al fix su StructuralCore)
                pattern_found = v.split(":", 1)[1]
                
                # Cerca e rinforza
                if pattern_found in self.rules:
                    rule = self.rules[pattern_found]
                    rule.activation_count += 1
                    rule.last_activated = datetime.now()
                    reinforced_count += 1
                    self.logger.info(f"🧠 Neuroplasticity: Reinforced synapse '{pattern_found}' (Score: {rule.activity_score})")

        if reinforced_count > 0 or delivery_sequence is not None:
            # Se abbiamo imparato qualcosa, potiamo le connessioni deboli
            self.prune_synapses()
            self._save()

    def prune_synapses(self):
        """
        [Biological Cap]
        Rimuove le regole con score più basso se superiamo la capacità massima.
        """
        if len(self.rules) <= self.max_synapses:
            return

        # Ordina per score crescente (i peggiori primi)
        sorted_rules = sorted(self.rules.values(), key=lambda r: r.activity_score)
        
        # Quanti rimuovere
        to_remove_count = len(self.rules) - self.max_synapses
        to_remove = sorted_rules[:to_remove_count]
        
        for rule in to_remove:
            self.logger.info(f"🧠 Neuroplasticity: Pruning weak synapse '{rule.pattern}' (Score: {rule.activity_score:.4f})")
            del self.rules[rule.pattern]
            
    def get_adaptive_instructions(self) -> str:
        """Ritorna istruzioni adattive per il prompt (opzionale)."""
        # Per ora non usato, placeholder per future evoluzioni
        return ""

    def get_active_rules(self) -> List[Tuple[str, str]]:
        """Restituisce la lista corrente di regole attive per il StructuralCore."""
        return [(r.pattern, r.replacement) for r in self.rules.values()]
