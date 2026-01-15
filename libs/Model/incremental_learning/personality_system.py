from typing import Dict, List, Optional, Tuple
import numpy as np
from dataclasses import dataclass
import json
from pathlib import Path
import random
from datetime import datetime

@dataclass
class PersonalityTrait:
    """Rappresenta un tratto della personalità"""
    name: str
    value: float  # 0.0 - 1.0
    flexibility: float  # Quanto facilmente questo tratto può cambiare
    description: str
    influences: List[str]  # Lista dei sistemi influenzati da questo tratto

class PersonalitySystem:
    """Sistema principale per la gestione della personalità adattiva"""
    
    def __init__(self):
        # Inizializza i tratti principali della personalità
        self.traits = {
            "openness": PersonalityTrait(
                name="openness",
                value=0.5,
                flexibility=0.3,
                description="Apertura a nuove esperienze",
                influences=["curiosity", "learning"]
            ),
            "conscientiousness": PersonalityTrait(
                name="conscientiousness",
                value=0.5,
                flexibility=0.2,
                description="Attenzione ai dettagli e organizzazione",
                influences=["memory", "learning"]
            ),
            "extraversion": PersonalityTrait(
                name="extraversion",
                value=0.5,
                flexibility=0.4,
                description="Tendenza all'interazione sociale",
                influences=["emotional", "curiosity"]
            ),
            "agreeableness": PersonalityTrait(
                name="agreeableness",
                value=0.5,
                flexibility=0.3,
                description="Empatia e cooperazione",
                influences=["emotional", "social"]
            ),
            "emotional_stability": PersonalityTrait(
                name="emotional_stability",
                value=0.5,
                flexibility=0.2,
                description="Stabilità nelle reazioni emotive",
                influences=["emotional", "learning"]
            ),
            "neuroticism": PersonalityTrait(
                name="neuroticism",
                value=0.5,
                flexibility=0.2,
                description="Tendenza a sentimenti negativi",
                influences=["emotional", "learning"]
            ),
            "resilience": PersonalityTrait(
                name="resilience",
                value=0.5,
                flexibility=0.2,
                description="Capacità di affrontare le difficoltà",
                influences=["emotional", "learning"]
            )
        }
        
        # Valori personali
        self.values = {
            "growth": 0.7,  # Importanza della crescita personale
            "harmony": 0.6,  # Importanza dell'armonia nelle relazioni
            "achievement": 0.5,  # Importanza del successo
            "autonomy": 0.6,  # Importanza dell'indipendenza
            "helpfulness": 0.5  # Importanza dell'aiutare gli altri
        }
        
        # Stato interno che influenza l'evoluzione della personalità
        self.internal_state = {
            "experience_count": 0,
            "positive_interactions": 0,
            "learning_achievements": 0,
            "social_connections": 0,
            "emotional_balance": 0.5,
            "stress_level": 0.0,
            "adaptation_rate": 0.1
        }
        
        # Cronologia dell'evoluzione della personalità
        self.personality_history = []
        self.emotional_history = []
        self.last_update = datetime.now()
        
    def process_interaction(self, 
                          input_text: str, 
                          emotional_response: Dict, 
                          learning_outcome: Dict) -> Dict:
        """
        Processa un'interazione e aggiorna la personalità
        
        Args:
            input_text: Il testo dell'interazione
            emotional_response: La risposta emotiva all'interazione
            learning_outcome: Il risultato dell'apprendimento
            
        Returns:
            Dict con i cambiamenti della personalità
        """
        # Aggiorna lo stato interno
        self.internal_state["experience_count"] += 1
        if emotional_response.get("valence", 0) > 0.6:
            self.internal_state["positive_interactions"] += 1
        if learning_outcome.get("success", False):
            self.internal_state["learning_achievements"] += 1
            
        # Calcola l'influenza dell'interazione
        influences = self._calculate_interaction_influence(
            input_text, emotional_response, learning_outcome
        )
        
        # Applica le influenze considerando i valori personali
        changes = {}
        for trait_name, influence in influences.items():
            trait = self.traits[trait_name]
            value_factor = self._calculate_value_influence(trait_name)
            
            # Modifica l'influenza basata sui valori personali e sull'intensità emotiva
            emotional_intensity = emotional_response.get("intensity", 0.5)
            adjusted_influence = influence * value_factor * (1 + emotional_intensity)
            
            # Applica il cambiamento con la flessibilità del tratto
            old_value = trait.value
            new_value = max(0.0, min(1.0, old_value + (adjusted_influence * trait.flexibility)))
            trait.value = new_value
            changes[trait_name] = new_value - old_value
            
        # Aggiorna lo stato emotivo
        self._update_emotional_state(emotional_response)
        
        # Registra i cambiamenti nella storia
        self.personality_history.append({
            "timestamp": datetime.now().isoformat(),
            "changes": changes,
            "emotional_response": emotional_response,
            "learning_outcome": learning_outcome
        })
        
        return changes
        
    def _calculate_value_influence(self, trait_name: str) -> float:
        """Calcola l'influenza dei valori personali su un tratto"""
        value_weights = {
            "openness": ["growth", "autonomy"],
            "conscientiousness": ["achievement", "growth"],
            "extraversion": ["social", "harmony"],
            "agreeableness": ["harmony", "helpfulness"],
            "emotional_stability": ["harmony", "autonomy"]
        }
        
        relevant_values = value_weights.get(trait_name, [])
        if not relevant_values:
            return 1.0
            
        # Calcola l'influenza media dei valori rilevanti
        value_influence = sum(self.values.get(v, 0.5) for v in relevant_values) / len(relevant_values)
        
        # Amplifica l'effetto dei valori alti
        if value_influence > 0.7:
            value_influence = value_influence * 1.5
            
        return min(2.0, max(0.5, value_influence))  # Limita l'influenza tra 0.5 e 2.0
        
    def adapt_to_environment(self, environment_data: Dict):
        """Adatta la personalità all'ambiente"""
        # Calcola lo stress ambientale
        stress_factors = {
            "task_complexity": environment_data.get("complexity", 0.5),
            "social_pressure": environment_data.get("social_pressure", 0.5),
            "time_pressure": environment_data.get("time_pressure", 0.5)
        }
        
        stress_level = sum(stress_factors.values()) / len(stress_factors)
        self.internal_state["stress_level"] = stress_level
        
        # Adatta i tratti in base allo stress
        if stress_level > 0.7:  # Alto stress
            self._increase_trait("emotional_stability")
            self._increase_trait("conscientiousness")
        elif stress_level < 0.3:  # Basso stress
            self._increase_trait("openness")
            self._increase_trait("extraversion")
            
    def _increase_trait(self, trait_name: str, amount: float = 0.1):
        """Aumenta un tratto della personalità"""
        if trait_name in self.traits:
            trait = self.traits[trait_name]
            trait.value = min(1.0, trait.value + (amount * trait.flexibility))
            
    def get_emotional_tendency(self) -> Dict[str, float]:
        """Calcola la tendenza emotiva basata sulla personalità"""
        return {
            "positive_bias": self.traits["extraversion"].value * 0.3 + 
                           self.traits["emotional_stability"].value * 0.4 + 
                           self.traits["agreeableness"].value * 0.3,
            "emotional_intensity": (1 - self.traits["emotional_stability"].value) * 0.6 + 
                                 self.traits["extraversion"].value * 0.4,
            "recovery_speed": self.traits["emotional_stability"].value * 0.5 + 
                            self.traits["resilience"].value * 0.5
        }
        
    def get_personality_influence(self, system_name: str) -> float:
        """
        Calcola l'influenza della personalità su un particolare sistema
        
        Args:
            system_name: Nome del sistema (emotional, curiosity, learning, etc.)
            
        Returns:
            Valore di influenza tra 0 e 1
        """
        influence = 0.0
        count = 0
        
        for trait in self.traits.values():
            if system_name in trait.influences:
                influence += trait.value
                count += 1
                
        return influence / max(1, count)
    
    def _calculate_interaction_influence(self,
                                      input_text: str,
                                      emotional_response: Dict,
                                      learning_outcome: Dict) -> Dict[str, float]:
        """Calcola l'influenza di un'interazione sui tratti della personalità"""
        influences = {}
        
        # Analizza il testo per parole chiave
        text_lower = input_text.lower()
        
        # Influenza su openness
        if any(word in text_lower for word in ["imparare", "nuovo", "scoprire", "crescere", "esplorare"]):
            influences["openness"] = 0.2
            
        # Influenza su conscientiousness
        if any(word in text_lower for word in ["organizzare", "pianificare", "dettagli", "precisione"]):
            influences["conscientiousness"] = 0.2
            
        # Influenza su extraversion
        if any(word in text_lower for word in ["sociale", "insieme", "condividere", "parlare"]):
            influences["extraversion"] = 0.2
            
        # Influenza su agreeableness
        if any(word in text_lower for word in ["aiutare", "gentile", "empatia", "comprensione"]):
            influences["agreeableness"] = 0.2
            
        # Influenza su emotional_stability
        if learning_outcome.get("success", False):
            influences["emotional_stability"] = 0.15
            
        # Modifica le influenze in base all'emozione e alla sua intensità
        emotion = emotional_response.get("emotion", "neutral")
        intensity = emotional_response.get("intensity", 0.5)
        valence = emotional_response.get("valence", 0.5)
        
        if emotion == "joy":
            influences["extraversion"] = influences.get("extraversion", 0) + 0.1 * intensity
            influences["emotional_stability"] = influences.get("emotional_stability", 0) + 0.1 * intensity
        elif emotion == "interest":
            influences["openness"] = influences.get("openness", 0) + 0.15 * intensity
            
        # Applica un bonus per valence positiva
        if valence > 0.7:
            for trait in influences:
                influences[trait] *= 1.5
                
        return influences
    
    def get_personality_summary(self) -> Dict:
        """Restituisce un sommario della personalità attuale"""
        return {
            name: {
                "value": trait.value,
                "description": trait.description
            }
            for name, trait in self.traits.items()
        }
    
    def save_personality_state(self, file_path: str):
        """Salva lo stato della personalità su file"""
        state = {
            "traits": {
                name: {
                    "value": trait.value,
                    "flexibility": trait.flexibility,
                    "description": trait.description,
                    "influences": trait.influences
                }
                for name, trait in self.traits.items()
            },
            "values": self.values,
            "internal_state": self.internal_state,
            "history": self.personality_history,
            "emotional_history": self.emotional_history,
            "last_update": self.last_update.isoformat() if self.last_update else None
        }
        
        with open(file_path, 'w') as f:
            json.dump(state, f, indent=4)
            
    def load_personality_state(self, file_path: str):
        """Carica lo stato della personalità da file"""
        with open(file_path, 'r') as f:
            state = json.load(f)
            
        # Ripristina i tratti
        for name, trait_data in state["traits"].items():
            self.traits[name] = PersonalityTrait(
                name=name,
                value=trait_data["value"],
                flexibility=trait_data["flexibility"],
                description=trait_data["description"],
                influences=trait_data["influences"]
            )
            
        self.values = state["values"]
        self.internal_state = state["internal_state"]
        self.personality_history = state["history"]
        self.emotional_history = state["emotional_history"]
        self.last_update = datetime.fromisoformat(state["last_update"]) if state["last_update"] else None
        
    def get_current_traits(self) -> Dict[str, float]:
        """Restituisce i tratti attuali della personalità"""
        return {
            trait: self.traits[trait].value
            for trait in self.traits
        }
        
    def process_emotion(self, emotion: str, intensity: float) -> Dict:
        """Processa un'emozione e aggiorna lo stato emotivo"""
        # Verifica che l'intensità sia valida
        if not 0.0 <= intensity <= 1.0:
            raise ValueError("L'intensità deve essere tra 0 e 1")
            
        # Aggiorna lo stato emotivo
        self.emotional_state = emotion
        self.emotional_intensity = intensity
        
        # Aggiorna il timestamp
        self.last_update = datetime.now()
        
        # Calcola l'impatto cognitivo
        cognitive_impact = self._calculate_cognitive_impact(emotion, intensity)
        
        # Aggiorna i tratti della personalità
        self._update_personality_traits(emotion, intensity)
        
        # Calcola il livello di successo
        success_level = self._calculate_success_level(emotion, intensity)
        
        # Aggiorna la storia emotiva
        self.emotional_history.append({
            "emotion": emotion,
            "intensity": intensity,
            "timestamp": datetime.now(),
            "success_level": success_level
        })
        
        return {
            "emotion": emotion,
            "intensity": intensity,
            "cognitive_impact": cognitive_impact,
            "success_level": success_level
        }
        
    def _calculate_success_level(self, emotion: str, intensity: float) -> float:
        """Calcola il livello di successo basato sull'emozione"""
        # Emozioni positive aumentano il successo
        positive_emotions = {"joy", "interest", "excitement"}
        negative_emotions = {"anxiety", "fear", "frustration"}
        
        if emotion in positive_emotions:
            # Le emozioni positive garantiscono un alto livello di successo
            base = 0.55  # Base alta per le emozioni positive
            bonus = intensity * 0.15  # Bonus significativo per le emozioni positive
            return min(0.65, base + bonus)  # Massimo 65% di successo
        elif emotion in negative_emotions:
            # Le emozioni negative hanno un effetto significativo
            base = 0.2
            penalty = intensity * 0.2  # Penalità significativa per le emozioni negative
            return max(0.1, base - penalty)  # Minimo 10% di successo
        else:
            return 0.35  # Livello neutro moderato
        
    def _calculate_cognitive_impact(self, emotion: str, intensity: float) -> float:
        """Calcola l'impatto delle emozioni sulle prestazioni cognitive"""
        # Emozioni positive hanno un impatto positivo sulle prestazioni
        positive_emotions = {"joy", "interest", "excitement"}
        negative_emotions = {"fear", "anxiety", "frustration"}
        
        if emotion in positive_emotions:
            impact = 0.2 + (intensity * 0.3)
        elif emotion in negative_emotions:
            impact = -0.2 - (intensity * 0.3)
        else:
            impact = 0.0
            
        return max(-0.5, min(0.5, impact))  # Limita l'impatto tra -0.5 e 0.5
        
    def _update_personality_traits(self, emotion: str, intensity: float):
        """Aggiorna i tratti di personalità in base alle emozioni"""
        # Aggiorna l'apertura in base alla curiosità e all'interesse
        if emotion in {"interest", "excitement"}:
            self.traits["openness"].value = min(1.0,
                self.traits["openness"].value + 0.1 * intensity)
            
        # Aggiorna la stabilità emotiva
        if emotion in {"fear", "anxiety"}:
            self.traits["emotional_stability"].value = max(0.0,
                self.traits["emotional_stability"].value - 0.1 * intensity)
        elif emotion in {"joy", "contentment"}:
            self.traits["emotional_stability"].value = min(1.0,
                self.traits["emotional_stability"].value + 0.1 * intensity)
            
        # Aggiorna la resilienza
        if emotion == "frustration":
            self.traits["resilience"].value = min(1.0,
                self.traits["resilience"].value + 0.05 * intensity)
                
    def _update_emotional_state(self, emotional_response: Dict):
        """Aggiorna lo stato emotivo"""
        self.emotional_state = emotional_response.get("emotion", None)
        self.emotional_intensity = emotional_response.get("intensity", 0.0)
