"""
Strutture cognitive fondamentali per ALLMA.
Questo modulo implementa le strutture cognitive di base che simulano
le capacità innate del cervello umano per l'apprendimento e la comprensione.
"""

from enum import Enum
from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
import numpy as np
from collections import defaultdict
import re

class ConceptType(Enum):
    """Tipi fondamentali di concetti"""
    SPATIAL = "spatial"         # Concetti spaziali (sopra, sotto, dentro, fuori)
    TEMPORAL = "temporal"       # Concetti temporali (prima, dopo, durante)
    CAUSAL = "causal"          # Relazioni causali (perché, quindi, se-allora)
    QUANTITATIVE = "quantity"   # Concetti quantitativi (più, meno, uguale)
    EMOTIONAL = "emotional"     # Concetti emotivi (felice, triste, arrabbiato)
    RELATIONAL = "relational"   # Relazioni tra concetti (è-un, ha-un, parte-di)
    ABSTRACT = "abstract"       # Concetti astratti (libertà, giustizia, bellezza)

@dataclass
class Concept:
    """Rappresenta un concetto base con il suo significato e relazioni"""
    name: str
    type: ConceptType
    attributes: Dict[str, float] = field(default_factory=dict)
    relations: Dict[str, List[str]] = field(default_factory=dict)
    examples: List[str] = field(default_factory=list)
    vector: Optional[np.ndarray] = None
    
    def __hash__(self):
        return hash(self.name)

class SemanticNetwork:
    """Rete semantica che rappresenta relazioni tra concetti"""
    def __init__(self):
        self.concepts: Dict[str, Concept] = {}
        self.relations: Dict[str, Dict[str, float]] = defaultdict(dict)
        
    def add_concept(self, concept: Concept):
        """Aggiunge un nuovo concetto alla rete"""
        self.concepts[concept.name] = concept
        
    def add_relation(self, concept1: str, concept2: str, relation_type: str, strength: float = 1.0):
        """Aggiunge una relazione tra due concetti"""
        self.relations[concept1][concept2] = strength
        self.concepts[concept1].relations.setdefault(relation_type, []).append(concept2)
        
    def get_related_concepts(self, concept_name: str, min_strength: float = 0.5) -> List[Tuple[str, float]]:
        """Trova concetti correlati con una forza minima di relazione"""
        if concept_name not in self.relations:
            return []
        return [(c, s) for c, s in self.relations[concept_name].items() if s >= min_strength]

