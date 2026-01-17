"""Sistema di risposta contestuale per ALLMA."""
from enum import Enum
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from allma_model.user_system.user_preferences import LearningPreference, LearningStyle
from allma_model.response_system.response_format import ResponseFormat
from allma_model.types import TechnicalLevel

@dataclass
class ProjectContext:
    """Contesto del progetto."""
    project_id: str
    name: str
    description: str
    topic: str
    settings: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ResponseContext:
    """Contesto per la generazione della risposta."""
    user_id: str
    current_topic: str
    technical_level: TechnicalLevel
    conversation_history: List[str] = field(default_factory=list)
    user_preferences: Optional[LearningPreference] = None

@dataclass
class ProcessedResponse:
    """Classe per rappresentare una risposta processata."""
    content: str
    emotion: str = "neutral"
    emotion_detected: bool = False
    topics: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    technical_level: TechnicalLevel = TechnicalLevel.INTERMEDIATE
    format: ResponseFormat = ResponseFormat.BALANCED
    includes_advanced_concepts: bool = False
    project_context: Optional[Dict[str, Any]] = None
    user_preferences: Optional[LearningPreference] = None
    knowledge_integrated: bool = False
    confidence: float = 0.0
    is_valid: bool = True
    includes_code: bool = False
    references_previous_context: bool = False

    @property
    def topic(self) -> str:
        """Returns the first topic if available, otherwise returns None"""
        return self.topics[0] if self.topics else None

class ContextualResponseGenerator:
    """Generatore di risposte contestuali."""
    
    def __init__(self):
        """Inizializza il generatore di risposte."""
        pass
    
    def generate_response(
        self,
        query: str,
        context: ResponseContext
    ) -> ProcessedResponse:
        """
        Genera una risposta basata sulla query e il contesto.
        
        Args:
            query: Query dell'utente
            context: Contesto della risposta
            
        Returns:
            ProcessedResponse con la risposta generata
        """
        if not query.strip():
            return ProcessedResponse(
                content="Error: input non valido. Per favore, fornisci una domanda valida.",
                technical_level=context.technical_level,
                format=ResponseFormat.BALANCED,
                is_valid=False,
                references_previous_context=False
            )
            
        # Determina il formato della risposta in base al contesto
        response_format = self._determine_response_format(query, context)
        
        # Verifica se la query fa riferimento al contesto precedente
        references_context = self._check_context_reference(query, context)
        
        # Genera la risposta in base al formato
        if response_format == ResponseFormat.CODE_FIRST:
            response_text = self._generate_code_first_response(query, context)
            includes_code = True
        elif response_format == ResponseFormat.THEORY_FIRST:
            response_text = self._generate_theory_first_response(query, context)
            includes_code = False
        else:
            response_text = self._generate_balanced_response(query, context)
            includes_code = "def" in response_text or "class" in response_text
            
        # Verifica se la risposta include concetti avanzati
        includes_advanced = self._check_advanced_concepts(response_text, context.technical_level)
        
        return ProcessedResponse(
            content=response_text,
            technical_level=context.technical_level,
            format=response_format,
            includes_advanced_concepts=includes_advanced,
            is_valid=True,
            includes_code=includes_code,
            references_previous_context=references_context
        )
        
    def _check_context_reference(self, query: str, context: ResponseContext) -> bool:
        """Verifica se la query fa riferimento al contesto precedente"""
        # Parole che indicano riferimento al contesto
        context_words = [
            "questo", "quello", "precedente", "sopra",
            "altro", "esempio", "ancora", "come"
        ]
        
        # Verifica se la query contiene parole di riferimento al contesto
        query_words = query.lower().split()
        if any(word in query_words for word in context_words):
            return True
            
        # Verifica se c'è una storia della conversazione
        if context.conversation_history:
            # Verifica se la query è correlata agli ultimi messaggi
            last_messages = context.conversation_history[-3:]
            for msg in last_messages:
                if any(word in msg.lower() for word in query_words):
                    return True
                    
        return False
        
    def _determine_response_format(
        self,
        query: str,
        context: ResponseContext
    ) -> ResponseFormat:
        """Determina il formato della risposta in base alla query e al contesto"""
        if any(word in query.lower() for word in ["esempio", "codice", "implementazione"]):
            return ResponseFormat.CODE_FIRST
        elif any(word in query.lower() for word in ["teoria", "concetto", "spiegazione"]):
            return ResponseFormat.THEORY_FIRST
        return ResponseFormat.BALANCED
        
    def _generate_code_first_response(
        self,
        query: str,
        context: ResponseContext
    ) -> str:
        """Genera una risposta che inizia con il codice"""
        if "parametr" in context.conversation_history[-1].lower():
            return """
def esempio_funzione(param1: str, param2: int = 0):
    '''
    Esempio di funzione con parametri
    
    Args:
        param1: Primo parametro (stringa)
        param2: Secondo parametro (intero, default=0)
    '''
    return f"{param1} ripetuto {param2} volte"
"""
        return "Ecco un esempio di codice per la tua richiesta..."
        
    def _generate_theory_first_response(
        self,
        query: str,
        context: ResponseContext
    ) -> str:
        """Genera una risposta che inizia con la teoria"""
        return "La teoria dietro questo concetto è..."
        
    def _generate_balanced_response(
        self,
        query: str,
        context: ResponseContext
    ) -> str:
        """Genera una risposta bilanciata tra teoria e pratica"""
        q_lower = query.lower()
        
        # Basic Conversation Fallbacks (Safe Mode)
        if any(w in q_lower for w in ["ciao", "salve", "buongiorno", "buonasera"]):
            return "Ciao! Sono ALLMA. La mia rete neurale è attualmente offline (Safe Mode), ma sono qui."
            
        if any(w in q_lower for w in ["come stai", "tutto bene"]):
            return "Funziono in modalità di emergenza. I miei sistemi logici sono attivi, ma la creatività è limitata senza il Brain."
            
        if any(w in q_lower for w in ["chi sei", "cosa sei"]):
            return "Sono ALLMA (Advanced Learning and Emotional Memory Architecture). Al momento opero in modalità ridotta."

        # Generic Fallback
        return (f"Ho ricevuto il tuo messaggio: '{query}'.\n"
                "Tuttavia, il mio modulo LLM (Cervello) non è raggiungibile.\n"
                "Non posso generare una risposta complessa ora.")
        
    def _check_advanced_concepts(
        self,
        response: str,
        level: TechnicalLevel
    ) -> bool:
        """Verifica se la risposta include concetti avanzati"""
        advanced_keywords = [
            "metaclass", "descriptor", "decorator",
            "generator", "coroutine", "async"
        ]
        return any(keyword in response.lower() for keyword in advanced_keywords)
