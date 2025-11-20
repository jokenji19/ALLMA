"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Emotional Intelligence System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Emotional analysis algorithms
- Contextual response generation
- Emotional memory integration
- Personality adaptation systems
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from enum import Enum
from datetime import datetime
import time
import numpy as np
from collections import defaultdict
import logging
import spacy
import re

class EmotionType(Enum):
    """Tipi di emozioni supportate con maggiore granularità"""
    # Emozioni base
    JOY = "joy"
    SADNESS = "sadness"
    ANGER = "anger"
    FEAR = "fear"
    SURPRISE = "surprise"
    TRUST = "trust"
    ANTICIPATION = "anticipation"
    DISGUST = "disgust"
    NEUTRAL = "neutral"
    
    # Emozioni complesse
    GRATITUDE = "gratitude"
    PRIDE = "pride"
    CURIOSITY = "curiosity"
    EMPATHY = "empathy"
    NOSTALGIA = "nostalgia"
    ANXIETY = "anxiety"
    HOPE = "hope"
    DISAPPOINTMENT = "disappointment"
    CONFUSION = "confusion"
    SATISFACTION = "satisfaction"
    FRUSTRATION = "frustration"
    ADMIRATION = "admiration"
    SERENITY = "serenity"
    ENTHUSIASM = "enthusiasm"

    @property
    def primary_emotion(self) -> 'EmotionType':
        """Restituisce l'emozione primaria associata a questa emozione"""
        primary_map = {
            self.JOY: self.JOY,
            self.SADNESS: self.SADNESS,
            self.ANGER: self.ANGER,
            self.FEAR: self.FEAR,
            self.SURPRISE: self.SURPRISE,
            self.TRUST: self.TRUST,
            self.ANTICIPATION: self.ANTICIPATION,
            self.DISGUST: self.DISGUST,
            self.NEUTRAL: self.NEUTRAL,
            self.GRATITUDE: self.JOY,
            self.PRIDE: self.JOY,
            self.CURIOSITY: self.ANTICIPATION,
            self.EMPATHY: self.TRUST,
            self.NOSTALGIA: self.SADNESS,
            self.ANXIETY: self.FEAR,
            self.HOPE: self.ANTICIPATION,
            self.DISAPPOINTMENT: self.SADNESS,
            self.CONFUSION: self.SURPRISE,
            self.SATISFACTION: self.JOY,
            self.FRUSTRATION: self.ANGER,
            self.ADMIRATION: self.JOY,
            self.SERENITY: self.JOY,
            self.ENTHUSIASM: self.JOY
        }
        return primary_map[self]
        
    @property
    def intensity(self) -> float:
        """Restituisce l'intensità di default per questa emozione"""
        intensity_map = {
            self.JOY: 0.8,
            self.SADNESS: 0.7,
            self.ANGER: 0.9,
            self.FEAR: 0.8,
            self.SURPRISE: 0.6,
            self.TRUST: 0.5,
            self.ANTICIPATION: 0.4,
            self.DISGUST: 0.7,
            self.NEUTRAL: 0.1,
            self.GRATITUDE: 0.6,
            self.PRIDE: 0.7,
            self.CURIOSITY: 0.5,
            self.EMPATHY: 0.6,
            self.NOSTALGIA: 0.4,
            self.ANXIETY: 0.7,
            self.HOPE: 0.6,
            self.DISAPPOINTMENT: 0.5,
            self.CONFUSION: 0.4,
            self.SATISFACTION: 0.7,
            self.FRUSTRATION: 0.8,
            self.ADMIRATION: 0.7,
            self.SERENITY: 0.6,
            self.ENTHUSIASM: 0.9
        }
        return intensity_map[self]

