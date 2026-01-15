"""
Modulo per la gestione del profilo utente e delle preferenze
"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import time
import json

@dataclass
class UserPreferences:
    """Preferenze dell'utente"""
    communication_style: str = 'neutral'  # formal, casual, neutral
    response_length: str = 'medium'  # short, medium, long
    interaction_frequency: str = 'medium'  # low, medium, high
    emotional_sensitivity: float = 0.5
    social_engagement: float = 0.5
    favorite_topics: List[str] = field(default_factory=list)
    
class UserProfile:
    """Gestisce il profilo utente e le preferenze"""
    
    def __init__(self):
        self.preferences = UserPreferences()
        self.interaction_history = []
        self.emotional_history = []
        self.social_history = []
        self.last_update = time.time()
        
    def update_preferences(self, user_input: str, emotional_state, social_context):
        """Aggiorna le preferenze dell'utente in base all'interazione"""
        # Aggiorna la cronologia
        self.interaction_history.append({
            'input': user_input,
            'timestamp': time.time(),
            'emotional_state': emotional_state,
            'social_context': social_context
        })
        
        # Aggiorna la cronologia emotiva
        self.emotional_history.append({
            'state': emotional_state,
            'timestamp': time.time()
        })
        
        # Aggiorna la cronologia sociale
        self.social_history.append({
            'context': social_context,
            'timestamp': time.time()
        })
        
        # Analizza l'input per aggiornare le preferenze
        self._analyze_communication_style(user_input)
        self._update_emotional_sensitivity(emotional_state)
        self._update_social_engagement(social_context)
        
        # Aggiorna il timestamp
        self.last_update = time.time()
        
    def _analyze_communication_style(self, text: str):
        """Analizza lo stile di comunicazione dell'utente"""
        # Indicatori di formalità
        formal_indicators = {'cortesemente', 'gentilmente', 'per favore', 'grazie', 'potrebbe', 'vorrei'}
        casual_indicators = {'ehi', 'ciao', 'hey', 'ok', 'bello', 'forte'}
        
        text_lower = text.lower()
        # Conta gli indicatori
        formal_count = sum(1 for word in formal_indicators if word in text_lower)
        casual_count = sum(1 for word in casual_indicators if word in text_lower)
        
        # Aggiorna lo stile di comunicazione
        if formal_count > casual_count:
            self.preferences.communication_style = 'formal'
        elif casual_count > formal_count:
            self.preferences.communication_style = 'casual'
        # Se sono uguali, mantiene lo stile corrente
        
    def _update_emotional_sensitivity(self, emotional_state):
        """Aggiorna la sensibilità emotiva"""
        # Calcola la media mobile della sensibilità
        alpha = 0.3  # Fattore di smoothing
        current_sensitivity = emotional_state.intensity
        
        self.preferences.emotional_sensitivity = (
            alpha * current_sensitivity +
            (1 - alpha) * self.preferences.emotional_sensitivity
        )
        
    def _update_social_engagement(self, social_context):
        """Aggiorna il livello di engagement sociale"""
        # Calcola la media mobile dell'engagement
        alpha = 0.3  # Fattore di smoothing
        current_engagement = social_context.engagement_level
        
        self.preferences.social_engagement = (
            alpha * current_engagement +
            (1 - alpha) * self.preferences.social_engagement
        )
        
    def get_preferences(self) -> Dict:
        """Restituisce le preferenze correnti"""
        return {
            'communication_style': self.preferences.communication_style,
            'response_length': self.preferences.response_length,
            'interaction_frequency': self.preferences.interaction_frequency,
            'emotional_sensitivity': self.preferences.emotional_sensitivity,
            'social_engagement': self.preferences.social_engagement,
            'favorite_topics': self.preferences.favorite_topics
        }
        
    def get_profile_data(self) -> Dict:
        """Restituisce tutti i dati del profilo"""
        return {
            'preferences': self.get_preferences(),
            'interaction_history': self.interaction_history,
            'emotional_history': self.emotional_history,
            'social_history': self.social_history,
            'last_update': self.last_update,
            'interests': [topic for topic in self.preferences.favorite_topics]
        }
        
    def save_to_file(self, filename: str):
        """Salva il profilo su file"""
        # Converti le cronologie in dizionari
        interaction_history = []
        for item in self.interaction_history:
            interaction_dict = {
                'input': item['input'],
                'timestamp': item['timestamp'],
                'emotional_state': item['emotional_state'].to_dict() if hasattr(item['emotional_state'], 'to_dict') else item['emotional_state'],
                'social_context': item['social_context'].to_dict() if hasattr(item['social_context'], 'to_dict') else item['social_context']
            }
            interaction_history.append(interaction_dict)
            
        emotional_history = []
        for item in self.emotional_history:
            emotional_dict = {
                'state': item['state'].to_dict() if hasattr(item['state'], 'to_dict') else item['state'],
                'timestamp': item['timestamp']
            }
            emotional_history.append(emotional_dict)
            
        social_history = []
        for item in self.social_history:
            social_dict = {
                'context': item['context'].to_dict() if hasattr(item['context'], 'to_dict') else item['context'],
                'timestamp': item['timestamp']
            }
            social_history.append(social_dict)
        
        profile_data = {
            'preferences': self.get_preferences(),
            'interaction_history': interaction_history,
            'emotional_history': emotional_history,
            'social_history': social_history,
            'last_update': self.last_update
        }
        
        with open(filename, 'w') as f:
            json.dump(profile_data, f, indent=4)
            
    def load_from_file(self, filename: str):
        """Carica il profilo da file"""
        with open(filename, 'r') as f:
            profile_data = json.load(f)
            
        # Ripristina le preferenze
        for key, value in profile_data['preferences'].items():
            setattr(self.preferences, key, value)
            
        # Ripristina le cronologie
        self.interaction_history = profile_data['interaction_history']
        self.emotional_history = profile_data['emotional_history']
        self.social_history = profile_data['social_history']
        self.last_update = profile_data['last_update']
