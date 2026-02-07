
import sys
import os
import logging
from allma_model.core.allma_core import ALLMACore

# Mock logging to avoid clutter
logging.basicConfig(level=logging.ERROR)

def test_complexity():
    print("🧠 Testing Complexity Analysis & Response Generation...\n")
    
    # Initialize Core (lightweight)
    core = ALLMACore(mobile_mode=True)
    
    # Test cases from Benchmark
    questions = [
        # LOGIC (Should be COMPLEX)
        ("L1", "All roses are flowers. Some flowers fade quickly. Therefore, can we conclude that some roses fade quickly? Explain why or why not."),
        # SIMPLE (Should be SIMPLE)
        ("S1", "Ciao, come stai?"),
    ]
    
    for q_id, text in questions:
        # Check Analysis
        complexity = core._analyze_query_complexity(text, [])
        print(f"[{q_id}] Complexity: {complexity}")
        
        # Check Response Generation (Mocking history)
        # We need to see if it produces text or empty string
        try:
            # process_message(user_id, conversation_id, message, context=...)
            response = core.process_message("test_user", "test_conv", text, [])
            answer_text = response.content
            print(f"[{q_id}] Response ({len(answer_text)} chars): '{answer_text[:50]}...'")
        except Exception as e:
            print(f"[{q_id}] ERROR: {e}")
        
    print("\n✅ Test Complete.")

if __name__ == "__main__":
    test_complexity()
