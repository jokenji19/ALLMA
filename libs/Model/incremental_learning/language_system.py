"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file implements the Language Processing System of ALLMA.
Author: Cristof Bano
Created: January 2025

This file contains proprietary and patent-pending technologies including:
- Multi-language support
- Natural language understanding
- Context-aware responses
- Adaptive communication patterns
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Optional, List, Set, Any
import locale
import json
import spacy

class ResponseStyle(Enum):
    FORMAL = 1
    INFORMAL = 2
    INSTRUCTIVE = 3
    FRIENDLY = 4

@dataclass
class GrammaticalComponent:
    """Componente grammaticale di una frase"""
    text: str
    role: str  # soggetto, verbo, oggetto, etc.
    type: str   # tipo di parola
    position: int   # posizione della parola nella frase

@dataclass
class Understanding:
    """Comprensione di una frase"""
    components: List[GrammaticalComponent]
    intent: str
    entities: Dict[str, Any]
    sentiment: float
    confidence: float

@dataclass
class GeneratedResponse:
    """Risposta generata dal sistema"""
    understanding: Understanding
    response_text: str
    context: Dict
    learning_points: List[str]
    style: ResponseStyle
    confidence: float
    alternatives: List[str]
    context_updates: Dict

@dataclass
class LanguageVariant:
    """Classe per gestire le varianti regionali di una lingua"""
    region: str
    dialect: str = ""
    idioms: Dict[str, str] = field(default_factory=dict)
    cultural_references: Dict[str, str] = field(default_factory=dict)

@dataclass 
class LanguageContext:
    """Classe per gestire il contesto culturale e linguistico"""
    formal_style: bool
    honorifics: bool
    datetime_format: str
    number_format: str
    variants: Dict[str, LanguageVariant] = field(default_factory=dict)
    translation_memory: Dict[str, Dict[str, str]] = field(default_factory=dict)
    learning_rate: float = 0.1

    def add_translation(self, source: str, target: str, quality: float = 1.0):
        """Aggiunge una nuova traduzione alla memoria"""
        if source not in self.translation_memory:
            self.translation_memory[source] = {}
        
        # Aggiorna la traduzione esistente con learning rate
        if target in self.translation_memory[source]:
            current_quality = self.translation_memory[source][target]
            new_quality = current_quality * (1 - self.learning_rate) + quality * self.learning_rate
            self.translation_memory[source][target] = new_quality
        else:
            self.translation_memory[source][target] = quality

    def get_best_translation(self, text: str) -> Optional[str]:
        """Ottiene la migliore traduzione disponibile"""
        if text not in self.translation_memory:
            return None
            
        translations = self.translation_memory[text]
        if not translations:
            return None
            
        return max(translations.items(), key=lambda x: x[1])[0]

