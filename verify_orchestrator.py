import sys
import os
import time
from typing import Dict, Any

# Add this dir to path
sys.path.append(os.getcwd())

from allma_model.core.module_orchestrator import ModuleOrchestrator, ModulePriority
from allma_model.core.module_state_manager import ModuleStateManager

# Mock helper classes
class MockModule:
    """Mock module for testing orchestration"""
    def __init__(self, name, response_key, response_val):
        self.name = name
        self.response_key = response_key
        self.response_val = response_val
        
    def process(self, input_text, context):
        return {self.response_key: self.response_val}

def test_orchestration_selection():
    print("\n--- Testing Orchestrator Selection ---")
    orchestrator = ModuleOrchestrator()
    
    # Register Mock Modules
    mod_emotional = MockModule("emotional_adaptation", "response", "Sono felice!")
    orchestrator.register_module(
        "emotional_adaptation", mod_emotional, ModulePriority.HIGH, 50
    )
    
    mod_curiosity = MockModule("curiosity_system", "questions", ["Come stai?"])
    orchestrator.register_module(
        "curiosity_system", mod_curiosity, ModulePriority.MEDIUM, 50
    )
    
    # Test 1: Intent = 'joy' -> Should run Emotional, Skips Curiosity
    print("Test 1: Intent='joy' context={} (Expected: Emotional only)")
    results_joy = orchestrator.process("Sono felice", {}, intent='joy')
    
    if "emotional_adaptation" in results_joy['raw_results']:
        print("✅ Emotional module ran for 'joy'.")
    else:
        print("❌ FAILED: Emotional module skipped for 'joy'.")
        return False
        
    if "curiosity_system" not in results_joy['raw_results']:
         print("✅ Curiosity module skipped for 'joy'.")
    else:
         print("❌ FAILED: Curiosity module ran for 'joy' (Should be skipped).")
         return False

    # Test 2: Intent = 'question' -> Should run Curiosity, Skips Emotional
    print("\nTest 2: Intent='question' context={} (Expected: Curiosity only)")
    results_q = orchestrator.process("Cosa succede?", {}, intent='question')
    
    if "curiosity_system" in results_q['raw_results']:
        print("✅ Curiosity module ran for 'question'.")
    else:
        print("❌ FAILED: Curiosity module skipped for 'question'.")
        return False
        
    if "emotional_adaptation" not in results_q['raw_results']:
         print("✅ Emotional module skipped for 'question'.")
    else:
         print("❌ FAILED: Emotional module ran for 'question' (Should be skipped).")
         return False
         
    return True

def test_orchestration_coalescence():
    print("\n--- Testing Orchestrator Coalescence ---")
    orchestrator = ModuleOrchestrator()
    
    # Register modules that will run
    mod_emotional = MockModule("emotional_adaptation", "response", "Che bello!")
    orchestrator.register_module(
        "emotional_adaptation", mod_emotional, ModulePriority.HIGH, 50
    )
    
    mod_curiosity = MockModule("curiosity_system", "questions", ["Perché è bello?", "Raccontami."])
    orchestrator.register_module(
        "curiosity_system", mod_curiosity, ModulePriority.MEDIUM, 50
    )
    
    # Force both to run by simulation or broad intent? 
    # Or just test _merge_intelligent directly? 
    # Better to test _merge_intelligent directly to avoid selection logic interference in this unit test.
    
    raw_results = {
        'emotional_adaptation': {'response': "Che bello!"},
        'curiosity_system': {'questions': ["Perché è bello?", "Raccontami."]},
        'meta_learner': {'strategy': 'elaboration', 'hints': ['Usa metafore']}
    }
    
    merged = orchestrator._merge_intelligent(raw_results)
    
    print(f"Merged Result: {merged}")
    
    # 1. User Prefix should contain emotional response + first question
    expected_prefix = "Che bello! \nMi chiedo: Perché è bello?"
    if merged['user_prefix'] == expected_prefix:
        print("✅ User Prefix merged correctly.")
    else:
        print(f"❌ FAILED: User prefix mismatch.\nExp: {expected_prefix}\nGot: {merged['user_prefix']}")
        return False
        
    # 2. System Instruction should contain hints + extra questions
    if "Usa metafore" in merged['system_instruction'] and "Consider exploring: Raccontami." in merged['system_instruction']:
        print("✅ System Instructions merged correctly.")
    else:
        print(f"❌ FAILED: System instructions mismatch. Got: {merged['system_instruction']}")
        return False
        
    return True

if __name__ == "__main__":
    sel_pass = test_orchestration_selection()
    coal_pass = test_orchestration_coalescence()
    
    if sel_pass and coal_pass:
        print("\n✅ ORCHESTRATION VERIFIED!")
        sys.exit(0)
    else:
        print("\n❌ VERIFICATION FAILED")
        sys.exit(1)
