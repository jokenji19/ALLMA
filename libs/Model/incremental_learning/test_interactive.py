import unittest
from Model.incremental_learning.emotional_memory_integration import EmotionalMemoryIntegration

def print_interaction(prompt: str, response: str):
    print("\nUser:", prompt)
    print("ALLMA:", response)
    print("-" * 80)

class TestInteractiveScenarios(unittest.TestCase):
    def setUp(self):
        self.integration = EmotionalMemoryIntegration()
        
    def test_emotional_scenarios(self):
        """Test di diversi scenari emotivi"""
        
        # Test 1: Esperienza positiva con i gatti
        prompt = "Ho visto un gattino molto dolce oggi"
        response = self.integration.generate_response(prompt, {'is_significant': True})
        print_interaction(prompt, response)
        
        # Test 2: Memoria semantica sui gatti
        prompt = "Parlami dei gatti, cosa sai di loro?"
        response = self.integration.generate_response(prompt)
        print_interaction(prompt, response)
        
        # Test 3: Esperienza triste
        prompt = "Mi sento molto triste oggi"
        response = self.integration.generate_response(prompt, {'is_significant': True})
        print_interaction(prompt, response)
        
        # Test 4: Ricordo di una bella giornata
        prompt = "Ho passato una bellissima giornata al parco"
        response = self.integration.generate_response(prompt, {'is_significant': True})
        print_interaction(prompt, response)
        
        # Test 5: Domanda sulla giornata
        prompt = "Com'è stata la giornata?"
        response = self.integration.generate_response(prompt)
        print_interaction(prompt, response)
        
        # Test 6: Esperienza di apprendimento
        prompt = "Ho imparato molte cose nuove oggi"
        response = self.integration.generate_response(prompt, {'is_novel': True})
        print_interaction(prompt, response)
        
        # Test 7: Esperienza emozionante
        prompt = "Sono davvero entusiasta per il mio nuovo progetto!"
        response = self.integration.generate_response(prompt, {'is_significant': True})
        print_interaction(prompt, response)
        
        # Verifica che le risposte siano appropriate
        self.assertTrue(all(len(r) > 0 for r in [
            self.integration.generate_response(p) for p in [
                "Mi piacciono i gatti",
                "Sono triste",
                "Com'è la giornata?",
                "Cosa hai imparato?"
            ]
        ]))

if __name__ == '__main__':
    unittest.main()
