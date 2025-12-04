import unittest
from datetime import datetime, timedelta
from .cognitive_evolution_system import (
    CognitiveEvolutionSystem,
    CognitiveStage,
    CognitiveAbility,
    AbilityCategory
)

class TestCognitiveSystem(unittest.TestCase):
    def setUp(self):
        self.system = CognitiveEvolutionSystem()
        
    def test_initial_state(self):
        """Verifica lo stato iniziale del sistema"""
        self.assertEqual(self.system.current_stage, CognitiveStage.BASIC)
        self.assertGreater(len(self.system.abilities), 0)
        self.assertEqual(self.system.experience_pool, 0.0)
        
    def test_ability_evolution(self):
        """Verifica l'evoluzione delle abilità"""
        ability_name = "pattern_recognition"
        initial_level = self.system.abilities[ability_name].current_level
        
        # Simula l'uso dell'abilità
        for _ in range(10):
            self.system.use_ability(ability_name)
            
        final_level = self.system.abilities[ability_name].current_level
        self.assertGreater(final_level, initial_level)
        
    def test_stage_progression(self):
        """Verifica la progressione degli stadi cognitivi"""
        # Porta tutte le abilità base a livello alto
        for ability in self.system.abilities.values():
            if ability.stage_requirement == CognitiveStage.BASIC:
                ability.current_level = 0.9
                ability.experience_points = 100.0
                
        self.system.check_stage_progression()
        self.assertEqual(self.system.current_stage, CognitiveStage.INTERMEDIATE)
        
    def test_ability_dependencies(self):
        """Verifica il sistema di dipendenze delle abilità"""
        analytical_thinking = self.system.abilities["analytical_thinking"]
        pattern_recognition = self.system.abilities["pattern_recognition"]
        
        # Verifica che analytical_thinking dipenda da pattern_recognition
        self.assertIn("pattern_recognition", analytical_thinking.dependencies)
        
        # Verifica che non si possa aumentare analytical_thinking se pattern_recognition è basso
        pattern_recognition.current_level = 0.1
        initial_level = analytical_thinking.current_level
        self.system.use_ability("analytical_thinking")
        self.assertAlmostEqual(analytical_thinking.current_level, initial_level)
        
    def test_skill_decay(self):
        """Verifica il decadimento delle abilità non utilizzate"""
        ability_name = "focus_control"
        ability = self.system.abilities[ability_name]
        
        # Aumenta il livello
        ability.current_level = 0.8
        ability.last_used = datetime.now() - timedelta(days=30)
        
        self.system.apply_skill_decay()
        self.assertLess(ability.current_level, 0.8)
        
if __name__ == '__main__':
    unittest.main()
