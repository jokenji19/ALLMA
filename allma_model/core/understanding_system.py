"""
Sistema di Comprensione Avanzato di ALLMA
=======================================

Questo modulo implementa il sistema di comprensione linguistica avanzato che permette
ad ALLMA di analizzare e comprendere il linguaggio naturale in modo profondo.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Set, Optional, Tuple
from enum import Enum
import re
from collections import defaultdict
import time

class IntentType(Enum):
    STATEMENT = "affermazione"
    QUESTION = "domanda"
    REQUEST = "richiesta"
    OPINION = "opinione"
    EMOTION = "emozione"
    GREETING = "saluto"
    FAREWELL = "congedo"
    AGREEMENT = "accordo"
    DISAGREEMENT = "disaccordo"
    CLARIFICATION = "chiarimento"

class EmotionalTone(Enum):
    NEUTRAL = "neutro"
    POSITIVE = "positivo"
    NEGATIVE = "negativo"
    ENTHUSIASTIC = "entusiasta"
    CONCERNED = "preoccupato"
    UNCERTAIN = "incerto"
    FORMAL = "formale"
    INFORMAL = "informale"

@dataclass
class SentenceComponent:
    """Rappresenta un componente della frase con il suo ruolo e proprietà."""
    text: str
    role: str
    type: str
    position: int = 0
    properties: Dict = field(default_factory=dict)
    importance: float = 1.0
    relations: List = field(default_factory=list)

@dataclass
class ContextualReference:
    type: str
    value: str
    confidence: float
    resolution: Optional[str]

@dataclass
class UnderstandingResult:
    """Risultato dell'analisi di comprensione."""
    original_text: str
    intent: IntentType
    emotional_tone: EmotionalTone
    components: List[SentenceComponent]
    context: Dict[str, ContextualReference]
    confidence: float
    ambiguities: List[str]
    requires_clarification: bool
    new_words: List[str] = field(default_factory=list)
    sentence_patterns: List[Dict] = field(default_factory=list)
    patterns: List = field(default_factory=list)
    topic: Optional[str] = None

class AdvancedUnderstandingSystem:
    def __init__(self):
        self.context_history = []
        self.topic_tracker = defaultdict(float)
        self.emotion_analyzer = EmotionAnalyzer()
        self.intent_classifier = IntentClassifier()
        self.syntax_analyzer = SyntaxAnalyzer()
        self.context_resolver = ContextResolver()
        self.ambiguity_detector = AmbiguityDetector()
        self.ambiguities = []

    def understand(self, text: str, previous_context: Optional[Dict] = None, base_knowledge: Optional[Dict] = None) -> UnderstandingResult:
        cleaned_text = self._preprocess_text(text)
        
        components = self.syntax_analyzer.analyze(cleaned_text)
        
        intent = self.intent_classifier.classify(cleaned_text, components)
        
        emotional_tone = self.emotion_analyzer.analyze(cleaned_text, components)
        
        context = self.context_resolver.resolve(
            components,
            previous_context,
            self.context_history
        )
        
        self.ambiguities = self.ambiguity_detector.detect(
            components,
            context,
            self.context_history
        ) or []
        
        confidence = self._evaluate_confidence(
            components,
            context,
            self.ambiguities
        )
        
        needs_clarification = self._needs_clarification(
            confidence,
            self.ambiguities,
            components
        )
        
        new_words = []
        known_words = set()
        
        # Gestisci il caso di base_knowledge con vocabulary
        if base_knowledge and hasattr(base_knowledge, 'vocabulary'):
            for word_type in base_knowledge.vocabulary.values():
                known_words.update(word_type.keys())
        # Gestisci il caso di base_knowledge come dizionario
        elif base_knowledge and isinstance(base_knowledge, dict):
            if 'concepts' in base_knowledge:
                known_words.update(base_knowledge['concepts'])
            if 'vocabulary' in base_knowledge:
                known_words.update(base_knowledge['vocabulary'])
        
        # Identifica nuove parole dai componenti
        for component in components:
            if component.text.lower() not in known_words and len(component.text) > 2:
                new_words.append(component.text)
        
        sentence_patterns = self._identify_patterns(components)
        
        self._update_history(components, context, intent)
        
        return UnderstandingResult(
            original_text=text,
            intent=intent,
            emotional_tone=emotional_tone,
            components=components,
            context=context,
            confidence=confidence,
            ambiguities=self.ambiguities,
            requires_clarification=needs_clarification,
            new_words=new_words,
            sentence_patterns=sentence_patterns,
            patterns=[],
            topic=None
        )

    def _preprocess_text(self, text: str) -> str:
        """Preprocessa il testo prima dell'analisi."""
        # Rimuovi spazi extra
        text = ' '.join(text.split())
        
        # Rimuovi punteggiatura non necessaria
        text = re.sub(r'[^\w\s]', '', text)
        
        return text  # Non convertire in minuscolo per preservare i nomi propri

    def _evaluate_confidence(self, components, context, ambiguities) -> float:
        confidence = 1.0
        
        confidence -= len(ambiguities) * 0.1
        
        if not any(c.role == "soggetto" for c in components):
            confidence -= 0.2
        if not any(c.role == "verbo" for c in components):
            confidence -= 0.3
            
        unresolved_refs = [ref for ref in context.values() if not ref.resolution]
        confidence -= len(unresolved_refs) * 0.15
        
        return max(0.0, min(1.0, confidence))

    def _needs_clarification(self, confidence, ambiguities, components) -> bool:
        if confidence < 0.7:
            return True
        if len(ambiguities) > 2:
            return True
        if not any(c.role == "verbo" for c in components):
            return True
        return False

    def _update_history(self, components, context, intent):
        self.context_history.append({
            'components': components,
            'context': context,
            'intent': intent,
            'timestamp': time.time()
        })
        
        if len(self.context_history) > 10:
            self.context_history.pop(0)
        
        for comp in components:
            if comp.role in ["soggetto", "oggetto"]:
                self.topic_tracker[comp.text] += 1.0
        
        for topic in self.topic_tracker:
            self.topic_tracker[topic] *= 0.9

    def _identify_patterns(self, components: List[SentenceComponent]) -> List[Dict]:
        patterns = []
        
        if not components:
            return patterns
            
        current_pattern = {
            'type': 'sequence',
            'components': [c.role for c in components],
            'text': ' '.join(c.text for c in components),
            'frequency': 1,
            'examples': [' '.join(c.text for c in components)]
        }
        patterns.append(current_pattern)
        
        return patterns

