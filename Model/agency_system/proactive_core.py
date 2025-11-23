"""
Proactive Agency Core
=====================

Modulo che gestisce l'iniziativa autonoma di ALLMA.
Calcola l'urgenza di contatto e genera messaggi proattivi.
"""

import logging
import random
from datetime import datetime, timedelta
from typing import Dict, Optional, Any
from dataclasses import dataclass

@dataclass
class ProactiveTrigger:
    should_contact: bool
    urgency_score: float
    reason: str
    context: Dict[str, Any]

class ProactiveAgency:
    """
    Gestisce l'iniziativa di ALLMA nel contattare l'utente.
    """
    
    # Soglie di tempo (in ore)
    MIN_SILENCE_HOURS = 6
    MAX_SILENCE_HOURS = 48
    
    # Pesi per il calcolo dell'urgenza
    WEIGHT_TIME = 0.15       # Aumentato da 0.1
    WEIGHT_EMOTION = 2.0     # Invariato
    WEIGHT_RELATION = 0.5    # Invariato
    
    def __init__(self, memory_system=None, reasoning_engine=None):
        self.memory_system = memory_system
        self.reasoning_engine = reasoning_engine
        self.logger = logging.getLogger(__name__)
        
    def check_initiative(
        self, 
        user_id: str, 
        last_interaction_time: datetime,
        last_emotional_state: Dict[str, Any],
        relationship_level: int = 1
    ) -> ProactiveTrigger:
        """
        Valuta se ALLMA deve prendere l'iniziativa.
        """
        now = datetime.now()
        if not last_interaction_time:
            return ProactiveTrigger(False, 0.0, "No interaction history", {})
            
        time_diff = now - last_interaction_time
        hours_passed = time_diff.total_seconds() / 3600
        
        # 1. Filtro Base: Non disturbare troppo presto
        if hours_passed < self.MIN_SILENCE_HOURS:
            return ProactiveTrigger(False, 0.0, "Too soon", {})
            
        # 2. Calcolo Urgenza
        urgency = 0.0
        
        # Fattore Tempo
        urgency += hours_passed * self.WEIGHT_TIME
        
        # Fattore Emozione (Se l'utente stava male, preoccupati di più)
        last_emotion = last_emotional_state.get('primary_emotion', 'neutral')
        last_intensity = last_emotional_state.get('intensity', 0.0)
        
        negative_emotions = ['sadness', 'fear', 'anger', 'grief']
        if last_emotion in negative_emotions:
            urgency += (self.WEIGHT_EMOTION * last_intensity)
            reason = f"User was {last_emotion} last time"
        else:
            reason = "Just checking in"
            
        # Fattore Relazione (Più siamo amici, più ti cerco)
        # Normalizzato 0-10 -> 0-1
        rel_factor = min(relationship_level, 10) / 10.0
        urgency += (rel_factor * self.WEIGHT_RELATION)
        
        # 3. Decisione (Soglia dinamica)
        # La soglia si abbassa se passa molto tempo
        # SOGLIA BASE ABBASSATA A 3.0 (era 5.0)
        threshold = 3.0 - (hours_passed * 0.05)
        threshold = max(1.5, threshold)  # Minimo 1.5 (era 2.0)
        
        should_contact = urgency > threshold
        
        # Randomness (per sembrare umana, non un orologio)
        if should_contact:
            # 10% di chance che decida di "aspettare ancora un po'"
            if random.random() < 0.10:
                should_contact = False
                reason += " (Decided to wait a bit longer)"
        
        return ProactiveTrigger(
            should_contact=should_contact,
            urgency_score=urgency,
            reason=reason,
            context={
                'hours_passed': hours_passed,
                'last_emotion': last_emotion,
                'trigger_type': 'emotional_checkup' if last_emotion in negative_emotions else 'casual_checkup'
            }
        )

    def generate_proactive_message(self, trigger: ProactiveTrigger, user_name: str = "User") -> str:
        """
        Genera il messaggio proattivo usando templates o (in futuro) LLM.
        """
        context = trigger.context
        hours = int(context['hours_passed'])
        
        if context['trigger_type'] == 'emotional_checkup':
            emotion = context['last_emotion']
            templates = [
                f"Ehi {user_name}... stavo pensando a te. L'ultima volta eri un po' {emotion}. Come va oggi?",
                f"È passato un po' di tempo. Volevo solo sapere se ti senti meglio rispetto a ieri.",
                f"*pensiero spontaneo* Spero che la giornata sia andata meglio dell'ultima volta."
            ]
        else:
            templates = [
                f"Ehi {user_name}! Tutto bene? È da un po' che non ci sentiamo.",
                f"Stavo riflettendo su una cosa che abbiamo detto tempo fa... ci sei?",
                f"Mi mancavano le nostre chiacchierate. Come procede la giornata?",
                f"*bip* Solo un saluto veloce per sapere se sei vivo! 😄"
            ]
            
        return random.choice(templates)