class CognitiveStructures:
    """Implementa le strutture cognitive fondamentali"""
    def __init__(self):
        self.semantic_network = SemanticNetwork()
        self._initialize_basic_concepts()
        
    def _initialize_basic_concepts(self):
        """Inizializza i concetti cognitivi fondamentali"""
        # Concetti Spaziali
        spatial_concepts = {
            "sopra": ["alto", "superiore", "al di sopra"],
            "sotto": ["basso", "inferiore", "al di sotto"],
            "dentro": ["interno", "contenuto", "all'interno"],
            "fuori": ["esterno", "all'esterno", "fuori da"]
        }
        
        # Concetti Temporali
        temporal_concepts = {
            "prima": ["precedente", "anteriore", "in anticipo"],
            "dopo": ["successivo", "posteriore", "in seguito"],
            "durante": ["mentre", "nel corso di", "nel momento in cui"]
        }
        
        # Concetti Causali
        causal_concepts = {
            "perché": ["poiché", "dato che", "in quanto"],
            "quindi": ["perciò", "dunque", "di conseguenza"],
            "se": ["qualora", "nel caso in cui", "nell'ipotesi che"]
        }
        
        # Aggiungi concetti alla rete semantica
        for name, examples in spatial_concepts.items():
            concept = Concept(name=name, type=ConceptType.SPATIAL, examples=examples)
            self.semantic_network.add_concept(concept)
            
        for name, examples in temporal_concepts.items():
            concept = Concept(name=name, type=ConceptType.TEMPORAL, examples=examples)
            self.semantic_network.add_concept(concept)
            
        for name, examples in causal_concepts.items():
            concept = Concept(name=name, type=ConceptType.CAUSAL, examples=examples)
            self.semantic_network.add_concept(concept)
            
        # Aggiungi relazioni base
        self._add_basic_relations()
        
    def _add_basic_relations(self):
        """Aggiunge relazioni base tra concetti"""
        # Relazioni spaziali
        self.semantic_network.add_relation("sopra", "sotto", "opposto", 1.0)
        self.semantic_network.add_relation("dentro", "fuori", "opposto", 1.0)
        
        # Relazioni temporali
        self.semantic_network.add_relation("prima", "dopo", "opposto", 1.0)
        self.semantic_network.add_relation("durante", "prima", "sequenza", 0.7)
        self.semantic_network.add_relation("durante", "dopo", "sequenza", 0.7)
        
        # Relazioni causali
        self.semantic_network.add_relation("perché", "quindi", "conseguenza", 1.0)
        self.semantic_network.add_relation("se", "quindi", "implicazione", 0.9)
        
    def understand_concept(self, text: str) -> List[Tuple[Concept, float]]:
        """Analizza un testo e trova i concetti correlati con la loro rilevanza"""
        matches = []
        for concept in self.semantic_network.concepts.values():
            # Cerca corrispondenze dirette
            if concept.name in text.lower():
                matches.append((concept, 1.0))
                continue
                
            # Cerca negli esempi
            for example in concept.examples:
                if example in text.lower():
                    matches.append((concept, 0.8))
                    break
                    
        return matches
        
    def infer_relations(self, concepts: List[Concept]) -> List[Tuple[Concept, Concept, str, float]]:
        """Inferisce relazioni tra concetti dati"""
        relations = []
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i+1:]:
                # Controlla relazioni dirette
                if c2.name in self.semantic_network.relations.get(c1.name, {}):
                    strength = self.semantic_network.relations[c1.name][c2.name]
                    for relation_type, related in c1.relations.items():
                        if c2.name in related:
                            relations.append((c1, c2, relation_type, strength))
                            
                # Controlla relazioni causali speciali
                if c1.type == ConceptType.CAUSAL and c2.type == ConceptType.CAUSAL:
                    if (c1.name == "se" and c2.name == "quindi"):
                        relations.append((c1, c2, "implicazione", 0.9))
                    elif (c1.name == "perché" and c2.name == "quindi"):
                        relations.append((c1, c2, "conseguenza", 1.0))
                        
                # Controlla relazioni spazio-temporali
                if c1.type == ConceptType.TEMPORAL and c2.type == ConceptType.SPATIAL:
                    relations.append((c1, c2, "sequenza_spaziale", 0.7))
                elif c1.type == ConceptType.SPATIAL and c2.type == ConceptType.TEMPORAL:
                    relations.append((c2, c1, "sequenza_spaziale", 0.7))
                    
        return relations

@dataclass
class CausalRelation:
    """Rappresenta una relazione causale tra concetti"""
    antecedent: str
    consequent: str
    relation_type: str  # 'implicazione', 'conseguenza', 'correlazione'
    strength: float
    temporal_order: bool  # True se l'ordine temporale è rispettato
    bidirectional: bool = False  # True se la relazione è bidirezionale

@dataclass
class CausalPattern:
    """Rappresenta un pattern causale nel linguaggio"""
    pattern: str
    relation_type: str
    strength: float
    requires_temporal: bool = True
    examples: List[str] = field(default_factory=list)

