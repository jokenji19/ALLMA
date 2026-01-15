from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from datetime import datetime
import re
from collections import defaultdict
from allma_model.incremental_learning.emotional_system import Emotion, EmotionType
import numpy as np

class CommunicationMode(Enum):
    FORMAL = "formal"
    INFORMAL = "informal"
    TECHNICAL = "technical"
    EMPATHETIC = "empathetic"
    CONCISE = "concise"
    DETAILED = "detailed"
    NATURAL = "natural"

class IntentType(Enum):
    QUESTION = "question"
    STATEMENT = "statement"
    COMMAND = "command"
    REQUEST = "request"
    CLARIFICATION = "clarification"
    CONFIRMATION = "confirmation"

class SentimentType(Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    MIXED = "mixed"

@dataclass
class DialogContext:
    """Rappresenta il contesto di un dialogo"""
    topic: str
    mode: CommunicationMode
    history: List[str] = field(default_factory=list)
    entities: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

@dataclass
class Message:
    """Rappresenta un messaggio nel dialogo"""
    content: str
    intent: IntentType
    sentiment: SentimentType
    entities: Dict[str, Any]
    context: DialogContext
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Response:
    """Rappresenta una risposta del sistema"""
    content: str
    style: CommunicationMode
    timestamp: datetime = datetime.now()
    context: Optional[Dict] = None

@dataclass
class ConceptLink:
    """Rappresenta un collegamento tra due concetti"""
    source: str
    target: str
    relation_type: str
    weight: float = 1.0
    timestamp: datetime = field(default_factory=datetime.now)
    context: Optional[str] = None

class ConceptNetwork:
    """Rete di concetti e loro relazioni"""
    def __init__(self):
        self.concepts: Dict[str, Set[str]] = defaultdict(set)
        self.links: List[ConceptLink] = []
        self.concept_embeddings: Dict[str, np.ndarray] = {}
        
    def add_concept(self, concept: str, related_terms: Set[str]):
        """Aggiunge un nuovo concetto alla rete"""
        self.concepts[concept].update(related_terms)
        
    def add_link(self, link: ConceptLink):
        """Aggiunge un nuovo collegamento tra concetti"""
        self.links.append(link)
        self.concepts[link.source].add(link.target)
        self.concepts[link.target].add(link.source)
        
    def get_related_concepts(self, concept: str, max_distance: int = 2) -> Set[str]:
        """Trova concetti correlati entro una certa distanza"""
        related = set()
        current_level = {concept}
        
        for _ in range(max_distance):
            next_level = set()
            for current in current_level:
                next_level.update(self.concepts[current])
            related.update(next_level)
            current_level = next_level
            
        return related
        
    def find_path(self, source: str, target: str) -> List[ConceptLink]:
        """Trova il percorso più breve tra due concetti"""
        if source not in self.concepts or target not in self.concepts:
            return []
            
        visited = {source}
        queue = [(source, [])]
        
        while queue:
            current, path = queue.pop(0)
            
            if current == target:
                return path
                
            for link in self.links:
                if link.source == current and link.target not in visited:
                    visited.add(link.target)
                    queue.append((link.target, path + [link]))
                elif link.target == current and link.source not in visited:
                    visited.add(link.source)
                    queue.append((link.source, path + [link]))
                    
        return []
        
    def get_concept_similarity(self, concept1: str, concept2: str) -> float:
        """Calcola la similarità tra due concetti"""
        if concept1 not in self.concept_embeddings or concept2 not in self.concept_embeddings:
            return 0.0
            
        emb1 = self.concept_embeddings[concept1]
        emb2 = self.concept_embeddings[concept2]
        
        return np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
    def update_concept_embedding(self, concept: str, embedding: np.ndarray):
        """Aggiorna l'embedding di un concetto"""
        self.concept_embeddings[concept] = embedding
        
    def get_strongest_relations(self, concept: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Trova le relazioni più forti per un concetto"""
        relations = []
        
        for link in self.links:
            if link.source == concept:
                relations.append((link.target, link.weight))
            elif link.target == concept:
                relations.append((link.source, link.weight))
                
        return sorted(relations, key=lambda x: x[1], reverse=True)[:top_k]

class ContextTracker:
    """Sistema per il tracking del contesto della conversazione"""
    def __init__(self):
        self.concept_network = ConceptNetwork()
        self.current_context: Dict[str, Any] = {}
        self.context_history: List[Dict[str, Any]] = []
        self.active_concepts: Set[str] = set()
        
    def update_context(self, new_context: Dict[str, Any]):
        """Aggiorna il contesto corrente"""
        # Salva il contesto precedente nella storia
        if self.current_context:
            self.context_history.append(self.current_context.copy())
            
        # Aggiorna il contesto corrente
        self.current_context.update(new_context)
        
        # Estrai e aggiorna i concetti attivi
        self._extract_concepts(new_context)
        
    def _extract_concepts(self, context: Dict[str, Any]):
        """Estrae concetti dal contesto"""
        # Estrai concetti dal topic
        if "topic" in context:
            self.active_concepts.add(context["topic"])
            
        # Estrai concetti dalle entità
        if "entities" in context:
            for entity in context["entities"]:
                self.active_concepts.add(entity)
                
        # Crea collegamenti tra concetti attivi
        active_list = list(self.active_concepts)
        for i in range(len(active_list)):
            for j in range(i + 1, len(active_list)):
                link = ConceptLink(
                    source=active_list[i],
                    target=active_list[j],
                    relation_type="co-occurrence"
                )
                self.concept_network.add_link(link)
                
    def get_context_summary(self) -> Dict[str, Any]:
        """Restituisce un riepilogo del contesto attuale"""
        summary = {
            "current_context": self.current_context,
            "active_concepts": list(self.active_concepts),
            "context_depth": len(self.context_history)
        }
        
        if self.active_concepts:
            # Trova concetti correlati per ogni concetto attivo
            related_concepts = set()
            for concept in self.active_concepts:
                related = self.concept_network.get_related_concepts(concept)
                related_concepts.update(related)
                
            summary["related_concepts"] = list(related_concepts)
            
        return summary
        
    def find_relevant_context(self, query: str) -> Dict[str, Any]:
        """Trova il contesto rilevante per una query"""
        relevant_context = {}
        
        # Cerca nella storia del contesto
        for past_context in reversed(self.context_history + [self.current_context]):
            topic = past_context.get("topic", "").lower()
            if topic and any(term in query.lower() for term in topic.split()):
                relevant_context.update(past_context)
                break
                
        # Aggiungi concetti correlati
        query_concepts = set(query.lower().split())
        related_concepts = set()
        
        for concept in query_concepts:
            if concept in self.active_concepts:
                related = self.concept_network.get_related_concepts(concept)
                related_concepts.update(related)
                
        if related_concepts:
            relevant_context["related_concepts"] = list(related_concepts)
            
        # Se non abbiamo trovato un contesto rilevante nella storia
        # ma abbiamo un contesto corrente, usalo
        if not relevant_context and self.current_context:
            relevant_context.update(self.current_context)
            
        return relevant_context

class CommunicationSystem:
    """Sistema di comunicazione per la gestione del linguaggio naturale e del dialogo"""
    
    def __init__(self):
        self.contexts: Dict[str, DialogContext] = {}
        self.entity_types: Dict[str, Set[str]] = defaultdict(set)
        self.patterns: Dict[str, List[str]] = {
            "question": [
                r"\b(chi|cosa|dove|quando|perché|come)\b.*\?",
                r"\b(puoi|potresti|sai|hai)\b.*\?",
                r"\?.+$"
            ],
            "command": [
                r"^(fai|esegui|mostra|calcola|trova|cerca|analizza)\b",
                r"^(per favore,?\s)?(fai|esegui|mostra)\b"
            ],
            "request": [
                r"^(potresti|puoi|vorrei|voglio)\b",
                r"^(per favore|per cortesia)\b",
                r"\b(aiutarmi|aiutare)\b"
            ],
            "clarification": [
                r"\b(cosa intendi|puoi spiegare|non capisco|chiarire)\b",
                r"\b(più dettagli|esempio|specifico)\b"
            ],
            "confirmation": [
                r"\b(giusto|corretto|vero|confermi|sicuro)\b\?",
                r"^(quindi|dunque|allora)\b.*\?"
            ]
        }
        self.sentiment_patterns: Dict[str, List[str]] = {
            "positive": [
                r"\b(bene|ottimo|eccellente|perfetto|grazie|piacere)\b",
                r"\b(fantastico|meraviglioso|stupendo|bellissimo)\b"
            ],
            "negative": [
                r"\b(male|errore|problema|difficile|impossibile)\b",
                r"\b(non funziona|non va|impossibile)\b"
            ],
            "neutral": [
                r"^(ok|capito|ho capito|comprendo|vedo)\b",
                r"\b(normale|standard|regolare|comune)\b",
                r"\b(come|cosa|dove|quando|perché)\b.*\?"  # Domande sono generalmente neutrali
            ]
        }
        self.current_mode = CommunicationMode.NATURAL
        self.conversation_history = []
        self.context_tracker = ContextTracker()
        
    def create_context(self, topic: str, mode: CommunicationMode) -> DialogContext:
        """Crea un nuovo contesto di dialogo"""
        context = DialogContext(
            topic=topic,
            mode=mode
        )
        self.contexts[topic] = context
        return context
        
    def update_context(self, context: DialogContext, message: str) -> None:
        """Aggiorna il contesto con un nuovo messaggio"""
        context.history.append(message)
        
        # Estrai e aggiorna le entità
        new_entities = self._extract_entities(message)
        context.entities.update(new_entities)
        
        # Aggiorna i metadati
        context.metadata["last_update"] = datetime.now()
        context.metadata["message_count"] = len(context.history)
        
        # Aggiorna il contesto della conversazione
        self.context_tracker.update_context({
            "topic": context.topic,
            "entities": context.entities
        })
        
    def analyze_message(self, message: str, context: DialogContext) -> Message:
        """Analizza un messaggio e determina intent e sentiment"""
        intent = self._determine_intent(message)
        sentiment = self._analyze_sentiment(message)
        entities = self._extract_entities(message)
        
        return Message(
            content=message,
            intent=intent,
            sentiment=sentiment,
            entities=entities,
            context=context
        )
        
    def generate_response(
        self,
        input_text: str,
        emotion: Emotion,
        mode: CommunicationMode = None,
        context: Optional[Dict] = None
    ) -> Response:
        """
        Genera una risposta appropriata
        
        Args:
            input_text: Testo di input
            emotion: Stato emotivo
            mode: Modalità di comunicazione (opzionale)
            context: Contesto aggiuntivo (opzionale)
            
        Returns:
            Response: Risposta generata
            
        Raises:
            ValueError: Se input_text o emotion non sono validi
        """
        if not input_text or not isinstance(input_text, str):
            raise ValueError("input_text deve essere una stringa non vuota")
            
        if not emotion or not isinstance(emotion, Emotion):
            raise ValueError("emotion deve essere un'istanza valida di Emotion")
            
        # Usa la modalità specificata o quella corrente
        mode = mode or self.current_mode
        
        # Analizza l'input e genera una risposta appropriata
        content = self._generate_content(input_text, emotion, mode)
        
        # Crea la risposta
        response = Response(
            content=content,
            style=mode,
            context={"emotion": emotion.primary_emotion}
        )
        
        # Aggiorna la storia della conversazione
        self.conversation_history.append(response)
        
        return response
        
    def _determine_intent(self, message: str) -> IntentType:
        """Determina l'intento del messaggio"""
        message = message.lower()
        
        # Controlla ogni pattern per ogni tipo di intent
        for intent_type in IntentType:
            if intent_type.value in self.patterns:
                for pattern in self.patterns[intent_type.value]:
                    if re.search(pattern, message):
                        return intent_type
                        
        # Default a STATEMENT se nessun altro pattern corrisponde
        return IntentType.STATEMENT
        
    def _analyze_sentiment(self, message: str) -> SentimentType:
        """Analizza il sentiment del messaggio"""
        message = message.lower()
        
        # Se è una domanda, è generalmente neutrale
        if any(pattern in message for pattern in ["?", "come", "cosa", "dove", "quando", "perché"]):
            return SentimentType.NEUTRAL
            
        # Conta le corrispondenze per ogni tipo di sentiment
        sentiment_scores = defaultdict(int)
        
        for sentiment, patterns in self.sentiment_patterns.items():
            for pattern in patterns:
                if re.search(pattern, message):
                    sentiment_scores[sentiment] += 1
                    
        # Determina il sentiment dominante
        if not sentiment_scores:
            return SentimentType.NEUTRAL
            
        max_score = max(sentiment_scores.values())
        max_sentiments = [s for s, score in sentiment_scores.items() if score == max_score]
        
        if len(max_sentiments) > 1:
            return SentimentType.MIXED
            
        return SentimentType(max_sentiments[0])
        
    def _extract_entities(self, message: str) -> Dict[str, Any]:
        """Estrae entità dal messaggio"""
        entities = {}
        
        # Estrai date e orari
        date_patterns = [
            (r"\d{1,2}/\d{1,2}/\d{2,4}", "date"),
            (r"\d{1,2}:\d{2}", "time")
        ]
        
        for pattern, entity_type in date_patterns:
            matches = re.finditer(pattern, message)
            for match in matches:
                entities[entity_type] = match.group()
                
        # Estrai numeri
        number_matches = re.finditer(r"\d+(?:\.\d+)?", message)
        numbers = [float(match.group()) for match in number_matches]
        if numbers:
            entities["numbers"] = numbers
            
        # Estrai email
        email_matches = re.finditer(r"\b[\w\.-]+@[\w\.-]+\.\w+\b", message)
        emails = [match.group() for match in email_matches]
        if emails:
            entities["emails"] = emails
            
        return entities
        
    def _get_communication_style(self, mode: CommunicationMode) -> Dict[str, Any]:
        """Ottiene lo stile di comunicazione per una modalità"""
        styles = {
            CommunicationMode.FORMAL: {
                "greeting": "Gentile",
                "closing": "Cordialmente",
                "politeness": True,
                "technical_terms": False,
                "emotion_words": False
            },
            CommunicationMode.INFORMAL: {
                "greeting": "Ciao",
                "closing": "A presto",
                "politeness": False,
                "technical_terms": False,
                "emotion_words": True
            },
            CommunicationMode.TECHNICAL: {
                "greeting": "Salve",
                "closing": "Regards",
                "politeness": True,
                "technical_terms": True,
                "emotion_words": False
            },
            CommunicationMode.EMPATHETIC: {
                "greeting": "Caro",
                "closing": "Con affetto",
                "politeness": True,
                "technical_terms": False,
                "emotion_words": True
            },
            CommunicationMode.CONCISE: {
                "greeting": "",
                "closing": "",
                "politeness": False,
                "technical_terms": False,
                "emotion_words": False
            },
            CommunicationMode.DETAILED: {
                "greeting": "Salve",
                "closing": "In conclusione",
                "politeness": True,
                "technical_terms": True,
                "emotion_words": False
            },
            CommunicationMode.NATURAL: {
                "greeting": "",
                "closing": "",
                "politeness": False,
                "technical_terms": False,
                "emotion_words": True
            }
        }
        return styles.get(mode, styles[CommunicationMode.FORMAL])
        
    def _generate_base_response(self, message: Message) -> str:
        """Genera una risposta base in base all'intent del messaggio"""
        # Analizza il contesto storico
        context_info = self._analyze_context_history(message.context)
        
        # Ottieni la funzione di generazione appropriata
        intent_responses = {
            IntentType.QUESTION: self._generate_question_response,
            IntentType.COMMAND: self._generate_command_response,
            IntentType.REQUEST: self._generate_request_response,
            IntentType.CLARIFICATION: self._generate_clarification_response,
            IntentType.CONFIRMATION: self._generate_confirmation_response,
            IntentType.STATEMENT: self._generate_statement_response
        }
        
        generator = intent_responses.get(message.intent, self._generate_statement_response)
        base_response = generator(message)
        
        # Adatta la risposta al sentiment
        base_response = self._adapt_to_sentiment(base_response, message.sentiment)
        
        # Aggiungi contesto se necessario
        if self._needs_context(message):
            base_response = self._add_context(base_response, message.context)
            
        # Aggiungi informazioni dal contesto storico se rilevanti
        if context_info:
            base_response = f"{base_response} {context_info}"
            
        # Aggiungi riferimenti a problemi se presenti nel messaggio
        if "problema" in message.content.lower():
            base_response += " Posso aiutarti a risolvere il problema."
            
        return base_response
        
    def _analyze_context_history(self, context: DialogContext) -> Optional[str]:
        """Analizza la storia del contesto per informazioni rilevanti"""
        if not context.history:
            return None
            
        # Cerca pattern ricorrenti
        topics = self._extract_topics(context.history)
        entities = self._extract_recurring_entities(context.history)
        
        info = []
        if topics:
            info.append(f"Argomenti principali: {', '.join(topics)}")
        if entities:
            info.append(f"Elementi rilevanti: {', '.join(entities)}")
            
        return ". ".join(info) if info else None
        
    def _extract_topics(self, history: List[str]) -> List[str]:
        """Estrae i topic principali dalla storia"""
        # Implementazione base - da espandere con NLP
        topics = set()
        for msg in history:
            # Cerca sostantivi e frasi nominali
            words = msg.lower().split()
            for word in words:
                if len(word) > 3 and not any(c in word for c in "?!.,"):
                    topics.add(word)
        return list(topics)[:3]  # Limita ai 3 topic più rilevanti
        
    def _extract_recurring_entities(self, history: List[str]) -> List[str]:
        """Estrae entità ricorrenti dalla storia"""
        entities = {}
        for msg in history:
            msg_entities = self._extract_entities(msg)
            for entity, value in msg_entities.items():
                if entity not in entities:
                    entities[entity] = {"value": value, "count": 1}
                else:
                    entities[entity]["count"] += 1
                    
        # Ritorna solo entità che appaiono più di una volta
        return [f"{e}: {d['value']}" for e, d in entities.items() if d["count"] > 1]
        
    def _adapt_to_sentiment(self, response: str, sentiment: SentimentType) -> str:
        """Adatta la risposta al sentiment del messaggio"""
        sentiment_adaptations = {
            SentimentType.POSITIVE: [
                "Sono contento di sentirlo!",
                "Ottimo!",
                "Fantastico!"
            ],
            SentimentType.NEGATIVE: [
                "Mi dispiace per questo.",
                "Capisco la tua frustrazione.",
                "Vediamo come posso aiutarti."
            ],
            SentimentType.MIXED: [
                "Capisco i tuoi sentimenti contrastanti.",
                "È una situazione complessa.",
                "Vediamo gli aspetti positivi e negativi."
            ]
        }
        
        if sentiment in sentiment_adaptations:
            adaptation = sentiment_adaptations[sentiment][0]  # Usa sempre il primo per ora
            return f"{adaptation} {response}"
            
        return response

    def _generate_question_response(self, message: Message) -> str:
        """Genera una risposta a una domanda"""
        # Analizza il tipo di domanda
        question_type = self._analyze_question_type(message.content)
        
        # Cerca informazioni rilevanti nel contesto
        context_info = self._find_context_info(message)
        
        # Genera risposta base
        if question_type == "how":
            base = "Ecco i passaggi da seguire:"
        elif question_type == "why":
            base = "Questo accade perché:"
        elif question_type == "when":
            base = "Il momento migliore è:"
        elif question_type == "where":
            base = "Puoi trovarlo:"
        elif question_type == "who":
            base = "La persona responsabile è:"
        else:
            base = "La risposta è:"
            
        # Aggiungi informazioni dal contesto se disponibili
        if context_info:
            return f"{base} {context_info}"
            
        return base
        
    def _analyze_question_type(self, content: str) -> str:
        """Analizza il tipo di domanda"""
        content = content.lower()
        if "come" in content:
            return "how"
        elif "perché" in content:
            return "why"
        elif "quando" in content:
            return "when"
        elif "dove" in content:
            return "where"
        elif "chi" in content:
            return "who"
        return "what"
        
    def _find_context_info(self, message: Message) -> Optional[str]:
        """Cerca informazioni rilevanti nel contesto"""
        # Cerca nelle entità del contesto
        if message.context.entities:
            relevant_entities = []
            for key, value in message.context.entities.items():
                if key in message.content.lower():
                    relevant_entities.append(f"{key}: {value}")
            if relevant_entities:
                return ", ".join(relevant_entities)
                
        # Cerca nella storia del contesto
        if message.context.history:
            for hist_msg in reversed(message.context.history):
                if any(word in hist_msg.lower() for word in message.content.lower().split()):
                    return f"Secondo quanto detto prima: {hist_msg}"
                    
        return None
        
    def _generate_content(self, input_text: str, emotion: Emotion, mode: CommunicationMode) -> str:
        """Genera il contenuto della risposta"""
        # Template avanzati per ogni modalità
        templates = {
            CommunicationMode.NATURAL: [
                "Capisco quello che dici. {}",
                "Mi sembra di capire. {}",
                "Sì, comprendo. {}"
            ],
            CommunicationMode.FORMAL: [
                "Comprendo la sua affermazione. {}",
                "La sua osservazione è corretta. {}",
                "Mi permetto di rispondere che {}"
            ],
            CommunicationMode.TECHNICAL: [
                "Input analizzato. Risultato: {}",
                "Analisi tecnica: {}",
                "Output dell'elaborazione: {}"
            ],
            CommunicationMode.EMPATHETIC: [
                "Sento che ti senti {}. {}",
                "Capisco che provi {}. {}",
                "Dev'essere {} per te. {}"
            ],
            CommunicationMode.CONCISE: [
                "{}",
                "{} - Fine.",
                "In breve: {}"
            ],
            CommunicationMode.DETAILED: [
                "Analisi dettagliata:\n1. {}\n2. {}\n3. {}",
                "Spiegazione estesa:\n- Punto principale: {}\n- Dettagli: {}\n- Conclusione: {}",
                "Risposta completa:\n* {}\n* {}\n* {}"
            ]
        }
        
        # Genera la risposta base
        base_response = self._analyze_and_respond(input_text, emotion)
        
        # Seleziona il primo template per consistenza nei test
        template = templates[mode][0]
        
        # Adatta la risposta alla modalità
        if mode == CommunicationMode.EMPATHETIC:
            emotion_desc = self._describe_emotion(emotion)
            return template.format(emotion_desc, base_response)
        elif mode == CommunicationMode.DETAILED:
            context = self._get_response_context(input_text)
            implications = self._get_response_implications(input_text)
            return template.format(base_response, context, implications)
        else:
            return template.format(base_response)

    def _describe_emotion(self, emotion: Emotion) -> str:
        """Descrive un'emozione in modo naturale"""
        intensity_desc = "molto " if emotion.intensity > 0.7 else ""
        emotion_desc = {
            EmotionType.JOY: "felice",
            EmotionType.SADNESS: "triste",
            EmotionType.ANGER: "arrabbiato",
            EmotionType.FEAR: "preoccupato",
            EmotionType.SURPRISE: "sorpreso",
            EmotionType.TRUST: "fiducioso",
            EmotionType.ANTICIPATION: "in attesa",
            EmotionType.DISGUST: "infastidito",
            EmotionType.NEUTRAL: "tranquillo",
            EmotionType.FRUSTRATION: "frustrato",
            EmotionType.CONFUSION: "confuso",
            EmotionType.CURIOSITY: "curioso",
            EmotionType.HOPE: "speranzoso",
            EmotionType.ANXIETY: "ansioso"
        }
        return f"{intensity_desc}{emotion_desc.get(emotion.primary_emotion, emotion.primary_emotion.value.lower())}"

    def _get_emotional_context(self, emotion: Emotion) -> str:
        """Ottiene il contesto emotivo"""
        if emotion.secondary_emotions:
            emotions = [e.value for e in emotion.secondary_emotions]
            return f"Noto anche tracce di {', '.join(emotions)}"
        return ""

    def _get_emotional_implications(self, emotion: Emotion) -> str:
        """Ottiene le implicazioni emotive"""
        if emotion.valence > 0:
            return "Questo è un buon segno"
        elif emotion.valence < 0:
            return "Cerchiamo di migliorare questa situazione"
        return "Continuiamo a monitorare la situazione"

    def _get_response_context(self, input_text: str) -> str:
        """Ottiene il contesto della risposta"""
        # Implementazione base - da espandere
        return "Basato sul contesto attuale"

    def _get_response_implications(self, input_text: str) -> str:
        """Ottiene le implicazioni della risposta"""
        # Implementazione base - da espandere
        return "Possibili sviluppi futuri"

    def _analyze_and_respond(self, input_text: str, emotion: Emotion) -> str:
        """Analizza l'input e genera una risposta base"""
        # Risposte base per diverse emozioni
        emotion_responses = {
            EmotionType.JOY: "Sono contento che tu sia felice!",
            EmotionType.SADNESS: "Mi dispiace che tu ti senta così.",
            EmotionType.ANGER: "Capisco la tua frustrazione.",
            EmotionType.FEAR: "Non preoccuparti, possiamo risolvere insieme.",
            EmotionType.SURPRISE: "È davvero interessante!",
            EmotionType.TRUST: "Apprezzo la tua fiducia.",
            EmotionType.ANTICIPATION: "Vediamo cosa possiamo fare.",
            EmotionType.DISGUST: "Capisco il tuo disagio.",
            EmotionType.NEUTRAL: "Continua pure.",
            EmotionType.FRUSTRATION: "Capisco la tua frustrazione.",
            EmotionType.CONFUSION: "Ti aiuto a fare chiarezza.",
            EmotionType.CURIOSITY: "È interessante la tua curiosità.",
            EmotionType.HOPE: "Condivido il tuo ottimismo.",
            EmotionType.ANXIETY: "Cerchiamo di alleviare questa preoccupazione."
        }
        
        # Seleziona la risposta base dall'emozione
        base_response = emotion_responses.get(
            emotion.primary_emotion,
            "Capisco."
        )
        
        # Aggiungi dettagli basati sull'input
        if "problema" in input_text.lower() or "errore" in input_text.lower():
            base_response += " Posso aiutarti a risolvere il problema."
        elif "grazie" in input_text.lower():
            base_response += " Sono qui per aiutare!"
        elif "?" in input_text:
            base_response += " Cerchiamo di trovare una risposta."
            
        # Considera le emozioni secondarie
        if emotion.secondary_emotions:
            secondary_responses = []
            for sec_emotion in emotion.secondary_emotions:
                if sec_emotion in emotion_responses:
                    secondary_responses.append(emotion_responses[sec_emotion].lower())
            if secondary_responses:
                base_response += f" Inoltre, {' E '.join(secondary_responses)}"
                
        return base_response
        
    def _generate_command_response(self, message: Message) -> str:
        """Genera una risposta a un comando"""
        command_types = {
            "calcola": "Ho eseguito il calcolo richiesto.",
            "trova": "Ho cercato quello che mi hai chiesto.",
            "mostra": "Ecco quello che volevi vedere.",
            "esegui": "Ho eseguito l'operazione richiesta.",
            "analizza": "Ho completato l'analisi.",
            "cerca": "Ho effettuato la ricerca."
        }
        
        for cmd_type, response in command_types.items():
            if cmd_type in message.content.lower():
                return response
                
        return "Ho eseguito il comando richiesto."
        
    def _generate_request_response(self, message: Message) -> str:
        """Genera una risposta a una richiesta"""
        request_types = {
            "aiuto": "Certamente, sono qui per aiutarti.",
            "spiegazione": "Ti spiego subito.",
            "informazioni": "Ti fornisco tutte le informazioni necessarie.",
            "consiglio": "Ecco il mio consiglio.",
            "supporto": "Sono qui per supportarti."
        }
        
        for req_type, response in request_types.items():
            if req_type in message.content.lower():
                return response
                
        return "Certamente, procedo con la tua richiesta."
        
    def _generate_clarification_response(self, message: Message) -> str:
        """Genera una risposta di chiarimento"""
        clarification_types = {
            "non capisco": "Ti spiego meglio:",
            "cosa intendi": "Quello che intendo è:",
            "puoi spiegare": "Ecco una spiegazione più chiara:",
            "non è chiaro": "Permettimi di chiarire:",
            "più dettagli": "Ecco maggiori dettagli:"
        }
        
        for clar_type, response in clarification_types.items():
            if clar_type in message.content.lower():
                return response
                
        return "Mi spiego meglio:"
        
    def _generate_confirmation_response(self, message: Message) -> str:
        """Genera una risposta di conferma"""
        confirmation_types = {
            "giusto": "Sì, è corretto.",
            "vero": "Sì, è vero.",
            "confermi": "Confermo.",
            "sicuro": "Sì, sono sicuro.",
            "quindi": "Esatto, hai capito bene."
        }
        
        for conf_type, response in confirmation_types.items():
            if conf_type in message.content.lower():
                return response
                
        return "Sì, confermo."
        
    def _generate_statement_response(self, message: Message) -> str:
        """Genera una risposta a un'affermazione"""
        statement_types = {
            "penso": "Interessante il tuo punto di vista.",
            "credo": "Capisco la tua prospettiva.",
            "secondo me": "La tua opinione è importante.",
            "mi sembra": "È una buona osservazione.",
            "ho notato": "Grazie per averlo fatto notare."
        }
        
        for stmt_type, response in statement_types.items():
            if stmt_type in message.content.lower():
                return response
                
        return "Ho capito, grazie per l'informazione."

    def set_communication_mode(self, mode: CommunicationMode) -> None:
        """Imposta la modalità di comunicazione"""
        self.current_mode = mode
        
    def get_conversation_history(self) -> List[Response]:
        """Ottiene la storia della conversazione"""
        return self.conversation_history

    def _needs_context(self, message: Message) -> bool:
        """Determina se è necessario aggiungere contesto alla risposta"""
        # Aggiungi contesto se:
        # 1. È una richiesta di chiarimento
        # 2. Il contesto ha informazioni rilevanti
        # 3. Ci sono riferimenti ambigui nel messaggio
        return (
            message.intent == IntentType.CLARIFICATION or
            len(message.context.entities) > 0 or
            any(word in message.content.lower() for word in ["questo", "quello", "esso", "loro"])
        )
        
    def _add_context(self, response: str, context: DialogContext) -> str:
        """Aggiunge informazioni di contesto alla risposta"""
        # Aggiungi riferimenti al topic se rilevante
        if context.topic:
            response = f"Riguardo a {context.topic}, {response.lower()}"
            
        # Aggiungi riferimenti alle entità se necessario
        if context.entities:
            entity_str = ", ".join(f"{k}: {v}" for k, v in context.entities.items())
            response = f"{response} (Contesto: {entity_str})"
            
        return response
        
    def _apply_style(self, response: str, style: Dict[str, Any]) -> str:
        """Applica uno stile di comunicazione alla risposta"""
        styled = []
        
        # Aggiungi il saluto se presente
        if style["greeting"]:
            styled.append(f"{style['greeting']},")
            
        # Aggiungi la risposta principale
        if style["politeness"]:
            response = f"Per cortesia, {response.lower()}"
            
        styled.append(response)
        
        # Aggiungi la chiusura se presente
        if style["closing"]:
            styled.append(style["closing"])
            
        return " ".join(styled)
