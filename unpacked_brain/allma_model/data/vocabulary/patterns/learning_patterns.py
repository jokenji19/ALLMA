"""
Pattern di Apprendimento
=======================

Questo file definisce i pattern che ALLMA usa per riconoscere e apprendere
nuove parole durante le conversazioni.
"""

# Pattern universali per il riconoscimento di nuove parole
UNIVERSAL_PATTERNS = {
    "is_a": [
        "è un {category}",
        "è un tipo di {category}",
        "è una specie di {category}",
        "è simile a {category}",
        "è come {category} ma",
    ],
    
    "has_property": [
        "ha la caratteristica di {property}",
        "possiede {property}",
        "è caratterizzato da {property}",
        "ha {property}",
    ],
    
    "can_do": [
        "può {action}",
        "è capace di {action}",
        "serve per {action}",
        "si usa per {action}",
    ],
    
    "is_part_of": [
        "fa parte di {whole}",
        "è una parte di {whole}",
        "appartiene a {whole}",
        "è contenuto in {whole}",
    ],
    
    "has_parts": [
        "è composto da {parts}",
        "contiene {parts}",
        "è fatto di {parts}",
        "include {parts}",
    ]
}

# Pattern specifici per categoria grammaticale
CATEGORY_PATTERNS = {
    "CONCRETE_NOUN": {
        "physical_properties": [
            "è fatto di {material}",
            "ha forma {shape}",
            "è di colore {color}",
            "misura {size}",
        ],
        "location": [
            "si trova in {place}",
            "vive in {habitat}",
            "cresce in {environment}",
        ]
    },
    
    "ACTION_VERB": {
        "manner": [
            "si fa {manner}",
            "avviene {manner}",
            "si svolge {manner}",
        ],
        "purpose": [
            "serve per {purpose}",
            "ha lo scopo di {purpose}",
            "si usa per {purpose}",
        ]
    },
    
    "QUALITY_ADJ": {
        "intensity": [
            "è più {quality} di",
            "è molto {quality}",
            "è poco {quality}",
        ],
        "comparison": [
            "è come {reference}",
            "assomiglia a {reference}",
            "ricorda {reference}",
        ]
    }
}

# Regole per l'espansione del significato
EXPANSION_RULES = {
    "inheritance": {
        "rule": "eredita tutte le proprietà base della categoria",
        "example": "se X è un animale, X può muoversi"
    },
    "specialization": {
        "rule": "aggiunge proprietà specifiche alla categoria",
        "example": "il gatto è un animale che miagola"
    },
    "analogy": {
        "rule": "trasferisce proprietà da concetti simili",
        "example": "se X è come Y, X potrebbe avere proprietà di Y"
    },
    "composition": {
        "rule": "combina proprietà di più concetti",
        "example": "una casa galleggiante ha proprietà di casa e barca"
    }
}
