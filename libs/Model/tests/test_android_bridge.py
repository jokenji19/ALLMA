"""
Test del bridge API per l'integrazione Android
"""

import unittest
import tempfile
import os
import json
from datetime import datetime
from typing import Dict, Any

from Model.api.allma_api import AllmaAndroidBridge
from Model.emotional_system.emotional_core import EmotionalState
from Model.project_system.project_types import ProjectStatus

class TestAndroidBridge(unittest.TestCase):
    def setUp(self):
        """Setup per i test"""
        # Crea una directory temporanea per i file di test
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_bridge.db")
        
        # Inizializza il bridge
        self.bridge = AllmaAndroidBridge(db_path=self.db_path)
        self.test_user_id = "test_user_123"
        
    def tearDown(self):
        """Cleanup dopo i test"""
        if os.path.exists(self.db_path):
            os.remove(self.db_path)
        os.rmdir(self.temp_dir)
        
    def test_session_initialization(self):
        """Test dell'inizializzazione della sessione"""
        # Inizializza una sessione
        session = self.bridge.initialize_user_session(self.test_user_id)
        
        # Verifica la struttura della sessione
        self.assertIn("user_id", session)
        self.assertIn("emotional_state", session)
        self.assertIn("personality_state", session)
        self.assertIn("active_projects", session)
        self.assertIn("learning_progress", session)
        
        # Verifica i valori
        self.assertEqual(session["user_id"], self.test_user_id)
        self.assertIsInstance(session["emotional_state"], dict)
        self.assertIsInstance(session["personality_state"], dict)
        self.assertIsInstance(session["active_projects"], list)
        self.assertIsInstance(session["learning_progress"], dict)
        
    def test_message_processing(self):
        """Test del processamento dei messaggi"""
        # Invia un messaggio di test
        message = "Ciao, come stai?"
        context = {"session_id": "test_session"}
        
        response = self.bridge.process_message(self.test_user_id, message, context)
        
        # Verifica la risposta
        self.assertIn("response", response)
        self.assertIn("emotional_state", response)
        self.assertIn("personality_state", response)
        self.assertIsInstance(response["response"], str)
        self.assertIsInstance(response["emotional_state"], dict)
        self.assertIsInstance(response["personality_state"], dict)
        
    def test_project_management(self):
        """Test della gestione dei progetti"""
        # Crea un progetto
        project_name = "Test Project"
        project_desc = "A test project"
        project_meta = {"type": "test", "priority": "high"}
        
        project_id = self.bridge.create_project(
            self.test_user_id,
            project_name,
            project_desc,
            project_meta
        )
        
        # Verifica la creazione
        self.assertIsInstance(project_id, str)
        
        # Ottieni il riepilogo
        summary = self.bridge.get_project_summary(project_id)
        self.assertEqual(summary["name"], project_name)
        self.assertEqual(summary["description"], project_desc)
        self.assertEqual(summary["metadata"]["type"], "test")
        
        # Aggiorna il progetto
        update_success = self.bridge.update_project(
            project_id,
            "In Progress",
            {"progress": 50}
        )
        self.assertTrue(update_success)
        
        # Verifica l'aggiornamento
        updated_summary = self.bridge.get_project_summary(project_id)
        self.assertEqual(updated_summary["status"], "In Progress")
        self.assertEqual(updated_summary["metadata"]["progress"], 50)
        
    def test_learning_progress(self):
        """Test del monitoraggio dell'apprendimento"""
        # Crea le preferenze dell'utente
        preferences = {
            "learning_style": {
                "style": "visual",
                "confidence": 0.8
            },
            "language": "it",
            "notifications": True,
            "theme": "dark"
        }
        self.bridge.save_user_preferences(self.test_user_id, preferences)
        
        # Ottieni il progresso
        progress = self.bridge.get_learning_progress(self.test_user_id)
        
        # Verifica il formato della risposta
        self.assertIsInstance(progress, dict)
        self.assertIn("topics", progress)
        self.assertIn("confidence_levels", progress)
        self.assertIn("recent_learning", progress)
        
    def test_emotional_analysis(self):
        """Test dell'analisi emotiva"""
        # Analizza un testo
        text = "Sono molto felice di questo risultato!"
        analysis = self.bridge.get_emotional_analysis(text)
        
        # Verifica l'analisi
        self.assertIn("primary_emotion", analysis)
        self.assertIn("intensity", analysis)
        self.assertIn("valence", analysis)
        self.assertIsInstance(analysis["intensity"], float)
        self.assertTrue(0 <= analysis["intensity"] <= 1)
        
    def test_personality_insights(self):
        """Test degli insights sulla personalità"""
        # Ottieni gli insights
        insights = self.bridge.get_personality_insights(self.test_user_id)
        
        # Verifica gli insights
        self.assertIn("communication_style", insights)
        self.assertIn("learning_preferences", insights)
        self.assertIn("interaction_patterns", insights)
        
    def test_user_preferences(self):
        """Test della gestione delle preferenze utente"""
        # Salva alcune preferenze
        preferences = {
            "language": "it",
            "notifications": True,
            "theme": "dark"
        }
        
        save_success = self.bridge.save_user_preferences(
            self.test_user_id,
            preferences
        )
        self.assertTrue(save_success)
        
    def test_conversation_history(self):
        """Test della cronologia delle conversazioni"""
        # Ottieni la cronologia
        history = self.bridge.get_conversation_history(self.test_user_id)
        
        # Verifica la struttura
        self.assertIsInstance(history, list)
        if history:  # Se ci sono messaggi
            message = history[0]
            self.assertIn("text", message)
            self.assertIn("timestamp", message)
            self.assertIn("sender", message)
            
    def test_error_handling(self):
        """Test della gestione degli errori"""
        # Test con ID progetto non valido
        with self.assertRaises(Exception):
            self.bridge.get_project_summary("invalid_id")
            
        # Test con utente non valido
        with self.assertRaises(Exception):
            self.bridge.get_learning_progress("invalid_user")
            
        # Test con preferenze non valide
        with self.assertRaises(Exception):
            self.bridge.save_user_preferences(
                self.test_user_id,
                "invalid_preferences"  # Dovrebbe essere un dict
            )

if __name__ == '__main__':
    unittest.main()
