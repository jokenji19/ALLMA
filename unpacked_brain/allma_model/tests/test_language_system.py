"""
Test del Sistema Linguistico di ALLMA
"""

import unittest
from typing import List, Dict
from allma_model.core.language_system import LanguageSystem
from allma_model.core.response_system import ResponseStyle

class TestLanguageSystem(unittest.TestCase):
    def setUp(self):
        self.language_system = LanguageSystem()
        self.test_cases = {
            'basic_understanding': [
                {
                    'input': 'Mi chiamo Marco',
                    'expected_components': ['soggetto', 'verbo', 'nome']
                }
            ],
            'response_generation': [
                {
                    'input': 'Come ti chiami?',
                    'expected': 'Mi chiamo'
                },
                {
                    'input': 'Non ho capito bene',
                    'expected': 'spiegare'
                }
            ],
            'response_style': [
                {
                    'input': 'Mi scusi, potrebbe aiutarmi?',
                    'expected_style': ResponseStyle.FORMAL
                },
                {
                    'input': 'Ehi, come va?',
                    'expected_style': ResponseStyle.INFORMAL
                },
                {
                    'input': 'Non capisco questo concetto',
                    'expected_style': ResponseStyle.INSTRUCTIVE
                }
            ],
            'grammar_understanding': [
                {
                    'input': 'Il gatto nero dorme',
                    'expected_pattern': ['articolo', 'nome', 'aggettivo', 'verbo']
                },
                {
                    'input': 'Maria mangia una mela rossa',
                    'expected_pattern': ['nome', 'verbo', 'articolo', 'nome', 'aggettivo']
                }
            ]
        }
    
    def test_basic_understanding(self):
        """Testa la comprensione base delle frasi."""
        for case in self.test_cases['basic_understanding']:
            with self.subTest(input=case['input']):
                response = self.language_system.process_input(case['input'])
                components = [comp.role for comp in response.understanding.components]
                print(f"\nInput: {case['input']}")
                print(f"Components: {components}")
                print(f"Expected: {case['expected_components']}")
                for expected_component in case['expected_components']:
                    self.assertIn(expected_component, components)
    
    def test_response_generation(self):
        """Testa la generazione delle risposte."""
        for case in self.test_cases['response_generation']:
            with self.subTest(input=case['input']):
                response = self.language_system.process_input(case['input'])
                self.assertIn(case['expected'].lower(), response.response_text.lower())
    
    def test_response_style_adaptation(self):
        """Testa l'adattamento dello stile delle risposte."""
        for case in self.test_cases['response_style']:
            with self.subTest(input=case['input']):
                response = self.language_system.process_input(case['input'])
                self.assertEqual(response.style, case['expected_style'])
    
    def test_grammar_understanding(self):
        """Testa la comprensione grammaticale."""
        for case in self.test_cases['grammar_understanding']:
            with self.subTest(input=case['input']):
                response = self.language_system.process_input(case['input'])
                components = [comp.role for comp in response.understanding.components]
                matching_components = [i for i, (a, b) in 
                                    enumerate(zip(components, case['expected_pattern']))
                                    if a == b]
                self.assertTrue(matching_components)
    
    def test_context_maintenance(self):
        """Testa il mantenimento del contesto nella conversazione."""
        inputs = [
            "Mi chiamo Marco",
            "Come stai?",
            "Bene, grazie"
        ]
        
        for text in inputs:
            response = self.language_system.process_input(text)
        
        context = self.language_system.context
        self.assertIn("nome_utente", context)
        self.assertEqual(context["nome_utente"], "Marco")
    
    def test_emotional_understanding(self):
        """Testa il riconoscimento delle emozioni."""
        test_cases = [
            ("Sono molto felice oggi!", "POSITIVE"),
            ("Mi sento triste", "NEGATIVE"),
            ("Il cielo è blu", "NEUTRAL")
        ]
        
        for text, expected_emotion in test_cases:
            response = self.language_system.process_input(text)
            self.assertEqual(
                response.understanding.emotional_tone.name,
                expected_emotion
            )
    
    def test_learning_capability(self):
        """Testa la capacità di apprendimento."""
        inputs = [
            "Mi chiamo Marco",
            "Sono uno sviluppatore",
            "Mi piace programmare"
        ]
        
        learned_concepts = set()
        for text in inputs:
            response = self.language_system.process_input(text)
            print(f"\nPunti di apprendimento per '{text}':")
            for point in response.learning_points:
                print(f"  - {point}")
                if "Nuovo concetto appreso:" in point:
                    concept = point.replace("Nuovo concetto appreso:", "").strip().lower()
                    print(f"    Estratto concetto: '{concept}'")
                    learned_concepts.add(concept)
        
        print(f"\nConcetti appresi: {learned_concepts}")
        print(f"Concetti attesi: {{'marco', 'sviluppatore', 'programmare'}}")
        
        # Verifica che il sistema abbia imparato almeno alcuni concetti specifici
        expected_concepts = {"marco", "sviluppatore", "programmare"}
        self.assertTrue(
            any(concept in expected_concepts 
                for concept in learned_concepts),
            f"Expected to learn one of {expected_concepts}, but learned {learned_concepts}"
        )
    
    def test_error_handling(self):
        """Testa la gestione degli errori e delle ambiguità."""
        test_cases = [
            {
                'input': 'questa cosa qui',
                'expected_ambiguity': True
            },
            {
                'input': '!@#$%^',
                'expected_error': True
            }
        ]
        
        for case in test_cases:
            with self.subTest(input=case['input']):
                response = self.language_system.process_input(case['input'])
                if 'expected_ambiguity' in case:
                    self.assertTrue(
                        response.understanding.requires_clarification,
                        "Dovrebbe richiedere chiarimenti"
                    )
                if 'expected_error' in case:
                    self.assertTrue(
                        response.understanding.confidence < 0.5,
                        "La confidenza dovrebbe essere bassa"
                    )

if __name__ == '__main__':
    unittest.main()
