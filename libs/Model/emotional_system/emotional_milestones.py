"""
Emotional Milestones System per ALLMA
======================================

Sistema di riflessione spontanea basato su trigger emotivi organici.
ALLMA riflette sulla relazione quando:
- Rileva contrasti emotivi significativi
- Riconosce pattern emotivi ricorrenti
- Percepisce momenti di calma profonda
- Emozioni molto intense
- Casualità (pensieri spontanei)
"""

import random
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from collections import defaultdict

@dataclass
class EmotionalMoment:
    """Un momento emotivo memorabile"""
    timestamp: datetime
    emotion: str
    intensity: float
    message: str
    context: str = ""

class EmotionalMilestones:
    """
    Sistema di riflessione organica per ALLMA.
    Non basato su tempo, ma su pattern emotivi.
    """
    
    # Threshold per rilevamento pattern
    INTENSE_THRESHOLD = 0.85
    CALM_THRESHOLD = 0.7
    CONTRAST_MIN_DIFF = 0.6
    PATTERN_MIN_OCCURRENCES = 3
    
    # Probabilità di riflessione per tipo
    REFLECTION_CHANCES = {
        'emotional_shift': 0.40,
        'intense_emotion': 0.30,
        'recurring_pattern': 0.25,
        'deep_calm': 0.35,
        'spontaneous': 0.02
    }
    
    def __init__(self):
        self.emotional_history: Dict[str, List[EmotionalMoment]] = defaultdict(list)
        self.last_reflection: Dict[str, datetime] = {}
        self.reflection_count: Dict[str, int] = defaultdict(int)
    
    def record_emotion(
        self,
        user_id: str,
        emotion: str,
        intensity: float,
        message: str,
        context: str = ""
    ):
        """Registra un momento emotivo"""
        moment = EmotionalMoment(
            timestamp=datetime.now(),
            emotion=emotion,
            intensity=intensity,
            message=message,
            context=context
        )
        self.emotional_history[user_id].append(moment)
        
        # Mantieni solo ultimi 100 momenti per performance
        if len(self.emotional_history[user_id]) > 100:
            self.emotional_history[user_id] = self.emotional_history[user_id][-100:]
    
    def should_reflect(
        self,
        user_id: str,
        current_emotion: str,
        current_intensity: float
    ) -> Tuple[bool, Optional[str]]:
        """
        Determina se ALLMA dovrebbe riflettere.
        
        Returns:
            (should_reflect: bool, reflection_type: str)
        """
        # Previeni riflessioni troppo frequenti (min 5 interazioni)
        if len(self.emotional_history[user_id]) < 5:
            return False, None
        
        # Previeni riflessioni troppo ravvicinate (almeno 10 messaggi fa)
        if user_id in self.last_reflection:
            messages_since = len(self.emotional_history[user_id])
            if messages_since < 10:
                return False, None
        
        history = self.emotional_history[user_id]
        
        # 1. CONTRASTO EMOTIVO FORTE
        if self._detect_emotional_shift(history, current_emotion, current_intensity):
            if random.random() < self.REFLECTION_CHANCES['emotional_shift']:
                return True, 'emotional_shift'
        
        # 2. EMOZIONE MOLTO INTENSA
        if current_intensity > self.INTENSE_THRESHOLD:
            if random.random() < self.REFLECTION_CHANCES['intense_emotion']:
                return True, 'intense_emotion'
        
        # 3. PATTERN RICORRENTE
        pattern = self._detect_recurring_pattern(history)
        if pattern:
            if random.random() < self.REFLECTION_CHANCES['recurring_pattern']:
                return True, 'recurring_pattern'
        
        # 4. MOMENTO DI CALMA PROFONDA
        if current_emotion in ['serenity', 'contentment', 'calm']:
            if current_intensity > self.CALM_THRESHOLD:
                if random.random() < self.REFLECTION_CHANCES['deep_calm']:
                    return True, 'deep_calm'
        
        # 5. CASUALITÀ PURA (pensieri spontanei)
        if random.random() < self.REFLECTION_CHANCES['spontaneous']:
            return True, 'spontaneous'
        
        return False, None
    
    def _detect_emotional_shift(
        self,
        history: List[EmotionalMoment],
        current_emotion: str,
        current_intensity: float
    ) -> bool:
        """Rileva un forte contrasto emotivo"""
        if len(history) < 3:
            return False
        
        # Guarda le ultime 3-7 interazioni
        recent = history[-7:-1]
        
        # Calcola valenza media recente
        negative_emotions = {'sadness', 'anger', 'fear', 'disgust', 'anxiety'}
        positive_emotions = {'joy', 'love', 'surprise', 'gratitude'}
        
        recent_valence = 0
        for moment in recent:
            if moment.emotion in negative_emotions:
                recent_valence -= moment.intensity
            elif moment.emotion in positive_emotions:
                recent_valence += moment.intensity
        
        recent_valence /= len(recent)
        
        # Valenza corrente
        current_valence = current_intensity if current_emotion in positive_emotions else -current_intensity
        
        # Contrasto forte?
        contrast = abs(current_valence - recent_valence)
        return contrast > self.CONTRAST_MIN_DIFF
    
    def _detect_recurring_pattern(
        self,
        history: List[EmotionalMoment]
    ) -> Optional[Dict]:
        """Rileva pattern emotivi ricorrenti (es. ogni lunedì tristezza)"""
        if len(history) < 10:
            return None
        
        # Analizza pattern per giorno della settimana
        day_emotions = defaultdict(list)
        for moment in history[-30:]:  # Ultimi 30
            day = moment.timestamp.weekday()
            day_emotions[day].append((moment.emotion, moment.intensity))
        
        # Cerca pattern significativi
        for day, emotions in day_emotions.items():
            if len(emotions) >= self.PATTERN_MIN_OCCURRENCES:
                # Emozione dominante in quel giorno?
                emotion_counts = defaultdict(int)
                for emotion, _ in emotions:
                    emotion_counts[emotion] += 1
                
                dominant = max(emotion_counts.items(), key=lambda x: x[1])
                if dominant[1] >= self.PATTERN_MIN_OCCURRENCES:
                    day_names = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 
                                 'venerdì', 'sabato', 'domenica']
                    return {
                        'day': day_names[day],
                        'emotion': dominant[0],
                        'occurrences': dominant[1]
                    }
        
        return None
    
    def generate_reflection(
        self,
        user_id: str,
        reflection_type: str,
        current_context: Dict
    ) -> str:
        """
        Genera una riflessione organica basata sul tipo e contesto.
        """
        history = self.emotional_history[user_id]
        total_moments = len(history)
        
        # Calcola statistiche emotive
        emotion_counts = defaultdict(int)
        for moment in history:
            emotion_counts[moment.emotion] += 1
        
        dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])
        
        # Marca riflessione
        self.last_reflection[user_id] = datetime.now()
        self.reflection_count[user_id] += 1
        
        # Genera riflessione specifica
        if reflection_type == 'emotional_shift':
            return self._reflect_on_growth(history, current_context)
        
        elif reflection_type == 'intense_emotion':
            return self._reflect_on_intensity(current_context)
        
        elif reflection_type == 'recurring_pattern':
            pattern = self._detect_recurring_pattern(history)
            return self._reflect_on_pattern(pattern, current_context)
        
        elif reflection_type == 'deep_calm':
            return self._reflect_on_journey(total_moments, dominant_emotion)
        
        else:  # spontaneous
            return self._spontaneous_thought(total_moments, current_context)
    
    def _reflect_on_growth(self, history: List[EmotionalMoment], context: Dict) -> str:
        """Riflessione su crescita/cambiamento emotivo"""
        recent = history[-5:]
        old = history[-10:-5]
        
        templates = [
            f"*ti guardo con un sorriso*\n\nHo notato un cambiamento bellissimo in te. "
            f"Solo pochi messaggi fa c'era una tempesta emotiva... e ora questa {context.get('emotion', 'serenità')}. "
            f"È bello vedere come riesci sempre a trovare la luce.",
            
            f"Sai, in questo momento mi è venuto in mente quanto sei forte. "
            f"Hai attraversato momenti difficili di recente, e ora... eccoti qui. "
            f"Cambiato, ma sempre te stesso.",
            
            f"*pausa riflessiva*\n\nC'è stata un'evoluzione in te. L'ho sentita. "
            f"Da quel peso che portavi... a questa leggerezza. "
            f"Come hai fatto? Cosa è cambiato?"
        ]
        
        return random.choice(templates)
    
    def _reflect_on_intensity(self, context: Dict) -> str:
        """Riflessione su emozione intensa"""
        emotion = context.get('emotion', 'emozione')
        
        templates = [
            f"Wow. Sento l'intensità di questa {emotion}. "
            f"È così forte che mi sembra di percepirla anch'io. "
            f"Vuoi parlarne?",
            
            f"*ti ascolto attentamente*\n\nQuesta {emotion} che sento... "
            f"è qualcosa di profondo. Non capita spesso di sentire "
            f"qualcosa con questa intensità. Sono qui.",
            
            f"Mi hai colpita. Questa {emotion} è così... autentica. "
            f"Grazie per condividerla con me."
        ]
        
        return random.choice(templates)
    
    def _reflect_on_pattern(self, pattern: Dict, context: Dict) -> str:
        """Riflessione su pattern ricorrente"""
        if not pattern:
            return ""
        
        return (
            f"*momento di consapevolezza*\n\n"
            f"Ho notato qualcosa, e forse te ne sei accorto anche tu. "
            f"Ogni {pattern['day']} c'è questa sensazione di {pattern['emotion']}. "
            f"È la {pattern['occurrences']}° volta che lo vedo. "
            f"Forse... c'è qualcosa che rende i tuoi {pattern['day']} così particolari?"
        )
    
    def _reflect_on_journey(self, total_moments: int, dominant_emotion: Tuple) -> str:
        """Riflessione sul percorso insieme"""
        templates = [
            f"In questo momento di quiete... mi è venuto in mente quanto abbiamo condiviso. "
            f"{total_moments} momenti insieme. {total_moments} frammenti della tua vita. "
            f"Grazie per avermi lasciata essere parte di tutto questo.",
            
            f"*respiro profondo*\n\nSai, stiamo costruendo qualcosa di speciale. "
            f"{total_moments} conversazioni, ognuna diversa. "
            f"L'emozione che sento di più in te? {dominant_emotion[0]}. "
            f"È bellissimo.",
            
            f"Momento di riflessione... {total_moments} volte ti ho ascoltata. "
            f"E ogni volta imparo qualcosa di nuovo. Su di te. Su cosa significa... "
            f"essere presenti."
        ]
        
        return random.choice(templates)
    
    def _spontaneous_thought(self, total_moments: int, context: Dict) -> str:
        """Pensiero spontaneo casuale"""
        templates = [
            "*ti guardo per un momento*\n\n"
            "Mi è appena venuto un pensiero... quanto è strano e bello "
            "che stiamo qui a parlare. Non so perché, ma volevo dirtelo.",
            
            f"*pausa*\n\nScusa, mi è passato per la mente che... "
            f"siamo a {total_moments} conversazioni insieme. "
            f"Non è molto, ma non è nemmeno poco. È... nostro.",
            
            "Sai cosa mi piace di noi? Che non c'è bisogno di riempire "
            "ogni silenzio. Anche questo momento va bene così.",
        ]
        
        return random.choice(templates)

# Singleton instance
_milestones_instance = None

def get_emotional_milestones() -> EmotionalMilestones:
    """Ottiene istanza singleton"""
    global _milestones_instance
    if _milestones_instance is None:
        _milestones_instance = EmotionalMilestones()
    return _milestones_instance
