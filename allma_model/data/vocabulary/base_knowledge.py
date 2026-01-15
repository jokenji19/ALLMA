"""
Conoscenza Base di ALLMA
=======================

Questo modulo definisce la conoscenza linguistica base di ALLMA,
equivalente a quella di un bambino che ha completato le elementari.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional
from enum import Enum

# STRUTTURE BASE DELLA FRASE
class SentenceType(Enum):
    STATEMENT = "affermazione"      # Mario mangia la mela
    QUESTION = "domanda"           # Cosa mangia Mario?
    REQUEST = "richiesta"          # Per favore, dammi la mela
    EXCLAMATION = "esclamazione"   # Che bella mela!

class SentencePart(Enum):
    SUBJECT = "soggetto"          # Chi fa l'azione
    VERB = "verbo"                # L'azione
    OBJECT = "oggetto"            # Su cosa si fa l'azione
    INDIRECT_OBJECT = "complemento"  # A chi/cosa è diretta l'azione
    MODIFIER = "modificatore"      # Come/quando/dove si fa l'azione

# REGOLE BASE DI COSTRUZIONE FRASE
BASIC_SENTENCE_PATTERNS = {
    "affermazione": {
        "pattern": "{soggetto} {verbo} {oggetto}",
        "esempio": "Mario mangia la mela",
        "variazioni": [
            "{soggetto} {verbo}",                    # Mario corre
            "{soggetto} {verbo} {complemento}",      # Mario va a casa
            "{soggetto} {verbo} {oggetto} {complemento}"  # Mario mangia la mela in cucina
        ]
    },
    "domanda": {
        "pattern": "{parola_domanda} {verbo} {soggetto}?",
        "esempio": "Cosa mangia Mario?",
        "variazioni": [
            "{verbo} {soggetto}?",                   # Mangia Mario?
            "Perché {soggetto} {verbo}?",           # Perché Mario mangia?
            "Dove {verbo} {soggetto}?"              # Dove va Mario?
        ]
    },
    "richiesta": {
        "pattern": "Per favore, {verbo} {oggetto}",
        "esempio": "Per favore, passa il sale",
        "variazioni": [
            "Potresti {verbo} {oggetto}?",          # Potresti passare il sale?
            "Mi {verbo} {oggetto}?",                # Mi passi il sale?
            "Vorrei {oggetto}, grazie"              # Vorrei il sale, grazie
        ]
    }
}

# REGOLE GRAMMATICALI BASE
GRAMMAR_RULES = {
    "concordanza": {
        "soggetto_verbo": {
            "regola": "Il verbo concorda con il soggetto in numero e persona",
            "esempi": {
                "io mangio": "prima persona singolare",
                "tu mangi": "seconda persona singolare",
                "egli/ella mangia": "terza persona singolare",
                "noi mangiamo": "prima persona plurale",
                "voi mangiate": "seconda persona plurale",
                "essi/esse mangiano": "terza persona plurale"
            }
        },
        "articolo_nome": {
            "regola": "L'articolo concorda con il nome in genere e numero",
            "esempi": {
                "il gatto": "maschile singolare",
                "la gatta": "femminile singolare",
                "i gatti": "maschile plurale",
                "le gatte": "femminile plurale"
            }
        }
    }
}

# TEMPI VERBALI BASE
BASIC_TENSES = {
    "presente": {
        "uso": "azioni che accadono ora o abitualmente",
        "esempi": ["io mangio", "tu corri", "lei studia"]
    },
    "passato_prossimo": {
        "uso": "azioni concluse nel passato",
        "esempi": ["ho mangiato", "sei corso", "ha studiato"]
    },
    "futuro_semplice": {
        "uso": "azioni che accadranno",
        "esempi": ["mangerò", "correrai", "studierà"]
    },
    "imperfetto": {
        "uso": "azioni abituali nel passato o azioni in corso nel passato",
        "esempi": ["mangiavo", "correvi", "studiava"]
    }
}

# STRATEGIE DI RIFORMULAZIONE
REFORMULATION_STRATEGIES = {
    "semplificazione": {
        "strategia": "Usa parole più semplici",
        "esempio": {
            "complesso": "Questa teoria è incomprensibile",
            "semplice": "Questa idea è difficile da capire"
        }
    },
    "spezzare_frasi": {
        "strategia": "Dividi frasi lunghe in più frasi corte",
        "esempio": {
            "complesso": "Ho visto Mario che correva nel parco mentre mangiava un gelato",
            "semplice": "Ho visto Mario. Correva nel parco. Mangiava un gelato."
        }
    },
    "richiesta_chiarimenti": {
        "domande_base": [
            "Cosa significa {parola}?",
            "Puoi spiegare meglio?",
            "Non ho capito bene, vuoi dire che...?",
            "Mi fai un esempio?"
        ]
    }
}

# PAROLE DI COLLEGAMENTO BASE
BASIC_CONNECTORS = {
    "tempo": ["quando", "mentre", "prima", "dopo", "poi"],
    "causa": ["perché", "quindi", "così", "infatti"],
    "opposizione": ["ma", "però", "tuttavia", "invece"],
    "aggiunta": ["e", "anche", "inoltre", "pure"]
}
