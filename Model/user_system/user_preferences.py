"""UserPreferenceAnalyzer - Sistema di analisi preferenze utente per ALLMA."""

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from dataclasses import dataclass, field
from enum import Enum
from Model.user_system.learning_preference import LearningStyle, LearningPreference
from Model.types import CommunicationStyle

# Re-export types
__all__ = ['LearningStyle', 'LearningPreference', 'CommunicationStyle']

class ResponseStyle(str, Enum):
    """Stili di risposta possibili."""
    CODE_FIRST = "code_first"  # Inizia con esempi di codice
    CONCEPT_FIRST = "concept_first"  # Inizia con spiegazione concettuale
    VISUAL_FIRST = "visual_first"  # Inizia con diagrammi/immagini
    INTERACTIVE = "interactive"  # Stile interattivo
    BALANCED = "balanced"  # Stile bilanciato

@dataclass
class ResponsePreference:
    """Preferenze per lo stile di risposta."""
    format: ResponseStyle = ResponseStyle.BALANCED
    include_examples: bool = True
    include_references: bool = True
    technical_level: int = 3
    verbosity: int = 3

@dataclass
class UserPreferenceData:
    """Dati sulle preferenze dell'utente."""
    user_id: str
    learning_style: LearningStyle = LearningStyle.BALANCED
    communication_style: CommunicationStyle = CommunicationStyle.BALANCED
    interactions: List[Dict] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)
    technical_level: int = 3
    verbosity: int = 3

@dataclass
class UserPreferences:
    """Preferenze dell'utente"""
    learning_style: LearningStyle
    technical_level: int
    metadata: Optional[Dict[str, Any]] = None

