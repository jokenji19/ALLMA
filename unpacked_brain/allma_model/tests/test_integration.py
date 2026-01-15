"""Test di integrazione per ALLMA."""

import unittest
from datetime import datetime
import os
from allma_model.core.allma_core import ALLMACore
from allma_model.memory_system.conversational_memory import ConversationalMemory
from allma_model.emotional_system.emotional_core import EmotionalCore
from allma_model.project_system.project_tracker import ProjectTracker
from allma_model.user_system.user_preferences import UserPreferenceAnalyzer, LearningStyle
from allma_model.response_system.contextual_response import ContextualResponseGenerator
from allma_model.learning_system.incremental_learning import IncrementalLearner

class TestIntegration(unittest.TestCase):
    """Test di integrazione per tutti i sistemi di ALLMA."""
    
    def setUp(self):
        """Setup del test."""
        self.test_user = "test_user"
        self.test_db = "test.db"
        
        # Elimina il database se esiste
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
        # Inizializza il core
        self.core = ALLMACore(db_path=self.test_db)
        
        # Crea un progetto di test per Python
        self.test_project_id = self.core.create_project(
            self.test_user,
            "Python Learning",
            "A project to learn Python programming",
            {"topic": "python"}
        )
        
    def test_end_to_end_interaction(self):
        """Test di un'interazione completa end-to-end."""
        # 1. Inizia una nuova conversazione
        conversation_id = self.core.start_conversation(self.test_user)
        self.assertIsNotNone(conversation_id)
        
        # 2. Processa un messaggio con emozione
        response = self.core.process_message(
            self.test_user,
            conversation_id,
            "Sono molto contento di imparare Python!"
        )
        
        self.assertIsNotNone(response)
        self.assertTrue(response.emotion_detected)
        self.assertEqual(response.emotion, "joy")
        
        # 3. Verifica il tracking del progetto
        self.assertIsNotNone(response.project_context)
        self.assertEqual(response.project_context.topic, "python")
        
        # 4. Verifica l'adattamento alle preferenze
        self.assertIsNotNone(response.user_preferences)
        self.assertEqual(
            response.format,
            response.user_preferences.preferred_format
        )
        
        # 5. Verifica l'apprendimento
        knowledge = self.core.get_learned_knowledge("python")
        self.assertIsNotNone(knowledge)
        self.assertTrue(len(knowledge) > 0)
        
    def test_system_interaction(self):
        """Test delle interazioni tra sistemi."""
        # 1. Test Memoria-Emozioni
        emotion_memory = self.core.process_emotional_message(
            self.test_user,
            "Questo codice è fantastico!"
        )
        self.assertEqual(emotion_memory["emotion"], "joy")
        self.assertTrue(emotion_memory["is_stored"])
        
        # 2. Test Progetto-Preferenze
        project_preferences = self.core.get_project_preferences(
            self.test_user,
            self.test_project_id
        )
        self.assertIsNotNone(project_preferences)
        self.assertIn("technical_level", project_preferences)
        
        # 3. Test Risposta-Apprendimento
        learning_response = self.core.generate_learning_response(
            self.test_user,
            "Come funzionano le liste in Python?"
        )
        self.assertIsNotNone(learning_response)
        self.assertTrue(learning_response.knowledge_integrated)
        
    def test_error_handling(self):
        """Test della gestione degli errori tra sistemi."""
        # 1. Test errore memoria
        with self.assertRaises(ValueError):
            self.core.get_conversation_history("")
            
        # 2. Test errore emozioni
        with self.assertRaises(ValueError):
            self.core.process_emotional_message("", "test")
            
        # 3. Test errore progetto
        with self.assertRaises(ValueError):
            self.core.create_project("", "test", "description")
            
        # 4. Test errore preferenze
        with self.assertRaises(ValueError):
            self.core.update_user_preferences("", LearningStyle.KINESTHETIC)
            
    def test_data_consistency(self):
        """Test della consistenza dei dati tra sistemi."""
        # 1. Crea dati di test
        conversation_id = self.core.start_conversation(self.test_user)
        project_id = self.core.create_project(
            self.test_user,
            "test_project",
            "Test project"
        )
        
        # 2. Aggiungi interazioni
        messages = [
            "Come si usa Python?",
            "Grazie della spiegazione!",
            "Ora ho capito meglio."
        ]
        
        for msg in messages:
            self.core.process_message(
                self.test_user,
                conversation_id,
                msg
            )
            
        # 3. Verifica consistenza memoria
        history = self.core.get_conversation_history(conversation_id)
        self.assertEqual(len(history), len(messages))
        
        # 4. Verifica consistenza emozioni
        emotions = self.core.get_emotion_history(
            self.test_user,
            conversation_id=conversation_id
        )
        self.assertEqual(len(emotions), len(messages))
        
        # 5. Verifica consistenza progetto
        project = self.core.get_project(project_id)
        self.assertIsNotNone(project)
        self.assertEqual(project.user_id, self.test_user)
        
    def test_performance_metrics(self):
        """Test delle metriche di performance."""
        # 1. Test tempo di risposta
        start_time = datetime.now()
        self.core.process_message(
            self.test_user,
            "test_conversation",
            "Test message"
        )
        response_time = (datetime.now() - start_time).total_seconds()
        self.assertLess(response_time, 1.0)  # Max 1 secondo
        
        # 2. Test uso memoria
        import psutil
        import os
        process = psutil.Process(os.getpid())
        mem_before = process.memory_info().rss
        
        # Esegui operazioni intensive
        for i in range(100):
            self.core.process_message(
                self.test_user,
                f"conv_{i}",
                f"Message {i}"
            )
            
        mem_after = process.memory_info().rss
        mem_increase = (mem_after - mem_before) / 1024 / 1024  # MB
        self.assertLess(mem_increase, 100)  # Max 100MB
        
if __name__ == '__main__':
    unittest.main()
