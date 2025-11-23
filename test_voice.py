#!/usr/bin/env python3
"""
Test Voice System
=================
Verifica la modulazione emotiva della voce.
"""

import sys
import os
import logging

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.voice_system.voice_core import VoiceSystem

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_voice():
    print("=" * 70)
    print("🔊 TEST VOICE SYSTEM (TTS EMOTIVO)")
    print("=" * 70)
    
    voice = VoiceSystem()
    
    # Test 1: Gioia (Alta intensità)
    print("\n1️⃣  Test: Gioia (Intensità 0.9)")
    params = voice.get_voice_parameters('joy', 0.9)
    print(f"Params: {params}")
    
    if params['pitch'] > 1.0 and params['rate'] > 1.0:
        print("✅ SUCCESS: Pitch e Rate aumentati (Voce allegra).")
    else:
        print("❌ FAIL: Parametri non corretti per Gioia.")
        
    # Test 2: Tristezza (Alta intensità)
    print("\n2️⃣  Test: Tristezza (Intensità 0.8)")
    params = voice.get_voice_parameters('sadness', 0.8)
    print(f"Params: {params}")
    
    if params['pitch'] < 1.0 and params['rate'] < 1.0:
        print("✅ SUCCESS: Pitch e Rate diminuiti (Voce triste).")
    else:
        print("❌ FAIL: Parametri non corretti per Tristezza.")

    # Test 3: Simulazione Speak
    print("\n3️⃣  Simulazione Output")
    voice.speak("Sono così felice di vederti!", voice.get_voice_parameters('joy', 0.9))
    voice.speak("Mi sento un po' giù oggi...", voice.get_voice_parameters('sadness', 0.8))

if __name__ == "__main__":
    test_voice()
