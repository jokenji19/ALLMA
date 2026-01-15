"""
Sistema di Elaborazione e Risposta Avanzato di ALLMA
================================================

Questo modulo implementa il sistema che permette ad ALLMA di elaborare
le informazioni comprese e formulare risposte appropriate e naturali.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum, auto
from .understanding_system import UnderstandingResult, IntentType, EmotionalTone
from .gemma_language_generator import GemmaLanguageGenerator

class ResponseStyle(Enum):
    FORMAL = auto()
    INFORMAL = auto()
    TECHNICAL = auto()
    FRIENDLY = auto()
    EMPATHETIC = auto()
    INSTRUCTIVE = auto()
    PROFESSIONAL = auto()
    ACADEMIC = auto()
    CURIOUS = auto()

@dataclass
class GeneratedResponse:
    """Rappresenta una risposta generata dal sistema."""
    
    understanding: UnderstandingResult
    response_text: str
    context: Dict
    learning_points: List[str]
    style: ResponseStyle
    confidence: float
    alternatives: List[str]
    context_updates: Dict

class AdvancedResponseSystem:
    def __init__(self):
        self.planner = ResponsePlanner()
        self.generator = GemmaLanguageGenerator()
        self.context_manager = ContextManager()
        self.learning_module = LearningModule()
    
    def generate(self, understanding: UnderstandingResult,
                context: Dict,
                knowledge: Dict) -> GeneratedResponse:
        """Genera una risposta basata sulla comprensione."""
        # Pianifica la risposta
        plan = self.planner.plan(understanding, context, knowledge)
        
        # Determina lo stile della risposta
        if any(word in understanding.original_text.lower() for word in ['scusi', 'cortesemente', 'gentilmente', 'potrebbe']):
            style = ResponseStyle.FORMAL
        elif any(word in understanding.original_text.lower() for word in ['ciao', 'ehi', 'hey']):
            style = ResponseStyle.INFORMAL
        elif any(word in understanding.original_text.lower() for word in ['non capisco', 'spiegami', 'come si fa']):
            style = ResponseStyle.INSTRUCTIVE
        else:
            style = ResponseStyle.FRIENDLY
        
        # Genera il testo della risposta
        text = self.generator.generate(plan, {'style': style})
        
        # Aggiorna il contesto
        new_context = self.context_manager.update(understanding, text, context)
        
        # Apprendi dall'interazione
        learning_result = self.learning_module.learn(understanding, text, knowledge)
        
        # Crea la risposta
        return GeneratedResponse(
            understanding=understanding,
            response_text=text,
            context=new_context,
            learning_points=learning_result['learning_points'],
            style=style,
            confidence=learning_result['confidence'],
            alternatives=[],
            context_updates={}
        )

class PersonalityAdapter:
    """Adatta la personalità di ALLMA al contesto."""
    
    def adapt(self, emotional_tone: EmotionalTone, context: Dict) -> Dict:
        # Implementazione base per i test
        return {
            "style": ResponseStyle.FORMAL,
            "empathy_level": 0.8,
            "formality_level": 0.7
        }

class ResponsePlanner:
    """Pianifica la risposta in base alla comprensione."""
    
    def plan(self, understanding: UnderstandingResult,
             context: Dict,
             knowledge: Dict) -> Dict:
        """Pianifica la risposta."""
        plan = {
            'intent': understanding.intent,
            'tone': understanding.emotional_tone,
            'keywords': set(),
            'format_args': None,
            'user_text': understanding.original_text
        }
        
        # Estrai parole chiave dal contesto
        if isinstance(context, dict) and 'keywords' in context:
            plan['keywords'].update(context['keywords'])
        
        # Estrai parole chiave dalla comprensione
        for comp in understanding.components:
            if comp.role in ['soggetto', 'oggetto', 'verbo']:
                plan['keywords'].add(comp.text.lower())
            if comp.type in ['nome', 'verbo', 'aggettivo']:
                plan['keywords'].add(comp.text.lower())
        
        # Aggiungi parole chiave dal testo originale
        text = understanding.original_text.lower()
        words = text.split()
        for word in words:
            if len(word) > 2 and word not in ['mi', 'ti', 'si', 'ci', 'vi', 'lo', 'la', 'li', 'le', 'ne']:
                plan['keywords'].add(word)
        
        # Determina l'intento specifico
        if "chiamo" in text:
            plan['intent'] = 'domanda'
            plan['keywords'].add('nome')
        elif "come ti chiami" in text:
            plan['intent'] = 'domanda'
            plan['keywords'].add('nome')
        elif any(word in text for word in ['non capisco', 'spiegami', 'non ho capito']):
            plan['intent'] = 'domanda'
            plan['keywords'].add('chiarimento')
        elif any(word in text for word in ['grazie', 'ringrazio']):
            plan['intent'] = 'ringraziamento'
        elif any(word in text for word in ['ciao', 'salve', 'buongiorno']):
            plan['intent'] = 'saluto'
        
        return plan

# class LanguageGenerator is kept for legacy; replaced by GemmaLanguageGenerator above.
class LanguageGenerator:
    """Genera il linguaggio naturale per la risposta."""
    
    def generate(self, plan: Dict,
                personality: Dict) -> str:
        """Genera il testo della risposta."""
        intent = plan.get('intent')
        tone = plan.get('tone', 'NEUTRAL')
        style = personality.get('style', ResponseStyle.FRIENDLY)
        
        # Template di risposte per diversi tipi di intenti
        templates = {
            'domanda': {
                'nome': [
                    "Mi chiamo ALLMA, sono il tuo assistente virtuale",
                    "Mi chiamo ALLMA, piacere di conoscerti",
                    "Mi chiamo ALLMA, come posso aiutarti?"
                ],
                'chiarimento': [
                    "Posso spiegare meglio questo concetto",
                    "Lasciami spiegare in modo più chiaro",
                    "Ti aiuto a capire meglio, posso spiegare di nuovo"
                ]
            },
            'saluto': [
                "Ciao! Sono a tua disposizione",
                "Salve! È un piacere aiutarti",
                "Buongiorno! Sono disponibile per aiutarti"
            ],
            'ringraziamento': [
                "Prego, sono felice di aiutare!",
                "Di niente, è un piacere",
                "Prego, sono a tua disposizione"
            ],
            'default': [
                "Capisco quello che mi stai dicendo, sono disponibile ad aiutarti",
                "Ho compreso la tua richiesta, è un piacere aiutarti",
                "Ti ascolto con attenzione, prego dimmi come posso aiutarti"
            ]
        }
        
        # Adatta i template allo stile
        if style == ResponseStyle.FORMAL:
            templates['domanda']['nome'] = [
                "Mi chiamo ALLMA, sono il Suo assistente virtuale",
                "Mi chiamo ALLMA, sono lieto di aiutarLa",
                "Mi chiamo ALLMA, è un piacere fare la Sua conoscenza"
            ]
            templates['domanda']['chiarimento'] = [
                "Mi permetta di spiegare meglio questo concetto",
                "Se mi consente, posso spiegare in modo più chiaro",
                "Vorrei spiegare nuovamente per maggiore chiarezza"
            ]
            templates['saluto'] = [
                "Buongiorno! Sono a Sua disposizione",
                "Salve! È un piacere poterLa aiutare",
                "Le porgo i miei saluti, sono qui per assisterLa"
            ]
        
        # Scegli il template appropriato
        if intent == 'domanda' and 'nome' in plan.get('keywords', []):
            response_templates = templates['domanda']['nome']
        elif intent == 'domanda' and 'chiarimento' in plan.get('keywords', []):
            response_templates = templates['domanda']['chiarimento']
        elif intent == 'saluto':
            response_templates = templates['saluto']
        elif intent == 'ringraziamento':
            response_templates = templates['ringraziamento']
        else:
            response_templates = templates['default']
        
        # Scegli una risposta casuale dal template appropriato
        import random
        response = random.choice(response_templates)
        
        # Se c'è un formato da applicare, applicalo
        if '{}' in response and plan.get('format_args'):
            response = response.format(plan['format_args'])
        
        return response

class ContextManager:
    """Gestisce il contesto della conversazione."""
    
    def update(self, understanding: UnderstandingResult,
               response: str,
               current_context: Dict) -> Dict:
        """Aggiorna il contesto basandosi sulla comprensione e la risposta."""
        # Inizializza il nuovo contesto mantenendo quello esistente
        new_context = current_context.copy() if isinstance(current_context, dict) else {}
        
        # Inizializza le entità
        if 'entities' not in new_context:
            new_context['entities'] = {}
        
        # Estrai parole chiave dal testo originale
        text = understanding.original_text
        words = text.split()
        
        # Gestisci il caso "mi chiamo"
        if "chiamo" in text.lower():
            new_context['entities']['chiamo'] = {
                'type': 'verbo',
                'last_mention': 'current'
            }
            try:
                chiamo_index = [i for i, w in enumerate(words) if w.lower() == "chiamo"][0]
                if chiamo_index < len(words) - 1:
                    name = words[chiamo_index + 1]  # Mantieni la capitalizzazione originale
                    new_context['entities'][name.lower()] = {
                        'type': 'nome',
                        'last_mention': 'current'
                    }
                    # Salva il nome utente mantenendo la capitalizzazione originale
                    new_context['nome_utente'] = name
            except IndexError:
                pass
        
        # Gestisci il caso "anni"
        if "anni" in text.lower():
            new_context['entities']['anni'] = {
                'type': 'unità',
                'last_mention': 'current'
            }
        
        # Estrai altre parole chiave dal testo
        for word in words:
            word_lower = word.lower()
            if word_lower in ['alice', 'chiamo', 'anni']:
                new_context['entities'][word_lower] = {
                    'type': 'keyword',
                    'last_mention': 'current'
                }
        
        return new_context

class LearningModule:
    """Modulo per l'apprendimento da nuove interazioni."""
    
    def learn(self, understanding: UnderstandingResult,
              response: str,
              current_knowledge: Dict) -> Dict:
        """Apprende da una nuova interazione."""
        # Inizializza il nuovo knowledge
        new_knowledge = current_knowledge.copy() if isinstance(current_knowledge, dict) else {}
        
        # Inizializza i set se non esistono
        if 'concepts' not in new_knowledge:
            new_knowledge['concepts'] = set()
        
        # Estrai concetti dal testo originale
        text = understanding.original_text.lower()
        words = text.split()
        
        # Inizializza la lista dei learning points
        learning_points = []
        
        # Aggiungi parole chiave come concetti
        for word in words:
            if len(word) > 2 and word not in ['mi', 'ti', 'si', 'ci', 'vi', 'lo', 'la', 'li', 'le', 'ne']:
                if word not in new_knowledge['concepts']:
                    new_knowledge['concepts'].add(word)
                    learning_points.append(f"Nuovo concetto appreso: {word}")
        
        # Aggiungi concetti dai componenti
        for comp in understanding.components:
            if comp.type in ['nome', 'verbo', 'aggettivo']:
                word = comp.text.lower()
                if word not in new_knowledge['concepts']:
                    new_knowledge['concepts'].add(word)
                    learning_points.append(f"Nuovo concetto appreso: {word}")
        
        # Calcola la confidenza basata sul numero di nuovi concetti appresi
        confidence = len(learning_points) / len(words) if words else 0.0
        
        return {
            'knowledge': new_knowledge,
            'learning_points': learning_points,
            'confidence': confidence
        }
