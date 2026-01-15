"""
Sistema di Integrazione della Conoscenza di ALLMA
=============================================

Questo modulo integra:
1. La conoscenza base della lingua (base_knowledge.py)
2. Il vocabolario essenziale (essential_vocabulary.py)
3. Il sistema di comprensione (understanding_system.py)
4. Il sistema di risposta (response_system.py)
"""

from typing import Dict, List, Set, Optional, Union, Any
from dataclasses import dataclass
import importlib

# Importiamo tutti i componenti
from ..data.vocabulary.base_knowledge import (
    BASIC_SENTENCE_PATTERNS,
    GRAMMAR_RULES,
    BASIC_TENSES,
    REFORMULATION_STRATEGIES
)

from ..data.vocabulary.essential_vocabulary import (
    ESSENTIAL_VERBS,
    ESSENTIAL_NOUNS,
    ESSENTIAL_ADJECTIVES,
    ESSENTIAL_ADVERBS,
    ESSENTIAL_PRONOUNS,
    ESSENTIAL_PREPOSITIONS
)

from .understanding_system import AdvancedUnderstandingSystem
from .response_system import AdvancedResponseSystem

@dataclass
class KnowledgeBase:
    """Rappresenta tutta la conoscenza linguistica di ALLMA."""
    grammar: Dict        # regole grammaticali
    patterns: Dict      # pattern di frase
    vocabulary: Dict    # vocabolario
    learned: Dict      # parole/concetti imparati
    
    def query_knowledge(
        self,
        query: str,
        category: Optional[str] = None,
        threshold: float = 0.5
    ) -> Dict[str, Any]:
        """
        Cerca informazioni nella base di conoscenza.
        
        Args:
            query: Testo o pattern da cercare
            category: Categoria specifica dove cercare (grammar, patterns, vocabulary, learned)
            threshold: Soglia minima di similarità per i risultati
            
        Returns:
            Dict con i risultati della ricerca
        """
        results = {
            'found': False,
            'matches': [],
            'confidence': 0.0,
            'category': category
        }
        
        # Se specificata una categoria, cerca solo in quella
        if category:
            if category == 'grammar' and query in self.grammar:
                results['matches'].append(self.grammar[query])
                results['found'] = True
                results['confidence'] = 1.0
            elif category == 'patterns' and query in self.patterns:
                results['matches'].append(self.patterns[query])
                results['found'] = True
                results['confidence'] = 1.0
            elif category == 'vocabulary':
                for word_type, words in self.vocabulary.items():
                    if query in words:
                        results['matches'].append({
                            'type': word_type,
                            'value': words[query]
                        })
                        results['found'] = True
                        results['confidence'] = 1.0
            elif category == 'learned' and query in self.learned:
                results['matches'].append(self.learned[query])
                results['found'] = True
                results['confidence'] = 1.0
        else:
            # Cerca in tutte le categorie
            # Grammar
            if query in self.grammar:
                results['matches'].append({
                    'category': 'grammar',
                    'value': self.grammar[query]
                })
                results['found'] = True
                
            # Patterns
            if query in self.patterns:
                results['matches'].append({
                    'category': 'patterns',
                    'value': self.patterns[query]
                })
                results['found'] = True
                
            # Vocabulary
            for word_type, words in self.vocabulary.items():
                if query in words:
                    results['matches'].append({
                        'category': 'vocabulary',
                        'type': word_type,
                        'value': words[query]
                    })
                    results['found'] = True
                    
            # Learned
            if query in self.learned:
                results['matches'].append({
                    'category': 'learned',
                    'value': self.learned[query]
                })
                results['found'] = True
        
        # Calcola confidence se ci sono match
        if results['matches']:
            results['confidence'] = 1.0 if len(results['matches']) == 1 else 0.8
            
        return results

