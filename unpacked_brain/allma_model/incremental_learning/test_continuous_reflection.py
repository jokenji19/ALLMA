import unittest
import time
from datetime import datetime
from allma_model.incremental_learning.continuous_reflection_system import ContinuousReflectionSystem, ThoughtStream, ReflectionInsight

class TestContinuousReflection(unittest.TestCase):
    def setUp(self):
        self.reflection_system = ContinuousReflectionSystem()

    def tearDown(self):
        self.reflection_system.stop_reflection()

    def test_process_experience(self):
        """Testa l'elaborazione di una nuova esperienza"""
        experience = {
            'content': 'Conversazione sulla creatività artificiale',
            'context': {'type': 'discussion'},
            'emotional_state': {'interest': 0.8, 'curiosity': 0.9}
        }
        
        self.reflection_system.process_experience(experience)
        
        # Verifica che sia stato creato un nuovo flusso di pensieri
        active_thoughts = self.reflection_system.get_active_thoughts()
        self.assertTrue(len(active_thoughts) > 0)
        
        # Verifica che il topic sia stato estratto correttamente
        self.assertEqual(active_thoughts[0].topic, 'Conversazione')

    def test_continuous_reflection(self):
        """Testa il processo di riflessione continua"""
        # Aggiungi alcune esperienze
        experiences = [
            {
                'content': 'Discussione sulla coscienza artificiale',
                'context': {'type': 'philosophical'},
                'emotional_state': {'wonder': 0.9}
            },
            {
                'content': 'Analisi delle emozioni artificiali',
                'context': {'type': 'technical'},
                'emotional_state': {'curiosity': 0.8}
            }
        ]
        
        for exp in experiences:
            self.reflection_system.process_experience(exp)
        
        # Attendi un po' per permettere la riflessione
        import time
        time.sleep(2)
        
        # Verifica che siano state generate delle intuizioni
        insights = self.reflection_system.get_current_insights()
        self.assertTrue(len(insights) > 0)
        
        # Verifica che le metriche di riflessione siano state aggiornate
        metrics = self.reflection_system.get_reflection_metrics()
        self.assertTrue(all(0 <= v <= 1 for v in metrics.values()))

    def test_thought_connection(self):
        """Testa la connessione tra pensieri correlati"""
        # Aggiungi pensieri correlati
        experiences = [
            {
                'content': 'Apprendimento delle macchine',
                'context': {'type': 'technical'},
                'emotional_state': {'interest': 0.7}
            },
            {
                'content': 'Algoritmi di apprendimento',
                'context': {'type': 'technical'},
                'emotional_state': {'interest': 0.8}
            }
        ]
        
        for exp in experiences:
            self.reflection_system.process_experience(exp)
        
        # Attendi la generazione di connessioni
        time.sleep(2)
        
        # Verifica che esistano connessioni tra i pensieri
        thoughts = self.reflection_system.get_active_thoughts()
        self.assertTrue(any(len(t.connected_streams) > 0 for t in thoughts))

    def test_insight_generation(self):
        """Testa la generazione di intuizioni"""
        experience = {
            'content': 'Riflessione sulla natura della coscienza',
            'context': {'type': 'philosophical'},
            'emotional_state': {'wonder': 1.0, 'curiosity': 0.9}
        }
        
        self.reflection_system.process_experience(experience)
        
        # Attendi la generazione di intuizioni
        time.sleep(2)
        
        # Verifica le intuizioni generate
        insights = self.reflection_system.get_current_insights()
        if insights:
            insight = insights[0]
            self.assertIsInstance(insight, ReflectionInsight)
            self.assertTrue(0 <= insight.confidence <= 1)
            self.assertTrue(isinstance(insight.timestamp, datetime))

if __name__ == '__main__':
    unittest.main()
