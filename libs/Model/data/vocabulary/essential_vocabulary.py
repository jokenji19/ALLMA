"""
Vocabolario Essenziale di ALLMA
==============================

Questo modulo contiene il vocabolario base che ALLMA deve conoscere,
equivalente a quello di un bambino che ha completato le elementari.
"""

from dataclasses import dataclass
from typing import Dict, List, Set, Optional
from enum import Enum

# VERBI ESSENZIALI
ESSENTIAL_VERBS = {
    # VERBI DI STATO
    "essere": {
        "significato": "esistere, trovarsi in una condizione",
        "uso_base": ["io sono", "tu sei", "lui/lei è", "noi siamo", "voi siete", "loro sono"],
        "esempi": ["Io sono alto", "La casa è grande", "Siamo felici"],
        "costruzioni": ["essere + aggettivo", "essere + luogo", "essere + nome"]
    },
    "avere": {
        "significato": "possedere, provare una sensazione",
        "uso_base": ["io ho", "tu hai", "lui/lei ha", "noi abbiamo", "voi avete", "loro hanno"],
        "esempi": ["Ho fame", "Hai una casa", "Abbiamo tempo"],
        "costruzioni": ["avere + nome", "avere + sensazione", "avere da + infinito"]
    },
    
    # VERBI DI AZIONE BASE
    "fare": {
        "significato": "compiere un'azione, creare",
        "uso_base": ["io faccio", "tu fai", "lui/lei fa", "noi facciamo", "voi fate", "loro fanno"],
        "esempi": ["Faccio i compiti", "Fa caldo", "Fanno una festa"],
        "costruzioni": ["fare + nome", "far + infinito"]
    },
    "andare": {
        "significato": "spostarsi, muoversi verso un luogo",
        "uso_base": ["io vado", "tu vai", "lui/lei va", "noi andiamo", "voi andate", "loro vanno"],
        "esempi": ["Vado a scuola", "Andiamo al parco", "Vanno a casa"],
        "costruzioni": ["andare a + luogo", "andare in + luogo", "andare da + persona"]
    },
    
    # VERBI DI COMUNICAZIONE
    "dire": {
        "significato": "comunicare, esprimere",
        "uso_base": ["io dico", "tu dici", "lui/lei dice", "noi diciamo", "voi dite", "loro dicono"],
        "esempi": ["Dico la verità", "Dice sempre di sì", "Dicono che pioverà"],
        "costruzioni": ["dire + frase", "dire di + infinito", "dire che + frase"]
    }
}

# NOMI ESSENZIALI
ESSENTIAL_NOUNS = {
    # PERSONE
    "persona": {
        "categorie": ["famiglia", "amici", "professioni"],
        "esempi_base": {
            "famiglia": ["mamma", "papà", "fratello", "sorella", "nonno", "nonna"],
            "amici": ["amico", "amica", "compagno", "compagna"],
            "professioni": ["maestro", "dottore", "negoziante"]
        }
    },
    
    # LUOGHI
    "luogo": {
        "categorie": ["casa", "scuola", "città"],
        "esempi_base": {
            "casa": ["camera", "cucina", "bagno", "sala"],
            "scuola": ["classe", "cortile", "palestra"],
            "città": ["strada", "parco", "negozio", "ospedale"]
        }
    },
    
    # OGGETTI
    "oggetto": {
        "categorie": ["cibo", "vestiti", "strumenti"],
        "esempi_base": {
            "cibo": ["pane", "pasta", "frutta", "acqua"],
            "vestiti": ["maglia", "pantaloni", "scarpe"],
            "strumenti": ["penna", "libro", "telefono"]
        }
    }
}

# AGGETTIVI ESSENZIALI
ESSENTIAL_ADJECTIVES = {
    # QUALITÀ FISICHE
    "fisico": {
        "dimensione": ["grande", "piccolo", "alto", "basso", "lungo", "corto"],
        "forma": ["rotondo", "quadrato", "dritto", "curvo"],
        "colore": ["rosso", "blu", "giallo", "verde", "bianco", "nero"]
    },
    
    # QUALITÀ CARATTERIALI
    "carattere": {
        "positivi": ["buono", "gentile", "felice", "bravo", "simpatico"],
        "negativi": ["cattivo", "triste", "arrabbiato", "stanco"]
    },
    
    # QUALITÀ SENSORIALI
    "sensoriale": {
        "tatto": ["morbido", "duro", "liscio", "ruvido"],
        "gusto": ["dolce", "salato", "amaro"],
        "temperatura": ["caldo", "freddo", "tiepido"]
    }
}

# AVVERBI ESSENZIALI
ESSENTIAL_ADVERBS = {
    # TEMPO
    "tempo": {
        "quando": ["oggi", "ieri", "domani", "prima", "dopo", "sempre", "mai"],
        "frequenza": ["spesso", "qualche volta", "raramente"]
    },
    
    # MODO
    "modo": {
        "come": ["bene", "male", "velocemente", "lentamente", "insieme"],
        "intensità": ["molto", "poco", "troppo", "abbastanza"]
    },
    
    # LUOGO
    "luogo": {
        "dove": ["qui", "lì", "vicino", "lontano", "dentro", "fuori"],
        "direzione": ["avanti", "indietro", "su", "giù"]
    }
}

# PRONOMI ESSENZIALI
ESSENTIAL_PRONOUNS = {
    "personali": {
        "soggetto": ["io", "tu", "lui", "lei", "noi", "voi", "loro"],
        "complemento": ["me", "te", "lui", "lei", "noi", "voi", "loro"]
    },
    "possessivi": ["mio", "tuo", "suo", "nostro", "vostro", "loro"],
    "dimostrativi": ["questo", "quello", "ciò"],
    "interrogativi": ["chi", "che cosa", "quale", "quanto"]
}

# PREPOSIZIONI ESSENZIALI
ESSENTIAL_PREPOSITIONS = {
    "semplici": ["di", "a", "da", "in", "con", "su", "per", "tra", "fra"],
    "articolate": {
        "il": ["del", "al", "dal", "nel", "col", "sul"],
        "la": ["della", "alla", "dalla", "nella", "sulla"],
        "i": ["dei", "ai", "dai", "nei", "sui"],
        "le": ["delle", "alle", "dalle", "nelle", "sulle"]
    }
}

# NUMERI E QUANTITÀ
ESSENTIAL_NUMBERS = {
    "cardinali": {
        "unità": ["zero", "uno", "due", "tre", "quattro", "cinque", "sei", "sette", "otto", "nove"],
        "decine": ["dieci", "venti", "trenta", "quaranta", "cinquanta"],
        "primi_cento": "da uno a cento"
    },
    "ordinali": ["primo", "secondo", "terzo", "quarto", "quinto"],
    "quantità": ["tutto", "niente", "poco", "molto", "alcuni", "tanti"]
}
