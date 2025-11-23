#!/usr/bin/env python3
"""
Test Dynamic Response Engine
============================
Verifica che le risposte di sistema siano varie e non ripetitive.
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.response_system.dynamic_response_engine import DynamicResponseEngine

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_dynamic_responses():
    print("=" * 70)
    print("🚫 TEST DYNAMIC RESPONSE ENGINE (NO TEMPLATES)")
    print("=" * 70)
    
    engine = DynamicResponseEngine()
    
    # Test 1: Fallback Procedurale (Errori)
    print("\n1️⃣  Test Fallback Procedurale (Errori)")
    print("Generazione di 5 messaggi di errore consecutivi (devono variare):")
    responses = set()
    for i in range(5):
        msg = engine.generate_system_response('error', {'error': 'Test Error'})
        print(f"  Attempt {i+1}: {msg}")
        responses.add(msg)
        
    if len(responses) > 1:
        print("✅ SUCCESS: I messaggi variano.")
    else:
        print("❌ FAIL: I messaggi sono identici.")

    # Test 2: Fallback Procedurale (Saluti)
    print("\n2️⃣  Test Fallback Procedurale (Saluti)")
    print("Generazione di 5 saluti per 'Marco':")
    responses = set()
    for i in range(5):
        msg = engine.generate_system_response('greeting', {'user': 'Marco'})
        print(f"  Attempt {i+1}: {msg}")
        responses.add(msg)
        
    if len(responses) > 1:
        print("✅ SUCCESS: I saluti variano.")
    else:
        print("❌ FAIL: I saluti sono identici.")

    # Test 3: Generazione LLM (Mock)
    print("\n3️⃣  Test Generazione LLM (Creatività)")
    
    def mock_llm(prompt, **kwargs):
        return {'choices': [{'text': "Oh no! Un glitch nel matrix... ma sono ancora qui!"}]}
        
    msg = engine.generate_system_response(
        'error', 
        {'error': 'Connection Lost'}, 
        llm_callback=mock_llm
    )
    print(f"  LLM Response: {msg}")
    
    if "glitch nel matrix" in msg:
        print("✅ SUCCESS: LLM invocato correttamente.")
    else:
        print("❌ FAIL: LLM non usato.")

if __name__ == "__main__":
    test_dynamic_responses()
