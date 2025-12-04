"""
ALLMA Vocabulary System - Sistema di Vocabolario Incrementale
==========================================================

Questo modulo implementa un sistema di apprendimento incrementale del vocabolario
che permette ad ALLMA di:
1. Partire da parole radice fondamentali
2. Apprendere nuove parole attraverso il dialogo
3. Costruire relazioni semantiche tra le parole
4. Espandere il proprio vocabolario in modo naturale

Struttura:
- root_words/: contiene le parole radice fondamentali
- patterns/: contiene i pattern di apprendimento e le regole di espansione
- learned_words/: contiene le parole apprese durante le interazioni
"""

from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Set, Optional, Union

# Categorie grammaticali
class WordCategory(Enum):
    # Nomi
    CONCRETE_NOUN = "nome_concreto"     # oggetti fisici
    ABSTRACT_NOUN = "nome_astratto"     # concetti
    PERSON_NOUN = "nome_persona"        # persone
    PLACE_NOUN = "nome_luogo"          # luoghi
    
    # Verbi
    ACTION_VERB = "verbo_azione"       # azioni fisiche
    STATE_VERB = "verbo_stato"         # stati
    MENTAL_VERB = "verbo_mentale"      # processi mentali
    
    # Aggettivi
    QUALITY_ADJ = "aggettivo_qualità"  # qualità
    STATE_ADJ = "aggettivo_stato"      # stati
    RELATION_ADJ = "aggettivo_relazione" # relazioni
    
    # Avverbi
    MANNER_ADV = "avverbio_modo"       # modo
    TIME_ADV = "avverbio_tempo"        # tempo
    PLACE_ADV = "avverbio_luogo"       # luogo

@dataclass
class WordProperties:
    category: WordCategory
    gender: Optional[str] = None
    number: Optional[str] = None
    transitivity: Optional[bool] = None
    
@dataclass
class SemanticProperties:
    hypernyms: Set[str]    # categorie superiori
    hyponyms: Set[str]    # sottocategorie
    meronyms: Set[str]    # parti costituenti
    holonyms: Set[str]    # insiemi di cui fa parte

@dataclass
class LearningProperties:
    patterns: List[str]           # pattern per riconoscere nuove istanze
    expansion_rules: List[str]    # regole per espandere il significato
    learned_forms: Set[str]       # forme apprese durante l'uso