class IntegratedKnowledgeSystem:
    def __init__(self):
        # Inizializza la base di conoscenza
        self.knowledge = KnowledgeBase(
            grammar=GRAMMAR_RULES,
            patterns={},
            vocabulary={
                'verbs': ESSENTIAL_VERBS,
                'nouns': ESSENTIAL_NOUNS,
                'adjectives': ESSENTIAL_ADJECTIVES,
                'adverbs': ESSENTIAL_ADVERBS,
                'pronouns': ESSENTIAL_PRONOUNS,
                'prepositions': ESSENTIAL_PREPOSITIONS
            },
            learned={}
        )

        # Inizializza i sistemi avanzati
        self.understanding = AdvancedUnderstandingSystem()
        self.response = AdvancedResponseSystem()

        # Connette i sistemi alla base di conoscenza
        self._connect_systems()

    def _connect_systems(self):
        """Collega tutti i sistemi alla base di conoscenza."""
        
        # Estende il sistema di comprensione con la conoscenza base
        self.understanding.syntax_analyzer.grammar_rules = self.knowledge.grammar
        self.understanding.syntax_analyzer.sentence_patterns = self.knowledge.patterns
        
        # Fornisce il vocabolario al sistema di comprensione
        self.understanding.vocabulary = self.knowledge.vocabulary
        
        # Collega il sistema di risposta alla conoscenza
        self.response.language_generator.vocabulary = self.knowledge.vocabulary
        self.response.language_generator.patterns = self.knowledge.patterns

    def process_input(self, text: str, context: Optional[Dict] = None) -> str:
        """Elabora un input usando tutti i sistemi integrati."""
        
        # 1. Comprensione usando la conoscenza base
        understanding = self.understanding.understand(
            text,
            context,
            self.knowledge  # Passa la knowledge base
        )
        
        # 2. Generazione risposta usando vocabolario e pattern
        response = self.response.generate_response(
            understanding,
            context
        )
        
        # 3. Aggiornamento della conoscenza con nuovi apprendimenti
        self._update_knowledge(understanding, response)
        
        return response.text

    def _update_knowledge(self, understanding, response):
        """Aggiorna la base di conoscenza con nuovi apprendimenti."""
        
        # Aggiunge nuove parole apprese
        for word in understanding.new_words:
            if word not in self.knowledge.vocabulary:
                self.knowledge.learned[word] = {
                    'context': understanding.context,
                    'usage': understanding.components,
                    'confidence': understanding.confidence
                }
        
        # Aggiorna pattern di uso
        for pattern in understanding.sentence_patterns:
            pattern_key = self._make_pattern_key(pattern)
            if pattern_key not in self.knowledge.patterns:
                self.knowledge.patterns[pattern_key] = {
                    'type': pattern['type'],
                    'components': pattern['components'],
                    'text': pattern['text'],
                    'frequency': 1,
                    'examples': [pattern['text']]
                }
            else:
                self.knowledge.patterns[pattern_key]['frequency'] += 1
                if pattern['text'] not in self.knowledge.patterns[pattern_key]['examples']:
                    self.knowledge.patterns[pattern_key]['examples'].append(
                        pattern['text']
                    )

    def _make_pattern_key(self, pattern: Dict) -> str:
        """Crea una chiave univoca per il pattern."""
        return f"{pattern['type']}:{':'.join(pattern['components'])}"

    def get_knowledge_state(self) -> Dict:
        """Restituisce lo stato attuale della conoscenza."""
        return {
            'vocabulary_size': {
                'base': len(self.knowledge.vocabulary),
                'learned': len(self.knowledge.learned)
            },
            'patterns': len(self.knowledge.patterns),
            'grammar_rules': len(self.knowledge.grammar),
            'learning_progress': self._calculate_learning_progress()
        }

    def _calculate_learning_progress(self) -> Dict:
        """Calcola il progresso dell'apprendimento."""
        return {
            'vocabulary_growth': len(self.knowledge.learned) / len(self.knowledge.vocabulary),
            'pattern_mastery': sum(p['frequency'] for p in self.knowledge.patterns.values()) / 1000,
            'grammar_mastery': 0.8  # esempio base
        }

class KnowledgeValidator:
    """Valida la coerenza della base di conoscenza."""
    
    @staticmethod
    def validate_integration(knowledge: KnowledgeBase) -> bool:
        """Verifica che tutti i componenti siano correttamente integrati."""
        
        # Verifica presenza componenti essenziali
        essential_components = [
            'grammar',
            'patterns',
            'vocabulary',
            'learned'
        ]
        
        for component in essential_components:
            if not hasattr(knowledge, component):
                return False
        
        # Verifica coerenza vocabolario
        for word_type in ['verbs', 'nouns', 'adjectives', 'adverbs']:
            if word_type not in knowledge.vocabulary:
                return False
        
        # Verifica presenza regole grammaticali base
        if 'concordanza' not in knowledge.grammar:
            return False
        
        return True

class KnowledgeOptimizer:
    """Ottimizza la base di conoscenza per prestazioni migliori."""
    
    @staticmethod
    def optimize(knowledge: KnowledgeBase):
        """Ottimizza la struttura della conoscenza."""
        
        # Rimuove duplicati
        for word_type in knowledge.vocabulary:
            knowledge.vocabulary[word_type] = dict(set(knowledge.vocabulary[word_type].items()))
        
        # Ordina per frequenza d'uso
        for pattern_type in knowledge.patterns:
            knowledge.patterns[pattern_type] = dict(
                sorted(
                    knowledge.patterns[pattern_type].items(),
                    key=lambda x: x[1]['frequency'],
                    reverse=True
                )
            )
        
        # Prune di pattern poco usati
        for pattern_type in knowledge.patterns:
            knowledge.patterns[pattern_type] = {
                k: v for k, v in knowledge.patterns[pattern_type].items()
                if v['frequency'] > 1
            }
