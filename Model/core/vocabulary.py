from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from enum import Enum

class WordType(Enum):
    """Tipo di parola nel vocabolario"""
    NOUN = "sostantivo"
    VERB = "verbo"
    ADJECTIVE = "aggettivo"
    ADVERB = "avverbio"
    PREPOSITION = "preposizione"
    CONJUNCTION = "congiunzione"
    PRONOUN = "pronome"
    ARTICLE = "articolo"
    INTERJECTION = "interiezione"

class GrammaticalGender(Enum):
    """Genere grammaticale"""
    MASCULINE = "maschile"
    FEMININE = "femminile"
    NEUTRAL = "neutro"

class GrammaticalNumber(Enum):
    """Numero grammaticale"""
    SINGULAR = "singolare"
    PLURAL = "plurale"

@dataclass
class VerbConjugation:
    """Coniugazione di un verbo"""
    infinitive: str
    present_indicative: Dict[str, str]  # persona -> forma
    past_indicative: Dict[str, str]
    future_indicative: Dict[str, str]
    present_subjunctive: Dict[str, str]
    past_subjunctive: Dict[str, str]
    conditional: Dict[str, str]
    imperative: Dict[str, str]
    participle: Dict[str, str]  # presente/passato
    gerund: str

@dataclass
class WordDefinition:
    """Definizione di una parola"""
    word: str
    type: WordType
    etymology: str
    definitions: List[str]
    examples: List[str]
    synonyms: Set[str]
    antonyms: Set[str]
    register: str  # formale, informale, tecnico, etc.
    usage_notes: List[str]
    
    # Campi specifici per tipo di parola
    gender: Optional[GrammaticalGender] = None  # per sostantivi
    number: Optional[GrammaticalNumber] = None
    conjugation: Optional[VerbConjugation] = None  # per verbi
    comparative: Optional[str] = None  # per aggettivi
    superlative: Optional[str] = None  # per aggettivi

