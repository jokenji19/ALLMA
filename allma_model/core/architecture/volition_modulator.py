"""
Volition Modulator (Layer 3) — Corteccia Espressiva
===================================================
Responsabilità:
- Modulare la forma espressiva (Tono, Lunghezza, Lessico) in base allo IdentityState.
- Applicare vincoli rigidi (Hard Constraints) per evitare deriva semantica.
- Garantire che "Come lo dico" non tradisca "Cosa voglio dire".

Non gestisce:
- Contenuto logico (Reasoning Engine)
- Validazione strutturale (Layer 1)
- Apprendimento (Layer 4)
"""

import logging
import re
from typing import List, Tuple, Optional
from dataclasses import dataclass

# Tipi di modulazione
MODULATION_NONE = "none"
MODULATION_SIMPLIFY = "simplify"
MODULATION_EXPAND = "expand"
MODULATION_INTROSPECT = "introspect"
MODULATION_DIRECT = "direct"

class VolitionModulator:
    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def apply(self, text: str, identity_state: 'IdentityState') -> str:
        """
        Applica la modulazione volontaria al testo validato.
        
        Args:
            text: Testo strutturalmente valido (dal Layer 1).
            identity_state: Stato corrente dell'organismo (dal Layer 2).
            
        Returns:
            Testo modulato (o originale se i vincoli violati).
        """
        if not text or len(text) < 10:
            return text
            
        strategy = self._decide_strategy(identity_state)
        
        if strategy == MODULATION_NONE:
            return text
            
        modulated_text = text
        
        # Applicazione Strategie (Simulazione deterministica per V5.0)
        # In V5.1 questo userebbe un LLM "editor" molto piccolo o regole NLP
        try:
            if strategy == MODULATION_SIMPLIFY:
                modulated_text = self._simplify(text)
            elif strategy == MODULATION_DIRECT:
                modulated_text = self._make_direct(text)
            # Expand e Introspect richiederebbero generazione, per ora skip o semplice wrapping
            
            # --- HARD CONSTRAINTS (Vincoli Rigidi) ---
            if self._verify_constraints(original=text, candidate=modulated_text):
                return modulated_text
            else:
                self.logger.warning(f"🛡️ Volition: Vincoli violati per strategia {strategy}. Revert to original.")
                return text
                
        except Exception as e:
            self.logger.error(f"Volition Error: {e}")
            return text

    def _decide_strategy(self, state) -> str:
        """Decide la strategia basandosi su Maturity, Entropy e Stress."""
        if state.under_duress:
            return MODULATION_DIRECT # Sotto stress, sii diretto
            
        if state.entropy_index < 0.3:
            # Bassa entropia (ripetitivo) -> Prova a variare
            return MODULATION_EXPAND 
            
        if state.maturity > 0.8:
            # Alta maturità -> Stile più posato/semplice
            return MODULATION_SIMPLIFY
            
        return MODULATION_NONE

    def _simplify(self, text: str) -> str:
        """Rimuove avverbi e aggettivi superflui (Euristica semplice)."""
        # Rimuove parole "filler" comuni in italiano
        fillers = [
            r"\bveramente\b", r"\bdavvero\b", r"\bun po'\b", r"\bsostanzialmente\b",
            r"\bpraticamente\b", r"\bassolutamente\b", r"\bcomunque\b"
        ]
        simplified = text
        for f in fillers:
            simplified = re.sub(f, "", simplified, flags=re.IGNORECASE)
        
        # Normalizza spazi
        return re.sub(r'\s+', ' ', simplified).strip()

    def _make_direct(self, text: str) -> str:
        """Rende il tono più imperativo/diretto."""
        # Esempio: "Penso che dovresti fare X" -> "Fai X."
        # Molto rudimentale, per PoC usa replacement
        replacements = [
            (r"\bpenso che sia meglio\b", "è meglio"),
            (r"\bvorrei suggerirti di\b", "dovresti"),
            (r"\bmi sembra che\b", ""),
        ]
        direct = text
        for pat, repl in replacements:
            direct = re.sub(pat, repl, direct, flags=re.IGNORECASE)
        return re.sub(r'\s+', ' ', direct).strip()

    def _verify_constraints(self, original: str, candidate: str) -> bool:
        """
        Verifica i vincoli di invarianza.
        1. Length Bound: Non discostarsi più del 20%.
        2. Polarity Shield: Non introdurre negazioni non presenti (basic).
        """
        # 1. Length Bound
        len_orig = len(original)
        len_new = len(candidate)
        # Allow up to 50% reduction (was 40%) to support simplification
        if len_new < len_orig * 0.5 or len_new > len_orig * 1.5:
            self.logger.debug(f"Volition: Length constraint fail ({len_orig} -> {len_new})")
            return False
            
        # 2. Safety (Non svuotare il messaggio)
        if len(candidate.strip()) == 0:
            return False
            
        return True
