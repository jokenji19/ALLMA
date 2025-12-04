import unittest
from datetime import datetime
from .reasoning_system import (
    ReasoningSystem, Premise, Conclusion, Rule,
    ReasoningType
)

class TestReasoningSystem(unittest.TestCase):
    def setUp(self):
        self.reasoning_system = ReasoningSystem()
        
        # Aggiungi alcune regole di base
        self.reasoning_system.add_rule(
            "piove",
            "la strada è bagnata",
            0.9,
            "esperienza comune"
        )
        self.reasoning_system.add_rule(
            "è nuvoloso",
            "potrebbe piovere",
            0.7,
            "meteorologia"
        )
        
        # Aggiungi alcune analogie
        self.reasoning_system.add_analogy(
            "il cervello è come un computer",
            "processa informazioni e memorizza dati"
        )
        self.reasoning_system.add_analogy(
            "l'atomo è come il sistema solare",
            "ha un nucleo centrale con elementi che orbitano intorno"
        )
        
        # Aggiungi alcune relazioni causali
        self.reasoning_system.add_causal_relation(
            "aumento della temperatura",
            "espansione termica"
        )
        self.reasoning_system.add_causal_relation(
            "stress prolungato",
            "diminuzione delle difese immunitarie"
        )
        
    def test_add_premise(self):
        """Testa l'aggiunta di premesse"""
        premise = self.reasoning_system.add_premise(
            "piove forte",
            0.9,
            "osservazione diretta"
        )
        
        self.assertIsNotNone(premise)
        self.assertEqual(premise.statement, "piove forte")
        self.assertEqual(premise.confidence, 0.9)
        self.assertEqual(premise.source, "osservazione diretta")
        
        # Verifica che la premessa sia stata categorizzata correttamente
        category = self.reasoning_system._categorize_statement("piove forte")
        self.assertIn(premise, self.reasoning_system.knowledge_base[category])
        
    def test_deductive_reasoning(self):
        """Testa il ragionamento deduttivo"""
        # Crea una premessa
        premise = self.reasoning_system.add_premise(
            "piove",
            0.9,
            "osservazione"
        )
        
        # Applica il ragionamento deduttivo
        conclusion = self.reasoning_system.deductive_reasoning([premise])
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.DEDUCTIVE)
        self.assertEqual(conclusion.statement, "la strada è bagnata")
        self.assertGreater(conclusion.confidence, 0)
        self.assertLess(conclusion.confidence, 1)
        
    def test_inductive_reasoning(self):
        """Testa il ragionamento induttivo"""
        # Crea diverse osservazioni simili
        observations = [
            self.reasoning_system.add_premise(
                "questo corvo è nero",
                0.9,
                "osservazione"
            ),
            self.reasoning_system.add_premise(
                "quel corvo è nero",
                0.9,
                "osservazione"
            ),
            self.reasoning_system.add_premise(
                "tutti i corvi visti sono neri",
                0.9,
                "osservazione"
            )
        ]
        
        # Applica il ragionamento induttivo
        conclusion = self.reasoning_system.inductive_reasoning(observations)
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.INDUCTIVE)
        self.assertGreater(conclusion.confidence, 0)
        self.assertTrue("Generalmente" in conclusion.statement)
        
    def test_analogical_reasoning(self):
        """Testa il ragionamento analogico"""
        # Crea una premessa per il dominio sorgente
        source_premise = self.reasoning_system.add_premise(
            "il cervello è come un computer",  # Usa esattamente la stessa frase dell'analogia
            0.8,
            "analogia"
        )
        
        # Applica il ragionamento analogico
        conclusion = self.reasoning_system.analogical_reasoning(
            source_premise,
            "elaborazione mentale"
        )
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.ANALOGICAL)
        self.assertGreater(conclusion.confidence, 0)
        self.assertLess(conclusion.confidence, source_premise.confidence)
        
        # Test con una premessa simile ma non identica
        similar_premise = self.reasoning_system.add_premise(
            "il cervello funziona come un elaboratore",
            0.8,
            "analogia"
        )
        
        # Dovrebbe trovare l'analogia anche con una frase simile
        conclusion = self.reasoning_system.analogical_reasoning(
            similar_premise,
            "elaborazione mentale"
        )
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.ANALOGICAL)
        self.assertGreater(conclusion.confidence, 0)
        self.assertLess(conclusion.confidence, similar_premise.confidence)
        
    def test_abductive_reasoning(self):
        """Testa il ragionamento abduttivo"""
        # Crea un'osservazione
        observation = self.reasoning_system.add_premise(
            "diminuzione delle difese immunitarie",
            0.8,
            "osservazione medica"
        )
        
        # Applica il ragionamento abduttivo
        conclusion = self.reasoning_system.abductive_reasoning(observation)
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.ABDUCTIVE)
        self.assertGreater(conclusion.confidence, 0)
        self.assertTrue("stress prolungato" in conclusion.statement)
        
    def test_causal_reasoning(self):
        """Testa il ragionamento causale"""
        # Crea un evento
        event = self.reasoning_system.add_premise(
            "aumento della temperatura",
            0.9,
            "misurazione"
        )
        
        # Applica il ragionamento causale
        conclusion = self.reasoning_system.causal_reasoning(event)
        
        self.assertIsNotNone(conclusion)
        self.assertEqual(conclusion.reasoning_type, ReasoningType.CAUSAL)
        self.assertGreater(conclusion.confidence, 0)
        self.assertTrue("espansione termica" in conclusion.statement)
        
    def test_invalid_inputs(self):
        """Testa il comportamento con input non validi"""
        # Test con lista vuota di premesse
        self.assertIsNone(self.reasoning_system.deductive_reasoning([]))
        
        # Test con premessa non esistente per analogia
        invalid_premise = Premise("non esiste", 0.5, "test", datetime.now())
        self.assertIsNone(
            self.reasoning_system.analogical_reasoning(invalid_premise, "test")
        )
        
        # Test con evento non causale
        invalid_event = self.reasoning_system.add_premise(
            "evento non causale",
            0.5,
            "test"
        )
        self.assertIsNone(self.reasoning_system.causal_reasoning(invalid_event))
        
    def test_confidence_propagation(self):
        """Testa la propagazione della confidenza"""
        # Test deduttivo con premessa a bassa confidenza
        low_confidence_premise = self.reasoning_system.add_premise(
            "piove",
            0.3,
            "sentito dire"
        )
        conclusion = self.reasoning_system.deductive_reasoning([low_confidence_premise])
        
        self.assertIsNotNone(conclusion)
        self.assertLess(conclusion.confidence, low_confidence_premise.confidence)
        
        # Test causale con alta confidenza
        high_confidence_event = self.reasoning_system.add_premise(
            "aumento della temperatura",
            0.95,
            "misurazione precisa"
        )
        conclusion = self.reasoning_system.causal_reasoning(high_confidence_event)
        
        self.assertIsNotNone(conclusion)
        self.assertLess(conclusion.confidence, high_confidence_event.confidence)
        
    def test_explanation_generation(self):
        """Testa la generazione di spiegazioni"""
        # Test deduttivo
        premise = self.reasoning_system.add_premise(
            "piove",
            0.9,
            "osservazione"
        )
        conclusion = self.reasoning_system.deductive_reasoning([premise])
        
        self.assertIsNotNone(conclusion)
        self.assertTrue(conclusion.explanation)
        self.assertIn("Dedotto da", conclusion.explanation)
        
        # Test abduttivo
        observation = self.reasoning_system.add_premise(
            "diminuzione delle difese immunitarie",
            0.8,
            "osservazione medica"
        )
        conclusion = self.reasoning_system.abductive_reasoning(observation)
        
        self.assertIsNotNone(conclusion)
        self.assertTrue(conclusion.explanation)
        self.assertIn("Abduzione", conclusion.explanation)

if __name__ == '__main__':
    unittest.main()
