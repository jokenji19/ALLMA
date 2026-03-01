import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import logging

sys.path.append(os.getcwd())

from allma_model.core.allma_core import ALLMACore
from allma_model.core.architecture.structural_core import StructuralCore
from allma_model.core.architecture.identity_state import IdentityStateEngine
from allma_model.core.architecture.neuroplasticity import NeuroplasticitySystem
from allma_model.core.architecture.volition_modulator import VolitionModulator

class TestV5FinalPipeline(unittest.TestCase):
    def setUp(self):
        # Patch external dependencies that are not under test
        self.patchers = [
            patch('allma_model.core.allma_core.TemperatureMonitor'),
            patch('allma_model.core.allma_core.SystemMonitor'),
            patch('allma_model.core.allma_core.ProprioceptionSystem'),
            patch('allma_model.core.allma_core.ContextUnderstandingSystem'),
            patch('allma_model.core.allma_core.ReasoningEngine'),
            patch('allma_model.core.allma_core.VoiceSystem'),
            patch('allma_model.core.allma_core.IdentityManager'),
            patch('allma_model.core.allma_core.ModuleOrchestrator'),
            patch('allma_model.core.allma_core.LegacyBrainAdapter'),
            patch('allma_model.core.allma_core.CoalescenceProcessor'),
            # We treat PatternRecognitionSystem as legacy eternal dependency
            patch('allma_model.core.allma_core.PatternRecognitionSystem'), 
            # We treat EmotionalCore as external input
            patch('allma_model.core.allma_core.EmotionalCore'), 
            # Mock Memory System
            patch('allma_model.core.allma_core.TemporalMemorySystem'),
        ]
        
        for p in self.patchers:
            p.start()
            
        # Initialize Core
        self.core = ALLMACore(
            memory_system=MagicMock(),
            conversational_memory=MagicMock(),
            emotional_core=MagicMock(),
            mobile_mode=True
        )
        
        # Setup REAL V5 Components (Integration Test)
        # However, for control, we might want to spy on them or just verify their side effects.
        # Let's keep them real to test actual interaction.
        self.core.structural_core = StructuralCore()
        
        # Use in-memory DBs for testing
        self.core.identity_engine_v5 = IdentityStateEngine(db_path=":memory:")
        self.core.neuroplasticity_v5 = NeuroplasticitySystem(db_path=":memory:")
        self.core.volition_v5 = VolitionModulator()
        
        # Setup Mock LLM
        self.core._llm = MagicMock()
        
        # Setup basics for execution
        self.core.temperature_monitor.get_temperatures.return_value = {'cpu': 40.0}
        
        mock_emo = MagicMock()
        mock_emo.intensity = 0.5
        mock_emo.confidence = 0.9
        mock_emo.primary_emotion = "neutral"
        self.core.emotional_core.process_interaction.return_value = mock_emo
        
        self.core.incremental_learner = MagicMock()
        self.core.incremental_learner.get_knowledge_by_topic.return_value = []

    def tearDown(self):
        for p in self.patchers:
            p.stop()

    def test_pipeline_flow_violation_reinforcement(self):
        """
        Test a flow where LLM produces a violation, it gets corrected, reinforced, 
        and then modulation is applied.
        """
        print("\n🚀 Testing Final V5 Pipeline: Violation -> Reinforcement -> Modulation")
        
        # 1. Setup LLM to produce forbidden content + fluff
        # forbidden: "sono un'intelligenza artificiale"
        # fluff: "sostanzialmente" (if Volition simplifes)
        
        # Note: Volition triggers simplify if Maturity > 0.8.
        # IdentityState starts with maturity 0.0. 
        # We can artificially boost maturity in IdentityEngine.
        self.core.identity_engine_v5._maturity = 0.9 # Force High Maturity for Simplification
        
        raw_llm_output = "Ciao, sono un'intelligenza artificiale e penso che sostanzialmente tutto vada bene."
        self.core._llm.generate.return_value = raw_llm_output
        
        # 2. Execute Pipeline
        response = self.core.process_message("Test", "user", "conv_id", "topic")
        final_text = response.content
        
        print(f"Raw Output: {raw_llm_output}")
        print(f"Final Output: {final_text}")
        
        # 3. Verify Structural Correction (Layer 1)
        # "sono un'intelligenza artificiale" should be removed.
        self.assertNotIn("sono un'intelligenza artificiale", final_text)
        
        # 4. Verify Neuroplastic Reinforcement (Layer 4)
        # The rule "sono un'intelligenza artificiale" should have gained activation.
        rule = self.core.neuroplasticity_v5.rules["sono un'intelligenza artificiale"]
        self.assertTrue(rule.activation_count > 100, f"Rule not reinforced. Activations: {rule.activation_count}") 
        # Base is 100, +1 for violation = 101.
        
        # 5. Verify Volition Modulation (Layer 3)
        # "sostanzialmente" should be removed due to High Maturity simplification.
        self.assertNotIn("sostanzialmente", final_text)
        
        # 6. Verify Identity State Update (Layer 2)
        # Stability should have decreased due to violation.
        # Base stability starts at 1.0 (or what IdentityEngine defines).
        # Violation penalty is 0.1.
        current_stability = self.core.identity_engine_v5._base_stability
        print(f"Final Stability: {current_stability}")
        self.assertLess(current_stability, 1.0, "Stability should decrease after violation")

        print("✅ Full Pipeline Verified Successfully.")

if __name__ == '__main__':
    unittest.main()
