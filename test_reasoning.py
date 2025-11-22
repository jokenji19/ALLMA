#!/usr/bin/env python3
"""
Test Reasoning Engine
=====================

Test per verificare il funzionamento del "Flusso di Coscienza".
"""

import sys
import os
import logging
from datetime import datetime

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from Model.core.allma_core import ALLMACore

logging.basicConfig(level=logging.INFO, format='%(message)s')

def test_reasoning_engine():
    print("=" * 70)
    print("🧠 TEST REASONING ENGINE (STREAM OF CONSCIOUSNESS)")
    print("=" * 70)
    
    # Inizializza ALLMA
    print("\n1️⃣  Inizializzazione ALLMA...")
    allma = ALLMACore(mobile_mode=True)
    allma.start_conversation("test_reasoning")
    
    # Test cases
    test_inputs = [
        "Non so cosa fare della mia vita...",
        "Cos'è Python?",
        "Sono felice oggi!"
    ]
    
    for msg in test_inputs:
        print(f"\n\n👤 User: {msg}")
        print("-" * 40)
        
        # Esegui process_message (che ora include il reasoning)
        # Nota: process_message logga il pensiero come INFO, quindi lo vedremo nell'output
        response = allma.process_message("test_reasoning", "conv1", msg)
        
        print("-" * 40)
        print(f"🤖 ALLMA: {response.content[:100]}...")

if __name__ == "__main__":
    test_reasoning_engine()
