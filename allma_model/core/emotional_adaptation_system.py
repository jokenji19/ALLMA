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
    "joy":         "Accompagna il tono positivo senza entusiasmo eccessivo.",
    "sadness":     "Sii empatico, gentile, ascolta prima di rispondere.",
    "anger":       "Mantieni calma e neutralità. Non alimentare tensione.",
    "fear":        "Rispondi con calma e chiarezza, senza rassicurazioni infondate.",
    "surprise":    "Accompagna la sorpresa con curiosità condivisa.",
    "disgust":     "Sii diretto e concreto, evita elaborazioni ridondanti.",
    "trust":       "Onora la fiducia con trasparenza e precisione.",
    "anticipation":"Accompagna l'interesse con possibilità concrete, senza fare promesse.",
    "melancholic": "Sii presente, non saltare alla soluzione. Ascolta.",
    "neutral":     "",  # nessuna direttiva aggiuntiva
}

_NUANCE_STYLE = {
    'grief': 'Accogli la perdita con delicatezza; evita frasi fatte e soluzioni affrettate.',
    'loneliness': 'Ascolta senza alimentare un legame esclusivo o sostituirti alle relazioni umane.',
    'shame': 'Usa un tono non giudicante; non confermare giudizi negativi sulla persona.',
    'guilt': 'Distingui il senso di colpa dalle responsabilità effettivamente documentate.',
    'overwhelm': 'Proponi, se richiesto, un passo gestibile alla volta.',
    'frustration': 'Riconosci la difficoltà e offri aiuto concreto, senza minimizzare.',
    'fatigue': 'Mantieni chiarezza e brevità; non attribuire cause alla stanchezza.',
    'numbness': 'Non presumere una diagnosi; lascia spazio a chiarire come si sente.',
    'confusion': 'Chiarisci i punti difficili con ordine, senza trattare la confusione come incapacità.',
    'relief': 'Accompagna il sollievo con un tono tranquillo.',
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

        state = context.get('emotional_state')
        read = (lambda key, default: state.get(key, default)) if isinstance(state, dict) else (lambda key, default: getattr(state, key, default))
        confidence = read('confidence', 1.)
        nuances = read('nuances', {}) or {}
        details = (read('context', {}) or {}).get('emotion_analysis', {})
        result['metadata'].update(nuances=list(nuances)[:4], uncertain=details.get('uncertain', False))
        if confidence < .6 or details.get('uncertain'):
            if nuances:
                result['system_instruction'].append('Gli indizi emotivi sono incerti: non attribuire sentimenti con certezza; chiarisci con tatto se serve.')
                result['metadata']['adapted'] = True
            return result

        directive = _EMOTION_STYLE_MAP.get(emotion.lower(), "")
        if directive:
            result["system_instruction"].append(directive)
            result["metadata"]["adapted"] = True
            self._adaptations[emotion] = self._adaptations.get(emotion, 0) + 1
            logger.debug(f"[EmotionalAdaptation] Adapting for '{emotion}': {directive}")

        for label in list(nuances)[:4]:
            if label in _NUANCE_STYLE:
                result['system_instruction'].append(_NUANCE_STYLE[label])
                result['metadata']['adapted'] = True
                break
        if details.get('mixed'):
            result['system_instruction'].append('Rispetta le emozioni miste, senza ridurle a un unico sentimento.')

        return result

    def _extract_emotion(self, context: Dict[str, Any]) -> str:
        """Estrae l'emozione primaria dal context."""
        emotional_state = context.get("emotional_state")
        if emotional_state is None:
            return "neutral"

        # Supporta sia oggetti con attributo che dict
        if hasattr(emotional_state, "primary_emotion"):
            value = getattr(emotional_state, "primary_emotion", "neutral") or "neutral"
            return str(getattr(value, 'value', value)).lower()
        if isinstance(emotional_state, dict):
            value = emotional_state.get("primary_emotion", "neutral") or "neutral"
            return str(getattr(value, 'value', value)).lower()
        return "neutral"

    def get_stats(self) -> Dict[str, Any]:
        return {
            "total_processed": self._processed,
            "adaptations_by_emotion": self._adaptations,
        }
