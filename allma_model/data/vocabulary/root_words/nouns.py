"""
Parole Radice - Nomi
===================

Questo file definisce le parole radice fondamentali per i nomi,
da cui ALLMA può apprendere e categorizzare nuove parole.
"""

from .. import WordCategory, WordProperties, SemanticProperties, LearningProperties

ROOT_NOUNS = {
    # OGGETTI FISICI BASE
    "oggetto": {
        "properties": WordProperties(
            category=WordCategory.CONCRETE_NOUN,
            gender="maschile",
            number="singolare"
        ),
        "semantic": SemanticProperties(
            hypernyms=set(),  # è una categoria base
            hyponyms={"strumento", "contenitore", "dispositivo"},
            meronyms={"parte", "materiale"},
            holonyms=set()
        ),
        "learning": LearningProperties(
            patterns=[
                "è un oggetto che",
                "è un tipo di oggetto",
                "serve per",
                "è fatto di"
            ],
            expansion_rules=[
                "eredita_proprietà_base",
                "aggiungi_uso_specifico",
                "aggiungi_materiale"
            ],
            learned_forms=set()
        )
    },

    # ESSERI VIVENTI
    "essere_vivente": {
        "properties": WordProperties(
            category=WordCategory.CONCRETE_NOUN,
            gender="maschile",
            number="singolare"
        ),
        "semantic": SemanticProperties(
            hypernyms=set(),
            hyponyms={"animale", "pianta", "persona"},
            meronyms={"corpo", "organo"},
            holonyms={"natura", "ecosistema"}
        ),
        "learning": LearningProperties(
            patterns=[
                "è un essere vivente che",
                "è un tipo di essere",
                "vive in",
                "si nutre di"
            ],
            expansion_rules=[
                "eredita_caratteristiche_vita",
                "aggiungi_habitat",
                "aggiungi_comportamento"
            ],
            learned_forms=set()
        )
    },

    # LUOGHI
    "luogo": {
        "properties": WordProperties(
            category=WordCategory.PLACE_NOUN,
            gender="maschile",
            number="singolare"
        ),
        "semantic": SemanticProperties(
            hypernyms=set(),
            hyponyms={"spazio", "ambiente", "zona"},
            meronyms={"area", "confine"},
            holonyms={"territorio", "regione"}
        ),
        "learning": LearningProperties(
            patterns=[
                "è un luogo dove",
                "è un tipo di posto",
                "si trova in",
                "contiene"
            ],
            expansion_rules=[
                "eredita_proprietà_spaziali",
                "aggiungi_funzione",
                "aggiungi_caratteristiche"
            ],
            learned_forms=set()
        )
    },

    # CONCETTI ASTRATTI
    "concetto": {
        "properties": WordProperties(
            category=WordCategory.ABSTRACT_NOUN,
            gender="maschile",
            number="singolare"
        ),
        "semantic": SemanticProperties(
            hypernyms=set(),
            hyponyms={"idea", "teoria", "principio"},
            meronyms={"aspetto", "elemento"},
            holonyms={"conoscenza", "pensiero"}
        ),
        "learning": LearningProperties(
            patterns=[
                "è un concetto che",
                "è un tipo di idea",
                "si riferisce a",
                "comprende"
            ],
            expansion_rules=[
                "eredita_astrattezza",
                "aggiungi_campo_applicazione",
                "aggiungi_relazioni"
            ],
            learned_forms=set()
        )
    }
}
