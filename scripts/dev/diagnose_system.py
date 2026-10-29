
import sys
import unittest
from unittest.mock import MagicMock, patch
import logging

# Configure logging to capture critical errors
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

sys.path.append("/Users/erikahu/ALLMA/ALLMA_V4")

# MOCK ALL HEAVY DEPENDENCIES AGGRESSIVELY
import types

# Mock numpy
mock_numpy = MagicMock()
mock_numpy.typing = MagicMock()
mock_numpy.__version__ = "1.26.0" # Satisfy pandas check
sys.modules['numpy'] = mock_numpy
sys.modules['numpy.typing'] = mock_numpy.typing

# Mock pandas
sys.modules['pandas'] = MagicMock()
sys.modules['pandas.compat'] = MagicMock()
sys.modules['pandas.compat.numpy'] = MagicMock()

# Mock cv2 (OpenCV)
sys.modules['cv2'] = MagicMock()

# Mock torch/transformers
sys.modules['torch'] = MagicMock()
sys.modules['transformers'] = MagicMock()
sys.modules['sentence_transformers'] = MagicMock()
sys.modules['huggingface_hub'] = MagicMock()

# Mock Kivy to prevent window opening
mock_kivy = MagicMock()
mock_kivy.utils = MagicMock()
mock_kivy.app = MagicMock()
mock_kivy.uix = MagicMock()
mock_kivy.core = MagicMock()
mock_kivy.clock = MagicMock()
sys.modules['kivy'] = mock_kivy
sys.modules['kivy.utils'] = mock_kivy.utils
sys.modules['kivy.app'] = mock_kivy.app
sys.modules['kivy.uix'] = mock_kivy.uix
sys.modules['kivy.core'] = mock_kivy.core
sys.modules['kivy.clock'] = mock_kivy.clock


try:
    from allma_model.core.allma_core import ALLMACore
    from allma_model.emotional_system.emotional_core import EmotionalState
except ImportError as e:
    print(f"❌ CRITICAL IMPORT ERROR: {e}")
    sys.exit(1)

class SystemDiagnosis(unittest.TestCase):
    def setUp(self):
        print("\n🏥 STARTING SYSTEM DIAGNOSIS...")
        
    @patch('allma_model.core.allma_core.pipeline') 
    @patch('allma_model.agency_system.ml_emotional_system.MLEmotionalSystem')
    def test_core_initialization_and_wiring(self, mock_ml, mock_pipeline):
        """Verify that ALLMA Core initializes all subsystems correctly."""
        try:
            core = ALLMACore(db_path=":memory:", mobile_mode=False, emotion_pipeline=MagicMock())
            # Force mock ML
            if hasattr(core, 'emotional_core'):
                core.emotional_core.ml_system = mock_ml
            
            print("✅ ALLMACore Initialized.")
            
            # 1. Check Soul Connection
            if hasattr(core, 'soul') and core.soul:
                print(f"✅ Soul Connected. State: Energy={core.soul.state.energy:.2f}")
            else:
                print("❌ Soul NOT Connected!")
                
            # 2. Check Emotional Core
            if hasattr(core, 'emotional_core') and core.emotional_core:
                print("✅ Emotional Core Connected.")
            else:
                print("❌ Emotional Core NOT Connected!")

            # 3. Check Module Orchestrator
            if hasattr(core, 'module_orchestrator'):
                 print("✅ Module Orchestrator Present.")
            else:
                 print("⚠️ Module Orchestrator Monitor: Not strictly required but checked.")

            # 4. Dry Run Logic
            print("🔄 Attempting Dry Run of process_message (Refactored Pipeline)...")
            
            # Mock LLM generation to avoid calling actual model
            core._llm = MagicMock()
            core._llm.generate.return_value = "[[TH: I=Test|S=Calm]] Test Response"
            
            # Run
            response = core.process_message(
                user_id="diag_user",
                conversation_id="diag_chat",
                message="System Check"
            )
            
            if response:
                print("✅ Dry Run Successful. Response generated.")
            else:
                print("❌ Dry Run Failed. No response returned.")

        except Exception as e:
            print(f"❌ SYSTEM CRASH DURING DIAGNOSIS: {e}")
            import traceback
            traceback.print_exc()
            raise e

if __name__ == '__main__':
    unittest.main(verbosity=0)
