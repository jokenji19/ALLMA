import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import logging
from dataclasses import dataclass

sys.path.append(os.getcwd())

from allma_model.core.allma_core import ALLMACore
from allma_model.core.architecture.volition_modulator import VolitionModulator

@dataclass
class MockIdentityState:
    maturity: float = 0.5
    stability: float = 0.9
    entropy_index: float = 0.8
    drift_index: float = 0.1
    under_duress: bool = False
    creative_mode: bool = True

class TestVolitionIntegration(unittest.TestCase):
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
             patch('allma_model.core.allma_core.CoalescenceProcessor'), \
             patch('allma_model.core.allma_core.StructuralCore'), \
             patch('allma_model.core.allma_core.NeuroplasticitySystem'):

            self.core = ALLMACore(
                memory_system=MagicMock(),
                conversational_memory=MagicMock(),
                emotional_core=MagicMock(),
                mobile_mode=True
            )
            
            # Setup Real Volition
            self.core.volition_v5 = VolitionModulator()
            
            # Mock other layers
            self.core.structural_core.validate.side_effect = lambda t: (t, True, [])
            self.core.temperature_monitor.get_temperatures.return_value = {'cpu': 40.0}
            
            # Fix LLM Mock
            self.core._llm = MagicMock()
            self.core._llm.generate.return_value = "Response"
            
            mock_emo = MagicMock()
            mock_emo.intensity = 0.5
            mock_emo.confidence = 0.9
            mock_emo.primary_emotion = "neutral"
            self.core.emotional_core.process_interaction.return_value = mock_emo
            self.core.incremental_learner = MagicMock()
            self.core.incremental_learner.get_knowledge_by_topic.return_value = []
    
    def test_simplify_strategy(self):
        print("\n🎭 Testing Volition: SIMPLIFY Strategy...")
        
        # 1. Setup High Maturity State
        mock_state = MockIdentityState(maturity=0.9, entropy_index=0.5, under_duress=False)
        self.core.identity_engine_v5.compute_state.return_value = mock_state
        
        # 2. Setup LLM output with fluff
        fluffy_text = "Penso che sia veramente davvero un po' importante sostanzialmente ascoltare."
        self.core._llm = MagicMock()
        self.core._llm.generate.return_value = fluffy_text
        
        # 3. Process
        # We need to capture the final output. 
        # Since process_message logs the final answer, we can check the return object or mock logging.
        # But process_message returns a ProcessedResponse.
        
        response = self.core.process_message("Test", "user", "conv_id", "topic")
        
        # 4. Verify Simplification
        # "veramente", "davvero", "un po'", "sostanzialmente" should be gone.
        expected_text = "Penso che sia importante ascoltare."
        
        print(f"Original: '{fluffy_text}'")
        print(f"Modulated: '{response.content}'")
        
        self.assertNotIn("sostanzialmente", response.content)
        self.assertNotIn("davvero", response.content)
        self.assertLess(len(response.content), len(fluffy_text))
        print("✅ Simplification Verified.")

    def test_direct_strategy(self):
        print("\n🎭 Testing Volition: DIRECT Strategy (Duress)...")
        
        # 1. Setup Duress State
        mock_state = MockIdentityState(maturity=0.5, under_duress=True)
        self.core.identity_engine_v5.compute_state.return_value = mock_state
        
        # 2. Setup Indirect LLM output
        indirect_text = "Vorrei suggerirti di provare a riavviare il sistema."
        self.core._llm.generate.return_value = indirect_text
        
        # 3. Process
        response = self.core.process_message("Aiuto", "user", "conv_id", "topic")
        
        # 4. Verify Directness
        # "Vorrei suggerirti di" -> "dovresti" or removed based on logic
        # My Direct logic replacements: (r"\bvorrei suggerirti di\b", "dovresti")
        
        expected_fragment = "dovresti provare"
        print(f"Original: '{indirect_text}'")
        print(f"Modulated: '{response.content}'")
        
        self.assertIn("dovresti", response.content)
        print("✅ Directness Verified.")

if __name__ == '__main__':
    unittest.main()
