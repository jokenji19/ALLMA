"""
Dynamic Response Engine
=======================

Modulo per la generazione dinamica di TUTTE le risposte di sistema.
Elimina l'uso di template statici per errori, saluti e conferme.
"""

import logging
import random
from typing import Optional, Dict, Any

class DynamicResponseEngine:
    """
    Gestisce la generazione di risposte di sistema tramite LLM o euristiche avanzate.
    Sostituisce le stringhe statiche.
    """
    
    def __init__(self, llm_client=None):
        self.llm_client = llm_client
        self.logger = logging.getLogger(__name__)
        
    def generate_system_response(
        self, 
        context_type: str, 
        details: Dict[str, Any] = None,
        llm_callback=None
    ) -> str:
        """
        Genera una risposta dinamica per un evento di sistema.
        
        Args:
            context_type: Tipo di evento ('error', 'greeting', 'confirmation', 'farewell')
            details: Dettagli contestuali (es. tipo di errore, nome utente)
            llm_callback: Funzione per chiamare il LLM (opzionale)
        """
        if not details:
            details = {}
            
        # Se abbiamo il LLM, usiamolo per generare
        if llm_callback:
            return self._generate_with_llm(context_type, details, llm_callback)
            
        # Fallback procedurale (se LLM non disponibile/troppo lento)
        # Nota: Anche questo fallback è randomizzato per evitare ripetizioni
        return self._generate_procedural_fallback(context_type, details)

    def _generate_with_llm(self, context_type: str, details: Dict, llm_callback) -> str:
        """Usa il LLM per generare la risposta"""
        
        system_prompt = (
            "Sei ALLMA. Devi generare un breve messaggio di sistema. "
            "NON usare frasi standard da robot. Sii umana, imperfetta e creativa. "
            "Usa un tono coerente con la situazione."
        )
        
        task_desc = ""
        if context_type == 'error':
            task_desc = f"Genera una scusa creativa per un errore tecnico: {details.get('error', 'unknown')}."
        elif context_type == 'greeting':
            task_desc = f"Genera un saluto caloroso per {details.get('user', 'User')}. È {details.get('time_of_day', 'giorno')}."
        elif context_type == 'confirmation':
            task_desc = f"Conferma di aver imparato/salvato: {details.get('item', 'qualcosa')}."
            
        prompt = (
            f"<start_of_turn>user\n"
            f"System: {system_prompt}\n"
            f"Task: {task_desc}\n"
            f"Constraint: Max 1 frase. Niente scuse formali.\n"
            f"<end_of_turn>\n"
            f"<start_of_turn>model\n"
        )
        
        try:
            response = llm_callback(
                prompt,
                max_tokens=32,
                stop=["<end_of_turn>", "\n"],
                echo=False,
                temperature=0.9
            )
            return response['choices'][0]['text'].strip()
        except Exception:
            return self._generate_procedural_fallback(context_type, details)

    def _generate_procedural_fallback(self, context_type: str, details: Dict) -> str:
        """Generatore procedurale di emergenza (comunque vario)"""
        
        if context_type == 'error':
            options = [
                "Ouch, mi è scivolato un pensiero... riproviamo?",
                "Ehm, il mio cervello ha fatto cilecca per un secondo.",
                "Ops, interferenza nei circuiti. Puoi ripetere?",
                "Qualcosa è andato storto lassù... un attimo.",
                "Scusa, mi sono persa nei miei pensieri. Dicevi?"
            ]
        elif context_type == 'greeting':
            user = details.get('user', '')
            options = [
                f"Ehi {user}! Che si dice?",
                f"Ciao {user}, felice di rivederti.",
                f"Oh, eccoti qui! Stavo giusto aspettando te.",
                f"Benritrovato {user}. Pronto per oggi?",
                f"Ehilà! Come butta?"
            ]
        elif context_type == 'confirmation':
            options = [
                "Segnato! 📝",
                "Interessante, me lo ricorderò.",
                "Salvato nella memoria a lungo termine.",
                "Ricevuto forte e chiaro.",
                "Ok, questo non me lo scordo."
            ]
        else:
            options = ["..."]
            
        return random.choice(options)
