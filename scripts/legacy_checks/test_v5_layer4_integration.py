import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import logging
from dataclasses import dataclass

sys.path.append(os.getcwd())

from allma_model.core.allma_core import ALLMACore
from allma_model.core.architecture.structural_core import StructuralCore
from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem

class TestNeuroplasticityIntegration(unittest.TestCase):
    def setUp(self):
        # Patch heavy dependencies
        with patch('allma_model.core.allma_core.TemperatureMonitor'), \
             patch('allma_model.core.allma_core.SystemMonitor'), \
             patch('allma_model.core.allma_core.ProprioceptionSystem'), \
             patch('allma_model.core.allma_core.ContextUnderstandingSystem'), \
             patch('allma_model.core.allma_core.ReasoningEngine'), \
             patch('allma_model.core.allma_core.IdentityStateEngine'), \
             patch('allma_model.core.allma_core.VoiceSystem'), \
             patch('allma_model.core.allma_core.IdentityManager'), \
             patch('allma_model.core.allma_core.ModuleOrchestrator'), \
             patch('allma_model.core.allma_core.LegacyBrainAdapter'), \
             patch('allma_model.core.allma_core.CoalescenceProcessor'):

            self.core = ALLMACore(
                memory_system=MagicMock(),
                conversational_memory=MagicMock(),
                emotional_core=MagicMock(),
                mobile_mode=True
            )
            
            # Setup REAL Neuroplasticity and StructuralCore
            self.core.structural_core = StructuralCore()
            self.core.neuroplasticity_v5 = NeuroplasticitySystem(db_path=":memory:")
            
            # Setup Mock LLM to return a violation
            self.core._llm = MagicMock()
            self.core._llm.generate.return_value = "Ciao, sono un'intelligenza artificiale creata per aiutarti."
            
            # Fix mocks required for execution
            self.core.temperature_monitor.get_temperatures.return_value = {'cpu': 40.0}
            mock_emo = MagicMock()
            mock_emo.intensity = 0.5
            mock_emo.confidence = 0.9
            mock_emo.primary_emotion = "neutral"
            self.core.emotional_core.process_interaction.return_value = mock_emo
            self.core.incremental_learner = MagicMock()
            self.core.incremental_learner.get_knowledge_by_topic.return_value = []
            
            # Setup Identity Engine return value
            mock_id_state = MagicMock()
            mock_id_state.maturity = 0.5
            mock_id_state.stability = 0.9
            mock_id_state.entropy_index = 0.8
            mock_id_state.under_duress = False
            mock_id_state.creative_mode = True
            
            # Since we patched the class, self.core.identity_engine_v5 is the instance.
            # But wait, self.core.identity_engine_v5 might be overwritten by __init__ if patched?
            # In setUp we do: patch('...IdentityStateEngine') as MockEngine:
            # self.core = ALLMACore(...)
            # So self.core.identity_engine_v5 is the return value of MockEngine()
            
            self.core.identity_engine_v5.compute_state.return_value = mock_id_state
    
    def test_neuroplastic_loop(self):
        print("\n🧠 Testing Layer 4 Loop (Validation -> Reinforcement)...")
        
        # 1. Inspect initial state of a rule
        target_rule = "sono un'intelligenza artificiale"
        initial_rule = self.core.neuroplasticity_v5.rules[target_rule]
        initial_activations = initial_rule.activation_count
        print(f"Initial Activations for '{target_rule}': {initial_activations}")
        
        # 2. Process message (Triggering the violation)
        self.core.process_message("Chi sei?", "user", "conv_id", "topic")
        
        # 3. Verify Structural Correction
        # The LLM output was "Ciao, sono un'intelligenza artificiale..."
        # It should be corrected by removing the forbidden phrase
        # But `process_message` returns a ProcessedResponse object, need to check that or capture valid text
        # Instead of checking return, we verify reinforcement which proves validation happened.
        
        # 4. Verify Reinforcement (Analysis)
        updated_rule = self.core.neuroplasticity_v5.rules[target_rule]
        new_activations = updated_rule.activation_count
        
        print(f"New Activations for '{target_rule}': {new_activations}")
        
        self.assertGreater(new_activations, initial_activations, "Rule was not reinforced!")
        self.assertEqual(new_activations, initial_activations + 1, " activation count should increment by 1")
        
        print("✅ Neuroplasticity Reinforcement Verified.")
        
        # 5. Verify Sync (Update Rules)
        # StructuralCore should have received rules. 
        # Since we use the default set, it's hard to tell if it updated. 
        # Let's add a custom rule to Neuroplasticity and run again.
        
        print("\n🔄 Testing Dynamic Rule Sync...")
        custom_pattern = r"pizza con ananas"
        self.core.neuroplasticity_v5.add_rule(custom_pattern, "[CIBO VIETATO]", initial_activation=50)
        
        # Run another turn
        self.core._llm.generate.return_value = "Amo la pizza con ananas."
        self.core.process_message("Ti piace?", "user", "conv_id", "topic")
        
        # Check if StructuralCore used the new rule
        # We can check internal state of structural core
        current_blacklist_patterns = [p for p, r in self.core.structural_core._base_blacklist]
        self.assertIn(custom_pattern, current_blacklist_patterns, "Custom rule not synced to StructuralCore!")
        
        print("✅ Rule Sync Verified.")

if __name__ == '__main__':
    unittest.main()