class EmotionAnalyzer:
    def analyze(self, text: str, components: List[SentenceComponent]) -> EmotionalTone:
        """Analizza il tono emotivo del testo."""
        # Parole chiave per ogni tono emotivo
        emotional_keywords = {
            EmotionalTone.POSITIVE: {
                'felice', 'contento', 'gioioso', 'allegro', 'sereno',
                'entusiasta', 'ottimista', 'soddisfatto', 'lieto'
            },
            EmotionalTone.NEGATIVE: {
                'triste', 'arrabbiato', 'deluso', 'frustrato', 'infelice',
                'scontento', 'irritato', 'annoiato', 'stanco', 'solo'
            },
            EmotionalTone.CONCERNED: {
                'preoccupato', 'ansioso', 'nervoso', 'teso', 'agitato',
                'inquieto', 'turbato', 'allarmato', 'spaventato'
            }
        }
        
        # Cerca negazioni
        has_negation = any(word in text.lower() for word in ['non', 'mai', 'niente', 'nessun', 'né'])
        
        # Conta le occorrenze di parole emotive
        scores = {tone: 0 for tone in emotional_keywords.keys()}
        
        for word in text.lower().split():
            for tone, keywords in emotional_keywords.items():
                if word in keywords:
                    scores[tone] += 1
        
        # Se c'è una negazione, inverti il significato
        if has_negation:
            if scores[EmotionalTone.POSITIVE] > 0:
                scores[EmotionalTone.NEGATIVE] += scores[EmotionalTone.POSITIVE]
                scores[EmotionalTone.POSITIVE] = 0
        
        # Trova il tono dominante
        max_score = max(scores.values())
        if max_score == 0:
            return EmotionalTone.NEUTRAL
        
        # In caso di parità, prioritizza NEGATIVE su CONCERNED e CONCERNED su POSITIVE
        if scores[EmotionalTone.NEGATIVE] == max_score:
            return EmotionalTone.NEGATIVE
        elif scores[EmotionalTone.CONCERNED] == max_score:
            return EmotionalTone.CONCERNED
        elif scores[EmotionalTone.POSITIVE] == max_score:
            return EmotionalTone.POSITIVE
        
        return EmotionalTone.NEUTRAL

