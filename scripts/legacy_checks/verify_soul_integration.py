
import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add project root to path
sys.path.append("/Users/erikahu/ALLMA/ALLMA_V4")

from allma_model.core.allma_core import ALLMACore
from allma_model.emotional_system.emotional_core import EmotionalState
from allma_model.soul.soul_core import SoulCore

class TestSoulIntegration(unittest.TestCase):
    @patch('allma_model.core.allma_core.pipeline') 
    @patch('allma_model.agency_system.ml_emotional_system.MLEmotionalSystem')
    def setUp(self, mock_ml_system, mock_pipeline):
        # Mock dependencies
        self.mock_soul = MagicMock()
        self.mock_soul.state.energy = 0.9 # High energy
        self.mock_soul.state.chaos = 0.8 # High chaos (Creative)
        self.mock_soul.get_volition.return_value = MagicMock(tone_modifier="Energetic/Enthusiastic")
        
        # Pass emotion_pipeline mock and mock ML system
        # We also need to mock module orchestrator to avoid it triggering things
        self.core = ALLMACore(
            db_path=":memory:", 
            mobile_mode=False, 
            emotion_pipeline=MagicMock()
        )
        # Force ML system mock into the core's emotional core if it exists
        if hasattr(self.core, 'emotional_core'):
             self.core.emotional_core.ml_system = mock_ml_system
        self.core.soul = self.mock_soul
        self.core.conversational_memory = MagicMock()
        self.core.conversational_memory.get_conversation_history.return_value = []
        self.core.incremental_learner = MagicMock()
        self.core.incremental_learner.get_knowledge_by_topic.return_value = None # Force LLM path
        self.core._llm = MagicMock()
        self.core._llm.generate.return_value = "Test response"
        
        # Identity Engine mock
        self.core.identity_engine = MagicMock()
        self.core.identity_engine.evaluate_action.return_value = (0.0, "No resistance")

    def test_process_message_calls_soul_pulse(self):
        """Verify that process_message calls soul.pulse()"""
        try:
            self.core.process_message(
                user_id="test_user", 
                conversation_id="test_conv", 
                message="Ciao ALLMA"
            )
        except Exception as e:
            print(f"Ignored error during generation (expected in mock env): {e}")

        # Check if pulse was called
        # Note: It might be called multiple times (EmotionalCore + ALLMACore), at least once is fine
        self.mock_soul.pulse.assert_called()
        print("\n✅ Soul Pulse called successfully.")

    def test_process_message_injects_soul_state(self):
        """Verify that the prompt sent to LLM contains the translated soul state"""
        self.core.process_message(
            user_id="test_user", 
            conversation_id="test_conv", 
            message="Come stai?"
        )
        
        # Check generate call args
        args, kwargs = self.core._llm.generate.call_args
        prompt = kwargs.get('prompt') or args[0]
        
        print(f"\n📝 Generated Prompt Snippet:\n...{prompt[-500:]}...")
        
        # Verify Feeling Instructions based on Energy=0.9 (set in setUp)
        expected_feeling = "Ti senti piena di vita e vibrante"
        self.assertIn(expected_feeling, prompt)
        print(f"\n✅ Found expected feeling in prompt: '{expected_feeling}'")
        
        # Verify Chaos instruction
        expected_chaos = "I tuoi pensieri sono vorticosi"
        self.assertIn(expected_chaos, prompt)
        print(f"\n✅ Found expected chaos instruction in prompt: '{expected_chaos}'")

if __name__ == '__main__':
    unittest.main()
