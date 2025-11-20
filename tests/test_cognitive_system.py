import unittest
from Model.incremental_learning.cognitive_evolution_system import CognitiveEvolutionSystem

class TestCognitiveSystem(unittest.TestCase):
    def setUp(self):
        self.cognitive_system = CognitiveEvolutionSystem()

    def test_process_experience_valid(self):
        """Test che il sistema gestisca correttamente esperienze valide"""
        experience = {
            "input": "Ho imparato qualcosa di nuovo",
            "type": "learning",
            "context": {"domain": "science"}
        }
        result = self.cognitive_system.process_experience(experience)
        self.assertGreater(result, 0)
        
    def test_process_experience_empty(self):
        """Test che il sistema gestisca correttamente esperienze vuote"""
        with self.assertRaises(ValueError):
            self.cognitive_system.process_experience({})
            
    def test_process_experience_invalid_input(self):
        """Test che il sistema gestisca correttamente input non validi"""
        with self.assertRaises(ValueError):
            self.cognitive_system.process_experience({"input": ""})
            
    def test_ability_transfer(self):
        """Test che l'apprendimento si trasferisca tra abilità correlate"""
        experience1 = {
            "input": "Ho risolto un problema matematico",
            "type": "problem_solving",
            "context": {"domain": "math"}
        }
        experience2 = {
            "input": "Ho applicato lo stesso metodo a un altro problema",
            "type": "learning",
            "context": {"domain": "physics"}
        }
        
        initial_abilities = self.cognitive_system.get_state()
        self.cognitive_system.process_experience(experience1)
        self.cognitive_system.process_experience(experience2)
        final_abilities = self.cognitive_system.get_state()
        
        # Verifica che ci sia stato un miglioramento in più abilità
        improved_abilities = 0
        for ability in final_abilities:
            if final_abilities[ability] > initial_abilities[ability]:
                improved_abilities += 1
        self.assertGreater(improved_abilities, 1)

if __name__ == '__main__':
    unittest.main()
