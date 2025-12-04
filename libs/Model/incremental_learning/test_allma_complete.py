import unittest
import torch
import os
import shutil
import tempfile
from Model.incremental_learning.training.allma_core import ALLMA, EmotionalSystem, Memory
from Model.incremental_learning.tokenizer import ALLMATokenizer

class TestALLMAComplete(unittest.TestCase):
    def setUp(self):
        """Inizializza l'ambiente di test"""
        self.test_dir = tempfile.mkdtemp()
        self.model = ALLMA()
        self.test_input = "Ciao, come stai?"
        self.test_response = "Sto bene, grazie!"
        
    def tearDown(self):
        """Pulisce l'ambiente dopo i test"""
        shutil.rmtree(self.test_dir)
        
    def test_initialization(self):
        """Test dell'inizializzazione del modello"""
        self.assertIsInstance(self.model.tokenizer, ALLMATokenizer)
        self.assertIsInstance(self.model.emotional_system, EmotionalSystem)
        self.assertIsInstance(self.model.memory, Memory)
        self.assertEqual(self.model.developmental_age, 0)
        
    def test_tokenizer(self):
        """Test del tokenizer"""
        # Test tokenizzazione
        tokens = self.model.tokenizer(self.test_input)
        self.assertIsInstance(tokens, torch.Tensor)
        
        # Test decodifica
        decoded = self.model.tokenizer.decode(tokens)
        self.assertIsInstance(decoded, str)
        
    def test_chat(self):
        """Test della funzione di chat"""
        # Prima aggiungiamo alcune interazioni alla memoria
        test_input = "Ciao, come stai?"
        test_response = "Ciao! Sto bene, grazie. E tu?"
        
        # Test risposta normale
        self.model.memory.add_interaction(test_input, test_response)
        response = self.model.chat(test_input)
        self.assertIsInstance(response, str)
        self.assertGreater(len(response), 0)
        self.assertNotEqual(response, "Mi dispiace, ho avuto un problema nel generare una risposta. Potresti riprovare?")
        
        # Reset della memoria per i test con temperatura
        self.model.memory.clear()
        self.model.memory.add_interaction(test_input, test_response)
        
        # Test con temperatura diversa
        responses_hot = []
        responses_cold = []
        
        # Raccogliamo più risposte con temperatura bassa
        for _ in range(5):
            responses_cold.append(self.model.chat(test_input, temperature=0.1))
        
        # Raccogliamo più risposte con temperatura alta
        for _ in range(5):
            responses_hot.append(self.model.chat(test_input, temperature=2.0))
        
        # Con temperatura alta dovremmo avere più varianti
        unique_hot = len(set(responses_hot))
        self.assertGreater(unique_hot, 1, 
                          "La temperatura alta dovrebbe produrre risposte diverse")
        
        # Con temperatura bassa dovremmo avere sempre la stessa risposta
        first_cold = responses_cold[0]
        for resp in responses_cold[1:]:
            self.assertEqual(resp, first_cold,
                           "La temperatura bassa dovrebbe produrre sempre la stessa risposta")
        
        # Le risposte con temperatura bassa dovrebbero essere uguali alla risposta base
        self.assertEqual(first_cold, test_response,
                        "La temperatura bassa dovrebbe produrre la risposta originale")
        
    def test_learning(self):
        """Test del sistema di apprendimento"""
        # Test apprendimento normale
        loss = self.model.learn(self.test_input, self.test_response)
        self.assertIsNotNone(loss)
        
        # Test apprendimento con feedback emotivo
        loss_emotional = self.model.learn(self.test_input, self.test_response, emotional_feedback=0.8)
        self.assertIsNotNone(loss_emotional)
        
    def test_emotional_system(self):
        """Test del sistema emotivo"""
        # Test analisi sentiment
        sentiment = self.model._analyze_sentiment("Sono molto felice oggi!")
        self.assertGreater(sentiment, 0.5)
        
        sentiment = self.model._analyze_sentiment("Sono molto triste oggi.")
        self.assertLess(sentiment, 0.5)
        
        # Test aggiornamento stato emotivo
        self.model.update_emotional_state("Che bella giornata!", 0.8)
        emotion = self.model.emotional_system.get_current_emotion()
        self.assertIsInstance(emotion, str)
        
    def test_memory_system(self):
        """Test del sistema di memoria"""
        # Test aggiunta in memoria
        self.model.memory.add_interaction(self.test_input, self.test_response)
        self.assertIn((self.test_input, self.test_response), self.model.memory.short_term)
        
        # Test consolidamento memoria
        self.model.consolidate_memory()
        memory_stats = self.model.get_memory_stats()
        self.assertIsInstance(memory_stats, dict)
        
    def test_save_load(self):
        """Test del salvataggio e caricamento"""
        # Salva il modello
        save_path = os.path.join(self.test_dir, "test_model.pt")
        self.model.save_model(save_path)
        self.assertTrue(os.path.exists(save_path))
        
        # Carica il modello
        new_model = ALLMA()
        new_model.load_model(save_path)
        
        # Verifica che i parametri siano stati caricati
        for p1, p2 in zip(self.model.parameters(), new_model.parameters()):
            self.assertTrue(torch.equal(p1, p2))
            
    def test_error_handling(self):
        """Test della gestione degli errori"""
        # Test input invalido
        response = self.model.chat("")
        self.assertIsInstance(response, str)
        
        # Test apprendimento con input invalido
        loss = self.model.learn("", "")
        self.assertIsNone(loss)
        
    def test_developmental_learning(self):
        """Test dell'apprendimento incrementale"""
        initial_age = self.model.developmental_age
        
        # Esegui alcuni cicli di apprendimento
        for _ in range(5):
            self.model.learn(self.test_input, self.test_response)
            
        # Verifica che l'età di sviluppo sia aumentata
        self.assertGreater(self.model.developmental_age, initial_age)
        
    def test_performance(self):
        """Test delle performance"""
        import time
        
        # Test tempo di risposta
        start_time = time.time()
        self.model.chat(self.test_input)
        response_time = time.time() - start_time
        
        # La risposta dovrebbe essere ragionevolmente veloce
        self.assertLess(response_time, 1.0)
        
if __name__ == '__main__':
    unittest.main()
