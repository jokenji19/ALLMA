"""
Emotional System Module
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending
"""

from typing import Dict, Any
from datetime import datetime

class EmotionalSystem:
    """Sistema di gestione delle emozioni per ALLMA"""
    
    def __init__(self):
        self.emotion_value = 0.0  # Range: -1.0 (negative) to 1.0 (positive)
        self.emotion_history = []
        self.current_emotion = "neutral"
        self.emotion_thresholds = {
            "very_negative": -0.8,
            "negative": -0.3,
            "neutral": 0.3,
            "positive": 0.8,
            "very_positive": 1.0
        }
        
    def process_emotion(self, text: str, valence: float = None) -> Dict[str, Any]:
        """Processa il testo e aggiorna lo stato emotivo"""
        if valence is None:
            # Simplified sentiment analysis
            positive_words = {"felice", "bello", "ottimo", "fantastico", "grazie"}
            negative_words = {"triste", "brutto", "male", "pessimo", "scusa"}
            
            words = set(text.lower().split())
            pos_count = len(words & positive_words)
            neg_count = len(words & negative_words)
            
            if pos_count + neg_count > 0:
                valence = (pos_count - neg_count) / (pos_count + neg_count)
            else:
                valence = 0.0
                
        # Update emotion value with smoothing
        self.emotion_value = 0.7 * self.emotion_value + 0.3 * valence
        self.emotion_value = max(-1.0, min(1.0, self.emotion_value))
        
        # Determine current emotion
        for emotion, threshold in sorted(self.emotion_thresholds.items()):
            if self.emotion_value <= threshold:
                self.current_emotion = emotion
                break
                
        # Record in history
        self.emotion_history.append({
            "timestamp": datetime.now(),
            "text": text,
            "valence": valence,
            "emotion": self.current_emotion,
            "emotion_value": self.emotion_value
        })
        
        return {
            "emotion": self.current_emotion,
            "value": self.emotion_value,
            "valence": valence
        }
        
    def get_current_emotion(self) -> str:
        """Restituisce l'emozione corrente"""
        return self.current_emotion
        
    def get_emotion_history(self) -> list:
        """Restituisce la storia delle emozioni"""
        return self.emotion_history
        
    def reset_emotion(self) -> None:
        """Resetta lo stato emotivo a neutrale"""
        self.emotion_value = 0.0
        self.current_emotion = "neutral"