class LanguageSystem:
    def __init__(self):
        self.nlp = spacy.load("it_core_news_sm")
        self.initialize_language()
        
        # Inizializza il contesto
        self.context = {
            'keywords': set(),
            'entities': {},
            'emotional_tone': None,
            'current_topic': None,
            'nome_utente': None
        }

    def get_device_system_language(self) -> str:
        """Ottiene la lingua del sistema operativo e la regione"""
        try:
            locale_info = locale.getdefaultlocale()[0]
            lang_code, region_code = locale_info.split('_')
            return lang_code.lower(), region_code.upper()
        except:
            return "en", "US"  # Fallback to US English

    def initialize_language(self) -> None:
        """Inizializza la lingua del sistema"""
        lang_code, region_code = self.get_device_system_language()
        self.set_language(lang_code, region_code)

    def set_language(self, lang_code: str, region_code: str = None) -> None:
        """Imposta la lingua corrente e la variante regionale"""
        if lang_code in self.available_languages:
            self.current_language = self.available_languages[lang_code]
            
            # Imposta la variante regionale se disponibile
            if region_code and region_code in self.current_language["context"].variants:
                self.current_variant = self.current_language["context"].variants[region_code]
            else:
                # Usa la prima variante disponibile come fallback
                first_region = next(iter(self.current_language["context"].variants))
                self.current_variant = self.current_language["context"].variants[first_region]
        else:
            self.current_language = self.available_languages["en"]
            self.current_variant = self.current_language["context"].variants["US"]

    def process_input(self, text: str) -> GeneratedResponse:
        """Elabora l'input dell'utente e genera una risposta."""
        doc = self.nlp(text)
        
        # Debug spaCy dettagliato
        print("\nAnalisi spaCy dettagliata:")
        for token in doc:
            print(f"\nToken: {token.text}")
            print(f"  POS: {token.pos_}")
            print(f"  DEP: {token.dep_}")
            print(f"  HEAD: {token.head.text}")
            print(f"  LEMMA: {token.lemma_}")
            print(f"  SHAPE: {token.shape_}")
            print(f"  TAG: {token.tag_}")
            print(f"  IS_STOP: {token.is_stop}")
            print(f"  IS_PUNCT: {token.is_punct}")
            print(f"  IS_SPACE: {token.is_space}")
            print(f"  IS_ALPHA: {token.is_alpha}")
            print(f"  IS_DIGIT: {token.is_digit}")
            print(f"  LIKE_NUM: {token.like_num}")
            print(f"  LIKE_URL: {token.like_url}")
            print(f"  LIKE_EMAIL: {token.like_email}")
            print(f"  IS_OOV: {token.is_oov}")
            print(f"  CHILDREN: {[child.text for child in token.children]}")
            print(f"  Role assegnato: {self._get_grammatical_role(token)}")
        
        # Analisi della frase
        components = []
        for token in doc:
            role = self._get_grammatical_role(token)
            comp = GrammaticalComponent(
                text=token.text,
                role=role,
                type=token.pos_,
                position=token.i
            )
            components.append(comp)
        
        # Rileva l'intento
        intent = self._detect_intent(doc)
        
        # Analizza il sentiment
        sentiment = self._analyze_sentiment(doc)
        
        # Crea l'oggetto Understanding
        understanding = Understanding(
            components=components,
            intent=intent,
            sentiment=sentiment,
            entities=self._extract_entities(doc),
            confidence=0.8
        )
        
        # Aggiorna il contesto
        self._update_context(understanding)
        
        # Genera la risposta
        response_text, style = self._generate_response(understanding)
        
        # Identifica i punti di apprendimento
        learning_points = self._identify_learning_points(understanding)
        
        # Crea e restituisci la risposta
        return GeneratedResponse(
            understanding=understanding,
            response_text=response_text,
            context=self.context,
            learning_points=learning_points,
            style=style,
            confidence=0.8,
            alternatives=[],
            context_updates={}
        )

    def _get_grammatical_role(self, token) -> str:
        """Determina il ruolo grammaticale di un token"""
        # Caso speciale per "Mi chiamo X"
        if token.text.lower() == "mi":
            return "soggetto"
        if token.text.lower() == "chiamo" or token.pos_ == "VERB":
            return "verbo"
        if token.pos_ == "PROPN" or token.pos_ == "NOUN":
            return "nome"
            
        # Mappatura per altri casi
        dep_mapping = {
            'nsubj': 'soggetto',
            'ROOT': 'verbo',
            'obj': 'oggetto',
            'amod': 'attributo'
        }
        
        pos_mapping = {
            'ADJ': 'attributo',
            'ADV': 'avverbio',
            'ADP': 'preposizione',
            'DET': 'articolo',
            'PRON': 'pronome'
        }
        
        # Prima prova con la dipendenza sintattica
        if token.dep_ in dep_mapping:
            return dep_mapping[token.dep_]
            
        # Poi con il part-of-speech
        if token.pos_ in pos_mapping:
            return pos_mapping[token.pos_]
            
        return "altro"

    def _detect_intent(self, doc) -> str:
        """Rileva l'intento della frase"""
        text = doc.text.lower()
        
        # Verifica se è una presentazione
        if "mi chiamo" in text or "sono" in text:
            return "introduction"
            
        # Verifica se è un saluto
        if any(token.text.lower() in ["ciao", "salve", "hey"] for token in doc):
            return "greeting"
            
        # Verifica se è un ringraziamento
        elif any(token.text.lower() in ["grazie", "prego"] for token in doc):
            return "gratitude"
            
        # Verifica se è una domanda
        elif any(token.text.lower() in ["come", "perché", "quando", "dove"] for token in doc) or doc[0].text.lower() in ["come", "perché", "quando", "dove"]:
            return "question"
            
        # Verifica se è un'azione
        elif any(token.dep_ == "ROOT" and token.pos_ == "VERB" for token in doc):
            return "action"
            
        else:
            return "statement"

    def _extract_entities(self, doc) -> Dict:
        """Estrae le entità dal testo"""
        entities = {}
        for ent in doc.ents:
            entities[ent.text.lower()] = {
                'type': ent.label_,
                'last_mention': 'current'
            }
        
        # Estrai anche parole chiave che potrebbero essere entità
        for token in doc:
            if token.pos_ in ["NOUN", "PROPN"]:
                entities[token.text.lower()] = {
                    'type': token.pos_.lower(),
                    'last_mention': 'current'
                }
                
        return entities

    def _update_context(self, understanding: Understanding):
        """Aggiorna il contesto con le nuove informazioni"""
        # Aggiorna le entità nel contesto
        self.context["entities"].update(understanding.entities)
        
        # Aggiorna le parole chiave
        for comp in understanding.components:
            if comp.role in ["soggetto", "oggetto", "nome"]:
                self.context["keywords"].add(comp.text.lower())
        
        # Aggiorna il tono emotivo
        if abs(understanding.sentiment) > 0.3:
            self.context["emotional_tone"] = "positive" if understanding.sentiment > 0 else "negative"
            
        # Gestisci le presentazioni
        if understanding.intent == "introduction":
            text = " ".join(comp.text.lower() for comp in understanding.components)
            if "mi chiamo" in text:
                for i, comp in enumerate(understanding.components):
                    if comp.text.lower() == "chiamo" and i+1 < len(understanding.components):
                        self.context["nome_utente"] = understanding.components[i+1].text
            elif "sono" in text:
                for i, comp in enumerate(understanding.components):
                    if comp.text.lower() == "sono" and i+1 < len(understanding.components):
                        self.context["nome_utente"] = understanding.components[i+1].text

    def _generate_response(self, understanding: Understanding) -> tuple[str, ResponseStyle]:
        """Genera una risposta appropriata"""
        if understanding.intent == "introduction":
            if self.context["nome_utente"]:
                return f"Piacere di conoscerti, {self.context['nome_utente']}!", ResponseStyle.FORMAL
            return "Piacere di conoscerti!", ResponseStyle.FORMAL
            
        elif understanding.intent == "greeting":
            return "Ciao! Come posso aiutarti?", ResponseStyle.INFORMAL
            
        elif understanding.intent == "gratitude":
            return "Prego!", ResponseStyle.INFORMAL
            
        elif understanding.intent == "question":
            if "come ti chiami" in " ".join(comp.text.lower() for comp in understanding.components):
                return "Mi chiamo ALLMA, sono il tuo assistente!", ResponseStyle.FORMAL
            return self._generate_question_response(understanding), ResponseStyle.FORMAL
            
        elif understanding.intent == "action":
            return self._generate_action_response(understanding), ResponseStyle.INSTRUCTIVE
            
        else:
            return self._generate_statement_response(understanding), ResponseStyle.FORMAL

    def _identify_learning_points(self, understanding: Understanding) -> List[str]:
        """Identifica i punti di apprendimento dall'interazione"""
        learning_points = []
        
        # Apprendi nuovi concetti
        for comp in understanding.components:
            if comp.role in ["soggetto", "oggetto", "nome"]:
                concept = comp.text.lower()
                if concept not in ["mi", "tu", "lui", "lei", "noi", "voi", "loro", "allma"]:
                    learning_points.append(f"Nuovo concetto appreso: {concept}")
                    # Aggiungi alla memoria
                    self.context["keywords"].add(concept)
        
        # Apprendi relazioni
        for i, comp in enumerate(understanding.components[:-1]):
            if comp.role == "soggetto" and understanding.components[i+1].role == "verbo":
                relation = f"{comp.text} -> {understanding.components[i+1].text}"
                learning_points.append(f"Nuova relazione: {relation}")
        
        # Apprendi pattern
        pattern = " ".join(comp.role for comp in understanding.components)
        learning_points.append(f"Nuovo pattern grammaticale: {pattern}")
        
        return learning_points

    def _generate_question_response(self, understanding: Understanding) -> str:
        """Genera una risposta per una domanda"""
        # Implementazione semplificata
        return "Mi dispiace, non so rispondere a questa domanda."

    def _generate_action_response(self, understanding: Understanding) -> str:
        """Genera una risposta per un'azione"""
        verb = next((comp.text for comp in understanding.components if comp.role == "verbo"), None)
        if verb:
            return f"Capisco che vuoi {verb}. Posso aiutarti con questo.", ResponseStyle.INSTRUCTIVE
        return "Non ho capito cosa vuoi fare", ResponseStyle.FORMAL

    def _generate_statement_response(self, understanding: Understanding) -> str:
        """Genera una risposta per un'affermazione"""
        subject = next((comp.text for comp in understanding.components if comp.role == "soggetto"), None)
        if subject:
            return f"Ho capito che stai parlando di {subject}."
        return "Capisco quello che dici."

    def translate(self, text: str, target_lang: str, source_lang: str = None) -> str:
        """Traduce il testo nella lingua target"""
        if not source_lang:
            source_lang = list(self.available_languages.keys())[
                list(self.available_languages.values()).index(self.current_language)
            ]
            
        if target_lang not in self.available_languages:
            return text
            
        # Prova a ottenere una traduzione dalla memoria
        target_context = self.available_languages[target_lang]["context"]
        translation = target_context.get_best_translation(text)
        
        if translation:
            return translation
            
        # In una implementazione reale, qui si userebbe un servizio di traduzione
        # Per ora restituiamo il testo originale
        return text

    def get_response(self, key: str, **kwargs) -> str:
        """Ottiene una risposta nella lingua corrente"""
        responses = {
            "it": {
                "greeting": "Ciao! Come posso aiutarti oggi?",
                "farewell": "Arrivederci! A presto!",
                "error": "Mi dispiace, si è verificato un errore."
            },
            "en": {
                "greeting": "Hi! How can I help you today?",
                "farewell": "Goodbye! See you soon!",
                "error": "I'm sorry, an error occurred."
            },
            "es": {
                "greeting": "¡Hola! ¿Cómo puedo ayudarte hoy?",
                "farewell": "¡Adiós! ¡Hasta pronto!",
                "error": "Lo siento, ha ocurrido un error."
            }
        }
        
        lang_code = list(self.available_languages.keys())[
            list(self.available_languages.values()).index(self.current_language)
        ]
        
        response = responses[lang_code].get(key, responses["en"][key])
        
        # Applica idiomi e riferimenti culturali della variante corrente
        if self.current_variant:
            for idiom, translation in self.current_variant.idioms.items():
                if idiom in response:
                    response = response.replace(idiom, translation)
                    
        return response

    def format_response(self, response: str, context: Dict) -> str:
        """Formatta la risposta in base al contesto culturale e linguistico"""
        if self.current_language["context"].formal_style:
            # Aggiunge formalità se necessario
            response = response.replace("tu", "Lei")
            response = response.replace("tuo", "Suo")
        
        # Applica il formato data/ora corretto
        if "{date}" in response:
            from datetime import datetime
            date_format = self.current_language["context"].datetime_format
            response = response.replace("{date}", datetime.now().strftime(date_format))
            
        # Applica il formato numerico corretto
        if "{number}" in context:
            if self.current_language["context"].number_format == "EU":
                context["number"] = str(context["number"]).replace(".", ",")
            
        return response.format(**context)

    def learn_from_feedback(self, original_text: str, improved_text: str, quality: float):
        """Apprende dalle correzioni e feedback degli utenti"""
        lang_code = list(self.available_languages.keys())[
            list(self.available_languages.values()).index(self.current_language)
        ]
        
        context = self.current_language["context"]
        context.add_translation(original_text, improved_text, quality)

    def _analyze_sentiment(self, doc) -> float:
        """
        Analizza il sentimento del testo usando regole semplici.
        Restituisce un valore tra 0 (molto negativo) e 1 (molto positivo).
        """
        # Dizionario di parole positive e negative con i loro pesi
        positive_words = {
            'bello': 0.8, 'buono': 0.7, 'ottimo': 0.9, 'fantastico': 1.0,
            'eccellente': 0.9, 'piacere': 0.7, 'grazie': 0.6, 'felice': 0.8,
            'contento': 0.7, 'bravo': 0.7, 'gentile': 0.6, 'caro': 0.5,
            'perfetto': 0.9, 'magnifico': 0.9, 'stupendo': 0.9,
            'sì': 0.6, 'ok': 0.6, 'certo': 0.6
        }
        
        negative_words = {
            'brutto': -0.8, 'cattivo': -0.7, 'pessimo': -0.9, 'terribile': -1.0,
            'orribile': -0.9, 'male': -0.7, 'no': -0.6, 'mai': -0.5,
            'triste': -0.7, 'arrabbiato': -0.8, 'deluso': -0.7, 'difficile': -0.5,
            'impossibile': -0.8, 'sbagliato': -0.7, 'errore': -0.6,
            'problema': -0.5, 'non': -0.4
        }
        
        # Calcola il sentimento
        sentiment = 0.5  # Valore neutro di default
        word_count = 0
        
        for token in doc:
            word = token.text.lower()
            if word in positive_words:
                sentiment += positive_words[word]
                word_count += 1
            elif word in negative_words:
                sentiment += negative_words[word]
                word_count += 1
                
        # Se abbiamo trovato parole con sentimento, calcola la media
        if word_count > 0:
            sentiment = (sentiment + 0.5 * word_count) / (word_count + 1)
            
        # Assicurati che il valore sia tra 0 e 1
        return max(0.0, min(1.0, sentiment))

    available_languages = {
        "it": {
            "name": "Italiano",
            "context": LanguageContext(
                formal_style=True,
                honorifics=False,
                datetime_format="%d/%m/%Y",
                number_format="EU",
                variants={
                    "IT": LanguageVariant(
                        region="Italia",
                        dialect="Standard",
                        idioms={
                            "in bocca al lupo": "good luck",
                            "non avere peli sulla lingua": "to be outspoken"
                        }
                    ),
                    "CH": LanguageVariant(
                        region="Svizzera",
                        dialect="Ticinese",
                        idioms={
                            "non avere peli sulla lingua": "to speak frankly"
                        }
                    )
                }
            )
        },
        "en": {
            "name": "English",
            "context": LanguageContext(
                formal_style=False,
                honorifics=False,
                datetime_format="%m/%d/%Y",
                number_format="US",
                variants={
                    "US": LanguageVariant(
                        region="United States",
                        dialect="American",
                        idioms={
                            "break a leg": "good luck",
                            "speak your mind": "to be outspoken"
                        }
                    ),
                    "GB": LanguageVariant(
                        region="United Kingdom",
                        dialect="British",
                        idioms={
                            "break a leg": "good luck",
                            "speak your mind": "to be frank"
                        }
                    )
                }
            )
        },
        "es": {
            "name": "Español",
            "context": LanguageContext(
                formal_style=True,
                honorifics=True,
                datetime_format="%d/%m/%Y",
                number_format="EU",
                variants={
                    "ES": LanguageVariant(
                        region="España",
                        dialect="Castellano",
                        idioms={
                            "mucha mierda": "good luck",
                            "sin pelos en la lengua": "to be outspoken"
                        }
                    ),
                    "MX": LanguageVariant(
                        region="México",
                        dialect="Mexicano",
                        idioms={
                            "suerte": "good luck",
                            "hablar sin rodeos": "to be frank"
                        }
                    )
                }
            )
        }
    }
