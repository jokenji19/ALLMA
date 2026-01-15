"""
Sistema Linguistico Principale di ALLMA
Integra i sistemi di comprensione e risposta
"""

from typing import Dict, List, Optional
from .understanding_system import AdvancedUnderstandingSystem, UnderstandingResult
from .response_system import AdvancedResponseSystem, GeneratedResponse, ResponseStyle

class LanguageSystem:
    """Sistema principale per la comprensione e generazione del linguaggio."""
    
    def __init__(self):
        self.understanding = AdvancedUnderstandingSystem()
        self.response = AdvancedResponseSystem()
        self.context = {
            'keywords': set(),
            'entities': {},
            'emotional_tone': None,
            'current_topic': None
        }
        self.knowledge = {
            'concepts': set(),
            'relations': set(),
            'patterns': set()
        }
    
    def process_input(self, text: str) -> GeneratedResponse:
        """Processa un input testuale e genera una risposta."""
        # Comprendi l'input
        understanding = self.understanding.understand(
            text,
            self.context
        )
        
        # Genera una risposta
        response = self.response.generate(
            understanding,
            self.context,
            self.knowledge
        )
        
        # Aggiorna il contesto
        if isinstance(response.context, dict):
            # Mantieni le parole chiave esistenti
            if 'keywords' in self.context:
                response.context['keywords'].update(self.context['keywords'])
            # Aggiorna il contesto
            self.context = response.context
        
        # Aggiorna la conoscenza
        if isinstance(response.learning_points, dict):
            # Mantieni i concetti esistenti
            if 'concepts' in self.knowledge:
                response.learning_points['concepts'].update(self.knowledge['concepts'])
            # Aggiorna la conoscenza
            self.knowledge = response.learning_points
        
        # Aggiungi le nuove parole apprese ai concetti
        if understanding.new_words:
            if 'concepts' not in self.knowledge:
                self.knowledge['concepts'] = set()
            for word in understanding.new_words:
                self.knowledge['concepts'].add(word.lower())
        
        return response

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
