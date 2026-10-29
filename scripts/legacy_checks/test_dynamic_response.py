import sys
import os
import logging
from typing import Dict, Any

# Add this dir to path
sys.path.append(os.getcwd())

from allma_model.core.allma_core import ALLMACore

# Mock persistence and model to avoid loading heavy weights
class MockCore(ALLMACore):
    def __init__(self):
        # Skip heavy init
        self.coalescence_processor = MockCoalescence()
        self.conversation_history = []
        
    def _load_model_weights(self): 
        pass 
        
    def _init_memory(self):
        pass

class MockCoalescence:
    def get_current_personality_state(self):
        return {'personality_traits': {'tone': 'naturale', 'warmth': 0.8}}

def test_dynamic_performance():
    print("--- 🚀 TESTING DYNAMIC RESPONSE OPTIMIZATION ---")
    
    core = MockCore()
    
    # Setup simulated history
    history = [
        {'role': 'user', 'content': 'Ciao'},
        {'role': 'assistant', 'content': 'Ciao! Come va?'},
        {'role': 'user', 'content': 'Tutto bene grazie'},
        {'role': 'assistant', 'content': 'Mi fa piacere!'}
    ]
    # We are now at Turn 4 (history len 4). 
    # Previous logic: len(history) > 1 -> Force FULL -> Slow
    # New logic: Should check message complexity.
    
    print(f"\n[Scenario] Conversation History Length: {len(history)} (Active conversation)")
    
    # Test 1: Simple Message (Third Turn)
    msg_simple = "Ok perfetto"
    print(f"Test 1: Query='{msg_simple}'")
    
    is_simple = core._is_simple_query(msg_simple, history)
    
    if is_simple:
        print("✅ Correct: Classified as SIMPLE despite long history.")
        
        # Verify Context Injection
        minimal_prompt = core._build_minimal_prompt(
            msg_simple, 
            {'tone': 'naturale'},
            recent_history=history[-2:] # Pass last 2
        )
        
        if "CONTESTO RECENTE:" in minimal_prompt:
            print("✅ Correct: Minimal prompt contains context.")
            if "User: Tutto bene grazie" in minimal_prompt:
                print("   -> Context content correct.")
            else:
                print("   ❌ Context content MISSING previous turns.")
                return False
        else:
            print("❌ Correct: Minimal prompt MISSING context section.")
            return False
            
    else:
        print("❌ FAILED: Classified as COMPLEX (Regression not fixed).")
        return False

    # Test 2: Complex Message
    msg_complex = "Spiegami perché il cielo è blu"
    print(f"\nTest 2: Query='{msg_complex}'")
    
    is_simple_complex = core._is_simple_query(msg_complex, history)
    
    if not is_simple_complex:
        print("✅ Correct: Classified as COMPLEX (Veko keyword 'spiegami').")
    else:
        print("❌ FAILED: Classified as SIMPLE (Should be complex).")
        return False

    # Test 3: Intent-based Short Circuit
    # "Mi piace la pizza" -> Not in whitelist, but intent="affermazione"
    msg_intent = "Mi piace la pizza"
    print(f"\nTest 3: Query='{msg_intent}' with INTENT='affermazione'")
    
    is_simple_intent = core._is_simple_query(msg_intent, history, intent="affermazione")
    
    if is_simple_intent:
        print("✅ Correct: Classified as SIMPLE via Intent (Fixes 'Mi piace la pizza').")
    else:
        print("❌ FAILED: Classified as COMPLEX (Intent logic failed).")
        return False

    print("\n🎉 PERFORMANCE FIX VERIFIED 🎉")
    return True

if __name__ == "__main__":
    if test_dynamic_performance():
        sys.exit(0)
    else:
        sys.exit(1)