@dataclass
class Emotion:
    """Rappresenta uno stato emotivo"""
    primary_emotion: EmotionType
    intensity: float
    valence: float
    timestamp: datetime = field(default_factory=datetime.now)
    secondary_emotions: Optional[List[EmotionType]] = None
    name: str = ""
    arousal: float = 0.0
    dominance: float = 0.0

    def get_current_intensity(self) -> float:
        """Calcola l'intensità attuale dell'emozione considerando il decadimento"""
        elapsed_time = (datetime.now() - self.timestamp).total_seconds()
        decay_factor = 1.0 / (1.0 + 0.1 * elapsed_time)  # Decadimento iperbolico
        return max(0.05, self.intensity * decay_factor)  # Mantieni almeno un'intensità minima
        
    def to_dict(self) -> Dict:
        """Converte l'emozione in un dizionario"""
        return {
            'primary_emotion': self.primary_emotion.value,
            'intensity': self.intensity,
            'valence': self.valence,
            'timestamp': self.timestamp.isoformat(),
            'secondary_emotions': [e.value for e in (self.secondary_emotions or [])],
            'name': self.name,
            'arousal': self.arousal,
            'dominance': self.dominance
        }
    
@dataclass
class EmotionalState:
    """Rappresenta lo stato emotivo corrente"""
    primary_emotion: EmotionType
    intensity: float = 0.5
    secondary_emotions: List[Tuple[EmotionType, float]] = None
    language: str = "it"
    context: Dict = field(default_factory=dict)
    
    def get_emotion_name(self) -> str:
        """Restituisce il nome dell'emozione nella lingua corretta"""
        emotion_names = {
            "it": {
                EmotionType.JOY: "felicità",
                EmotionType.SADNESS: "tristezza",
                EmotionType.ANGER: "rabbia",
                EmotionType.FEAR: "paura",
                EmotionType.DISGUST: "disgusto",
                EmotionType.SURPRISE: "sorpresa",
                EmotionType.TRUST: "fiducia",
                EmotionType.ANTICIPATION: "anticipazione",
                EmotionType.ANXIETY: "ansia",
                EmotionType.CURIOSITY: "curiosità",
                EmotionType.NEUTRAL: "neutralità"
            },
            "en": {
                EmotionType.JOY: "joy",
                EmotionType.SADNESS: "sadness",
                EmotionType.ANGER: "anger",
                EmotionType.FEAR: "fear",
                EmotionType.DISGUST: "disgust",
                EmotionType.SURPRISE: "surprise",
                EmotionType.TRUST: "trust",
                EmotionType.ANTICIPATION: "anticipation",
                EmotionType.ANXIETY: "anxiety",
                EmotionType.CURIOSITY: "curiosity",
                EmotionType.NEUTRAL: "neutrality"
            }
        }
        return emotion_names.get(self.language, emotion_names["en"]).get(self.primary_emotion, "neutral")

@dataclass
class EmotionalPattern:
    """Pattern emotivo che rappresenta una sequenza di emozioni nel tempo"""
    emotions: List[Emotion]
    frequency: int = 1
    last_occurrence: datetime = field(default_factory=datetime.now)
    context: Optional[str] = None
    
    def matches(self, sequence: List[Emotion], threshold: float = 0.8) -> bool:
        """Verifica se una sequenza di emozioni corrisponde a questo pattern"""
        if len(sequence) != len(self.emotions):
            return False
        
        matches = 0
        for e1, e2 in zip(self.emotions, sequence):
            if (e1.primary_emotion == e2.primary_emotion and 
                abs(e1.intensity - e2.intensity) < 0.2 and
                abs(e1.valence - e2.valence) < 0.2):
                matches += 1
                
        return (matches / len(sequence)) >= threshold

