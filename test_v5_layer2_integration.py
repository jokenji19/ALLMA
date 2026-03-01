import unittest
from unittest.mock import MagicMock, patch, ANY
import sys
import os
import logging
from dataclasses import dataclass

sys.path.append(os.getcwd())

from allma_model.core.allma_core import ALLMACore
# Mock classes needed for patching
@dataclass
class MockIdentityState:
    maturity: float = 0.5
    stability: float = 0.9
    entropy_index: float = 0.8
    drift_index: float = 0.1
    under_duress: bool = False
    creative_mode: bool = True

class TestIdentityStateIntegration(unittest.TestCase):
    def setUp(self):
        # Heavy Patching again
        with patch('allma_model.core.allma_core.TemperatureMonitor'), \
             patch('allma_model.core.allma_core.SystemMonitor'), \
             patch('allma_model.core.allma_core.ProprioceptionSystem'), \
             patch('allma_model.core.allma_core.ContextUnderstandingSystem'), \
             patch('allma_model.core.allma_core.ReasoningEngine'), \
             patch('allma_model.core.allma_core.DreamManager'), \
             patch('allma_model.core.allma_core.ProactiveAgency'), \
             patch('allma_model.core.allma_core.VisionSystem'), \
             patch('allma_model.core.allma_core.VoiceSystem'), \
             patch('allma_model.core.allma_core.ModuleOrchestrator'), \
             patch('allma_model.core.allma_core.LegacyBrainAdapter'), \
             patch('allma_model.core.allma_core.CoalescenceProcessor'), \
             patch('allma_model.core.allma_core.IdentityManager'), \
             patch('allma_model.core.allma_core.StructuralCore'), \
             patch('allma_model.core.allma_core.IdentityStateEngine') as MockEngine:
             
            self.core = ALLMACore(
                memory_system=MagicMock(),
                conversational_memory=MagicMock(),
                emotional_core=MagicMock(),
                mobile_mode=True
            )
            # Fix: Temperature monitor must return dict with numbers
            self.core.temperature_monitor.get_temperatures.return_value = {'cpu': 40.0}

            # Grab the instance of the engine created inside ALLMACore
            self.mock_engine_instance = self.core.identity_engine_v5
    
    def test_bidirectional_pipeline(self):
        print("\n🧪 Testing Layer 2 Pipeline (Compute -> Inject -> Update)...")
        
        # 1. Setup Mock State return
        mock_state = MockIdentityState()
        self.mock_engine_instance.compute_state.return_value = mock_state
        
        # 2. Setup Mock LLM and Dependencies
        self.core._llm = MagicMock()
        self.core._llm.generate.return_value = "Response text."
        self.core.incremental_learner = MagicMock()
        self.core.incremental_learner.get_knowledge_by_topic.return_value = []
        
        # Setup Structural Core to return specific violations
        self.core.structural_core.validate.return_value = ("Clean text.", True, [])
        
        # Emotion setup
        mock_emo_state = MagicMock()
        mock_emo_state.intensity = 0.7
        mock_emo_state.confidence = 0.9 # Fix: Must be float for > comparison
        mock_emo_state.primary_emotion = "joy"
        self.core.emotional_core.process_interaction.return_value = mock_emo_state
        
        # 3. Execute process_message
        self.core.process_message("Hello", "user", "conv_id", "topic")
        
        # 4. Verify COMPUTE STATE called PRE-GENERATION
        self.mock_engine_instance.compute_state.assert_called_once()
        # Check if context metrics were passed (e.g. emotional intensity)
        call_args = self.mock_engine_instance.compute_state.call_args[0][0]
        self.assertEqual(call_args['emotional_intensity'], 0.7)
        print("✅ Phase A (Compute) Verified.")
        
        # 5. Verify PROMPT INJECTION
        # Since ReasoningEngine is mocked, it returns a MagicMock prompt. 
        # We must check that _build_reasoning_prompt was called with our system instruction.
        
        # Get the call args of reasoning_engine._build_reasoning_prompt
        # It's called as: _build_reasoning_prompt(message, context_data)
        build_call = self.core.reasoning_engine._build_reasoning_prompt.call_args
        self.assertIsNotNone(build_call, "ReasoningEngine._build_reasoning_prompt was not called!")
        
        args, kwargs = build_call
        context_passed = args[1] if len(args) > 1 else kwargs.get('context_data')
        
        self.assertIn('system_instruction', context_passed, "system_instruction missing from context_data")
        v5_prompt = context_passed['system_instruction']
        
        self.assertIn("STATO V5:", v5_prompt)
        self.assertIn("MATURITÀ: 0.50", v5_prompt)
        print("✅ Phase B (Injection) Verified via ReasoningEngine args.")
        
        # 6. Verify UPDATE STATE called POST-VALIDATION
        # It should be called with the text returned by StructuralCore ("Clean text.")
        self.mock_engine_instance.update_state.assert_called_once_with(
            validated_text="Clean text.",
            violations=[]
        )
        print("✅ Phase D (Update) Verified.")

if __name__ == '__main__':
    unittest.main()