class UserPreferenceAnalyzer:
    """Sistema di analisi preferenze utente."""
    
    def __init__(self):
        """Inizializza l'analizzatore di preferenze."""
        self.user_interactions: Dict[str, List[Tuple[str, str, datetime]]] = {}
        self.topic_preferences: Dict[str, Dict[str, float]] = {}
        self.learning_styles: Dict[str, LearningPreference] = {}
        
    def record_interaction(
        self,
        user_id: str,
        text: str,
        interaction_type: str
    ) -> None:
        """
        Registra un'interazione con l'utente.
        
        Args:
            user_id: ID dell'utente
            text: Testo dell'interazione
            interaction_type: Tipo di interazione
        """
        if user_id not in self.user_interactions:
            self.user_interactions[user_id] = []
        self.user_interactions[user_id].append(
            (text, interaction_type, datetime.now())
        )
        
    def record_topic_interaction(
        self,
        user_id: str,
        text: str,
        interaction_type: str,
        topic: str
    ) -> None:
        """
        Registra un'interazione con un topic specifico.
        
        Args:
            user_id: ID dell'utente
            text: Testo dell'interazione
            interaction_type: Tipo di interazione
            topic: Topic dell'interazione
        """
        # Aggiorna score del topic
        if user_id not in self.topic_preferences:
            self.topic_preferences[user_id] = {}
        if interaction_type == "positive_feedback":
            self.topic_preferences[user_id][topic] = self.topic_preferences[user_id].get(topic, 0) + 1.0
        elif interaction_type == "negative_feedback":
            self.topic_preferences[user_id][topic] = self.topic_preferences[user_id].get(topic, 0) - 0.5
        elif interaction_type in ["topic_interest", "language_preference"]:
            self.topic_preferences[user_id][topic] = self.topic_preferences[user_id].get(topic, 0) + 0.5
            
    def analyze_learning_style(
        self,
        user_id: str
    ) -> LearningPreference:
        """
        Analizza lo stile di apprendimento dell'utente.

        Args:
            user_id: ID dell'utente

        Returns:
            Preferenze di apprendimento
        """
        # Inizializza i conteggi degli stili
        style_counts = {
            LearningStyle.VISUAL: 0,
            LearningStyle.AUDITORY: 0,
            LearningStyle.KINESTHETIC: 0,
            LearningStyle.THEORETICAL: 0,
            LearningStyle.BALANCED: 0
        }

        # Analizza le interazioni dell'utente
        interactions = self.user_interactions.get(user_id, [])
        if not interactions:
            return LearningPreference(
                style=LearningStyle.BALANCED,
                technical_level=3
            )

        # Analizza le interazioni per determinare lo stile
        for text, interaction_type, _ in interactions:
            if "immagine" in text.lower() or "diagramma" in text.lower():
                style_counts[LearningStyle.VISUAL] += 1
            elif "ascolta" in text.lower() or "spiega" in text.lower():
                style_counts[LearningStyle.AUDITORY] += 1
            elif "prova" in text.lower() or "esempio" in text.lower():
                style_counts[LearningStyle.KINESTHETIC] += 1
            elif "teoria" in text.lower() or "concetto" in text.lower():
                style_counts[LearningStyle.THEORETICAL] += 1

        # Determina lo stile predominante
        max_count = max(style_counts.values())
        if max_count == 0:
            predominant_style = LearningStyle.BALANCED
        else:
            predominant_styles = [
                style for style, count in style_counts.items()
                if count == max_count
            ]
            predominant_style = predominant_styles[0]

        # Calcola il livello tecnico
        technical_level = self._calculate_technical_level(user_id)

        return LearningPreference(
            style=predominant_style,
            technical_level=technical_level
        )
        
    def get_user_preferences(self, user_id: str) -> Optional[LearningPreference]:
        """
        Recupera le preferenze di apprendimento di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Preferenze di apprendimento o None se non trovate
        """
        return self.learning_styles.get(user_id)

    def get_learning_style(self, user_id: str) -> LearningStyle:
        """
        Recupera lo stile di apprendimento dell'utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Stile di apprendimento
        """
        if user_id in self.learning_styles:
            return self.learning_styles[user_id].style
        return LearningStyle.BALANCED

    def adapt_response_style(
        self,
        user_id: str,
        query: str
    ) -> ResponsePreference:
        """
        Adatta lo stile di risposta alle preferenze dell'utente.
        
        Args:
            user_id: ID dell'utente
            query: Query dell'utente
            
        Returns:
            Stile di risposta adattato
        """
        # Prima controlla se esistono già delle preferenze
        if user_id in self.learning_styles:
            style = self.learning_styles[user_id]
        else:
            # Se non esistono, analizza lo stile
            style = self.analyze_learning_style(user_id)
        
        if style.style == LearningStyle.VISUAL:
            return ResponsePreference(
                format=ResponseStyle.VISUAL_FIRST,
                include_examples=True,
                include_references=False,
                technical_level=3,
                verbosity=2
            )
        elif style.style == LearningStyle.AUDITORY:
            return ResponsePreference(
                format=ResponseStyle.CONCEPT_FIRST,
                include_examples=True,
                include_references=True,
                technical_level=4,
                verbosity=4
            )
        elif style.style == LearningStyle.KINESTHETIC:
            return ResponsePreference(
                format=ResponseStyle.CODE_FIRST,
                include_examples=True,
                include_references=False,
                technical_level=4,
                verbosity=2
            )
        elif style.style == LearningStyle.THEORETICAL:
            return ResponsePreference(
                format=ResponseStyle.CONCEPT_FIRST,
                include_examples=True,
                include_references=True,
                technical_level=5,
                verbosity=4
            )
        else:  # LearningStyle.BALANCED
            return ResponsePreference(
                format=ResponseStyle.BALANCED,
                include_examples=True,
                include_references=True,
                technical_level=3,
                verbosity=3
            )
            
    def update_user_preference(
        self,
        user_id: str,
        style: LearningStyle,
        confidence: float = 0.8
    ) -> None:
        """
        Aggiorna manualmente le preferenze di un utente.
        
        Args:
            user_id: ID dell'utente
            style: Stile di apprendimento
            confidence: Livello di confidenza
        """
        self.learning_styles[user_id] = LearningPreference(
            style=style,
            confidence=confidence,
            last_updated=datetime.now()
        )
        
    def get_topic_preferences(
        self,
        user_id: str
    ) -> Dict[str, float]:
        """
        Recupera le preferenze per topic di un utente.
        
        Args:
            user_id: ID dell'utente
            
        Returns:
            Dizionario topic -> score
        """
        return self.topic_preferences.get(user_id, {})

    def _calculate_technical_level(self, user_id: str) -> int:
        # TO DO: implementare il calcolo del livello tecnico
        return 3
