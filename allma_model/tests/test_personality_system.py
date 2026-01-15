"""Test del sistema di personalità"""

import unittest
import tempfile
import os
import sqlite3
import json
from Model.personality_system.personality import Personality
from Model.memory_system.knowledge_memory import KnowledgeMemory
from Model.emotional_system.emotional_core import EmotionalCore
from Model.core.response_generator import ResponseGenerator

class TestPersonalitySystem(unittest.TestCase):
    def setUp(self):
        """Setup per i test"""
        # Crea un file temporaneo per il database
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test.db")
        
        # Inizializza i componenti
        self.knowledge_memory = KnowledgeMemory(self.db_path)
        self.emotional_core = EmotionalCore()
        self.personality = Personality()
        self.response_generator = ResponseGenerator(self.knowledge_memory)
        
        # Crea esplicitamente la tabella
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS knowledge (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    metadata TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
        
    def tearDown(self):
        """Cleanup dopo i test"""
        # Rimuovi il file temporaneo
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
        
    def test_personality_initialization(self):
        """Test dell'inizializzazione della personalità"""
        self.assertEqual(self.personality._style["communication_style"], "neutral")
        self.assertEqual(self.personality._style["technical_level"], "intermediate")
        self.assertEqual(self.personality._style["response_length"], "medium")
        
    def test_personality_adaptation(self):
        """Test dell'adattamento della personalità"""
        # Test adattamento alle preferenze
        preferences = {
            "communication_style": "formal",
            "technical_level": "expert"
        }
        self.personality.adapt_to_preferences(preferences)
        
        self.assertEqual(self.personality._style["communication_style"], "formal")
        self.assertEqual(self.personality._style["technical_level"], "expert")
        
    def test_personality_emotional_integration(self):
        """Test dell'integrazione con il sistema emotivo"""
        # Simula un'emozione
        self.emotional_core.current_emotion = "happy"
        
        # Adatta la personalità all'emozione
        self.personality.adapt_to_emotion(self.emotional_core)
        
        # Verifica che l'emozione influenzi la personalità
        self.assertEqual(self.personality._style["emotion_influence"], "happy")
        
    def test_personality_knowledge_integration(self):
        """Test dell'integrazione con il sistema di conoscenza"""
        # Memorizza conoscenza di test
        self.knowledge_memory.store_knowledge(
            "ALLMA uses a formal communication style for technical discussions",
            {"topic": "communication_style"}
        )
        
        # Cerca conoscenza correlata
        results = self.knowledge_memory.get_knowledge_for_text("communication style")
        self.assertTrue(any("formal" in result for result in results))
        
    def test_personality_response_influence(self):
        """Test dell'influenza della personalità sulle risposte"""
        # Setup mock response generator
        mock_response = "This is a test response"
        self.response_generator.generate_response = lambda query, context=None: mock_response
        
        # Test influenza sulle risposte
        query = "What is machine learning?"
        context = {
            "user_id": "test_user",
            "technical_level": "beginner"
        }
        
        # Genera risposta con personalità formale
        self.personality._style["communication_style"] = "formal"
        response_formal = self.personality.influence_response(
            query, self.response_generator, context
        )
        
        # Genera risposta con personalità casual
        self.personality._style["communication_style"] = "casual"
        response_casual = self.personality.influence_response(
            query, self.response_generator, context
        )
        
        # Verifica che le risposte siano diverse
        self.assertNotEqual(response_formal, response_casual)
        
    def test_personality_persistence(self):
        """Test della persistenza della personalità"""
        # Imposta uno stile
        self.personality._style["communication_style"] = "formal"
        self.personality._style["technical_level"] = "expert"
        
        # Salva lo stato
        self.personality.save_state()
        
        # Reset della personalità
        self.personality.reset()
        
        # Carica lo stato
        self.personality.load_state()
        
        # Verifica che lo stato sia stato ripristinato
        self.assertEqual(self.personality._style["communication_style"], "formal")
        self.assertEqual(self.personality._style["technical_level"], "expert")
        
    def test_personality_reset(self):
        """Test del reset della personalità"""
        # Imposta uno stile
        self.personality._style["communication_style"] = "formal"
        self.personality._style["technical_level"] = "expert"
        
        # Reset della personalità
        self.personality.reset()
        
        # Verifica che lo stile sia tornato ai valori default
        self.assertEqual(self.personality._style["communication_style"], "neutral")
        self.assertEqual(self.personality._style["technical_level"], "intermediate")
        self.assertEqual(self.personality._style["response_length"], "medium")
        self.assertIsNone(self.personality._style["emotion_influence"])

if __name__ == '__main__':
    unittest.main()
