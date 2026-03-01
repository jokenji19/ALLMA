"""
StructuralCore (Layer 1) — Midollo Spinale di ALLMA v5
======================================================
Responsabilità:
- Validazione strutturale immutabile per il turno corrente (Snapshot).
- Applicazione regole "hard" (Pattern Contracts).
- Idempotenza (Output deterministico).
- Protezione identità di base.

Non gestisce:
- Stato emotivo (Layer 2)
- Modulazione espressiva (Layer 3)
- Apprendimento (Layer 4)
"""

import re
import logging
from typing import List, Tuple, Dict, Optional, FrozenSet
from dataclasses import dataclass, field

@dataclass(frozen=True)
class PatternContract:
    """
    Contratto strutturale immutabile.
    Definisce cosa è vietato (blacklist) e cosa è obbligatorio (whitelist).
    """
    forbidden_patterns: FrozenSet[Tuple[str, str]]  # (regex, replacement)
    required_structure: FrozenSet[str]              # regex che DEVONO essere presenti (opzionale)
    
    def validate(self, text: str) -> Tuple[bool, List[str]]:
        """Verifica se il testo rispetta il contratto."""
        violations = []
        # Check forbidden
        for pattern, _ in self.forbidden_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                violations.append(f"FORBIDDEN:{pattern}")
        
        # Check required (se definiti)
        for pattern in self.required_structure:
            if not re.search(pattern, text, re.IGNORECASE):
                violations.append(f"MISSING:{pattern}")
                
        return len(violations) == 0, violations

class StructuralCore:
    """
    Midollo Spinale.
    Esegue la validazione strutturale su uno snapshot immutabile delle regole.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Regole di base (Hard-coded per sicurezza iniziale)
        # Queste possono essere estese dal Neuroplastic Governance in futuro
        self._base_blacklist = [
            (r"sono un'intelligenza artificiale", ""),
            (r"sono un'ia", ""),
            (r"in quanto ia", ""),
            (r"sono un modello linguistico", ""),
            (r"sono un assistente virtuale", ""),
            (r"sono un programma", ""),
            (r"come modello linguistico", ""),
            (r"openai", ""),
            (r"anthropic", ""),
            (r"chatgpt", ""),
            (r"gpt-", ""),
            (r"google deepmind", ""),
        ]
        
        self._current_snapshot: Optional[PatternContract] = None
        self._create_snapshot() # Inizializza snapshot base

    def _create_snapshot(self):
        """Crea uno snapshot immutabile delle regole correnti."""
        frozen_blacklist = frozenset(self._base_blacklist)
        # Per ora nessun required structure stringente
        frozen_required = frozenset([]) 
        
        self._current_snapshot = PatternContract(
            forbidden_patterns=frozen_blacklist,
            required_structure=frozen_required
        )
        self.logger.debug("🔒 StructuralCore: Snapshot creato/aggiornato.")

    def update_rules(self, new_blacklist: List[Tuple[str, str]]):
        """
        Aggiorna le regole (chiamato dal Neuroplastic Governance - Layer 4).
        L'aggiornamento ha effetto solo al prossimo snapshot (turno successivo).
        """
        self._base_blacklist = new_blacklist
        # In v5, lo snapshot si aggiorna esplicitamente tra un turno e l'altro.
        # Qui simuliamo l'aggiornamento immediato per semplicità, ma 
        # l'architettura prevede che `validate` usi self._current_snapshot
        self._create_snapshot() 

    def validate(self, text: str) -> Tuple[str, bool, List[str]]:
        """
        Valida e corregge il testo in modo idempotente.
        
        Args:
            text: Testo Raw dal LLM.
            
        Returns:
            (testo_corretto, is_valid, violations)
        """
        if not self._current_snapshot:
            self._create_snapshot()
            
        contract = self._current_snapshot
        is_valid, violations = contract.validate(text)
        
        if is_valid:
            return text, True, []
        
        # Correzione Idempotente (Touch-up)
        # Applica sostituzioni solo per i pattern vietati rilevati
        corrected_text = text
        applied_fixes = []
        
        for pattern, replacement in contract.forbidden_patterns:
            if re.search(pattern, corrected_text, re.IGNORECASE):
                # Sostituzione
                before = corrected_text
                corrected_text = re.sub(pattern, replacement, corrected_text, flags=re.IGNORECASE)
                if before != corrected_text:
                    applied_fixes.append(pattern)
        
        # Pulizia spazi creati dalle rimozioni
        corrected_text = re.sub(r'\s+', ' ', corrected_text).strip()
        
        # Verify idempotency (Ricontrolla se il testo corretto è valido)
        is_final_valid, remaining_violations = contract.validate(corrected_text)
        
        if not is_final_valid:
            self.logger.warning(
                f"⚠️ StructuralCore: Correzione incompleta. Violazioni residue: {remaining_violations}"
            )
            
        return corrected_text, is_final_valid, violations
