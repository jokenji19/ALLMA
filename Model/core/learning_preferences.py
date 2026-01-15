"""Definizione delle preferenze di apprendimento dell'utente."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from datetime import datetime, date
from typing import Any
from Model.user_system.user_preferences import LearningStyle, CommunicationStyle, LearningPreference

# @dataclass
# class LearningPreference:
#     """Rappresenta le preferenze di apprendimento di un utente."""
    
#     primary_style: LearningStyle = LearningStyle.BALANCED
#     secondary_style: Optional[LearningStyle] = None
#     communication_style: CommunicationStyle = CommunicationStyle.BALANCED
#     confidence: float = 0.0
#     last_updated: Optional[datetime] = None
#     detail_level: float = 0.5
#     examples_vs_theory: float = 0.5
#     technical_level: float = 0.5
#     preferred_topics: List[str] = field(default_factory=list)
#     avoided_topics: List[str] = field(default_factory=list)
#     format_preferences: Dict[str, float] = field(default_factory=lambda: {
#         "code": 0.5,
#         "diagrams": 0.5,
#         "text": 0.5,
#         "interactive": 0.5
#     })

#     def __post_init__(self):
#         """Inizializza gli attributi dopo la creazione dell'istanza."""
#         # Assicurati che primary_style sia un'istanza di LearningStyle
#         if isinstance(self.primary_style, str):
#             self.primary_style = LearningStyle(self.primary_style.lower())
#         elif not isinstance(self.primary_style, LearningStyle):
#             self.primary_style = LearningStyle.BALANCED
            
#         # Assicurati che secondary_style sia un'istanza di LearningStyle
#         if isinstance(self.secondary_style, str):
#             self.secondary_style = LearningStyle(self.secondary_style.lower())
#         elif not isinstance(self.secondary_style, LearningStyle) and self.secondary_style is not None:
#             self.secondary_style = None

#         # Assicurati che communication_style sia un'istanza di CommunicationStyle
#         if isinstance(self.communication_style, str):
#             self.communication_style = CommunicationStyle(self.communication_style.lower())
#         elif not isinstance(self.communication_style, CommunicationStyle):
#             self.communication_style = CommunicationStyle.BALANCED

#         # Assicurati che last_updated sia un'istanza di datetime
#         if self.last_updated is None:
#             self.last_updated = datetime.now()
#         elif isinstance(self.last_updated, str):
#             try:
#                 self.last_updated = datetime.fromisoformat(self.last_updated)
#             except ValueError:
#                 self.last_updated = datetime.now()

#         # Normalizza i valori numerici
#         self.confidence = max(0.0, min(1.0, float(self.confidence)))
#         self.detail_level = max(0.0, min(1.0, float(self.detail_level)))
#         self.examples_vs_theory = max(0.0, min(1.0, float(self.examples_vs_theory)))
#         self.technical_level = max(0.0, min(1.0, float(self.technical_level)))

#         # Assicurati che le liste siano effettivamente liste
#         if not isinstance(self.preferred_topics, list):
#             self.preferred_topics = list(self.preferred_topics) if self.preferred_topics else []
#         if not isinstance(self.avoided_topics, list):
#             self.avoided_topics = list(self.avoided_topics) if self.avoided_topics else []

#         # Normalizza le preferenze di formato
#         if not isinstance(self.format_preferences, dict):
#             self.format_preferences = {
#                 "code": 0.5,
#                 "diagrams": 0.5,
#                 "text": 0.5,
#                 "interactive": 0.5
#             }
#         else:
#             for key in ["code", "diagrams", "text", "interactive"]:
#                 if key not in self.format_preferences:
#                     self.format_preferences[key] = 0.5
#                 else:
#                     self.format_preferences[key] = max(0.0, min(1.0, float(self.format_preferences[key])))

#     def to_dict(self) -> Dict[str, Any]:
#         """Converte le preferenze in un dizionario."""
#         return {
#             "primary_style": self.primary_style.value,
#             "secondary_style": self.secondary_style.value if self.secondary_style else None,
#             "communication_style": self.communication_style.value,
#             "confidence": self.confidence,
#             "last_updated": self.last_updated.isoformat() if self.last_updated else None,
#             "detail_level": self.detail_level,
#             "examples_vs_theory": self.examples_vs_theory,
#             "technical_level": self.technical_level,
#             "preferred_topics": self.preferred_topics,
#             "avoided_topics": self.avoided_topics,
#             "format_preferences": self.format_preferences
#         }

#     @classmethod
#     def from_dict(cls, data: Dict[str, Any]) -> 'LearningPreference':
#         """
#         Crea un'istanza di LearningPreference da un dizionario.
        
