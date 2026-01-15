import unittest
import os
from datetime import datetime

from Model.core.allma_core import ALLMACore
from Model.project_tracking.project_tracker import ProjectTracker
from Model.emotional_system.emotional_core import EmotionalCore
from Model.user_preferences.preference_analyzer import (
    PreferenceAnalyzer,
    CommunicationStyle,
    LearningStyle
)
from Model.memory_system.conversational_memory import ConversationalMemory
from Model.core.response_generator import ResponseGenerator
from Model.learning_system.incremental_learning import IncrementalLearner
from Model.core.knowledge_memory import KnowledgeMemory
from Model.core.personality import Personality
from Model.core.context_understanding import ContextUnderstandingSystem

class TestSevenSystemsIntegration(unittest.TestCase):
    """Test di integrazione per i sette sistemi principali di ALLMA"""
    
    def setUp(self):
        """Setup per i test di integrazione"""
        self.test_db = "test_integration.db"
        self.test_user_id = "test_user_integration"
        
        # Inizializza il database
        from Model.database.init_db import init_db
        init_db(self.test_db)
        
        # Inizializza i componenti di supporto
        self.knowledge_memory = KnowledgeMemory()
        self.personality = Personality()
        self.context_system = ContextUnderstandingSystem()
        
        # Inizializza tutti i sistemi principali
        self.core = ALLMACore(db_path=self.test_db)
        self.project_tracker = ProjectTracker(self.test_db)
        self.emotional_core = EmotionalCore()
        self.preference_analyzer = PreferenceAnalyzer(self.test_db)
        self.conversational_memory = ConversationalMemory()
        self.response_generator = ResponseGenerator(
            context_system=self.context_system,
            knowledge_memory=self.knowledge_memory,
            personality=self.personality
        )
        self.incremental_learning = IncrementalLearner()
        
    def tearDown(self):
        """Cleanup dopo i test"""
        if os.path.exists(self.test_db):
            os.remove(self.test_db)
            
    def test_full_interaction_flow(self):
        """Test del flusso completo di interazione attraverso tutti i sistemi"""
        # 1. Crea un nuovo progetto
        project_id = self.project_tracker.create_project(
            name="Test Integration Project",
            description="A test project for integration testing",
            user_id=self.test_user_id
        )
        
        # 2. Simula una preferenza utente
        self.preference_analyzer.update_user_preferences(
            user_id=self.test_user_id,
            preferences={
                'communication_style': {
                    'value': CommunicationStyle.TECHNICAL.value,
                    'confidence': 0.9
                },
                'learning_style': {
                    'value': LearningStyle.VISUAL.value,
                    'confidence': 0.9
                }
            }
        )
        
        # 3. Simula un'interazione emotiva
        emotional_state = self.emotional_core.detect_emotion(
            "I'm excited to work on this project!",
            context={'user_id': self.test_user_id}
        )
        
        # 4. Memorizza l'interazione
        conversation_id = self.conversational_memory.store_conversation(
            user_id=self.test_user_id,
            content="",
            metadata={'project_id': project_id}
        )
        self.conversational_memory.store_message(
            conversation_id=conversation_id,
            role="user",
            content="Let's start working on the project",
            metadata={'project_id': project_id}
        )
        
        # 5. Genera una risposta
        response = self.response_generator.generate_response(
            query="What's our first task?"
        )
        
        # 6. Applica l'apprendimento incrementale
        self.incremental_learning.learn_from_interaction(
            interaction={
                'input': "What's our first task?",
                'response': response,
                'feedback': 'positive'
            },
            user_id=self.test_user_id
        )
        
        # Verifica che tutti i sistemi abbiano funzionato correttamente
        self.assertTrue(project_id is not None)
        self.assertTrue(emotional_state is not None)
        self.assertTrue(response is not None)
        
        # Verifica la memoria conversazionale
        recent_memory = self.conversational_memory.get_recent_interactions(
            user_id=self.test_user_id,
            limit=1
        )
        self.assertEqual(len(recent_memory), 1)
        
    def test_error_handling(self):
        """Test della gestione degli errori tra i sistemi"""
        # Test di recupero da errori di database
        with self.assertRaises(Exception):
            self.core.process_interaction(
                "Test message",
                invalid_param="should fail"
            )
            
    def test_performance(self):
        """Test delle performance del sistema integrato"""
        import time
        
        start_time = time.time()
        
        # Crea una nuova conversazione
        conversation_id = self.core.start_conversation(self.test_user_id)
        
        # Esegui una serie di operazioni integrate
        for i in range(10):
            self.core.process_message(
                user_id=self.test_user_id,
                conversation_id=conversation_id,
                message=f"Test message {i}"
            )
            
        end_time = time.time()
        execution_time = end_time - start_time
        
        # Verifica che il tempo di esecuzione sia accettabile
        self.assertLess(execution_time, 5.0)  # dovrebbe completare in meno di 5 secondi

if __name__ == '__main__':
    unittest.main()
