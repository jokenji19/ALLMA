import unittest
from datetime import datetime
import os
from .contextual_learning_system import (
    ContextualLearningSystem,
    Context,
    ContextEncoder,
    ContextualMemory,
    KnowledgeTransfer
)

class TestContextualLearningSystem(unittest.TestCase):
    def setUp(self):
        self.learning_system = ContextualLearningSystem()
        
    def test_context_encoding(self):
        """Verifica la codifica del contesto"""
        encoder = ContextEncoder()
        
        # Testa la codifica di un testo
        text = "Python programming language"
        embedding = encoder.encode(text)
        
        self.assertEqual(embedding.shape[1], 384)  # Dimensione dell'embedding di MiniLM
        
    def test_contextual_memory(self):
        """Verifica la memoria contestuale"""
        memory = ContextualMemory()
        
        # Crea un contesto di test
        context = Context(
            topic="programming",
            subtopics={"python", "coding"},
            entities={"Python"},
            sentiment=0.8,
            timestamp=datetime.now(),
            user_state={"skill_level": "intermediate"},
            previous_contexts=[],
            confidence=1.0
        )
        
        # Aggiungi il contesto
        memory.add_context(context)
        
        # Trova contesti simili
        similar = memory.find_similar_contexts(context)
        self.assertTrue(len(similar) > 0)
        
    def test_knowledge_transfer(self):
        """Verifica il trasferimento di conoscenza"""
        kt = KnowledgeTransfer()
        
        # Crea due contesti
        source_context = Context(
            topic="python",
            subtopics={"programming", "coding"},
            entities={"Python"},
            sentiment=0.8,
            timestamp=datetime.now(),
            user_state={},
            previous_contexts=[],
            confidence=1.0
        )
        
        target_context = Context(
            topic="javascript",
            subtopics={"programming", "web"},
            entities={"JavaScript"},
            sentiment=0.7,
            timestamp=datetime.now(),
            user_state={},
            previous_contexts=[],
            confidence=1.0
        )
        
        # Aggiungi conoscenza
        kt.add_knowledge(
            source_context,
            {"concept": "variables", "difficulty": "basic"}
        )
        
        # Trasferisci conoscenza
        transferred = kt.transfer_knowledge(source_context, target_context, 0.8)
        self.assertTrue(transferred)
        
    def test_full_system_integration(self):
        """Verifica l'integrazione completa del sistema"""
        # Processa un input
        result = self.learning_system.process_input(
            "Python è un linguaggio di programmazione versatile",
            user_state={"skill_level": "beginner"},
            previous_contexts=[]
        )
        
        self.assertIn("current_context", result)
        self.assertIn("similar_contexts_found", result)
        self.assertIn("knowledge_transferred", result)
        
        # Verifica il contesto corrente
        current_context = self.learning_system.get_current_context()
        self.assertIsNotNone(current_context)
        self.assertIn("topic", current_context)
        self.assertIn("subtopics", current_context)
        
    def test_system_persistence(self):
        """Verifica il salvataggio e caricamento dello stato del sistema"""
        # Processa alcuni input
        self.learning_system.process_input(
            "Python è fantastico per il machine learning",
            user_state={"interest": "AI"},
            previous_contexts=[]
        )
        
        # Salva lo stato
        test_file = "test_contextual_state.json"
        self.learning_system.save_state(test_file)
        
        # Crea un nuovo sistema e carica lo stato
        new_system = ContextualLearningSystem()
        new_system.load_state(test_file)
        
        # Verifica che il contesto sia stato preservato
        self.assertEqual(
            new_system.get_current_context()["topic"],
            self.learning_system.get_current_context()["topic"]
        )
        
        # Pulisci
        os.remove(test_file)

if __name__ == '__main__':
    unittest.main()