class IntentClassifier:
    def classify(self, text: str, components: List[SentenceComponent]) -> IntentType:
        """Classifica l'intento basandosi su componenti e parole chiave."""
        
        # PHASE 20 FIX: Check for interrogative components, not just "?"
        has_interrogative = any(c.type == 'interrogativo' for c in components)
        has_question_mark = "?" in text
        
        # Se c'è un interrogativo o un punto interrogativo, è una domanda
        if has_interrogative or has_question_mark:
            return IntentType.QUESTION
        
        # Controlla per richieste esplicite
        elif any(word in text.lower() for word in ["per favore", "potresti", "puoi", "vorrei", "mi aiuti"]):
            return IntentType.REQUEST
        
        # Controlla per saluti
        elif any(word in text.lower() for word in ["ciao", "salve", "buongiorno", "buonasera", "hey"]):
            return IntentType.GREETING
        
        # Controlla per opinioni
        elif any(word in text.lower() for word in ["penso", "credo", "secondo me", "mi sembra", "direi"]):
            return IntentType.OPINION
        
        # Default: affermazione
        return IntentType.STATEMENT

class SyntaxAnalyzer:
    """Analizza la struttura sintattica delle frasi."""
    
    def analyze(self, text: str) -> List[SentenceComponent]:
        """Analizza la struttura sintattica di una frase."""
        # Tokenizza la frase
        words = text.split()
        components = []
        
        # ===== DIZIONARI ESPANSI (PHASE 20 FIX) =====
        
        # Articoli
        articles = {'il', 'lo', 'la', 'i', 'gli', 'le', 'un', 'uno', 'una'}
        
        # Preposizioni (espanse)
        prepositions = {'di', 'a', 'da', 'in', 'con', 'su', 'per', 'tra', 'fra', 'del', 'della', 'dei', 'degli', 'delle', 'al', 'alla', 'ai', 'agli', 'alle'}
        
        # Pronomi personali
        pronouns = {'io', 'tu', 'egli', 'ella', 'noi', 'voi', 'essi', 'esse', 'mi', 'ti', 'si', 'ci', 'vi', 'gli', 'le', 'ne', 'lo', 'la', 'li'}
        
        # NUOVO: Pronomi/Aggettivi interrogativi
        interrogatives = {
            'qual', 'quale', 'quali',  # Which
            'che', 'cosa',  # What
            'chi',  # Who
            'come',  # How
            'quando',  # When
            'dove',  # Where
            'perché', 'perchè',  # Why
            'quanto', 'quanta', 'quanti', 'quante'  # How much/many
        }
        
        # NUOVO: Aggettivi possessivi
        possessives = {
            'mio', 'mia', 'miei', 'mie',
            'tuo', 'tua', 'tuoi', 'tue',
            'suo', 'sua', 'suoi', 'sue',
            'nostro', 'nostra', 'nostri', 'nostre',
            'vostro', 'vostra', 'vostri', 'vostre',
            'loro'
        }

        # Verbi comuni (espanso)
        common_verbs = {
            'chiamo', 'chiami', 'chiama', 'chiamiamo', 'chiamate', 'chiamano',
            'sono', 'sei', 'è', 'siamo', 'siete',
            'ho', 'hai', 'ha', 'abbiamo', 'avete', 'hanno',
            'faccio', 'fai', 'fa', 'facciamo', 'fate', 'fanno',
            'vado', 'vai', 'va', 'andiamo', 'andate', 'vanno',
            'vengo', 'vieni', 'viene', 'veniamo', 'venite', 'vengono',
            'dico', 'dici', 'dice', 'diciamo', 'dite', 'dicono',
            'penso', 'pensi', 'pensa', 'pensiamo', 'pensate', 'pensano',
            'credo', 'credi', 'crede', 'crediamo', 'credete', 'credono',
            'voglio', 'vuoi', 'vuole', 'vogliamo', 'volete', 'vogliono',
            'mangia', 'mangio', 'mangi', 'mangiamo', 'mangiate', 'mangiano',
            'dorme', 'dormo', 'dormi', 'dormiamo', 'dormite', 'dormono',
            'sta', 'sto', 'stai', 'stiamo', 'state', 'stanno'
        }
        
        # Aggettivi comuni (espanso)
        common_adjectives = {
            'bello', 'bella', 'belli', 'belle',
            'brutto', 'brutta', 'brutti', 'brutte',
            'grande', 'grandi',
            'piccolo', 'piccola', 'piccoli', 'piccole',
            'alto', 'alta', 'alti', 'alte',
            'basso', 'bassa', 'bassi', 'basse',
            'buono', 'buona', 'buoni', 'buone',
            'cattivo', 'cattiva', 'cattivi', 'cattive',
            'nero', 'nera', 'neri', 'nere',
            'bianco', 'bianca', 'bianchi', 'bianche',
            'rosso', 'rossa', 'rossi', 'rosse',
            'verde', 'verdi',
            'blu',
            'giallo', 'gialla', 'gialli', 'gialle',
            'preferito', 'preferita', 'preferiti', 'preferite',
            'nuovo', 'nuova', 'nuovi', 'nuove',
            'vecchio', 'vecchia', 'vecchi', 'vecchie'
        }
        
        # ===== ANALISI PAROLE (CON PRIORIT CORRETTA) =====
        
        for i, word in enumerate(words):
            original_word = word
            word_lower = word.lower()
            
            # Rimuovi debug print per performance
            # print(f"DEBUG - Analisi parola: {word}")
            
            # PRIORITY ORDER: Più specifico prima!
            
            # 1. Pronomi/Aggettivi INTERROGATIVI (massima priorità)
            if word_lower in interrogatives:
                type = 'interrogativo'
                role = 'interrogativo'
            
            # 2. Aggettivi POSSESSIVI
            elif word_lower in possessives:
                type = 'aggettivo_possessivo'
                role = 'possessivo'
            
            # 3. Articoli
            elif word_lower in articles:
                type = 'articolo'
                role = 'articolo'
            
            # 4. Preposizioni
            elif word_lower in prepositions:
                type = 'preposizione'
                role = 'preposizione'
            
            # 5. Pronomi personali
            elif word_lower in pronouns:
                type = 'pronome'
                role = 'soggetto'
            
            # 6. Verbi
            elif word_lower in common_verbs:
                type = 'verbo'
                role = 'verbo'
            
            # 7. Aggettivi qualificativi
            elif word_lower in common_adjectives:
                type = 'aggettivo'
                role = 'attributo'
            
            # 8. FALLBACK LOGIC (Migliorato)
            else:
                # Se segue un articolo, probabilmente è un nome
                if i > 0 and components[-1].type == 'articolo':
                    type = 'nome'
                    role = 'oggetto'
                # Se segue un possessivo, probabilmente è un nome
                elif i > 0 and components[-1].type == 'aggettivo_possessivo':
                    type = 'nome'
                    role = 'oggetto'
                # Se segue un verbo essere/avere, potrebbe essere complemento
                elif i > 0 and components[-1].text.lower() in ['è', 'sono', 'era', 'sei']:
                    type = 'nome'
                    role = 'complemento'
                # Default: nome comune
                else:
                    type = 'nome'
                    role = 'complemento'
            
            # Crea il componente
            component = SentenceComponent(
                text=word,
                role=role,
                type=type,
                position=i
            )
            # Rimuovi print per performance
            # print(f"Componente creato: {component.text} -> tipo: {component.type}, ruolo: {component.role}")
            components.append(component)
        
        # Raffina i ruoli basandosi sul contesto
        self._refine_roles(components)
        
        return components

    def _refine_roles(self, components: List[SentenceComponent]):
        """Raffina i ruoli basandosi sul contesto della frase."""
        # Se c'è un verbo "essere" o "chiamarsi", il componente successivo è un nome
        for i, comp in enumerate(components):
            print(f"Raffinamento ruolo per: {comp.text} -> ruolo attuale: {comp.role}")
            
            # Non modificare il ruolo se è già "nome"
            if comp.role == "nome":
                print(f"Nuovo ruolo: {comp.role}")
                continue
                
            # Regole di raffinamento
            if comp.type == "pronome":
                comp.role = "soggetto"
            elif comp.type == "verbo":
                comp.role = "verbo"
            elif comp.type == "nome":
                # Se è preceduto da un verbo come "essere" o "chiamarsi"
                if i > 0 and components[i-1].text.lower() in ["sono", "è", "chiamo", "chiama"]:
                    comp.role = "nome"
                else:
                    comp.role = "soggetto"
            
            print(f"Nuovo ruolo: {comp.role}")

class ContextResolver:
    def resolve(self, components: List[SentenceComponent], 
               previous_context: Optional[Dict],
               context_history: List[Dict]) -> Dict[str, ContextualReference]:
        return {"base_context": ContextualReference(
            type="base",
            value="test",
            confidence=1.0,
            resolution=None
        )}

class AmbiguityDetector:
    def detect(self, components: List[SentenceComponent],
              context: Dict[str, ContextualReference],
              context_history: List[Dict]) -> List[str]:
        return []