class ItalianVocabulary:
    """
    Vocabolario completo della lingua italiana
    """
    
    def __init__(self):
        """Inizializza il vocabolario"""
        self.words: Dict[str, WordDefinition] = {}
        self.word_forms: Dict[str, str] = {}  # forma flessa -> forma base
        self.idioms: Dict[str, List[str]] = {}  # parola -> espressioni idiomatiche
        self.proverbs: Dict[str, List[str]] = {}  # parola -> proverbi
        self.semantic_fields: Dict[str, List[str]] = {}  # campo -> parole
        self.derivatives: Dict[str, Dict[str, List[str]]] = {}  # parola -> derivati
        
        # Carica il vocabolario dal database
        self._load_vocabulary_data()
        
    def _load_vocabulary_data(self):
        """Carica i dati dal database"""
        from ..data.vocabulary_data import (
            ITALIAN_WORDS,
            IDIOMS,
            PROVERBS,
            SEMANTIC_FIELDS,
            WORD_DERIVATIVES
        )
        
        # Carica le parole
        for word, data in ITALIAN_WORDS.items():
            self.add_word(
                word=word,
                type=data["type"],
                etymology=data["etymology"],
                definitions=data["definitions"],
                examples=data["examples"],
                synonyms=data["synonyms"],
                antonyms=data["antonyms"],
                register=data["register"],
                usage_notes=data["usage_notes"],
                gender=data.get("gender"),
                number=data.get("number"),
                conjugation=data.get("conjugation"),
                comparative=data.get("comparative"),
                superlative=data.get("superlative")
            )
            
        # Carica espressioni idiomatiche
        self.idioms = IDIOMS
        
        # Carica proverbi
        self.proverbs = PROVERBS
        
        # Carica campi semantici
        self.semantic_fields = SEMANTIC_FIELDS
        
        # Carica derivati e forme flesse
        self._load_derivatives(WORD_DERIVATIVES)
        
    def _load_derivatives(self, derivatives: Dict[str, Dict[str, List[str]]]):
        """
        Carica i derivati e le forme flesse
        
        Args:
            derivatives: Dizionario con i derivati per ogni parola
        """
        self.derivatives = derivatives
        
        # Aggiungi le forme al dizionario delle forme flesse
        for word, forms in derivatives.items():
            for category, words in forms.items():
                for derived in words:
                    self.word_forms[derived] = word
                    
    def add_word(self, word: str, type: WordType, etymology: str,
                definitions: List[str], examples: List[str],
                synonyms: Set[str], antonyms: Set[str],
                register: str, usage_notes: List[str],
                gender: Optional[GrammaticalGender] = None,
                number: Optional[GrammaticalNumber] = None,
                conjugation: Optional[VerbConjugation] = None,
                comparative: Optional[str] = None,
                superlative: Optional[str] = None):
        """Aggiunge una nuova parola al vocabolario"""
        definition = WordDefinition(
            word=word,
            type=type,
            etymology=etymology,
            definitions=definitions,
            examples=examples,
            synonyms=synonyms,
            antonyms=antonyms,
            register=register,
            usage_notes=usage_notes,
            gender=gender,
            number=number,
            conjugation=conjugation,
            comparative=comparative,
            superlative=superlative
        )
        
        self.words[word] = definition
        
        # Aggiungi le forme flesse per i verbi
        if conjugation:
            for tense_dict in [conjugation.present_indicative,
                             conjugation.past_indicative,
                             conjugation.future_indicative,
                             conjugation.present_subjunctive,
                             conjugation.past_subjunctive,
                             conjugation.conditional,
                             conjugation.imperative]:
                for form in tense_dict.values():
                    self.word_forms[form] = word
                    
            # Aggiungi participi e gerundio
            for participle in conjugation.participle.values():
                self.word_forms[participle] = word
            self.word_forms[conjugation.gerund] = word
            
    def get_word(self, word: str) -> Optional[WordDefinition]:
        """
        Recupera la definizione di una parola
        
        Args:
            word: La parola da cercare
            
        Returns:
            Optional[WordDefinition]: La definizione della parola o None
        """
        # Cerca la forma base
        if word in self.words:
            return self.words[word]
            
        # Cerca nelle forme flesse
        if word in self.word_forms:
            base_form = self.word_forms[word]
            return self.words[base_form]
            
        return None
        
    def search_words(self, query: str) -> List[WordDefinition]:
        """
        Cerca parole che corrispondono alla query
        
        Args:
            query: Query di ricerca
            
        Returns:
            List[WordDefinition]: Lista di definizioni trovate
        """
        results = []
        query_lower = query.lower()
        
        for word, definition in self.words.items():
            # Cerca nel lemma
            if query_lower in word.lower():
                results.append(definition)
                continue
                
            # Cerca nelle definizioni
            if any(query_lower in d.lower() for d in definition.definitions):
                results.append(definition)
                continue
                
            # Cerca nei sinonimi
            if any(query_lower in s.lower() for s in definition.synonyms):
                results.append(definition)
                continue
                
            # Cerca negli esempi
            if any(query_lower in e.lower() for e in definition.examples):
                results.append(definition)
                
        return results

    def get_related_words(self, word: str) -> Dict[str, List[str]]:
        """
        Trova parole correlate a una data parola
        
        Args:
            word: La parola di partenza
            
        Returns:
            Dict[str, List[str]]: Dizionario con tipi di relazione e parole correlate
        """
        definition = self.get_word(word)
        if not definition:
            return {}
            
        related = {
            "sinonimi": list(definition.synonyms),
            "antonimi": list(definition.antonyms)
        }
        
        # Aggiungi altre relazioni in base al tipo di parola
        if definition.type == WordType.VERB:
            # Trova sostantivi e aggettivi derivati
            related["sostantivi_derivati"] = []
            related["aggettivi_derivati"] = []
            
        elif definition.type == WordType.NOUN:
            # Trova verbi e aggettivi correlati
            related["verbi_correlati"] = []
            related["aggettivi_correlati"] = []
            
        return related

    def get_idioms(self, word: str) -> List[str]:
        """Recupera le espressioni idiomatiche per una parola"""
        return self.idioms.get(word, [])
        
    def get_proverbs(self, word: str) -> List[str]:
        """Recupera i proverbi associati a una parola"""
        return self.proverbs.get(word, [])
        
    def get_semantic_field(self, field: str) -> List[str]:
        """Recupera le parole in un campo semantico"""
        return self.semantic_fields.get(field, [])
        
    def get_all_semantic_fields(self) -> List[str]:
        """Recupera tutti i campi semantici disponibili"""
        return list(self.semantic_fields.keys())

    def get_derivatives(self, word: str) -> Dict[str, List[str]]:
        """
        Ottiene tutti i derivati di una parola
        
        Args:
            word: La parola di cui cercare i derivati
            
        Returns:
            Dict[str, List[str]]: Dizionario con categorie e derivati
        """
        return self.derivatives.get(word, {})
        
    def get_word_family(self, word: str) -> Dict[str, Any]:
        """
        Ottiene tutta la famiglia di parole correlate
        
        Args:
            word: La parola di partenza
            
        Returns:
            Dict[str, Any]: Dizionario con tutte le parole correlate
        """
        family = {
            "base": word,
            "derivatives": self.get_derivatives(word),
            "idioms": self.get_idioms(word),
            "proverbs": self.get_proverbs(word),
            "synonyms": set(),
            "antonyms": set()
        }
        
        # Aggiungi sinonimi e antonimi se la parola esiste
        if word_def := self.get_word(word):
            family["synonyms"] = word_def.synonyms
            family["antonyms"] = word_def.antonyms
            
        return family
        
    def analyze_word(self, word: str) -> Dict[str, Any]:
        """
        Analisi completa di una parola
        
        Args:
            word: La parola da analizzare
            
        Returns:
            Dict[str, Any]: Dizionario con tutte le informazioni sulla parola
        """
        analysis = {
            "found": False,
            "base_form": word,
            "definition": None,
            "family": None,
            "semantic_fields": []
        }
        
        # Cerca la forma base
        base_word = self.word_forms.get(word, word)
        if word_def := self.get_word(base_word):
            analysis.update({
                "found": True,
                "base_form": base_word,
                "definition": word_def,
                "family": self.get_word_family(base_word)
            })
            
            # Trova i campi semantici
            for field, words in self.semantic_fields.items():
                if base_word in words:
                    analysis["semantic_fields"].append(field)
                    
        return analysis