#         Args:
#             data: Dizionario con i dati delle preferenze
            
#         Returns:
#             Nuova istanza di LearningPreference
#         """
#         # Gestisci sia il formato con learning_style come sotto-dizionario
#         # che il formato con style direttamente nel dizionario
#         if "learning_style" in data and isinstance(data["learning_style"], dict):
#             learning_style = data["learning_style"]
#             primary_style = learning_style.get("style", LearningStyle.BALANCED)
#             secondary_style = learning_style.get("secondary_style")
#             confidence = learning_style.get("confidence", 0.0)
#         else:
#             # Se lo stile è direttamente nel dizionario principale
#             primary_style = data.get("style", LearningStyle.BALANCED)
#             secondary_style = data.get("secondary_style")
#             confidence = data.get("confidence", 0.0)

#         # Gestisci sia il formato con communication_style come sotto-dizionario
#         # che il formato con style direttamente nel dizionario
#         if "communication_style" in data and isinstance(data["communication_style"], dict):
#             comm_style = data["communication_style"]
#             communication_style = comm_style.get("style", CommunicationStyle.BALANCED)
#         else:
#             communication_style = data.get("communication_style", CommunicationStyle.BALANCED)
        
#         # Crea l'istanza con i valori di default
#         return cls(
#             primary_style=primary_style,
#             secondary_style=secondary_style,
#             communication_style=communication_style,
#             confidence=confidence,
#             last_updated=datetime.now(),
#             detail_level=data.get("detail_level", 0.5),
#             examples_vs_theory=data.get("examples_vs_theory", 0.5),
#             technical_level=data.get("technical_level", 0.5),
#             preferred_topics=data.get("preferred_topics", []),
#             avoided_topics=data.get("avoided_topics", []),
#             format_preferences=data.get("format_preferences", {
#                 "code": 0.5,
#                 "diagrams": 0.5,
#                 "text": 0.5,
#                 "interactive": 0.5
#             })
#         )

#     def update_from_interaction(self, interaction_data: Dict) -> None:
#         """
#         Aggiorna le preferenze in base a un'interazione.
        
#         Args:
#             interaction_data: Dati sull'interazione con l'utente
#         """
#         # Aggiorna il livello di dettaglio se specificato
#         if "detail_level" in interaction_data:
#             self.detail_level = (
#                 self.detail_level * 0.8 + 
#                 interaction_data["detail_level"] * 0.2
#             )
        
#         # Aggiorna la preferenza esempi vs teoria
#         if "examples_used" in interaction_data:
#             self.examples_vs_theory = (
#                 self.examples_vs_theory * 0.8 + 
#                 (1.0 if interaction_data["examples_used"] else 0.0) * 0.2
#             )
        
#         # Aggiorna il livello tecnico
#         if "technical_terms_used" in interaction_data:
#             self.technical_level = (
#                 self.technical_level * 0.8 + 
#                 interaction_data["technical_terms_used"] * 0.2
#             )
        
#         # Aggiorna i topic preferiti
#         if "topic" in interaction_data and interaction_data.get("positive_feedback", False):
#             if interaction_data["topic"] not in self.preferred_topics:
#                 self.preferred_topics.append(interaction_data["topic"])
        
#         # Aggiorna i topic da evitare
#         if "topic" in interaction_data and interaction_data.get("negative_feedback", False):
#             if interaction_data["topic"] not in self.avoided_topics:
#                 self.avoided_topics.append(interaction_data["topic"])
        
#         # Aggiorna le preferenze di formato
#         if "format_used" in interaction_data and "format_success" in interaction_data:
#             format_type = interaction_data["format_used"]
#             if format_type in self.format_preferences:
#                 self.format_preferences[format_type] = (
#                     self.format_preferences[format_type] * 0.8 +
#                     (1.0 if interaction_data["format_success"] else 0.0) * 0.2
#                 )

#     def get_preferred_format(self) -> str:
#         """
#         Determina il formato preferito in base alle preferenze attuali.
        
#         Returns:
#             Il formato con il punteggio più alto
#         """
#         return max(self.format_preferences.items(), key=lambda x: x[1])[0]

#     def is_topic_preferred(self, topic: str) -> bool:
#         """
#         Verifica se un topic è tra quelli preferiti.
        
#         Args:
#             topic: Topic da verificare
            
#         Returns:
#             True se il topic è preferito
#         """
#         return topic in self.preferred_topics

#     def is_topic_avoided(self, topic: str) -> bool:
#         """
#         Verifica se un topic è tra quelli da evitare.
        
#         Args:
#             topic: Topic da verificare
            
#         Returns:
#             True se il topic è da evitare
#         """
#         return topic in self.avoided_topics
