"""
Copyright (c) 2025 Cristof Bano. All rights reserved.
Patent Pending - ALLMA (Adaptive Learning and Language Model Architecture)

This file contains test cases for the Cognitive Evolution System.
Author: Cristof Bano
Created: January 2025

This test suite validates:
- Incremental learning capabilities
- Pattern recognition
- Cognitive adaptation
- Memory integration
"""

import unittest
from datetime import datetime, timedelta
import os
from .cognitive_evolution_system import (
    CognitiveEvolutionSystem,
    CognitiveStage,
    CognitiveAbility,
    AbilityCategory
)

class TestCognitiveEvolutionSystem(unittest.TestCase):
    def setUp(self):
        self.system = CognitiveEvolutionSystem()
        
    def test_initial_state(self):
        """Verifica lo stato iniziale del sistema"""
        self.assertEqual(self.system.current_stage, CognitiveStage.BASIC)
        self.assertTrue(len(self.system.abilities) > 0)
        self.assertEqual(self.system.experience_pool, 0.0)
        
    def test_ability_usage(self):
        """Verifica l'uso delle abilità"""
        # Usa un'abilità di base più volte per assicurarsi di guadagnare esperienza
        total_exp = 0.0
        for _ in range(10):
            result = self.system.use_ability(
                "pattern_recognition",
                {"difficulty": 1.0}  # Massima difficoltà per massimo exp
            )
            total_exp += result["experience_gained"]
            
        # Verifica che almeno uno dei tentativi abbia avuto successo
        ability = self.system.abilities["pattern_recognition"]
        self.assertTrue(total_exp > 0, "Nessuna esperienza guadagnata dopo 10 tentativi")
        self.assertTrue(ability.experience_points > 0, "L'abilità non ha accumulato esperienza")
        self.assertTrue(ability.usage_count > 0, "L'abilità non registra utilizzi")
        
    def test_prerequisites(self):
        """Verifica il sistema dei prerequisiti"""
        # Prova a usare un'abilità avanzata
        result = self.system.use_ability(
            "creative_synthesis",
            {"difficulty": 0.5}
        )
        
        # Dovrebbe fallire per prerequisiti non soddisfatti
        self.assertFalse(result["success"])
        self.assertEqual(result["error"], "Prerequisites not met")
        
    def test_ability_evolution(self):
        """Verifica l'evoluzione delle abilità"""
        ability = self.system.abilities["pattern_recognition"]
        initial_level = ability.current_level
        
        # Usa l'abilità più volte
        for _ in range(10):
            self.system.use_ability(
                "pattern_recognition",
                {"difficulty": 0.8}  # Alta difficoltà = più esperienza
            )
            
        # Verifica che il livello sia aumentato
        self.assertTrue(ability.current_level > initial_level)
        
    def test_stage_progression(self):
        """Verifica la progressione degli stadi"""
        # Aumenta artificialmente i livelli delle abilità e il conteggio utilizzi
        for ability in self.system.abilities.values():
            ability.current_level = 0.4
            ability.usage_count = 20  # Aggiungiamo anche il conteggio utilizzi
            
        # Forza un controllo dello stadio
        self.system._check_stage_evolution()
        
        # Dovrebbe essere passato a INTERMEDIATE
        self.assertEqual(self.system.current_stage, CognitiveStage.INTERMEDIATE)
        
    def test_development_summary(self):
        """Verifica il sommario dello sviluppo"""
        summary = self.system.get_development_summary()
        
        self.assertIn("current_stage", summary)
        self.assertIn("experience_pool", summary)
        self.assertIn("abilities_by_category", summary)
        self.assertIn("available_abilities", summary)
        self.assertIn("development_focus", summary)
        
    def test_ability_categories(self):
        """Verifica la categorizzazione delle abilità"""
        for ability_name in self.system.abilities:
            category = self.system._get_ability_category(ability_name)
            self.assertIsInstance(category, str)
            self.assertTrue(category in [c.value for c in AbilityCategory])
            
    def test_system_persistence(self):
        """Verifica il salvataggio e caricamento dello stato"""
        # Usa alcune abilità per generare stato
        self.system.use_ability("pattern_recognition", {"difficulty": 0.5})
        self.system.use_ability("focus_control", {"difficulty": 0.3})
        
        # Salva lo stato
        test_file = "test_cognitive_state.json"
        self.system.save_state(test_file)
        
        # Crea un nuovo sistema e carica lo stato
        new_system = CognitiveEvolutionSystem()
        new_system.load_state(test_file)
        
        # Verifica che lo stato sia stato preservato
        self.assertEqual(
            new_system.current_stage,
            self.system.current_stage
        )
        self.assertEqual(
            new_system.experience_pool,
            self.system.experience_pool
        )
        
        # Confronta le abilità
        for ability_name in self.system.abilities:
            old_ability = self.system.abilities[ability_name]
            new_ability = new_system.abilities[ability_name]
            self.assertEqual(old_ability.current_level, new_ability.current_level)
            self.assertEqual(old_ability.experience_points, new_ability.experience_points)
            
        # Pulisci
        os.remove(test_file)
        
    def test_development_suggestions(self):
        """Verifica i suggerimenti di sviluppo"""
        suggestions = self.system._suggest_development_focus()
        
        # Verifica che ci siano suggerimenti
        self.assertTrue(isinstance(suggestions, list))
        
        # Se ci sono suggerimenti, verifica la loro struttura
        for suggestion in suggestions:
            self.assertTrue(
                "ability" in suggestion or "abilities" in suggestion
            )
            self.assertIn("reason", suggestion)

if __name__ == '__main__':
    unittest.main()
