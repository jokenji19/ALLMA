from typing import Dict, List, Set, Optional, Any
import time
from dataclasses import dataclass
from enum import Enum

class ConceptType(Enum):
    """Tipo di concetto nell'enciclopedia"""
    GENERAL = "general"           # Concetto generale
    DEFINITION = "definition"     # Definizione precisa
    PROCESS = "process"          # Processo o procedura
    THEORY = "theory"           # Teoria o framework
    EXAMPLE = "example"         # Esempio pratico
    TOOL = "tool"              # Strumento o tecnologia

@dataclass
class SemanticRelation:
    """Relazione semantica tra concetti"""
    source: str
    target: str
    relation_type: str
    strength: float  # 0-1, forza della relazione
    context: List[str]  # Domini in cui la relazione è valida

@dataclass
class ConceptNode:
    """Nodo dell'enciclopedia che rappresenta un concetto"""
    name: str
    type: ConceptType
    definition: str
    short_description: str
    long_description: str
    examples: List[str]
    synonyms: Set[str]
    categories: List[str]
    related_terms: Set[str]
    prerequisites: Set[str]
    applications: List[str]
    verification_level: int  # 1-5, quanto è verificata l'informazione
    last_updated: float
    source: str

class Encyclopedia:
    """
    Enciclopedia interna di ALLMA che mantiene una base di conoscenza
    strutturata e verificata
    """
    
    def __init__(self):
        """Inizializza l'enciclopedia"""
        self.concepts: Dict[str, ConceptNode] = {}
        self.relations: List[SemanticRelation] = []
        self.categories: Dict[str, Set[str]] = {}
        self.synonyms: Dict[str, Set[str]] = {}
        
        # Inizializza la conoscenza di base
        self._initialize_base_knowledge()
        
    def _initialize_base_knowledge(self):
        """Inizializza la conoscenza di base dell'enciclopedia"""
        # Esempio di struttura per "Rete Neurale"
        self.add_concept(
            name="rete_neurale",
            type=ConceptType.DEFINITION,
            definition="Modello computazionale ispirato al funzionamento dei neuroni biologici",
            short_description="Sistema di elaborazione che simula il cervello",
            long_description="""
            Una rete neurale artificiale è un modello computazionale ispirato alla struttura e al funzionamento 
            del cervello biologico. È composta da unità di elaborazione interconnesse (neuroni artificiali) 
            organizzate in strati. Ogni connessione ha un peso che viene modificato durante l'apprendimento.
            
            Le reti neurali sono particolarmente efficaci in:
            - Riconoscimento di pattern
            - Classificazione
            - Previsione di serie temporali
            - Approssimazione di funzioni
            """,
            examples=[
                "Riconoscimento di cifre scritte a mano",
                "Previsione del prezzo delle azioni",
                "Traduzione automatica"
            ],
            synonyms={"neural network", "rete neurale artificiale", "ANN"},
            categories=["machine learning", "intelligenza artificiale", "deep learning"],
            related_terms={"perceptron", "deep learning", "backpropagation"},
            prerequisites={"algebra lineare", "calcolo differenziale"},
            applications=[
                "Computer Vision",
                "Natural Language Processing",
                "Robotica"
            ],
            verification_level=5,
            source="academic_research"
        )
        
    def add_concept(self, name: str, type: ConceptType, definition: str,
                   short_description: str, long_description: str,
                   examples: List[str], synonyms: Set[str],
                   categories: List[str], related_terms: Set[str],
                   prerequisites: Set[str], applications: List[str],
                   verification_level: int, source: str):
        """Aggiunge un nuovo concetto all'enciclopedia"""
        concept = ConceptNode(
            name=name,
            type=type,
            definition=definition,
            short_description=short_description,
            long_description=long_description,
            examples=examples,
            synonyms=synonyms,
            categories=categories,
            related_terms=related_terms,
            prerequisites=prerequisites,
            applications=applications,
            verification_level=verification_level,
            last_updated=time.time(),
            source=source
        )
        
        self.concepts[name] = concept
        
        # Aggiorna gli indici
        for synonym in synonyms:
            if synonym not in self.synonyms:
                self.synonyms[synonym] = set()
            self.synonyms[synonym].add(name)
            
        for category in categories:
            if category not in self.categories:
                self.categories[category] = set()
            self.categories[category].add(name)
            
    def add_relation(self, source: str, target: str, relation_type: str,
                    strength: float, context: List[str]):
        """Aggiunge una relazione semantica tra concetti"""
        relation = SemanticRelation(
            source=source,
            target=target,
            relation_type=relation_type,
            strength=strength,
            context=context
        )
        self.relations.append(relation)
        
    def get_concept(self, term: str) -> Optional[ConceptNode]:
        """
        Recupera un concetto dall'enciclopedia
        
        Args:
            term: Il termine da cercare (può essere il nome o un sinonimo)
            
        Returns:
            Optional[ConceptNode]: Il concetto trovato o None
        """
        # Cerca il termine diretto
        if term in self.concepts:
            return self.concepts[term]
            
        # Cerca nei sinonimi
        for synonym, concepts in self.synonyms.items():
            if term.lower() in synonym.lower():
                if concepts:  # Prendi il primo concetto associato
                    return self.concepts[list(concepts)[0]]
                    
        return None
        
    def get_related_concepts(self, concept_name: str) -> List[ConceptNode]:
        """
        Trova concetti correlati a un dato concetto
        
        Args:
            concept_name: Nome del concetto
            
        Returns:
            List[ConceptNode]: Lista di concetti correlati
        """
        related = []
        
        # Cerca nelle relazioni
        for relation in self.relations:
            if relation.source == concept_name:
                if relation.target in self.concepts:
                    related.append(self.concepts[relation.target])
            elif relation.target == concept_name:
                if relation.source in self.concepts:
                    related.append(self.concepts[relation.source])
                    
        return related
        
    def search_concepts(self, query: str) -> List[ConceptNode]:
        """
        Cerca concetti che corrispondono alla query
        
        Args:
            query: Query di ricerca
            
        Returns:
            List[ConceptNode]: Lista di concetti trovati
        """
        results = []
        query_lower = query.lower()
        
        # Cerca nei nomi dei concetti
        for name, concept in self.concepts.items():
            if query_lower in name.lower():
                results.append(concept)
                continue
                
            # Cerca nella definizione
            if query_lower in concept.definition.lower():
                results.append(concept)
                continue
                
            # Cerca nei sinonimi
            if any(query_lower in syn.lower() for syn in concept.synonyms):
                results.append(concept)
                continue
                
            # Cerca nelle categorie
            if any(query_lower in cat.lower() for cat in concept.categories):
                results.append(concept)
                
        return results
