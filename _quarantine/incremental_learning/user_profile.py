"""
Sistema di profilo utente con apprendimento incrementale delle preferenze
"""
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass, field
import json
from collections import defaultdict
import time

@dataclass
class CommunicationPreference:
    """Preferenze di comunicazione dell'utente"""
    formality_level: float = 0.5    # 0 = informale, 1 = formale
    verbosity_level: float = 0.5    # 0 = conciso, 1 = dettagliato
    technical_level: float = 0.5    # 0 = base, 1 = tecnico
    emotional_style: str = "neutral" # stile emotivo della comunicazione
    preferred_topics: List[str] = field(default_factory=list)  # topic preferiti
    avoided_topics: List[str] = field(default_factory=list)    # topic da evitare
    language: str = "it"            # lingua preferita
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte le preferenze in un dizionario"""
        return {
            'formality_level': self.formality_level,
            'verbosity_level': self.verbosity_level,
            'technical_level': self.technical_level,
            'emotional_style': self.emotional_style,
            'preferred_topics': self.preferred_topics.copy(),
            'avoided_topics': self.avoided_topics.copy(),
            'language': self.language
        }
    
    def update_from_feedback(self, feedback: Dict[str, float]):
        """Aggiorna le preferenze basandosi sul feedback"""
        if 'formality_level' in feedback:
            self.formality_level = (self.formality_level * 0.6 + feedback['formality_level'] * 0.4)
        if 'verbosity_level' in feedback:
            self.verbosity_level = (self.verbosity_level * 0.6 + feedback['verbosity_level'] * 0.4)
        if 'technical_level' in feedback:
            # Diamo più peso al feedback tecnico per farlo crescere più rapidamente
            self.technical_level = (self.technical_level * 0.4 + feedback['technical_level'] * 0.6)
        if 'emotional_style' in feedback:
            self.emotional_style = feedback['emotional_style']

@dataclass
class InteractionMetrics:
    """Metriche di interazione dell'utente"""
    total_interactions: int = 0
    positive_responses: int = 0
    negative_responses: int = 0
    average_session_length: float = 0.0
    topic_frequencies: Dict[str, int] = field(default_factory=dict)
    
    # Metriche Evolutive (Lifelong Learning)
    first_interaction_timestamp: float = field(default_factory=time.time)
    last_interaction_timestamp: float = field(default_factory=time.time)
    synergy_score: float = 0.0
    evolution_stage: str = "Analisi Iniziale"
    
    def update_from_interaction(self, interaction_data: Dict[str, Any]):
        """Aggiorna le metriche basandosi su una nuova interazione"""
        self.total_interactions += 1
        self.last_interaction_timestamp = time.time()
        
        # Aggiorna risposte positive/negative basate sul sentiment
        if interaction_data.get('sentiment', 0) > 0:
            self.positive_responses += 1
        elif interaction_data.get('sentiment', 0) < 0:
            self.negative_responses += 1
            
        # Aggiorna durata sessione
        if 'session_length' in interaction_data:
            total_length = self.average_session_length * (self.total_interactions - 1)
            total_length += interaction_data['session_length']
            self.average_session_length = total_length / self.total_interactions
            
        # Aggiorna frequenze topic
        if 'topic' in interaction_data:
            topic = interaction_data['topic']
            self.topic_frequencies[topic] = self.topic_frequencies.get(topic, 0) + 1
    
    def get_engagement_metrics(self) -> Dict[str, float]:
        """Calcola metriche di engagement"""
        total_responses = self.positive_responses + self.negative_responses
        return {
            'response_ratio': self.positive_responses / total_responses if total_responses > 0 else 0.5,
            'avg_session_length': self.average_session_length,
            'interaction_frequency': self.total_interactions
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte le metriche in un dizionario"""
        return {
            'total_interactions': self.total_interactions,
            'positive_responses': self.positive_responses,
            'negative_responses': self.negative_responses,
            'average_session_length': self.average_session_length,
            'topic_frequencies': self.topic_frequencies.copy()
        }

@dataclass
class UserProfile:
    """Profilo utente con preferenze e metriche di interazione"""
    user_id: str
    name: Optional[str] = None
    age: Optional[int] = None
    creation_time: float = field(default_factory=time.time)
    last_update: float = field(default_factory=time.time)
    preferences: CommunicationPreference = field(default_factory=CommunicationPreference)
    metrics: InteractionMetrics = field(default_factory=InteractionMetrics)
    interaction_history: List[Dict[str, Any]] = field(default_factory=list)
    
    def update_from_interaction(self, interaction_data: Dict[str, Any]):
        """Aggiorna il profilo basandosi su una nuova interazione"""
        self.last_update = time.time()
        self.interaction_history.append(interaction_data)
        
        # Limita la storia delle interazioni
        if len(self.interaction_history) > 100:
            self.interaction_history = self.interaction_history[-100:]
            
        # Aggiorna metriche
        self.metrics.update_from_interaction(interaction_data)
        
        # Aggiorna preferenze dai feedback specifici
        feedback = {}
        if 'formality_feedback' in interaction_data:
            feedback['formality_level'] = interaction_data['formality_feedback']
        if 'verbosity_feedback' in interaction_data:
            feedback['verbosity_level'] = interaction_data['verbosity_feedback']
        if 'technical_feedback' in interaction_data:
            feedback['technical_level'] = interaction_data['technical_feedback']
        if 'emotional_feedback' in interaction_data:
            feedback['emotional_style'] = 'empathetic' if interaction_data['emotional_feedback'] > 0.7 else 'neutral'
        
        # Aggiorna topic preferiti se il feedback è positivo
        if 'topic' in interaction_data and interaction_data.get('topic_feedback', 0) > 0.7:
            if interaction_data['topic'] not in self.preferences.preferred_topics:
                self.preferences.preferred_topics.append(interaction_data['topic'])
        
        if feedback:
            self.preferences.update_from_feedback(feedback)
    
    def get_technical_level(self) -> float:
        """Ottieni il livello tecnico corrente"""
        return self.preferences.technical_level
    
    def get_communication_style(self) -> Dict[str, Any]:
        """Ottieni lo stile di comunicazione corrente"""
        return {
            'formality': self.preferences.formality_level,
            'verbosity': self.preferences.verbosity_level,
            'technical_level': self.preferences.technical_level,
            'emotional_style': self.preferences.emotional_style,
            'preferred_topics': self.preferences.preferred_topics.copy()
        }
    
    def get_interests(self) -> List[str]:
        """Restituisce i topic di interesse dell'utente"""
        return self.preferences.preferred_topics
    
    def save_to_file(self, filepath: str):
        """Salva il profilo su file"""
        data = {
            'user_id': self.user_id,
            'name': self.name,
            'age': self.age,
            'creation_time': self.creation_time,
            'last_update': self.last_update,
            'preferences': self.preferences.to_dict(),
            'metrics': self.metrics.to_dict(),
            'interaction_history': self.interaction_history
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def load_from_file(cls, filepath: str) -> 'UserProfile':
        """Carica il profilo da file"""
        with open(filepath, 'r') as f:
            data = json.load(f)
        
        profile = cls(data['user_id'])
        profile.name = data.get('name')
        profile.age = data.get('age')
        profile.creation_time = data['creation_time']
        profile.last_update = data['last_update']
        
        # Ricostruisci preferenze
        prefs = CommunicationPreference()
        prefs.__dict__.update(data['preferences'])
        profile.preferences = prefs
        
        # Ricostruisci metriche
        metrics = InteractionMetrics()
        metrics.__dict__.update(data['metrics'])
        profile.metrics = metrics
        
        profile.interaction_history = data['interaction_history']
        return profile
