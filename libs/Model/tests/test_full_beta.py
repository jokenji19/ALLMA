"""
Test completo della beta di ALLMA che verifica l'integrazione di tutti i componenti principali.
"""

import unittest
from datetime import datetime, timedelta
from typing import Dict, List, Any
import time

from ..core.nlp_processor import NLPProcessor
from ..core.extraction import InformationExtractor
from ..core.knowledge_memory import KnowledgeMemory
from ..core.personality_coalescence import CoalescenceProcessor, EmotionalState
from ..core.context_understanding import ContextUnderstandingSystem
from ..core.document_processor import DocumentProcessor
from ..core.visual_memory import VisualMemorySystem
from ..core.personality import Personality  # Nuova classe Personality

class TestFullBeta(unittest.TestCase):
    def setUp(self):
        """Inizializza tutti i componenti necessari per i test"""
        self.nlp = NLPProcessor()
        self.extractor = InformationExtractor()
        self.knowledge = KnowledgeMemory(nlp=self.nlp)
        self.personality = Personality()  # Utilizza la nuova classe Personality
        self.context = ContextUnderstandingSystem()
        self.doc_processor = DocumentProcessor()
        self.visual_memory = VisualMemorySystem()
        
        # Configurazione iniziale per i test
        self.test_concepts = {
            "machine_learning": {
                "description": "Il machine learning è un sottocampo dell'intelligenza artificiale",
                "related": ["deep_learning", "neural_networks", "data_science"],
                "confidence": 0.4
            },
            "neural_networks": {
                "description": "Le reti neurali sono modelli ispirati al cervello biologico",
                "related": ["deep_learning", "machine_learning", "backpropagation"],
                "confidence": 0.45
            },
            "data_science": {
                "description": "La data science combina statistica, programmazione e domain expertise",
                "related": ["machine_learning", "statistics", "programming"],
                "confidence": 0.5
            }
        }

    def test_1_initial_learning_capability(self):
        """Verifica la capacità di apprendimento iniziale di ALLMA"""
        # Inseriamo i concetti iniziali
        for concept, data in self.test_concepts.items():
            self.knowledge.add_concept(concept, data["description"], data["confidence"])
            
        # Verifichiamo che i concetti siano stati memorizzati correttamente
        for concept in self.test_concepts:
            self.assertTrue(self.knowledge.has_concept(concept))
            self.assertGreaterEqual(self.knowledge.get_concept_confidence(concept), 0.4)

    def test_2_emotional_response_integration(self):
        """Verifica l'integrazione delle risposte emotive con l'apprendimento"""
        # Test con emozione positiva
        emotional_impact = self.personality._analyze_emotional_context('joy')
        self.assertGreater(emotional_impact, 0.0)
        
        # Test con emozione negativa
        emotional_impact = self.personality._analyze_emotional_context('anger')
        self.assertLess(emotional_impact, 0.0)
        
        # Test con emozione neutra
        emotional_impact = self.personality._analyze_emotional_context('neutral')
        self.assertEqual(emotional_impact, 0.0)
        
        # Verifica l'impatto delle emozioni sull'apprendimento
        self.personality.update_personality({
            'type': 'learning',
            'success': True,
            'confidence': 0.8,
            'emotion': 'joy'
        })
        
        traits = self.personality.get_traits()
        self.assertGreater(traits['openness'], 0.5)
        self.assertGreater(traits['conscientiousness'], 0.5)

    def test_3_context_awareness(self):
        """Verifica la consapevolezza del contesto nelle interazioni"""
        conversation = [
            "Parliamo di machine learning",
            "In particolare, mi interessano le reti neurali",
            "Come si collegano alla data science?"
        ]
        
        context = {}
        for message in conversation:
            # Aggiorna il contesto con ogni messaggio
            new_context = self.context.update_context(message, context)
            self.assertIsNotNone(new_context)
            
            # Verifica che il contesto mantenga coerenza
            if "topic" in new_context:
                self.assertIn(new_context["topic"], 
                            ["machine_learning", "neural_networks", "data_science"])
            
            context = new_context

    def test_4_knowledge_integration(self):
        """Verifica l'integrazione della conoscenza attraverso diverse fonti"""
        # Test di apprendimento da testo
        test_text = """
        Il machine learning è fondamentale per la data science moderna.
        Le reti neurali sono uno strumento potente del deep learning.
        """
        
        # Estrai concetti dal testo
        processed = self.nlp.process_text(test_text)
        concepts = processed.get('concepts', [])
        
        # Aggiungi i concetti alla memoria
        for concept in concepts:
            self.knowledge.add_concept(
                concept,
                f"Concetto estratto da: {test_text}",
                0.7
            )
            
        # Verifica che i concetti principali siano stati memorizzati
        key_concepts = ['machine_learning', 'data_science', 'neural_network', 'deep_learning']
        for concept in key_concepts:
            self.assertTrue(
                self.knowledge.has_concept(concept),
                f"Concetto {concept} non trovato nella memoria"
            )
            
        # Aggiorna la personalità
        self.personality.update_personality({
            'type': 'learning',
            'success': True,
            'confidence': 0.7,
            'emotion': 'joy'
        })
        
        # Verifica l'evoluzione della personalità
        evolution = self.personality.analyze_personality_evolution()
        self.assertGreater(evolution['growth'], 0.0)

    def test_5_personality_evolution(self):
        """Verifica l'evoluzione della personalità nel tempo"""
        # Simula una serie di interazioni positive
        interactions = [
            {
                'type': 'learning',
                'success': True,
                'confidence': 0.8,
                'emotion': 'joy'
            },
            {
                'type': 'social',
                'success': True,
                'confidence': 0.9,
                'emotion': 'trust'
            },
            {
                'type': 'problem_solving',
                'success': True,
                'confidence': 0.85,
                'emotion': 'anticipation'
            }
        ]
        
        # Processa le interazioni
        for interaction in interactions:
            self.personality.update_personality(interaction)
            time.sleep(0.1)  # Simula il passaggio del tempo
            
        # Verifica che i tratti siano aumentati
        traits = self.personality.get_traits()
        initial_traits = {
            'openness': 0.5,
            'conscientiousness': 0.5,
            'extraversion': 0.5,
            'agreeableness': 0.5
        }
        
        # Verifica che almeno un tratto sia aumentato significativamente
        increased = False
        for trait in ['openness', 'conscientiousness', 'extraversion', 'agreeableness']:
            if traits[trait] > initial_traits[trait]:
                increased = True
                break
                
        self.assertTrue(increased, "Nessun tratto della personalità è aumentato")
        
        # Verifica l'evoluzione complessiva
        evolution = self.personality.analyze_personality_evolution()
        self.assertGreater(evolution['growth'], 0.0, "Non c'è stata crescita nella personalità")
        self.assertEqual(evolution['trend'], 'growing', "Il trend non è in crescita")

    def test_6_full_interaction_cycle(self):
        """Verifica un ciclo completo di interazione"""
        # Input dell'utente
        user_input = "Vorrei capire meglio come il machine learning si applica alla data science"
        
        # Estrai concetti
        processed = self.nlp.process_text(user_input)
        concepts = processed.get('concepts', [])
        
        # Verifica che siano stati estratti i concetti principali
        self.assertIn('machine_learning', concepts)
        self.assertIn('data_science', concepts)
        
        # Aggiungi i concetti alla memoria
        for concept in concepts:
            self.knowledge.add_concept(
                concept,
                f"Concetto estratto da: {user_input}",
                0.7
            )
            
        # Verifica che i concetti siano stati memorizzati
        for concept in concepts:
            self.assertTrue(self.knowledge.has_concept(concept))
            
        # Aggiorna la personalità
        self.personality.update_personality({
            'type': 'learning',
            'success': True,
            'confidence': 0.7,
            'emotion': 'joy'
        })
        
        # Verifica l'evoluzione della personalità
        evolution = self.personality.analyze_personality_evolution()
        self.assertGreater(evolution['growth'], 0.0)

    def test_7_long_term_learning(self):
        """Verifica l'apprendimento a lungo termine"""
        # Simula una serie di interazioni di apprendimento
        interactions = [
            {
                'text': "Il machine learning è fondamentale per la data science",
                'concepts': ['machine_learning', 'data_science'],
                'confidence': 0.7,
                'emotion': 'joy'
            },
            {
                'text': "Le reti neurali sono uno strumento del deep learning",
                'concepts': ['neural_network', 'deep_learning'],
                'confidence': 0.8,
                'emotion': 'trust'
            },
            {
                'text': "L'intelligenza artificiale sta rivoluzionando molti settori",
                'concepts': ['artificial_intelligence'],
                'confidence': 0.9,
                'emotion': 'joy'
            },
            {
                'text': "Il deep learning è una parte cruciale del machine learning",
                'concepts': ['deep_learning', 'machine_learning'],
                'confidence': 0.9,
                'emotion': 'trust'
            },
            {
                'text': "La data science utilizza tecniche di machine learning",
                'concepts': ['data_science', 'machine_learning'],
                'confidence': 0.95,
                'emotion': 'joy'
            }
        ]
        
        # Processa le interazioni
        for interaction in interactions:
            # Aggiungi concetti alla memoria
            for concept in interaction['concepts']:
                self.knowledge.add_concept(
                    concept,
                    f"Concetto estratto da: {interaction['text']}",
                    interaction['confidence']
                )
                
            # Aggiorna la personalità
            self.personality.update_personality({
                'type': 'learning',
                'success': True,
                'confidence': interaction['confidence'],
                'emotion': interaction['emotion']
            })
                
            # Simula il passaggio del tempo
            time.sleep(0.1)
            
        # Verifica la confidenza media dei concetti
        confidences = []
        for interaction in interactions:
            for concept in interaction['concepts']:
                confidence = self.knowledge.get_concept_confidence(concept)
                confidences.append(confidence)
                
        average_confidence = sum(confidences) / len(confidences)
        self.assertGreaterEqual(average_confidence, 0.7)
        
        # Verifica l'evoluzione della personalità
        evolution = self.personality.analyze_personality_evolution()
        self.assertGreater(evolution['growth'], 0.0)
        self.assertEqual(evolution['trend'], 'growing')

if __name__ == '__main__':
    unittest.main()
