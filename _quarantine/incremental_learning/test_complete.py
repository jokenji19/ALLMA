import unittest
import torch
import os
import shutil
from datetime import datetime
from allma_model.incremental_learning.training.allma_core import ALLMA
from allma_model.incremental_learning.tokenizer import ALLMATokenizer
from allma_model.incremental_learning.persistence import ALLMAPersistence
from allma_model.incremental_learning.android_interface import ALLMAAndroidInterface
from allma_model.incremental_learning.metrics import ALLMAMetrics
from allma_model.incremental_learning.emotional_system import EmotionalSystem
from allma_model.incremental_learning.debug import ALLMADebugger

class TestALLMAComplete(unittest.TestCase):
    def setUp(self):
        # Crea directory temporanee per i test
        self.test_dir = "test_data"
        self.model_dir = os.path.join(self.test_dir, "model")
        self.persistence_dir = os.path.join(self.test_dir, "persistence")
        self.log_dir = os.path.join(self.test_dir, "logs")
        
        os.makedirs(self.test_dir, exist_ok=True)
        os.makedirs(self.model_dir, exist_ok=True)
        os.makedirs(self.persistence_dir, exist_ok=True)
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Inizializza i componenti
        self.model = ALLMA()
        self.interface = ALLMAAndroidInterface(self.model_dir, self.persistence_dir)
        self.metrics = ALLMAMetrics()
        self.debugger = ALLMADebugger(self.log_dir)
        
    def tearDown(self):
        # Pulisci le directory di test
        shutil.rmtree(self.test_dir)
        
    def test_tokenizer(self):
        """Test del sistema di tokenizzazione"""
        tokenizer = ALLMATokenizer()
        
        # Test tokenizzazione base
        text = "Hello world!"
        tokens = tokenizer.tokenize(text)
        self.assertIsInstance(tokens, torch.Tensor)
        self.assertEqual(tokens.dtype, torch.long)
        
        # Test aggiunta al vocabolario
        tokenizer.add_to_vocab("test")
        self.assertIn("test", tokenizer.vocab)
        
        # Test decode
        decoded = tokenizer.decode(tokens)
        self.assertIsInstance(decoded, str)
        
    def test_persistence(self):
        """Test del sistema di persistenza"""
        persistence = ALLMAPersistence(self.persistence_dir)
        
        # Test salvataggio checkpoint
        persistence.save_checkpoint(self.model, "test_checkpoint.pt")
        self.assertTrue(os.path.exists(os.path.join(
            self.persistence_dir, "checkpoints", "test_checkpoint.pt")))
            
        # Test creazione backup
        backup_name = persistence.create_backup()
        self.assertTrue(os.path.exists(os.path.join(
            self.persistence_dir, "backups", backup_name)))
            
    def test_android_interface(self):
        """Test dell'interfaccia Android"""
        # Test processamento input
        response = self.interface.process_input("Hello!", {
            "emotional_state": "joy",
            "feedback": 1.0
        })
        self.assertTrue(response["success"])
        self.assertIn("response", response)
        
        # Test info modello
        info = self.interface.get_model_info()
        self.assertIn("developmental_age", info)
        self.assertIn("emotional_state", info)
        
    def test_metrics(self):
        """Test del sistema di metriche"""
        # Test valutazione risposta
        metrics = self.metrics.evaluate_response(
            "Hello, how are you?",
            "Hi!",
            "Hello, I'm fine thanks!"
        )
        self.assertIn("overall_quality", metrics)
        self.assertGreaterEqual(metrics["overall_quality"], 0)
        self.assertLessEqual(metrics["overall_quality"], 1)
        
        # Test riepilogo metriche
        summary = self.metrics.get_metrics_summary()
        self.assertIsInstance(summary, dict)
        
    def test_emotional_system(self):
        """Test del sistema emotivo"""
        emotional_system = EmotionalSystem()
        
        # Test aggiornamento emozione
        emotional_system.update_emotion("joy", 0.5)
        state = emotional_system.get_emotional_state()
        self.assertGreater(state["joy"], 0)
        
        # Test emozione dominante
        dominant = emotional_system.get_dominant_emotion()
        self.assertIsInstance(dominant, str)
        
        # Test fattore di apprendimento
        factor = emotional_system.get_learning_factor()
        self.assertGreater(factor, 0)
        
    def test_debugger(self):
        """Test del sistema di debug"""
        # Test logging
        self.debugger.log_interaction(
            "test input",
            "test response",
            {"context": "test"}
        )
        
        # Test analisi performance
        self.model.emotional_system = EmotionalSystem()  # Assicurati che ci sia un sistema emotivo
        performance = self.debugger.analyze_performance(self.model)
        self.assertIn("memory", performance)
        self.assertIn("emotions", performance)
        
        # Test export
        export_file = os.path.join(self.test_dir, "debug_export.json")
        self.debugger.export_debug_data(export_file)
        self.assertTrue(os.path.exists(export_file))
        
    def test_complete_interaction(self):
        """Test di un'interazione completa"""
        # Input dell'utente
        user_input = "Hello, how are you?"
        context = {
            "emotional_state": "joy",
            "feedback": 1.0,
            "target_response": "I'm doing great, thanks for asking!"
        }
        
        # Processa l'input attraverso l'interfaccia
        response = self.interface.process_input(user_input, context)
        
        # Valuta la risposta
        metrics = self.metrics.evaluate_response(
            response["response"],
            user_input,
            context["target_response"]
        )
        
        # Log dell'interazione
        self.debugger.log_interaction(user_input, response["response"], context)
        
        # Verifica
        self.assertTrue(response["success"])
        self.assertGreater(metrics["overall_quality"], 0.5)
        
    def test_model_export(self):
        """Test dell'esportazione del modello"""
        export_path = os.path.join(self.model_dir, "mobile_model.pt")
        success = self.interface.export_for_mobile(export_path)
        self.assertTrue(success)
        self.assertTrue(os.path.exists(export_path))
        
if __name__ == '__main__':
    unittest.main()
