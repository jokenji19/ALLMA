"""Response format enum"""

from enum import Enum, auto

class ResponseFormat(Enum):
    """Formati di risposta disponibili"""
    
    # Risposta bilanciata tra dettaglio e concisione
    BALANCED = auto()
    
    # Risposta dettagliata e approfondita
    DETAILED = auto()
    
    # Risposta concisa e diretta
    CONCISE = auto()
    
    # Risposta con focus su esempi pratici
    PRACTICAL = auto()
    
    # Risposta con focus su concetti teorici
    THEORETICAL = auto()
    
    # Risposta con focus su analogie e metafore
    ANALOGICAL = auto()
    
    # Risposta che inizia con il codice
    CODE_FIRST = auto()
    
    # Risposta che inizia con la teoria
    THEORY_FIRST = auto()
