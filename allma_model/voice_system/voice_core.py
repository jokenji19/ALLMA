"""
Voice Core System
=================

Modulo per la gestione della sintesi vocale (TTS) emotiva.
Calcola i parametri audio (pitch, speed) in base allo stato emotivo.
"""

import logging
from typing import Dict, Any, Optional

class VoiceSystem:
    """
    Gestisce la voce di ALLMA, modulando i parametri in base alle emozioni.
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        # Parametri base (neutri)
        self.base_pitch = 1.0
        self.base_rate = 1.0
        
    def get_voice_parameters(self, emotion: str, intensity: float) -> Dict[str, float]:
        """
        Calcola i parametri TTS per una data emozione.
        
        Args:
            emotion: Emozione primaria (es. 'joy', 'sadness')
            intensity: Intensità dell'emozione (0.0 - 1.0)
            
        Returns:
            Dizionario con 'pitch' e 'rate'
        """
        emotion = str(getattr(emotion, 'value', emotion)).lower()
        try:
            intensity = max(0.0, min(1.0, float(intensity)))
        except (ValueError, TypeError):
            intensity = 0.0
        pitch = self.base_pitch
        rate = self.base_rate
        
        # Modulazione Emotiva
        if emotion == 'joy':
            # Felicità: Voce più acuta e veloce
            pitch += (0.2 * intensity)
            rate += (0.1 * intensity)
            
        elif emotion == 'sadness':
            # Tristezza: Voce più grave e lenta
            pitch -= (0.2 * intensity)
            rate -= (0.2 * intensity)
            
        elif emotion == 'anger':
            # A calm reply should not mirror the user's agitation.
            pitch -= (0.05 * intensity)
            rate -= (0.05 * intensity)
            
        elif emotion == 'fear':
            pitch -= (0.03 * intensity)
            rate -= (0.08 * intensity)
            
        elif emotion == 'surprise':
            # Sorpresa: Voce molto acuta
            pitch += (0.4 * intensity)
        elif emotion == 'trust':
            rate -= (0.03 * intensity)
        elif emotion == 'anticipation':
            pitch += (0.05 * intensity)
            
        # Limiti di sicurezza per evitare voci distorte
        pitch = max(0.9, min(1.1, pitch))
        rate = max(0.85, min(1.15, rate))
        
        return {
            'pitch': pitch,
            'rate': rate,
            'emotion': emotion
        }

    def speak(self, text: str, emotion_params: Dict[str, float]):
        """
        Comando per parlare (Interfaccia verso Android TTS).
        In ambiente desktop/test, simula l'output.
        """
        pitch = emotion_params.get('pitch', 1.0)
        rate = emotion_params.get('rate', 1.0)
        
        self.logger.info(f"🔊 SPEAKING: '{text}' | Pitch: {pitch:.2f}, Rate: {rate:.2f}")
        
        # Qui andrebbe l'integrazione con plyer.tts o jnius per Android
        # try:
        #     from plyer import tts
        #     tts.speak(text) # Plyer base non supporta pitch dinamico facilmente, servirebbe codice nativo Java
        # except ImportError:
        #     pass
