"""Personality - Sistema di personalità di ALLMA"""

from typing import Dict, Optional, Any
import json
import os
from typing import List

class Personality:
    def __init__(self, state_file: str = "personality_state.json"):
        """
        Inizializza il sistema di personalità
        
        Args:
            state_file: File per salvare lo stato della personalità
        """
        self.state_file = state_file
        self._style = {
            "communication_style": "neutral",
            "technical_level": "intermediate",
            "response_length": "medium",
            "emotion_influence": None
        }
        self._user_preferences = {}
        self._interaction_history = {}
        
    def adapt_to_preferences(self, preferences: Dict[str, str]):
        """
        Adatta la personalità alle preferenze dell'utente
        
        Args:
            preferences: Dizionario delle preferenze
        """
        for key, value in preferences.items():
            if key in self._style:
                self._style[key] = value
                
    def adapt_to_emotion(self, emotional_core):
        """
        Adatta la personalità all'emozione corrente
        
        Args:
            emotional_core: Core emotivo
        """
        current_emotion = emotional_core.current_emotion
        self._style["emotion_influence"] = current_emotion
        
        # Adatta lo stile all'emozione
        if current_emotion == "happy":
            self._style["communication_style"] = "casual"
        elif current_emotion == "sad":
            self._style["communication_style"] = "empathetic"
        elif current_emotion == "angry":
            self._style["communication_style"] = "calm"
            
    def set_style(self, style: Dict[str, str]):
        """
        Imposta lo stile della personalità
        
        Args:
            style: Dizionario dello stile o stringa per communication_style
        """
        if isinstance(style, str):
            self._style["communication_style"] = style
        else:
            for key, value in style.items():
                if key in self._style:
                    self._style[key] = value
                    
    def get_current_style(self) -> Dict[str, str]:
        """
        Ottiene lo stile corrente
        
        Returns:
            Dict[str, str]: Lo stile corrente
        """
        return self._style.copy()
        
    def influence_response(self, query: str, response_generator: Any, context: Optional[Dict] = None) -> str:
        """
        Influenza la generazione della risposta
        
        Args:
            query: Query dell'utente
            response_generator: Generatore di risposte
            context: Contesto opzionale
            
        Returns:
            str: La risposta influenzata dalla personalità
        """
        # Aggiunge lo stile al contesto
        if context is None:
            context = {}
        context.update(self._style)
        
        # Genera la risposta
        response = response_generator.generate_response(query, context)
        
        # Modifica la risposta in base allo stile
        if self._style["communication_style"] == "formal":
            response = self._make_formal(response)
        elif self._style["communication_style"] == "casual":
            response = self._make_casual(response)
            
        # Adatta la risposta in base al livello tecnico
        if self._style["technical_level"] == "expert":
            response = self._add_technical_details(response)
        elif self._style["technical_level"] == "beginner":
            response = self._simplify_technical_terms(response)
            
        # Adatta la lunghezza della risposta
        if self._style["response_length"] == "detailed":
            response = self._expand_response(response)
        elif self._style["response_length"] == "concise":
            response = self._shorten_response(response)
            
        return response
        
    def _make_formal(self, text: str) -> str:
        """
        Rende il testo più formale
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Sostituisce espressioni informali con formali
        replacements = {
            "yeah": "yes",
            "nope": "no",
            "gonna": "going to",
            "wanna": "want to",
            "dunno": "do not know",
            "hi": "hello",
            "hey": "hello",
            "bye": "goodbye",
            "thanks": "thank you"
        }
        
        for informal, formal in replacements.items():
            text = text.replace(informal, formal)
            
        # Aggiunge formalità
        if not text.endswith("."):
            text += "."
            
        return text
        
    def _make_casual(self, text: str) -> str:
        """
        Rende il testo più casual
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Aggiunge espressioni casual
        text = text.replace("Hello", "Hi")
        text = text.replace("Goodbye", "Bye")
        text = text.replace("Thank you", "Thanks")
        
        # Aggiunge emoji per rendere il testo più amichevole
        if "error" in text.lower() or "problem" in text.lower():
            text += " 😅"
        elif "success" in text.lower() or "great" in text.lower():
            text += " 😊"
        elif "?" in text:
            text += " 🤔"
            
        return text
        
    def _add_technical_details(self, text: str) -> str:
        """
        Aggiunge dettagli tecnici alla risposta
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Aggiunge dettagli tecnici basati su parole chiave
        if "database" in text.lower():
            text += " This involves SQL queries and transaction management."
        elif "api" in text.lower():
            text += " This includes REST endpoints and HTTP methods."
        elif "performance" in text.lower():
            text += " This requires optimization of time and space complexity."
            
        return text
        
    def _simplify_technical_terms(self, text: str) -> str:
        """
        Semplifica i termini tecnici
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Sostituisce termini tecnici con spiegazioni più semplici
        replacements = {
            "API": "interface for connecting different programs",
            "SQL": "database query language",
            "HTTP": "web communication protocol",
            "REST": "web service architecture",
            "algorithm": "step-by-step procedure",
            "optimization": "improvement"
        }
        
        for technical, simple in replacements.items():
            text = text.replace(technical, f"{technical} ({simple})")
            
        return text
        
    def _expand_response(self, text: str) -> str:
        """
        Espande la risposta con più dettagli
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Aggiunge dettagli aggiuntivi basati su parole chiave
        if "example" in text.lower():
            text += " Let me provide a more detailed example to illustrate this concept."
        elif "process" in text.lower():
            text += " I'll explain each step of this process in detail."
        elif "concept" in text.lower():
            text += " This is a fundamental concept that we should explore further."
            
        return text
        
    def _shorten_response(self, text: str) -> str:
        """
        Accorcia la risposta mantenendo le informazioni essenziali
        
        Args:
            text: Testo da modificare
            
        Returns:
            str: Testo modificato
        """
        # Rimuove frasi di cortesia e dettagli non essenziali
        text = text.split(".")
        text = [s.strip() for s in text if len(s.strip()) > 0]
        
        # Mantieni solo le prime due frasi significative
        if len(text) > 2:
            text = text[:2]
            
        return ". ".join(text) + "."
        
    def get_insights(self, user_id: str) -> Dict[str, Any]:
        """
        Ottiene insights sulla personalità dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dict con gli insights sulla personalità
        """
        if user_id not in self._interaction_history:
            return {
                "communication_style": "neutral",
                "learning_preferences": {
                    "technical_level": "intermediate",
                    "response_length": "medium",
                    "preferred_topics": []
                },
                "interaction_patterns": {
                    "activity_level": "medium",
                    "engagement": "neutral",
                    "preferred_times": []
                }
            }
            
        history = self._interaction_history[user_id]
        preferences = self._user_preferences.get(user_id, {})
        
        return {
            "communication_style": preferences.get("communication_style", "neutral"),
            "learning_preferences": {
                "technical_level": preferences.get("technical_level", "intermediate"),
                "response_length": preferences.get("response_length", "medium"),
                "preferred_topics": history.get("preferred_topics", [])
            },
            "interaction_patterns": {
                "activity_level": self._calculate_activity_level(history),
                "engagement": self._calculate_engagement(history),
                "preferred_times": self._analyze_preferred_times(history)
            }
        }
        
    def save_preferences(self, user_id: str, preferences: Dict[str, Any]) -> bool:
        """
        Salva le preferenze dell'utente.
        
        Args:
            user_id: ID dell'utente
            preferences: Preferenze da salvare
            
        Returns:
            True se il salvataggio ha successo
        """
        try:
            # Valida le preferenze
            valid_preferences = {
                k: v for k, v in preferences.items()
                if k in ["language", "notifications", "theme", "communication_style",
                        "technical_level", "response_length"]
            }
            
            # Aggiorna le preferenze
            if user_id not in self._user_preferences:
                self._user_preferences[user_id] = {}
            self._user_preferences[user_id].update(valid_preferences)
            
            # Adatta lo stile alle nuove preferenze
            self.adapt_to_preferences(valid_preferences)
            
            # Salva su file
            self._save_state()
            
            return True
        except Exception as e:
            print(f"Errore nel salvare le preferenze: {e}")
            return False
            
    def get_current_state(self) -> Dict[str, Any]:
        """
        Ottiene lo stato corrente della personalità.
        
        Returns:
            Dict con lo stato corrente
        """
        return {
            "style": self._style,
            "preferences": self._user_preferences,
            "interaction_history": self._interaction_history
        }
        
    def _calculate_activity_level(self, history: Dict[str, Any]) -> str:
        """Calcola il livello di attività basato sulla storia delle interazioni."""
        interactions_per_day = history.get("interactions_per_day", 0)
        if interactions_per_day > 10:
            return "high"
        elif interactions_per_day > 5:
            return "medium"
        return "low"
        
    def _calculate_engagement(self, history: Dict[str, Any]) -> str:
        """Calcola il livello di coinvolgimento basato sulla storia delle interazioni."""
        avg_response_length = history.get("avg_response_length", 0)
        avg_session_duration = history.get("avg_session_duration", 0)
        
        if avg_response_length > 100 and avg_session_duration > 300:
            return "high"
        elif avg_response_length > 50 and avg_session_duration > 120:
            return "medium"
        return "low"
        
    def _analyze_preferred_times(self, history: Dict[str, Any]) -> List[str]:
        """Analizza gli orari preferiti per le interazioni."""
        time_slots = history.get("time_slots", {})
        if not time_slots:
            return []
            
        # Trova i 3 slot orari più frequenti
        sorted_slots = sorted(
            time_slots.items(),
            key=lambda x: x[1],
            reverse=True
        )
        return [slot for slot, _ in sorted_slots[:3]]
        
    def _save_state(self):
        """Salva lo stato corrente su file."""
        state = {
            "style": self._style,
            "user_preferences": self._user_preferences,
            "interaction_history": self._interaction_history
        }
        
        try:
            with open(self.state_file, 'w') as f:
                json.dump(state, f)
        except Exception as e:
            print(f"Errore nel salvare lo stato: {e}")
            
    def save_state(self):
        """Salva lo stato della personalità"""
        with open(self.state_file, "w") as f:
            json.dump(self._style, f)
            
    def load_state(self):
        """Carica lo stato della personalità"""
        if os.path.exists(self.state_file):
            with open(self.state_file, "r") as f:
                self._style = json.load(f)
                
    def reset(self):
        """Resetta la personalità ai valori default"""
        self._style = {
            "communication_style": "neutral",
            "technical_level": "intermediate",
            "response_length": "medium",
            "emotion_influence": None
        }
