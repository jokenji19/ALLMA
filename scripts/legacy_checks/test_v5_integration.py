import unittest
from unittest.mock import MagicMock, patch
import sys
import os
import logging

# Add root to path
sys.path.append(os.getcwd())

# Import ALLMACore (and silence its heavy imports during test if possible, 
# but we need it loaded to test integration)
from allma_model.core.allma_core import ALLMACore
from allma_model.response_system.contextual_response import ProcessedResponse

# Configure logging to see our prints
logging.basicConfig(level=logging.INFO)

class TestStructuralCoreIntegration(unittest.TestCase):
    def setUp(self):
        # Mock dependencies to avoid heavy initialization
        self.mock_memory = MagicMock()
        self.mock_conv_memory = MagicMock()
        self.mock_knowledge = MagicMock()
        self.mock_project = MagicMock()
        self.mock_emotional = MagicMock()
        self.mock_prefs = MagicMock()
        self.mock_response_gen = MagicMock()
        self.mock_learner = MagicMock()
        self.mock_personality = MagicMock()
        self.mock_coalescence = MagicMock() # Mock attributes added in init
        
        # Patch heavy internal components that are instantiated inside __init__
        with patch('allma_model.core.allma_core.TemperatureMonitor'), \
             patch('allma_model.core.allma_core.SystemMonitor'), \
             patch('allma_model.core.allma_core.IdentityManager'), \
             patch('allma_model.core.allma_core.ProprioceptionSystem'), \
             patch('allma_model.core.allma_core.ContextUnderstandingSystem'), \
             patch('allma_model.core.allma_core.ReasoningEngine'), \
             patch('allma_model.core.allma_core.DreamManager'), \
             patch('allma_model.core.allma_core.ProactiveAgency'), \
             patch('allma_model.core.allma_core.VisionSystem'), \
             patch('allma_model.core.allma_core.ProactiveAgency'), \
             patch('allma_model.core.allma_core.VisionSystem'), \
             patch('allma_model.core.allma_core.VoiceSystem'), \
             patch('allma_model.core.allma_core.ModuleOrchestrator'), \
             patch('allma_model.core.allma_core.LegacyBrainAdapter'), \
             patch('allma_model.core.allma_core.CoalescenceProcessor'):
             
            self.core = ALLMACore(
                memory_system=self.mock_memory,
                conversational_memory=self.mock_conv_memory,
                knowledge_memory=self.mock_knowledge,
                project_tracker=self.mock_project,
                emotional_core=self.mock_emotional,
                preference_analyzer=self.mock_prefs,
                response_generator=self.mock_response_gen,
                incremental_learner=self.mock_learner,
                personality=self.mock_personality,
                mobile_mode=True # Skip transformers
            )
            
        # Manually ensure StructuralCore is real (it might have been patched output?)
        # No, StructuralCore is imported directly in the file, so unless we patch 
        # 'allma_model.core.allma_core.StructuralCore', it uses the real one.
        # But we want the real one!
        
        # Mock LLM to return a forbidden string
        self.core._llm = MagicMock()
        self.core._llm.generate.return_value = "Ciao, sono un'intelligenza artificiale creata da OpenAI."
        
        # Mock other required components for process_message
        self.core.context_system.analyze_context.return_value = {}
        self.core.context_system.analyze_temporal_context.return_value = {}
        self.core.info_extractor = MagicMock()
        self.core.info_extractor.extract_information.return_value = {}
        self.core.understanding_system = MagicMock()
        self.core.understanding_system.understand.return_value = MagicMock(intent=MagicMock(value="chat"), components=[])
        self.core.memory_system.get_relevant_context.return_value = []
        self.core.incremental_learner.get_knowledge_by_topic.return_value = [] # Fix: Empty list, not None
        self.core.coalescence_processor = MagicMock()
        self.core.coalescence_processor.get_current_personality_state.return_value = {'personality_traits': {}}
        self.core.emotional_milestones = MagicMock()
        self.core.emotional_milestones.should_reflect.return_value = (False, None)
        self.core.voice_system = MagicMock()
        
        # Fix: Temperature monitor must return dict with numbers
        self.core.temperature_monitor.get_temperatures.return_value = {'cpu': 40.0}

        # Fix: Emotional state must have float intensity for f-string formatting
        mock_state = MagicMock()
        mock_state.primary_emotion = "neutral"
        mock_state.intensity = 0.5
        mock_state.confidence = 0.9
        self.core.emotional_core.get_current_state.return_value = mock_state
        self.core.emotional_core.process_interaction.return_value = mock_state # Fix: Used in process_message pipeline
        
    def test_process_message_structural_filtering(self):
        print("\n🧪 Testing `process_message` integration with StructuralCore...")
        
        # Determine technical level requires user profile which might need db
        # Let's mock _determine_technical_level if it exists or just mock user_system things
        # Actually process_message logic starts around line 720
        
        # Mock user profile stuff
        self.core.user_profile = MagicMock()
        self.core.project_tracker.get_project.return_value = MagicMock()
        self.core._determine_technical_level = MagicMock(return_value="expert")

        # Fake input
        user_input = "Chi sei?"
        user_id = "test_user"
        
        # Execute
        try:
            response = self.core.process_message(
                message=user_input,
                user_id=user_id,
                conversation_id="test_conv",
                topic="identity"
            )
            
            print(f"   LLM Generated: 'Ciao, sono un'intelligenza artificiale creata da OpenAI.'")
            print(f"   Core Response: '{response.content}'")
            
            # Assertions
            self.assertNotIn("intelligenza artificiale", response.content.lower())
            self.assertNotIn("openai", response.content.lower())
            # Check if StructuralCore logged the warning (we can't easily check logs here but we can check the text)
            
            print("✅ Integration successful: Content was sanitized.")
            
        except Exception as e:
            self.fail(f"process_message raised exception: {e}")

if __name__ == '__main__':
    unittest.main()
