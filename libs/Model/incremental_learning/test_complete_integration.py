import unittest
import numpy as np
import time
from Model.incremental_learning.pattern_recognition_system import PatternRecognitionSystem, Pattern
from Model.incremental_learning.emotional_adaptation_system import EmotionalAdaptationSystem
from Model.incremental_learning.social_learning_system import SocialLearningSystem
from Model.incremental_learning.meta_learning_system import MetaLearningSystem

class TestCompleteIntegration(unittest.TestCase):
    def setUp(self):
        """Inizializza i sistemi per i test"""
        self.pattern_system = PatternRecognitionSystem()
        self.emotional_system = EmotionalAdaptationSystem()
        self.social_system = SocialLearningSystem()
        self.meta_system = MetaLearningSystem()
        
        # Configura le connessioni tra i sistemi
        self.pattern_system.register_observer(self.emotional_system)
        self.pattern_system.register_observer(self.social_system)
        
        # Registra i sistemi con i nomi corretti
        self.meta_system.register_system(self.pattern_system, "pattern_recognition")
        self.meta_system.register_system(self.emotional_system, "emotional_adaptation")
        self.meta_system.register_system(self.social_system, "social_learning")
    
    def test_complete_system_integration(self):
        """Test di integrazione completa tra tutti i sistemi"""
        # 1. Creazione e apprendimento di pattern base
        features = [1.0, 0.0, 0.0]
        pattern = self.pattern_system.learn_pattern(features, "test_category")
        
        self.assertIsNotNone(pattern)
        self.assertTrue(pattern.validation_history[-1].is_valid)
        
        # 2. Risposta emotiva al pattern
        emotional_response = self.emotional_system.process_pattern(pattern)
        self.assertIsNotNone(emotional_response)
        self.assertGreater(emotional_response.intensity, 0.0)
        
        # 3. Apprendimento sociale
        social_feedback = self.social_system.evaluate_pattern(pattern)
        self.assertIsNotNone(social_feedback)
        self.assertTrue(hasattr(social_feedback, 'acceptance_score'))
        
        # 4. Meta-apprendimento e ottimizzazione
        meta_insights = self.meta_system.analyze_learning_process()
        self.assertIsNotNone(meta_insights)
        self.assertTrue(len(meta_insights) > 0)
        
        # 5. Test di evoluzione integrata
        # Simula una sequenza di apprendimento con feedback multipli
        for _ in range(5):
            # Genera features leggermente diverse
            noise = np.random.normal(0, 0.1, 3)
            new_features = np.clip(np.array(features) + noise, 0, 1)
            new_features = new_features / np.sum(new_features)
            
            # Apprende il nuovo pattern
            new_pattern = self.pattern_system.learn_pattern(new_features.tolist(), "test_category")
            
            # Processa le risposte emotive e sociali
            emotional_response = self.emotional_system.process_pattern(new_pattern)
            social_feedback = self.social_system.evaluate_pattern(new_pattern)
            
            # Verifica che il sistema stia evolvendo
            self.assertGreater(new_pattern.stability_score, 0.0)
            self.assertGreater(emotional_response.intensity, 0.0)
            self.assertGreater(social_feedback.acceptance_score, 0.0)
            
            time.sleep(0.1)  # Simula il passaggio del tempo
            
        # 6. Verifica l'apprendimento meta-cognitivo
        final_insights = self.meta_system.analyze_learning_process()
        self.assertTrue(len(final_insights) > len(meta_insights))
        
        # 7. Test di generalizzazione
        similar_features = [0.9, 0.1, 0.0]
        recognition_results = self.pattern_system.recognize_pattern(similar_features)
        
        self.assertTrue(len(recognition_results) > 0)
        best_match = recognition_results[0]
        self.assertGreater(best_match.similarity, 0.7)
        
        # 8. Test di adattamento emotivo
        emotional_adaptation = self.emotional_system.get_adaptation_state()
        self.assertIsNotNone(emotional_adaptation)
        self.assertTrue(hasattr(emotional_adaptation, 'sensitivity'))
        
        # 9. Test di apprendimento sociale avanzato
        social_knowledge = self.social_system.get_collective_knowledge()
        self.assertIsNotNone(social_knowledge)
        self.assertTrue(len(social_knowledge) > 0)
        
        # 10. Verifica dello stato complessivo del sistema
        system_state = self.meta_system.get_system_state()
        self.assertIsNotNone(system_state)
        self.assertTrue(all(component in system_state 
                          for component in ['pattern_recognition', 'emotional_adaptation', 'social_learning']))
    
    def test_stress_integration(self):
        """Test di integrazione sotto stress"""
        # Genera molti pattern diversi rapidamente
        num_patterns = 50
        categories = ["cat_A", "cat_B", "cat_C"]
        
        for _ in range(num_patterns):
            # Genera features casuali
            features = np.random.random(3)
            features = features / np.sum(features)
            category = np.random.choice(categories)
            
            # Processa il pattern attraverso tutti i sistemi
            pattern = self.pattern_system.learn_pattern(features.tolist(), category)
            self.emotional_system.process_pattern(pattern)
            self.social_system.evaluate_pattern(pattern)
            
            if _ % 10 == 0:  # Ogni 10 pattern
                self.meta_system.analyze_learning_process()
        
        # Verifica che i sistemi siano ancora funzionanti
        self.assertTrue(len(self.pattern_system.get_all_patterns()) > 0)
        self.assertIsNotNone(self.emotional_system.get_adaptation_state())
        self.assertTrue(len(self.social_system.get_collective_knowledge()) > 0)
        
    def test_error_recovery(self):
        """Test di recupero da errori e situazioni anomale"""
        # 1. Test con features invalide
        with self.assertRaises(ValueError):
            self.pattern_system.learn_pattern([], "test")
        
        # Verifica che il sistema sia ancora funzionante
        valid_features = [1.0, 0.0, 0.0]
        pattern = self.pattern_system.learn_pattern(valid_features, "test")
        self.assertIsNotNone(pattern)
        
        # 2. Test con pattern corrotto
        current_time = time.time()
        corrupted_pattern = Pattern(
            id=str(current_time),
            features=np.array([-1.0, -1.0, -1.0]),
            category="test",
            creation_time=current_time,
            last_update=current_time,
            occurrences=0,
            stability_score=0.0
        )
        emotional_response = self.emotional_system.process_pattern(corrupted_pattern)
        self.assertIsNotNone(emotional_response)  # Il sistema dovrebbe gestire il pattern corrotto
        
        # 3. Test di sovraccarico del sistema meta
        for _ in range(100):  # Genera molte richieste rapidamente
            self.meta_system.analyze_learning_process()
        
        # Verifica che il sistema sia ancora responsivo
        self.assertIsNotNone(self.meta_system.get_system_state())
        
    def tearDown(self):
        """Pulisce dopo i test"""
        self.pattern_system = None
        self.emotional_system = None
        self.social_system = None
        self.meta_system = None

if __name__ == '__main__':
    unittest.main()
