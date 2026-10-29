
import time
import logging
import sys
import os
from datetime import datetime

# Add path
sys.path.append("/Users/erikahu/ALLMA/ALLMA_V4")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


import time
import logging
import sys
import os
from datetime import datetime

# Add path
sys.path.append("/Users/erikahu/ALLMA/ALLMA_V4")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def verify_dreaming_full():
    print("test: Initializing Core...")
    try:
        from allma_model.core.allma_core import ALLMACore
        # Mobile mode to skip heavy LLM loading
        core = ALLMACore(mobile_mode=True, db_path="dream_test_v2.db")
        conv_id = core.start_conversation("user_test")

        # 1. Populate Knowledge Base to trigger Dynamic Curiosity
        # We need to access incremental_learner. But it's inside dream_manager? No, core has it.
        # Core initializes it.
        
        from allma_model.learning_system.incremental_learning import LearningUnit, ConfidenceLevel
        
        print("test: Populating Knowledge Base...")
        unit = LearningUnit(
            topic="quantum_computing",
            content="Quantum superposition allows qubits to be in multiple states at once.",
            source="user_test",
            confidence=ConfidenceLevel.MEDIUM,
            timestamp=datetime.now()
        )
        core.incremental_learner.add_learning_unit(unit)
        
        # Mock LLM for Dream Generation
        class MockLLM:
            def generate(self, prompt, *args, **kwargs):
                if "quantum_computing" in prompt:
                    return "What if we could use superposition for human decision making?"
                return "Generic curiosity?"
        
        # Inject Mock LLM into reasoning engine (which dream manager uses)
        # Check how dream manager gets reasoning engine.
        # It's passed in init. core.reasoning_engine.
        core.reasoning_engine.llm = MockLLM()

        # 1. Trigger Dream (Empty Memory -> Curiosity)
        print("test: Triggering Dream/Curiosity...")
        core.dream_manager.current_user_id = "user_test"
        core.dream_manager._fetch_unconsolidated_memories = lambda: []
        
        core.dream_manager._start_dream_thread()  # Start directly
        
        print("test: Waiting for Dream Cycle (5s)...")
        time.sleep(5)
        
        # 2. Check Pending Verification
        pending = core.dream_manager.pending_verification
        if pending:
            print(f"test: SUCCESS - Pending Verifications found: {len(pending)}")
            print(f"test: First Insight: {pending[0]['text']}")
            if "superposition" in pending[0]['text']:
                print("test: SUCCESS - Dynamic Curiosity generated correctly from Knowledge Base.")
            else:
                print("test: WARNING - Curiosity text does not match expected dynamic output (Fallback used?).")
        else:
            print("test: FAILURE - No pending verifications generated (Curiosity failed?)")
            return

        # 3. Trigger User Feedback Loop
        print("test: Sending Greeting 'Ciao'...")
        
        # Mock LLM (Again, for core process_message if needed)
        core._llm = MockLLM()
        
        response = core.process_message(conv_id, "user_test", "Ciao ALLMA")
        print("test: Message processed.")
        
        # Check if pending was cleared
        if not core.dream_manager.pending_verification:
            print("test: SUCCESS - Pending verification was consumed by the greeting.")
        else:
            print("test: FAILURE - Pending verification still exists (Injection failed).")

    except Exception as e:
        print(f"test: ERROR: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    verify_dreaming_full()

