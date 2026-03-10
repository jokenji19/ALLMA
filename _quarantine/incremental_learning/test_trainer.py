import unittest
import sys
import os
from pathlib import Path
import logging
import torch

# Aggiungi il percorso della directory principale al PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

from allma_model.incremental_learning.training.natural_trainer import NaturalTrainer, TrainingMetrics
from allma_model.incremental_learning.training.initial_experiences import DevelopmentalStage
from allma_model.incremental_learning.training.allma_core import ALLMA

class TestNaturalTrainer(unittest.TestCase):
    def setUp(self):
        """Setup per i test"""
        # Configura logging per il test
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Inizializza il modello
        self.model = ALLMA()
        
        # Inizializza il trainer
        self.trainer = NaturalTrainer(
            model=self.model,
            experiences_file='data/initial_experiences.json',
            checkpoint_dir='test_checkpoints',
            batch_size=1
        )

    def test_developmental_progression(self):
        """Testa la progressione dello sviluppo attraverso gli stadi"""
        print("\nTest Progressione Sviluppo")
        
        # Test primi passi dello sviluppo sensomotorio precoce
        metrics = self.trainer.train_developmental_stage(
            DevelopmentalStage.SENSORIMOTOR_EARLY,
            num_experiences=10
        )
        
        print(f"\nMetriche dopo sviluppo sensomotorio precoce:")
        print(f"Età di sviluppo: {metrics.developmental_age:.2f} settimane")
        print(f"Stabilità emotiva: {metrics.emotional_stability:.2f}")
        print(f"Coerenza risposte: {metrics.response_coherence:.2f}")
        
        self.assertGreater(metrics.developmental_age, 0)
        self.assertGreater(metrics.emotional_stability, 0)
        self.assertGreater(metrics.response_coherence, 0)

    def test_emotional_learning(self):
        """Testa l'influenza delle emozioni sull'apprendimento"""
        print("\nTest Apprendimento Emotivo")
        
        # Simula un'esperienza positiva
        happy_experience = {
            'input': 'Cucù!',
            'response': '*sorriso*',
            'emotion': 'happy',
            'context': {'physical_state': 'rested'},
            'stage': 'sensorimotor_mid'
        }
        
        loss_happy = self.trainer._process_experience(happy_experience)
        
        # Simula un'esperienza negativa
        sad_experience = {
            'input': '*rumore forte*',
            'response': '*pianto*',
            'emotion': 'sad',
            'context': {'physical_state': 'tired'},
            'stage': 'sensorimotor_early'
        }
        
        loss_sad = self.trainer._process_experience(sad_experience)
        
        print(f"\nLoss con emozione positiva: {loss_happy:.4f}")
        print(f"Loss con emozione negativa: {loss_sad:.4f}")
        
        # La loss dovrebbe essere minore per esperienze positive
        self.assertLess(loss_happy, loss_sad)

    def test_sleep_consolidation(self):
        """Testa il consolidamento durante il sonno"""
        print("\nTest Consolidamento Sonno")
        
        # Forza il bisogno di sonno
        self.trainer.sleep_system.memories_since_sleep = 150
        
        # Verifica che il sistema richieda il sonno
        needs_sleep = self.trainer.sleep_system.needs_sleep()
        self.assertTrue(needs_sleep)
        
        # Esegui ciclo di sonno
        initial_retention = self.trainer.metrics.memory_retention
        self.trainer._sleep_cycle()
        final_retention = self.trainer.metrics.memory_retention
        
        print(f"\nRitenzione memoria pre-sonno: {initial_retention:.4f}")
        print(f"Ritenzione memoria post-sonno: {final_retention:.4f}")
        
        # La ritenzione dovrebbe migliorare dopo il sonno
        self.assertGreater(final_retention, initial_retention)

    def test_critical_period(self):
        """Testa l'adattamento del learning rate durante i periodi critici"""
        print("\nTest Periodo Critico")
        
        # Test learning rate in fase precoce
        early_lr = self.trainer.critical_period.get_learning_rate(0.001)
        
        # Simula passaggio del tempo
        for _ in range(100):
            self.trainer.critical_period.update()
        
        # Test learning rate in fase più avanzata
        late_lr = self.trainer.critical_period.get_learning_rate(0.001)
        
        print(f"\nLearning rate iniziale: {early_lr:.6f}")
        print(f"Learning rate dopo periodo: {late_lr:.6f}")
        
        # Il learning rate dovrebbe diminuire col tempo
        self.assertGreater(early_lr, late_lr)

    def test_complete_development(self):
        """Testa un ciclo completo di sviluppo abbreviato"""
        print("\nTest Sviluppo Completo")
        
        stages = [
            (DevelopmentalStage.SENSORIMOTOR_EARLY, 5),
            (DevelopmentalStage.SENSORIMOTOR_MID, 5),
            (DevelopmentalStage.SENSORIMOTOR_LATE, 5),
            (DevelopmentalStage.PREOPERATIONAL_EARLY, 5),
            (DevelopmentalStage.PREOPERATIONAL_LATE, 5)
        ]
        
        initial_metrics = None
        final_metrics = None
        
        for stage, num_experiences in stages:
            print(f"\nTraining stadio: {stage.value}")
            metrics = self.trainer.train_developmental_stage(stage, num_experiences)
            
            if initial_metrics is None:
                initial_metrics = metrics
            final_metrics = metrics
        
        print("\nConfronti sviluppo:")
        print(f"Età iniziale: {initial_metrics.developmental_age:.2f} settimane")
        print(f"Età finale: {final_metrics.developmental_age:.2f} settimane")
        print(f"Stabilità emotiva iniziale: {initial_metrics.emotional_stability:.2f}")
        print(f"Stabilità emotiva finale: {final_metrics.emotional_stability:.2f}")
        
        self.assertGreater(final_metrics.developmental_age, initial_metrics.developmental_age)
        self.assertGreater(final_metrics.emotional_stability, initial_metrics.emotional_stability)

    def tearDown(self):
        """Pulizia dopo i test"""
        # Rimuovi i checkpoint di test
        import shutil
        if os.path.exists('test_checkpoints'):
            shutil.rmtree('test_checkpoints')

if __name__ == '__main__':
    unittest.main(verbosity=2)
