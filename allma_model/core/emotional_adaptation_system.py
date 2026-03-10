"""
EmotionalAdaptationSystem — ALLMA V6
======================================
Adatta il tono e lo stile della risposta all'umore corrente dell'utente.

Registrato nel ModuleOrchestrator come Tier 1 (CRITICAL priority).
"""
from __future__ import annotations
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


# Mapping stato emotivo → direttiva di stile
_EMOTION_STYLE_MAP: Dict[str, str] = {
    "joy":         "Rispecchia l'entusiasmo dell'utente con energia positiva.",
    "sadness":     "Sii empatico, gentile, ascolta prima di rispondere.",
    "anger":       "Mantieni calma e neutralità. Non alimentare tensione.",
    "fear":        "Rassicura l'utente con chiarezza e solidità.",
    "surprise":    "Accompagna la sorpresa con curiosità condivisa.",
    "disgust":     "Sii diretto e concreto, evita elaborazioni ridondanti.",
    "trust":       "Onora la fiducia con trasparenza e precisione.",
    "anticipation":"Alimenta l'aspettativa con contesto e dettagli.",
    "melancholic": "Sii presente, non saltare alla soluzione. Ascolta.",
    "neutral":     "",  # nessuna direttiva aggiuntiva
}


class EmotionalAdaptationSystem:
    """
    Adattatore di stile emotivo per il ModuleOrchestrator.

    process() ritorna:
        {
            'user_prefix':       List[str]
            'system_instruction': List[str]  ← direttiva stile emotivo
            'metadata':          Dict
        }
    """

    def __init__(self):
        self._processed = 0
        self._adaptations: Dict[str, int] = {}
        logger.info("✅ EmotionalAdaptationSystem initialized.")

    def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Chiamato dal ModuleOrchestrator ad ogni messaggio.

        Args:
            user_input: messaggio corrente dell'utente
            context:    deve contenere 'emotional_state' con attributo/chiave
                        'primary_emotion' oppure dict con 'primary_emotion'
        """
        self._processed += 1
        result: Dict[str, Any] = {
            "user_prefix": [],
            "system_instruction": [],
            "metadata": {"emotion": "neutral", "adapted": False},
        }

        emotion = self._extract_emotion(context)
        result["metadata"]["emotion"] = emotion

        directive = _EMOTION_STYLE_MAP.get(emotion.lower(), "")
        if directive:
            result["system_instruction"].append(directive)
            result["metadata"]["adapted"] = True
            self._adaptations[emotion] = self._adaptations.get(emotion, 0) + 1
            logger.debug(f"[EmotionalAdaptation] Adapting for '{emotion}': {directive}")

        return result

    def _extract_emotion(self, context: Dict[str, Any]) -> str:
        """Estrae l'emozione primaria dal context."""
        emotional_state = context.get("emotional_state")
        if emotional_state is None:
            return "neutral"

        # Supporta sia oggetti con attributo che dict
        if hasattr(emotional_state, "primary_emotion"):
            return getattr(emotional_state, "primary_emotion", "neutral") or "neutral"
        if isinstance(emotional_state, dict):
            return emotional_state.get("primary_emotion", "neutral") or "neutral"
        return "neutral"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_processed": self._processed,
            "adaptations_by_emotion": self._adaptations,
        }
