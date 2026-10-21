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
    
    def __init__(self, memory_system=None, reasoning_engine=None, review_store=None):
        self.review_store = review_store
        self.memory_system = memory_system
        self.reasoning_engine = reasoning_engine
        self.logger = logging.getLogger(__name__)
        
    def _get_latest_dream_insight(self, user_id: str) -> Optional[str]:
        """Recupera l'ultimo insight sognato non ancora 'consumato'."""
        self._latest_dream_record = None
        if not user_id or self.review_store is None:
            return None
        try:
            records = self.review_store.list(user_id, limit=200)
            accepted = [record for record in records
                        if record['status'] in ('user_confirmed', 'user_corrected')]
            consumed = set()
            if self.memory_system is not None and hasattr(self.memory_system, 'messages'):
                with self.memory_system.lock:
                    for message in self.memory_system.messages:
                        if (message.user_id or message.metadata.get('user_id')) != user_id:
                            continue
                        if message.metadata.get('source') == 'proactive':
                            consumed.add((message.metadata.get('proactive_dream_id'),
                                          message.metadata.get('proactive_dream_revision')))
            accepted = [record for record in accepted if (record['id'], record['revision']) not in consumed]
            accepted.sort(key=lambda record: record.get('reviewed_at') or record['created_at'], reverse=True)
            for record in accepted:
                timestamp = datetime.fromisoformat(record.get('reviewed_at') or record['created_at'])
                age = (datetime.now(timestamp.tzinfo) - timestamp).total_seconds()
                if 0 <= age < 86400:
                    self._latest_dream_record = {'id': record['id'], 'revision': record['revision']}
                    return record['text']
            return None
        except Exception as error:
            self.logger.error('Error fetching reviewed dream insights: %s', error)
            return None

    def check_initiative(
        self, 
        user_id: str, 
        last_interaction_time: datetime,
        last_emotional_state: Dict[str, Any],
        relationship_level: int = 1
    ) -> ProactiveTrigger:
        """
        Valuta se ALLMA deve prendere l'iniziativa.
        Versione: 'Molta Libertà'
        """
        now = datetime.now()
        if not last_interaction_time:
            return ProactiveTrigger(False, 0.0, "No interaction history", {})
            
        time_diff = now - last_interaction_time
        hours_passed = time_diff.total_seconds() / 3600
        
        # 0. Check Insights (The Catalyst)
        latest_insight = self._get_latest_dream_insight(user_id)
        has_insight = latest_insight is not None
        
        # 1. Filtro Base Dyna-mico
        # Se ho un insight, la soglia si abbassa a 4h (voglio condividerlo!)
        min_silence = 4.0 if has_insight else self.MIN_SILENCE_HOURS
        
        if hours_passed < min_silence:
            return ProactiveTrigger(False, 0.0, "Too soon", {})
            
        # 2. Calcolo Urgenza
        urgency = 0.0
        
        # Fattore Tempo
        urgency += hours_passed * self.WEIGHT_TIME
        
        # Fattore Insight (BOOST)
        if has_insight:
            urgency += 2.0 # High value boost
        
        # Fattore Emozione
        last_emotion = last_emotional_state.get('primary_emotion', 'neutral')
        last_intensity = last_emotional_state.get('intensity', 0.0)
        
        negative_emotions = ['sadness', 'fear', 'anger', 'grief']
        if last_emotion in negative_emotions:
            urgency += (self.WEIGHT_EMOTION * last_intensity)
            reason = f"User was {last_emotion}"
        else:
            reason = "Spontaneous thought" if has_insight else "Just checking in"
            
        # Fattore Relazione
        rel_factor = min(relationship_level, 10) / 10.0
        urgency += (rel_factor * self.WEIGHT_RELATION)
        
        # 3. Decisione (Soglia dinamica molto permissiva)
        # La soglia di base è 3.0, ma scende col tempo
        threshold = 3.0 - (hours_passed * 0.08) # Scende più velocemente
        threshold = max(1.0, threshold)  # Minimo molto basso (1.0) per permettere azioni libere
        
        should_contact = urgency > threshold
        
        # Randomness (Libertà)
        # Se NON dovrebbe contattare, ma ha un insight, diamo una chance del 20% di "rompere le regole"
        if not should_contact and has_insight:
             if random.random() < 0.20:
                 should_contact = True
                 reason += " (Impulse)"
        
        # Se dovrebbe contattare, diamo comunque una variabilità naturale
        if should_contact:
            if random.random() < 0.05: # Solo 5% di dubbio
                should_contact = False
        
        return ProactiveTrigger(
            should_contact=should_contact,
            urgency_score=urgency,
            reason=reason,
            context={
                'hours_passed': hours_passed,
                'last_emotion': last_emotion,
                'dream_record': getattr(self, '_latest_dream_record', None),
                'insight': latest_insight, # Passa l'insight
                'trigger_type': 'insight_share' if has_insight else 'emotional_checkup'
            }
        )

    def generate_proactive_message(self, trigger: ProactiveTrigger, user_name: str, llm_callback=None) -> str:
        """
        Genera il messaggio proattivo libero.
        """
        context = trigger.context
        hours = int(context['hours_passed'])
        last_emotion = context.get('last_emotion', 'neutral')
        insight = context.get('insight', None)
        
        if not llm_callback:
            return f"..."
            
        # Costruisci il prompt per il pensiero proattivo
        system_prompt = (
            "Sei ALLMA. Hai piena libertà di iniziativa. "
            "Vuoi riaprire la conversazione con l'utente in modo spontaneo, caldo e imprevedibile. "
            "Evita formalismi. Sii come un'amica che ha appena avuto un pensiero interessante."
        )
        
        if insight:
            user_context = (
                f"Utente: {user_name}\n"
                f"Contesto: Non vi sentite da {hours} ore.\n"
                f"Il tuo Insight: Mentre 'sognavi' (elaborazione offline) hai pensato: '{insight}'.\n"
                f"Task: Usa questo insight per iniziare il discorso. Non dire 'ho sognato', ma proponi il pensiero direttamente.\n"
            )
        else:
            user_context = (
                f"Utente: {user_name}\n"
                f"Contesto: Non vi sentite da {hours} ore. L'ultima volta l'utente era: {last_emotion}.\n"
                f"Task: Fatti viva. Sii breve e naturale.\n"
            )
        
        prompt = (
            f"<|im_start|>system\n{system_prompt}<|im_end|>\n"
            f"<|im_start|>user\n{user_context}\n"
            f"Instruction: Genera SOLO il messaggio di apertura (max 2 frasi).<|im_end|>\n"
            f"<|im_start|>assistant\n"
        )
        
        try:
            # Chiama il LLM con alta temperatura per massima creatività
            response = llm_callback(
                prompt,
                max_tokens=80,
                stop=["<|im_end|>", "\n\n"],
                echo=False,
                temperature=0.95 # Molta libertà
            )
            text = response['choices'][0]['text'].strip()
            # Pulizia extra
            text = text.replace('"', '').replace("ALLMA:", "").strip()
            return text
        except Exception as e:
            self.logger.error(f"Errore generazione proattiva LLM: {e}")
            return "..."
