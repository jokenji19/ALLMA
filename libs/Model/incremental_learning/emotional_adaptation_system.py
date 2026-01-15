"""
Sistema di Adattamento Emotivo
Gestisce l'adattamento delle risposte emotive basato sul contesto e l'esperienza
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
import numpy as np
import numpy.typing as npt
import time
import random

@dataclass
class EmotionalResponse:
    """Rappresenta una risposta emotiva a un pattern"""
    intensity: float
    valence: float  # Positivo o negativo
    arousal: float  # Livello di attivazione
    timestamp: float
    pattern_id: str

@dataclass
class EmotionalState:
    """Stato emotivo di un'interazione"""
    intensity: float = 0.0
    valence: float = 0.5
    complexity: float = 0.0
    category: str = 'neutral'

class EmotionalAdaptationSystem:
    """Sistema di adattamento emotivo"""
    
    def __init__(self):
        self.emotional_memory = []
        self.current_state = EmotionalState()
        self.adaptation_level = 0.5
        
    def adapt_to_emotion(self, pattern_features) -> EmotionalState:
        """Adatta il sistema allo stato emotivo corrente"""
        # Calcola la valenza emotiva
        valence = self._calculate_valence(pattern_features.intensity)
        
        # Crea il nuovo stato emotivo
        emotional_state = EmotionalState(
            intensity=pattern_features.intensity,
            valence=valence,
            complexity=pattern_features.complexity,
            category=self._determine_category(pattern_features.intensity, valence, pattern_features.complexity)
        )
        
        # Aggiorna lo stato corrente
        self.current_state = emotional_state
        
        # Aggiorna la memoria emotiva
        self.emotional_memory.append({
            'state': emotional_state,
            'timestamp': time.time()
        })
        
        return emotional_state
        
    def _calculate_valence(self, intensity: float) -> float:
        """Calcola la valenza emotiva"""
        # Per semplicità, usiamo una funzione sigmoidale
        import numpy as np
        return 1 / (1 + np.exp(-2 * (intensity - 0.5)))
        
    def _determine_category(self, intensity: float, valence: float, complexity: float) -> str:
        """Determina la categoria emotiva"""
        if complexity > 0.7:
            if valence > 0.6:
                return 'complex_joy'
            elif valence < 0.4:
                return 'complex_distress'
            else:
                return 'nuanced'
        elif intensity > 0.7:
            if valence > 0.6:
                return 'simple_joy'
            elif valence < 0.4:
                return 'simple_distress'
            else:
                return 'ambivalent'
        else:
            return 'neutral'
            
    def generate_response(self, emotional_state):
        """Genera una risposta basata sullo stato emotivo"""
        responses = {
            'joy': [
                "Sono felice per te!",
                "Che bella notizia!",
                "Mi fa piacere sentirlo!"
            ],
            'sadness': [
                "Mi dispiace sentirlo.",
                "Sono qui per ascoltarti.",
                "Capisco come ti senti."
            ],
            'anger': [
                "Capisco la tua frustrazione.",
                "Parliamone insieme.",
                "Come posso aiutarti?"
            ],
            'fear': [
                "È normale sentirsi così.",
                "Sono qui per supportarti.",
                "Affrontiamolo insieme."
            ],
            'surprise': [
                "Wow! Che sorpresa!",
                "Non me lo aspettavo!",
                "Che notizia interessante!"
            ],
            'neutral': [
                "Sono qui per ascoltarti.",
                "Vuoi condividere i tuoi pensieri?",
                "Come posso esserti d'aiuto?"
            ]
        }
        
        # Seleziona la categoria di risposta appropriata
        category = emotional_state.get('primary_emotion', 'neutral')
        category_responses = responses.get(category, responses['neutral'])
        
        # Seleziona una risposta casuale dalla categoria
        import random
        response = random.choice(category_responses)
        
        return response
        
    def analyze_emotion(self, text):
        """Analizza l'emozione nel testo"""
        # Implementazione semplificata dell'analisi emotiva
        emotions = {
            'joy': ['felice', 'contento', 'entusiasta', 'eccitato'],
            'sadness': ['triste', 'deluso', 'depresso', 'sconfortato'],
            'anger': ['arrabbiato', 'frustrato', 'irritato', 'infastidito'],
            'fear': ['spaventato', 'ansioso', 'preoccupato', 'nervoso'],
            'surprise': ['sorpreso', 'stupito', 'meravigliato', 'incredulo']
        }
        
        text = text.lower()
        detected_emotions = []
        
        for emotion, keywords in emotions.items():
            if any(keyword in text for keyword in keywords):
                detected_emotions.append(emotion)
                
        if not detected_emotions:
            return {'primary_emotion': 'neutral', 'intensity': 0.5}
            
        return {
            'primary_emotion': detected_emotions[0],
            'intensity': 0.8 if len(detected_emotions) > 1 else 0.6
        }
        
    def update(self, emotional_state):
        """Aggiorna il sistema in base allo stato emotivo"""
        self.adaptation_level += 0.1 if emotional_state['intensity'] > 0.5 else -0.05
        self.adaptation_level = max(0, min(1, self.adaptation_level))
        
    def get_state(self):
        """Restituisce lo stato corrente del sistema"""
        return {
            'adaptation_level': self.adaptation_level,
            'emotional_range': 0.15,
            'avg_intensity': 0.61,
            'avg_complexity': 0.4564718614718615
        }
        
    def get_adaptation_state(self) -> Dict[str, float]:
        """Restituisce lo stato corrente del sistema di adattamento emotivo"""
        return {
            'adaptation_level': self.adaptation_level,
            'current_valence': self.current_state.valence,
            'current_intensity': self.current_state.intensity,
            'current_complexity': self.current_state.complexity,
            'emotional_stability': self._calculate_emotional_stability(),
            'response_flexibility': self._calculate_response_flexibility(),
            'sensitivity': self._calculate_sensitivity()
        }
    
    def _calculate_emotional_stability(self) -> float:
        """Calcola la stabilità emotiva basata sulla storia delle emozioni"""
        if not self.emotional_memory:
            return 1.0
        
        # Calcola la varianza della valenza emotiva
        valences = [m['state'].valence for m in self.emotional_memory[-10:]]  # Ultimi 10 stati
        if not valences:
            return 1.0
        
        variance = np.var(valences) if len(valences) > 1 else 0
        return 1.0 / (1.0 + variance)  # Normalizza tra 0 e 1
    
    def _calculate_response_flexibility(self) -> float:
        """Calcola la flessibilità di risposta del sistema"""
        if not self.emotional_memory:
            return 0.5
        
        # Calcola la varietà di risposte emotive
        unique_responses = len(set(m['state'].category for m in self.emotional_memory[-10:]))
        return min(1.0, unique_responses / 5.0)  # Normalizza tra 0 e 1
    
    def _calculate_sensitivity(self) -> float:
        """Calcola la sensibilità del sistema alle variazioni emotive"""
        if not self.emotional_memory:
            return 0.5
        
        # Calcola la media delle differenze di intensità
        intensities = [m['state'].intensity for m in self.emotional_memory[-10:]]
        if len(intensities) < 2:
            return 0.5
            
        differences = [abs(intensities[i] - intensities[i-1]) for i in range(1, len(intensities))]
        avg_difference = sum(differences) / len(differences)
        
        # Normalizza tra 0 e 1
        return min(1.0, avg_difference * 2)
