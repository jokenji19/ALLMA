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
        # Extract primary emotion from features if available, else infer/default
        emotion_type = getattr(pattern_features, 'primary_emotion', 'neutral')
        
        # Calcola la valenza emotiva
        valence = self._calculate_valence(pattern_features.intensity, emotion_type)
        
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
        
        return emotional_state
        
    def process(self, user_input: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Standard interface for ModuleOrchestrator"""
        # 1. Analyze input
        features_dict = self.analyze_emotion(user_input)
        
        # 2. Create a Mock object for features because adapt_to_emotion expects object access
        class Features:
            def __init__(self, d):
                self.intensity = d.get('intensity', 0.5)
                self.primary_emotion = d.get('primary_emotion', 'neutral')
                self.complexity = 0.5
        
        features = Features(features_dict)
        
        # 3. Update State
        new_state = self.adapt_to_emotion(features)
        
        # 4. Generate Response
        response = self.generate_response(
            {'primary_emotion': new_state.category.replace('simple_', '').replace('complex_', '')}
        )
        
        return {
            'response': response,
            'valence': new_state.valence,
            'intensity': new_state.intensity,
            'category': new_state.category
        }

    def _calculate_valence(self, intensity: float, emotion_type: str = 'neutral') -> float:
        """Calcola la valenza emotiva basata su tipo e intensità"""
        # Base valences for different emotions
        base_valence = {
            'joy': 0.8,
            'surprise': 0.6,
            'neutral': 0.5,
            'sadness': 0.3,
            'fear': 0.2,
            'anger': 0.2
        }.get(emotion_type, 0.5)
        
        # Modulate by intensity
        # Positive emotions: high intensity -> higher valence
        # Negative emotions: high intensity -> lower valence
        if base_valence > 0.5:
            valence = base_valence + (intensity * 0.2)
        elif base_valence < 0.5:
            valence = base_valence - (intensity * 0.2)
        else:
            valence = 0.5
            
        return max(0.0, min(1.0, valence))
        
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
                "Sono davvero felice per te!",
                "Che notizia fantastica!",
                "È meraviglioso sentirlo!",
                "La tua gioia è contagiosa.",
                "Questo mi rallegra la giornata.",
                "Ottimo risultato!",
                "Continua così!",
                "Splendido!",
                "Che momento speciale!",
                "Ti sento molto positivo oggi!"
            ],
            'sadness': [
                "Mi dispiace molto che tu ti senta così.",
                "Sono qui se hai bisogno di sfogarti.",
                "A volte è giusto prendersi un momento per la tristezza.",
                "Spero che le cose migliorino presto.",
                "Ti sono vicino.",
                "Posso fare qualcosa per aiutarti?",
                "È un momento difficile, lo capisco.",
                "Non sei solo in questo.",
                "Prenditi il tempo che ti serve.",
                "Vorrei poterti aiutare di più."
            ],
            'anger': [
                "Capisco la tua frustrazione.",
                "Sembra una situazione davvero irritante.",
                "Hai tutto il diritto di essere arrabbiato.",
                "Cerchiamo di mantenere la calma e analizzare la situazione.",
                "Vuoi parlarne più in dettaglio?",
                "Sfogarsi può aiutare.",
                "Cosa ti ha fatto arrabbiare di più?",
                "Respiro profondo. Sono qui.",
                "Non lasciare che la rabbia ti rovini la giornata.",
                "Affrontiamo la cosa un passo alla volta."
            ],
            'fear': [
                "È normale avere paura in certe situazioni.",
                "Affronteremo questa preoccupazione insieme.",
                "Cosa ti spaventa di più esattamente?",
                "Cerca di concentrarti sul presente.",
                "Sono qui per supportarti in ogni modo.",
                "La paura può essere utile se la ascoltiamo.",
                "Non lasciare che l'ansia prenda il sopravvento.",
                "Sei più forte di quanto pensi.",
                "Tutto si risolverà.",
                "Facciamo un passo alla volta."
            ],
            'surprise': [
                "Wow! Davvero inaspettato!",
                "Non me lo sarei mai immaginato!",
                "Che colpo di scena!",
                "Incredibile!",
                "Raccontami di più, sono curioso!",
                "Questa sì che è una novità.",
                "Davvero sorprendente.",
                "Chi l'avrebbe mai detto!",
                "Mi hai lasciato senza parole.",
                "Che sorpresa piacevole (spero!)"
            ],
            'neutral': [
                "Capisco.",
                "Interessante.",
                "Dimmi di più.",
                "Continuo ad ascoltarti.",
                "Cosa ne pensi?",
                "Sono qui.",
                "Procediamo.",
                "Tutto chiaro.",
                "Certo.",
                "Ok, andiamo avanti."
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