class EmotionalSystem:
    """Sistema emotivo avanzato con analisi sofisticata e memoria emotiva"""
    
    def __init__(self):
        """Inizializza il sistema emotivo"""
        self.nlp = spacy.load("it_core_news_lg")
        self.emotional_memory = []
        self.context_window = []
        self._load_emotional_lexicon()
        self.emotion_patterns = {
            "it": {
                EmotionType.ANXIETY: [
                    (["ansio", "preoccupa", "stress", "agita", "teso", "nervos", "tension"], 1.0),
                    (["non so", "forse", "magari", "potrebbe", "incert"], 0.5),
                    (["difficile", "duro", "problema", "non riesco"], 0.7),
                    (["paura di", "temo di", "ho paura"], 0.8)
                ],
                EmotionType.JOY: [
                    (["felic", "content", "gioi", "delizia", "eccita", "seren"], 1.0),
                    (["bell", "meraviglios", "fantastic", "ottim", "eccezional"], 0.8),
                    (["amo", "adoro", "passion", "mi piace"], 0.9),
                    (["positiv", "ottimist", "fiducios"], 0.7)
                ],
                EmotionType.FEAR: [
                    (["paur", "terror", "spaventa", "timore", "preoccup"], 1.0),
                    (["ansio", "inquiet", "non sicuro"], 0.8),
                    (["dubbio", "incert", "non so se"], 0.6),
                    (["rischio", "pericolo", "minaccia"], 0.9)
                ],
                EmotionType.SADNESS: [
                    (["triste", "infelice", "depress", "malincon", "sconfort"], 1.0),
                    (["solo", "solitud", "dispiac", "soffr"], 0.8),
                    (["non ce la faccio", "non riesco", "difficile", "pesante"], 0.6),
                    (["deluso", "amareggiato", "sfiduciato"], 0.7)
                ],
                EmotionType.ANGER: [
                    (["arrabbia", "furios", "incazza", "nervos", "irritat"], 1.0),
                    (["fastidio", "secca", "infastid", "disturba"], 0.8),
                    (["non sopport", "odio", "detesto", "mi da fastidio"], 0.9),
                    (["insopportabile", "intollerabile", "esasperato"], 0.7)
                ],
                EmotionType.CURIOSITY: [
                    (["curios", "interessa", "affascina", "intriga"], 1.0),
                    (["vorrei sapere", "mi chiedo", "dimmi", "raccontami"], 0.8),
                    (["come mai", "perché", "in che modo", "come funziona"], 0.7),
                    (["scoprire", "esplorare", "conoscere", "imparare"], 0.9)
                ],
                EmotionType.SURPRISE: [
                    (["sorpres", "stupit", "meraviglia", "incredibil"], 1.0),
                    (["inaspettat", "non me lo aspettavo", "che shock"], 0.9),
                    (["wow", "oh", "davvero", "sul serio"], 0.8),
                    (["non ci posso credere", "è incredibile", "mai visto"], 0.7)
                ],
                EmotionType.HOPE: [
                    (["sper", "fiduci", "ottimis", "futuro", "motivat"], 1.0),
                    (["possibil", "ce la far", "miglior", "cambier"], 0.8),
                    (["desider", "sogn", "aspett", "progett"], 0.7),
                    (["avanti", "progress", "crescit", "svilupp"], 0.6)
                ]
            },
            "en": {
                EmotionType.ANXIETY: [
                    (["anxious", "worried", "stress", "nervous", "tense"], 1.0),
                    (["not sure", "maybe", "perhaps", "might", "uncertain"], 0.5),
                    (["difficult", "hard", "problem", "can't manage"], 0.7),
                    (["afraid of", "fear of", "I'm scared"], 0.8)
                ],
                EmotionType.JOY: [
                    (["happy", "glad", "joy", "delight", "excited", "serene"], 1.0),
                    (["nice", "wonderful", "fantastic", "great", "exceptional"], 0.8),
                    (["love", "adore", "passion", "enjoy"], 0.9),
                    (["positive", "optimistic", "confident"], 0.7)
                ],
                EmotionType.FEAR: [
                    (["fear", "terror", "scared", "afraid", "worried"], 1.0),
                    (["anxious", "concerned", "not sure"], 0.8),
                    (["doubt", "uncertain", "don't know if"], 0.6),
                    (["risk", "danger", "threat"], 0.9)
                ],
                EmotionType.SADNESS: [
                    (["sad", "unhappy", "depress", "melanchol", "down"], 1.0),
                    (["alone", "lonely", "sorry", "suffer"], 0.8),
                    (["can't do it", "can't manage", "difficult", "heavy"], 0.6),
                    (["disappointed", "bitter", "hopeless"], 0.7)
                ],
                EmotionType.ANGER: [
                    (["angry", "furious", "mad", "nervous", "irritated"], 1.0),
                    (["annoyed", "bothered", "disturbed"], 0.8),
                    (["can't stand", "hate", "detest", "bothers me"], 0.9),
                    (["unbearable", "intolerable", "exasperated"], 0.7)
                ],
                EmotionType.CURIOSITY: [
                    (["curious", "interested", "fascinated", "intrigued"], 1.0),
                    (["want to know", "wonder", "tell me", "explain"], 0.8),
                    (["how come", "why", "how does", "how works"], 0.7),
                    (["discover", "explore", "learn", "understand"], 0.9)
                ],
                EmotionType.SURPRISE: [
                    (["surprise", "astonish", "amaze", "incredible"], 1.0),
                    (["unexpected", "didn't expect", "shocking"], 0.9),
                    (["wow", "oh", "really", "seriously"], 0.8),
                    (["can't believe", "unbelievable", "never seen"], 0.7)
                ],
                EmotionType.HOPE: [
                    (["hope", "trust", "optimist", "future", "motivated"], 1.0),
                    (["possible", "can do", "better", "change"], 0.8),
                    (["desire", "dream", "expect", "plan"], 0.7),
                    (["forward", "progress", "growth", "develop"], 0.6)
                ]
            }
        }
        
        self.current_state = EmotionalState(
            primary_emotion=EmotionType.NEUTRAL,
            intensity=0.05,
            language="it"
        )
        self.emotional_history = []  # Lista delle emozioni precedenti
        self.emotional_patterns = []
        self.context_emotions = defaultdict(list)
        self.long_term_memory = {
            'last_interaction': time.time(),
            'emotional_baseline': {
                'primary_emotion': EmotionType.NEUTRAL,
                'intensity': 0.05,
                'valence': 0.0
            },
            'common_patterns': [],
            'emotional_triggers': defaultdict(list)
        }
        
    def calculate_emotional_decay(self, time_passed: float) -> float:
        """Calcola il fattore di decadimento basato sul tempo trascorso"""
        if time_passed <= 3600:
            return 0.85  # Decadimento più rapido (era 0.9)
        elif time_passed <= 86400:
            return 0.7  # Decadimento giornaliero
        elif time_passed <= 604800:
            return 0.5  # Decadimento settimanale
        elif time_passed <= 2592000:
            return 0.3  # Decadimento mensile
        elif time_passed <= 31536000:
            return 0.1  # Decadimento annuale
        else:
            return 0.05  # Decadimento massimo (oltre l'anno)

    def process_stimulus(self, text: str, context: Dict = None) -> Emotion:
        """
        Processa uno stimolo testuale e genera un'emozione

        Args:
            text: Testo da analizzare
            context: Contesto opzionale

        Returns:
            Emotion generata
            
        Raises:
            ValueError: se il testo è None
        """
        if text is None:
            raise ValueError("Il testo non può essere None")
            
        # Analizza il testo con spaCy
        doc = self.nlp(text)
        
        # Estrai informazioni rilevanti
        triggers = self._extract_emotional_triggers(doc)
        time_ref = self._extract_time_reference(doc)
        social_context = self._extract_social_context(doc)
        intensity_mods = self._extract_intensity_modifiers(doc)
        
        # Analizza il contenuto emotivo
        emotion_scores = self._analyze_emotional_content(doc)
        
        # Determina l'emozione primaria
        primary_emotion = self._determine_primary_emotion(emotion_scores)
        
        # Trova emozioni secondarie
        secondary_emotions = self._find_secondary_emotions(emotion_scores, primary_emotion)
        
        # Calcola intensità e valenza
        base_intensity = primary_emotion.intensity
        intensity = base_intensity * sum(intensity_mods.values()) if intensity_mods else base_intensity
        valence = 0.5  # Valore neutro di default
        
        # Crea l'oggetto Emotion
        emotion = Emotion(
            primary_emotion=primary_emotion,
            intensity=intensity,
            valence=valence,
            secondary_emotions=[emotion for emotion, _ in secondary_emotions]
        )
        
        # Aggiorna la memoria emotiva
        if context:
            if isinstance(context, dict):
                context_key = str(context)
            else:
                context_key = str(context)
            self.context_emotions[context_key].append(emotion)
            
            # Mantieni solo le ultime 10 emozioni per contesto
            if len(self.context_emotions[context_key]) > 10:
                self.context_emotions[context_key] = self.context_emotions[context_key][-10:]
        
        # Aggiorna i pattern emotivi
        self.update_emotional_patterns(emotion)
        
        # Aggiorna la storia emotiva
        self.emotional_history.append(emotion)
        
        return emotion

    def _extract_emotional_triggers(self, doc) -> List[str]:
        """Estrae i trigger emotivi dal testo"""
        triggers = []
        
        # Cerca eventi o situazioni che causano l'emozione
        for sent in doc.sents:
            for token in sent:
                if token.dep_ in ["nsubj", "dobj"] and not token.is_stop:
                    triggers.append(token.text)
                    
        return triggers
        
    def _extract_time_reference(self, doc) -> str:
        """Estrae riferimenti temporali"""
        time_indicators = {
            "presente": ["ora", "adesso", "oggi"],
            "passato": ["ieri", "prima", "scorso"],
            "futuro": ["domani", "dopo", "prossimo"]
        }
        
        text_lower = doc.text.lower()
        for timeframe, indicators in time_indicators.items():
            if any(ind in text_lower for ind in indicators):
                return timeframe
                
        return "presente"
        
    def _extract_social_context(self, doc) -> Dict[str, Any]:
        """Estrae il contesto sociale"""
        return {
            "personal": any(word in doc.text.lower() for word in ["io", "mi", "il", "la", "che", "di"]),
            "interpersonal": any(word in doc.text.lower() for word in ["tu", "ti", "te", "noi", "ci"]),
            "formal": any(word in doc.text.lower() for word in ["lei", "voi", "loro"])
        }
        
    def _extract_intensity_modifiers(self, doc) -> Dict[str, float]:
        """Estrae modificatori di intensità"""
        intensity_modifiers = {
            "molto": 1.5,
            "poco": 0.5,
            "abbastanza": 0.8,
            "troppo": 2.0,
            "estremamente": 2.0,
            "davvero": 1.5,
            "veramente": 1.5,
            "proprio": 1.2,
            "decisamente": 1.5,
            "incredibilmente": 2.0,
            "assolutamente": 2.0,
            "totalmente": 2.0,
            "completamente": 2.0,
            "un po'": 0.5,
            "leggermente": 0.3,
            "appena": 0.3
        }
        
        modifiers = {}
        for token in doc:
            if token.text.lower() in intensity_modifiers:
                modifiers[token.text.lower()] = intensity_modifiers[token.text.lower()]
                
        return modifiers
        
    def _load_emotional_lexicon(self):
        """Carica il lessico emotivo"""
        self.emotional_lexicon = {
            "it": {
                EmotionType.JOY: ["felice", "contento", "allegr", "gioi", "entusiast"],
                EmotionType.SADNESS: ["triste", "infelice", "depress", "malincon"],
                EmotionType.ANGER: ["arrabbiato", "furioso", "irritato", "nervoso"],
                EmotionType.FEAR: ["spaventato", "impaurito", "terrorizzato", "ansioso"],
                EmotionType.DISGUST: ["disgustato", "nauseato", "schifato"],
                EmotionType.SURPRISE: ["sorpreso", "stupito", "meravigliato"],
                EmotionType.TRUST: ["fiducioso", "sicuro", "tranquillo"],
                EmotionType.ANTICIPATION: ["eccitato", "impaziente", "desideroso"],
                EmotionType.ANXIETY: ["ansioso", "preoccupato", "agitato", "teso"],
                EmotionType.CURIOSITY: ["curioso", "interessato", "affascinato"],
                EmotionType.HOPE: ["sper", "fiduci", "ottimis", "futuro", "motivat"]
            },
            "en": {
                EmotionType.JOY: ["happy", "joyful", "glad", "delighted"],
                EmotionType.SADNESS: ["sad", "unhappy", "depressed", "melancholic"],
                EmotionType.ANGER: ["angry", "furious", "irritated", "nervous"],
                EmotionType.FEAR: ["scared", "frightened", "terrified", "anxious"],
                EmotionType.DISGUST: ["disgusted", "nauseated", "repulsed"],
                EmotionType.SURPRISE: ["surprised", "astonished", "amazed"],
                EmotionType.TRUST: ["trusting", "confident", "secure"],
                EmotionType.ANTICIPATION: ["excited", "eager", "looking forward"],
                EmotionType.ANXIETY: ["anxious", "worried", "nervous", "tense"],
                EmotionType.CURIOSITY: ["curious", "interested", "fascinated"],
                EmotionType.HOPE: ["hope", "trust", "optimist", "future", "motivated"]
            }
        }
        
    def _analyze_emotional_content(self, doc) -> Dict[EmotionType, float]:
        """Analizza il contenuto emotivo del testo"""
        emotion_scores = {emotion: 0.0 for emotion in EmotionType}
        text = doc.text.lower()
        
        # Determina la lingua
        language = "it" if any(word in text for word in ["sono", "mi", "il", "la", "che", "di"]) else "en"
        
        # Analizza il testo per ogni emozione
        for emotion, patterns in self.emotion_patterns[language].items():
            for pattern_list, weight in patterns:
                for pattern in pattern_list:
                    if pattern in text:
                        emotion_scores[emotion] = max(emotion_scores[emotion], weight)
                        
        # Analizza parole chiave specifiche
        for emotion, keywords in self.emotional_lexicon[language].items():
            for keyword in keywords:
                if keyword in text:
                    emotion_scores[emotion] = max(emotion_scores[emotion], 0.8)
                    
        # Analizza congiunzioni avversative per identificare emozioni contrastanti
        contrasts = ["ma", "però", "tuttavia", "nonostante", "sebbene", "anche se"] if language == "it" else \
                   ["but", "however", "although", "despite", "even though", "yet"]
                   
        for contrast in contrasts:
            if contrast in text:
                parts = text.split(contrast)
                if len(parts) == 2:
                    # Analizza separatamente le due parti
                    for part in parts:
                        for emotion, patterns in self.emotion_patterns[language].items():
                            for pattern_list, weight in patterns:
                                for pattern in pattern_list:
                                    if pattern in part:
                                        emotion_scores[emotion] = max(emotion_scores[emotion], weight)
                                        
        # Normalizza i punteggi
        max_score = max(emotion_scores.values(), default=0.0)
        if max_score > 0:
            for emotion in emotion_scores:
                emotion_scores[emotion] = float(emotion_scores[emotion] / max_score)
                
        return emotion_scores
        
    def _determine_primary_emotion(self, emotion_scores: Dict[EmotionType, float]) -> EmotionType:
        """Determina l'emozione primaria"""
        if not emotion_scores:
            return EmotionType.NEUTRAL
            
        # Trova l'emozione con il punteggio più alto
        max_emotion = max(emotion_scores.items(), key=lambda x: x[1])
        
        if max_emotion[1] == 0:
            return EmotionType.NEUTRAL
            
        return max_emotion[0]
        
    def _find_secondary_emotions(self, emotion_scores: Dict[EmotionType, float], 
                               primary_emotion: EmotionType) -> List[Tuple[EmotionType, float]]:
        """Trova emozioni secondarie"""
        secondary_emotions = []
        
        # Ordina le emozioni per punteggio
        sorted_emotions = sorted(
            [(e, s) for e, s in emotion_scores.items() if e != primary_emotion],
            key=lambda x: x[1],
            reverse=True
        )
        
        # Aggiungi le emozioni secondarie con punteggio superiore alla soglia
        threshold = 0.3  # Soglia più bassa per catturare più emozioni secondarie
        for emotion, score in sorted_emotions:
            if score >= threshold:
                secondary_emotions.append((emotion, score))
                
        # Aggiungi emozioni correlate basate su regole
        emotion_relations = {
            EmotionType.ANXIETY: [EmotionType.FEAR, EmotionType.CONFUSION],
            EmotionType.JOY: [EmotionType.HOPE, EmotionType.ENTHUSIASM],
            EmotionType.FEAR: [EmotionType.ANXIETY, EmotionType.CONFUSION],
            EmotionType.SADNESS: [EmotionType.DISAPPOINTMENT, EmotionType.NOSTALGIA],
            EmotionType.ANGER: [EmotionType.FRUSTRATION, EmotionType.DISAPPOINTMENT],
            EmotionType.CURIOSITY: [EmotionType.ANTICIPATION, EmotionType.HOPE],
            EmotionType.SURPRISE: [EmotionType.CURIOSITY, EmotionType.CONFUSION],
            EmotionType.HOPE: [EmotionType.JOY, EmotionType.ANTICIPATION]
        }
        
        if primary_emotion in emotion_relations:
            for related_emotion in emotion_relations[primary_emotion]:
                if related_emotion not in [e[0] for e in secondary_emotions]:
                    secondary_emotions.append((related_emotion, 0.5))
                    
        return secondary_emotions[:3]  # Limita a 3 emozioni secondarie
        
    def _update_emotional_memory(self, emotional_state: EmotionalState):
        """Aggiorna la memoria emotiva"""
        # Aggiungi lo stato emotivo corrente alla memoria
        self.emotional_memory.append(emotional_state)
        
        # Mantieni solo gli ultimi 10 stati emotivi
        if len(self.emotional_memory) > 10:
            self.emotional_memory.pop(0)
            
        # Aggiorna la finestra di contesto
        self.context_window = self.emotional_memory[-3:]  # Mantieni gli ultimi 3 stati
        
    def update(self) -> None:
        """Aggiorna lo stato emotivo applicando il decadimento"""
        if self.current_state.primary_emotion:
            # Calcola il tempo trascorso dall'ultima emozione
            elapsed_time = (datetime.now() - self.current_state.primary_emotion.timestamp).total_seconds()
            
            # Applica il decadimento
            decay_rate = self.calculate_emotional_decay(elapsed_time)
            self.current_state.primary_emotion.valence *= (1 - decay_rate)

    def get_current_state(self) -> EmotionalState:
        """Restituisce lo stato emotivo corrente"""
        # Aggiorna lo stato prima di restituirlo
        self.update()
        return self.current_state

    def process_secondary_emotions(self, primary_emotion: EmotionType, context: Dict) -> List[EmotionType]:
        """Genera emozioni secondarie basate sull'emozione primaria e il contesto"""
        secondary_emotions = []
        
        # Mappatura delle emozioni secondarie comuni
        emotion_mappings = {
            EmotionType.JOY: [EmotionType.GRATITUDE, EmotionType.SERENITY],
            EmotionType.SADNESS: [EmotionType.DISAPPOINTMENT, EmotionType.MELANCHOLY],
            EmotionType.ANGER: [EmotionType.FRUSTRATION, EmotionType.IRRITATION],
            EmotionType.FEAR: [EmotionType.ANXIETY, EmotionType.WORRY],
            EmotionType.SURPRISE: [EmotionType.AMAZEMENT, EmotionType.CONFUSION],
            EmotionType.PRIDE: [EmotionType.SATISFACTION, EmotionType.CONFIDENCE],
            EmotionType.NEUTRAL: []
        }
        
        # Aggiungi emozioni secondarie basate sul contesto
        if primary_emotion in emotion_mappings:
            secondary_emotions.extend(emotion_mappings[primary_emotion])
            
        # Filtra le emozioni in base al contesto
        context_valence = context.get('sentiment', 0.5)
        secondary_emotions = [e for e in secondary_emotions if self._is_emotion_compatible(e, context_valence)]
        
        return secondary_emotions
        
    def _is_emotion_compatible(self, emotion: EmotionType, context_valence: float) -> bool:
        """Verifica se un'emozione è compatibile con la valenza del contesto"""
        positive_emotions = {EmotionType.GRATITUDE, EmotionType.SERENITY, EmotionType.SATISFACTION, 
                           EmotionType.CONFIDENCE, EmotionType.AMAZEMENT}
        negative_emotions = {EmotionType.DISAPPOINTMENT, EmotionType.MELANCHOLY, EmotionType.FRUSTRATION,
                           EmotionType.IRRITATION, EmotionType.ANXIETY, EmotionType.WORRY}
        
        if emotion in positive_emotions and context_valence > 0.5:
            return True
        if emotion in negative_emotions and context_valence < 0.5:
            return True
        return False

    def get_adaptation_state(self) -> Dict[str, float]:
        """
        Restituisce lo stato di adattamento del sistema emotivo
        
        Returns:
            Dizionario con le metriche di adattamento
        """
        current_time = time.time()
        time_since_last = current_time - self.long_term_memory['last_interaction']
        
        # Calcola la sensibilità basata sul tempo trascorso dall'ultima interazione
        sensitivity = 1.0 / (1.0 + 0.1 * time_since_last)
        
        # Ottieni l'ultima emozione dalla storia
        last_emotion = self.emotional_history[-1] if self.emotional_history else None
        current_intensity = last_emotion.intensity if last_emotion else 0.0
        current_valence = last_emotion.valence if last_emotion else 0.0
        
        return {
            'sensitivity': sensitivity,
            'current_intensity': current_intensity,
            'current_valence': current_valence,
            'time_since_last_interaction': time_since_last
        }

    def detect_emotional_blend(self, emotions: List[Emotion]) -> Optional[List[Tuple[EmotionType, float]]]:
        """Rileva miscele di emozioni e le loro intensità relative"""
        if not emotions:
            return None
            
        # Calcola l'intensità totale per normalizzazione
        total_intensity = sum(e.intensity for e in emotions)
        if total_intensity == 0:
            return []
            
        # Calcola le intensità relative
        blend = [(e.primary_emotion, e.intensity / total_intensity) for e in emotions]
        
        # Ordina per intensità decrescente
        return sorted(blend, key=lambda x: x[1], reverse=True)
        
    def update_emotional_patterns(self, new_emotion: Emotion):
        """Aggiorna i pattern emotivi basati sulla nuova emozione"""
        self.emotional_history.append(new_emotion)
        
        # Mantieni solo le ultime 10 emozioni per l'analisi dei pattern
        if len(self.emotional_history) > 10:
            self.emotional_history = self.emotional_history[-10:]
            
        # Cerca pattern esistenti
        for pattern in self.emotional_patterns:
            if pattern.matches(self.emotional_history[-len(pattern.emotions):]):
                pattern.frequency += 1
                pattern.last_occurrence = datetime.now()
                return
                
        # Crea nuovi pattern per sequenze di 2-4 emozioni
        for length in range(2, 5):
            if len(self.emotional_history) >= length:
                new_pattern = EmotionalPattern(
                    emotions=self.emotional_history[-length:],
                    context=self.current_state.context if hasattr(self.current_state, 'context') else None
                )
                self.emotional_patterns.append(new_pattern)
                
@dataclass
class EmotionalStateVAD:
    """Stato emotivo con valence (positivo/negativo), arousal (attivazione) e dominance (controllo)"""
    valence: float = 0.0    # Range: [-1, 1]
    arousal: float = 0.0    # Range: [0, 1]
    dominance: float = 0.5  # Range: [0, 1]
