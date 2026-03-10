"""
CuriosityDrive — ALLMA V6
==========================
Modulo di curiosità cognitiva: analizza ogni messaggio utente e genera
domande o hook di esplorazione per arricchire il contesto della risposta.

Registrato nel ModuleOrchestrator come Tier 1 (HIGH priority).
"""
from __future__ import annotations
import re
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class CuriosityDrive:
    """
    Genera 'hook di curiosità' attivabili dal ModuleOrchestrator.

    process() ritorna un dict compatibile con il contratto dell'Orchestratore:
        {
            'user_prefix':       List[str]  — frasi prepesse al turn utente
            'system_instruction': List[str] — istruzioni addizionali al system prompt
            'metadata':          Dict       — dati extra per debug
        }
    """

    # Parole chiave che attivano la curiosità esplicita
    CURIOSITY_TRIGGERS = {
        "perché", "come mai", "why", "how come",
        "spiegami", "explain", "dimmi di più", "tell me more",
        "cosa pensi", "what do you think", "sai che",
        "mi chiedo", "i wonder", "curious", "curioso",
    }

    # Domande aperte che il modulo può iniettare nel contesto
    OPEN_HOOKS = [
        "Esplora ogni aspetto interessante della domanda.",
        "Se c'è qualcosa di sorprendente nell'argomento, portalo in superficie.",
        "Collega questo topic a qualcosa di inaspettato se pertinente.",
    ]

    def __init__(self):
        self._trigger_count = 0
        self._total_processed = 0
        logger.info("✅ CuriosityDrive initialized.")

    def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Punto di ingresso chiamato dal ModuleOrchestrator.

        Args:
            user_input: messaggio dell'utente
            context:    contesto corrente (emotional_state, memories, intent, ...)

        Returns:
            dict con chiavi 'user_prefix', 'system_instruction', 'metadata'
        """
        self._total_processed += 1
        result: Dict[str, Any] = {
            "user_prefix": [],
            "system_instruction": [],
            "metadata": {"triggered": False, "score": 0.0},
        }

        if not user_input or not isinstance(user_input, str):
            return result

        text_lower = user_input.lower()
        score = self._compute_curiosity_score(text_lower, context)
        result["metadata"]["score"] = round(score, 3)

        if score >= 0.4:
            self._trigger_count += 1
            result["metadata"]["triggered"] = True
            # Scegli un hook in rotation
            hook = self.OPEN_HOOKS[self._trigger_count % len(self.OPEN_HOOKS)]
            result["system_instruction"].append(hook)
            logger.debug(f"[CuriosityDrive] Triggered (score={score:.2f}): {hook}")

        return result

    def _compute_curiosity_score(self, text: str, context: Dict[str, Any]) -> float:
        """Score 0-1 basato su trigger keywords, lunghezza, intent."""
        score = 0.0

        # Trigger espliciti
        triggered = sum(1 for kw in self.CURIOSITY_TRIGGERS if kw in text)
        score += min(triggered * 0.3, 0.6)

        # Query lunga = più contesto = più curiosità potenziale
        word_count = len(text.split())
        if word_count > 10:
            score += 0.15
        if word_count > 25:
            score += 0.1

        # Intent da context
        intent = context.get("intent", "")
        if isinstance(intent, str) and intent in ("domanda", "question", "spiegazione"):
            score += 0.2

        return min(score, 1.0)

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_processed": self._total_processed,
            "trigger_count": self._trigger_count,
            "trigger_rate": round(self._trigger_count / max(self._total_processed, 1), 3),
        }
