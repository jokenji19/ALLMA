"""EmotionalCore - Sistema emotivo avanzato per ALLMA."""

from typing import Dict, List, Optional, Tuple, Any
import json
from dataclasses import dataclass, field
from transformers import pipeline
import numpy as np
from sklearn.preprocessing import MinMaxScaler

@dataclass
class EmotionalState:
    """Classe per rappresentare lo stato emotivo."""
    primary_emotion: str
    confidence: float
    secondary_emotions: Dict[str, float]
    intensity: float
    context: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        """
        Converte lo stato emotivo in un dizionario.
        
        Returns:
            Dict: Dizionario con i dati dello stato emotivo
        """
        return {
            "primary_emotion": self.primary_emotion,
            "confidence": self.confidence,
            "secondary_emotions": self.secondary_emotions,
            "intensity": self.intensity,
            "context": self.context
        }

class EmotionalCore:
    """Sistema emotivo avanzato."""
    
    def __init__(self):
        """Inizializza il sistema emotivo."""
        self.emotion_classifier = pipeline(
            "text-classification",
            model="j-hartmann/emotion-english-distilroberta-base",
            return_all_scores=True
        )
        self.intensity_scaler = MinMaxScaler()
        self.emotion_history: Dict[str, List[EmotionalState]] = {}
        self.current_emotion = None
        self.emotion_intensity = 0.0
        
        # Dizionario di traduzione semplice italiano-inglese per parole emotive comuni
        self.translation_dict = {
            'felice': 'happy',
            'triste': 'sad',
            'arrabbiato': 'angry',
            'contento': 'happy',
            'gioioso': 'joyful',
            'preoccupato': 'worried',
            'spaventato': 'scared',
            'sorpreso': 'surprised',
            'annoiato': 'bored',
            'entusiasta': 'excited',
            'soddisfatto': 'satisfied',
            'deluso': 'disappointed',
            'frustrato': 'frustrated',
            'nervoso': 'nervous',
            'calmo': 'calm',
            'rilassato': 'relaxed',
            'ansioso': 'anxious',
            'stanco': 'tired',
            'energico': 'energetic',
            'molto': 'very',
            'poco': 'little',
            'non': 'not',
            'sono': 'am',
            'mi sento': 'i feel',
            'mi': 'me',
            'sento': 'feel',
            'che': 'that',
            'quando': 'when',
            'perché': 'because',
            'e': 'and',
            'o': 'or',
            'ma': 'but',
            'se': 'if',
            'imparare': 'learning',
            'studiare': 'studying',
            'lavorare': 'working',
            'giocare': 'playing',
            'dormire': 'sleeping',
            'mangiare': 'eating',
            'bere': 'drinking',
            'parlare': 'talking',
            'scrivere': 'writing',
            'leggere': 'reading',
            'guardare': 'watching',
            'ascoltare': 'listening',
            'pensare': 'thinking',
            'credere': 'believing',
            'sapere': 'knowing',
            'capire': 'understanding',
            'volere': 'wanting',
            'potere': 'can',
            'dovere': 'must',
            'python': 'python'
        }
        
    def _translate_to_english(self, text: str) -> str:
        """
        Traduce il testo dall'italiano all'inglese usando un dizionario semplice.
        
        Args:
            text: Testo da tradurre
            
        Returns:
            Testo tradotto
        """
        # Converte il testo in minuscolo
        text = text.lower()
        
        # Divide il testo in parole
        words = text.split()
        
        # Traduce ogni parola se presente nel dizionario
        translated_words = [self.translation_dict.get(word, word) for word in words]
        
        # Unisce le parole tradotte
        return ' '.join(translated_words)
        
    def detect_emotion(
        self,
        text: str,
        context: Optional[Dict] = None
    ) -> EmotionalState:
        """
        Rileva le emozioni dal testo e contesto.
        
        Args:
            text: Testo da analizzare
            context: Contesto opzionale
            
        Returns:
            Stato emotivo rilevato
        """
        if context is None:
            context = {}
            
        try:
            # Traduci il testo in inglese
            translated_text = self._translate_to_english(text)
            print(f"DEBUG - Translated text: {translated_text}")
            
            # Analizza emozioni dal testo tradotto
            result = self.emotion_classifier(translated_text)
            print(f"DEBUG - Raw result: {result}")
            
            if not result or not isinstance(result, list):
                raise ValueError("Invalid classifier output")
                
            # Il risultato è una lista di liste, prendiamo la prima
            emotions = result[0]
            print(f"DEBUG - First list: {emotions}")
            
            if not emotions or not isinstance(emotions, list):
                raise ValueError("Invalid emotions format")
                
            # Applica pesi per favorire emozioni positive
            weights = {
                'joy': 1.5,
                'surprise': 1.2,
                'neutral': 0.8,
                'anger': 1.0,
                'disgust': 1.0,
                'fear': 1.0,
                'sadness': 1.0
            }
            
            # Applica i pesi
            for emotion in emotions:
                emotion['score'] *= weights.get(emotion['label'], 1.0)
                
            # Ordina per score
            emotions.sort(key=lambda x: x['score'], reverse=True)
            print(f"DEBUG - Sorted emotions: {emotions}")
            
            # Estrai emozione primaria
            primary = emotions[0]['label']
            confidence = emotions[0]['score']
            print(f"DEBUG - Primary emotion: {primary} ({confidence})")
            
            # Estrai emozioni secondarie
            secondary = {
                e['label']: e['score']
                for e in emotions[1:]
            }
            print(f"DEBUG - Secondary emotions: {secondary}")
            
            # Calcola intensità
            intensity = self._calculate_emotional_intensity(
                confidence,
                secondary,
                context
            )
            
            # Aggiorna lo stato emotivo
            self.current_emotion = primary
            self.emotion_intensity = intensity
            
            return EmotionalState(
                primary_emotion=primary,
                confidence=confidence,
                secondary_emotions=secondary,
                intensity=intensity,
                context=context
            )
            
        except Exception as e:
            print(f"Errore nell'analisi delle emozioni: {e}")
            return EmotionalState(
                primary_emotion="neutral",
                confidence=0.0,
                secondary_emotions={},
                intensity=0.0,
                context=context
            )
            
    def generate_emotional_response(
        self,
        detected_emotion: EmotionalState,
        base_response: str
    ) -> str:
        """
        Genera una risposta appropriata all'emozione rilevata.
        
        Args:
            detected_emotion: Stato emotivo rilevato
            base_response: Risposta base da adattare
            
        Returns:
            Risposta adattata emotivamente
        """
        try:
            # Adatta in base all'emozione primaria
            response = self._adapt_to_primary_emotion(
                base_response,
                detected_emotion
            )
            
            # Modifica intensità della risposta solo se non è neutrale
            if detected_emotion.primary_emotion != "neutral":
                response = self._adjust_response_intensity(
                    response,
                    detected_emotion.intensity
                )
            
            # Aggiungi elementi di supporto emotivo solo se non è neutrale
            if detected_emotion.primary_emotion != "neutral":
                response = self._add_emotional_support(
                    response,
                    detected_emotion
                )
            
            return response
            
        except Exception as e:
            print(f"Errore nella generazione della risposta emotiva: {e}")
            return base_response
            
    def track_emotional_state(
        self,
        user_id: str,
        emotional_state: EmotionalState
    ) -> None:
        """
        Traccia lo stato emotivo di un utente nel tempo.
        
        Args:
            user_id: ID dell'utente
            emotional_state: Stato emotivo da tracciare
        """
        if user_id not in self.emotion_history:
            self.emotion_history[user_id] = []
            
        self.emotion_history[user_id].append(emotional_state)
        
        # Mantieni solo gli ultimi 100 stati
        if len(self.emotion_history[user_id]) > 100:
            self.emotion_history[user_id] = self.emotion_history[user_id][-100:]
            
    def analyze_emotional_trends(
        self,
        user_id: str
    ) -> Dict:
        """
        Analizza i trend emotivi di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dizionario con statistiche e trend emotivi
        """
        if user_id not in self.emotion_history:
            return {
                'dominant_emotion': None,
                'average_intensity': 0.0,
                'emotion_distribution': {},
                'intensity_trend': 'stable'
            }
            
        history = self.emotion_history[user_id]
        
        # Calcola emozione dominante
        emotions = [state.primary_emotion for state in history]
        emotion_counts = {}
        for emotion in emotions:
            emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
            
        dominant_emotion = max(
            emotion_counts.items(),
            key=lambda x: x[1]
        )[0]
        
        # Calcola intensità media
        intensities = [state.intensity for state in history]
        avg_intensity = sum(intensities) / len(intensities)
        
        # Calcola distribuzione emozioni
        total = len(emotions)
        distribution = {
            emotion: count / total
            for emotion, count in emotion_counts.items()
        }
        
        # Analizza trend intensità
        if len(intensities) >= 2:
            if intensities[-1] > intensities[0]:
                trend = 'increasing'
            elif intensities[-1] < intensities[0]:
                trend = 'decreasing'
            else:
                trend = 'stable'
        else:
            trend = 'stable'
            
        return {
            'dominant_emotion': dominant_emotion,
            'average_intensity': avg_intensity,
            'emotion_distribution': distribution,
            'intensity_trend': trend
        }
        
    def get_intensity(self) -> float:
        """
        Restituisce l'intensità dell'emozione corrente.
        
        Returns:
            float: Intensità dell'emozione
        """
        return self.emotion_intensity
        
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """
        Analizza il contenuto emotivo di un testo.
        
        Args:
            text: Testo da analizzare
            
        Returns:
            Dict con l'analisi emotiva
        """
        emotion_state = self.detect_emotion(text)
        return {
            "primary_emotion": emotion_state.primary_emotion,
            "intensity": emotion_state.intensity,
            "valence": self._calculate_valence(emotion_state),
            "secondary_emotions": emotion_state.secondary_emotions
        }
        
    def get_current_state(self) -> Dict[str, Any]:
        """
        Ottiene lo stato emotivo corrente.
        
        Returns:
            Dict con lo stato emotivo corrente
        """
        if self.current_emotion:
            return self.current_emotion.to_dict()
        return {
            "primary_emotion": "neutral",
            "confidence": 1.0,
            "secondary_emotions": {},
            "intensity": 0.0,
            "context": {}
        }
        
    def get_user_emotional_state(self, user_id: str) -> EmotionalState:
        """
        Recupera lo stato emotivo corrente dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Stato emotivo corrente dell'utente
        """
        if user_id not in self.emotion_history or not self.emotion_history[user_id]:
            # Se non c'è storia emotiva, restituisci uno stato neutrale
            return EmotionalState(
                primary_emotion="neutral",
                confidence=1.0,
                secondary_emotions={},
                intensity=0.5
            )
            
        # Restituisci l'ultimo stato emotivo registrato
        return self.emotion_history[user_id][-1]
        
    def _calculate_emotional_intensity(
        self,
        confidence: float,
        secondary_emotions: Dict[str, float],
        context: Dict
    ) -> float:
        """Calcola l'intensità emotiva."""
        # Base intensity from confidence
        intensity = confidence
        
        # Adjust based on secondary emotions
        if secondary_emotions:
            max_secondary = max(secondary_emotions.values())
            intensity = (intensity + max_secondary) / 2
            
        # Adjust based on context
        if context.get('urgent', False):
            intensity *= 1.2
        if context.get('important', False):
            intensity *= 1.1
            
        # Normalize
        return min(max(intensity, 0.0), 1.0)
        
    def _adapt_to_primary_emotion(
        self,
        response: str,
        emotion: EmotionalState
    ) -> str:
        """Adatta la risposta all'emozione primaria."""
        adaptations = {
            'joy': lambda r: f"Sono felice di questo! {r}",
            'sadness': lambda r: f"Mi dispiace per questo. {r}",
            'anger': lambda r: f"Capisco la tua frustrazione. {r}",
            'fear': lambda r: f"Non preoccuparti. {r}",
            'surprise': lambda r: f"Davvero interessante! {r}",
            'neutral': lambda r: r
        }
        
        adapter = adaptations.get(
            emotion.primary_emotion,
            adaptations['neutral']
        )
        return adapter(response)
        
    def _adjust_response_intensity(
        self,
        response: str,
        intensity: float
    ) -> str:
        """Regola l'intensità della risposta."""
        if intensity > 0.8:
            response = response.upper()
        elif intensity > 0.6:
            response += "!"
        return response
        
    def _add_emotional_support(
        self,
        response: str,
        emotion: EmotionalState
    ) -> str:
        """Aggiunge elementi di supporto emotivo."""
        if emotion.intensity > 0.7:
            response += "\nSono qui per aiutarti."
        if emotion.confidence > 0.8:
            response += f"\nPercepisco chiaramente il tuo stato d'animo {emotion.primary_emotion}."
        return response
        
    def _calculate_valence(self, emotion_state: EmotionalState) -> float:
        """
        Calcola la valenza emotiva (positiva/negativa).
        
        Args:
            emotion_state: Stato emotivo
            
        Returns:
            float tra -1 (molto negativo) e 1 (molto positivo)
        """
        # Definisci la valenza per ogni emozione
        valence_map = {
            "joy": 1.0,
            "love": 0.8,
            "admiration": 0.6,
            "approval": 0.4,
            "caring": 0.3,
            "excitement": 0.5,
            "gratitude": 0.7,
            "pride": 0.6,
            "relief": 0.3,
            "neutral": 0.0,
            "confusion": -0.2,
            "disapproval": -0.4,
            "disappointment": -0.5,
            "anger": -0.8,
            "annoyance": -0.3,
            "disgust": -0.7,
            "embarrassment": -0.4,
            "fear": -0.6,
            "grief": -0.9,
            "nervousness": -0.3,
            "remorse": -0.5,
            "sadness": -0.7
        }
        
        # Calcola la valenza pesata
        valence = valence_map.get(emotion_state.primary_emotion, 0.0) * emotion_state.confidence
        
        # Considera anche le emozioni secondarie
        for emotion, score in emotion_state.secondary_emotions.items():
            valence += valence_map.get(emotion, 0.0) * score * 0.5  # Peso dimezzato
            
        # Normalizza tra -1 e 1
        return max(min(valence, 1.0), -1.0)
