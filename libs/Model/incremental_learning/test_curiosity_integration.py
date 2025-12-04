import unittest
from Model.incremental_learning.emotional_memory_integration import EnhancedMemorySystem
from Model.incremental_learning.curiosity_system import CuriosityDrive

class TestCuriosityIntegration(unittest.TestCase):
    def setUp(self):
        self.memory_system = EnhancedMemorySystem()

    def test_initial_state(self):
        """Testa lo stato iniziale del sistema integrato"""
        self.assertIsInstance(self.memory_system.curiosity, CuriosityDrive)
        self.assertEqual(self.memory_system.curiosity.development_state['knowledge_level'], 0.0)
        self.assertEqual(len(self.memory_system.episodic), 0)

    def test_learning_progression(self):
        """Testa la progressione dell'apprendimento"""
        # Prima interazione
        response1 = self.memory_system.process_input("Ciao, sono curioso di imparare!")
        self.assertIn('questions', response1)
        self.assertIn('emotional_state', response1)
        initial_knowledge = response1['development_state']['knowledge_level']

        # Seconda interazione
        response2 = self.memory_system.process_input("Mi piace molto imparare cose nuove!")
        self.assertTrue(response2['development_state']['knowledge_level'] > initial_knowledge)

    def test_curiosity_emotional_integration(self):
        """Testa l'integrazione tra curiosità ed emozioni"""
        response = self.memory_system.process_input("Sono molto emozionato di scoprire cose nuove!")
        
        # Verifica la presenza di stati emotivi legati alla curiosità
        self.assertIn('curiosity', response['emotional_state'])
        self.assertIn('wonder', response['emotional_state'])
        self.assertTrue(response['emotional_state']['curiosity'] > 0)

    def test_memory_curiosity_interaction(self):
        """Testa l'interazione tra memoria e curiosità"""
        # Prima memoria
        self.memory_system.process_input("I gatti sono animali interessanti")
        
        # Seconda memoria correlata
        response = self.memory_system.process_input("Mi chiedo come fanno i gatti a essere così agili")
        
        # Verifica che il sistema generi domande pertinenti
        self.assertTrue(any('gatti' in q.lower() for q in response['questions']))
        
    def test_curiosity_development(self):
        """Testa lo sviluppo della curiosità nel tempo"""
        initial_complexity = self.memory_system.curiosity.development_state['question_complexity']
        
        # Simula diverse interazioni
        for _ in range(5):
            self.memory_system.process_input("Nuova informazione interessante!")
            
        final_complexity = self.memory_system.curiosity.development_state['question_complexity']
        self.assertTrue(final_complexity > initial_complexity)

    def test_reward_system(self):
        """Testa il sistema di ricompensa"""
        response = self.memory_system.process_input("Una nuova scoperta molto interessante!")
        self.assertIn('reward', response)
        self.assertTrue(0 <= response['reward'] <= 1)

if __name__ == '__main__':
    unittest.main()
