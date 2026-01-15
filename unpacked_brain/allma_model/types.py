"""Tipi di dati comuni usati in tutto il sistema ALLMA."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from datetime import datetime
from allma_model.response_system.response_format import ResponseFormat

class TechnicalLevel(Enum):
    """Livelli di competenza tecnica."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"

class LearningStyle(str, Enum):
    """Stili di apprendimento possibili."""
    VISUAL = "visual"          # Preferisce immagini e diagrammi
    AUDITORY = "auditory"      # Preferisce spiegazioni verbali
    KINESTHETIC = "kinesthetic"  # Preferisce esempi pratici
    THEORETICAL = "theoretical"  # Preferisce teoria e concetti
    BALANCED = "balanced"      # Non ha preferenze specifiche

class CommunicationStyle(str, Enum):
    """Stili di comunicazione possibili."""
    DIRECT = "direct"          # Comunicazione diretta e concisa
    ELABORATE = "elaborate"    # Comunicazione dettagliata
    FORMAL = "formal"          # Comunicazione formale
    INFORMAL = "informal"      # Comunicazione informale
    TECHNICAL = "technical"    # Comunicazione tecnica
    SUPPORTIVE = "supportive"  # Comunicazione incoraggiante
    INDIRECT = "indirect"      # Comunicazione indiretta
    BALANCED = "balanced"      # Comunicazione equilibrata
    DETAILED = "detailed"      # Comunicazione dettagliata
    SIMPLIFIED = "simplified"  # Comunicazione semplificata
    INTERACTIVE = "interactive" # Comunicazione interattiva

@dataclass
class LearningPreference:
    """Preferenze di apprendimento dell'utente"""
    style: LearningStyle = None
    communication_style: CommunicationStyle = None
    technical_level: int = 3
    confidence: float = 0.8
    last_updated: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)
    preferred_format: ResponseFormat = ResponseFormat.BALANCED
    
    def __init__(self, 
                 style: LearningStyle = None,
                 primary_style: LearningStyle = None,
                 communication_style: CommunicationStyle = None,
                 technical_level: int = 3,
                 confidence: float = 0.8,
                 last_updated: datetime = None,
                 metadata: Dict[str, Any] = None,
                 preferred_format: ResponseFormat = ResponseFormat.BALANCED):
        """
        Inizializza le preferenze di apprendimento.
        Accetta sia style che primary_style per retrocompatibilità.
        """
        self.style = primary_style if primary_style is not None else style
        self.communication_style = communication_style
        self.technical_level = technical_level
        self.confidence = confidence
        self.last_updated = last_updated if last_updated is not None else datetime.now()
        self.metadata = metadata if metadata is not None else {}
        self.preferred_format = preferred_format

    @property
    def primary_style(self) -> LearningStyle:
        """Ritorna lo stile primario di apprendimento."""
        return self.style

    @property
    def format(self) -> ResponseFormat:
        """Ritorna il formato di risposta preferito."""
        return self.preferred_format

@dataclass
class ProcessedResponse:
    """Risposta processata dal sistema"""
    content: str
    emotion: str = "neutral"
    topics: List[str] = field(default_factory=list)
    emotion_detected: bool = False
    project_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[Dict[str, Any]] = None
    knowledge_integrated: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    format: ResponseFormat = ResponseFormat.BALANCED
    confidence: float = 0.0
    technical_level: TechnicalLevel = TechnicalLevel.INTERMEDIATE
    includes_advanced_concepts: bool = False

class EmotionalState:
    """Stato emotivo dell'utente"""
    def __init__(self, primary_emotion: str, confidence: float = 0.0):
        """
        Inizializza lo stato emotivo
        
        Args:
            primary_emotion: Emozione primaria
            confidence: Livello di confidenza
        """
        self.primary_emotion = primary_emotion
        self.confidence = confidence