class CausalStructure:
    """Struttura cognitiva innata per la comprensione della causalità"""
    def __init__(self):
        self.causal_patterns = [
            CausalPattern(
                pattern=r"se\s+([^,]+),?\s+(?:quindi|allora)\s+([^\.]+)",
                relation_type="implicazione",
                strength=0.9,
                examples=["se piove, quindi prendo l'ombrello"]
            ),
            CausalPattern(
                pattern=r"perché\s+([^,]+),?\s+(?:quindi|allora)\s+([^\.]+)",
                relation_type="conseguenza",
                strength=1.0,
                examples=["perché piove, quindi resto a casa"]
            ),
            CausalPattern(
                pattern=r"quando\s+([^,]+),?\s+(?:succede|accade)\s+([^\.]+)",
                relation_type="temporale_causale",
                strength=0.7,
                examples=["quando piove, succede che la strada si bagna"]
            )
        ]
        
        self.causal_markers = {
            "condizione": ["se", "quando", "nel caso", "qualora"],
            "conseguenza": ["quindi", "allora", "di conseguenza", "perciò"],
            "causa": ["perché", "poiché", "in quanto", "dato che"],
            "effetto": ["risulta", "porta a", "produce", "causa"]
        }
        
    def find_causal_relations(self, text: str) -> List[CausalRelation]:
        """Trova tutte le relazioni causali nel testo"""
        relations = []
        
        # Cerca pattern causali
        for pattern in self.causal_patterns:
            matches = re.finditer(pattern.pattern, text.lower())
            for match in matches:
                antecedent = match.group(1).strip()
                consequent = match.group(2).strip()
                relations.append(CausalRelation(
                    antecedent=antecedent,
                    consequent=consequent,
                    relation_type=pattern.relation_type,
                    strength=pattern.strength,
                    temporal_order=True
                ))
                
        # Cerca marker causali
        for marker_type, markers in self.causal_markers.items():
            for marker in markers:
                if marker in text.lower():
                    # Trova la frase che contiene il marker
                    sentences = re.split(r'[.!?]', text.lower())
                    for sentence in sentences:
                        if marker in sentence:
                            # Analizza la struttura causale della frase
                            self._analyze_causal_sentence(sentence, marker, marker_type, relations)
                            
        return relations
        
    def _analyze_causal_sentence(self, sentence: str, marker: str, marker_type: str, relations: List[CausalRelation]):
        """Analizza una frase per trovare relazioni causali basate su marker"""
        if marker_type in ["condizione", "causa"]:
            # Il marker introduce l'antecedente
            parts = sentence.split(marker)
            if len(parts) == 2:
                antecedent = parts[1].strip()
                # Cerca un marker di conseguenza
                for cons_marker in self.causal_markers["conseguenza"]:
                    if cons_marker in antecedent:
                        cons_parts = antecedent.split(cons_marker)
                        if len(cons_parts) == 2:
                            relations.append(CausalRelation(
                                antecedent=cons_parts[0].strip(),
                                consequent=cons_parts[1].strip(),
                                relation_type="implicazione" if marker_type == "condizione" else "conseguenza",
                                strength=0.9 if marker_type == "condizione" else 1.0,
                                temporal_order=True
                            ))
                            
class CognitiveProcessor:
    """Processore cognitivo che integra tutte le strutture cognitive"""
    def __init__(self):
        self.structures = CognitiveStructures()
        
    def process_input(self, text: str) -> Dict:
        """Processa un input testuale usando le strutture cognitive"""
        # Trova concetti rilevanti
        concepts = self.structures.understand_concept(text)
        
        # Trova relazioni tra i concetti
        concept_objects = [c for c, _ in concepts]
        relations = self.structures.infer_relations(concept_objects)
        
        return {
            "concepts": [(c.name, c.type.value, score) for c, score in concepts],
            "relations": [(c1.name, c2.name, rel_type, strength) 
                         for c1, c2, rel_type, strength in relations]
        }

class EnhancedCognitiveProcessor(CognitiveProcessor):
    """Versione migliorata del processore cognitivo con comprensione causale"""
    def __init__(self):
        super().__init__()
        self.causal_structure = CausalStructure()
        
    def process_input(self, text: str) -> Dict[str, Any]:
        """Processa un input testuale usando tutte le strutture cognitive"""
        # Trova concetti e relazioni causali
        concepts = []
        for marker in self.causal_structure.causal_markers["causa"]:
            if marker in text.lower():
                concepts.append((marker, "causal", 1.0))
                
        for marker in self.causal_structure.causal_markers["condizione"]:
            if marker in text.lower():
                concepts.append((marker, "causal", 1.0))
                
        # Calcola il livello di comprensione basato sul numero di concetti trovati
        understanding_level = min(1.0, len(concepts) * 0.2)  # 0.2 per concetto, max 1.0
                
        return {
            "concepts": concepts,
            "relations": [],
            "understanding_level": understanding_level
        }
